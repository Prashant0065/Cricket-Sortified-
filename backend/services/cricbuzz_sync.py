
"""Synchronize Cricbuzz live-match metadata with PostgreSQL.

Dry-run mode is enabled by default. No changes are committed in dry-run mode.
This module synchronizes match metadata and participating teams only.
"""

from datetime import datetime, timezone
from typing import Any

from backend.database.connection import get_connection
from backend.services.cricbuzz_client import get_live_matches


ALLOWED_STATUSES = {
    "scheduled",
    "live",
    "completed",
    "abandoned",
    "no_result",
}

FORMAT_LABELS = {
    "TEST": ("Test Cricket", "International"),
    "T20": ("Twenty20", "Limited Overs"),
    "T20I": ("Twenty20 International", "International"),
    "ODI": ("One Day International", "International"),
    "FIRSTCLASS": ("First-Class Cricket", "Domestic"),
    "LISTA": ("List A Cricket", "Domestic"),
}


def _text(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default

    value = str(value).strip()
    return value or default


def _external_id(value: Any) -> str | None:
    value = _text(value)

    if value is None:
        return None

    if value.lower() in {"none", "null", "undefined"}:
        return None

    return value


def _parse_start_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None

    try:
        timestamp = int(value)

        if timestamp > 10_000_000_000:
            return datetime.fromtimestamp(
                timestamp / 1000,
                tz=timezone.utc,
            )

        if timestamp > 0:
            return datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            )

    except (TypeError, ValueError, OSError, OverflowError):
        pass

    try:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed

    except (TypeError, ValueError):
        return None



def _extract_matches(payload: Any) -> list[dict]:
    """Extract matchInfo records and deduplicate by Cricbuzz matchId."""

    if not isinstance(payload, dict):
        raise ValueError(
            "Cricbuzz live-matches response must be a JSON object."
        )

    matches_by_id = {}
    matches_without_id = []

    for type_group in payload.get("typeMatches", []) or []:
        if not isinstance(type_group, dict):
            continue

        for series_group in type_group.get("seriesMatches", []) or []:
            if not isinstance(series_group, dict):
                continue

            wrapper = series_group.get("seriesAdWrapper") or {}

            if not isinstance(wrapper, dict):
                continue

            for item in wrapper.get("matches", []) or []:
                if not isinstance(item, dict):
                    continue

                info = item.get("matchInfo") or {}

                if not isinstance(info, dict) or not info:
                    continue

                match_id = _external_id(info.get("matchId"))

                if not match_id:
                    matches_without_id.append(info)
                    continue

                if match_id not in matches_by_id:
                    matches_by_id[match_id] = info

    return list(matches_by_id.values()) + matches_without_id


def _normalise_format(
    value: Any,
) -> tuple[str, str, str]:
    code = (
        _text(value, "OTHER") or "OTHER"
    ).upper().replace(" ", "")[:20]

    name, category = FORMAT_LABELS.get(
        code,
        (code, "Cricket"),
    )

    return code, name, category


def _normalise_status(
    status: Any,
    state: Any = None,
) -> str:
    """Map known Cricbuzz statuses to values accepted by PostgreSQL."""

    raw_status = _text(status, "") or ""
    raw_state = _text(state, "") or ""
    text = f"{raw_status} {raw_state}".strip().lower()

    if any(term in text for term in (
        "abandoned", "cancelled", "canceled"
    )):
        return "abandoned"

    if any(term in text for term in (
        "no result", "no-result", "without a result"
    )):
        return "no_result"

    if any(term in text for term in (
        "won by", "drawn", "match drawn", "tied",
        "match tied", "result:"
    )):
        return "completed"

    if any(term in text for term in (
        "upcoming", "not started", "starts at",
        "scheduled", "yet to begin", "match begins",
        "match starts"
    )):
        return "scheduled"

    if any(term in text for term in (
        "live", "innings break", "stumps", "day ",
        "session", "lunch", "tea break", "need ",
        "trail by", "lead by", "overs", "in progress",
        "opt to", "opted to"
    )):
        return "live"

    # Unknown statuses default to scheduled instead of being
    # incorrectly classified as live.
    return "scheduled"


