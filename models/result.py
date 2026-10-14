"""Typing result and Memory Rush round models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ModeCode(StrEnum):
    CLASSIC = "classic"
    MEMORY = "memory"
    CHAOS = "chaos"


@dataclass(slots=True)
class RoundRecord:
    round_number: int
    challenge_id: int
    accuracy: float
    passed: bool


@dataclass(slots=True)
class ResultDraft:
    """A finished game before it is persisted."""

    mode: ModeCode
    wpm: float
    accuracy: float
    errors: int
    duration_seconds: int
    rounds: int = 0
    round_details: list[RoundRecord] = field(default_factory=list)


@dataclass(slots=True)
class Result:
    result_id: int
    user_id: int
    mode: ModeCode
    wpm: float
    accuracy: float
    errors: int
    score: float
    duration_seconds: int
    rounds: int
    created_at: datetime
    round_details: list[RoundRecord] = field(default_factory=list)