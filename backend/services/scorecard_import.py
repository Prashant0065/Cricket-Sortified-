"""Import Cricbuzz scorecards and verified match results into PostgreSQL.

Safe by default:
- dry_run=True rolls back all database changes.
- dry_run=False commits the import.
- Match winners are updated only when the winner can be matched
  to exactly one team linked to the local match.
"""

from __future__ import annotations

import re
from typing import Any

from backend.database.connection import get_connection
from backend.services.cricbuzz_client import get_match_scorecard


class ScorecardImportError(Exception):
    """Raised when a scorecard cannot be safely mapped to the database."""


def _first(data: dict, *keys: str) -> Any:
    if not isinstance(data, dict):
        return None

    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value

    return None


def _as_int(value: Any, default: int | None = None) -> int | None:
    if value is None or value == "" or isinstance(value, bool):
        return default

    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default


def _as_bool_out(value: Any) -> bool:
    """Interpret a Cricbuzz dismissal description as out or not out."""
    if isinstance(value, bool):
        return value

    text = str(value or "").strip().casefold()

    if not text:
        return False

    not_out_values = {
        "not out",
        "notout",
        "false",
        "0",
        "no",
        "did not bat",
        "didn't bat",
        "dnb",
        "retired hurt",
        "retired not out",
        "absent hurt",
    }

    return text not in not_out_values


def _items(value: Any) -> list[dict]:
    """Convert a list or dictionary of player entries into a list."""
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]

    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]

    return []


def _overs_to_balls(value: Any) -> int | None:
    """Convert cricket overs notation such as 17.4 into 106 legal balls."""
    if value is None or value == "":
        return None

    try:
        text = str(value).strip()

        if "." in text:
            whole, fraction = text.split(".", 1)

            if not fraction.isdigit() or len(fraction) != 1:
                return None

            overs = int(whole or 0)
            balls = int(fraction)

            if overs < 0 or balls > 5:
                return None

            return overs * 6 + balls

        numeric = float(text)

        if not numeric.is_integer() or numeric < 0:
            return None

        return int(numeric) * 6

    except (TypeError, ValueError, OverflowError):
        return None


def _innings_list(payload: Any) -> list[dict]:
    if not isinstance(payload, dict):
        raise ScorecardImportError(
            "Scorecard response is not a JSON object."
        )

    rows = payload.get("scorecard")

    if not isinstance(rows, list) or not rows:
        raise ScorecardImportError(
            "No scorecard innings array was found. "
            "No database changes were made."
        )

    innings = [row for row in rows if isinstance(row, dict)]

    if not innings:
        raise ScorecardImportError(
            "Scorecard innings array is empty or invalid."
        )

    return innings


def _team_details(inn: dict) -> tuple[Any, str | None]:
    """Extract the batting team's external ID and name."""
    team_details = inn.get("batTeamDetails")
    if not isinstance(team_details, dict):
        team_details = {}

    team_id = _first(
        inn,
        "batTeamId",
        "battingTeamId",
        "teamId",
        "team_id",
    )

    if team_id is None:
        team_id = _first(
            team_details,
            "batTeamId",
            "teamId",
            "id",
            "team_id",
        )

    team_name = _first(
        inn,
        "batteamname",
        "batTeamName",
        "battingTeamName",
        "teamName",
        "batteamsname",
        "batTeamShortName",
        "battingTeamShortName",
    )

    if not team_name:
        team_name = _first(
            team_details,
            "batTeamName",
            "teamName",
            "teamShortName",
            "shortName",
            "name",
        )

    if isinstance(team_name, str):
        team_name = team_name.strip()

    return team_id, team_name or None


def _batters(inn: dict) -> list[dict]:
    direct = _items(
        _first(inn, "batsman", "batsmen", "batters")
    )

    if direct:
        return direct

    details = inn.get("batTeamDetails")

    if isinstance(details, dict):
        return _items(
            _first(
                details,
                "batsmenData",
                "batsmen",
                "batsman",
            )
        )

    return []


