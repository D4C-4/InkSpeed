"""Key Chaos mode configuration."""
from models.result import ModeCode

from .typing_test import TypingTest


class ChaosTest(TypingTest):
    def __init__(self, *args, **kwargs):
        super().__init__(ModeCode.CHAOS, *args, **kwargs)