def _upsert_format(cur, raw_format: Any) -> int:
    """Find a format by its unique code or insert it."""

    code, name, category = _normalise_format(raw_format)

    cur.execute(
        "SELECT format_id FROM formats WHERE code = %s",
        (code,),
    )
    row = cur.fetchone()

    if row:
        # Preserve existing format names and categories.
        return row[0]

    cur.execute(
        """
        INSERT INTO formats (code, name, category)
        VALUES (%s, %s, %s)
        RETURNING format_id
        """,
        (code, name, category),
    )

    return cur.fetchone()[0]


def _upsert_team(cur, team: Any) -> int | None:
    """Resolve a team by external ID or an unambiguous fallback."""

    if not isinstance(team, dict):
        return None

    name = _text(team.get("teamName") or team.get("name"))
    external_id = _external_id(
        team.get("teamId") or team.get("id")
    )
    country = _text(
        team.get("countryName") or team.get("country")
    )

    if not name:
        return None

    if external_id:
        cur.execute(
            """
            SELECT team_id
            FROM teams
            WHERE external_id = %s
            LIMIT 1
            """,
            (external_id,),
        )
        row = cur.fetchone()

        if row:
            cur.execute(
                """
                UPDATE teams
                SET name = %s,
                    country = COALESCE(%s, country)
                WHERE team_id = %s
                """,
                (name, country, row[0]),
            )
            return row[0]

    if country is not None:
        cur.execute(
            """
            SELECT team_id, external_id
            FROM teams
            WHERE LOWER(name) = LOWER(%s)
              AND LOWER(country) = LOWER(%s)
            LIMIT 2
            """,
            (name, country),
        )
    else:
        cur.execute(
            """
            SELECT team_id, external_id
            FROM teams
            WHERE LOWER(name) = LOWER(%s)
              AND external_id IS NULL
            LIMIT 2
            """,
            (name,),
        )

    rows = cur.fetchall()

    if len(rows) == 1:
        team_id, existing_external_id = rows[0]

        if external_id and existing_external_id is None:
            cur.execute(
                """
                UPDATE teams
                SET external_id = %s
                WHERE team_id = %s
                """,
                (external_id, team_id),
            )

        return team_id

    cur.execute(
        """
        INSERT INTO teams (name, country, external_id)
        VALUES (%s, %s, %s)
        RETURNING team_id
        """,
        (name, country, external_id),
    )

    return cur.fetchone()[0]


def _upsert_series(
    cur,
    info: dict,
    format_id: int,
) -> int | None:
    """Resolve a series by external ID before a safe fallback."""

    name = _text(info.get("seriesName"))
    external_id = _external_id(info.get("seriesId"))

    if not name and not external_id:
        return None

    if external_id:
        cur.execute(
            """
            SELECT series_id
            FROM series
            WHERE external_id = %s
            LIMIT 1
            """,
            (external_id,),
        )
        row = cur.fetchone()

        if row:
            cur.execute(
                """
                UPDATE series
                SET name = %s,
                    format_id = COALESCE(%s, format_id)
                WHERE series_id = %s
                """,
                (
                    name or f"Series {external_id}",
                    format_id,
                    row[0],
                ),
            )
            return row[0]

    if name:
        cur.execute(
            """
            SELECT series_id
            FROM series
            WHERE LOWER(name) = LOWER(%s)
              AND external_id IS NULL
            LIMIT 2
            """,
            (name,),
        )
        rows = cur.fetchall()

        if len(rows) == 1:
            series_id = rows[0][0]

            if external_id:
                cur.execute(
                    """
                    UPDATE series
                    SET external_id = %s,
                        format_id = COALESCE(format_id, %s)
                    WHERE series_id = %s
                    """,
                    (external_id, format_id, series_id),
                )

            return series_id

    cur.execute(
        """
        INSERT INTO series (name, format_id, external_id)
        VALUES (%s, %s, %s)
        RETURNING series_id
        """,
        (
            name or f"Series {external_id}",
            format_id,
            external_id,
        ),
    )

    return cur.fetchone()[0]


