import unittest

from database.database_manager import UsernameError, validate_username


class UsernameValidationTests(unittest.TestCase):
    def assert_message(self, value, expected):
        with self.assertRaisesRegex(UsernameError, f"^{expected}$"):
            validate_username(value)

    def test_exact_validation_messages(self):
        self.assert_message("", "Please enter a username.")
        self.assert_message("abc", "Username is too short. Use at least 4 characters.")
        self.assert_message("a" * 21, "Username is too long. Use 20 characters or fewer.")
        self.assert_message(
            "bad name",
            r"Use only letters, numbers, underscore \(_\), dot \(\.\) or hyphen \(-\). No spaces.",
        )
        self.assertEqual(validate_username("Jaik"), "Jaik")
