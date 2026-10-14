CREATE DATABASE IF NOT EXISTS inkspeed_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE inkspeed_db;

CREATE TABLE IF NOT EXISTS users (
    user_id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_users_username (username)
);

CREATE TABLE IF NOT EXISTS challenges (
    challenge_id INT NOT NULL AUTO_INCREMENT,
    category VARCHAR(100) NOT NULL,
    difficulty ENUM('easy', 'medium', 'hard') NOT NULL,
    text TEXT NOT NULL,
    passage_text TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (challenge_id),
    KEY idx_challenges_selection (is_active, difficulty)
);

CREATE TABLE IF NOT EXISTS results (
    result_id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    mode ENUM('classic', 'memory', 'chaos') NOT NULL,
    wpm DECIMAL(6, 1) NOT NULL DEFAULT 0,
    accuracy DECIMAL(5, 1) NOT NULL DEFAULT 0,
    errors INT NOT NULL DEFAULT 0,
    score DECIMAL(8, 1) NOT NULL DEFAULT 0,
    duration_seconds INT NOT NULL DEFAULT 0,
    rounds INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (result_id),
    CONSTRAINT fk_results_user
        FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON DELETE CASCADE,
    KEY idx_results_user_mode (user_id, mode, created_at),
    KEY idx_results_mode_score (mode, score)
);

CREATE TABLE IF NOT EXISTS round_results (
    round_result_id INT NOT NULL AUTO_INCREMENT,
    result_id INT NOT NULL,
    round_number INT NOT NULL,
    challenge_id INT NOT NULL,
    accuracy DECIMAL(5, 1) NOT NULL DEFAULT 0,
    passed TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (round_result_id),
    UNIQUE KEY uq_round_results_number (result_id, round_number),
    CONSTRAINT fk_round_results_result
        FOREIGN KEY (result_id) REFERENCES results (result_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_round_results_challenge
        FOREIGN KEY (challenge_id) REFERENCES challenges (challenge_id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS achievements (
    achievement_id INT NOT NULL AUTO_INCREMENT,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255) NOT NULL,
    PRIMARY KEY (achievement_id),
    UNIQUE KEY uq_achievements_code (code)
);

CREATE TABLE IF NOT EXISTS user_achievements (
    user_achievement_id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    achievement_id INT NOT NULL,
    result_id INT NULL,
    unlocked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_achievement_id),
    UNIQUE KEY uq_user_achievements (user_id, achievement_id),
    CONSTRAINT fk_user_achievements_user
        FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_achievements_achievement
        FOREIGN KEY (achievement_id) REFERENCES achievements (achievement_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_achievements_result
        FOREIGN KEY (result_id) REFERENCES results (result_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key VARCHAR(50) NOT NULL,
    setting_value VARCHAR(255) NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (setting_key)
);