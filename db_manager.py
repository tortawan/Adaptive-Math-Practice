# -*- coding: utf-8 -*-
"""
Database Management Module.

This module handles all database interactions for the Adaptive Math Practice
application using SQLite. It includes creating tables, adding users,
retrieving user data, saving and fetching user progress, and calculating
user proficiency levels. It also manages invitation codes for registration.
"""

# db_manager.py
import sqlite3
import time
import config # Use constants from config
import logging

# Configure basic logging
# Consider moving this to a central logging setup in main.py or a setup_logging.py
# if you want more control across the application (e.g., file logging).
# For now, this is fine here.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self, db_name: str = config.DATABASE_NAME):
        """Initializes the DatabaseManager and ensures tables exist."""
        self.db_name = db_name
        self.create_tables()

    def _get_connection(self) -> sqlite3.Connection | None:
        """
        Establishes a database connection.
        Returns the connection object or None if connection fails.
        """
        try:
            conn = sqlite3.connect(self.db_name)
            # Optional: Enable foreign key constraints if needed (helps data integrity)
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except sqlite3.Error as e:
            logging.error(f"Database connection error to '{self.db_name}': {e}", exc_info=True)
            return None

    def create_tables(self):
        """Creates necessary database tables if they don't already exist."""
        query_users = """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL -- Stores bcrypt hash
            )
        """
        # MODIFIED: Added set_identifier, image_filename, removed redundant folder_name if category/set is there
        query_progress = """
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                year INTEGER,
                question_number INTEGER,
                set_identifier TEXT, -- e.g., '8', '10A', '12B'
                category TEXT, -- e.g., 'Algebra', 'Geometry'
                user_choice TEXT,
                correct_choice TEXT,
                answer_time INTEGER, -- Time in seconds
                attempt_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                image_filename TEXT, -- Store the image filename for easier review lookup
                folder_name TEXT, -- Keep folder name for context/grouping progress
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            )
        """
        query_index = """
            CREATE INDEX IF NOT EXISTS idx_user_progress_username_date
            ON user_progress (username, attempt_date DESC);
        """ # Index for faster progress retrieval per user, sorted by date

        # --- Invitation Code Tables (Keep from previous change) ---
        query_invitation_codes = """
            CREATE TABLE IF NOT EXISTS invitation_codes (
                code TEXT PRIMARY KEY NOT NULL,
                is_used INTEGER DEFAULT 0, -- 0=false (default), 1=true
                date_generated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_by_username TEXT,
                used_date TIMESTAMP
            )
        """
        query_code_index = """
            CREATE INDEX IF NOT EXISTS idx_invitation_codes_unused
            ON invitation_codes (is_used, code);
        """
        # --- End Invitation Code Tables ---


        conn = self._get_connection()
        if not conn:
            logging.error("Cannot create tables: Database connection failed.")
            return

        try:
            with conn: # Use context manager for automatic commit/rollback
                cursor = conn.cursor()
                cursor.execute(query_users)
                cursor.execute(query_progress)
                cursor.execute(query_index)
                cursor.execute(query_invitation_codes) # Execute invitation code query
                cursor.execute(query_code_index)      # Execute invitation code index query
            # logging.info("Database tables checked/created successfully.")
        except sqlite3.Error as e:
            logging.error(f"Database error creating tables: {e}", exc_info=True)
        finally:
            conn.close()

    def add_user(self, username: str, hashed_password: str) -> bool:
        """
        Adds a new user or replaces the password if the user already exists.
        Consider using INSERT OR IGNORE or checking existence first if replacement is not desired.
        Returns True on success, False on failure.
        """
        query = "INSERT OR REPLACE INTO users (username, password) VALUES (?, ?)"
        conn = self._get_connection()
        if not conn:
            return False

        success = False
        try:
            with conn:
                conn.execute(query, (username, hashed_password))
            # logging.info(f"User '{username}' added or replaced successfully.") # Optional success log
            success = True
        except sqlite3.Error as e:
            logging.error(f"Database error adding/replacing user '{username}': {e}", exc_info=True)
        finally:
            conn.close()
        return success

    def get_user_hash(self, username: str) -> str | None:
        """Retrieves the stored password hash for a user. Returns hash or None."""
        query = "SELECT password FROM users WHERE username = ?"
        conn = self._get_connection()
        if not conn:
            return None

        user_hash = None
        try:
            with conn:
                cursor = conn.execute(query, (username,))
                result = cursor.fetchone()
                if result:
                    user_hash = result[0]
        except sqlite3.Error as e:
            logging.error(f"Database error getting hash for user '{username}': {e}", exc_info=True)
        finally:
            conn.close()
        return user_hash

    # MODIFIED: Signature changed to accept specific metadata fields
    def save_user_progress(self, username: str, folder_name: str, year: int | None, question_number: int | None,
                           set_identifier: str | None, category: str | None, image_filename: str | None,
                           user_choice: str, correct_choice: str, answer_time: int) -> bool:
        """
        Saves a user's attempt for a specific question using provided metadata.
        Returns True on success, False on failure.
        """
        query = """
            INSERT INTO user_progress (username, folder_name, year, question_number, set_identifier,
                                       category, user_choice, correct_choice, answer_time, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        conn = self._get_connection()
        if not conn:
            return False

        success = False
        try:
            with conn:
                conn.execute(query, (username, folder_name, year, question_number, set_identifier,
                                     category, user_choice, correct_choice, answer_time, image_filename))
            success = True
        except sqlite3.Error as e:
            log_id = f"Q#{question_number}" if question_number else f"Img:{image_filename}"
            logging.error(f"Database error saving progress for user '{username}', {log_id} in '{folder_name}': {e}", exc_info=True)
        finally:
            conn.close()
        return success

    # MODIFIED: Select statement updated to match new column order/names
    def get_user_progress(self, username: str) -> list[tuple]:
        """
        Retrieves all progress entries for a user, ordered by most recent first.
        Returns a list of tuples, or an empty list on error/no data.
        """
        query = """
            SELECT folder_name, year, question_number, set_identifier, category,
                   user_choice, correct_choice, answer_time, attempt_date, image_filename
            FROM user_progress
            WHERE username = ?
            ORDER BY attempt_date DESC
        """
        conn = self._get_connection()
        if not conn:
            return []

        progress_data = []
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, (username,))
                progress_data = cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Database error retrieving progress for user '{username}': {e}", exc_info=True)
        finally:
            conn.close()
        return progress_data

    # MODIFIED: Uses question_number directly from fetched progress data (Index 2)
    def calculate_user_level(self, username: str) -> int:
        """
        Calculates the user's current level based on recent performance across defined levels.
        Starts at level 1. Moves up if performance criteria are met for a level.
        """
        user_progress = self.get_user_progress(username) # Already sorted DESC by date
        if not user_progress:
            return 1 # Start at level 1 if no history

        highest_level_passed = 0 # Start below level 1
        num_levels = len(config.LEVEL_RANGES)

        # Iterate through levels defined in config
        for level in range(1, num_levels + 1):
            # Check if level definition exists
            if level not in config.LEVEL_RANGES:
                logging.warning(f"Level {level} not found in config.LEVEL_RANGES during level calculation.")
                continue

            level_range = config.LEVEL_RANGES[level]

            # Filter attempts relevant to the current level being assessed
            # MODIFIED: Index 2 is question_number based on get_user_progress SELECT
            level_attempts = [
                attempt for attempt in user_progress
                if attempt[2] is not None and attempt[2] in level_range
            ]

            # Check if enough attempts exist *at this level* for assessment
            if len(level_attempts) >= config.QUESTIONS_FOR_LEVEL_ASSESSMENT:
                # Take the most recent attempts for this level
                recent_attempts_at_level = level_attempts[:config.QUESTIONS_FOR_LEVEL_ASSESSMENT]

                # Count correct answers (index 5: user_choice, index 6: correct_choice)
                correct_count = sum(1 for attempt in recent_attempts_at_level
                                    if attempt[5] is not None and attempt[5] == attempt[6])

                # Check if user passed this level based on config threshold
                if correct_count > config.CORRECT_ANSWERS_TO_LEVEL_UP:
                    highest_level_passed = level # User mastered this level
                else:
                    # User did not meet criteria for this level. Their current working level
                    # is one above the last level they *did* pass. Stop checking higher levels.
                    break
            else:
                # Not enough attempts at this level to assess mastery.
                # User's current working level is one above the last level passed. Stop here.
                break

        # User's current working level is one above the highest they passed, capped at max level
        current_level = min(highest_level_passed + 1, num_levels)
        # logging.info(f"Calculated level for user '{username}': {current_level} (Highest passed: {highest_level_passed})")
        return current_level

    # --- Invitation Code Methods (Keep from previous change) ---
    def validate_invitation_code(self, code: str) -> bool:
        """Checks if an invitation code exists and is unused."""
        if not code:
            return False
        query = "SELECT 1 FROM invitation_codes WHERE code = ? AND is_used = 0"
        conn = self._get_connection()
        if not conn:
            return False

        is_valid = False
        try:
            with conn:
                cursor = conn.execute(query, (code,))
                result = cursor.fetchone()
                if result:
                    is_valid = True
        except sqlite3.Error as e:
            logging.error(f"Database error validating code '{code}': {e}", exc_info=True)
        finally:
            conn.close()
        logging.info(f"Validation result for code '{code}': {is_valid}")
        return is_valid

    def mark_code_used(self, code: str, username: str) -> bool:
        """Marks an invitation code as used by a specific user."""
        if not code or not username:
            return False
        query = """
            UPDATE invitation_codes
            SET is_used = 1, used_by_username = ?, used_date = CURRENT_TIMESTAMP
            WHERE code = ? AND is_used = 0
        """
        conn = self._get_connection()
        if not conn:
            return False

        success = False
        try:
            with conn:
                cursor = conn.execute(query, (username, code))
                # Check if any row was actually updated (means code was valid and unused)
                if cursor.rowcount > 0:
                    success = True
                    logging.info(f"Successfully marked code '{code}' as used by '{username}'.")
                else:
                    # This case might happen in a race condition, or if code was already used
                    logging.warning(f"Failed to mark code '{code}' as used for '{username}'. It might have been already used or invalid.")

        except sqlite3.Error as e:
            logging.error(f"Database error marking code '{code}' used by '{username}': {e}", exc_info=True)
        finally:
            conn.close()
        return success
    # --- End Invitation Code Methods ---
