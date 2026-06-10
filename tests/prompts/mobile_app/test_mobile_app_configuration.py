"""Tests for the MobileAppConfigurationPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.mobile_app.mobile_app_configuration import (
    MobileAppConfigurationPrompts,
)


class TestMobileAppConfigurationPrompts(unittest.TestCase):
    """Test cases for the MobileAppConfigurationPrompts class."""

    def test_get_mobile_apps_registered(self):
        """Test that get_mobile_apps is registered in the prompt registry."""
        # The registry contains staticmethod objects, so we need to unwrap them
        func = MobileAppConfigurationPrompts.get_all_mobile_apps
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_mobile_app_registered(self):
        """Test that get_mobile_app is registered in the prompt registry."""
        func = MobileAppConfigurationPrompts.get_mobile_app_by_id
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_mobile_app_geo_location_configuration_registered(self):
        """Test that get_mobile_app_geo_location_configuration is registered in the prompt registry."""
        func = MobileAppConfigurationPrompts.get_mobile_app_geo_location_configuration
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_mobile_app_ip_masking_configuration_registered(self):
        """Test that get_mobile_app_ip_masking_configuration is registered in the prompt registry."""
        func = MobileAppConfigurationPrompts.get_mobile_app_ip_masking_configuration
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = MobileAppConfigurationPrompts.get_prompts()
        self.assertEqual(len(prompts), 7)
        self.assertEqual(prompts[0][0], 'get_all_mobile_apps')
        self.assertEqual(prompts[1][0], 'get_mobile_app_by_id')
        self.assertEqual(prompts[2][0], 'get_mobile_app_geo_location_configuration')
        self.assertEqual(prompts[3][0], 'get_mobile_app_geo_mapping_rules')
        self.assertEqual(prompts[4][0], 'get_mobile_app_ip_masking_configuration')
        self.assertEqual(prompts[5][0], 'get_all_mobile_app_source_map_upload_configurations')
        self.assertEqual(prompts[6][0], 'get_mobile_app_source_map_upload_configuration_by_id')

    def test_get_mobile_apps_prompt_content(self):
        """Test that get_mobile_apps returns expected prompt content."""
        result = MobileAppConfigurationPrompts.get_all_mobile_apps()
        self.assertIn("Get all mobile apps", result)
        self.assertIn("configured mobile app monitoring", result)

    def test_get_mobile_app_prompt_content(self):
        """Test that get_mobile_app returns expected prompt content."""
        result = MobileAppConfigurationPrompts.get_mobile_app_by_id(mobile_app_id="app-123")
        self.assertIn("Get mobile app configuration", result)
        self.assertIn("app-123", result)

    def test_get_mobile_app_geo_location_configuration_prompt_content(self):
        """Test that get_mobile_app_geo_location_configuration returns expected prompt content."""
        result = MobileAppConfigurationPrompts.get_mobile_app_geo_location_configuration(mobile_app_id="app-123")
        self.assertIn("geo-location configuration", result)
        self.assertIn("app-123", result)

    def test_get_mobile_app_ip_masking_configuration_prompt_content(self):
        """Test that get_mobile_app_ip_masking_configuration returns expected prompt content."""
        result = MobileAppConfigurationPrompts.get_mobile_app_ip_masking_configuration(mobile_app_id="app-123")
        self.assertIn("IP masking configuration", result)
        self.assertIn("app-123", result)

    def test_all_prompts_return_strings(self):
        """Test that all prompt methods return strings."""
        prompts = MobileAppConfigurationPrompts.get_prompts()

        for name, prompt_func in prompts:
            if name == "get_all_mobile_apps":
                result = prompt_func()

            elif name == "get_mobile_app_by_id" or name == "get_mobile_app_geo_location_configuration" or (name in ('get_mobile_app_geo_mapping_rules', 'get_mobile_app_ip_masking_configuration')) or name == "get_all_mobile_app_source_map_upload_configurations":
                result = prompt_func(mobile_app_id="test")

            elif name == "get_mobile_app_source_map_upload_configuration_by_id":
                result = prompt_func(
                    mobile_app_id="test",
                    config_id="config-123"
                )

            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_class_is_instantiable(self):
        """Test that the class can be instantiated."""
        instance = MobileAppConfigurationPrompts()
        self.assertIsInstance(instance, MobileAppConfigurationPrompts)


if __name__ == '__main__':
    unittest.main()
