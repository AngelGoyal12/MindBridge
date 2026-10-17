
import unittest

from auth.security import hash_password, verify_password


class PasswordSecurityTests(unittest.TestCase):
    def test_correct_password_is_verified(self):
        password = "DemoPassword123!"
        stored_hash = hash_password(password)

        self.assertNotEqual(stored_hash, password)
        self.assertTrue(verify_password(password, stored_hash))

    def test_incorrect_password_is_rejected(self):
        stored_hash = hash_password("CorrectPassword123!")

        self.assertFalse(
            verify_password("WrongPassword123!", stored_hash)
        )

    def test_hashes_use_random_salts(self):
        password = "DemoPassword123!"

        first_hash = hash_password(password)
        second_hash = hash_password(password)

        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(verify_password(password, first_hash))
        self.assertTrue(verify_password(password, second_hash))

    def test_empty_password_is_rejected(self):
        with self.assertRaises(ValueError):
            hash_password("")

        self.assertFalse(verify_password("", "some-hash"))


if __name__ == "__main__":
    unittest.main()