def _bowlers(inn: dict) -> list[dict]:
    direct = _items(
        _first(inn, "bowler", "bowlers")
    )

    if direct:
        return direct

    details = inn.get("bowlTeamDetails")

    if isinstance(details, dict):
        return _items(
            _first(
                details,
                "bowlersData",
                "bowlers",
                "bowler",
            )
        )

    return []


def _innings_totals(
    inn: dict,
) -> tuple[int | None, int | None, int | None, bool]:
    score_obj = inn.get("scoreDetails")

    if not isinstance(score_obj, dict):
        score_obj = {}

    total = _as_int(
        _first(
            inn,
            "totalRuns",
            "totalruns",
            "runs",
            "score",
        )
    )

    if total is None:
        total = _as_int(
            _first(
                score_obj,
                "runs",
                "totalRuns",
                "score",
            )
        )

    wickets = _as_int(
        _first(
            inn,
            "wickets",
            "wicketsLost",
            "wickets_lost",
        )
    )

    if wickets is None:
        wickets = _as_int(
            _first(
                score_obj,
                "wickets",
                "wicketsLost",
            )
        )

    overs = _first(
        inn,
        "overs",
        "oversBowled",
        "over",
    )

    if overs is None:
        overs = _first(
            score_obj,
            "overs",
            "oversBowled",
        )

    balls = _overs_to_balls(overs)

    completed_value = _first(
        inn,
        "isCompleted",
        "is_completed",
    )

    if isinstance(completed_value, bool):
        completed = completed_value
    else:
        completed = total is not None and wickets is not None

    return total, wickets, balls, completed


def _resolve_team(
    cur,
    match_id: int,
    external_team_id: Any,
    team_name: str | None,
) -> int:
    """Resolve a Cricbuzz team and verify it belongs to the match."""
    team_id = None

    if external_team_id is not None:
        cur.execute(
            """
            SELECT team_id
            FROM teams
            WHERE external_id = %s
            LIMIT 1
            """,
            (str(external_team_id),),
        )

        row = cur.fetchone()

        if row:
            team_id = row[0]

    if team_id is None and team_name:
        cur.execute(
            """
            SELECT team_id
            FROM teams
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))
            ORDER BY team_id
            LIMIT 1
            """,
            (team_name,),
        )

        row = cur.fetchone()

        if row:
            team_id = row[0]

    if team_id is None:
        raise ScorecardImportError(
            "Could not map batting team "
            f"'{team_name or external_team_id}' to a local team."
        )

    cur.execute(
        """
        SELECT 1
        FROM match_teams
        WHERE match_id = %s
          AND team_id = %s
        """,
        (match_id, team_id),
    )

    if cur.fetchone() is None:
        raise ScorecardImportError(
            f"Resolved team_id={team_id} is not linked to "
            f"local match_id={match_id}. Refresh match metadata "
            "synchronization before importing this scorecard."
        )

    return int(team_id)


def _resolve_player(cur, player: dict) -> int:
    """Find or create a player using their external ID or name."""
    name = _first(
        player,
        "name",
        "fullName",
        "playerName",
        "nickName",
        "nickname",
        "batName",
        "bowlName",
    )

    external_id = _first(
        player,
        "id",
        "playerId",
        "externalId",
        "external_id",
    )

    name = str(name).strip() if name is not None else ""

    if not name:
        raise ScorecardImportError(
            "A scorecard player entry is missing a player name."
        )

    external_text = (
        str(external_id)
        if external_id not in (None, "", 0, "0")
        else None
    )

    if external_text:
        cur.execute(
            """
            SELECT player_id
            FROM players
            WHERE external_id = %s
            LIMIT 1
            """,
            (external_text,),
        )

        row = cur.fetchone()

        if row:
            cur.execute(
                """
                UPDATE players
                SET full_name = %s
                WHERE player_id = %s
                """,
                (name, row[0]),
            )

            return int(row[0])

    cur.execute(
        """
        SELECT player_id
        FROM players
        WHERE LOWER(TRIM(full_name)) = LOWER(TRIM(%s))
        ORDER BY player_id
        LIMIT 1
        """,
        (name,),
    )

    row = cur.fetchone()

    if row:
        if external_text:
            cur.execute(
                """
                UPDATE players
                SET external_id = %s
                WHERE player_id = %s
                  AND external_id IS NULL
                """,
                (external_text, row[0]),
            )

        return int(row[0])

    cur.execute(
        """
        INSERT INTO players (full_name, external_id)
        VALUES (%s, %s)
        RETURNING player_id
        """,
        (name, external_text),
    )

    return int(cur.fetchone()[0])


