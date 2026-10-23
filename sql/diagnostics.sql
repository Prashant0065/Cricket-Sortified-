
-- Cricbuzz LiveStats: Read-only database diagnostics
-- These queries do not modify database records.

-- 1. Count records in the main tables.
SELECT 'matches' AS table_name, COUNT(*) AS row_count
FROM matches

UNION ALL

SELECT 'players', COUNT(*)
FROM players

UNION ALL

SELECT 'innings', COUNT(*)
FROM innings

UNION ALL

SELECT 'batting_stats', COUNT(*)
FROM batting_stats

UNION ALL

SELECT 'bowling_stats', COUNT(*)
FROM bowling_stats;

-- 2. Inspect recent matches and their recorded results.
SELECT
    match_id,
    external_id,
    description,
    status,
    winner_team_id,
    result_type,
    result_margin
FROM matches
ORDER BY start_time DESC NULLS LAST
LIMIT 20;

-- 3. Inspect innings and their associated matches.
SELECT
    i.innings_id,
    i.match_id,
    i.innings_number,
    i.batting_team_id,
    i.total_runs,
    i.wickets_lost,
    i.legal_balls,
    i.is_completed
FROM innings AS i
ORDER BY
    i.match_id,
    i.innings_number
LIMIT 50;

-- 4. Check which players have recorded batting statistics.
SELECT
    p.player_id,
    p.full_name,
    COUNT(bs.batting_stat_id) AS batting_records
FROM players AS p
LEFT JOIN batting_stats AS bs
    ON bs.player_id = p.player_id
GROUP BY
    p.player_id,
    p.full_name
ORDER BY
    batting_records DESC,
    p.full_name
LIMIT 25;
