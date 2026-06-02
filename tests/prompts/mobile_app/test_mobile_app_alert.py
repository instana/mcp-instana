"""Tests for the MobileAppAlertPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.mobile_app.mobile_app_alert import MobileAppAlertPrompts


class TestMobileAppAlertPrompts(unittest.TestCase):
    """Test cases for the MobileAppAlertPrompts class."""

    def test_find_mobile_app_alert_config_registered(self):
        """Test that find_mobile_app_alert_config is registered in the prompt registry."""
        # The registry contains staticmethod objects, so we need to unwrap them
        func = MobileAppAlertPrompts.find_mobile_app_alert_config
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = MobileAppAlertPrompts.get_prompts()
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[0][0], 'find_active_mobile_app_alert_configs')
        self.assertEqual(prompts[1][0], 'find_mobile_app_alert_config')

    def test_find_mobile_app_alert_config_returns_string(self):
        """Test that find_mobile_app_alert_config returns a string."""
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(id="test_id")
        self.assertIsInstance(result, str)

    def test_find_mobile_app_alert_config_without_parameters(self):
        """Test find_mobile_app_alert_config with minimal parameters."""
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(id="test_id")
        self.assertIn("Retrieve mobile app alert configuration", result)
        self.assertIn("id: test_id", result)
        self.assertIn("valid_on: None", result)

    def test_find_mobile_app_alert_config_with_id(self):
        """Test find_mobile_app_alert_config with id parameter."""
        test_id = "alert_12345"
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(id=test_id)
        self.assertIsInstance(result, str)
        self.assertIn("Retrieve mobile app alert configuration", result)
        self.assertIn(f"id: {test_id}", result)
        self.assertIn("valid_on: None", result)

    def test_find_mobile_app_alert_config_with_valid_on(self):
        """Test find_mobile_app_alert_config with valid_on parameter."""
        test_timestamp = 1609459200
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(id="test_id", valid_on=test_timestamp)
        self.assertIsInstance(result, str)
        self.assertIn("Retrieve mobile app alert configuration", result)
        self.assertIn("id: test_id", result)
        self.assertIn(f"valid_on: {test_timestamp}", result)

    def test_find_mobile_app_alert_config_with_all_parameters(self):
        """Test find_mobile_app_alert_config with all parameters."""
        test_id = "alert_xyz"
        test_timestamp = 1609545600
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(
            id=test_id,
            valid_on=test_timestamp
        )
        self.assertIsInstance(result, str)
        self.assertIn("Retrieve mobile app alert configuration", result)
        self.assertIn(f"id: {test_id}", result)
        self.assertIn(f"valid_on: {test_timestamp}", result)

    def test_find_mobile_app_alert_config_with_empty_id(self):
        """Test find_mobile_app_alert_config with empty string id."""
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(id="")
        self.assertIsInstance(result, str)
        self.assertIn("id: ", result)

    def test_find_mobile_app_alert_config_with_zero_timestamp(self):
        """Test find_mobile_app_alert_config with zero timestamp."""
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(id="test_id", valid_on=0)
        self.assertIsInstance(result, str)
        self.assertIn("valid_on: 0", result)

    def test_find_mobile_app_alert_config_with_negative_timestamp(self):
        """Test find_mobile_app_alert_config with negative timestamp."""
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(id="test_id", valid_on=-1)
        self.assertIsInstance(result, str)
        self.assertIn("valid_on: -1", result)

    def test_find_mobile_app_alert_config_with_large_timestamp(self):
        """Test find_mobile_app_alert_config with large timestamp."""
        large_timestamp = 9999999999
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(id="test_id", valid_on=large_timestamp)
        self.assertIsInstance(result, str)
        self.assertIn(f"valid_on: {large_timestamp}", result)

    def test_find_mobile_app_alert_config_prompt_structure(self):
        """Test that the prompt has the expected structure."""
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(
            id="test_id",
            valid_on=1234567890
        )
        # Check that prompt contains expected sections
        self.assertIn("Retrieve mobile app alert configuration", result)
        self.assertIn("Parameters:", result)
        self.assertIn("- id:", result)
        self.assertIn("- valid_on:", result)

    def test_get_prompts_returns_callable(self):
        """Test that get_prompts returns callable methods."""
        prompts = MobileAppAlertPrompts.get_prompts()
        for name, method in prompts:
            self.assertIsInstance(name, str)
            self.assertTrue(callable(method))

    def test_find_mobile_app_alert_config_with_special_characters(self):
        """Test find_mobile_app_alert_config with special characters in id."""
        special_id = "alert-xyz_123@test"
        result = MobileAppAlertPrompts.find_mobile_app_alert_config(id=special_id)
        self.assertIsInstance(result, str)
        self.assertIn(special_id, result)

    def test_find_mobile_app_alert_config_multiple_calls_idempotent(self):
        """Test that multiple calls with same parameters return consistent results."""
        result1 = MobileAppAlertPrompts.find_mobile_app_alert_config(
            id="test",
            valid_on=1609459200
        )
        result2 = MobileAppAlertPrompts.find_mobile_app_alert_config(
            id="test",
            valid_on=1609459200
        )
        self.assertEqual(result1, result2)


if __name__ == '__main__':
    unittest.main()
