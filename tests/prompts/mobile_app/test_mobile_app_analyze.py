"""Tests for the MobileAppAnalyzePrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.mobile_app.mobile_app_analyze import MobileAppAnalyzePrompts


class TestMobileAppAnalyzePrompts(unittest.TestCase):
    """Test cases for the MobileAppAnalyzePrompts class."""

    def test_get_mobile_app_beacon_groups_registered(self):
        """Test that get_mobile_app_beacon_groups is registered in the prompt registry."""
        # The registry contains staticmethod objects, so we need to unwrap them
        func = MobileAppAnalyzePrompts.get_mobile_app_beacon_groups
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_all_mobile_app_beacons_registered(self):
        """Test that get_all_mobile_app_beacons is registered in the prompt registry."""
        func = MobileAppAnalyzePrompts.get_all_mobile_app_beacons
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = MobileAppAnalyzePrompts.get_prompts()
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[0][0], 'get_mobile_app_beacon_groups')
        self.assertEqual(prompts[1][0], 'get_all_mobile_app_beacons')


if __name__ == '__main__':
    unittest.main()
