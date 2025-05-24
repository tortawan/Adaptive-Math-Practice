import unittest
from auth_utils import hash_password, verify_password # Make sure auth_utils.py is in the same directory or accessible in PYTHONPATH

class TestAuthUtils(unittest.TestCase):

    def test_hash_password_creates_valid_hash(self):
        """Test that hash_password returns a non-empty string (the hash)."""
        password = "testpassword123"
        hashed_password = hash_password(password)
        self.assertIsInstance(hashed_password, str)
        self.assertTrue(len(hashed_password) > 0)
        # bcrypt hashes typically start with '$2b$' or similar
        self.assertTrue(hashed_password.startswith('$2b$'))

    def test_verify_password_correct(self):
        """Test that verify_password returns True for a correct password."""
        password = "securePassword!@#"
        hashed_password = hash_password(password)
        self.assertTrue(verify_password(hashed_password, password))

    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for an incorrect password."""
        password_correct = "myRealPassword"
        password_incorrect = "wrongPassword"
        hashed_password = hash_password(password_correct)
        self.assertFalse(verify_password(hashed_password, password_incorrect))

    def test_verify_password_empty_stored_hash(self):
        """Test that verify_password returns False if the stored hash is empty or None."""
        password = "somePassword"
        self.assertFalse(verify_password("", password))
        self.assertFalse(verify_password(None, password)) # type: ignore

    def test_verify_password_empty_provided_password(self):
        """Test verifying an empty provided password against a valid hash."""
        original_password = "validPassword"
        hashed_password = hash_password(original_password)
        # bcrypt's checkpw will handle this; it should return False
        self.assertFalse(verify_password(hashed_password, ""))

    def test_passwords_with_special_chars(self):
        """Test hashing and verification with passwords containing special characters."""
        password = "P@$$wOrd W!th $p€c!@l Ch@r$"
        hashed_password = hash_password(password)
        self.assertTrue(verify_password(hashed_password, password))
        self.assertFalse(verify_password(hashed_password, "P@$$wOrd W!th $p€c!@l Ch@r")) # Slightly different

    def test_different_passwords_produce_different_hashes(self):
        """Test that two different passwords produce two different hashes."""
        password_a = "password123"
        password_b = "password456"
        hash_a = hash_password(password_a)
        hash_b = hash_password(password_b)
        self.assertNotEqual(hash_a, hash_b)

    def test_same_password_produces_different_hashes_due_to_salt(self):
        """Test that hashing the same password multiple times produces different hashes (due to salting)."""
        password = "commonPassword"
        hash_1 = hash_password(password)
        hash_2 = hash_password(password)
        # Hashes should be different because of the salt, but both should verify
        self.assertNotEqual(hash_1, hash_2)
        self.assertTrue(verify_password(hash_1, password))
        self.assertTrue(verify_password(hash_2, password))

if __name__ == '__main__':
    unittest.main()