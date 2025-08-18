"""Tests for the ApplicationResourcesPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_resources import ApplicationResourcesPrompts


class TestApplicationResourcesPrompts(unittest.TestCase):
    """Test cases for the ApplicationResourcesPrompts class."""

    def test_application_insights_summary_registered(self):
        """Test that application_insights_summary is registered in the prompt registry."""
        self.assertIn(ApplicationResourcesPrompts.application_insights_summary, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = ApplicationResourcesPrompts.get_prompts()
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0][0], 'application_insights_summary')


if __name__ == '__main__':
    unittest.main()


