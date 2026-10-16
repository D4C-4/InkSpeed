import os
from pathlib import Path

import mysql.connector


DB_NAME = os.getenv("MYSQL_DATABASE", "inkspeed_db")


def connect_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=DB_NAME,
    )


def initialize_database():
    """Create the application database and tables if they do not exist."""
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
    )
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            CREATE DATABASE IF NOT EXISTS `{DB_NAME}`
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
            """
        )
        cursor.execute(f"USE `{DB_NAME}`")
        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        for statement in schema.split(";"):
            statement = statement.strip()
            if statement and not statement.upper().startswith(("CREATE DATABASE", "USE ")):
                cursor.execute(statement)
        migrations = {
            "challenges": {
                "category": "VARCHAR(100) NOT NULL DEFAULT 'General'",
                "text": "TEXT NULL",
                "passage_text": "TEXT NULL",
                "is_active": "TINYINT(1) NOT NULL DEFAULT 1",
                "created_at": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            },
            "results": {
                "mode": "ENUM('classic', 'memory', 'chaos') NOT NULL DEFAULT 'classic'",
                "rounds": "INT NOT NULL DEFAULT 0",
                "created_at": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
            },
            "round_results": {
                "accuracy": "DECIMAL(5, 1) NOT NULL DEFAULT 0",
            },
            "achievements": {
                "code": "VARCHAR(50) NULL",
            },
            "user_achievements": {
                "result_id": "INT NULL",
            },
        }
        for table, columns in migrations.items():
            for column, definition in columns.items():
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s AND column_name = %s
                    """,
                    (DB_NAME, table, column),
                )
                if cursor.fetchone()[0] == 0:
                    cursor.execute(
                        f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}"
                    )
        cursor.execute(
            """
            UPDATE challenges
            SET text = COALESCE(text, passage_text),
                passage_text = COALESCE(passage_text, text),
                category = COALESCE(category, 'General')
            WHERE text IS NULL
            """
        )
        cursor.execute(
            """
            UPDATE achievements
            SET code = LOWER(REPLACE(name, ' ', '_'))
            WHERE code IS NULL
            """
        )
        cursor.execute(
            """
            DELETE duplicate
            FROM achievements AS duplicate
            INNER JOIN achievements AS original
                ON original.code = duplicate.code
               AND original.achievement_id < duplicate.achievement_id
            """
        )
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = %s AND table_name = 'achievements'
              AND index_name = 'uq_achievements_code'
            """,
            (DB_NAME,),
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "ALTER TABLE achievements ADD UNIQUE KEY uq_achievements_code (code)"
            )
        _ensure_project_extensions(cursor)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """,
        (DB_NAME, table),
    )
    return cursor.fetchone()[0] == 1


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """,
        (DB_NAME, table, column),
    )
    return cursor.fetchone()[0] == 1


def _index_exists(cursor, table: str, index: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.statistics
        WHERE table_schema = %s AND table_name = %s AND index_name = %s
        """,
        (DB_NAME, table, index),
    )
    return cursor.fetchone()[0] > 0


