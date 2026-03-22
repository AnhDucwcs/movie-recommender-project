-- Seed demo data for users/interactions
-- This file runs automatically on first Postgres initialization.

TRUNCATE TABLE interactions RESTART IDENTITY CASCADE;
TRUNCATE TABLE users RESTART IDENTITY CASCADE;

INSERT INTO users (username, created_at) VALUES
('nguyen_van_a', NOW() - INTERVAL '10 days'),
('tran_thi_b', NOW() - INTERVAL '5 days'),
('le_van_c', NOW() - INTERVAL '1 day');

INSERT INTO interactions (user_id, movie_id, interaction_type, rating_value, created_at) VALUES
(1, 2571, 'RATING', 5.0, NOW() - INTERVAL '9 days'),
(1, 260, 'LIKE', 5.0, NOW() - INTERVAL '8 days'),
(1, 1196, 'RATING', 4.5, NOW() - INTERVAL '7 days'),
(1, 1200, 'RATING', 4.0, NOW() - INTERVAL '6 days'),
(1, 356, 'RATING', 2.0, NOW() - INTERVAL '5 days'),
(2, 1721, 'LIKE', 5.0, NOW() - INTERVAL '4 days'),
(2, 1, 'RATING', 5.0, NOW() - INTERVAL '3 days'),
(2, 3114, 'RATING', 4.5, NOW() - INTERVAL '2 days'),
(2, 595, 'LIKE', 5.0, NOW() - INTERVAL '1 day');
