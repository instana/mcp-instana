"""Tests for the ApplicationMetricsPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_metrics import ApplicationMetricsPrompts


class TestApplicationMetricsPrompts(unittest.TestCase):
    """Test cases for the ApplicationMetricsPrompts class."""

    def test_get_application_metrics_registered(self):
        """Test that get_application_metrics is registered in the prompt registry."""
        self.assertIn(ApplicationMetricsPrompts.get_application_metrics, PROMPT_REGISTRY)

    def test_get_application_endpoints_metrics_registered(self):
        """Test that get_application_endpoints_metrics is registered in the prompt registry."""
        self.assertIn(ApplicationMetricsPrompts.get_application_endpoints_metrics, PROMPT_REGISTRY)

    def test_get_application_service_metrics_registered(self):
        """Test that get_application_service_metrics is registered in the prompt registry."""
        self.assertIn(ApplicationMetricsPrompts.get_application_service_metrics, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = ApplicationMetricsPrompts.get_prompts()
        self.assertEqual(len(prompts), 3)
        self.assertEqual(prompts[0][0], 'get_application_metrics')
        self.assertEqual(prompts[1][0], 'get_application_endpoints_metrics')
        self.assertEqual(prompts[2][0], 'get_application_service_metrics')


if __name__ == '__main__':
    unittest.main()


