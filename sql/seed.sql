-- Cricbuzz LiveStats development seed data.
-- IMPORTANT: these are illustrative DEMO records, not verified match results.
-- This script is safe to re-run for the records identified by their unique names.

BEGIN;

INSERT INTO teams (team_name, country)
VALUES
    ('India', 'India'),
    ('Australia', 'Australia'),
    ('England', 'England'),
    ('New Zealand', 'New Zealand'),
    ('South Africa', 'South Africa'),
    ('Pakistan', 'Pakistan')
ON CONFLICT (team_name) DO NOTHING;

INSERT INTO players (full_name, country, batting_style, bowling_style, playing_role)
VALUES
    ('Demo Batter One', 'India', 'Right-hand bat', NULL, 'Batter'),
    ('Demo Batter Two', 'Australia', 'Left-hand bat', NULL, 'Batter'),
    ('Demo All-Rounder', 'England', 'Right-hand bat', 'Right-arm medium', 'All-rounder'),
    ('Demo Bowler One', 'New Zealand', 'Right-hand bat', 'Right-arm fast', 'Bowler'),
    ('Demo Bowler Two', 'South Africa', 'Left-hand bat', 'Left-arm fast', 'Bowler'),
    ('Demo Wicketkeeper', 'Pakistan', 'Right-hand bat', NULL, 'Wicketkeeper-batter')
ON CONFLICT DO NOTHING;

INSERT INTO venues (venue_name, city, country)
VALUES
    ('Demo Cricket Ground', 'New Delhi', 'India'),
    ('Demo Oval', 'Melbourne', 'Australia')
ON CONFLICT (venue_name, city, country) DO NOTHING;

INSERT INTO series (series_name, start_date, end_date)
VALUES
    ('LiveStats Demo Series A', DATE '2026-01-01', DATE '2026-01-10'),
    ('LiveStats Demo Series B', DATE '2026-02-01', DATE '2026-02-10')
ON CONFLICT (series_name, start_date) DO NOTHING;

-- The dates and scores below are deliberately labelled as demo fixtures/data.
INSERT INTO matches (
    external_match_id, description, series_id, venue_id, format_id,
    team1_id, team2_id, status, start_time, winner_team_id
)
SELECT
    'LIVESTATS-DEMO-001',
    'DEMO: India vs Australia',
    s.series_id, v.venue_id, f.format_id,
    t1.team_id, t2.team_id,
    'Demo completed',
    TIMESTAMPTZ '2026-01-05 09:00:00+00',
    t1.team_id
FROM series s
JOIN venues v ON v.venue_name = 'Demo Cricket Ground'
JOIN match_formats f ON f.format_name = 'ODI'
JOIN teams t1 ON t1.team_name = 'India'
JOIN teams t2 ON t2.team_name = 'Australia'
WHERE s.series_name = 'LiveStats Demo Series A'
ON CONFLICT (external_match_id) DO NOTHING;

INSERT INTO matches (
    external_match_id, description, series_id, venue_id, format_id,
    team1_id, team2_id, status, start_time, winner_team_id
)
SELECT
    'LIVESTATS-DEMO-002',
    'DEMO: England vs New Zealand',
    s.series_id, v.venue_id, f.format_id,
    t1.team_id, t2.team_id,
    'Demo completed',
    TIMESTAMPTZ '2026-02-05 09:00:00+00',
    t2.team_id
FROM series s
JOIN venues v ON v.venue_name = 'Demo Oval'
JOIN match_formats f ON f.format_name = 'T20'
JOIN teams t1 ON t1.team_name = 'England'
JOIN teams t2 ON t2.team_name = 'New Zealand'
WHERE s.series_name = 'LiveStats Demo Series B'
ON CONFLICT (external_match_id) DO NOTHING;

-- Add one sample batting record per demo player per demo match.
INSERT INTO batting_stats (
    match_id, player_id, team_id, innings_number,
    runs, balls_faced, fours, sixes, is_not_out
)
SELECT m.match_id, p.player_id, t.team_id, 1,
       x.runs, x.balls, x.fours, x.sixes, x.not_out
FROM (VALUES
    ('LIVESTATS-DEMO-001', 'Demo Batter One', 'India', 84, 76, 8, 2, FALSE),
    ('LIVESTATS-DEMO-001', 'Demo Batter Two', 'Australia', 61, 55, 5, 1, TRUE),
    ('LIVESTATS-DEMO-001', 'Demo All-Rounder', 'England', 25, 19, 2, 1, FALSE),
    ('LIVESTATS-DEMO-001', 'Demo Bowler One', 'New Zealand', 8, 10, 1, 0, FALSE),
    ('LIVESTATS-DEMO-002', 'Demo All-Rounder', 'England', 42, 28, 4, 2, FALSE),
    ('LIVESTATS-DEMO-002', 'Demo Wicketkeeper', 'Pakistan', 57, 39, 6, 1, TRUE),
    ('LIVESTATS-DEMO-002', 'Demo Bowler Two', 'South Africa', 11, 8, 1, 0, FALSE)
) AS x(external_match_id, player_name, team_name, runs, balls, fours, sixes, not_out)
JOIN matches m ON m.external_match_id = x.external_match_id
JOIN players p ON p.full_name = x.player_name
JOIN teams t ON t.team_name = x.team_name
ON CONFLICT (match_id, player_id, innings_number) DO NOTHING;

INSERT INTO bowling_stats (
    match_id, player_id, team_id, innings_number,
    overs_bowled, legal_balls, runs_conceded, wickets, maidens
)
SELECT m.match_id, p.player_id, t.team_id, 1,
       x.overs, x.balls, x.runs, x.wickets, x.maidens
FROM (VALUES
    ('LIVESTATS-DEMO-001', 'Demo Bowler One', 'New Zealand', 8.0::NUMERIC, 48, 36, 3, 1),
    ('LIVESTATS-DEMO-001', 'Demo Bowler Two', 'South Africa', 7.0::NUMERIC, 42, 41, 2, 0),
    ('LIVESTATS-DEMO-002', 'Demo All-Rounder', 'England', 4.0::NUMERIC, 24, 27, 1, 0),
    ('LIVESTATS-DEMO-002', 'Demo Bowler One', 'New Zealand', 4.0::NUMERIC, 24, 22, 2, 0)
) AS x(external_match_id, player_name, team_name, overs, balls, runs, wickets, maidens)
JOIN matches m ON m.external_match_id = x.external_match_id
JOIN players p ON p.full_name = x.player_name
JOIN teams t ON t.team_name = x.team_name
ON CONFLICT (match_id, player_id, innings_number) DO NOTHING;

COMMIT;
