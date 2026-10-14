import unittest
import uuid

from database.database_manager import add_user, delete_user, get_users, rename_user, select_user


class UserTests(unittest.TestCase):
    def test_duplicate_and_rename_rules(self):
        try:
            get_users()
        except Exception as error:
            self.skipTest(f"MySQL is unavailable: {error}")

        first = add_user(f"case_{uuid.uuid4().hex[:10]}")
        second = add_user(f"other_{uuid.uuid4().hex[:9]}")
        try:
            with self.assertRaisesRegex(ValueError, "already taken"):
                add_user(first.username.upper())
            with self.assertRaisesRegex(ValueError, "already your username"):
                rename_user(first.user_id, first.username)
            renamed = rename_user(first.user_id, first.username.swapcase())
            self.assertEqual(renamed.username, first.username.swapcase())
            with self.assertRaisesRegex(ValueError, "already taken"):
                rename_user(second.user_id, renamed.username)
        finally:
            delete_user(first.user_id)
            delete_user(second.user_id)

    def test_create_select_delete_twenty_users(self):
        try:
            get_users()
        except Exception as error:
            self.skipTest(f"MySQL is unavailable: {error}")

        names = [f"test_{uuid.uuid4().hex[:12]}_{index:02d}" for index in range(20)]
        users = []
        try:
            users = [add_user(name) for name in names]
            listed_ids = {user.user_id for user in get_users()}
            for user in users:
                self.assertIn(user.user_id, listed_ids)
                select_user(user.user_id)
        finally:
            for user in users:
                delete_user(user.user_id)
            select_user(None)
        remaining_ids = {item.user_id for item in get_users()}
        self.assertTrue(all(user.user_id not in remaining_ids for user in users))
