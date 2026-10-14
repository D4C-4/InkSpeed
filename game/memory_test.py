"""Memory Rush mode configuration."""
from models.result import ModeCode

from .typing_test import TypingTest


class MemoryTest(TypingTest):
    def __init__(self, *args, **kwargs):
        super().__init__(ModeCode.MEMORY, *args, **kwargs)