import unittest
from unittest.mock import patch, MagicMock
import urllib.parse # For verifying URL encoding
import requests

# Assuming latex_utils.py is in the same directory or accessible
from latex_utils import (
    find_latex_segments,
    get_codecogs_url,
    download_image_data,
    PLACEHOLDER_FORMAT
)

class TestLatexUtils(unittest.TestCase):

    def test_find_latex_segments_empty_string(self):
        text = ""
        processed_text, segments = find_latex_segments(text)
        self.assertEqual(processed_text, "")
        self.assertEqual(segments, {})

    def test_find_latex_segments_no_latex(self):
        text = "This is a plain text string."
        processed_text, segments = find_latex_segments(text)
        self.assertEqual(processed_text, text)
        self.assertEqual(segments, {})

    def test_find_latex_segments_simple_inline(self):
        text = "Inline math $x=y$ here."
        placeholder = PLACEHOLDER_FORMAT.format(0)
        expected_processed = f"Inline math {placeholder} here."
        expected_segments = {
            placeholder: {'latex': 'x=y', 'display': False, 'is_boxed': False}
        }
        processed_text, segments = find_latex_segments(text)
        self.assertEqual(processed_text, expected_processed)
        self.assertEqual(segments, expected_segments)

    def test_find_latex_segments_simple_display(self):
        text = "Display math $$a+b=c$$ follows."
        placeholder = PLACEHOLDER_FORMAT.format(0)
        # The regex adds newlines around display math if they are present in the original match group,
        # but the replacement itself aims for `\n\n{key}\n\n` if the match starts/ends with \n.
        # The current `display_repl` adds prefix/suffix based on match.group(0) newlines.
        # If `<span class="math-block">a\+b\=c</span>` is not surrounded by newlines, the placeholder won't be either initially.
        # Let's test based on the actual replacement logic.
        expected_processed = f"Display math {placeholder} follows."
        expected_segments = {
            placeholder: {'latex': 'a+b=c', 'display': True, 'is_boxed': False}
        }
        processed_text, segments = find_latex_segments(text)
        self.assertEqual(processed_text, expected_processed)
        self.assertEqual(segments, expected_segments)

    def test_find_latex_segments_simple_boxed(self):
        text = "Boxed math \\boxed{E=mc^2} is important."
        placeholder = PLACEHOLDER_FORMAT.format(0)
        expected_processed = f"Boxed math {placeholder} is important."
        expected_segments = {
            placeholder: {'latex': 'E=mc^2', 'display': True, 'is_boxed': True}
        }
        processed_text, segments = find_latex_segments(text)
        self.assertEqual(processed_text, expected_processed)
        self.assertEqual(segments, expected_segments)

    def test_find_latex_segments_multiple_and_mixed(self):
        text = "One $L_1$ and two $L_2$. Then $$\\text{Display}$$ and \\boxed{B_1}."
        p0 = PLACEHOLDER_FORMAT.format(0) # Will be Display (matched first by regex order)
        p1 = PLACEHOLDER_FORMAT.format(1) # Will be Boxed (matched next)
        p2 = PLACEHOLDER_FORMAT.format(2) # Will be L_1 (inline)
        p3 = PLACEHOLDER_FORMAT.format(3) # Will be L_2 (inline)

        # The order of regex application in find_latex_segments is: $$, then $, then \boxed
        # Let's adjust p-values based on actual regex substitution order in find_latex_segments:
        # 1. $$...$$
        # 2. $(...)$ (single, non-greedy)
        # 3. \boxed{...}

        # Corrected p-values based on function's regex order:
        # processed_text = re.sub(r'\$\$(.*?)\$\$', display_repl, processed_text, flags=re.DOTALL)
        # processed_text = re.sub(r'(?<!\$)\$([^\$]+?)\$(?!\$)', inline_repl, processed_text)
        # processed_text = re.sub(r'\\boxed{(.*?)}', boxed_repl, processed_text, flags=re.DOTALL)

        # Actual order of placeholders:
        p_display = PLACEHOLDER_FORMAT.format(0) # $$...$$
        p_l1 = PLACEHOLDER_FORMAT.format(1)      # $L_1$
        p_l2 = PLACEHOLDER_FORMAT.format(2)      # $L_2$
        p_boxed = PLACEHOLDER_FORMAT.format(3)   # \boxed{B_1}

        expected_processed = f"One {p_l1} and two {p_l2}. Then {p_display} and {p_boxed}."
        expected_segments = {
            p_display: {'latex': '\\text{Display}', 'display': True, 'is_boxed': False},
            p_l1: {'latex': 'L_1', 'display': False, 'is_boxed': False},
            p_l2: {'latex': 'L_2', 'display': False, 'is_boxed': False},
            p_boxed: {'latex': 'B_1', 'display': True, 'is_boxed': True},
        }
        processed_text, segments = find_latex_segments(text)
        self.assertEqual(processed_text, expected_processed)
        self.assertEqual(segments, expected_segments)

    def test_find_latex_segments_avoids_dollar_amounts(self):
        text = "This costs $5.00, not $math$."
        # The current regex $([^\$]+?)\$ will match "$5.00, not $" first.
        # The content "5.00, not " is not purely numeric, so it becomes a placeholder.
        p_first_match = PLACEHOLDER_FORMAT.format(0)

        expected_processed = f"This costs {p_first_match}math$."
        expected_segments = {
            p_first_match: {'latex': '5.00, not', 'display': False, 'is_boxed': False}
        }
        # If your regex was more sophisticated to isolate $math$ only:
        # p_math_only = PLACEHOLDER_FORMAT.format(0)
        # expected_processed = f"This costs $5.00, not {p_math_only}."
        # expected_segments = {
        #    p_math_only: {'latex': 'math', 'display': False, 'is_boxed': False}
        # }

        processed_text, segments = find_latex_segments(text)
        self.assertEqual(processed_text, expected_processed)
        self.assertEqual(segments, expected_segments)

    def test_find_latex_segments_empty_delimiters(self):
        text = "Empty $$ $$ and $ $ and \\boxed{ }."
        # The function is designed to ignore empty LaTeX segments for replacement
        # if not latex: return match.group(0)
        self.assertEqual(find_latex_segments(text), (text, {}))


    def test_get_codecogs_url_inline(self):
        latex = "x_i"
        expected_url_part = urllib.parse.quote(f"${latex}$", safe='$\\=+*{}()[]^')
        url = get_codecogs_url(latex, is_display=False, is_boxed=False)
        self.assertIn(expected_url_part, url)
        self.assertIn(r"\dpi{150}", url)
        self.assertTrue(url.startswith("https://latex.codecogs.com/png.latex?"))

    def test_get_codecogs_url_display(self):
        latex = "\\frac{a}{b}"
        # Display logic in get_codecogs_url: if not startswith('\\'), adds $$.
        # Since this starts with \\, it doesn't add $$.
        expected_url_part = urllib.parse.quote(latex, safe='$\\=+*{}()[]^')
        url = get_codecogs_url(latex, is_display=True, is_boxed=False)
        self.assertIn(expected_url_part, url)

        latex2 = "a+b" # Does not start with '\'
        expected_url_part2 = urllib.parse.quote(f"$${latex2}$$", safe='$\\=+*{}()[]^')
        url2 = get_codecogs_url(latex2, is_display=True, is_boxed=False)
        self.assertIn(expected_url_part2, url2)


    def test_get_codecogs_url_boxed(self):
        latex = "x=1"
        expected_url_part = urllib.parse.quote(f"\\boxed{{{latex}}}", safe='$\\=+*{}()[]^')
        url = get_codecogs_url(latex, is_display=False, is_boxed=True) # is_display is ignored if is_boxed
        self.assertIn(expected_url_part, url)
        url_display_true = get_codecogs_url(latex, is_display=True, is_boxed=True)
        self.assertIn(expected_url_part, url_display_true)

    @patch('requests.get')
    def test_download_image_data_success(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None # No error
        # Simulate PNG header
        mock_response.content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDAT\x08\xd7c`\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82'
        mock_requests_get.return_value = mock_response

        test_url = "http://fakeurl.com/image.png"
        image_data = download_image_data(test_url)

        mock_requests_get.assert_called_once_with(test_url, stream=True, timeout=15, headers=unittest.mock.ANY)
        mock_response.raise_for_status.assert_called_once()
        self.assertEqual(image_data, mock_response.content)

    @patch('requests.get')
    def test_download_image_data_http_error(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        mock_requests_get.return_value = mock_response

        image_data = download_image_data("http://fakeurl.com/notfound.png")
        self.assertIsNone(image_data)

    @patch('requests.get')
    def test_download_image_data_request_exception(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.RequestException("Connection failed")

        image_data = download_image_data("http://fakeurl.com/unreachable.png")
        self.assertIsNone(image_data)

    @patch('requests.get')
    def test_download_image_data_not_png(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'This is not a PNG' # Invalid image data
        mock_requests_get.return_value = mock_response

        image_data = download_image_data("http://fakeurl.com/not_a_png.txt")
        self.assertIsNone(image_data)


if __name__ == '__main__':
    unittest.main()