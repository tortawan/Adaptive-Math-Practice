# config.py
"""
Application Configuration.

This module centralizes all configuration variables for the Adaptive Math
Practice application. It loads sensitive keys from a .env file and defines
constants for application behavior, UI, AI, difficulty levels, and static content.

To use AI features, create a '.env' file in the root directory with your
GOOGLE_API_KEY:
    GOOGLE_API_KEY=AIz...Your...Key...Here
Ensure '.env' is added to your .gitignore file.
"""
import os
import json
from dotenv import load_dotenv
# from cryptography.fernet import Fernet # Keep if using encrypted file method as an alternative

# Load variables from .env file.
load_dotenv()

# --- Application Constants ---
APP_TITLE = "Adaptive Math Practice"
WINDOW_SIZE = "1200x800"
IMAGE_WINDOW_SIZE = "1600x1000" # For the main practice window
PROGRESS_WINDOW_SIZE = "1400x1000" # For the progress review window
DATABASE_NAME = "app_database.db"
TIMER_DURATION = 150 # seconds
IMAGE_DISPLAY_SIZE = (1200, 1200) # Max size for displaying question images in main view
OPTION_LETTERS = ["A", "B", "C", "D", "E"]

# --- AI Configuration ---
# Name of the Google Generative AI model to use (used in ai_helper.py)
AI_MODEL_NAME = 'gemini-2.0-flash-exp' # Example: 'gemini-1.5-flash-latest' or specific version

# --- Difficulty Levels ---
# Defines the question number ranges for each difficulty level (inclusive start, exclusive end)
LEVEL_RANGES = {
    1: range(1, 6),   # Level 1: Questions 1-5
    2: range(6, 11),  # Level 2: Questions 6-10
    3: range(11, 16), # Level 3: Questions 11-15
    4: range(16, 21), # Level 4: Questions 16-20
    5: range(21, 26)  # Level 5: Questions 21-25
}
# Level assessment parameters
QUESTIONS_FOR_LEVEL_ASSESSMENT = 25 # How many recent questions *at a specific level* are considered
CORRECT_ANSWERS_TO_LEVEL_UP = 21 # How many correct answers needed *out of* assessment count (e.g., >21 means 22+)

# --- Secure API Key Loading ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Debug print (useful during development)
# print(f"--- Debug: config.py trying to load GOOGLE_API_KEY ---") # Keep for dev if needed

if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY environment variable not set or empty.")
    print("         AI features will be disabled. Create a '.env' file with GOOGLE_API_KEY=YOUR_KEY.")
else:
    print(f"--- Debug: config.py loaded GOOGLE_API_KEY starting with '{GOOGLE_API_KEY[:4]}...' ---")


# --- Static Content ---
MOTIVATIONAL_PHRASES = [
    "Practice makes perfect. - Benjamin Franklin",
    "Practice puts brains in your muscles. - Sam Snead",
    "Everything is practice. - Pele",
    "Champions keep playing until they get it right. - Billie Jean King",
    "An ounce of practice is worth more than tons of preaching. - Mahatma Gandhi",
    "Knowledge is of no value unless you put it into practice. - Anton Chekhov",
    "The only way to learn mathematics is to do mathematics. - Paul Halmos",
    "Success is the sum of small efforts, repeated day in and day out. - Robert Collier",
    "Don't practice until you get it right. Practice until you can't get it wrong. - Unknown",
    "The journey of a thousand miles begins with a single step. - Lao Tzu",
    "Believe you can and you're halfway there. - Theodore Roosevelt",
    "It does not matter how slowly you go as long as you do not stop. - Confucius",
    "The expert in anything was once a beginner.",
    "Mistakes are proof that you are trying.",
    "Every problem is a chance for you to do your best.",
    "The more you practice, the luckier you get. - Gary Player (adapted)",
    "Persistence guarantees that results are inevitable. - Paramahansa Yogananda",
    "You don't have to be great to start, but you have to start to be great. - Zig Ziglar",
    "Challenges are what make life interesting. Overcoming them is what makes life meaningful. - Joshua Marine",
    "The best way to predict the future is to create it. - Peter Drucker",
    "The more you practice, the more you realize that success is a journey, not a destination."
]

# --- Sound Files ---
# Uses Windows specific system sound aliases.
# For cross-platform use, consider libraries like 'playsound' or 'simpleaudio' and actual sound files.
HEARTBEAT_SOUND = "SystemHand"      # Typically a short, soft sound
WARNING_SOUND = "SystemExclamation" # Typically a more alerting sound

# --- Optional: Encrypted File Loading Logic (If not using .env) ---
# (Keep this section commented out if you prefer the .env method)
# ENCRYPTION_KEY_PATH = "secret.key" # Ensure this key is secured (e.g., via env var itself!)
# ENCRYPTED_CONFIG_PATH = "config.enc"
#
# def load_encryption_key(path=ENCRYPTION_KEY_PATH):
#     # Best practice: Load this base key from an environment variable
#     # base_key = os.getenv("APP_ENCRYPTION_KEY")
#     # if not base_key: return None # Handle error
#     # return base_key.encode() # Assuming env var holds the key directly
#     try:
#         with open(path, 'rb') as key_file:
#             return key_file.read()
#     except FileNotFoundError:
#         print(f"Error: Encryption key file not found at {path}")
#         return None
#
# def load_decrypted_api_keys(key_path=ENCRYPTION_KEY_PATH, config_path=ENCRYPTED_CONFIG_PATH):
#     key = load_encryption_key(key_path)
#     if not key: return {}
#     cipher = Fernet(key)
#     try:
#         with open(config_path, 'r') as config_file:
#             encrypted_api_keys = json.load(config_file)
#         # Ensure keys exist in the decrypted dict, even if None
#         decrypted_keys = {"GOOGLE_API_KEY": None}
#         for k, v in encrypted_api_keys.items():
#             try:
#                 decrypted_keys[k] = cipher.decrypt(v.encode()).decode()
#             except Exception as decrypt_error:
#                 print(f"Error decrypting key '{k}': {decrypt_error}")
#         return decrypted_keys
#     except (FileNotFoundError, json.JSONDecodeError) as e:
#         print(f"Error loading/decrypting API keys file: {e}")
#         return {"GOOGLE_API_KEY": None} # Return default structure on error
#
# # If using encrypted file method, uncomment below and comment out os.getenv above
# # decrypted_keys = load_decrypted_api_keys()
# # GOOGLE_API_KEY = decrypted_keys.get("GOOGLE_API_KEY")
# # if not GOOGLE_API_KEY:
# #     print("WARNING: GOOGLE_API_KEY not found or failed to decrypt. AI features disabled.")

# Final debug print to confirm script execution finished
# print(f"--- Debug: config.py finished loading ---")