def _foreign_key_exists(cursor, table: str, column: str, referenced_table: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.key_column_usage
        WHERE constraint_schema = %s AND table_name = %s
          AND column_name = %s AND referenced_table_name = %s
        """,
        (DB_NAME, table, column, referenced_table),
    )
    return cursor.fetchone()[0] > 0


def _ensure_project_extensions(cursor) -> None:
    """Apply additive lookup/security schema changes to fresh and existing databases."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS challenge_categories (
            category_id INT NOT NULL AUTO_INCREMENT,
            category_name VARCHAR(100) NOT NULL,
            parent_category_id INT NULL,
            PRIMARY KEY (category_id),
            UNIQUE KEY uq_challenge_categories_name (category_name),
            KEY idx_challenge_categories_parent (parent_category_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS game_modes (
            mode_id INT NOT NULL AUTO_INCREMENT,
            mode_name VARCHAR(50) NOT NULL,
            description VARCHAR(255) NULL,
            PRIMARY KEY (mode_id),
            UNIQUE KEY uq_game_modes_name (mode_name)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_roles (
            role_id INT NOT NULL AUTO_INCREMENT,
            user_id INT NULL,
            role_name VARCHAR(20) NOT NULL,
            PRIMARY KEY (role_id),
            UNIQUE KEY uq_user_roles_name (role_name)
        )
        """
    )
    if _column_exists(cursor, "user_roles", "user_id"):
        cursor.execute("ALTER TABLE user_roles MODIFY user_id INT NULL")
    if _column_exists(cursor, "user_roles", "role_name"):
        cursor.execute("ALTER TABLE user_roles MODIFY role_name VARCHAR(20) NOT NULL")
    cursor.execute(
        """
        UPDATE users u
        INNER JOIN user_roles duplicate ON duplicate.role_id = u.role_id
        INNER JOIN (
            SELECT role_name, MIN(role_id) AS role_id
            FROM user_roles GROUP BY role_name
        ) keep_role ON keep_role.role_name = duplicate.role_name
        SET u.role_id = keep_role.role_id
        """
    )
    cursor.execute(
        """
        DELETE duplicate
        FROM user_roles duplicate
        INNER JOIN user_roles original
            ON original.role_name = duplicate.role_name
           AND original.role_id < duplicate.role_id
        """
    )
    if not _index_exists(cursor, "user_roles", "uq_user_roles_name"):
        cursor.execute("ALTER TABLE user_roles ADD UNIQUE KEY uq_user_roles_name (role_name)")
    cursor.execute(
        """
        UPDATE results r
        INNER JOIN game_modes duplicate ON duplicate.mode_id = r.mode_id
        INNER JOIN (
            SELECT mode_name, MIN(mode_id) AS mode_id
            FROM game_modes GROUP BY mode_name
        ) keep_mode ON keep_mode.mode_name = duplicate.mode_name
        SET r.mode_id = keep_mode.mode_id
        """
    )
    cursor.execute(
        """
        DELETE duplicate
        FROM game_modes duplicate
        INNER JOIN game_modes original
            ON original.mode_name = duplicate.mode_name
           AND original.mode_id < duplicate.mode_id
        """
    )
    if not _index_exists(cursor, "game_modes", "uq_game_modes_name"):
        cursor.execute("ALTER TABLE game_modes ADD UNIQUE KEY uq_game_modes_name (mode_name)")
    for table, column, definition in (
        ("users", "password_hash", "VARCHAR(255) NULL"),
        ("users", "role_id", "INT NULL"),
        ("challenges", "category_id", "INT NULL"),
        ("results", "mode_id", "INT NULL"),
    ):
        if not _column_exists(cursor, table, column):
            cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS personal_bests (
            best_id INT NOT NULL AUTO_INCREMENT,
            user_id INT NOT NULL,
            mode_id INT NOT NULL,
            best_score DECIMAL(8, 2) NOT NULL DEFAULT 0,
            result_id INT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (best_id),
            UNIQUE KEY uq_personal_bests_user_mode (user_id, mode_id)
        )
        """
    )
    cursor.execute(
        """
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
        )
        """
    )
    if not _index_exists(cursor, "personal_bests", "uq_personal_bests_user_mode"):
        cursor.execute(
            "ALTER TABLE personal_bests ADD UNIQUE KEY uq_personal_bests_user_mode (user_id, mode_id)"
        )
    if not _index_exists(cursor, "personal_bests", "idx_personal_bests_mode_score"):
        cursor.execute(
            "ALTER TABLE personal_bests ADD INDEX idx_personal_bests_mode_score (mode_id, best_score)"
        )
    cursor.execute(
        """
        INSERT IGNORE INTO game_modes (mode_name, description) VALUES
        ('Classic', 'A standard timed typing test.'),
        ('Memory Rush', 'Memorize passages and type them without seeing them.'),
        ('Key Chaos', 'Type passages through scrambled letter keys.')
        """
    )
    cursor.execute(
        "INSERT IGNORE INTO user_roles (user_id, role_name) VALUES (NULL, 'Admin'), (NULL, 'Player'), (NULL, 'Viewer')"
    )
    cursor.execute(
        """
        INSERT IGNORE INTO challenge_categories (category_name)
        SELECT DISTINCT category FROM challenges
        WHERE category IS NOT NULL AND TRIM(category) <> ''
        """
    )
    cursor.execute(
        """
        UPDATE challenges c
        INNER JOIN challenge_categories cc ON cc.category_name = c.category
        SET c.category_id = cc.category_id
        WHERE c.category_id IS NULL
        """
    )
    cursor.execute(
        """
        UPDATE results r
        INNER JOIN game_modes gm ON gm.mode_name = CASE r.mode
            WHEN 'classic' THEN 'Classic'
            WHEN 'memory' THEN 'Memory Rush'
            WHEN 'chaos' THEN 'Key Chaos'
        END
        SET r.mode_id = gm.mode_id
        WHERE r.mode_id IS NULL
        """
    )
    cursor.execute(
        "UPDATE users u INNER JOIN user_roles ur ON ur.role_name = 'Player' SET u.role_id = ur.role_id WHERE u.role_id IS NULL"
    )
    for table, index, statement in (
        ("users", "idx_users_role", "ALTER TABLE users ADD INDEX idx_users_role (role_id)"),
        ("challenges", "idx_challenges_category", "ALTER TABLE challenges ADD INDEX idx_challenges_category (category_id)"),
        ("results", "idx_results_mode_id_score", "ALTER TABLE results ADD INDEX idx_results_mode_id_score (mode_id, score)"),
    ):
        if not _index_exists(cursor, table, index):
            cursor.execute(statement)
    for table, column, referenced, constraint, action in (
        ("users", "role_id", "user_roles", "fk_users_role", "ON DELETE RESTRICT"),
        ("challenges", "category_id", "challenge_categories", "fk_challenges_category", "ON DELETE RESTRICT"),
        ("results", "mode_id", "game_modes", "fk_results_mode_lookup", "ON DELETE RESTRICT"),
    ):
        if not _foreign_key_exists(cursor, table, column, referenced):
            cursor.execute(
                f"ALTER TABLE `{table}` ADD CONSTRAINT `{constraint}` "
                f"FOREIGN KEY (`{column}`) REFERENCES `{referenced}`(`{column.replace('_id', '_id')}`) {action}"
            )
    if _column_exists(cursor, "users", "role_id"):
        cursor.execute("ALTER TABLE users MODIFY role_id INT NOT NULL")
    if _column_exists(cursor, "challenges", "category_id"):
        cursor.execute("ALTER TABLE challenges MODIFY category_id INT NOT NULL")
    if _column_exists(cursor, "results", "mode_id"):
        cursor.execute("ALTER TABLE results MODIFY mode_id INT NOT NULL")
