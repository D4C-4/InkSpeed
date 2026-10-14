"""Typing passage domain model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass(slots=True)
class Challenge:
    challenge_id: int
    category: str
    difficulty: Difficulty
    text: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None