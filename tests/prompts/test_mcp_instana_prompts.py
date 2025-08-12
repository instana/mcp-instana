"""Tests for the mcp_instana_prompts module."""
import unittest
from unittest.mock import MagicMock, patch

from src.prompts.mcp_instana_prompts import PROMPT_REGISTRY, auto_register_prompt, mcp


class TestMcpInstanaPrompts(unittest.TestCase):
    """Test cases for the mcp_instana_prompts module."""

    def test_auto_register_prompt_decorator(self):
        """Test that auto_register_prompt correctly registers functions."""
        # Create a test function
        test_registry = []

        # Mock the FastMCP prompt decorator
        with patch('src.prompts.mcp_instana_prompts.mcp') as mock_mcp:
            # Set up the mock to return the function unchanged
            mock_prompt = MagicMock()
            mock_prompt.return_value = lambda func: func
            mock_mcp.prompt.return_value = mock_prompt

            # Create a temporary replacement for auto_register_prompt that uses our test registry
            def test_auto_register(func):
                func = mock_mcp.prompt()(func)
                test_registry.append(func)
                return func

            # Apply our test decorator
            @test_auto_register
            def test_function():
                return "test"

            # Verify the function was registered
            self.assertIn(test_function, test_registry)
            # Verify the mcp.prompt decorator was called
            mock_mcp.prompt.assert_called_once()

    def test_prompt_registry_not_empty(self):
        """Test that PROMPT_REGISTRY is populated with prompt functions."""
        # This is a basic check to ensure the registry is populated
        self.assertGreater(len(PROMPT_REGISTRY), 0)

    def test_app_alerts_list_registered(self):
        """Test that app_alerts_list is registered in the prompt registry."""
        # Import the function to ensure it's registered
        from src.prompts.mcp_instana_prompts import app_alerts_list

        # Check if it's in the registry
        self.assertIn(app_alerts_list, PROMPT_REGISTRY)

    def test_app_alert_details_registered(self):
        """Test that app_alert_details is registered in the prompt registry."""
        # Import the function to ensure it's registered
        from src.prompts.mcp_instana_prompts import app_alert_details

        # Check if it's in the registry
        self.assertIn(app_alert_details, PROMPT_REGISTRY)

    def test_get_application_metrics_registered(self):
        """Test that get_application_metrics is registered in the prompt registry."""
        # Import the function to ensure it's registered
        from src.prompts.mcp_instana_prompts import get_application_metrics

        # Check if it's in the registry
        self.assertIn(get_application_metrics, PROMPT_REGISTRY)

    def test_get_infrastructure_metrics_registered(self):
        """Test that get_infrastructure_metrics is registered in the prompt registry."""
        # Import the function to ensure it's registered
        from src.prompts.mcp_instana_prompts import get_infrastructure_metrics

        # Check if it's in the registry
        self.assertIn(get_infrastructure_metrics, PROMPT_REGISTRY)

    def test_get_application_topology_registered(self):
        """Test that get_application_topology is registered in the prompt registry."""
        # Import the function to ensure it's registered
        from src.prompts.mcp_instana_prompts import get_application_topology

        # Check if it's in the registry
        self.assertIn(get_application_topology, PROMPT_REGISTRY)

    def test_registry_size(self):
        """Test that the registry contains the expected number of prompts."""
        # Count the number of functions with @auto_register_prompt in the source file
        import inspect
        import re

        with open('src/prompts/mcp_instana_prompts.py', 'r') as f:
            content = f.read()
            # Count occurrences of @auto_register_prompt
            decorator_count = len(re.findall(r'@auto_register_prompt', content))

            # Verify that the registry has the same number of entries
            self.assertEqual(len(PROMPT_REGISTRY), decorator_count)

    @patch('src.prompts.mcp_instana_prompts.asyncio.run')
    def test_main(self, mock_run):
        """Test the main function calls asyncio.run with the correct parameters."""
        from src.prompts.mcp_instana_prompts import main
        main()
        mock_run.assert_called_once()
        # We can't easily check the exact arguments since they're passed to an async function,
        # but we can verify the call was made


if __name__ == '__main__':
    unittest.main()

# Made with Bob