def _upsert_venue(
    cur,
    venue: Any,
) -> int | None:
    """Resolve a venue using its external ID or safe fallback."""

    if not isinstance(venue, dict):
        return None

    name = _text(venue.get("ground") or venue.get("name"))
    external_id = _external_id(
        venue.get("id") or venue.get("venueId")
    )
    city = _text(venue.get("city"))
    country = _text(
        venue.get("country") or venue.get("countryName")
    )

    if not name and not external_id:
        return None

    if external_id:
        cur.execute(
            """
            SELECT venue_id
            FROM venues
            WHERE external_id = %s
            LIMIT 1
            """,
            (external_id,),
        )
        row = cur.fetchone()

        if row:
            cur.execute(
                """
                UPDATE venues
                SET name = %s,
                    city = COALESCE(%s, city),
                    country = COALESCE(%s, country)
                WHERE venue_id = %s
                """,
                (
                    name or f"Venue {external_id}",
                    city,
                    country,
                    row[0],
                ),
            )
            return row[0]

    fallback_name = name or f"Venue {external_id}"

    if city is not None:
        cur.execute(
            """
            SELECT venue_id, external_id
            FROM venues
            WHERE LOWER(name) = LOWER(%s)
              AND LOWER(city) = LOWER(%s)
            LIMIT 2
            """,
            (fallback_name, city),
        )
    else:
        cur.execute(
            """
            SELECT venue_id, external_id
            FROM venues
            WHERE LOWER(name) = LOWER(%s)
              AND external_id IS NULL
            LIMIT 2
            """,
            (fallback_name,),
        )

    rows = cur.fetchall()

    if len(rows) == 1:
        venue_id, existing_external_id = rows[0]

        if external_id and existing_external_id is None:
            cur.execute(
                """
                UPDATE venues
                SET external_id = %s,
                    country = COALESCE(%s, country)
                WHERE venue_id = %s
                """,
                (external_id, country, venue_id),
            )

        return venue_id

    cur.execute(
        """
        INSERT INTO venues (name, city, country, external_id)
        VALUES (%s, %s, %s, %s)
        RETURNING venue_id
        """,
        (fallback_name, city, country, external_id),
    )

    return cur.fetchone()[0]


def _upsert_match(
    cur,
    info: dict,
    series_id: int | None,
    venue_id: int | None,
    format_id: int,
) -> int:
    """Upsert a match by its Cricbuzz ID."""

    external_id = _external_id(info.get("matchId"))

    if not external_id:
        raise ValueError(
            "A match has no valid Cricbuzz matchId. "
            "The synchronization transaction will be rolled back."
        )

    description = _text(
        info.get("matchDesc") or info.get("description"),
        "Cricket match",
    )

    start_time = _parse_start_time(
        info.get("startDate") or info.get("startTime")
    )

    status = _normalise_status(
        info.get("status"),
        info.get("state"),
    )

    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported match status: {status}")

    cur.execute(
        """
        SELECT match_id
        FROM matches
        WHERE external_id = %s
        LIMIT 1
        """,
        (external_id,),
    )
    row = cur.fetchone()

    if row:
        cur.execute(
            """
            UPDATE matches
            SET series_id = COALESCE(%s, series_id),
                venue_id = COALESCE(%s, venue_id),
                format_id = %s,
                description = %s,
                start_time = COALESCE(%s, start_time),
                status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE match_id = %s
            """,
            (
                series_id,
                venue_id,
                format_id,
                description,
                start_time,
                status,
                row[0],
            ),
        )
        return row[0]

    cur.execute(
        """
        INSERT INTO matches (
            series_id,
            venue_id,
            format_id,
            description,
            start_time,
            status,
            external_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING match_id
        """,
        (
            series_id,
            venue_id,
            format_id,
            description,
            start_time,
            status,
            external_id,
        ),
    )

    return cur.fetchone()[0]


