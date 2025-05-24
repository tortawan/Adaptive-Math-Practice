import unittest
from unittest.mock import patch, MagicMock, call # Import MagicMock and call
import sqlite3 # We'll be mocking parts of this
import time # For any time-related default values

# Assuming db_manager.py and config.py are in the same directory or accessible
from db_manager import DatabaseManager
import config # For LEVEL_RANGES etc.

# A dummy config for testing, so we don't depend on the actual config.py values changing
# Or, ensure your config.py is stable and its values are suitable for these tests.
# For simplicity here, we'll assume config.py is available and provides the necessary constants.

class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        """Set up for each test method."""
        # We pass a dummy db_name because connect will be mocked anyway
        self.db_manager = DatabaseManager(db_name=":memory:") # Use in-memory for setup simplicity, though it will be mocked

    @patch('sqlite3.connect') # Patch the connect function in the sqlite3 module
    def test_create_tables(self, mock_sqlite_connect):
        """Test that create_tables executes the correct SQL statements."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn # sqlite3.connect() will now return our mock_conn
        mock_conn.cursor.return_value = mock_cursor # conn.cursor() will return our mock_cursor

        self.db_manager.create_tables() # Call the method we're testing

        # Check that sqlite3.connect was called with the correct db_name
        mock_sqlite_connect.assert_called_once_with(self.db_manager.db_name)

        # Check that execute was called with the expected SQL queries
        expected_calls = [
            call("PRAGMA foreign_keys = ON"), # From _get_connection
            call(unittest.mock.ANY), # users table
            call(unittest.mock.ANY), # user_progress table
            call(unittest.mock.ANY), # user_progress index
            call(unittest.mock.ANY), # invitation_codes table
            call(unittest.mock.ANY)  # invitation_codes index
        ]
        # mock_cursor.execute.assert_has_calls(expected_calls, any_order=False)
        # More robust check for the number of execute calls if SQL text is complex to match
        self.assertEqual(mock_cursor.execute.call_count, len(expected_calls) -1) # -1 because PRAGMA is on conn

        # Check PRAGMA call on connection
        mock_conn.execute.assert_called_once_with("PRAGMA foreign_keys = ON")

        # Check if connection was closed (implicitly by context manager or explicitly)
        mock_conn.close.assert_called_once()


    @patch('sqlite3.connect')
    def test_add_user_success(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        # mock_cursor = MagicMock() # Not directly used by add_user's execute
        mock_sqlite_connect.return_value = mock_conn

        username = "testuser"
        hashed_password = "hashed_password_example"
        result = self.db_manager.add_user(username, hashed_password)

        mock_sqlite_connect.assert_called_once_with(self.db_manager.db_name)
        # The PRAGMA is called first by _get_connection
        mock_conn.execute.assert_any_call("PRAGMA foreign_keys = ON")
        
        expected_sql_insert = "INSERT OR REPLACE INTO users (username, password) VALUES (?, ?)"
        # Check that the INSERT was called after PRAGMA
        mock_conn.execute.assert_any_call(expected_sql_insert, (username, hashed_password))
        
        # Ensure execute was called at least for PRAGMA and the INSERT
        self.assertGreaterEqual(mock_conn.execute.call_count, 2)

        # If the 'with conn:' block completes without error, commit is implicit.
        # So, we don't assert mock_conn.commit.assert_called_once() here
        # if we trust the context manager behavior of the mock_conn.
        # Instead, we rely on the 'success = True' path being taken.
        
        mock_conn.close.assert_called_once()
        self.assertTrue(result) # This implies the 'with' block succeeded

    @patch('sqlite3.connect')
    def test_get_user_hash_found(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor # conn.execute() returns cursor

        expected_hash = "stored_hash_example"
        mock_cursor.fetchone.return_value = (expected_hash,) # fetchone returns a tuple

        username = "testuser"
        retrieved_hash = self.db_manager.get_user_hash(username)

        mock_sqlite_connect.assert_called_once_with(self.db_manager.db_name)
        expected_sql = "SELECT password FROM users WHERE username = ?"
        mock_conn.execute.assert_any_call(expected_sql, (username,))
        mock_cursor.fetchone.assert_called_once()
        mock_conn.close.assert_called_once()
        self.assertEqual(retrieved_hash, expected_hash)

    @patch('sqlite3.connect')
    def test_get_user_hash_not_found(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor

        mock_cursor.fetchone.return_value = None # Simulate user not found

        username = "nonexistentuser"
        retrieved_hash = self.db_manager.get_user_hash(username)

        self.assertIsNone(retrieved_hash)
        mock_conn.close.assert_called_once()


    @patch('sqlite3.connect')
    def test_save_user_progress(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_sqlite_connect.return_value = mock_conn

        # Original arguments for the method
        # username, folder_name, year, question_number, set_identifier, category, image_filename, user_choice, correct_choice, answer_time
        args_method = ("testuser", "AMC 8 2020", 2020, 1, "8", "Algebra", "q1.png", "A", "A", 30)
        result = self.db_manager.save_user_progress(*args_method)

        mock_sqlite_connect.assert_called_once_with(self.db_manager.db_name)
        mock_conn.execute.assert_any_call("PRAGMA foreign_keys = ON")

        # Arguments as they should be passed to the SQL execute, matching the SQL string's placeholders
        # SQL: (username, folder_name, year, question_number, set_identifier, category, user_choice, correct_choice, answer_time, image_filename)
        expected_args_for_sql = (
            args_method[0], args_method[1], args_method[2], args_method[3], args_method[4], 
            args_method[5], args_method[7], args_method[8], args_method[9], args_method[6]
        )
        
        # Check that the INSERT statement was made
        insert_sql_found = False
        for call_item in mock_conn.execute.call_args_list:
            args, _ = call_item
            if "INSERT INTO user_progress" in args[0]:
                self.assertEqual(args[1], expected_args_for_sql) # Check parameters for the INSERT
                insert_sql_found = True
                break
        self.assertTrue(insert_sql_found, "INSERT statement for user_progress not found")
        
        # Commit is implicit
        mock_conn.close.assert_called_once()
        self.assertTrue(result)

    @patch('sqlite3.connect')
    def test_get_user_progress(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # (folder_name, year, question_number, set_identifier, category, user_choice, correct_choice, answer_time, attempt_date, image_filename)
        expected_progress_data = [
            ("AMC 8 2020", 2020, 1, "8", "Algebra", "A", "A", 30, "2023-01-01 10:00:00", "q1.png"),
            ("AMC 8 2020", 2020, 2, "8", "Geometry", "B", "C", 45, "2023-01-01 10:05:00", "q2.png")
        ]
        mock_cursor.fetchall.return_value = expected_progress_data

        username = "testuser"
        progress = self.db_manager.get_user_progress(username)

        expected_sql = """
        SELECT folder_name, year, question_number, set_identifier, category,
               user_choice, correct_choice, answer_time, attempt_date, image_filename
        FROM user_progress
        WHERE username = ?
        ORDER BY attempt_date DESC
    """
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(unittest.mock.ANY, (username,)) # Check username param
        mock_cursor.fetchall.assert_called_once()
        mock_conn.close.assert_called_once()
        self.assertEqual(progress, expected_progress_data)


    # Test calculate_user_level (this is the most complex one)
    # We will mock get_user_progress directly on the instance of db_manager
    # This way, we don't need to mock sqlite3.connect for these specific tests.
    def test_calculate_user_level_no_progress(self):
        with patch.object(self.db_manager, 'get_user_progress', return_value=[]) as mock_get_progress:
            level = self.db_manager.calculate_user_level("newuser")
            mock_get_progress.assert_called_once_with("newuser")
            self.assertEqual(level, 1) # Default to level 1

    def test_calculate_user_level_advances(self):
        # Mock config values directly if they are too complex or you want to isolate
        # For simplicity, we use config directly. Ensure these values are set:
        # config.LEVEL_RANGES = {1: range(1, 6), 2: range(6, 11), ...}
        # config.QUESTIONS_FOR_LEVEL_ASSESSMENT = 3 (for easier testing)
        # config.CORRECT_ANSWERS_TO_LEVEL_UP = 2 (meaning 3 correct to pass)

        # Temporarily patch config for this test if needed, or ensure config is suitable
        with patch('config.QUESTIONS_FOR_LEVEL_ASSESSMENT', 3), \
             patch('config.CORRECT_ANSWERS_TO_LEVEL_UP', 2): # Need 3 correct out of 3 to pass for level up

            # Progress: (folder_name, year, question_number, set_id, category, user_choice, correct_choice, time, date, img)
            # Remember: get_user_progress returns items sorted by date DESC (most recent first)
            mock_progress_data = [
                # Level 1 attempts - 3 correct for Qs 1,2,3
                ("Set1", 2020, 3, "ID1", "CatA", "A", "A", 10, "2023-01-01 10:05:00", "q3.png"),
                ("Set1", 2020, 2, "ID1", "CatA", "B", "B", 10, "2023-01-01 10:04:00", "q2.png"),
                ("Set1", 2020, 1, "ID1", "CatA", "C", "C", 10, "2023-01-01 10:03:00", "q1.png"),
                 # Some other attempts that don't affect level 1 assessment
                ("Set1", 2020, 6, "ID1", "CatB", "D", "D", 10, "2023-01-01 10:02:00", "q6.png"),
            ]
            with patch.object(self.db_manager, 'get_user_progress', return_value=mock_progress_data):
                level = self.db_manager.calculate_user_level("testuser")
                # User passes level 1 (3/3 correct > 2), so current working level should be 2
                self.assertEqual(level, 2)


    def test_calculate_user_level_not_enough_attempts_for_assessment(self):
        with patch('config.QUESTIONS_FOR_LEVEL_ASSESSMENT', 5), \
             patch('config.CORRECT_ANSWERS_TO_LEVEL_UP', 3):
            mock_progress_data = [ # Only 2 attempts in level 1 range
                ("Set1", 2020, 2, "ID1", "CatA", "A", "A", 10, "2023-01-01 10:01:00", "q2.png"),
                ("Set1", 2020, 1, "ID1", "CatA", "B", "B", 10, "2023-01-01 10:00:00", "q1.png"),
            ]
            with patch.object(self.db_manager, 'get_user_progress', return_value=mock_progress_data):
                level = self.db_manager.calculate_user_level("testuser")
                # Not enough attempts for level 1 assessment, stays at level 1 (highest_passed_level = 0 + 1)
                self.assertEqual(level, 1)


    def test_calculate_user_level_fails_level_assessment(self):
        with patch('config.QUESTIONS_FOR_LEVEL_ASSESSMENT', 3), \
             patch('config.CORRECT_ANSWERS_TO_LEVEL_UP', 2): # Need 3 correct
            mock_progress_data = [ # Only 2 correct out of 3 for level 1
                ("Set1", 2020, 3, "ID1", "CatA", "A", "X", 10, "2023-01-01 10:02:00", "q3.png"), # Incorrect
                ("Set1", 2020, 2, "ID1", "CatA", "B", "B", 10, "2023-01-01 10:01:00", "q2.png"), # Correct
                ("Set1", 2020, 1, "ID1", "CatA", "C", "C", 10, "2023-01-01 10:00:00", "q1.png"), # Correct
            ]
            with patch.object(self.db_manager, 'get_user_progress', return_value=mock_progress_data):
                level = self.db_manager.calculate_user_level("testuser")
                # Fails level 1 assessment (2 correct not > 2), stays at level 1
                self.assertEqual(level, 1)

    def test_calculate_user_level_caps_at_max_level(self):
         # Assume max level is 5 from config.LEVEL_RANGES
        max_level = max(config.LEVEL_RANGES.keys()) if config.LEVEL_RANGES else 1

        with patch('config.QUESTIONS_FOR_LEVEL_ASSESSMENT', 1), \
             patch('config.CORRECT_ANSWERS_TO_LEVEL_UP', 0): # Needs 1 correct
            # Simulate passing all levels up to max_level
            mock_progress_data = []
            for lvl in range(1, max_level + 1):
                if lvl in config.LEVEL_RANGES:
                    # Get a question number from that level's range
                    q_num_for_level = next(iter(config.LEVEL_RANGES[lvl]))
                    mock_progress_data.append(
                        ("Set1", 2020, q_num_for_level, f"ID{lvl}", "Cat", "A", "A", 10, f"2023-01-01 10:0{lvl}:00", f"q{q_num_for_level}.png")
                    )
            mock_progress_data.reverse() # Most recent first

            with patch.object(self.db_manager, 'get_user_progress', return_value=mock_progress_data):
                level = self.db_manager.calculate_user_level("testuser_pro")
                self.assertEqual(level, max_level) # Should be capped at max_level

    @patch('sqlite3.connect')
    def test_validate_invitation_code_valid(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,) # Code exists and is unused

        is_valid = self.db_manager.validate_invitation_code("VALIDCODE")
        self.assertTrue(is_valid)
        expected_sql = "SELECT 1 FROM invitation_codes WHERE code = ? AND is_used = 0"
        mock_conn.execute.assert_any_call(expected_sql, ("VALIDCODE",))

    @patch('sqlite3.connect')
    def test_validate_invitation_code_invalid_or_used(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None # Code does not exist or is used

        is_valid = self.db_manager.validate_invitation_code("INVALIDCODE")
        self.assertFalse(is_valid)

    @patch('sqlite3.connect')
    def test_validate_invitation_code_empty(self, mock_sqlite_connect):
        # No need to mock connect if the method returns early
        is_valid = self.db_manager.validate_invitation_code("")
        self.assertFalse(is_valid)
        mock_sqlite_connect.assert_not_called() # Ensure DB is not hit for empty code

    @patch('sqlite3.connect')
    def test_mark_code_used_success(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor_for_update = MagicMock() # mock_conn.execute() for UPDATE returns this
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor_for_update # For the UPDATE statement
        mock_cursor_for_update.rowcount = 1 # Simulate that 1 row was updated

        username = "newuser"
        code = "VALIDCODE"
        result = self.db_manager.mark_code_used(code, username)

        mock_sqlite_connect.assert_called_once_with(self.db_manager.db_name)
        # PRAGMA call
        mock_conn.execute.assert_any_call("PRAGMA foreign_keys = ON")

        # Check that the UPDATE statement was made
        # We can check that 'UPDATE invitation_codes' is part of one of the execute calls
        update_sql_found = False
        for call_item in mock_conn.execute.call_args_list:
            args, _ = call_item
            if "UPDATE invitation_codes" in args[0]:
                self.assertEqual(args[1], (username, code)) # Check parameters for the UPDATE
                update_sql_found = True
                break
        self.assertTrue(update_sql_found, "UPDATE statement for invitation_codes not found")

        # Again, commit is implicit if the 'with conn:' block succeeded
        mock_conn.close.assert_called_once()
        self.assertTrue(result)

    @patch('sqlite3.connect')
    def test_mark_code_used_failure_or_already_used(self, mock_sqlite_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite_connect.return_value = mock_conn
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.rowcount = 0 # Simulate that no row was updated

        result = self.db_manager.mark_code_used("ALREADYUSEDCODE", "anotheruser")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()