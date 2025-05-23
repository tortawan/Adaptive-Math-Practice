# Adaptive Math Practice Application

## 🌟 Description

The Adaptive Math Practice Application is a desktop tool built with Python and Tkinter. It's designed to help users enhance their math skills by practicing problems, particularly those styled after AMC (American Mathematics Competitions) questions. The application features user authentication, adaptive question difficulty, timed challenges, comprehensive progress tracking, and AI-powered (via Google Gemini) step-by-step solutions for detailed review. It also includes an invitation code system for new user registration.

## ✨ Features

* **User Authentication**: Secure registration (with optional invitation codes) and login system using bcrypt for password hashing.
* **Practice Sets**: Dynamically loads math problems from local folders (e.g., "AMC 8 2020", "AMC 10A 2021"). Each set is defined by image files and a `metadata.json` file detailing questions, answers, and other properties.
* **Interactive Question Display**: Clearly presents question images within a dedicated practice window.
* **Timed Practice**: Each question is timed (configurable duration), with visual cues for the remaining time to simulate exam conditions.
* **Multiple Choice Interface**: Standard A-E multiple-choice options for answering questions.
* **Adaptive & Random Question Selection**:
    * **AI Selection**: Intelligently selects questions based on the user's calculated proficiency level, drawing from configurable difficulty tiers.
    * **Random Selection**: Allows users to practice questions in a random order from the chosen set.
* **Comprehensive Progress Tracking**: Saves all attempts, including chosen answer, correct answer, time taken, and date of attempt, to a local SQLite database.
* **In-Depth Progress Review**: Users can view their entire practice history in a sortable and filterable table. Clicking on any past question allows for a detailed review.
* **AI-Powered Explanations**: Fetches detailed, step-by-step solution explanations from Google's Gemini model for any reviewed question.
* **LaTeX Rendering**: Beautifully renders mathematical expressions and formulas within AI explanations as images using the CodeCogs API, ensuring clarity for complex notation.
* **Motivational Content**: Displays random motivational phrases to keep users encouraged.
* **Customizable UI Elements**: Includes features like configurable font sizes for readability in solution windows and styled progress tables.

## 🖼️ Sneak Peek (Screenshots/GIF)

**(Highly Recommended: Add your screenshots and/or a GIF here!)**

* **Login & Registration Window:**
    * `[Link to Screenshot of Login Window]`
    * `[Link to Screenshot of Registration Window with Invitation Code]`
* **Practice Set Selection:**
    * `[Link to Screenshot of Folder and Method Selection]`
* **Main Practice Window:**
    * `[Link to Screenshot of Question Display with Timer and Options]`
* **Progress Review Table:**
    * `[Link to Screenshot of Progress Table]`
* **Solution Review Window:**
    * `[Link to Screenshot of Reviewed Question with AI Explanation and Rendered LaTeX]`
* **(Optional) GIF Demo:**
    * `[Link to GIF showing the main workflow]`

## 🛠️ Technology Stack

* **Programming Language**: Python 3
* **GUI**: Tkinter (Python's standard GUI library)
* **Database**: SQLite 3
* **AI Model**: Google Gemini (configurable model via `config.py`)
* **Image Handling**: Pillow (PIL Fork)
* **API Key Management**: `python-dotenv`
* **Password Hashing**: `bcrypt`
* **HTTP Requests**: `requests` (for LaTeX image rendering)
* **Sound (Windows)**: `winsound` (for timer alerts)

## 🚀 Setup and Installation

### Prerequisites

* Python 3.8 or newer.
* Git (for cloning the repository).
* Internet access (for AI features and LaTeX image rendering).

### Steps

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/tortawan/JobSearch/tree/main/Adaptive_Math_Practice
    cd Adaptive_Math_Practice # Or your project's root folder name
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    Ensure you are in the project's root directory where `requirements.txt` is located.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Google API Key:**
    * Create a file named `.env` in the root directory of the project (e.g., alongside `main.py`).
    * Add your Google API Key to this file. You can obtain a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
        ```env
        GOOGLE_API_KEY="YOUR_ACTUAL_GOOGLE_API_KEY_HERE"
        ```
    * **Important**: Ensure `.env` is listed in your `.gitignore` file to prevent committing your API key.

5.  **Prepare Practice Sets (Question Folders):**
    * The application loads questions from subdirectories within the main application folder (where `main.py` resides).
    * These subdirectories should ideally start with "AMC" (e.g., `AMC 8 2020`, `AMC 10A 2021`) to be automatically detected by the dropdown menu.
    * Each practice set folder **must** contain:
        * **Image files**: `.png`, `.jpg`, or `.gif` files for each question.
        * **A `metadata.json` file**: This file links image filenames to their properties.

    **Example `metadata.json` structure:**
    ```json
    {
      "set_name": "AMC 8 2020 Example Set",
      "questions": [
        {
          "image_filename": "q1.png",
          "question_number": 1,
          "correct_answer": "A",
          "year": 2020,
          "set_identifier": "8",
          "category": "Algebra"
        },
        {
          "image_filename": "q2.png",
          "question_number": 2,
          "correct_answer": "C",
          "year": 2020,
          "set_identifier": "8",
          "category": "Geometry"
        }
      ]
    }
    ```

## ▶️ Running the Application

Once the setup is complete, navigate to the project's root directory in your terminal (where `main.py` is located) and run:

```bash
python main.py
