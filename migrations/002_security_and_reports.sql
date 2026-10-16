USE inkspeed_db;

DELIMITER $$

DROP PROCEDURE IF EXISTS add_lookup_foreign_keys$$

CREATE PROCEDURE add_lookup_foreign_keys()
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.key_column_usage
        WHERE constraint_schema = DATABASE() AND table_name = 'users'
          AND column_name = 'role_id' AND referenced_table_name = 'user_roles'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT fk_users_role
            FOREIGN KEY (role_id) REFERENCES user_roles (role_id)
            ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.key_column_usage
        WHERE constraint_schema = DATABASE() AND table_name = 'challenges'
          AND column_name = 'category_id' AND referenced_table_name = 'challenge_categories'
    ) THEN
        ALTER TABLE challenges
            ADD CONSTRAINT fk_challenges_category
            FOREIGN KEY (category_id) REFERENCES challenge_categories (category_id)
            ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.key_column_usage
        WHERE constraint_schema = DATABASE() AND table_name = 'results'
          AND column_name = 'mode_id' AND referenced_table_name = 'game_modes'
    ) THEN
        ALTER TABLE results
            ADD CONSTRAINT fk_results_mode_lookup
            FOREIGN KEY (mode_id) REFERENCES game_modes (mode_id)
            ON DELETE RESTRICT;
    END IF;
END$$

CALL add_lookup_foreign_keys()$$
DROP PROCEDURE add_lookup_foreign_keys$$

DELIMITER ;

UPDATE users u
INNER JOIN user_roles ur ON ur.role_name = 'Player'
SET u.role_id = ur.role_id
WHERE u.role_id IS NULL;

ALTER TABLE users MODIFY role_id INT NOT NULL;
ALTER TABLE challenges MODIFY category_id INT NOT NULL;
ALTER TABLE results MODIFY mode_id INT NOT NULL;

CREATE OR REPLACE VIEW v_leaderboard AS
SELECT
    pb.user_id,
    u.username,
    pb.mode_id,
    gm.mode_name,
    pb.best_score,
    pb.result_id,
    pb.updated_at
FROM personal_bests pb
INNER JOIN users u ON u.user_id = pb.user_id
INNER JOIN game_modes gm ON gm.mode_id = pb.mode_id;

CREATE OR REPLACE VIEW v_user_history AS
SELECT
    r.result_id,
    r.user_id,
    u.username,
    r.mode,
    r.mode_id,
    gm.mode_name,
    r.wpm,
    r.accuracy,
    r.errors,
    r.score,
    r.duration_seconds,
    r.rounds,
    r.created_at
FROM results r
INNER JOIN users u ON u.user_id = r.user_id
INNER JOIN game_modes gm ON gm.mode_id = r.mode_id;