def sync_live_match_metadata(dry_run: bool = True) -> dict:
    """Preview or commit Cricbuzz live-match metadata synchronization."""

    if not isinstance(dry_run, bool):
        raise ValueError("dry_run must be a boolean.")

    payload = get_live_matches()
    matches = _extract_matches(payload)

    if not matches:
        return {
            "mode": "dry_run" if dry_run else "sync",
            "database_changed": False,
            "matches_found": 0,
            "matches_processed": 0,
            "matches_skipped": 0,
            "operation_counts": {},
            "preview": [],
            "message": (
                "Cricbuzz returned no match metadata; "
                "no database records were changed."
            ),
        }

    counts = {
        "formats_processed": 0,
        "series_resolved": 0,
        "teams_resolved": 0,
        "venues_resolved": 0,
        "matches_processed": 0,
        "match_team_links_inserted": 0,
    }

    preview = []
    skipped = []

    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                for info in matches:
                    external_match_id = _external_id(
                        info.get("matchId")
                    )

                    if not external_match_id:
                        skipped.append({
                            "reason": "Missing Cricbuzz matchId",
                            "description": _text(
                                info.get("matchDesc"),
                                "Unknown match",
                            ),
                        })
                        continue

                    code, _, _ = _normalise_format(
                        info.get("matchFormat")
                    )

                    format_id = _upsert_format(
                        cur,
                        info.get("matchFormat"),
                    )
                    counts["formats_processed"] += 1

                    # Diagnostic: inspect external series identity
                    # before resolving or inserting a series.
                    print(
                        "MATCH:",
                        info.get("matchId"),
                        "| SERIES ID:",
                        info.get("seriesId"),
                        "| SERIES NAME:",
                        info.get("seriesName"),
                        "| DESCRIPTION:",
                        info.get("matchDesc"),
                    )

                    
                    print(
                        "MATCH:",
                        info.get("matchId"),
                        "| SERIES ID:",
                        info.get("seriesId"),
                        "| SERIES NAME:",
                        info.get("seriesName"),
                        "| DESCRIPTION:",
                        info.get("matchDesc"),
                    )


                    series_id = _upsert_series(
                        cur,
                        info,
                        format_id,
                    )

                    if series_id is not None:
                        counts["series_resolved"] += 1

                    venue_id = _upsert_venue(
                        cur,
                        info.get("venueInfo"),
                    )

                    if venue_id is not None:
                        counts["venues_resolved"] += 1

                    match_id = _upsert_match(
                        cur,
                        info,
                        series_id,
                        venue_id,
                        format_id,
                    )
                    counts["matches_processed"] += 1

                    linked_teams = []

                    for team_key in ("team1", "team2"):
                        team = info.get(team_key)
                        team_id = _upsert_team(cur, team)

                        if team_id is None:
                            continue

                        counts["teams_resolved"] += 1

                        cur.execute(
                            """
                            INSERT INTO match_teams (
                                match_id,
                                team_id,
                                is_home
                            )
                            VALUES (%s, %s, %s)
                            ON CONFLICT (match_id, team_id)
                            DO NOTHING
                            """,
                            (
                                match_id,
                                team_id,
                                team_key == "team1",
                            ),
                        )

                        counts["match_team_links_inserted"] += (
                            cur.rowcount
                        )

                        if isinstance(team, dict):
                            team_name = _text(
                                team.get("teamName") or team.get("name")
                            )

                            if team_name:
                                linked_teams.append(team_name)

                    preview.append({
                        "external_match_id": external_match_id,
                        "description": _text(
                            info.get("matchDesc"),
                            "Cricket match",
                        ),
                        "series": _text(info.get("seriesName")),
                        "format": code,
                        "status": _normalise_status(
                            info.get("status"),
                            info.get("state"),
                        ),
                        "teams": linked_teams,
                    })

            if dry_run:
                conn.rollback()
            else:
                conn.commit()

        except Exception:
            conn.rollback()
            raise

    return {
        "mode": "dry_run" if dry_run else "sync",
        "database_changed": not dry_run,
        "matches_found": len(matches),
        "matches_processed": len(preview),
        "matches_skipped": len(skipped),
        "operation_counts": counts,
        "skipped_matches": skipped[:20],
        "preview": preview[:20],
        "message": (
            "Operations previewed and rolled back. "
            "No database changes were committed."
            if dry_run
            else "Live match metadata synchronization committed successfully."
        ),
    }
