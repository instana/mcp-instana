"""Tests for the WebsiteAlertPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.website.website_alert import WebsiteAlertPrompts


class TestWebsiteAlertPrompts(unittest.TestCase):
    """Test cases for the WebsiteAlertPrompts class."""

    def test_find_website_alert_config_registered(self):
        """Test that find_website_alert_config is registered in the prompt registry."""
        # The registry contains staticmethod objects, so we need to unwrap them
        func = WebsiteAlertPrompts.find_website_alert_config
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = WebsiteAlertPrompts.get_prompts()
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[0][0], 'find_active_website_alert_configs')
        self.assertEqual(prompts[1][0], 'find_website_alert_config')

    def test_find_website_alert_config_returns_string(self):
        """Test that find_website_alert_config returns a string."""
        result = WebsiteAlertPrompts.find_website_alert_config(id="test_id")
        self.assertIsInstance(result, str)

    def test_find_website_alert_config_without_parameters(self):
        """Test find_website_alert_config with minimal parameters."""
        result = WebsiteAlertPrompts.find_website_alert_config(id="test_id")
        self.assertIn("Retrieve website alert configuration", result)
        self.assertIn("id: test_id", result)
        self.assertIn("valid_on: None", result)

    def test_find_website_alert_config_with_id(self):
        """Test find_website_alert_config with id parameter."""
        test_id = "alert_12345"
        result = WebsiteAlertPrompts.find_website_alert_config(id=test_id)
        self.assertIsInstance(result, str)
        self.assertIn("Retrieve website alert configuration", result)
        self.assertIn(f"id: {test_id}", result)
        self.assertIn("valid_on: None", result)

    def test_find_website_alert_config_with_valid_on(self):
        """Test find_website_alert_config with valid_on parameter."""
        test_timestamp = 1609459200
        result = WebsiteAlertPrompts.find_website_alert_config(id="test_id", valid_on=test_timestamp)
        self.assertIsInstance(result, str)
        self.assertIn("Retrieve website alert configuration", result)
        self.assertIn("id: test_id", result)
        self.assertIn(f"valid_on: {test_timestamp}", result)

    def test_find_website_alert_config_with_all_parameters(self):
        """Test find_website_alert_config with all parameters."""
        test_id = "alert_xyz"
        test_timestamp = 1609545600
        result = WebsiteAlertPrompts.find_website_alert_config(
            id=test_id,
            valid_on=test_timestamp
        )
        self.assertIsInstance(result, str)
        self.assertIn("Retrieve website alert configuration", result)
        self.assertIn(f"id: {test_id}", result)
        self.assertIn(f"valid_on: {test_timestamp}", result)

    def test_find_website_alert_config_with_empty_id(self):
        """Test find_website_alert_config with empty string id."""
        result = WebsiteAlertPrompts.find_website_alert_config(id="")
        self.assertIsInstance(result, str)
        self.assertIn("id: ", result)

    def test_find_website_alert_config_with_zero_timestamp(self):
        """Test find_website_alert_config with zero timestamp."""
        result = WebsiteAlertPrompts.find_website_alert_config(id="test_id", valid_on=0)
        self.assertIsInstance(result, str)
        self.assertIn("valid_on: 0", result)

    def test_find_website_alert_config_with_negative_timestamp(self):
        """Test find_website_alert_config with negative timestamp."""
        result = WebsiteAlertPrompts.find_website_alert_config(id="test_id", valid_on=-1)
        self.assertIsInstance(result, str)
        self.assertIn("valid_on: -1", result)

    def test_find_website_alert_config_with_large_timestamp(self):
        """Test find_website_alert_config with large timestamp."""
        large_timestamp = 9999999999
        result = WebsiteAlertPrompts.find_website_alert_config(id="test_id", valid_on=large_timestamp)
        self.assertIsInstance(result, str)
        self.assertIn(f"valid_on: {large_timestamp}", result)

    def test_find_website_alert_config_prompt_structure(self):
        """Test that the prompt has the expected structure."""
        result = WebsiteAlertPrompts.find_website_alert_config(
            id="test_id",
            valid_on=1234567890
        )
        # Check that prompt contains expected sections
        self.assertIn("Retrieve website alert configuration", result)
        self.assertIn("Parameters:", result)
        self.assertIn("- id:", result)
        self.assertIn("- valid_on:", result)

    def test_get_prompts_returns_callable(self):
        """Test that get_prompts returns callable methods."""
        prompts = WebsiteAlertPrompts.get_prompts()
        for name, method in prompts:
            self.assertIsInstance(name, str)
            self.assertTrue(callable(method))

    def test_find_website_alert_config_with_special_characters(self):
        """Test find_website_alert_config with special characters in id."""
        special_id = "alert-xyz_123@test"
        result = WebsiteAlertPrompts.find_website_alert_config(id=special_id)
        self.assertIsInstance(result, str)
        self.assertIn(special_id, result)

    def test_find_website_alert_config_with_uuid(self):
        """Test find_website_alert_config with UUID format id."""
        uuid_id = "550e8400-e29b-41d4-a716-446655440000"
        result = WebsiteAlertPrompts.find_website_alert_config(id=uuid_id)
        self.assertIsInstance(result, str)
        self.assertIn(uuid_id, result)

    def test_find_website_alert_config_multiple_calls_idempotent(self):
        """Test that multiple calls with same parameters return consistent results."""
        result1 = WebsiteAlertPrompts.find_website_alert_config(
            id="test",
            valid_on=1609459200
        )
        result2 = WebsiteAlertPrompts.find_website_alert_config(
            id="test",
            valid_on=1609459200
        )
        self.assertEqual(result1, result2)

    def test_find_website_alert_config_different_parameters_different_output(self):
        """Test that different parameters produce different outputs."""
        result1 = WebsiteAlertPrompts.find_website_alert_config(id="alert1")
        result2 = WebsiteAlertPrompts.find_website_alert_config(id="alert2")
        self.assertNotEqual(result1, result2)

    def test_find_website_alert_config_is_static_method(self):
        """Test that find_website_alert_config is a static method."""
        self.assertTrue(isinstance(
            WebsiteAlertPrompts.__dict__['find_website_alert_config'],
            staticmethod
        ))

    def test_get_prompts_is_class_method(self):
        """Test that get_prompts is a class method."""
        self.assertTrue(hasattr(WebsiteAlertPrompts.get_prompts, '__self__'))

    def test_find_website_alert_config_returns_multiline_string(self):
        """Test that find_website_alert_config returns a multiline string."""
        result = WebsiteAlertPrompts.find_website_alert_config(id="test_id")
        self.assertGreater(len(result.split('\n')), 1)


if __name__ == '__main__':
    unittest.main()
