
-- 1. Check row counts
SELECT 'formats' AS table_name, COUNT(*) AS total FROM formats
UNION ALL
SELECT 'series', COUNT(*) FROM series
UNION ALL
SELECT 'teams', COUNT(*) FROM teams
UNION ALL
SELECT 'venues', COUNT(*) FROM venues
UNION ALL
SELECT 'matches', COUNT(*) FROM matches
UNION ALL
SELECT 'match_teams', COUNT(*) FROM match_teams;

-- 2. Check for duplicate external match IDs
SELECT external_id, COUNT(*) AS duplicate_count
FROM matches
WHERE external_id IS NOT NULL
GROUP BY external_id
HAVING COUNT(*) > 1;

-- 3. Check for matches missing team links
SELECT m.match_id, m.external_id, m.description
FROM matches AS m
LEFT JOIN match_teams AS mt
    ON mt.match_id = m.match_id
WHERE m.external_id IS NOT NULL
GROUP BY m.match_id, m.external_id, m.description
HAVING COUNT(mt.team_id) < 2;

-- 4. Confirm the demo match still exists
SELECT
    match_id,
    external_id,
    description,
    status
FROM matches
WHERE match_id = 1;

-- 5. Inspect synchronized matches
SELECT
    m.match_id,
    m.external_id,
    m.description,
    m.status,
    f.code AS format,
    s.name AS series
FROM matches AS m
LEFT JOIN formats AS f
    ON f.format_id = m.format_id
LEFT JOIN series AS s
    ON s.series_id = m.series_id
WHERE m.external_id IS NOT NULL
ORDER BY m.match_id;
