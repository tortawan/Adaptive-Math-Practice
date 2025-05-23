# main.py
"""
Main Application Entry Point.

This script initializes and runs the Adaptive Math Practice application.
It sets up necessary paths, configures logging (basic), handles DPI awareness
for Windows, and launches the main login window.
"""
import tkinter as tk
from tkinter import messagebox
import logging
import sys
import os

# Ensure the script's directory is in the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import the main application window class
try:
    from login_window import LoginApp
except ImportError as e:
    logging.critical(f"Fatal Error: Could not import LoginApp from login_window: {e}", exc_info=True)
    # Attempt to show a Tkinter error message if Tkinter itself is available
    try:
        root = tk.Tk()
        root.withdraw() # Hide the main Tk window
        messagebox.showerror("Startup Error", f"Failed to load application components (login_window.py missing or corrupted):\n{e}\n\nPlease ensure all .py files are correctly placed.")
        root.destroy()
    except Exception as tk_e:
         print(f"Tkinter error reporting failed during startup error: {tk_e}") # Fallback to console
    sys.exit(1)

# Configure basic logging
# For a more advanced setup, you might have a separate logging_config.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()] # Outputs to console
)
# Example: Add file logging
# logging.getLogger().addHandler(logging.FileHandler("app.log"))


# ==============================================================================
# Main Execution
# ==============================================================================
if __name__ == "__main__":
    # DPI awareness setting for Windows (helps with UI scaling on high-DPI screens)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
        logging.info("Successfully set DPI awareness for Windows.")
    except ImportError:
        logging.info("Could not import ctypes (not on Windows or not available), skipping DPI awareness setting.")
    except Exception as e:
        logging.warning(f"Could not set DPI awareness: {e}")

    logging.info("Starting Adaptive Math Practice application...")
    try:
        app = LoginApp()
        app.mainloop()
        logging.info("Application closed normally.")
    except Exception as e:
        logging.critical(f"Fatal error during main application execution: {e}", exc_info=True)
        try:
            # Attempt to show a Tkinter error for fatal runtime errors
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Runtime Error", f"Application encountered a fatal error:\n{e}\n\nCheck logs or console for details.")
            root.destroy()
        except Exception as tk_e:
            print(f"Tkinter error reporting failed during fatal runtime error handling: {tk_e}")
        sys.exit(1)