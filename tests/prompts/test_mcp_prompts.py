"""
Unit tests for the mcp_prompts module
"""

import unittest
from unittest.mock import MagicMock, call, patch

# Import the module to test
from src.prompts.mcp_prompts import (
    INSTANA_PROMPTS,
    debug_print,
    get_all_application_prompts,
    get_all_infrastructure_prompts,
    get_all_prompts,
    prompt,
    prompts,
)


class TestMcpPrompts(unittest.TestCase):
    """Test the mcp_prompts module"""

    def setUp(self):
        """Set up test fixtures"""
        # Clear the prompts dictionary before each test
        prompts.clear()

    def tearDown(self):
        """Tear down test fixtures"""
        # Clear the prompts dictionary after each test
        prompts.clear()

    def test_prompt_decorator(self):
        """Test that the prompt decorator correctly registers functions"""
        # Define a test function
        @prompt(
            name="test_prompt",
            description="Test description",
            category="test_category",
            arguments=[{"name": "arg1", "type": "string", "required": True}]
        )
        def test_function():
            return "test_result"

        # Check that the function was registered correctly
        self.assertIn("test_prompt", prompts)
        self.assertEqual(prompts["test_prompt"]["function"], test_function)
        self.assertEqual(prompts["test_prompt"]["description"], "Test description")
        self.assertEqual(prompts["test_prompt"]["category"], "test_category")
        self.assertEqual(len(prompts["test_prompt"]["arguments"]), 1)
        self.assertEqual(prompts["test_prompt"]["arguments"][0]["name"], "arg1")
        self.assertEqual(prompts["test_prompt"]["arguments"][0]["type"], "string")
        self.assertEqual(prompts["test_prompt"]["arguments"][0]["required"], True)

        # Check that the function still works
        self.assertEqual(test_function(), "test_result")

    def test_prompt_decorator_default_arguments(self):
        """Test that the prompt decorator works with default arguments"""
        # Define a test function with minimal arguments
        @prompt(name="minimal_prompt")
        def minimal_function():
            return "minimal_result"

        # Check that the function was registered correctly with default values
        self.assertIn("minimal_prompt", prompts)
        self.assertEqual(prompts["minimal_prompt"]["function"], minimal_function)
        self.assertEqual(prompts["minimal_prompt"]["description"], "")
        self.assertEqual(prompts["minimal_prompt"]["category"], "")
        self.assertEqual(prompts["minimal_prompt"]["arguments"], [])

        # Check that the function still works
        self.assertEqual(minimal_function(), "minimal_result")

    @patch('sys.stderr')
    def test_debug_print(self, mock_stderr):
        """Test that debug_print writes to stderr"""
        debug_print("Test message")
        mock_stderr.write.assert_called()

        # Check that the message was printed to stderr
        calls = [call.write('Test message'), call.write('\n')]
        mock_stderr.assert_has_calls(calls, any_order=False)

    @patch('sys.stderr')
    def test_debug_print_multiple_args(self, mock_stderr):
        """Test that debug_print handles multiple arguments"""
        debug_print("Test", "message", 123)
        mock_stderr.write.assert_called()

        # Check that the message was printed to stderr with separate write calls
        calls = [
            call.write('Test'),
            call.write(' '),
            call.write('message'),
            call.write(' '),
            call.write('123'),
            call.write('\n')
        ]
        mock_stderr.assert_has_calls(calls, any_order=False)

    def test_get_all_application_prompts_empty(self):
        """Test get_all_application_prompts with no prompts registered"""
        result = get_all_application_prompts()
        self.assertIn("=== AVAILABLE PROMPTS ===", result)
        self.assertNotIn("get_all_application_prompts", result)

    def test_get_all_application_prompts(self):
        """Test get_all_application_prompts with prompts registered"""
        # Register some test prompts
        @prompt(
            name="app_test_prompt",
            description="App test description",
            category="application_test",
            arguments=[{"name": "arg1", "type": "string", "required": True, "description": "Test arg"}]
        )
        def app_test_function():
            pass

        @prompt(
            name="infra_test_prompt",
            description="Infra test description",
            category="infrastructure_test"
        )
        def infra_test_function():
            pass

        # Call the function
        result = get_all_application_prompts()

        # Check that the result contains the expected content
        self.assertIn("=== AVAILABLE PROMPTS ===", result)
        self.assertIn("--- APPLICATION_TEST ---", result)
        self.assertIn("🔹 app_test_prompt", result)
        self.assertIn("App test description", result)
        self.assertIn("• arg1 (string) [REQUIRED] - Test arg", result)

        # Check that it doesn't include itself
        self.assertNotIn("get_all_application_prompts", result)

    def test_get_all_infrastructure_prompts_empty(self):
        """Test get_all_infrastructure_prompts with no prompts registered"""
        result = get_all_infrastructure_prompts()
        self.assertIn("=== AVAILABLE PROMPTS ===", result)
        self.assertNotIn("get_all_infrastructure_prompts", result)

    def test_get_all_infrastructure_prompts(self):
        """Test get_all_infrastructure_prompts with prompts registered"""
        # Register some test prompts
        @prompt(
            name="app_test_prompt",
            description="App test description",
            category="application_test"
        )
        def app_test_function():
            pass

        @prompt(
            name="infra_test_prompt",
            description="Infra test description",
            category="infrastructure_test",
            arguments=[{"name": "arg1", "type": "string", "required": True, "description": "Test arg", "default": "default_value"}]
        )
        def infra_test_function():
            pass

        # Call the function
        result = get_all_infrastructure_prompts()

        # Check that the result contains the expected content
        self.assertIn("=== AVAILABLE PROMPTS ===", result)
        self.assertIn("--- INFRASTRUCTURE_TEST ---", result)
        self.assertIn("🔹 infra_test_prompt", result)
        self.assertIn("Infra test description", result)
        self.assertIn("• arg1 (string) [REQUIRED] - Test arg (default: default_value)", result)

        # Check that it doesn't include itself
        self.assertNotIn("get_all_infrastructure_prompts", result)

    def test_get_all_prompts_empty(self):
        """Test get_all_prompts with no prompts registered"""
        result = get_all_prompts()
        self.assertIn("=== AVAILABLE PROMPTS ===", result)
        self.assertNotIn("get_all_prompts", result)

    def test_get_all_prompts(self):
        """Test get_all_prompts with prompts registered"""
        # Register some test prompts
        @prompt(
            name="app_test_prompt",
            description="App test description",
            category="application_test",
            arguments=[{"name": "arg1", "type": "string", "required": False, "description": "Test arg"}]
        )
        def app_test_function():
            pass

        @prompt(
            name="infra_test_prompt",
            description="Infra test description",
            category="infrastructure_test",
            arguments=[{"name": "arg1", "type": "string", "required": True, "description": "Test arg"}]
        )
        def infra_test_function():
            pass

        @prompt(
            name="uncategorized_prompt",
            description="No category description"
        )
        def uncategorized_function():
            pass

        # Call the function
        result = get_all_prompts()

        # Check that the result contains the expected content
        self.assertIn("=== AVAILABLE PROMPTS ===", result)
        self.assertIn("--- APPLICATION_TEST ---", result)
        self.assertIn("🔹 app_test_prompt", result)
        self.assertIn("App test description", result)
        self.assertIn("• arg1 (string) - Test arg", result)

        self.assertIn("--- INFRASTRUCTURE_TEST ---", result)
        self.assertIn("🔹 infra_test_prompt", result)
        self.assertIn("Infra test description", result)
        self.assertIn("• arg1 (string) [REQUIRED] - Test arg", result)

        self.assertIn("---  ---", result)  # Empty category name for uncategorized prompts
        self.assertIn("🔹 uncategorized_prompt", result)
        self.assertIn("No category description", result)
        self.assertIn("No arguments required", result)

        # Check that it doesn't include itself
        self.assertNotIn("get_all_prompts", result)

    def test_get_all_prompts_error_handling(self):
        """Test error handling in get_all_prompts"""
        # Create a prompt with invalid data that will cause an exception
        prompts["invalid_prompt"] = "not a dict"

        # Call the function
        result = get_all_prompts()

        # Check that it handled the error gracefully
        self.assertIn("=== AVAILABLE PROMPTS ===", result)
        self.assertNotIn("invalid_prompt", result)

    def test_instana_prompts_constant(self):
        """Test that INSTANA_PROMPTS is the same as prompts"""
        self.assertEqual(INSTANA_PROMPTS, prompts)

        # Add a prompt and check that it's reflected in INSTANA_PROMPTS
        @prompt(name="test_constant_prompt")
        def test_constant_function():
            pass

        self.assertIn("test_constant_prompt", INSTANA_PROMPTS)

    def test_prompt_with_complex_arguments(self):
        """Test prompt with complex argument structures"""
        @prompt(
            name="complex_prompt",
            description="Complex prompt",
            category="test",
            arguments=[
                {
                    "name": "arg1",
                    "type": "object",
                    "required": True,
                    "description": "Complex object"
                },
                {
                    "name": "arg2",
                    "type": "list[string]",
                    "required": False,
                    "description": "List of strings"
                }
            ]
        )
        def complex_function():
            pass

        # Call get_all_prompts to format the arguments
        result = get_all_prompts()

        # Check that complex arguments are formatted correctly
        self.assertIn("🔹 complex_prompt", result)
        self.assertIn("• arg1 (object) [REQUIRED] - Complex object", result)
        self.assertIn("• arg2 (list[string]) - List of strings", result)

    def test_application_prompt_with_default_value(self):
        """Test application prompt with default value in arguments"""
        @prompt(
            name="app_default_prompt",
            description="Test application prompt with default value",
            category="application_test",
            arguments=[
                {
                    "name": "arg1",
                    "type": "string",
                    "required": False,
                    "description": "Argument with default",
                    "default": "default_value"
                }
            ]
        )
        def app_default_function():
            pass

        # Call get_all_application_prompts to format the arguments
        result = get_all_application_prompts()

        # Check that default value is included in the output
        self.assertIn("• arg1 (string) - Argument with default (default: default_value)", result)

    def test_get_prompts_with_exception(self):
        """Test that the get_*_prompts functions handle exceptions gracefully"""
        # Create a mock that raises an exception when accessed
        mock_prompts = MagicMock()
        mock_prompts.items.side_effect = Exception("Test exception")

        # Patch the prompts dictionary
        with patch('src.prompts.mcp_prompts.prompts', mock_prompts):
            # Call the functions
            app_result = get_all_application_prompts()
            infra_result = get_all_infrastructure_prompts()
            all_result = get_all_prompts()

            # Check that they handled the error gracefully
            self.assertIn("Error generating prompt list", app_result)
            self.assertIn("Test exception", app_result)
            self.assertIn("Error generating prompt list", infra_result)
            self.assertIn("Test exception", infra_result)
            self.assertIn("Error generating prompt list", all_result)
            self.assertIn("Test exception", all_result)

    def test_prompt_with_default_value(self):
        """Test prompt with default value in arguments"""
        @prompt(
            name="test_default_prompt",
            description="Test prompt with default value",
            category="test",
            arguments=[
                {
                    "name": "arg1",
                    "type": "string",
                    "required": False,
                    "description": "Argument with default",
                    "default": "default_value"
                }
            ]
        )
        def test_default_function():
            pass

        # Call get_all_prompts to format the arguments
        result = get_all_prompts()

        # Check that default value is included in the output
        self.assertIn("• arg1 (string) - Argument with default (default: default_value)", result)

    def test_self_exclusion(self):
        """Test that get_*_prompts functions exclude themselves from the output"""
        # Register the functions as prompts (they already are, but let's make sure)
        prompts["get_all_application_prompts"] = {
            "function": get_all_application_prompts,
            "description": "Test description",
            "category": "system",
            "arguments": []
        }

        prompts["get_all_infrastructure_prompts"] = {
            "function": get_all_infrastructure_prompts,
            "description": "Test description",
            "category": "system",
            "arguments": []
        }

        prompts["get_all_prompts"] = {
            "function": get_all_prompts,
            "description": "Test description",
            "category": "system",
            "arguments": []
        }

        # Call the functions
        app_result = get_all_application_prompts()
        infra_result = get_all_infrastructure_prompts()
        all_result = get_all_prompts()

        # Check that they exclude themselves
        self.assertNotIn("🔹 get_all_application_prompts", app_result)
        self.assertNotIn("🔹 get_all_infrastructure_prompts", infra_result)
        self.assertNotIn("🔹 get_all_prompts", all_result)

    def test_non_dict_prompt(self):
        """Test handling of non-dictionary prompt data"""
        # Add a non-dictionary prompt
        prompts["invalid_prompt"] = "not a dict"

        # Call the functions
        app_result = get_all_application_prompts()
        infra_result = get_all_infrastructure_prompts()
        all_result = get_all_prompts()

        # Check that the invalid prompt is not included
        self.assertNotIn("🔹 invalid_prompt", app_result)
        self.assertNotIn("🔹 invalid_prompt", infra_result)
        self.assertNotIn("🔹 invalid_prompt", all_result)


if __name__ == '__main__':
    unittest.main()
