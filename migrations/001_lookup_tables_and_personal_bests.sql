USE inkspeed_db;

CREATE TABLE IF NOT EXISTS challenge_categories (
    category_id INT NOT NULL AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL,
    parent_category_id INT NULL,
    PRIMARY KEY (category_id),
    UNIQUE KEY uq_challenge_categories_name (category_name),
    KEY idx_challenge_categories_parent (parent_category_id)
);

CREATE TABLE IF NOT EXISTS game_modes (
    mode_id INT NOT NULL AUTO_INCREMENT,
    mode_name VARCHAR(50) NOT NULL,
    description VARCHAR(255) NULL,
    PRIMARY KEY (mode_id),
    UNIQUE KEY uq_game_modes_name (mode_name)
);

CREATE TABLE IF NOT EXISTS user_roles (
    role_id INT NOT NULL AUTO_INCREMENT,
    user_id INT NULL,
    role_name VARCHAR(20) NOT NULL,
    PRIMARY KEY (role_id),
    UNIQUE KEY uq_user_roles_name (role_name)
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INT NULL;
ALTER TABLE challenges ADD COLUMN IF NOT EXISTS category_id INT NULL;
ALTER TABLE results ADD COLUMN IF NOT EXISTS mode_id INT NULL;

ALTER TABLE user_roles MODIFY user_id INT NULL;
ALTER TABLE user_roles MODIFY role_name VARCHAR(20) NOT NULL;

CREATE TABLE IF NOT EXISTS personal_bests (
    best_id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    mode_id INT NOT NULL,
    best_score DECIMAL(8, 2) NOT NULL DEFAULT 0,
    result_id INT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (best_id),
    UNIQUE KEY uq_personal_bests_user_mode (user_id, mode_id),
    KEY idx_personal_bests_mode_score (mode_id, best_score),
    CONSTRAINT fk_personal_bests_user
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_personal_bests_mode
        FOREIGN KEY (mode_id) REFERENCES game_modes (mode_id) ON DELETE CASCADE,
    CONSTRAINT fk_personal_bests_result
        FOREIGN KEY (result_id) REFERENCES results (result_id) ON DELETE SET NULL
);

INSERT IGNORE INTO game_modes (mode_name, description) VALUES
    ('Classic', 'A standard timed typing test.'),
    ('Memory Rush', 'Memorize passages and type them without seeing them.'),
    ('Key Chaos', 'Type passages through scrambled letter keys.');

INSERT IGNORE INTO user_roles (user_id, role_name) VALUES
    (NULL, 'Admin'),
    (NULL, 'Player'),
    (NULL, 'Viewer');

INSERT IGNORE INTO challenge_categories (category_name)
SELECT DISTINCT category
FROM challenges
WHERE category IS NOT NULL AND TRIM(category) <> '';

UPDATE challenges c
INNER JOIN challenge_categories cc ON cc.category_name = c.category
SET c.category_id = cc.category_id
WHERE c.category_id IS NULL;

UPDATE results r
INNER JOIN game_modes gm
    ON gm.mode_name = CASE r.mode
        WHEN 'classic' THEN 'Classic'
        WHEN 'memory' THEN 'Memory Rush'
        WHEN 'chaos' THEN 'Key Chaos'
    END
SET r.mode_id = gm.mode_id
WHERE r.mode_id IS NULL;

UPDATE users u
INNER JOIN user_roles ur ON ur.role_name = 'Player'
SET u.role_id = ur.role_id
WHERE u.role_id IS NULL;

ALTER TABLE users ADD INDEX IF NOT EXISTS idx_users_role (role_id);
ALTER TABLE challenges ADD INDEX IF NOT EXISTS idx_challenges_category (category_id);
ALTER TABLE results ADD INDEX IF NOT EXISTS idx_results_mode_id_score (mode_id, score);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id BIGINT NOT NULL AUTO_INCREMENT,
    actor_user_id INT NULL,
    action_name VARCHAR(50) NOT NULL,
    entity_name VARCHAR(50) NOT NULL,
    entity_id INT NULL,
    details JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (audit_id),
    KEY idx_audit_actor_time (actor_user_id, created_at)
);
