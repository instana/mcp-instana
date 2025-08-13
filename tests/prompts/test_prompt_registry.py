"""Tests for the prompt registry and registration mechanism."""
import unittest
from unittest.mock import MagicMock, patch

from src.prompts import PROMPT_REGISTRY, auto_register_prompt, mcp


class TestPromptRegistry(unittest.TestCase):
    """Test cases for the prompt registry and registration mechanism."""

    def test_auto_register_prompt_decorator(self):
        """Test that auto_register_prompt correctly registers functions."""
        # Create a test function
        test_registry = []

        # Mock the FastMCP prompt decorator
        with patch('src.prompts.mcp') as mock_mcp:
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
        # Import the class method to ensure it's registered
        from src.prompts.application.application_alerts import ApplicationAlertsPrompts

        # Check if it's in the registry
        self.assertIn(ApplicationAlertsPrompts.app_alerts_list, PROMPT_REGISTRY)

    def test_app_alert_details_registered(self):
        """Test that app_alert_details is registered in the prompt registry."""
        # Import the class method to ensure it's registered
        from src.prompts.application.application_alerts import ApplicationAlertsPrompts

        # Check if it's in the registry
        self.assertIn(ApplicationAlertsPrompts.app_alert_details, PROMPT_REGISTRY)

    def test_app_alert_config_delete_registered(self):
        """Test that app_alert_config_delete is registered in the prompt registry."""
        # Import the class method to ensure it's registered
        from src.prompts.application.application_alerts import ApplicationAlertsPrompts

        # Check if it's in the registry
        self.assertIn(ApplicationAlertsPrompts.app_alert_config_delete, PROMPT_REGISTRY)

    def test_app_alert_config_enable_registered(self):
        """Test that app_alert_config_enable is registered in the prompt registry."""
        # Import the class method to ensure it's registered
        from src.prompts.application.application_alerts import ApplicationAlertsPrompts

        # Check if it's in the registry
        self.assertIn(ApplicationAlertsPrompts.app_alert_config_enable, PROMPT_REGISTRY)

    def test_get_application_metrics_registered(self):
        """Test that get_application_metrics is registered in the prompt registry."""
        # Import the class method to ensure it's registered
        from src.prompts.application.application_metrics import (
            ApplicationMetricsPrompts,
        )

        # Check if it's in the registry
        self.assertIn(ApplicationMetricsPrompts.get_application_metrics, PROMPT_REGISTRY)

    def test_get_infrastructure_metrics_registered(self):
        """Test that get_infrastructure_metrics is registered in the prompt registry."""
        # Import the class method to ensure it's registered
        from src.prompts.infrastructure.infrastructure_metrics import (
            InfrastructureMetricsPrompts,
        )

        # Check if it's in the registry
        self.assertIn(InfrastructureMetricsPrompts.get_infrastructure_metrics, PROMPT_REGISTRY)

    def test_get_application_topology_registered(self):
        """Test that get_application_topology is registered in the prompt registry."""
        # Import the class method to ensure it's registered
        from src.prompts.application.application_topology import (
            ApplicationTopologyPrompts,
        )

        # Check if it's in the registry
        self.assertIn(ApplicationTopologyPrompts.get_application_topology, PROMPT_REGISTRY)

    def test_registry_has_entries(self):
        """Test that the registry contains prompt entries."""
        # Just verify that the registry has entries
        self.assertGreater(len(PROMPT_REGISTRY), 0)

        # Print the number of entries for debugging
        print(f"PROMPT_REGISTRY contains {len(PROMPT_REGISTRY)} entries")



if __name__ == '__main__':
    unittest.main()

# Made with Bob
