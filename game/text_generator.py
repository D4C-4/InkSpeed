"""Challenge selection and passage generation."""
from __future__ import annotations

import random
from collections.abc import Sequence

from models.challenge import Challenge, Difficulty

SEED_PASSAGES = (
    ("Proverbs", Difficulty.EASY, "The early bird catches the worm."),
    ("Proverbs", Difficulty.EASY, "Practice makes perfect, so keep on typing."),
    ("Nature", Difficulty.EASY, "The river runs quietly past the old stone bridge."),
    ("Nature", Difficulty.MEDIUM, "Morning fog drifted over the hills while the birds began their song."),
    ("Technology", Difficulty.MEDIUM, "A good program is written for people to read and only incidentally for machines to run."),
    ("Literature", Difficulty.MEDIUM, "Ink spilled across the page like a story that refused to wait its turn."),
    ("Technology", Difficulty.HARD, "Encapsulation, inheritance, polymorphism, and abstraction form the pillars of object-oriented design."),
    ("Science", Difficulty.HARD, "Photosynthesis converts light energy into chemical energy, releasing oxygen as a by-product."),
)


def pick_challenge(
    challenges: Sequence[Challenge],
    difficulty: Difficulty | None = None,
    exclude_id: int | None = None,
    rng: random.Random | None = None,
) -> Challenge:
    if not challenges:
        raise ValueError("At least one active challenge is required.")
    rng = rng or random
    pool = [c for c in challenges if difficulty is None or c.difficulty == difficulty]
    pool = pool or list(challenges)
    if len(pool) > 1 and exclude_id is not None:
        without_previous = [c for c in pool if c.challenge_id != exclude_id]
        pool = without_previous or pool
    return rng.choice(pool)


def build_passage(
    challenges: Sequence[Challenge],
    difficulty: Difficulty | None,
    minimum_length: int,
    rng: random.Random | None = None,
) -> str:
    parts: list[str] = []
    previous: int | None = None
    while len(" ".join(parts)) < minimum_length:
        challenge = pick_challenge(challenges, difficulty, previous, rng)
        parts.append(challenge.text)
        previous = challenge.challenge_id
    return " ".join(parts)