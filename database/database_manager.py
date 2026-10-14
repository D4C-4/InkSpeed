"""MySQL repositories for users, challenges, results, and achievements."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from mysql.connector import IntegrityError

from database.connection import connect_db
from models import (
    ACHIEVEMENTS,
    Achievement,
    Challenge,
    Difficulty,
    ModeCode,
    Result,
    ResultDraft,
    RoundRecord,
    User,
    UserAchievement,
)

USERNAME_MIN, USERNAME_MAX = 4, 20
PASSAGE_MIN, PASSAGE_MAX = 10, 400
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(slots=True)
class SaveOutcome:
    result: Result
    unlocked: list[Achievement]
    is_new_best: bool


class UsernameError(ValueError):
    """A user-facing username validation error."""


def validate_username(username: str) -> str:
    cleaned = username.strip()
    if not cleaned:
        raise UsernameError("Please enter a username.")
    if len(cleaned) < USERNAME_MIN:
        raise UsernameError("Username is too short. Use at least 4 characters.")
    if len(cleaned) > USERNAME_MAX:
        raise UsernameError("Username is too long. Use 20 characters or fewer.")
    if _USERNAME_RE.fullmatch(cleaned) is None:
        raise UsernameError(
            "Use only letters, numbers, underscore (_), dot (.) or hyphen (-). No spaces."
        )
    return cleaned


def _validate_challenge(category: str, text: str) -> tuple[str, str]:
    cleaned_category, cleaned_text = category.strip(), text.strip()
    if not cleaned_category:
        raise ValueError("Category is required.")
    if not PASSAGE_MIN <= len(cleaned_text) <= PASSAGE_MAX:
        raise ValueError(
            f"Passage must be between {PASSAGE_MIN} and {PASSAGE_MAX} characters."
        )
    return cleaned_category, cleaned_text


def _user_from_row(row: dict[str, Any]) -> User:
    return User(row["user_id"], row["username"], row["created_at"])


def _challenge_from_row(row: dict[str, Any]) -> Challenge:
    return Challenge(
        row["challenge_id"],
        row["category"],
        Difficulty(row["difficulty"]),
        row["text"],
        bool(row["is_active"]),
        row.get("created_at"),
        row.get("updated_at"),
    )


def _result_from_row(
    row: dict[str, Any],
    round_details: list[RoundRecord] | None = None,
) -> Result:
    return Result(
        row["result_id"],
        row["user_id"],
        ModeCode(row["mode"]),
        float(row["wpm"]),
        float(row["accuracy"]),
        row["errors"],
        float(row["score"]),
        row["duration_seconds"],
        row["rounds"],
        row["created_at"],
        round_details or [],
    )


def add_user(username: str) -> User:
    """Create and return a user."""
    name = validate_username(username)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        try:
            cursor.execute("INSERT INTO users (username) VALUES (%s)", (name,))
        except IntegrityError as error:
            if error.errno == 1062:
                raise UsernameError(
                    f'The username "{name}" is already taken. Please choose another one.'
                ) from error
            raise
        conn.commit()
        cursor.execute(
            "SELECT user_id, username, created_at FROM users WHERE user_id = %s",
            (cursor.lastrowid,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("User was inserted but could not be reloaded.")
        return _user_from_row(row)
    finally:
        cursor.close()
        conn.close()


create_user = add_user


def get_users() -> list[User]:
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id, username, created_at FROM users ORDER BY username"
        )
        return [_user_from_row(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def get_user(user_id: int) -> User | None:
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id, username, created_at FROM users WHERE user_id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        return _user_from_row(row) if row else None
    finally:
        cursor.close()
        conn.close()


def rename_user(user_id: int, username: str) -> User:
    name = validate_username(username)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT username FROM users WHERE user_id = %s",
            (user_id,),
        )
        current = cursor.fetchone()
        if current is None:
            raise UsernameError("That user no longer exists. Please select a player again.")
        if current["username"] == name:
            raise UsernameError(
                "That is already your username. Enter a different one to rename."
            )
        cursor.execute(
            """
            SELECT user_id FROM users
            WHERE LOWER(username) = LOWER(%s) AND user_id <> %s
            """,
            (name, user_id),
        )
        if cursor.fetchone() is not None:
            raise UsernameError(
                f'The username "{name}" is already taken. Please choose another one.'
            )
        try:
            cursor.execute(
                "UPDATE users SET username = %s WHERE user_id = %s",
                (name, user_id),
            )
        except IntegrityError as error:
            if error.errno == 1062:
                raise UsernameError(
                    f'The username "{name}" is already taken. Please choose another one.'
                ) from error
            raise
        if cursor.rowcount != 1:
            raise ValueError(f"User {user_id} does not exist.")
        conn.commit()
        cursor.execute(
            "SELECT user_id, username, created_at FROM users WHERE user_id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("User was updated but could not be reloaded.")
        return _user_from_row(row)
    finally:
        cursor.close()
        conn.close()


def delete_user(user_id: int) -> None:
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            DELETE FROM user_achievements
            WHERE user_id = %s
            """,
            (user_id,),
        )
        cursor.execute(
            """
            DELETE rr FROM round_results AS rr
            INNER JOIN results AS r ON r.result_id = rr.result_id
            WHERE r.user_id = %s
            """,
            (user_id,),
        )
        cursor.execute("DELETE FROM results WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        cursor.execute(
            """
            UPDATE app_settings
            SET setting_value = NULL
            WHERE setting_key = 'current_user_id' AND setting_value = %s
            """,
            (str(user_id),),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_challenges(
    difficulty: Difficulty | None = None,
    include_inactive: bool = False,
) -> list[Challenge]:
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        clauses = []
        params: list[object] = []
        if not include_inactive:
            clauses.append("is_active = 1")
        if difficulty is not None:
            clauses.append("difficulty = %s")
            params.append(difficulty.value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cursor.execute(
            f"""
            SELECT challenge_id, category, difficulty, text, is_active,
                   created_at, updated_at
            FROM challenges
            {where}
            ORDER BY challenge_id
            """,
            tuple(params),
        )
        return [_challenge_from_row(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def add_challenge(category: str, difficulty: Difficulty, text: str) -> Challenge:
    category, text = _validate_challenge(category, text)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            INSERT INTO challenges (category, difficulty, text, passage_text)
            VALUES (%s, %s, %s, %s)
            """,
            (category, difficulty.value, text, text),
        )
        conn.commit()
        cursor.execute(
            """
            SELECT challenge_id, category, difficulty, text, is_active,
                   created_at, updated_at
            FROM challenges
            WHERE challenge_id = %s
            """,
            (cursor.lastrowid,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Challenge was inserted but could not be reloaded.")
        return _challenge_from_row(row)
    finally:
        cursor.close()
        conn.close()


def update_challenge(
    challenge_id: int,
    category: str,
    difficulty: Difficulty,
    text: str,
) -> Challenge:
    category, text = _validate_challenge(category, text)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            UPDATE challenges
            SET category = %s, difficulty = %s, text = %s, passage_text = %s
            WHERE challenge_id = %s
            """,
            (category, difficulty.value, text, text, challenge_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Challenge {challenge_id} does not exist.")
        conn.commit()
        cursor.execute(
            """
            SELECT challenge_id, category, difficulty, text, is_active,
                   created_at, updated_at
            FROM challenges
            WHERE challenge_id = %s
            """,
            (challenge_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Challenge was updated but could not be reloaded.")
        return _challenge_from_row(row)
    finally:
        cursor.close()
        conn.close()


def delete_challenge(challenge_id: int) -> None:
    """Soft-delete a challenge so historical rounds remain valid."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE challenges SET is_active = 0 WHERE challenge_id = %s",
            (challenge_id,),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Challenge {challenge_id} does not exist.")
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def _score(draft: ResultDraft) -> float:
    if draft.mode == ModeCode.MEMORY:
        return float(draft.rounds)
    return round(draft.wpm * (draft.accuracy / 100), 1)


def _round_records(cursor: Any, result_id: int) -> list[RoundRecord]:
    cursor.execute(
        """
        SELECT round_number, challenge_id, accuracy, passed
        FROM round_results
        WHERE result_id = %s
        ORDER BY round_number
        """,
        (result_id,),
    )
    return [
        RoundRecord(
            row["round_number"],
            row["challenge_id"],
            float(row["accuracy"]),
            bool(row["passed"]),
        )
        for row in cursor.fetchall()
    ]


def save_result(user_id: int, draft: ResultDraft) -> SaveOutcome:
    """Persist a result, its rounds, and newly unlocked achievements atomically."""
    score = _score(draft)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    unlocked: list[Achievement] = []
    try:
        cursor.execute(
            """
            SELECT result_id, user_id, mode, wpm, accuracy, errors, score,
                   duration_seconds, rounds, created_at
            FROM results
            WHERE user_id = %s AND mode = %s
            ORDER BY score DESC, created_at ASC
            LIMIT 1
            """,
            (user_id, draft.mode.value),
        )
        previous_row = cursor.fetchone()

        cursor.execute(
            """
            INSERT INTO results
                (user_id, mode, wpm, accuracy, errors, score, duration_seconds, rounds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                draft.mode.value,
                draft.wpm,
                draft.accuracy,
                draft.errors,
                score,
                draft.duration_seconds,
                draft.rounds,
            ),
        )
        result_id = int(cursor.lastrowid)

        for round_record in draft.round_details:
            cursor.execute(
                """
                INSERT INTO round_results
                    (result_id, round_number, challenge_id, accuracy, passed)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    result_id,
                    round_record.round_number,
                    round_record.challenge_id,
                    round_record.accuracy,
                    round_record.passed,
                ),
            )

        cursor.execute(
            """
            SELECT result_id, user_id, mode, wpm, accuracy, errors, score,
                   duration_seconds, rounds, created_at
            FROM results
            WHERE result_id = %s
            """,
            (result_id,),
        )
        result_row = cursor.fetchone()
        if result_row is None:
            raise RuntimeError("Result was inserted but could not be reloaded.")
        result = _result_from_row(result_row, _round_records(cursor, result_id))

        cursor.execute(
            """
            SELECT a.achievement_id, a.code
            FROM achievements AS a
            INNER JOIN user_achievements AS ua
                ON ua.achievement_id = a.achievement_id
            WHERE ua.user_id = %s
            """,
            (user_id,),
        )
        owned_codes = {row["code"] for row in cursor.fetchall()}

        for achievement in ACHIEVEMENTS:
            if achievement.code not in owned_codes and achievement.test(result):
                cursor.execute(
                    """
                    INSERT INTO user_achievements (user_id, achievement_id, result_id)
                    SELECT %s, achievement_id, %s
                    FROM achievements
                    WHERE code = %s
                    """,
                    (user_id, result_id, achievement.code),
                )
                if cursor.rowcount == 1:
                    unlocked.append(achievement)

        conn.commit()
        previous_score = float(previous_row["score"]) if previous_row else None
        return SaveOutcome(
            result=result,
            unlocked=unlocked,
            is_new_best=previous_score is None or score > previous_score,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_results(
    user_id: int | None = None,
    mode: ModeCode | None = None,
) -> list[Result]:
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        clauses = []
        params: list[object] = []
        if user_id is not None:
            clauses.append("user_id = %s")
            params.append(user_id)
        if mode is not None:
            clauses.append("mode = %s")
            params.append(mode.value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cursor.execute(
            f"""
            SELECT result_id, user_id, mode, wpm, accuracy, errors, score,
                   duration_seconds, rounds, created_at
            FROM results
            {where}
            ORDER BY created_at DESC
            """,
            tuple(params),
        )
        results = []
        for row in cursor.fetchall():
            results.append(_result_from_row(row, _round_records(cursor, row["result_id"])))
        return results
    finally:
        cursor.close()
        conn.close()


def get_leaderboard(mode: ModeCode) -> list[Result]:
    """Return one highest-scoring result per user for a mode."""
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT r.result_id, r.user_id, r.mode, r.wpm, r.accuracy, r.errors,
                   r.score, r.duration_seconds, r.rounds, r.created_at
            FROM results AS r
            INNER JOIN (
                SELECT user_id, MAX(score) AS best_score
                FROM results
                WHERE mode = %s
                GROUP BY user_id
            ) AS best
                ON best.user_id = r.user_id AND best.best_score = r.score
            WHERE r.mode = %s
            ORDER BY r.score DESC, r.created_at ASC
            """,
            (mode.value, mode.value),
        )
        results = []
        seen_users: set[int] = set()
        for row in cursor.fetchall():
            if row["user_id"] in seen_users:
                continue
            seen_users.add(row["user_id"])
            results.append(_result_from_row(row, _round_records(cursor, row["result_id"])))
        return results
    finally:
        cursor.close()
        conn.close()


def seed_achievements() -> None:
    """Insert the Python achievement catalogue without duplicating rows."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.executemany(
            """
            INSERT INTO achievements (code, name, description)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE name = VALUES(name), description = VALUES(description)
            """,
            [(a.code, a.name, a.description) for a in ACHIEVEMENTS],
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def seed_challenges() -> None:
    conn = connect_db()
    cursor = conn.cursor()
    try:
        for category, difficulty, text in (
            ("Proverbs", Difficulty.EASY, "The early bird catches the worm."),
            ("Proverbs", Difficulty.EASY, "Practice makes perfect, so keep on typing."),
            ("Nature", Difficulty.EASY, "The river runs quietly past the old stone bridge."),
            ("Nature", Difficulty.MEDIUM, "Morning fog drifted over the hills while the birds began their song."),
            ("Technology", Difficulty.MEDIUM, "A good program is written for people to read and only incidentally for machines to run."),
            ("Literature", Difficulty.MEDIUM, "Ink spilled across the page like a story that refused to wait its turn."),
            ("Technology", Difficulty.HARD, "Encapsulation, inheritance, polymorphism, and abstraction form the pillars of object-oriented design."),
            ("Science", Difficulty.HARD, "Photosynthesis converts light energy into chemical energy, releasing oxygen as a by-product."),
        ):
            cursor.execute(
                """
                INSERT INTO challenges (category, difficulty, text, passage_text)
                SELECT %s, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM challenges WHERE text = %s
                )
                """,
                (category, difficulty.value, text, text, text),
            )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def seed_defaults() -> None:
    seed_achievements()
    seed_challenges()


def get_user_achievements(user_id: int) -> list[UserAchievement]:
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT ua.user_id, ua.achievement_id, a.code, ua.result_id, ua.unlocked_at
            FROM user_achievements AS ua
            INNER JOIN achievements AS a ON a.achievement_id = ua.achievement_id
            WHERE ua.user_id = %s
            ORDER BY ua.unlocked_at
            """,
            (user_id,),
        )
        return [
            UserAchievement(
                row["user_id"],
                row["achievement_id"],
                row["code"],
                row["result_id"],
                row["unlocked_at"],
            )
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()
        conn.close()


def select_user(user_id: int | None) -> None:
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES ('current_user_id', %s)
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            """,
            (str(user_id) if user_id is not None else None,),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_selected_user_id() -> int | None:
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT setting_value FROM app_settings WHERE setting_key = 'current_user_id'"
        )
        row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        return int(row[0])
    finally:
        cursor.close()
        conn.close()
