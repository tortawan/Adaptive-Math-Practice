import unittest
from unittest.mock import patch, MagicMock
import os # For os.path.basename

# Assuming ai_helper.py and config.py are in the same directory or accessible
# Important: 'ai_helper' will be imported here, running its initial setup block.
# Our tests for get_solution will often override ai_helper.AI_ENABLED and ai_helper.ai_model
import ai_helper
# We don't strictly need 'import config' here unless we're testing config-dependent initial values directly
# and want to patch config itself. For now, we patch ai_helper's usage of config or its effects.

class TestAIHelper(unittest.TestCase):

    def setUp(self):
        # This method is called before each test.
        # We'll use direct patching within tests for clarity on what's being controlled.
        # Keep a reference to original values if you need to restore them meticulously,
        # but for isolated function tests, patching usually suffices.
        self.original_ai_enabled = ai_helper.AI_ENABLED
        self.original_ai_model = ai_helper.ai_model

    def tearDown(self):
        # This method is called after each test.
        # Restore original module-level variables to avoid test interference.
        ai_helper.AI_ENABLED = self.original_ai_enabled
        ai_helper.ai_model = self.original_ai_model

    @patch('ai_helper.Image.open')  # Mock PIL.Image.open used within ai_helper
    @patch('ai_helper.genai.GenerativeModel') # Mock the GenerativeModel class
    def test_get_solution_success(self, mock_GenerativeModel, mock_image_open):
        # --- Arrange ---
        # 1. Ensure ai_helper thinks AI is enabled and has a model
        # We'll patch ai_helper.AI_ENABLED and ai_helper.ai_model for this test's scope
        mock_model_instance = MagicMock() # This will be our fake ai_model
        patcher_ai_enabled = patch('ai_helper.AI_ENABLED', True)
        patcher_ai_model = patch('ai_helper.ai_model', mock_model_instance)

        # Start patchers
        self.mock_ai_enabled = patcher_ai_enabled.start()
        self.mock_ai_model = patcher_ai_model.start()
        # Add to cleanup to stop them after the test
        self.addCleanup(patcher_ai_enabled.stop)
        self.addCleanup(patcher_ai_model.stop)


        dummy_image_path = "dummy/path/to/image.png"
        correct_answer = "A"
        expected_ai_response_text = "This is the step-by-step solution."

        # 2. Configure mock_image_open (from PIL.Image)
        mock_pil_image = MagicMock(name="MockPILImage") # Give it a name for easier debugging
        mock_image_open.return_value = mock_pil_image

        # 3. Configure the mock_model_instance (the result of genai.GenerativeModel(...))
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = expected_ai_response_text
        # Simulate no blocking issues
        mock_gemini_response.prompt_feedback = None # Or MagicMock(block_reason=None)
        mock_model_instance.generate_content.return_value = mock_gemini_response

        # --- Act ---
        solution = ai_helper.get_solution(dummy_image_path, correct_answer)

        # --- Assert ---
        self.assertEqual(solution, expected_ai_response_text)
        mock_image_open.assert_called_once_with(dummy_image_path)

        mock_model_instance.generate_content.assert_called_once()
        args, _kwargs = mock_model_instance.generate_content.call_args
        prompt_list = args[0]

        self.assertIn("You are a helpful math tutor.", prompt_list[0])
        self.assertIn(f"The correct answer for this multiple-choice question is '{correct_answer}'.", prompt_list[1])
        self.assertIn("Use LaTeX for mathematical expressions", prompt_list[2]) # Check part of your prompt instructions
        self.assertEqual(prompt_list[3], mock_pil_image) # Check if the (mocked) PIL image object was passed

    def test_get_solution_ai_disabled(self):
        # Patch ai_helper.AI_ENABLED directly for this test case
        patcher_ai_enabled = patch('ai_helper.AI_ENABLED', False)
        patcher_ai_model = patch('ai_helper.ai_model', None) # Also ensure model is None

        self.mock_ai_enabled = patcher_ai_enabled.start()
        self.mock_ai_model = patcher_ai_model.start()
        self.addCleanup(patcher_ai_enabled.stop)
        self.addCleanup(patcher_ai_model.stop)

        dummy_image_path = "dummy/path/to/image.png"
        correct_answer = "B"

        solution = ai_helper.get_solution(dummy_image_path, correct_answer)

        self.assertEqual(solution, "AI features are currently disabled or the model is not initialized.")
        # Optionally, assert that Image.open and any model methods were NOT called.
        # (This requires patching them and then using assert_not_called())

    @patch('ai_helper.Image.open')
    @patch('ai_helper.genai.GenerativeModel')
    def test_get_solution_api_error(self, mock_GenerativeModel, mock_image_open):
        mock_model_instance = MagicMock()
        patcher_ai_enabled = patch('ai_helper.AI_ENABLED', True)
        patcher_ai_model = patch('ai_helper.ai_model', mock_model_instance)
        self.mock_ai_enabled = patcher_ai_enabled.start()
        self.mock_ai_model = patcher_ai_model.start()
        self.addCleanup(patcher_ai_enabled.stop)
        self.addCleanup(patcher_ai_model.stop)

        dummy_image_path = "dummy/path/to/image.png"
        correct_answer = "C"
        api_error_message = "Network connection failed during API call"

        mock_image_open.return_value = MagicMock(name="MockPILImageForApiError")
        # Simulate an error during the API call
        mock_model_instance.generate_content.side_effect = Exception(api_error_message)

        solution = ai_helper.get_solution(dummy_image_path, correct_answer)

        self.assertIn("Error: Failed to get explanation from AI.", solution)
        self.assertIn(api_error_message, solution) # Check if the original error message is part of the output

    @patch('ai_helper.Image.open')
    @patch('ai_helper.genai.GenerativeModel')
    def test_get_solution_prompt_blocked(self, mock_GenerativeModel, mock_image_open):
        mock_model_instance = MagicMock()
        patcher_ai_enabled = patch('ai_helper.AI_ENABLED', True)
        patcher_ai_model = patch('ai_helper.ai_model', mock_model_instance)
        self.mock_ai_enabled = patcher_ai_enabled.start()
        self.mock_ai_model = patcher_ai_model.start()
        self.addCleanup(patcher_ai_enabled.stop)
        self.addCleanup(patcher_ai_model.stop)

        dummy_image_path = "dummy/path/to/image.png"
        correct_answer = "D"
        block_reason_msg = "Content was blocked due to safety concerns."

        mock_image_open.return_value = MagicMock(name="MockPILImageForPromptBlock")

        mock_gemini_response = MagicMock()
        mock_gemini_response.text = "This text should not be used." # If text exists despite block
        # Configure prompt_feedback to indicate blocking
        mock_gemini_response.prompt_feedback = MagicMock()
        mock_gemini_response.prompt_feedback.block_reason = "SAFETY"
        mock_gemini_response.prompt_feedback.block_reason_message = block_reason_msg
        mock_model_instance.generate_content.return_value = mock_gemini_response

        solution = ai_helper.get_solution(dummy_image_path, correct_answer)

        self.assertIn("Error: AI response blocked.", solution)
        self.assertIn(block_reason_msg, solution)

    @patch('ai_helper.Image.open', side_effect=FileNotFoundError("Mocked: Image file does not exist."))
    @patch('ai_helper.genai.GenerativeModel') # Still need to mock GenerativeModel
    def test_get_solution_image_not_found(self, mock_GenerativeModel, mock_image_open_filenotfound):
        # No need to mock ai_model instance if Image.open fails first,
        # but we need AI_ENABLED to be true for the code path to try Image.open
        mock_model_instance = MagicMock() # In case it's checked before Image.open in some logic
        patcher_ai_enabled = patch('ai_helper.AI_ENABLED', True)
        patcher_ai_model = patch('ai_helper.ai_model', mock_model_instance) # Ensure model is not None

        self.mock_ai_enabled = patcher_ai_enabled.start()
        self.mock_ai_model = patcher_ai_model.start()
        self.addCleanup(patcher_ai_enabled.stop)
        self.addCleanup(patcher_ai_model.stop)

        dummy_image_path = "non_existent_image.png"
        correct_answer = "E"

        solution = ai_helper.get_solution(dummy_image_path, correct_answer)

        # Check the error message structure from your ai_helper.py
        expected_error_message = f"Error: Could not load image file '{os.path.basename(dummy_image_path)}'."
        self.assertEqual(solution, expected_error_message)

        mock_image_open_filenotfound.assert_called_once_with(dummy_image_path)
        # Ensure that generate_content was not called if the image failed to load
        mock_model_instance.generate_content.assert_not_called()

if __name__ == '__main__':
    unittest.main()