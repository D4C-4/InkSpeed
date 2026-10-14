"""Shared state machine for Classic, Memory Rush, and Key Chaos."""
from __future__ import annotations

import random
import time
from enum import StrEnum
from typing import Callable, Sequence

from models.challenge import Challenge, Difficulty
from models.result import ModeCode, ResultDraft, RoundRecord

from .key_mapper import make_key_map, scramble_count_for, translate_key
from .text_generator import build_passage, pick_challenge
from .typing_calculator import calc_accuracy, calc_wpm, compare


class Phase(StrEnum):
    SETUP = "setup"
    MEMORIZE = "memorize"
    TYPING = "typing"
    DONE = "done"


class TypingTest:
    def __init__(
        self,
        mode: ModeCode,
        challenges: Sequence[Challenge],
        duration: int,
        difficulty: Difficulty | None,
        on_finish: Callable[[ResultDraft], None],
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        self.mode, self.duration, self.difficulty = mode, duration, difficulty
        self.challenges, self.on_finish = challenges, on_finish
        self.clock, self.rng = clock, rng or random.Random()
        self.phase = Phase.SETUP
        self.target = ""
        self.typed = ""
        self.errors = 0
        self.key_map: dict[str, str] | None = None
        self.rounds: list[RoundRecord] = []
        self._challenge_id: int | None = None
        self._started: float | None = None
        self._memorize_until = 0.0
        self._total_chars = 0
        self._total_correct = 0
        self._total_errors = 0
        self._total_seconds = 0.0

    def start(self) -> None:
        self.phase = Phase.SETUP
        self.rounds.clear()
        self._total_chars = self._total_correct = self._total_errors = 0
        self._total_seconds = 0.0
        if self.mode == ModeCode.CLASSIC:
            self.target = build_passage(
                self.challenges, self.difficulty, self.duration * 12, self.rng
            )
            self._reset_round()
            self.phase = Phase.TYPING
        else:
            if self.mode == ModeCode.CHAOS:
                self.key_map = make_key_map(
                    scramble_count_for(self.difficulty, self.rng), self.rng
                )
            self._new_round()

    def tick(self) -> None:
        now = self.clock()
        if self.phase == Phase.MEMORIZE and now >= self._memorize_until:
            self.skip_memorize()
        elif (
            self.mode == ModeCode.CLASSIC
            and self.phase == Phase.TYPING
            and self._started is not None
            and now - self._started >= self.duration
        ):
            self._finish(self.typed, self.errors, self.duration)

    def skip_memorize(self) -> None:
        if self.phase == Phase.MEMORIZE:
            self.phase = Phase.TYPING
            self._started = None

    def type_char(self, char: str) -> None:
        if self.phase != Phase.TYPING or len(self.typed) >= len(self.target):
            return
        if self.key_map and self.mode == ModeCode.CHAOS:
            char = translate_key(char, self.key_map)
        if self._started is None:
            self._started = self.clock()
        if char != self.target[len(self.typed)]:
            self.errors += 1
        self.typed += char
        if len(self.typed) == len(self.target):
            self._finish(self.typed, self.errors, max(self.clock() - self._started, 0.5))

    def backspace(self) -> None:
        if self.mode == ModeCode.CLASSIC and self.phase == Phase.TYPING:
            self.typed = self.typed[:-1]

    @property
    def elapsed(self) -> float:
        return 0.0 if self._started is None else self.clock() - self._started

    @property
    def time_left(self) -> float:
        return max(0.0, self.duration - self.elapsed)

    @property
    def live_wpm(self) -> float:
        return calc_wpm(len(self.typed), max(self.elapsed, 1))

    @property
    def live_accuracy(self) -> float:
        correct, _ = compare(self.target, self.typed)
        return calc_accuracy(correct, len(self.typed))

    def _reset_round(self) -> None:
        self.typed, self.errors, self._started = "", 0, None

    def _new_round(self) -> None:
        challenge = pick_challenge(
            self.challenges, self.difficulty, self._challenge_id, self.rng
        )
        self.target, self._challenge_id = challenge.text, challenge.challenge_id
        self._reset_round()
        self._memorize_until = self.clock() + self.duration
        self.phase = Phase.MEMORIZE

    def _finish(self, typed: str, errors: int, seconds: float) -> None:
        correct, _ = compare(self.target, typed)
        wpm, accuracy = calc_wpm(len(typed), seconds), calc_accuracy(correct, len(typed))
        if self.mode != ModeCode.MEMORY:
            self._end(ResultDraft(self.mode, wpm, accuracy, errors, round(seconds)))
            return
        self._total_chars += len(typed)
        self._total_correct += correct
        self._total_errors += errors
        self._total_seconds += seconds
        passed = accuracy >= 90
        self.rounds.append(
            RoundRecord(len(self.rounds) + 1, self._challenge_id or 0, accuracy, passed)
        )
        if passed:
            self._new_round()
        else:
            self._end(
                ResultDraft(
                    self.mode,
                    calc_wpm(self._total_chars, self._total_seconds),
                    calc_accuracy(self._total_correct, self._total_chars),
                    self._total_errors,
                    round(self._total_seconds),
                    sum(round_result.passed for round_result in self.rounds),
                    list(self.rounds),
                )
            )

    def _end(self, draft: ResultDraft) -> None:
        self.phase = Phase.DONE
        self.on_finish(draft)


GameSession = TypingTest