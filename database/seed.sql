USE inkspeed_db;

INSERT INTO users (username)
VALUES ('demo_user')
ON DUPLICATE KEY UPDATE username = VALUES(username);

INSERT INTO achievements (code, name, description) VALUES
('first_ink', 'First Ink', 'Save your first result.'),
('wpm_40', 'Quick Quill', 'Reach 40 WPM in Classic.'),
('wpm_70', 'Speed Scribe', 'Reach 70 WPM in Classic.'),
('flawless', 'Flawless', 'Finish with 100% accuracy.'),
('memory_3', 'Steel Trap', 'Complete 3 Memory Rush rounds.'),
('chaos_tamer', 'Chaos Tamer', 'Finish Key Chaos above 80% accuracy.')
ON DUPLICATE KEY UPDATE
name = VALUES(name), description = VALUES(description);