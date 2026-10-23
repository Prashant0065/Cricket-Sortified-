from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_current_user
from backend.database.connection import get_connection
from backend.services.cricbuzz_sync import sync_live_match_metadata
from backend.services.cricbuzz_client import CricbuzzAPIError

router = APIRouter(
    prefix="/sync",
    tags=["Data Synchronization"],
)


def is_admin(user_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM user_roles AS ur
                    JOIN roles AS r ON r.role_id = ur.role_id
                    WHERE ur.user_id = %s
                      AND LOWER(r.name) = 'admin'
                );
                """,
                (user_id,),
            )
            result = cur.fetchone()

    return bool(result and result[0])


@router.post("/live-match-metadata")
def sync_live_match_metadata_route(
    dry_run: bool = Query(
        default=True,
        description=(
            "Preview changes when true; commit changes when false. "
            "Admin required to commit."
        ),
    ),
    current_user: dict = Depends(get_current_user),
):
    if not dry_run:
        print(
            "DEBUG current_user:",
            {
                "user_id": current_user.get("user_id"),
                "username": current_user.get("username"),
                "email": current_user.get("email"),
            },
            flush=True,
        )

        try:
            user_id = current_user.get("user_id")

            if user_id is None:
                raise HTTPException(
                    status_code=401,
                    detail="Authenticated user ID is missing.",
                )

            admin_result = is_admin(user_id)

            print(
                "DEBUG is_admin:",
                admin_result,
                flush=True,
            )

            if not admin_result:
                raise HTTPException(
                    status_code=403,
                    detail="Admin role required to commit synchronization.",
                )

        except HTTPException:
            raise

        except Exception as error:
            print(
                "ERROR verifying admin permissions:",
                repr(error),
                flush=True,
            )
            raise HTTPException(
                status_code=503,
                detail="Could not verify admin permissions.",
            ) from error

    try:
        return sync_live_match_metadata(dry_run=dry_run)

    except CricbuzzAPIError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    except Exception as error:
        print(
            "ERROR during live match metadata synchronization:",
            repr(error),
            flush=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Live match metadata synchronization failed. "
                "Check backend logs."
            ),
        ) from error
