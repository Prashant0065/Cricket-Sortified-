
CREATE OR REPLACE VIEW v_batting_leaderboard AS
SELECT
    p.player_id,
    p.full_name AS player_name,
    COUNT(DISTINCT i.innings_id)::BIGINT AS innings_played,
    COALESCE(SUM(bs.runs), 0)::BIGINT AS total_runs,
    COALESCE(SUM(bs.balls_faced), 0)::BIGINT AS total_balls,
    COALESCE(SUM(bs.fours), 0)::BIGINT AS total_fours,
    COALESCE(SUM(bs.sixes), 0)::BIGINT AS total_sixes
FROM players AS p
JOIN batting_stats AS bs
    ON bs.player_id = p.player_id
JOIN innings AS i
    ON i.innings_id = bs.innings_id
WHERE p.full_name NOT ILIKE 'Demo%'
GROUP BY p.player_id, p.full_name;

CREATE OR REPLACE VIEW v_bowling_leaderboard AS
SELECT
    p.player_id,
    p.full_name AS player_name,
    COUNT(DISTINCT i.innings_id)::BIGINT AS innings_bowled,
    COALESCE(SUM(bs.wickets), 0)::BIGINT AS total_wickets,
    COALESCE(SUM(bs.runs_conceded), 0)::BIGINT AS runs_conceded,
    COALESCE(SUM(bs.legal_balls), 0)::BIGINT AS legal_balls_bowled,
    COALESCE(SUM(bs.maidens), 0)::BIGINT AS total_maidens
FROM players AS p
JOIN bowling_stats AS bs
    ON bs.player_id = p.player_id
JOIN innings AS i
    ON i.innings_id = bs.innings_id
WHERE p.full_name NOT ILIKE 'Demo%'
GROUP BY p.player_id, p.full_name;
