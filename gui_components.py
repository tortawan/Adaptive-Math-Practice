# gui_components.py
"""
GUI Components Module.

This module defines reusable Tkinter GUI components, such as the user
registration window. These components are designed to be integrated into
the main application windows.
"""
import tkinter as tk
from tkinter import Toplevel, Frame, Label, Entry, Button, messagebox
import logging

# Assuming db_manager and auth_utils are in the same project structure
# For a showcase, it's better to rely on these being present.
# If there's an ImportError, it indicates a setup problem for the user to fix.
from db_manager import DatabaseManager
from auth_utils import hash_password


class RegistrationWindow(Toplevel):
    # ... (rest of the RegistrationWindow class) ...
    # Docstrings and comments are good.
    # The password validation (length) is a good example.
    # Consider adding a small note in the password validation like:
    # # TODO: Consider adding more complexity checks (e.g., uppercase, number, symbol)
    # This shows awareness of potential improvements.
    """Toplevel window for user registration."""
    def __init__(self, parent, db_manager: DatabaseManager):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager

        self.title("Register New User")
        self.geometry("400x300") # Adjust size as needed
        self.resizable(False, False)
        self.grab_set() # Make window modal
        self.transient(parent) # Associate with parent window

        self.create_widgets()
        self.center_window()
        self.username_entry.focus_set() # Focus on the first entry field

    def create_widgets(self):
        reg_frame = Frame(self, padx=20, pady=20)
        reg_frame.pack(expand=True)

        Label(reg_frame, text="Username:", font=("Helvetica", 12)).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.username_entry = Entry(reg_frame, font=("Helvetica", 12), width=25)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)

        Label(reg_frame, text="Password:", font=("Helvetica", 12)).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.password_entry = Entry(reg_frame, show="*", font=("Helvetica", 12), width=25)
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)

        Label(reg_frame, text="Confirm Password:", font=("Helvetica", 12)).grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.confirm_password_entry = Entry(reg_frame, show="*", font=("Helvetica", 12), width=25)
        self.confirm_password_entry.grid(row=2, column=1, padx=5, pady=5)

        # Add password requirement label (optional)
        Label(reg_frame, text="Min 8 characters", font=("Helvetica", 9), fg="grey").grid(row=3, column=1, sticky="w", padx=5)

        Button(reg_frame, text="Register", command=self.register_user, font=("Helvetica", 12, "bold"), width=15).grid(row=4, column=0, columnspan=2, pady=15)

        # Bind Enter key in password fields to register action
        self.password_entry.bind('<Return>', lambda event=None: self.register_user())
        self.confirm_password_entry.bind('<Return>', lambda event=None: self.register_user())

    def register_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        # --- Validation ---
        if not username or not password or not confirm_password:
            messagebox.showerror("Registration Error", "All fields are required.", parent=self)
            return

        if password != confirm_password:
            messagebox.showerror("Registration Error", "Passwords do not match.", parent=self)
            self.password_entry.delete(0, tk.END)
            self.confirm_password_entry.delete(0, tk.END)
            self.password_entry.focus_set()
            return

        # Optional: Password Complexity (Example: minimum length)
        if len(password) < 8:
            messagebox.showerror("Registration Error", "Password must be at least 8 characters long.", parent=self)
            return
        # TODO: Add more checks here (uppercase, number, symbol) if desired using regex or string checks

        # Check if username already exists
        if self.db_manager.get_user_hash(username) is not None:
            messagebox.showerror("Registration Error", f"Username '{username}' is already taken. Please choose another.", parent=self)
            self.username_entry.focus_set()
            return

        # --- Hashing and Saving ---
        try:
            hashed_pw = hash_password(password) # Use the imported function
            success = self.db_manager.add_user(username, hashed_pw)

            if success:
                messagebox.showinfo("Registration Successful", f"User '{username}' created successfully.\nYou can now log in.", parent=self.parent) # Show relative to login window
                self.destroy() # Close registration window on success
            else:
                # db_manager logs specific DB errors now
                messagebox.showerror("Registration Failed", "Could not create user due to a database error. Check logs for details.", parent=self)

        except Exception as e:
            logging.error(f"Error during hashing or saving user '{username}': {e}", exc_info=True)
            messagebox.showerror("Registration Failed", f"An unexpected error occurred: {e}", parent=self)

    def center_window(self):
        """Centers this Toplevel window relative to its parent."""
        self.update_idletasks()
        try:
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_w = self.parent.winfo_width()
            parent_h = self.parent.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            # Calculate position, ensuring it's on screen
            x = max(0, parent_x + (parent_w // 2) - (w // 2))
            y = max(0, parent_y + (parent_h // 2) - (h // 2))
            self.geometry(f'{w}x{h}+{x}+{y}')
        except tk.TclError:
            # Fallback if parent window info isn't available yet
            self.geometry(f'+{self.winfo_screenwidth()//2 - self.winfo_width()//2}+{self.winfo_screenheight()//2 - self.winfo_height()//2}')

