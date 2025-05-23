# -*- coding: utf-8 -*-
"""
Authentication Utilities.

This module provides helper functions for password management, including
hashing new passwords and verifying provided passwords against stored hashes
using bcrypt.
"""

# auth_utils.py
import bcrypt

def hash_password(password: str) -> str:
    """
    Hashes the password using bcrypt.

    Args:
        password (str): The plain text password to hash.

    Returns:
        str: The bcrypt hashed password, decoded to UTF-8.
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8') # Store hash as string in DB

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """
    Verifies a provided password against a stored bcrypt hash.

    Args:
        stored_hash (str): The bcrypt hashed password retrieved from storage.
        provided_password (str): The plain text password provided by the user.

    Returns:
        bool: True if the provided password matches the hash, False otherwise.
    """
    if not stored_hash: # Handle cases where user might not exist or hash is empty
        return False
    stored_hash_bytes = stored_hash.encode('utf-8')
    provided_password_bytes = provided_password.encode('utf-8')
    return bcrypt.checkpw(provided_password_bytes, stored_hash_bytes)