def _batting_row(
    cur,
    innings_id: int,
    position: int,
    batter: dict,
) -> None:
    player_id = _resolve_player(cur, batter)

    runs = _as_int(
        _first(batter, "runs", "r"),
        0,
    )
    balls = _as_int(
        _first(batter, "balls", "ballsFaced", "bf"),
        0,
    )
    fours = _as_int(
        _first(batter, "fours", "4s"),
        0,
    )
    sixes = _as_int(
        _first(batter, "sixes", "6s"),
        0,
    )

    dismissal = _first(
        batter,
        "out",
        "outDesc",
        "dismissal",
        "dismissalKind",
    )

    dismissal_text = str(dismissal).strip() if dismissal else None
    is_out = _as_bool_out(dismissal)

    cur.execute(
        """
        INSERT INTO batting_stats
        (
            innings_id,
            player_id,
            batting_position,
            runs,
            balls_faced,
            fours,
            sixes,
            dismissal_kind,
            is_out
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (innings_id, player_id) DO UPDATE SET
            batting_position = EXCLUDED.batting_position,
            runs = EXCLUDED.runs,
            balls_faced = EXCLUDED.balls_faced,
            fours = EXCLUDED.fours,
            sixes = EXCLUDED.sixes,
            dismissal_kind = EXCLUDED.dismissal_kind,
            is_out = EXCLUDED.is_out
        """,
        (
            innings_id,
            player_id,
            position,
            runs,
            balls,
            fours,
            sixes,
            dismissal_text[:50] if dismissal_text else None,
            is_out,
        ),
    )


def _bowling_row(
    cur,
    innings_id: int,
    bowler: dict,
) -> None:
    player_id = _resolve_player(cur, bowler)

    overs = _first(
        bowler,
        "overs",
        "oversBowled",
        "o",
    )

    balls = _as_int(
        _first(
            bowler,
            "legalBalls",
            "balls",
            "legal_balls",
        )
    )

    if balls is None:
        balls = _overs_to_balls(overs)

    if balls is None:
        balls = 0

    runs = _as_int(
        _first(
            bowler,
            "runs",
            "runsConceded",
            "conceded",
            "r",
        ),
        0,
    )

    wickets = _as_int(
        _first(
            bowler,
            "wickets",
            "wkts",
            "w",
        ),
        0,
    )

    maidens = _as_int(
        _first(
            bowler,
            "maidens",
            "maidenOvers",
            "m",
        ),
        0,
    )

    cur.execute(
        """
        INSERT INTO bowling_stats
        (
            innings_id,
            player_id,
            legal_balls,
            runs_conceded,
            wickets,
            maidens
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (innings_id, player_id) DO UPDATE SET
            legal_balls = EXCLUDED.legal_balls,
            runs_conceded = EXCLUDED.runs_conceded,
            wickets = EXCLUDED.wickets,
            maidens = EXCLUDED.maidens
        """,
        (
            innings_id,
            player_id,
            balls,
            runs,
            wickets,
            maidens,
        ),
    )


def _normalize_name(value: str) -> str:
    """Normalize case and whitespace for conservative name matching."""
    return " ".join(value.casefold().split())


