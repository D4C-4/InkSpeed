"""Key Chaos mapping utilities."""
from __future__ import annotations

import random
import string

from models.challenge import Difficulty

CHAOS_SCRAMBLES = {
    Difficulty.EASY: 5,
    Difficulty.MEDIUM: 8,
    Difficulty.HARD: 10,
}


def scramble_count_for(
    difficulty: Difficulty | None,
    rng: random.Random | None = None,
) -> int:
    rng = rng or random
    return CHAOS_SCRAMBLES[difficulty or rng.choice(list(CHAOS_SCRAMBLES))]


def make_key_map(count: int, rng: random.Random | None = None) -> dict[str, str]:
    rng = rng or random.Random()
    picked = rng.sample(list(string.ascii_lowercase), max(2, min(count, 25)))
    shuffled = picked[:]
    while any(left == right for left, right in zip(picked, shuffled)):
        rng.shuffle(shuffled)
    mapping = {letter: letter for letter in string.ascii_lowercase}
    mapping.update(zip(picked, shuffled))
    return mapping


def translate_key(key: str, mapping: dict[str, str]) -> str:
    translated = mapping.get(key.lower(), key)
    return translated.upper() if key.isupper() else translated


def reverse_scrambled(mapping: dict[str, str]) -> dict[str, str]:
    return {target: source for source, target in mapping.items() if source != target}