"""Pure typing calculations shared by every game mode."""
from __future__ import annotations

import math

from models.result import ModeCode


def calc_wpm(typed_chars: int, elapsed_seconds: float) -> float:
    if typed_chars <= 0 or elapsed_seconds <= 0:
        return 0.0
    return round(typed_chars / 5 / (elapsed_seconds / 60), 1)


def calc_accuracy(correct: int, typed: int) -> float:
    if typed <= 0:
        return 0.0
    return round(correct / typed * 100, 1)


def calc_score(mode: ModeCode, wpm: float, accuracy: float, rounds: int) -> float:
    if mode == ModeCode.MEMORY:
        return float(rounds)
    return round(wpm * accuracy / 100, 1)


def compare(target: str, typed: str) -> tuple[int, int]:
    correct = sum(
        1 for index, char in enumerate(typed)
        if index < len(target) and char == target[index]
    )
    return correct, len(typed) - correct


def format_duration(seconds: float) -> str:
    total = int(math.floor(seconds + 0.5))
    minutes, remainder = divmod(total, 60)
    return f"{minutes}m {remainder:02d}s" if minutes else f"{remainder}s"