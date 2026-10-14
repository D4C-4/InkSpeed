import unittest

from game.typing_test import Phase, TypingTest
from models import ModeCode


class TypingModeTests(unittest.TestCase):
    def test_blind_modes_never_shorten_typed_text(self):
        for mode in (ModeCode.MEMORY, ModeCode.CHAOS):
            with self.subTest(mode=mode):
                session = TypingTest(mode, [], 30, None, lambda draft: None)
                session.target = "abc"
                session.phase = Phase.TYPING
                session.type_char("a")
                session.backspace()
                self.assertEqual(session.typed, "a")
