# latex_utils.py
"""
LaTeX Processing Utilities.

This module provides functions for handling LaTeX content, primarily for
converting LaTeX expressions into renderable formats (e.g., image URLs via
CodeCogs API). It includes:
- Finding and segmenting LaTeX expressions ($...$, $$...$$, \\boxed{...}).
- Generating image URLs for LaTeX code using CodeCogs.
- Downloading image data from URLs.
"""
import re
import urllib.parse
import requests
import io
import logging
from PIL import Image, ImageTk # Keep PIL imports if image conversion/handling is done here

# Configure basic logging if needed independently, or rely on main app config
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Placeholder Format (Consistent across modules)
PLACEHOLDER_FORMAT = "@@LATEX_{}@@"
# Global counter `placeholder_idx_counter` was here but find_latex_segments uses a local one,
# which is safer. Removing unused global.

def find_latex_segments(text: str) -> tuple[str, dict]:
    """
    Parses text, identifies LaTeX segments ($$, $, \\boxed), stores them,
    and returns the text with placeholders.

    Args:
        text (str): The input text containing potential LaTeX segments.

    Returns:
        tuple: (text_with_placeholders, dict_of_latex_data)
               where dict_of_latex_data maps a placeholder key (str) to
               a dictionary: {'latex': str, 'display': bool, 'is_boxed': bool}
    """
    # Use a local dictionary for each call to avoid global state issues
    local_latex_placeholders = {}
    # Use a local index counter for this specific call
    current_placeholder_idx = 0
    processed_text = text

    # Define replacement functions for regex substitution
    def display_repl(match):
        nonlocal current_placeholder_idx, local_latex_placeholders
        latex = match.group(1).strip()
        if not latex: return match.group(0)
        key = PLACEHOLDER_FORMAT.format(current_placeholder_idx)
        local_latex_placeholders[key] = {'latex': latex, 'display': True, 'is_boxed': False}
        current_placeholder_idx += 1
        prefix = '\n\n' if match.group(0).startswith('\n') else ''
        suffix = '\n\n' if match.group(0).endswith('\n') else ''
        return f"{prefix}{key}{suffix}"

    def inline_repl(match):
        nonlocal current_placeholder_idx, local_latex_placeholders
        latex = match.group(1).strip()
        if not latex: return match.group(0)
        if re.fullmatch(r'\d+(\.\d+)?', latex): return match.group(0)
        key = PLACEHOLDER_FORMAT.format(current_placeholder_idx)
        local_latex_placeholders[key] = {'latex': latex, 'display': False, 'is_boxed': False}
        current_placeholder_idx += 1
        return key

    def boxed_repl(match):
        nonlocal current_placeholder_idx, local_latex_placeholders
        latex = match.group(1).strip()
        if not latex: return match.group(0)
        key = PLACEHOLDER_FORMAT.format(current_placeholder_idx)
        local_latex_placeholders[key] = {'latex': latex, 'display': True, 'is_boxed': True}
        current_placeholder_idx += 1
        prefix = '\n\n' if match.group(0).startswith('\n') else ''
        suffix = '\n\n' if match.group(0).endswith('\n') else ''
        return f"{prefix}{key}{suffix}"

    # Apply Regex Substitutions
    processed_text = re.sub(r'\$\$(.*?)\$\$', display_repl, processed_text, flags=re.DOTALL)
    processed_text = re.sub(r'(?<!\$)\$([^\$]+?)\$(?!\$)', inline_repl, processed_text)
    processed_text = re.sub(r'\\boxed{(.*?)}', boxed_repl, processed_text, flags=re.DOTALL)

    return processed_text, local_latex_placeholders


def get_codecogs_url(latex_code, is_display, is_boxed):
    """Generates a CodeCogs image URL."""
    if is_boxed:
        latex_with_delimiters = f"\\boxed{{{latex_code}}}"
    elif is_display:
        if not latex_code.strip().startswith('\\'):
             latex_with_delimiters = f"$${latex_code}$$"
        else:
             latex_with_delimiters = latex_code
    else: # Inline
        latex_with_delimiters = f"${latex_code}$"

    base_url = "https://latex.codecogs.com/png.latex?"
    # Ensure necessary characters for LaTeX and URLs are safe
    encoded_latex = urllib.parse.quote(latex_with_delimiters, safe='$\\=+*{}()[]^')
    render_options = r"\dpi{150}" # Higher DPI for clarity
    full_url = f"{base_url}{render_options} {encoded_latex}"
    return full_url

def download_image_data(url):
    """Downloads image data from a URL. Returns bytes or None."""
    try:
        # Add headers to mimic a browser request, might help with some servers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, stream=True, timeout=15, headers=headers) # Increased timeout
        response.raise_for_status() # Raise error for bad status codes (4xx, 5xx)
        image_data = response.content
        # Basic check: is the content likely an image? (e.g., check for PNG header)
        if not image_data or not image_data.startswith(b'\x89PNG'):
             logging.warning(f"URL did not return valid PNG data: {url}")
             return None
        return image_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error downloading image from {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error downloading image {url}: {e}", exc_info=True)
        return None

# Example usage (optional, for testing this module directly)
if __name__ == '__main__':
    test_text = r"This is inline $E=mc^2$ and display $$\frac{a}{b}$$ and boxed \boxed{x=5}."
    processed, latex_dict = find_latex_segments(test_text)
    print("Processed Text:", processed)
    print("Latex Dict:", latex_dict)
    for key, data in latex_dict.items():
        url = get_codecogs_url(data['latex'], data['display'], data['is_boxed'])
        print(f"{key}: {url}")
        # img_data = download_image_data(url)
        # print(f"  Downloaded {len(img_data) if img_data else 0} bytes")

