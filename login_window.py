# login_window.py
"""
Login and Practice Set Selection Window.

This module defines the main login window for the Adaptive Math Practice
application. It handles user authentication, registration (via gui_components),
and allows logged-in users to select a practice set (e.g., "AMC" folders)
and a question selection method before starting a practice session.
"""
import os
import random
import tkinter as tk
from tkinter import Tk, Label, Entry, Button, Frame, messagebox, Toplevel
from tkinter import ttk
import logging
import json

# --- Project Modules ---
import config
from db_manager import DatabaseManager
from auth_utils import verify_password
from gui_components import RegistrationWindow
# For a showcase, ensure practice_window and ImageWindow are available
from practice_window import ImageWindow


# ==============================================================================
# Login Application Class
# ==============================================================================
class LoginApp(Tk):
    """Main application class handling login and practice set selection."""
    def __init__(self):
        super().__init__()
        # Initialize database manager early
        self.db_manager = DatabaseManager(config.DATABASE_NAME)
        # Ensure tables exist (idempotent call within db_manager init)

        self.phrases = config.MOTIVATIONAL_PHRASES
        self.image_window = None # Reference to the main ImageWindow (Practice Window)

        self.setup_window()
        self.create_widgets()
        self._center_on_screen() # Center the main login window

    def setup_window(self):
        self.title(f"{config.APP_TITLE} - Login")
        self.geometry(config.WINDOW_SIZE)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """Creates the initial login widgets."""
        # Destroy existing widgets if any (e.g., if returning to this screen)
        for widget in self.winfo_children():
            widget.destroy()

        login_frame = Frame(self, padx=20, pady=20)
        login_frame.pack(expand=True)

        # Username/Password fields
        Label(login_frame, text="Username:", font=("Helvetica", 14)).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.username_entry = Entry(login_frame, font=("Helvetica", 14), width=30)
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)
        self.username_entry.focus_set() # Set focus on username entry

        Label(login_frame, text="Password:", font=("Helvetica", 14)).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.password_entry = Entry(login_frame, show="*", font=("Helvetica", 14), width=30)
        self.password_entry.grid(row=1, column=1, padx=10, pady=10)

        # Frame for buttons
        buttons_frame = Frame(login_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=20)

        # Login Button
        Button(buttons_frame, text="Login", command=self.login, font=("Helvetica", 14, "bold"), width=12, height=1).pack(side=tk.LEFT, padx=10)

        # Register Button
        Button(buttons_frame, text="Register", command=self.open_registration_window, font=("Helvetica", 14), width=12, height=1).pack(side=tk.LEFT, padx=10)

        # Bind Enter key to login for convenience in both entry fields
        self.username_entry.bind('<Return>', lambda event=None: self.login())
        self.password_entry.bind('<Return>', lambda event=None: self.login())

    def login(self):
        username = self.username_entry.get().strip() # Strip whitespace
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Login Failed", "Please enter both username and password.", parent=self)
            return

        stored_hash = self.db_manager.get_user_hash(username)

        # Call verify_password with the retrieved hash and entered password
        if stored_hash and verify_password(stored_hash, password):
            logging.info(f"User '{username}' logged in successfully.")
            # Clear login frame and show next step
            for widget in self.winfo_children():
                widget.destroy() # Clear the login frame widgets
            self.show_folder_dropdown(username)
        else:
            logging.warning(f"Failed login attempt for user '{username}'.")
            messagebox.showerror("Login Failed", "Incorrect username or password.", parent=self)
            self.password_entry.delete(0, tk.END) # Clear password field on failure
            self.password_entry.focus_set() # Set focus back to password

    def open_registration_window(self):
        # Create and show the registration window (imported from gui_components)
        RegistrationWindow(self, self.db_manager)

    def show_folder_dropdown(self, username):
        """Shows the screen for selecting a practice set folder."""
        # Find folders starting with "AMC" in the application's directory
        amc_dirs = []
        app_dir = ""
        try:
            # Use __file__ which is generally more reliable
            app_dir = os.path.dirname(os.path.abspath(__file__))
            all_items = os.listdir(app_dir)
            # Filter for directories starting with "AMC" (case-insensitive check might be better)
            amc_dirs = sorted([d for d in all_items if os.path.isdir(os.path.join(app_dir, d)) and d.upper().startswith("AMC")])
        except FileNotFoundError:
            messagebox.showerror("Error", f"Cannot list directories in the application folder: {app_dir}", parent=self)
        except Exception as e:
            logging.error(f"Error listing directories in '{app_dir}': {e}", exc_info=True)
            messagebox.showerror("Error", f"Error listing directories: {e}", parent=self)

        selection_frame = Frame(self, padx=20, pady=20)
        selection_frame.pack(expand=True)

        if not amc_dirs:
            messagebox.showwarning("No Practice Sets Found", f"No folders starting with 'AMC' found in the application directory:\n{app_dir}\n\nPlease create some practice set folders.", parent=self)
            # Provide an exit button if no sets are found
            Button(selection_frame, text="Exit", command=self.destroy, font=("Helvetica", 14), width=12).pack(pady=20)
            return # Stop here if no folders

        Label(selection_frame, text="Select Practice Set:", font=("Helvetica", 14)).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.folder_dropdown = ttk.Combobox(selection_frame, values=amc_dirs, state="readonly", font=("Helvetica", 12), width=30)
        self.folder_dropdown.grid(row=0, column=1, padx=10, pady=10)
        if amc_dirs: # Avoid error if list is empty
             self.folder_dropdown.current(0) # Select first one by default

        Label(selection_frame, text="Question Selection:", font=("Helvetica", 14)).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.method_dropdown = ttk.Combobox(selection_frame, values=["Random", "AI Selection"], state="readonly", font=("Helvetica", 12), width=30)
        self.method_dropdown.set("AI Selection") # Default to adaptive
        self.method_dropdown.grid(row=1, column=1, padx=10, pady=10)

        Button(selection_frame, text="Start Practice", command=lambda: self.load_metadata_and_start(username), font=("Helvetica", 14, "bold"), width=15, height=2).grid(row=2, column=0, columnspan=2, pady=20)


    # NEW: Function to load metadata before starting the practice window
    def load_metadata_and_start(self, username):
        """Loads metadata.json for the selected folder and starts the practice window."""
        selected_folder = self.folder_dropdown.get()
        question_method = self.method_dropdown.get()

        if not selected_folder:
            messagebox.showwarning("No Practice Set Selected", "Please select a practice set folder.", parent=self)
            return

        # Construct full path based on app location
        app_dir = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(app_dir, selected_folder)

        if not os.path.isdir(folder_path):
            messagebox.showerror("Error", f"Selected folder '{selected_folder}' not found at expected location:\n{folder_path}", parent=self)
            return

        # --- Load metadata.json ---
        metadata_path = os.path.join(folder_path, "metadata.json")
        questions_data = []
        if not os.path.exists(metadata_path):
             messagebox.showerror("Metadata Error", f"Required file 'metadata.json' not found in folder:\n{selected_folder}", parent=self)
             return
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            # Basic validation
            if not isinstance(metadata, dict) or 'questions' not in metadata or not isinstance(metadata['questions'], list):
                 raise ValueError("Invalid metadata structure: 'questions' list not found.")
            questions_data = metadata['questions']
            if not questions_data:
                 raise ValueError("Metadata file contains no questions.")

            # Validate that image files exist and add full path
            valid_questions = []
            missing_files = []
            for q_dict in questions_data:
                if not isinstance(q_dict, dict) or 'image_filename' not in q_dict:
                     logging.warning(f"Skipping invalid question entry in metadata: {q_dict}")
                     continue
                img_file = q_dict['image_filename']
                img_path = os.path.join(folder_path, img_file)
                if os.path.isfile(img_path):
                     q_dict['full_image_path'] = img_path # Add full path for convenience
                     valid_questions.append(q_dict)
                else:
                     missing_files.append(img_file)

            if missing_files:
                 messagebox.showwarning("Missing Images", f"The following image files listed in metadata.json were not found in '{selected_folder}':\n" + "\n".join(missing_files), parent=self)
                 # Decide if you want to proceed with only the valid ones or stop
                 # For now, let's proceed if at least some are valid
                 # return

            if not valid_questions:
                 messagebox.showerror("No Valid Questions", f"No valid questions found in '{selected_folder}' after checking metadata and image files.", parent=self)
                 return

            questions_data = valid_questions # Use only the questions with existing images

        except json.JSONDecodeError as e:
             messagebox.showerror("Metadata Error", f"Error parsing 'metadata.json' in '{selected_folder}':\n{e}", parent=self)
             return
        except ValueError as e:
             messagebox.showerror("Metadata Error", f"Error in 'metadata.json' structure in '{selected_folder}':\n{e}", parent=self)
             return
        except Exception as e:
             logging.error(f"Error loading metadata for '{selected_folder}': {e}", exc_info=True)
             messagebox.showerror("Error", f"Could not load metadata for '{selected_folder}': {e}", parent=self)
             return
        # --- End Metadata Loading ---


        # Proceed to open the main practice window
        self.withdraw() # Hide the login/selection window
        window_title = f"{config.APP_TITLE} - {username} - {random.choice(self.phrases)}"
        # MODIFIED: Pass questions_data (list of dicts) instead of image_files
        self.image_window = ImageWindow(self, folder_path, questions_data, window_title, username,
                                        selected_folder, question_method, self.db_manager)


    def _center_on_screen(self):
        """Centers the main Tk window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def on_closing(self):
        """Handles closing the main application window."""
        logging.info("Closing application.")
        # Ensure child windows are also closed
        if self.image_window and self.image_window.winfo_exists():
            # ImageWindow's on_closing should handle its own children
            self.image_window.destroy()
        self.destroy()

