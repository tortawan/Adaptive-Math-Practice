# -*- coding: utf-8 -*-
"""
AI Helper Module.

This module provides functionalities to interact with Google's Generative AI 
(Gemini) for tasks like generating math problem solutions based on an image 
and a correct answer. It handles API configuration and AI model interaction.
"""

# ai_helper.py
import google.generativeai as genai
from PIL import Image
import config # For API Key and AI Model Name
import os

AI_ENABLED = False
ai_model = None


if config.GOOGLE_API_KEY:
    try:
        genai.configure(api_key=config.GOOGLE_API_KEY)
        # Use the model name from config.py
        ai_model = genai.GenerativeModel(config.AI_MODEL_NAME) 
        AI_ENABLED = True
        print(f"Google Generative AI configured successfully with model: {config.AI_MODEL_NAME}.")
    except Exception as e:
        print(f"ERROR: Failed to configure Google Generative AI: {e}")
else:
    print("INFO: Google Generative AI features disabled (API key not found).")


def get_solution(image_path: str, correct_answer: str) -> str:
    """
    Gets a solution explanation from the configured AI model.

    Args:
        image_path (str): The path to the image file of the math problem.
        correct_answer (str): The correct answer to the multiple-choice question.

    Returns:
        str: A step-by-step explanation from the AI, or an error/info message.
    """
    if not AI_ENABLED or not ai_model:
        return "AI features are currently disabled or the model is not initialized."

    try:
        img = Image.open(image_path)
        prompt = [
            "You are a helpful math tutor. Provide a clear, step-by-step explanation as a highschool student calculation for how to solve the problem shown in the image.",
            f"The correct answer for this multiple-choice question is '{correct_answer}'. Explain the reasoning to reach this answer.",
            "Format the explanation clearly. Use LaTeX for mathematical expressions and formulas, enclosed in single dollar signs (e.g., $x^2 + y^2 = z^2$). For complex or multi-line equations, you can use double dollar signs ($$\\frac{a}{b}$$). For important results or formulas that should stand out, use \\boxed{your_formula}.", # Added more LaTeX guidance
            img
        ]
        # Consider adding parameters like temperature if you want to control creativity/determinism
        response = ai_model.generate_content(prompt)
        
        # It's good practice to check response.prompt_feedback for safety blocks
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            print(f"Warning: AI response was blocked. Reason: {response.prompt_feedback.block_reason_message}")
            return f"Error: AI response blocked. {response.prompt_feedback.block_reason_message}"
            
        return response.text
    except FileNotFoundError:
        print(f"ERROR: Image file not found at {image_path}")
        return f"Error: Could not load image file '{os.path.basename(image_path)}'."
    except Exception as e:
        print(f"ERROR: AI solution generation failed: {e}")
        # Consider checking e.g. response.candidates[0].finish_reason if available and not text
        return f"Error: Failed to get explanation from AI.\nDetails: {e}"