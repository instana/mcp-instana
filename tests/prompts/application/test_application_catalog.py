"""Tests for the ApplicationCatalogPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_catalog import ApplicationCatalogPrompts


class TestApplicationCatalogPrompts(unittest.TestCase):
    """Test cases for the ApplicationCatalogPrompts class."""

    def test_app_catalog_yesterday_registered(self):
        """Test that app_catalog_yesterday is registered in the prompt registry."""
        self.assertIn(ApplicationCatalogPrompts.app_catalog_yesterday, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = ApplicationCatalogPrompts.get_prompts()
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0][0], 'app_catalog_yesterday')


if __name__ == '__main__':
    unittest.main()