def _parse_match_result(status: Any) -> dict | None:
    """Parse common Cricbuzz match-result messages conservatively.

    Supported examples:
    - Team A won by 15 runs
    - Team A won by 5 wickets
    - Team A won by an innings and 36 runs

    Ties, draws, no-results, live statuses, and unsupported wording are
    ignored so existing result fields are not overwritten with guesses.
    """
    if not isinstance(status, str):
        return None

    text = " ".join(status.strip().split())
    if not text:
        return None

    # Test the innings result first; it contains the word "runs" but its
    # margin is specifically the number of runs in addition to an innings.
    innings_match = re.search(
        r"^(?P<winner>.+?)\s+won\s+by\s+an?\s+innings?\s+and\s+"
        r"(?P<margin>\d+)\s+runs?\b",
        text,
        flags=re.IGNORECASE,
    )

    if innings_match:
        winner_name = innings_match.group("winner").strip()
        margin = int(innings_match.group("margin"))
        if winner_name and margin >= 0:
            return {
                "winner_name": winner_name,
                "result_type": "innings",
                "result_margin": margin,
                "status_text": text,
            }
        return None

    regular_match = re.search(
        r"^(?P<winner>.+?)\s+won\s+by\s+"
        r"(?P<margin>\d+)\s+"
        r"(?P<kind>runs?|wickets?)\b",
        text,
        flags=re.IGNORECASE,
    )

    if not regular_match:
        return None

    winner_name = regular_match.group("winner").strip()
    margin = int(regular_match.group("margin"))
    kind = regular_match.group("kind").lower()
    result_type = "runs" if kind.startswith("run") else "wickets"

    if not winner_name or margin < 0:
        return None

    return {
        "winner_name": winner_name,
        "result_type": result_type,
        "result_margin": margin,
        "status_text": text,
    }


def _update_match_result(
    cur,
    local_match_id: int,
    status: Any,
    warnings: list[str],
) -> dict | None:
    """Save a result only when the winner matches a linked local team."""
    parsed = _parse_match_result(status)

    if parsed is None:
        if status:
            warnings.append(
                "Match result was not recognized; existing result fields "
                "were left unchanged. Cricbuzz status: "
                f"{str(status)[:200]}"
            )

        return None

    cur.execute(
        """
        SELECT t.team_id, t.name
        FROM match_teams AS mt
        JOIN teams AS t
          ON t.team_id = mt.team_id
        WHERE mt.match_id = %s
        """,
        (local_match_id,),
    )

    linked_teams = cur.fetchall()
    wanted_name = _normalize_name(parsed["winner_name"])

    matches = [
        (int(team_id), team_name)
        for team_id, team_name in linked_teams
        if isinstance(team_name, str)
        and _normalize_name(team_name) == wanted_name
    ]

    if len(matches) != 1:
        warnings.append(
            f"Could not uniquely match Cricbuzz winner "
            f"'{parsed['winner_name']}' to a team linked to "
            f"local match_id={local_match_id}. Existing result fields "
            "were left unchanged."
        )

        return None

    winner_team_id, winner_name = matches[0]

    cur.execute(
        """
        UPDATE matches
        SET winner_team_id = %s,
            result_type = %s,
            result_margin = %s
        WHERE match_id = %s
        """,
        (
            winner_team_id,
            parsed["result_type"],
            parsed["result_margin"],
            local_match_id,
        ),
    )

    return {
        "winner_team_id": winner_team_id,
        "winner_team": winner_name,
        "result_type": parsed["result_type"],
        "result_margin": parsed["result_margin"],
        "source_status": parsed["status_text"],
    }


