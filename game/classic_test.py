"""Classic mode configuration."""
from models.result import ModeCode

from .typing_test import TypingTest


class ClassicTest(TypingTest):
    def __init__(self, *args, **kwargs):
        super().__init__(ModeCode.CLASSIC, *args, **kwargs)