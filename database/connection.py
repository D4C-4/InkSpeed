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
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = %s AND table_name = 'users'
              AND column_name = 'role_id'
            """,
            (DB_NAME,),
        )
        has_role_column = cursor.fetchone()[0] == 1
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = %s AND table_name = 'user_roles'
            """,
            (DB_NAME,),
        )
        has_role_table = cursor.fetchone()[0] == 1
        if has_role_column and has_role_table:
            cursor.execute(
                "SELECT COUNT(*) FROM user_roles WHERE role_id = 2"
            )
            if cursor.fetchone()[0] == 1:
                cursor.execute(
                    """
                    ALTER TABLE users
                    MODIFY COLUMN role_id INT NOT NULL DEFAULT 2
                    """
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
        conn.commit()
    finally:
        cursor.close()
        conn.close()