def import_scorecard(
    external_match_id: int,
    dry_run: bool = True,
) -> dict:
    """Import a scorecard for a match already in the local matches table."""
    external_id = str(int(external_match_id))

    payload = get_match_scorecard(int(external_match_id))
    innings_rows = _innings_list(payload)
    match_result = payload.get("status")

    summary = {
        "external_match_id": external_id,
        "mode": "dry_run" if dry_run else "sync",
        "database_changed": False,
        "innings_seen": len(innings_rows),
        "innings_processed": 0,
        "batters_processed": 0,
        "bowlers_processed": 0,
        "warnings": [],
        "innings_preview": [],
        "match_result": match_result,
        "result_update_preview": None,
    }

    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT match_id
                    FROM matches
                    WHERE external_id = %s
                    LIMIT 1
                    """,
                    (external_id,),
                )

                match_row = cur.fetchone()

                if not match_row:
                    raise ScorecardImportError(
                        f"External match ID {external_id} is not in "
                        "matches.external_id. Run the existing live-match "
                        "metadata sync first; no match is created here."
                    )

                local_match_id = int(match_row[0])
                summary["local_match_id"] = local_match_id

                result_preview = _update_match_result(
                    cur,
                    local_match_id,
                    match_result,
                    summary["warnings"],
                )

                summary["result_update_preview"] = result_preview

                for index, inn in enumerate(innings_rows, start=1):
                    team_ext_id, team_name = _team_details(inn)

                    local_team_id = _resolve_team(
                        cur,
                        local_match_id,
                        team_ext_id,
                        team_name,
                    )

                    innings_number = _as_int(
                        _first(
                            inn,
                            "inningsNumber",
                            "innings_number",
                            "inningsNo",
                        ),
                        index,
                    )

                    if not innings_number or innings_number < 1:
                        raise ScorecardImportError(
                            f"Invalid innings number in scorecard item {index}."
                        )

                    total, wickets, balls, completed = _innings_totals(inn)

                    cur.execute(
                        """
                        INSERT INTO innings
                        (
                            match_id,
                            innings_number,
                            batting_team_id,
                            total_runs,
                            wickets_lost,
                            legal_balls,
                            is_completed
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (match_id, innings_number) DO UPDATE SET
                            batting_team_id = EXCLUDED.batting_team_id,
                            total_runs = EXCLUDED.total_runs,
                            wickets_lost = EXCLUDED.wickets_lost,
                            legal_balls = EXCLUDED.legal_balls,
                            is_completed = EXCLUDED.is_completed
                        RETURNING innings_id
                        """,
                        (
                            local_match_id,
                            innings_number,
                            local_team_id,
                            total,
                            wickets,
                            balls,
                            completed,
                        ),
                    )

                    local_innings_id = int(cur.fetchone()[0])

                    batters = _batters(inn)
                    bowlers = _bowlers(inn)

                    for position, batter in enumerate(batters, start=1):
                        _batting_row(
                            cur,
                            local_innings_id,
                            position,
                            batter,
                        )

                    for bowler in bowlers:
                        _bowling_row(
                            cur,
                            local_innings_id,
                            bowler,
                        )

                    summary["innings_processed"] += 1
                    summary["batters_processed"] += len(batters)
                    summary["bowlers_processed"] += len(bowlers)

                    summary["innings_preview"].append(
                        {
                            "innings_number": innings_number,
                            "batting_team": team_name,
                            "batters": len(batters),
                            "bowlers": len(bowlers),
                            "total_runs": total,
                            "wickets_lost": wickets,
                            "legal_balls": balls,
                        }
                    )

                    if not batters:
                        summary["warnings"].append(
                            f"Innings {innings_number}: "
                            "no recognized batter list."
                        )

                    if not bowlers:
                        summary["warnings"].append(
                            f"Innings {innings_number}: "
                            "no recognized bowler list."
                        )

            if dry_run:
                conn.rollback()
                summary["message"] = (
                    "Preview completed. All database writes were rolled "
                    "back; no records changed."
                )
                summary["database_changed"] = False
            else:
                conn.commit()
                summary["message"] = (
                    "Scorecard import committed successfully."
                )
                summary["database_changed"] = True

        except Exception:
            conn.rollback()
            raise

    return summary