-- Cricbuzz LiveStats analytics views.
-- Column names match backend/api/routes/analytics.py.
-- These views summarize whatever records exist in the database.
-- Demo rows remain demo rows; live API data must be imported separately.

BEGIN;

CREATE OR REPLACE VIEW v_batting_leaderboard AS
SELECT
    p.player_id,
    p.full_name AS player_name,
    COUNT(DISTINCT (bs.match_id, bs.innings_number))::INTEGER AS innings_played,
    COALESCE(SUM(bs.runs), 0)::BIGINT AS total_runs,
    COALESCE(SUM(bs.balls_faced), 0)::BIGINT AS total_balls,
    COALESCE(SUM(bs.fours), 0)::BIGINT AS total_fours,
    COALESCE(SUM(bs.sixes), 0)::BIGINT AS total_sixes
FROM players p
LEFT JOIN batting_stats bs ON bs.player_id = p.player_id
GROUP BY p.player_id, p.full_name;

CREATE OR REPLACE VIEW v_bowling_leaderboard AS
SELECT
    p.player_id,
    p.full_name AS player_name,
    COUNT(DISTINCT (ws.match_id, ws.innings_number))::INTEGER AS innings_bowled,
    COALESCE(SUM(ws.wickets), 0)::BIGINT AS total_wickets,
    COALESCE(SUM(ws.runs_conceded), 0)::BIGINT AS runs_conceded,
    COALESCE(SUM(ws.legal_balls), 0)::BIGINT AS legal_balls_bowled,
    COALESCE(SUM(ws.maidens), 0)::BIGINT AS total_maidens
FROM players p
LEFT JOIN bowling_stats ws ON ws.player_id = p.player_id
GROUP BY p.player_id, p.full_name;

CREATE OR REPLACE VIEW v_match_summary AS
SELECT
    m.match_id,
    m.description,
    m.status,
    m.start_time,
    m.series_id,
    m.venue_id,
    m.format_id
FROM matches m;

COMMIT;
