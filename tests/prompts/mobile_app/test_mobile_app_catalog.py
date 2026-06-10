"""Tests for the MobileAppCatalogPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.mobile_app.mobile_app_catalog import MobileAppCatalogPrompts


class TestMobileAppCatalogPrompts(unittest.TestCase):
    """Test cases for the MobileAppCatalogPrompts class."""

    def test_get_mobile_app_catalog_tags_registered(self):
        """Test that get_mobile_app_catalog_tags is registered in the prompt registry."""
        func = MobileAppCatalogPrompts.get_mobile_app_tag_catalog
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_mobile_app_catalog_metrics_registered(self):
        """Test that get_mobile_app_catalog_metrics is registered in the prompt registry."""
        # The registry contains staticmethod objects, so we need to unwrap them
        func = MobileAppCatalogPrompts.get_mobile_app_metric_catalog
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = MobileAppCatalogPrompts.get_prompts()
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[0][0], 'get_mobile_app_tag_catalog')
        self.assertEqual(prompts[1][0], 'get_mobile_app_metric_catalog')


if __name__ == '__main__':
    unittest.main()
