"""Achievement definitions and persisted unlocks."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .result import ModeCode, Result


@dataclass(frozen=True, slots=True)
class Achievement:
    code: str
    name: str
    description: str
    test: Callable[[Result], bool]


@dataclass(slots=True)
class UserAchievement:
    user_id: int
    achievement_id: int
    code: str
    result_id: int | None
    unlocked_at: datetime


ACHIEVEMENTS: tuple[Achievement, ...] = (
    Achievement("first_ink", "First Ink", "Save your first result.", lambda r: bool(r)),
    Achievement(
        "wpm_40",
        "Quick Quill",
        "Reach 40 WPM in Classic.",
        lambda r: r.mode == ModeCode.CLASSIC and r.wpm >= 40 and r.accuracy >= 90,
    ),
    Achievement(
        "wpm_70",
        "Speed Scribe",
        "Reach 70 WPM in Classic.",
        lambda r: r.mode == ModeCode.CLASSIC and r.wpm >= 70 and r.accuracy >= 90,
    ),
    Achievement(
        "flawless",
        "Flawless",
        "Finish with 100% accuracy.",
        lambda r: r.mode != ModeCode.MEMORY and r.accuracy == 100 and r.wpm > 0,
    ),
    Achievement(
        "memory_3",
        "Steel Trap",
        "Complete 3 Memory Rush rounds.",
        lambda r: r.mode == ModeCode.MEMORY and r.rounds >= 3,
    ),
    Achievement(
        "chaos_tamer",
        "Chaos Tamer",
        "Finish Key Chaos above 80% accuracy.",
        lambda r: r.mode == ModeCode.CHAOS and r.accuracy >= 80,
    ),
)