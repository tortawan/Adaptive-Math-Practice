# Adaptive Math Practice Application

## Description

The Adaptive Math Practice Application is a desktop tool built with Python and Tkinter designed to help users practice math problems, particularly those in the style of AMC (American Mathematics Competitions). It features user authentication, adaptive question difficulty based on performance, timed questions, progress tracking, and AI-powered (via Google Gemini) step-by-step solutions for review.

## Features

* **User Authentication**: Secure registration and login system using bcrypt for password hashing.
* **Practice Sets**: Load math problems from local folders (e.g., "AMC 8", "AMC 10") containing images and a `metadata.json` file.
* **Question Display**: Shows question images clearly in the UI.
* **Timed Practice**: Each question is timed, with visual cues for remaining time.
* **Multiple Choice**: Standard A-E multiple choice options.
* **Adaptive Difficulty (AI Selection)**: The application can select questions based on the user's calculated proficiency level, drawing from configurable difficulty tiers. Random question selection is also available.
* **Progress Tracking**: Saves all attempts, including chosen answer, correct answer, and time taken, to a local SQLite database.
* **Progress Review**: Users can view their entire practice history in a sortable table, and click on any past question to review it.
* **AI Explanations**: For reviewed questions, the app fetches a step-by-step solution from Google's Gemini model.
* **LaTeX Rendering**: AI explanations containing LaTeX are rendered as images (via CodeCogs API) directly within the explanation text box for proper mathematical formatting.
* **Motivational Content**: Displays random motivational phrases.

## Technology Stack

* **Programming Language**: Python 3
* **GUI**: Tkinter (Python's standard GUI library)
* **Database**: SQLite 3
* **AI**: Google Generative AI (Gemini API)
* **Image Handling**: Pillow (PIL Fork)
* **Password Hashing**: bcrypt
* **API Key Management**: python-dotenv
* **HTTP Requests**: requests (for LaTeX image rendering)
* **Sound (Windows)**: winsound

## Setup Instructions

### Prerequisites

* Python 3.8 or newer.
* Access to the internet (for AI features and LaTeX rendering).
* (Optional but recommended) [Git](https://git-scm.com/downloads) for cloning.

### Installation

1.  **Clone the repository (or download the source code):**
    ```bash
    git clone <your-repository-url>
    cd <repository-folder-name>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    ```
    Activate it:
    * Windows: `venv\Scripts\activate`
    * macOS/Linux: `source venv/bin/activate`

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the Google API Key:**
    * Create a file named `.env` in the root directory of the project.
    * Add your Google API Key to this file:
        ```
        GOOGLE_API_KEY=YOUR_ACTUAL_GOOGLE_API_KEY_HERE
        ```
    * You can obtain a Google API Key from the [Google AI Studio](https://aistudio.google.com/app/apikey).

### Preparing Practice Sets (Question Folders)

The application loads questions from subdirectories within the main application folder. These subdirectories should ideally start with "AMC" (e.g., `AMC 8 2020`, `AMC 10A 2021`) to be automatically detected.

Each practice set folder must contain:
* **Image files**: `.png`, `.jpg`, or `.gif` files for each question.
* **A `metadata.json` file**: This file links image filenames to their properties.

**Example `metadata.json` structure:**
```json
{
  "set_name": "AMC 8 2020 Example",
  "questions": [
    {
      "image_filename": "q1.png",
      "question_number": 1,
      "correct_answer": "A",
      "year": 2020,
      "set_identifier": "8", // e.g., 8 for AMC 8, 10A for AMC 10A
      "category": "Algebra" // Optional: Geometry, Number Theory, etc.
    },
    {
      "image_filename": "q2.png",
      "question_number": 2,
      "correct_answer": "C",
      "year": 2020,
      "set_identifier": "8",
      "category": "Geometry"
    }
    // ... more questions
  ]
}
