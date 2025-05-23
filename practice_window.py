# practice_window.py
"""
Practice Session Window.

This module defines the `ImageWindow` class, which is the core interface for
a user's practice session. It handles:
- Displaying math question images.
- Managing a timer for each question.
- Presenting multiple-choice options.
- Selecting questions based on chosen method (random or AI-adaptive).
- Saving user progress to the database.
- Displaying overall user progress in a sortable table.
- Showing detailed views of past questions with AI-generated explanations,
  including rendering LaTeX as images.
"""
import os
import random
import json
import threading
import time
import tkinter as tk
from tkinter import (Label, Button, Frame, IntVar, Checkbutton, messagebox,
                     Toplevel, Text, Canvas, scrolledtext)
from tkinter import ttk
from tkinter import font as tkFont
import requests
import io
from PIL import Image, ImageTk, UnidentifiedImageError
import winsound # For sounds on Windows
import queue
from datetime import datetime
import logging
import re

# --- Project Modules ---
import config
from db_manager import DatabaseManager
from ai_helper import get_solution as get_ai_solution, AI_ENABLED
from latex_utils import find_latex_segments, get_codecogs_url, download_image_data, PLACEHOLDER_FORMAT

# ==============================================================================
# Main Image Display Window Class
# ==============================================================================
class ImageWindow(Toplevel):
    """Main window for displaying questions and handling user interaction."""
    def __init__(self, parent: tk.Tk, folder_path: str, questions_data: list[dict], window_title: str, username: str,
                 folder_name: str, question_method: str, db_manager: DatabaseManager):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.username = username
        self.folder_name = folder_name
        self.folder_path = folder_path
        self.question_selection_method = question_method
        self.setup_window(window_title)
        self.initialize_variables(questions_data)
        self.create_widgets()
        self._configure_text_tags() # Configure fonts first
        # Configure Treeview style after initializing variables and configuring fonts
        self._configure_treeview_style() # NEW: Call style configuration
        self.show_next_image() # Load the first image

    def setup_window(self, title: str):
        self.title(title)
        self.geometry(config.IMAGE_WINDOW_SIZE)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def initialize_variables(self, questions_data: list[dict]):
        # (No changes needed in this method from the previous version)
        self.available_questions = list(questions_data)
        self.current_question_data: dict | None = None
        self.option: str | None = None
        self.timer_seconds: int = config.TIMER_DURATION
        self.after_id: str | None = None
        self.start_time: float = 0.0
        self.progress_window: Toplevel | None = None
        self.treeview_sort_state: dict = {}
        self.tree_data: list = []
        self.choice_made: bool = True
        self.user_level: int = self.db_manager.calculate_user_level(self.username)
        self.specific_question_windows: dict[str, dict] = {}
        self.image_label_ref = None
        self._ai_processing_queue = queue.Queue()
        self.default_font = None
        self.bold_font = None
        self.italic_font = None
        self._check_ai_solution_queue(self._ai_processing_queue) # Start queue checker
        logging.info(f"Starting practice for user '{self.username}' (Level {self.user_level}) in folder '{self.folder_name}' with {len(self.available_questions)} questions.")

    def _configure_text_tags(self):
        """Configure tags for basic Markdown rendering in Text widgets."""
        # MODIFIED: Increase base font size for Text widgets (e.g., AI explanation)
        base_font_size = 12 # Adjust this value as needed (was likely 10 or 11 before)

        try:
            temp_text = Text(self)
            # Get default font properties but override size
            default_font_props = tkFont.Font(font=temp_text.cget("font"))
            default_family = default_font_props.actual("family")
            default_weight = default_font_props.actual("weight")
            default_slant = default_font_props.actual("slant")
            temp_text.destroy()

            # Create base font with desired size
            self.default_font = tkFont.Font(family=default_family, size=base_font_size, weight=default_weight, slant=default_slant)

            # Create bold and italic variations based on the new default
            self.bold_font = tkFont.Font(font=self.default_font)
            self.bold_font.configure(weight="bold")

            self.italic_font = tkFont.Font(font=self.default_font)
            self.italic_font.configure(slant="italic")

        except tk.TclError:
             logging.warning("Could not get default font for Text widget. Using fallback.")
             # Provide fallback fonts with desired size
             self.default_font = tkFont.Font(family="Helvetica", size=base_font_size)
             self.bold_font = tkFont.Font(family="Helvetica", size=base_font_size, weight="bold")
             self.italic_font = tkFont.Font(family="Helvetica", size=base_font_size, slant="italic")
        logging.info(f"Configured Text widget base font: {self.default_font.actual()}")

    # NEW: Method to configure Treeview style
    def _configure_treeview_style(self):
        """Configures the style for the progress Treeview."""
        try:
            style = ttk.Style(self) # Get style object associated with this window

            # --- Define Font ---
            # Use the base font we determined for Text widgets or define separately
            # Let's use a slightly smaller font for the treeview than the explanation box
            tree_font_size = 11 # Adjust as needed
            if self.default_font:
                tree_font_family = self.default_font.actual("family")
                tree_font = tkFont.Font(family=tree_font_family, size=tree_font_size)
            else: # Fallback
                tree_font = tkFont.Font(family="Helvetica", size=tree_font_size)

            # --- Define Row Height ---
            # Default is often around 20-22. Increase for more padding.
            tree_row_height = 28 # Adjust as needed (e.g., 25, 28, 30)

            # Configure the base Treeview style (affects all Treeviews in this window)
            # style.configure('Treeview', font=tree_font, rowheight=tree_row_height)

            # OR: Create a custom style (safer if you might add other Treeviews)
            custom_style_name = 'Progress.Treeview'
            style.configure(custom_style_name, font=tree_font, rowheight=tree_row_height)
            # Also configure the heading font if desired
            style.configure(f"{custom_style_name}.Heading", font=(tree_font_family, tree_font_size, 'bold'))


            logging.info(f"Configured Treeview style '{custom_style_name}' with Font: {tree_font.actual()}, RowHeight: {tree_row_height}")

        except Exception as e:
            logging.error(f"Failed to configure Treeview style: {e}", exc_info=True)


    def create_widgets(self):
        # (No changes needed in this method)
        self.top_frame = Frame(self)
        self.top_frame.pack(fill='x', padx=10, pady=5)
        self.image_name_label = Label(self.top_frame, text="Loading...", font=("Helvetica", 16), anchor='w')
        self.image_name_label.pack(side='left', fill='x', expand=True)
        self.timer_label = Label(self.top_frame, text="--:--", font=("Helvetica", 16, "bold"), anchor='e')
        self.timer_label.pack(side='right')
        self.image_frame = Frame(self)
        self.image_frame.pack(pady=10, fill="both", expand=True)
        self.image_label = Label(self.image_frame)
        self.image_label.pack(expand=True)
        self.options_frame = Frame(self)
        self.options_frame.pack(pady=10)
        self.option_vars = {}
        for letter in config.OPTION_LETTERS:
            var = IntVar(value=0)
            chk = Checkbutton(self.options_frame, text=letter, variable=var,
                              font=("Helvetica", 14),
                              command=lambda opt=letter: self.on_checkbox_click(opt))
            chk.pack(side='left', padx=15)
            self.option_vars[letter] = var
        buttons_frame = Frame(self)
        buttons_frame.pack(pady=10)
        Button(buttons_frame, text="Next Question", command=self.show_next_image, font=("Helvetica", 12, "bold"), width=15).pack(side='left', padx=20)
        self.result_button = Button(buttons_frame, text="Show Progress", command=self.show_user_progress, font=("Helvetica", 12), width=15)
        self.result_button.pack(side='left', padx=20)

    # --- ADDED BACK MISSING METHOD ---
    def show_next_image(self):
        """Processes the current answer and displays the next question."""
        # MODIFIED: Check against current_question_data
        if not self.choice_made and self.current_question_data is not None:
            self.show_temporary_warning("Please select an answer.")
            return

        # MODIFIED: Check against current_question_data
        if self.current_question_data is not None:
            self.process_current_question() # Save progress for the previous question

        # MODIFIED: Check available_questions list
        if not self.available_questions:
            messagebox.showinfo("Practice Set Complete", "All questions answered!", parent=self)
            self.on_closing()
            return

        # MODIFIED: Select the next question dictionary
        next_question = self.select_next_question()
        if not next_question:
             messagebox.showerror("Error", "Could not select next question.", parent=self)
             # Potentially handle this better - maybe try random again?
             return

        self.current_question_data = next_question
        try:
            # Remove the selected question dictionary from the available list
            # This requires comparing dictionaries, which can be tricky if mutable.
            # Assuming image_filename is unique within the set for removal.
            filename_to_remove = self.current_question_data['image_filename']
            self.available_questions = [q for q in self.available_questions if q['image_filename'] != filename_to_remove]
        except Exception as e:
             logging.error(f"Error removing question from available list: {e}", exc_info=True)
             # Continue anyway, but might see duplicates if error occurs

        # MODIFIED: Get image path from the current question dictionary
        image_path = self.current_question_data.get('full_image_path') # Use pre-calculated path
        if not image_path: # Fallback if 'full_image_path' wasn't added
            image_path = os.path.join(self.folder_path, self.current_question_data['image_filename'])


        self.display_image(image_path)
        self.update_image_name_label() # Update label based on new current_question_data
        self.reset_question_state()
    # --- END OF ADDED METHOD ---


    def process_current_question(self):
        """Saves the user's answer for the previously displayed question."""
        # MODIFIED: Check current_question_data and user's selected option
        if self.current_question_data is None or self.option is None:
            return # Nothing to process

        # MODIFIED: Get details directly from the question dictionary
        q_data = self.current_question_data
        correct_answer = q_data.get('correct_answer', "N/A")
        year = q_data.get('year')
        q_num = q_data.get('question_number')
        set_id = q_data.get('set_identifier')
        category = q_data.get('category')
        img_filename = q_data.get('image_filename')

        end_time = time.time()
        answer_time = max(0, int(end_time - self.start_time)) if self.start_time > 0 else 0

        # MODIFIED: Call save_user_progress with individual fields
        success = self.db_manager.save_user_progress(
            username=self.username,
            folder_name=self.folder_name, # Keep folder name for context
            year=year,
            question_number=q_num,
            set_identifier=set_id,
            category=category,
            image_filename=img_filename, # Save filename for easier lookup later
            user_choice=self.option,
            correct_choice=correct_answer,
            answer_time=answer_time
        )
        if not success:
            log_id = f"Q#{q_num}" if q_num else f"Img:{img_filename}"
            messagebox.showerror("Save Error", f"Failed to save progress for {log_id}.", parent=self)

    # MODIFIED: Renamed and changed logic to select a question dictionary
    def select_next_question(self) -> dict | None:
        """Selects the next question dictionary based on the chosen method."""
        if not self.available_questions: return None

        selected_question_dict = None
        if self.question_selection_method == "Random":
            selected_question_dict = random.choice(self.available_questions)
        elif self.question_selection_method == "AI Selection":
            try:
                self.user_level = self.db_manager.calculate_user_level(self.username)
                logging.info(f"AI Selection: Level for '{self.username}' is {self.user_level}")
            except Exception as e:
                logging.error(f"Error calculating user level: {e}", exc_info=True)
                return random.choice(self.available_questions) # Fallback

            target_level = self.user_level
            eligible_questions = []
            if target_level in config.LEVEL_RANGES:
                target_range = config.LEVEL_RANGES[target_level]
                # MODIFIED: Filter based on question_number field in dictionary
                eligible_questions = [
                    q_dict for q_dict in self.available_questions
                    if q_dict.get('question_number') is not None and q_dict['question_number'] in target_range
                ]
                logging.info(f"{len(eligible_questions)} questions found at target level {target_level}.")
            else:
                logging.warning(f"Level {target_level} not in config. Selecting randomly.")
                return random.choice(self.available_questions) # Fallback

            if eligible_questions:
                selected_question_dict = random.choice(eligible_questions)
            else:
                # If no questions at target level, maybe try adjacent levels or just random?
                logging.warning(f"No available questions at level {target_level}. Selecting randomly from remaining.")
                # Avoid error if available_questions became empty unexpectedly
                if self.available_questions:
                    selected_question_dict = random.choice(self.available_questions)
                else:
                    return None # No questions left at all
        else:
            logging.warning(f"Unknown method '{self.question_selection_method}'. Selecting randomly.")
            if self.available_questions:
                 selected_question_dict = random.choice(self.available_questions)
            else:
                 return None

        if selected_question_dict:
            logging.info(f"Selected next question: {selected_question_dict.get('image_filename', 'N/A')} (Q# {selected_question_dict.get('question_number', 'N/A')})")
        return selected_question_dict

    def display_image(self, image_path: str):
        # (No changes needed)
        target_width = 1600
        try:
            img_orig = Image.open(image_path)
            w_orig, h_orig = img_orig.size
            if w_orig > 0:
                aspect_ratio = h_orig / w_orig
                new_height = int(target_width * aspect_ratio)
                img_resized = img_orig.resize((target_width, new_height), Image.Resampling.LANCZOS)
                self.image_label_ref = ImageTk.PhotoImage(img_resized)
            else:
                logging.warning(f"Image has zero width: {image_path}")
                self.image_label_ref = ImageTk.PhotoImage(img_orig)
            self.image_label.configure(image=self.image_label_ref, text="")
        except (FileNotFoundError, UnidentifiedImageError, Exception) as e:
            error_msg = f"Error loading/resizing image:\n{os.path.basename(image_path)}\n{e}"
            logging.error(f"Failed to load/resize image '{image_path}': {e}", exc_info=True)
            messagebox.showerror("Image Error", error_msg, parent=self)
            self.image_label.configure(text=error_msg, image='')
            self.image_label_ref = None

    def update_image_name_label(self):
        # (No changes needed)
        if not self.current_question_data:
            self.image_name_label.config(text="No Question")
            return
        q_data = self.current_question_data
        year = q_data.get('year', 'N/A'); q_num = q_data.get('question_number', 'N/A')
        set_id = q_data.get('set_identifier', ''); category = q_data.get('category', '')
        set_display = f" Set {set_id}" if set_id and set_id != 'NA' else ""
        cat_display = f" ({category})" if category else ""
        display_text = f"{self.folder_name}{set_display} - Yr {year} Q {q_num}{cat_display}"
        self.image_name_label.config(text=display_text)

    def reset_question_state(self):
         # (No changes needed)
         self.choice_made = False; self.option = None; self.start_time = time.time()
         self.reset_timer(); self.clear_all_option_selections()

    def clear_all_option_selections(self):
         # (No changes needed)
         for var in self.option_vars.values(): var.set(0)

    def on_checkbox_click(self, selected_option: str):
         # (No changes needed)
         for option, var in self.option_vars.items(): var.set(1 if option == selected_option else 0)
         self.option = selected_option; self.choice_made = True

    def reset_timer(self):
         # (No changes needed)
         if self.after_id: self.after_cancel(self.after_id)
         self.timer_seconds = config.TIMER_DURATION
         mins, secs = divmod(self.timer_seconds, 60)
         self.timer_label.config(text=f"{mins:02d}:{secs:02d}", fg='black')
         self.update_timer()

    def update_timer(self):
         # (No changes needed)
         mins, secs = divmod(self.timer_seconds, 60)
         current_text = f"{mins:02d}:{secs:02d}"
         if self.timer_label.cget("text") != current_text: self.timer_label.config(text=current_text)
         if self.timer_seconds <= 0:
             if self.timer_label.cget("text") != "Time's Up!":
                 self.timer_label.config(text="Time's Up!", fg='red')
                 self.play_sound_async(config.WARNING_SOUND)
             if self.after_id: self.after_cancel(self.after_id); self.after_id = None
             return
         new_color, play_heartbeat = 'black', False
         if self.timer_seconds <= 10: new_color, play_heartbeat = 'red', self.timer_seconds % 2 != 0
         elif self.timer_seconds <= 30: new_color, play_heartbeat = 'orange', self.timer_seconds % 5 == 0
         if self.timer_label.cget("fg") != new_color: self.timer_label.config(fg=new_color)
         if play_heartbeat: self.play_sound_async(config.HEARTBEAT_SOUND)
         self.timer_seconds -= 1
         self.after_id = self.after(1000, self.update_timer)

    def play_sound_async(self, sound_alias: str):
         # (No changes needed)
         try: threading.Thread(target=winsound.PlaySound, args=(sound_alias, winsound.SND_ALIAS | winsound.SND_ASYNC), daemon=True).start()
         except Exception as e: logging.warning(f"Sound error '{sound_alias}': {e}")

    def show_temporary_warning(self, message: str, duration_ms: int = 1500):
         # (No changes needed)
         self.play_sound_async(config.WARNING_SOUND)
         try:
             popup = Toplevel(self); popup.title("Warning"); popup.transient(self); popup.resizable(False, False)
             Label(popup, text=message, wraplength=380, font=("Helvetica", 12), justify="center").pack(pady=20, padx=20)
             self.center_window(popup, relative_to=self)
             popup.after(duration_ms, popup.destroy)
         except Exception as e: messagebox.showwarning("Warning", message, parent=self)

    # MODIFIED: Always close existing window (if any) before creating a new one
    def show_user_progress(self):
        """Displays the user's progress, ensuring it's always up-to-date."""
        # Close the existing progress window if it's open
        if self.progress_window and self.progress_window.winfo_exists():
            logging.info("Closing existing progress window before reopening.")
            self._on_progress_close() # Use the existing close handler

        # Now, fetch fresh data and create the window
        try:
            progress = self.db_manager.get_user_progress(self.username)
        except Exception as e:
            messagebox.showerror("Progress Error", f"DB error fetching progress: {e}", parent=self)
            return
        if not progress:
            messagebox.showinfo("Progress", "No progress recorded yet.", parent=self)
            return

        self.tree_data = [(i, list(a)) for i, a in enumerate(progress)]
        self.progress_window = self.create_progress_window() # This will now always create a new window
        if self.progress_window and hasattr(self, 'tree'):
            self.tree.bind("<Button-1>", self.on_question_click)


    def create_progress_window(self) -> Toplevel | None:
        """Creates the progress Toplevel window."""
        # MODIFIED: Apply the custom style to the Treeview
        try:
            prog_win = Toplevel(self); prog_win.title(f"{self.username}'s Progress")
            prog_win.geometry(config.PROGRESS_WINDOW_SIZE); prog_win.protocol("WM_DELETE_WINDOW", self._on_progress_close)
            frame = Frame(prog_win); frame.pack(fill='both', expand=True, padx=10, pady=10)
            cols = ("Folder", "Year", "Q#", "Set", "Category", "Choice", "Correct", "Time(s)", "Date", "Image")

            # MODIFIED: Apply the custom style name here
            custom_style_name = 'Progress.Treeview'
            self.tree = ttk.Treeview(frame, columns=cols, show="headings", style=custom_style_name)

            vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
            hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
            self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            self.tree.grid(row=0, column=0, sticky='nsew'); vsb.grid(row=0, column=1, sticky='ns'); hsb.grid(row=1, column=0, sticky='ew')
            frame.grid_rowconfigure(0, weight=1); frame.grid_columnconfigure(0, weight=1)
            widths = {"Folder": 120, "Year": 60, "Q#": 40, "Set": 50, "Category": 100, "Choice": 60, "Correct": 60, "Time(s)": 60, "Date": 150, "Image": 150}
            self.treeview_sort_state = {}
            for c in cols: self.treeview_sort_state[c]=False; self.tree.heading(c,text=c,command=lambda x=c:self._sort_treeview(x)); self.tree.column(c,anchor="center",width=widths.get(c,100),minwidth=40)
            self.tree.tag_configure("correct", background="#e0ffe0"); self.tree.tag_configure("incorrect", background="#ffe0e0"); self.tree.tag_configure("partial", background="#fff5e0")
            self._populate_treeview(); self.center_window(prog_win, relative_to=self); prog_win.lift()
            return prog_win
        except Exception as e: logging.error(f"Create progress window error: {e}", exc_info=True); messagebox.showerror("Error", f"Cannot create progress window: {e}", parent=self); return None

    def _populate_treeview(self):
         # (No changes needed)
         if not hasattr(self, 'tree') or not self.tree.winfo_exists(): return
         for i in self.tree.get_children(): self.tree.delete(i)
         for iid, vals in self.tree_data:
             f_name, yr, qn, set_id, cat, uc, cc, at, adr, img_fname = vals
             tag = "partial" if cc == "N/A" else ("correct" if uc == cc else "incorrect")
             try: fdate = datetime.strptime(adr.split('.')[0], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M') if adr else 'NA'
             except: fdate = str(adr or 'NA')
             dvals = (f_name or 'NA', yr if yr is not None else 'NA', qn if qn is not None else 'NA', set_id or 'NA', cat or 'NA', uc or 'NA', cc or 'NA', at if at is not None else 'NA', fdate, img_fname or 'NA')
             self.tree.insert("", 'end', iid=str(iid), values=dvals, tags=(tag,))

    def _sort_treeview(self, col: str):
         # (No changes needed)
         if not hasattr(self, 'tree') or not self.tree.winfo_exists(): logging.warning("Attempted to sort non-existent treeview."); return
         reverse = not self.treeview_sort_state.get(col, False)
         try:
             columns = self.tree["columns"]; col_index = columns.index(col)
             def key_func(item_data_tuple):
                 db_values = item_data_tuple[1]
                 if col_index >= len(db_values): logging.warning(f"Col index {col_index} out of range: {item_data_tuple}"); return ""
                 value = db_values[col_index]
                 if value is None or value == 'NA': return -float('inf') if not reverse else float('inf')
                 if col in ["Year", "Q#", "Time(s)"]:
                     try: return int(value)
                     except (ValueError, TypeError): return 0
                 elif col == "Date": raw_date = db_values[8] if len(db_values) > 8 else None; return raw_date if raw_date else ""
                 try: return str(value).lower()
                 except Exception: return ""
             self.tree_data.sort(key=key_func, reverse=reverse)
             self.treeview_sort_state[col] = reverse
             self._populate_treeview()
         except (ValueError, IndexError) as e: logging.error(f"Sort index error col '{col}': {e}", exc_info=True)
         except Exception as e: logging.error(f"Unexpected sort error col '{col}': {e}", exc_info=True)

    def _on_progress_close(self):
         # (No changes needed)
         if self.progress_window and self.progress_window.winfo_exists():
             try:
                 self.progress_window.destroy()
             except tk.TclError:
                 logging.warning("TclError destroying progress window (might already be gone).")
             except Exception as e:
                 logging.error(f"Error destroying progress window: {e}", exc_info=True)
         self.progress_window = None # Ensure reference is cleared


    def on_question_click(self, event):
         # (No changes needed)
         if not hasattr(self, 'tree') or not self.tree.winfo_exists(): return
         try:
             region = self.tree.identify_region(event.x, event.y); iid_str = self.tree.identify_row(event.y)
             if region not in ("cell", "tree") or not iid_str: return
             self.tree.selection_remove(iid_str)
             s_data = next((t[1] for t in self.tree_data if str(t[0]) == iid_str), None)
             if not s_data: logging.error(f"No data for iid {iid_str}"); return
             f_name, yr, qn, set_id, cat, uc, cc, at, adr, img_fname = s_data
             if not f_name or not img_fname: messagebox.showwarning("Missing Info", "Folder name or image filename missing.", parent=self.progress_window or self); return
             target_folder = self.find_folder_path(f_name)
             if not target_folder: messagebox.showerror("Folder Error", f"Cannot find folder '{f_name}'.", parent=self.progress_window or self); return
             img_path = os.path.join(target_folder, img_fname)
             if os.path.exists(img_path): self.show_specific_question_image(img_path, cc or "N/A")
             else: messagebox.showerror("Image Not Found", f"Cannot find image:\n{img_fname}\nin folder '{f_name}'.", parent=self.progress_window or self)
         except Exception as e: logging.error(f"Treeview click error: {e}", exc_info=True); messagebox.showerror("Error", f"Click error: {e}", parent=self.progress_window or self)

    def find_folder_path(self, folder_name_from_db: str) -> str | None:
         # (No changes needed)
         try:
             if self.folder_name == folder_name_from_db and os.path.isdir(self.folder_path): return self.folder_path
             app_dir = os.path.dirname(os.path.abspath(__file__)); potential_path = os.path.join(app_dir, folder_name_from_db)
             return potential_path if os.path.isdir(potential_path) else None
         except Exception as e: logging.error(f"Find folder error '{folder_name_from_db}': {e}", exc_info=True); return None

    def show_specific_question_image(self, image_path: str, correct_answer: str):
        """Displays a question image and AI solution in a scrollable popup. Allows multiple."""
        # (No changes needed)
        if image_path in self.specific_question_windows:
            existing_info = self.specific_question_windows[image_path]
            if existing_info['window'].winfo_exists():
                logging.info(f"Lifting existing window for {os.path.basename(image_path)}")
                existing_info['window'].lift(); existing_info['window'].focus_set(); return
            else: del self.specific_question_windows[image_path]

        try:
            parent = self.progress_window if self.progress_window and self.progress_window.winfo_exists() else self
            popup = Toplevel(parent)
            popup.title(f"Review: {os.path.basename(image_path)}"); popup.geometry("1800x1400")
            popup.transient(parent)
            popup.protocol("WM_DELETE_WINDOW", lambda path=image_path: self._on_specific_question_close(path))
            mf = Frame(popup); mf.pack(fill="both", expand=True); cv = Canvas(mf); sb = ttk.Scrollbar(mf, orient="vertical", command=cv.yview)
            sf = Frame(cv); cv.configure(yscrollcommand=sb.set); cv.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
            cv_win = cv.create_window((0, 0), window=sf, anchor="nw")
            sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all"))); cv.bind("<Configure>", lambda e: cv.itemconfig(cv_win, width=e.width))
            scroll_fn = lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"); cv.bind("<MouseWheel>", scroll_fn); sf.bind("<MouseWheel>", scroll_fn)
            img_lbl = Label(sf); img_lbl.pack(pady=10, padx=10); img_lbl.bind("<MouseWheel>", scroll_fn)
            popup_image_ref = None
            try:
                img_orig = Image.open(image_path); w_orig, h_orig = img_orig.size; target_width = 1600
                if w_orig > 0: aspect_ratio = h_orig / w_orig; new_height = int(target_width * aspect_ratio); img_resized = img_orig.resize((target_width, new_height), Image.Resampling.LANCZOS); popup_image_ref = ImageTk.PhotoImage(img_resized)
                else: logging.warning(f"Review image has zero width: {image_path}"); popup_image_ref = ImageTk.PhotoImage(img_orig)
                img_lbl.config(image=popup_image_ref)
            except Exception as e: logging.error(f"Failed to load/resize review image: {image_path} - {e}", exc_info=True); img_lbl.config(text=f"Error loading image:\n{e}", fg="red")
            ttk.Separator(sf, orient='horizontal').pack(fill='x', pady=10, padx=10)
            Label(sf, text="AI Explanation:", font=("Helvetica", 14, "bold")).pack(pady=(5, 0), padx=10, anchor='w')
            sol_widget = Text(sf, wrap=tk.WORD, height=25, state=tk.DISABLED, font=self.default_font, relief="solid", bd=1, padx=5, pady=5)
            sol_widget.pack(pady=10, padx=10, fill="both", expand=True); sol_widget.bind("<MouseWheel>", scroll_fn)
            if self.bold_font: sol_widget.tag_configure("bold", font=self.bold_font)
            if self.italic_font: sol_widget.tag_configure("italic", font=self.italic_font)
            sol_widget.tag_configure("listitem", lmargin1=20, lmargin2=35)
            self.specific_question_windows[image_path] = {
                'window': popup, 'text_widget': sol_widget, 'image_ref': popup_image_ref, 'latex_image_refs': []
            }
            logging.info(f"Opened solution window for {os.path.basename(image_path)}. Total open: {len(self.specific_question_windows)}")
            self.request_ai_solution(image_path, correct_answer, sol_widget, request_id=image_path)
            self.center_window(popup, relative_to=self); popup.lift(); popup.focus_set()
        except Exception as e: logging.error(f"Show review window error: {e}", exc_info=True); messagebox.showerror("Error", f"Cannot display review: {e}", parent=self)

    def _on_specific_question_close(self, image_path: str):
         # (No changes needed)
         logging.info(f"Closing solution window for {os.path.basename(image_path)}")
         if image_path in self.specific_question_windows:
             window_info = self.specific_question_windows[image_path]
             if window_info['window'].winfo_exists():
                 try: window_info['window'].destroy()
                 except tk.TclError: pass
             del self.specific_question_windows[image_path]
             logging.info(f"Removed window {os.path.basename(image_path)} from dict. Remaining: {len(self.specific_question_windows)}")

    def _ai_solution_worker(self, image_path, correct_answer, result_queue, request_id):
         # (No changes needed)
         logging.info(f"AI Worker: Requesting solution for ID: {request_id} ({os.path.basename(image_path)})")
         result_payload = {'id': request_id}
         try:
             solution_text = get_ai_solution(image_path, correct_answer)
             text_placeholders, latex_dict = find_latex_segments(solution_text)
             img_data_dict = {}; threads = []; img_q = queue.Queue()
             def fetch_img(k, u): img_q.put((k, download_image_data(u)))
             for k, d in latex_dict.items(): url = get_codecogs_url(d['latex'], d['display'], d['is_boxed']); t = threading.Thread(target=fetch_img, args=(k, url), daemon=True); threads.append(t); t.start()
             for t in threads: t.join(timeout=20)
             while not img_q.empty():
                 k, data = img_q.get()
                 if data is not None and k in latex_dict: img_data_dict[k] = {'data': data, 'display': latex_dict[k]['display']}
                 elif k in latex_dict: img_data_dict[k] = {'data': None, 'display': latex_dict[k]['display']}
             result_payload['status'] = 'success'; result_payload['text'] = text_placeholders; result_payload['latex'] = img_data_dict
             result_queue.put(result_payload)
             logging.info(f"AI Worker: Finished processing ID: {request_id}")
         except Exception as e:
             logging.error(f"AI Worker Error for ID {request_id}: {e}", exc_info=True)
             result_payload['status'] = 'error'; result_payload['message'] = f"Error processing ID {request_id}: {e}"
             result_queue.put(result_payload)

    def _apply_markdown_tags(self, text_widget, text_segment, start_index):
         # (No changes needed)
         bold_pattern = re.compile(r"\*\*(.*?)\*\*"); processed_text_for_insertion = ""; applied_tags = []; last_match_end = 0
         for bold_match in bold_pattern.finditer(text_segment):
             pre_text = text_segment[last_match_end:bold_match.start()]; processed_text_for_insertion += pre_text
             bold_content = bold_match.group(1); tag_start_offset = len(processed_text_for_insertion)
             processed_text_for_insertion += bold_content; tag_end_offset = len(processed_text_for_insertion)
             applied_tags.append(("bold", tag_start_offset, tag_end_offset)); last_match_end = bold_match.end()
         processed_text_for_insertion += text_segment[last_match_end:]
         current_insert_index_str = text_widget.index(start_index)
         text_widget.insert(current_insert_index_str, processed_text_for_insertion)
         end_insert_index_str = text_widget.index(f"{current_insert_index_str} + {len(processed_text_for_insertion)} chars")
         for tag, start_offset, end_offset in applied_tags:
             try:
                 tag_start_index = text_widget.index(f"{current_insert_index_str} + {start_offset} chars")
                 tag_end_index = text_widget.index(f"{current_insert_index_str} + {end_offset} chars")
                 text_widget.tag_add(tag, tag_start_index, tag_end_index)
             except tk.TclError as e: logging.warning(f"TclError applying tag '{tag}': {e}")
         stripped_segment = text_segment.lstrip()
         if stripped_segment.startswith(("* ", "- ", "+ ")) or \
            (stripped_segment.find(". ") > 0 and stripped_segment[:stripped_segment.find(". ")].isdigit()):
              text_widget.tag_add("listitem", current_insert_index_str, end_insert_index_str)
         return end_insert_index_str

    def _update_solution_widget(self, text_widget, window_info, result_data):
         # (No changes needed)
         if not text_widget.winfo_exists(): logging.warning("Attempted to update a destroyed text widget."); return
         try:
             text_widget.config(state=tk.NORMAL); text_widget.delete("1.0", tk.END); window_info['latex_image_refs'].clear()
             if result_data.get('status') == 'error': text_widget.insert("1.0", result_data.get('message', "Unknown error occurred."))
             elif result_data.get('status') == 'success':
                 text_ph = result_data['text']; latex_imgs = result_data['latex']; last_idx = 0
                 placeholder_re = re.compile(PLACEHOLDER_FORMAT.format(r'(\d+)')); current_insert_index = "1.0"
                 for match in placeholder_re.finditer(text_ph):
                     key = match.group(0); start, end = match.span(); text_segment = text_ph[last_idx:start]
                     if text_segment: current_insert_index = self._apply_markdown_tags(text_widget, text_segment, current_insert_index)
                     if key in latex_imgs:
                         info = latex_imgs[key]; img_bytes = info['data']; is_disp = info['display']
                         if img_bytes:
                             try:
                                 img = Image.open(io.BytesIO(img_bytes)); photo = ImageTk.PhotoImage(img); window_info['latex_image_refs'].append(photo)
                                 nl_b, nl_a = ("\n", "\n") if is_disp else ("", " "); text_widget.insert(current_insert_index, nl_b); current_insert_index = text_widget.index(f"{current_insert_index} + {len(nl_b)} chars")
                                 text_widget.image_create(current_insert_index, image=photo, padx=5, pady=(5 if is_disp else 1)); current_insert_index = text_widget.index(f"{current_insert_index} + 1 chars")
                                 text_widget.insert(current_insert_index, nl_a); current_insert_index = text_widget.index(f"{current_insert_index} + {len(nl_a)} chars")
                             except Exception as img_e: logging.error(f"Failed to create PhotoImage for {key}: {img_e}"); err_text = f"[IMG ERR: {key}]"; text_widget.insert(current_insert_index, err_text); current_insert_index = text_widget.index(f"{current_insert_index} + {len(err_text)} chars")
                         else: fail_text = f"[IMG FAILED: {key}]"; text_widget.insert(current_insert_index, fail_text); current_insert_index = text_widget.index(f"{current_insert_index} + {len(fail_text)} chars")
                     else: q_text = f"[{key} ?]"; text_widget.insert(current_insert_index, q_text); current_insert_index = text_widget.index(f"{current_insert_index} + {len(q_text)} chars")
                     last_idx = end
                 remaining_text = text_ph[last_idx:]
                 if remaining_text: current_insert_index = self._apply_markdown_tags(text_widget, remaining_text, current_insert_index)
             else: text_widget.insert("1.0", f"Unknown result status: {result_data.get('status')}")
         except tk.TclError as e: logging.warning(f"TclError during widget update (likely destroyed): {e}")
         except Exception as e:
             logging.error(f"Error updating solution widget: {e}", exc_info=True)
             try: # Attempt to display error in the widget if it still exists
                 if text_widget.winfo_exists(): text_widget.delete("1.0", tk.END); text_widget.insert("1.0", f"Error displaying solution: {e}")
             except Exception as inner_e: logging.error(f"Failed to display error in text widget: {inner_e}")
         finally:
              try: # Ensure widget is disabled even if errors occurred
                  if text_widget.winfo_exists():
                      text_widget.config(state=tk.DISABLED)
                      canvas = text_widget.master.master
                      if isinstance(canvas, Canvas): canvas.after(50, lambda: canvas.configure(scrollregion=canvas.bbox("all")))
              except tk.TclError: pass
              except Exception as final_e: logging.error(f"Error in finally block of _update_solution_widget: {final_e}")


    def _check_ai_solution_queue(self, result_queue):
         # (No changes needed)
         try:
             result = result_queue.get_nowait(); request_id = result.get('id')
             if not request_id: logging.warning(f"Received AI result with no ID: {result}"); return
             if request_id in self.specific_question_windows:
                  target_info = self.specific_question_windows[request_id]; target_window = target_info['window']; target_text_widget = target_info['text_widget']
                  if target_window.winfo_exists() and target_text_widget.winfo_exists(): logging.info(f"Routing AI result for ID {request_id} to its window."); self._update_solution_widget(target_text_widget, target_info, result)
                  else: logging.warning(f"Window/widget for ID {request_id} closed before result. Discarding."); del self.specific_question_windows[request_id]
             else: logging.warning(f"Received AI result for unknown or closed window ID: {request_id}. Discarding.")
         except queue.Empty: pass
         except Exception as e: logging.error(f"Error in AI solution queue checker: {e}", exc_info=True)
         finally:
              if self.winfo_exists(): self.after(200, self._check_ai_solution_queue, result_queue)


    def request_ai_solution(self, image_path, correct_answer, text_widget, request_id):
        """Starts thread to get AI solution and display it in the correct window."""
        # FIX: Corrected the if/try/except structure
        if not AI_ENABLED:
            try:
                # Only modify widget if it still exists
                if text_widget.winfo_exists():
                    text_widget.config(state=tk.NORMAL)
                    text_widget.delete("1.0",tk.END)
                    text_widget.insert("1.0","AI Features Disabled (No API Key).")
                    text_widget.config(state=tk.DISABLED)
            except Exception as e:
                # Log if updating the widget fails even here
                logging.warning(f"Error updating text widget to show AI disabled: {e}")
            return # Stop processing if AI is not enabled

        # Proceed if AI is enabled
        try:
            # Only modify widget if it still exists
            if text_widget.winfo_exists():
                text_widget.config(state=tk.NORMAL)
                text_widget.delete("1.0",tk.END)
                text_widget.insert("1.0","Fetching/Rendering AI Explanation...")
                text_widget.config(state=tk.DISABLED)
        except tk.TclError:
            logging.warning("Text widget destroyed before AI request could show 'Fetching...' message.")
            return # Don't start thread if widget is gone

        # Start the background thread
        thread = threading.Thread(target=self._ai_solution_worker,
                                  args=(image_path, correct_answer, self._ai_processing_queue, request_id),
                                  daemon=True)
        thread.start()


    def center_window(self, window, relative_to=None):
         # (No changes needed)
         window.update_idletasks()
         try:
             w, h = window.winfo_width(), window.winfo_height()
             if relative_to and relative_to.winfo_exists(): px, py, pw, ph = relative_to.winfo_x(), relative_to.winfo_y(), relative_to.winfo_width(), relative_to.winfo_height(); x, y = px+(pw//2)-(w//2), py+(ph//2)-(h//2)
             else: sw, sh = window.winfo_screenwidth(), window.winfo_screenheight(); x, y = (sw//2)-(w//2), (sh//2)-(h//2)
             sw, sh = window.winfo_screenwidth(), window.winfo_screenheight(); x, y = max(0, min(x, sw-w)), max(0, min(y, sh-h))
             window.geometry(f'{w}x{h}+{x}+{y}')
         except Exception as e: logging.warning(f"Centering error: {e}")

    def on_closing(self):
         # (No changes needed)
         logging.info("Closing practice window...")
         if self.after_id:
             try: self.after_cancel(self.after_id)
             except tk.TclError: pass
             except Exception as e: logging.warning(f"Error cancelling timer on close: {e}")
             finally: self.after_id = None
         open_window_keys = list(self.specific_question_windows.keys())
         for img_path in open_window_keys: self._on_specific_question_close(img_path)
         if self.progress_window and self.progress_window.winfo_exists(): self.progress_window.destroy()
         self.image_label_ref = None; self.destroy()
         if self.parent and self.parent.winfo_exists(): logging.info("Exiting application."); self.parent.destroy()

