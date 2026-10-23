
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_current_user
from backend.database.connection import get_connection
from backend.services.cricbuzz_client import CricbuzzAPIError
from backend.services.scorecard_import import (
    import_scorecard,
    ScorecardImportError,
)

router = APIRouter(prefix="/sync", tags=["Data Synchronization"])


def _is_admin(user_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM user_roles ur
                    JOIN roles r ON r.role_id = ur.role_id
                    WHERE ur.user_id = %s
                      AND LOWER(r.name) = 'admin'
                )
                """,
                (user_id,),
            )
            row = cur.fetchone()

    return bool(row and row[0])


def _require_admin(current_user: dict) -> None:
    """Reject non-admin users before any external API request is made."""
    user_id = current_user.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user ID is missing.",
        )

    try:
        admin = _is_admin(int(user_id))
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user ID is invalid.",
        ) from error
    except Exception as error:
        print("Admin permission check failed:", repr(error), flush=True)
        raise HTTPException(
            status_code=503,
            detail="Could not verify admin permissions.",
        ) from error

    if not admin:
        raise HTTPException(
            status_code=403,
            detail="Admin role required to synchronize scorecards.",
        )


@router.post("/scorecard/{external_match_id}")
def sync_scorecard(
    external_match_id: int,
    dry_run: bool = Query(
        default=True,
        description=(
            "Admin-only endpoint. True previews and rolls back; "
            "false commits the scorecard import."
        ),
    ),
    current_user: dict = Depends(get_current_user),
):
    if external_match_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="External match ID must be positive.",
        )

    # Check permissions before calling Cricbuzz, even in dry-run mode.
    _require_admin(current_user)

    try:
        return import_scorecard(
            external_match_id,
            dry_run=dry_run,
        )
    except CricbuzzAPIError as error:
        print(f"Cricbuzz API error: {error}", flush=True)
        raise HTTPException(
            status_code=502,
            detail="Cricbuzz scorecard request failed. Check backend logs.",
        ) from error
    except ScorecardImportError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except Exception as error:
        print("Scorecard import failed:", repr(error), flush=True)
        raise HTTPException(
            status_code=500,
            detail="Scorecard import failed. Check backend logs.",
        ) from error


@router.post("/scorecards/bulk")
def bulk_sync_scorecards(
    dry_run: bool = Query(
        default=True,
        description=(
            "Admin-only endpoint. True previews and rolls back each match; "
            "false commits each successful match."
        ),
    ),
    max_matches: int = Query(
        default=5,
        ge=1,
        le=10,
        description="Maximum eligible matches to process in this batch.",
    ),
    current_user: dict = Depends(get_current_user),
):
    # Check permissions before querying candidates or calling Cricbuzz.
    _require_admin(current_user)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        m.external_id,
                        m.match_id,
                        m.winner_team_id,
                        EXISTS (
                            SELECT 1
                            FROM innings i
                            WHERE i.match_id = m.match_id
                        ) AS has_innings
                    FROM matches m
                    WHERE LOWER(m.status) = 'completed'
                      AND m.external_id IS NOT NULL
                      AND (
                          m.winner_team_id IS NULL
                          OR NOT EXISTS (
                              SELECT 1
                              FROM innings i
                              WHERE i.match_id = m.match_id
                          )
                      )
                    ORDER BY
                        CASE
                            WHEN m.winner_team_id IS NULL THEN 0
                            ELSE 1
                        END,
                        m.match_id
                    LIMIT %s
                    """,
                    (max_matches,),
                )

                candidates = cur.fetchall()

        matches = [
            {
                "external_match_id": int(row[0]),
                "local_match_id": int(row[1]),
                "winner_missing": row[2] is None,
                "innings_missing": not bool(row[3]),
            }
            for row in candidates
        ]

    except Exception as error:
        print("Bulk sync candidate query failed:", repr(error), flush=True)
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve eligible matches. Check backend logs.",
        ) from error

    results = []
    scorecards_processed = 0
    failed = 0
    results_recognized = 0
    warnings_count = 0
    committed_matches = 0

    for candidate in matches:
        external_match_id = candidate["external_match_id"]

        try:
            result = import_scorecard(
                external_match_id=external_match_id,
                dry_run=dry_run,
            )

            warnings = result.get("warnings", [])
            result_preview = result.get("result_update_preview")

            scorecards_processed += 1
            warnings_count += len(warnings)

            if result_preview:
                results_recognized += 1

            if not dry_run and result.get("database_changed") is True:
                committed_matches += 1

            results.append(
                {
                    "external_match_id": external_match_id,
                    "local_match_id": candidate["local_match_id"],
                    "success": True,
                    "scorecard_processed": (
                        result.get("innings_processed", 0) > 0
                    ),
                    "innings_processed": result.get(
                        "innings_processed", 0
                    ),
                    "batters_processed": result.get(
                        "batters_processed", 0
                    ),
                    "bowlers_processed": result.get(
                        "bowlers_processed", 0
                    ),
                    "match_result": result.get("match_result"),
                    "result_update_preview": result_preview,
                    "result_recognized": result_preview is not None,
                    "database_changed": result.get(
                        "database_changed", False
                    ),
                    "warnings": warnings,
                    "message": result.get("message", ""),
                }
            )

        except CricbuzzAPIError:
            failed += 1
            print(
                f"Cricbuzz API failed for external match "
                f"{external_match_id}",
                flush=True,
            )
            results.append(
                {
                    "external_match_id": external_match_id,
                    "local_match_id": candidate["local_match_id"],
                    "success": False,
                    "error": "Cricbuzz API request failed.",
                }
            )

        except ScorecardImportError as error:
            failed += 1
            results.append(
                {
                    "external_match_id": external_match_id,
                    "local_match_id": candidate["local_match_id"],
                    "success": False,
                    "error": str(error),
                }
            )

        except Exception as error:
            failed += 1
            print(
                f"Bulk scorecard import failed for "
                f"{external_match_id}: {repr(error)}",
                flush=True,
            )
            results.append(
                {
                    "external_match_id": external_match_id,
                    "local_match_id": candidate["local_match_id"],
                    "success": False,
                    "error": (
                        "Unexpected import error. Check backend logs."
                    ),
                }
            )

    return {
        "mode": "dry_run" if dry_run else "sync",
        "database_changed": committed_matches > 0,
        "matches_found": len(matches),
        "scorecards_processed": scorecards_processed,
        "failed": failed,
        "results_recognized_or_previewed": results_recognized,
        "warnings_count": warnings_count,
        "matches_committed": committed_matches,
        "results": results,
    }
