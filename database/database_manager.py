"""MySQL repositories for users, challenges, results, and achievements."""
from __future__ import annotations

import re
from dataclasses import dataclass
import json
from typing import Any

from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

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


class AuthorizationError(PermissionError):
    """A user does not have permission to perform an operation."""


ROLE_ADMIN = "Admin"
ROLE_PLAYER = "Player"
ROLE_VIEWER = "Viewer"


def _role_id(cursor: Any, role_name: str) -> int:
    cursor.execute(
        "SELECT role_id FROM user_roles WHERE role_name = %s", (role_name,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Role {role_name} is not configured.")
    return int(row["role_id"] if isinstance(row, dict) else row[0])


def _role_name(user_id: int, cursor: Any) -> str:
    cursor.execute(
        """
        SELECT ur.role_name
        FROM users AS u
        INNER JOIN user_roles AS ur ON ur.role_id = u.role_id
        WHERE u.user_id = %s
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise AuthorizationError("The signed-in user no longer exists.")
    return row["role_name"] if isinstance(row, dict) else row[0]


def _require_role(actor_user_id: int | None, allowed: set[str], owner_id: int | None = None) -> None:
    if actor_user_id is None:
        return
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        role = _role_name(actor_user_id, cursor)
        if role not in allowed and (owner_id is None or actor_user_id != owner_id):
            raise AuthorizationError(
                "You are not allowed to perform this action.")
    finally:
        cursor.close()
        conn.close()


def _audit(cursor: Any, actor_user_id: int | None, action: str, entity: str, entity_id: int | None, details: dict[str, Any] | None = None) -> None:
    cursor.execute(
        """
        INSERT INTO audit_log (actor_user_id, action_name, entity_name, entity_id, details)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (actor_user_id, action, entity, entity_id, json.dumps(details or {})),
    )


def validate_username(username: str) -> str:
    cleaned = username.strip()
    if not cleaned:
        raise UsernameError("Please enter a username.")
    if len(cleaned) < USERNAME_MIN:
        raise UsernameError(
            "Username is too short. Use at least 4 characters.")
    if len(cleaned) > USERNAME_MAX:
        raise UsernameError(
            "Username is too long. Use 20 characters or fewer.")
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


def _category_id(cursor: Any, category: str) -> int:
    cursor.execute(
        """
        INSERT INTO challenge_categories (category_name)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE category_id = LAST_INSERT_ID(category_id)
        """,
        (category,),
    )
    return int(cursor.lastrowid)


def _user_from_row(row: dict[str, Any]) -> User:
    return User(
        row["user_id"],
        row["username"],
        row["created_at"],
        row.get("role_id"),
        row.get("role_name", ROLE_PLAYER),
    )


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


def add_user(
    username: str,
    password: str | None = None,
    role_name: str = ROLE_PLAYER,
    actor_user_id: int | None = None,
) -> User:
    """Create and return a user."""
    _require_role(actor_user_id, {ROLE_ADMIN})
    name = validate_username(username)
    if password is not None and len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        role = _role_id(cursor, role_name)
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role_id) VALUES (%s, %s, %s)",
                (name, generate_password_hash(password or name), role),
            )
        except IntegrityError as error:
            if error.errno == 1062:
                raise UsernameError(
                    f'The username "{name}" is already taken. Please choose another one.'
                ) from error
            raise
        conn.commit()
        cursor.execute(
            """
            SELECT u.user_id, u.username, u.created_at, u.role_id, ur.role_name
            FROM users AS u
            INNER JOIN user_roles AS ur ON ur.role_id = u.role_id
            WHERE u.user_id = %s
            """,
            (cursor.lastrowid,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("User was inserted but could not be reloaded.")
        _audit(cursor, actor_user_id, "CREATE", "users",
               int(row["user_id"]), {"username": name})
        conn.commit()
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
            """
            SELECT u.user_id, u.username, u.created_at, u.role_id, ur.role_name
            FROM users AS u
            INNER JOIN user_roles AS ur ON ur.role_id = u.role_id
            ORDER BY u.username
            """
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
            """
            SELECT u.user_id, u.username, u.created_at, u.role_id, ur.role_name
            FROM users AS u
            INNER JOIN user_roles AS ur ON ur.role_id = u.role_id
            WHERE u.user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return _user_from_row(row) if row else None
    finally:
        cursor.close()
        conn.close()


def rename_user(user_id: int, username: str, actor_user_id: int | None = None) -> User:
    _require_role(actor_user_id, {ROLE_ADMIN}, user_id)
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
            raise UsernameError(
                "That user no longer exists. Please select a player again.")
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
            """
            SELECT u.user_id, u.username, u.created_at, u.role_id, ur.role_name
            FROM users AS u
            INNER JOIN user_roles AS ur ON ur.role_id = u.role_id
            WHERE u.user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("User was updated but could not be reloaded.")
        _audit(cursor, actor_user_id, "UPDATE",
               "users", user_id, {"username": name})
        conn.commit()
        return _user_from_row(row)
    finally:
        cursor.close()
        conn.close()


def delete_user(user_id: int, actor_user_id: int | None = None) -> None:
    _require_role(actor_user_id, {ROLE_ADMIN}, user_id)
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
        _audit(cursor, actor_user_id, "DELETE", "users", user_id)
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
            SELECT c.challenge_id, cc.category_name AS category, c.difficulty,
                   COALESCE(c.text, c.passage_text) AS text, c.is_active,
                   c.created_at, c.updated_at
            FROM challenges
            AS c
            INNER JOIN challenge_categories AS cc ON cc.category_id = c.category_id
            {where}
            ORDER BY challenge_id
            """,
            tuple(params),
        )
        return [_challenge_from_row(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def add_challenge(
    category: str,
    difficulty: Difficulty,
    text: str,
    actor_user_id: int | None = None,
) -> Challenge:
    _require_role(actor_user_id, {ROLE_ADMIN})
    category, text = _validate_challenge(category, text)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        category_id = _category_id(cursor, category)
        cursor.execute(
            """
            INSERT INTO challenges (category_id, category, difficulty, text, passage_text)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (category_id, category, difficulty.value, text, text),
        )
        conn.commit()
        cursor.execute(
            """
            SELECT c.challenge_id, cc.category_name AS category, c.difficulty,
                   COALESCE(c.text, c.passage_text) AS text, c.is_active,
                   c.created_at, c.updated_at
            FROM challenges AS c
            INNER JOIN challenge_categories AS cc ON cc.category_id = c.category_id
            WHERE c.challenge_id = %s
            """,
            (cursor.lastrowid,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(
                "Challenge was inserted but could not be reloaded.")
        _audit(cursor, actor_user_id, "CREATE", "challenges",
               int(row["challenge_id"]), {"category": category})
        conn.commit()
        raise RuntimeError(
            "Challenge was inserted but could not be reloaded.")
        return _challenge_from_row(row)
    finally:
        cursor.close()
        conn.close()


def update_challenge(
    challenge_id: int,
    category: str,
    difficulty: Difficulty,
    text: str,
    actor_user_id: int | None = None,
) -> Challenge:
    _require_role(actor_user_id, {ROLE_ADMIN})
    category, text = _validate_challenge(category, text)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        category_id = _category_id(cursor, category)
        cursor.execute(
            """
            UPDATE challenges
            SET category_id = %s, category = %s, difficulty = %s, text = %s, passage_text = %s
            WHERE challenge_id = %s
            """,
            (category_id, category, difficulty.value, text, text, challenge_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Challenge {challenge_id} does not exist.")
        conn.commit()
        cursor.execute(
            """
            SELECT c.challenge_id, cc.category_name AS category, c.difficulty,
                   COALESCE(c.text, c.passage_text) AS text, c.is_active,
                   c.created_at, c.updated_at
            FROM challenges AS c
            INNER JOIN challenge_categories AS cc ON cc.category_id = c.category_id
            WHERE c.challenge_id = %s
            """,
            (challenge_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(
                "Challenge was updated but could not be reloaded.")
        _audit(cursor, actor_user_id, "UPDATE", "challenges",
               challenge_id, {"category": category})
        conn.commit()
        return _challenge_from_row(row)
    finally:
        cursor.close()
        conn.close()


def delete_challenge(challenge_id: int, actor_user_id: int | None = None) -> None:
    _require_role(actor_user_id, {ROLE_ADMIN})
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
        _audit(cursor, actor_user_id, "DELETE", "challenges", challenge_id)
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


def save_result(
    user_id: int,
    draft: ResultDraft,
    actor_user_id: int | None = None,
) -> SaveOutcome:
    """Persist a result, its rounds, and newly unlocked achievements atomically."""
    _require_role(actor_user_id, {ROLE_ADMIN, ROLE_PLAYER}, user_id)
    if draft.accuracy < 50:
        raise ValueError("Results below 50% accuracy are not accepted.")
    if draft.wpm > 250:
        raise ValueError("Results above 250 WPM are not accepted.")
    score = _score(draft)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    unlocked: list[Achievement] = []
    try:
        cursor.execute(
            """
            SELECT pb.best_score, pb.result_id
            FROM personal_bests AS pb
            INNER JOIN game_modes AS gm ON gm.mode_id = pb.mode_id
            WHERE pb.user_id = %s AND gm.mode_name = %s
            """,
            (user_id, _mode_label(draft.mode)),
        )
        previous_row = cursor.fetchone()
        cursor.execute(
            "SELECT mode_id FROM game_modes WHERE mode_name = %s", (_mode_label(draft.mode),))
        mode_id = int(cursor.fetchone()["mode_id"])

        cursor.execute(
            """
            INSERT INTO results
                (user_id, mode, mode_id, wpm, accuracy, errors, score, duration_seconds, rounds)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                draft.mode.value,
                mode_id,
                draft.wpm,
                draft.accuracy,
                draft.errors,
                score,
                draft.duration_seconds,
                draft.rounds,
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
            raise RuntimeError(
                "Result was inserted but could not be reloaded.")
        result = _result_from_row(
            result_row, _round_records(cursor, result_id))

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

        _upsert_personal_best(cursor, user_id, mode_id, score, result_id)
        _audit(cursor, actor_user_id, "CREATE", "results",
               result_id, {"mode": draft.mode.value})
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


def _mode_label(mode: ModeCode) -> str:
    return {
        ModeCode.CLASSIC: "Classic",
        ModeCode.MEMORY: "Memory Rush",
        ModeCode.CHAOS: "Key Chaos",
    }[mode]


def _upsert_personal_best(cursor: Any, user_id: int, mode_id: int, score: float, result_id: int) -> None:
    cursor.execute(
        """
        INSERT INTO personal_bests (user_id, mode_id, best_score, result_id)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            best_score = IF(
                VALUES(best_score) > personal_bests.best_score,
                VALUES(best_score),
                personal_bests.best_score
            ),
            result_id = IF(
                VALUES(best_score) > personal_bests.best_score,
                VALUES(result_id),
                personal_bests.result_id
            ),
            updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, mode_id, score, result_id),
    )


def _recalculate_personal_best(cursor: Any, user_id: int, mode_id: int) -> None:
    cursor.execute(
        """
        SELECT result_id, score
        FROM results
        WHERE user_id = %s AND mode_id = %s
        ORDER BY score DESC, created_at ASC, result_id ASC
        LIMIT 1
        """,
        (user_id, mode_id),
    )
    row = cursor.fetchone()
    if row is None:
        cursor.execute(
            "DELETE FROM personal_bests WHERE user_id = %s AND mode_id = %s",
            (user_id, mode_id),
        )
    else:
        cursor.execute(
            """
            INSERT INTO personal_bests (user_id, mode_id, best_score, result_id)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE best_score = VALUES(best_score),
                result_id = VALUES(result_id), updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, mode_id, row["score"], row["result_id"]),
        )


def delete_result(
    user_id: int,
    result_id: int,
    actor_user_id: int | None = None,
) -> None:
    _require_role(actor_user_id, {ROLE_ADMIN, ROLE_PLAYER}, user_id)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id, mode_id FROM results WHERE result_id = %s",
            (result_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("That result no longer exists.")
        if int(row["user_id"]) != user_id:
            raise AuthorizationError("You can only delete your own results.")
        cursor.execute(
            "DELETE FROM round_results WHERE result_id = %s", (result_id,))
        cursor.execute(
            "DELETE FROM user_achievements WHERE result_id = %s", (result_id,))
        cursor.execute(
            "UPDATE personal_bests SET result_id = NULL WHERE result_id = %s",
            (result_id,),
        )
        cursor.execute(
            "DELETE FROM results WHERE result_id = %s AND user_id = %s", (result_id, user_id))
        _recalculate_personal_best(cursor, user_id, int(row["mode_id"]))
        _audit(cursor, actor_user_id, "DELETE",
               "results", result_id, {"user_id": user_id})
        conn.commit()
        re_evaluate_achievements(user_id, actor_user_id)
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
            results.append(_result_from_row(
                row, _round_records(cursor, row["result_id"])))
        return results
    finally:
        cursor.close()
        conn.close()


def get_leaderboard(mode: ModeCode) -> list[Result]:
    """Return one highest-scoring result per user from personal_bests."""
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT r.result_id, r.user_id, r.mode, r.wpm, r.accuracy, r.errors,
                   r.score, r.duration_seconds, r.rounds, r.created_at
            FROM personal_bests AS pb
            INNER JOIN game_modes AS gm ON gm.mode_id = pb.mode_id
            INNER JOIN results AS r ON r.result_id = pb.result_id
            WHERE pb.user_id = r.user_id AND gm.mode_name = %s
            ORDER BY r.score DESC, r.created_at ASC
            """,
            (_mode_label(mode),),
        )
        results = []
        for row in cursor.fetchall():
            results.append(_result_from_row(
                row, _round_records(cursor, row["result_id"])))
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
    cursor = conn.cursor(dictionary=True)
    try:
        for category, difficulty, text in (
            ("Proverbs", Difficulty.EASY, "The early bird catches the worm."),
            ("Proverbs", Difficulty.EASY,
             "Practice makes perfect, so keep on typing."),
            ("Nature", Difficulty.EASY,
             "The river runs quietly past the old stone bridge."),
            ("Nature", Difficulty.MEDIUM,
             "Morning fog drifted over the hills while the birds began their song."),
            ("Technology", Difficulty.MEDIUM,
             "A good program is written for people to read and only incidentally for machines to run."),
            ("Literature", Difficulty.MEDIUM,
             "Ink spilled across the page like a story that refused to wait its turn."),
            ("Technology", Difficulty.HARD,
             "Encapsulation, inheritance, polymorphism, and abstraction form the pillars of object-oriented design."),
            ("Science", Difficulty.HARD,
             "Photosynthesis converts light energy into chemical energy, releasing oxygen as a by-product."),
        ):
            category_id = _category_id(cursor, category)
            cursor.execute(
                """
                INSERT INTO challenges (category_id, category, difficulty, text, passage_text)
                SELECT %s, %s, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM challenges WHERE text = %s
                )
                """,
                (category_id, category, difficulty.value, text, text, text),
            )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def seed_defaults() -> None:
    from os import getenv

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id FROM users WHERE username = %s", ("admin",))
        if cursor.fetchone() is None:
            admin_password = getenv("INKSPEED_ADMIN_PASSWORD", "Admin@12345")
            cursor.execute(
                "SELECT role_id FROM user_roles WHERE role_name = %s", (ROLE_ADMIN,))
            role_id = cursor.fetchone()["role_id"]
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role_id)
                VALUES (%s, %s, %s)
                """,
                ("admin", generate_password_hash(admin_password), role_id),
            )
            _audit(cursor, None, "CREATE", "users",
                   cursor.lastrowid, {"username": "admin"})
            conn.commit()
    finally:
        cursor.close()
        conn.close()
    seed_achievements()
    seed_challenges()


def authenticate_user(username: str, password: str) -> User | None:
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT u.user_id, u.username, u.password_hash, u.created_at,
                   u.role_id, ur.role_name
            FROM users AS u
            INNER JOIN user_roles AS ur ON ur.role_id = u.role_id
            WHERE LOWER(u.username) = LOWER(%s)
            """,
            (username.strip(),),
        )
        row = cursor.fetchone()
        if row is None or not row["password_hash"] or not check_password_hash(
            row["password_hash"], password
        ):
            return None
        return _user_from_row(row)
    finally:
        cursor.close()
        conn.close()


def re_evaluate_achievements(user_id: int, actor_user_id: int | None = None) -> None:
    _require_role(actor_user_id, {ROLE_ADMIN, ROLE_PLAYER}, user_id)
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT result_id, user_id, mode, wpm, accuracy, errors, score,
                   duration_seconds, rounds, created_at
            FROM results WHERE user_id = %s
            """,
            (user_id,),
        )
        results = [_result_from_row(row) for row in cursor.fetchall()]
        for achievement in ACHIEVEMENTS:
            cursor.execute(
                "SELECT achievement_id FROM achievements WHERE code = %s",
                (achievement.code,),
            )
            achievement_row = cursor.fetchone()
            if achievement_row is None:
                continue
            qualifies = next(
                (result for result in results if achievement.test(result)), None)
            if qualifies is None:
                cursor.execute(
                    """
                    DELETE FROM user_achievements
                    WHERE user_id = %s AND achievement_id = %s
                    """,
                    (user_id, achievement_row["achievement_id"]),
                )
            else:
                cursor.execute(
                    """
                    INSERT IGNORE INTO user_achievements (user_id, achievement_id, result_id)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id,
                     achievement_row["achievement_id"], qualifies.result_id),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


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
