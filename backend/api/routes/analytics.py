from fastapi import APIRouter, Depends, HTTPException
from backend.database.connection import get_connection
from backend.api.dependencies import get_current_user

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


def execute_query(query: str, params: tuple = ()):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                columns = [description.name for description in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]

    except Exception as error:
        print("Analytics database error:", repr(error), flush=True)
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve analytics data. Check backend logs.",
        ) from error


@router.get("/batting-leaderboard")
def get_batting_leaderboard(
    current_user: dict = Depends(get_current_user),
):
    return execute_query("""
        SELECT
            player_id,
            player_name,
            innings_played,
            total_runs,
            total_balls,
            total_fours,
            total_sixes
        FROM v_batting_leaderboard
        WHERE innings_played > 0 AND player_name NOT ILIKE %s
        ORDER BY total_runs DESC, player_name ASC;
    """, ("Demo%",))


@router.get("/bowling-leaderboard")
def get_bowling_leaderboard(
    current_user: dict = Depends(get_current_user),
):
    return execute_query("""
        SELECT
            player_id,
            player_name,
            innings_bowled,
            total_wickets,
            runs_conceded,
            legal_balls_bowled,
            total_maidens
        FROM v_bowling_leaderboard
        WHERE innings_bowled > 0 AND player_name NOT ILIKE %s
        ORDER BY total_wickets DESC, player_name ASC;
    """, ("Demo%",))



@router.get("/match-summary")
def get_match_summary():
    return execute_query("""
        SELECT
            m.match_id,
            m.external_id AS external_match_id,
            m.description,
            m.status,
            m.start_time,
            s.name AS series,
            v.name AS venue,
            f.name AS format,
            t1.name AS team_1,
            t2.name AS team_2,
            winner.name AS winner
        FROM matches m
        LEFT JOIN series s
            ON s.series_id = m.series_id
        LEFT JOIN venues v
            ON v.venue_id = m.venue_id
        LEFT JOIN formats f
            ON f.format_id = m.format_id
        LEFT JOIN match_teams mt1
            ON mt1.match_id = m.match_id
           AND mt1.is_home = TRUE
        LEFT JOIN teams t1
            ON t1.team_id = mt1.team_id
        LEFT JOIN match_teams mt2
            ON mt2.match_id = m.match_id
           AND mt2.is_home = FALSE
        LEFT JOIN teams t2
            ON t2.team_id = mt2.team_id
        LEFT JOIN teams winner
            ON winner.team_id = m.winner_team_id
        ORDER BY m.start_time DESC NULLS LAST, m.match_id DESC;
    """)


@router.get("/player-stats/{player_id}")
def get_player_stats(
    player_id: int,
    current_user: dict = Depends(get_current_user),
):
    results = execute_query("""
        SELECT
            p.player_id,
            p.full_name AS player_name,
            COALESCE(b.total_runs, 0) AS total_runs,
            COALESCE(b.total_balls, 0) AS total_balls,
            COALESCE(b.total_fours, 0) AS total_fours,
            COALESCE(b.total_sixes, 0) AS total_sixes,
            COALESCE(w.total_wickets, 0) AS total_wickets,
            COALESCE(w.runs_conceded, 0) AS runs_conceded,
            COALESCE(w.legal_balls_bowled, 0) AS legal_balls_bowled
        FROM players AS p
        LEFT JOIN (
            SELECT
                player_id,
                SUM(runs) AS total_runs,
                SUM(balls_faced) AS total_balls,
                SUM(fours) AS total_fours,
                SUM(sixes) AS total_sixes
            FROM batting_stats
            GROUP BY player_id
        ) AS b ON b.player_id = p.player_id
        LEFT JOIN (
            SELECT
                player_id,
                SUM(wickets) AS total_wickets,
                SUM(runs_conceded) AS runs_conceded,
                SUM(legal_balls) AS legal_balls_bowled
            FROM bowling_stats
            GROUP BY player_id
        ) AS w ON w.player_id = p.player_id
        WHERE p.player_id = %s;
    """, (player_id,))

    if not results:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    return results[0]


@router.get("/match-overview")
def get_match_overview(
    current_user: dict = Depends(get_current_user),
):
    return execute_query("""
        SELECT *
        FROM vw_match_overview
        ORDER BY start_time DESC NULLS LAST, match_id DESC;
    """)


@router.get("/team-match-stats")
def get_team_match_stats(
    current_user: dict = Depends(get_current_user),
):
    return execute_query("""
        SELECT
            team_id,
            team_name,
            country,
            matches_played,
            completed_matches,
            wins,
            losses
        FROM vw_team_match_stats
        ORDER BY wins DESC, matches_played DESC, team_name ASC;
    """)


@router.get("/match-status-summary")
def get_match_status_summary(
    current_user: dict = Depends(get_current_user),
):
    return execute_query("""
        SELECT
            format,
            status,
            total_matches
        FROM vw_match_status_summary
        ORDER BY format, status;
    """)
