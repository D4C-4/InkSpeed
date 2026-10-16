"""Small HTTP API for the InkSpeed React client.

The browser UI stays responsible for presentation. All persistent state remains
in the existing MySQL repository layer.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import logging
from typing import Any

from flask import Flask, jsonify, request
import mysql.connector
from mysql.connector import IntegrityError

from database.connection import initialize_database
from database.database_manager import (
    add_challenge,
    add_user,
    delete_challenge,
    delete_user,
    get_challenges,
    get_results,
    get_selected_user_id,
    get_user_achievements,
    get_user,
    get_users,
    rename_user,
    save_result,
    seed_defaults,
    select_user,
    update_challenge,
)
from database.database_manager import UsernameError
from models import Difficulty, ModeCode, ResultDraft, RoundRecord

app = Flask(__name__)
logger = logging.getLogger(__name__)


@app.errorhandler(UsernameError)
def handle_username_error(error: UsernameError):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(mysql.connector.Error)
def handle_database_error(error):
    logger.exception("Database request failed", exc_info=error)
    return jsonify({
        "error": "Can't reach the database. Make sure MySQL is running in XAMPP, then try again."
    }), 503


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    logger.exception("Unexpected API request failure", exc_info=error)
    return jsonify({"error": "Something went wrong. Please try again."}), 500


def _json_value(value: Any) -> Any:
    if callable(value):
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {
            key: _json_value(item)
            for key, item in value.items()
            if not callable(item)
        }
    if hasattr(value, "__dataclass_fields__"):
        return _json_value(asdict(value))
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _state() -> dict[str, Any]:
    users = get_users()
    results = get_results()
    return {
        "users": _json_value(users),
        "challenges": _json_value(get_challenges()),
        "results": _json_value(results),
        "userAchievements": _json_value(
            [achievement for user in users for achievement in get_user_achievements(
                user.user_id)]
        ),
        "currentUserId": get_selected_user_id(),
    }


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = request.headers.get(
        "Origin", "*")
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PATCH,DELETE,OPTIONS"
    return response


@app.get("/api/state")
def state():
    return jsonify(_state())


@app.post("/api/users")
def create_user():
    user = add_user(request.json.get("username", ""))
    select_user(user.user_id)
    return jsonify(_state()), 201


@app.patch("/api/users/<int:user_id>")
def edit_user(user_id: int):
    rename_user(user_id, request.json.get("username", ""))
    return jsonify(_state())


@app.delete("/api/users/<int:user_id>")
def remove_user(user_id: int):
    delete_user(user_id)
    return jsonify(_state())


@app.post("/api/selected")
def set_selected_user():
    value = request.json.get("userId")
    select_user(int(value) if value is not None else None)
    return jsonify(_state())


@app.post("/api/challenges")
def create_or_update_challenge():
    data = request.json
    difficulty = Difficulty(data["difficulty"])
    challenge_id = data.get("id")
    if challenge_id is None:
        add_challenge(data.get("category", ""),
                      difficulty, data.get("text", ""))
    else:
        update_challenge(int(challenge_id), data.get(
            "category", ""), difficulty, data.get("text", ""))
    return jsonify(_state())


@app.delete("/api/challenges/<int:challenge_id>")
def remove_challenge(challenge_id: int):
    delete_challenge(challenge_id)
    return jsonify(_state())


@app.post("/api/results")
def create_result():
    data = request.json
    user_id = int(data["userId"])
    if get_user(user_id) is None:
        logger.warning("Attempted to create result for non-existent user")
        return jsonify({"error": "The selected user is no longer available. Please select or create a user again."}), 400
    rounds = [
        RoundRecord(
            int(round_data["round"]),
            int(round_data["challengeId"]),
            float(round_data["accuracy"]),
            bool(round_data["passed"]),
        )
        for round_data in data.get("roundDetails", [])
    ]
    try:
        outcome = save_result(
            user_id,
            ResultDraft(
                ModeCode(data["mode"]),
                float(data["wpm"]),
                float(data["accuracy"]),
                int(data["errors"]),
                int(data["duration"]),
                int(data.get("rounds", 0)),
                rounds,
            ),
        )
        return jsonify({"state": _state(), "outcome": _json_value(outcome)})
    except IntegrityError as error:
        logger.exception("save_result failed", exc_info=error)
        return jsonify({"error": f"Could not save result: {error.msg}"}), 400


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    initialize_database()
    seed_defaults()
    app.run(host="127.0.0.1", port=5000, debug=True)
