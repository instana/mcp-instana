"""Tests for the ApplicationSettingsPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_settings import ApplicationSettingsPrompts


class TestApplicationSettingsPrompts(unittest.TestCase):
    """Test cases for the ApplicationSettingsPrompts class."""

    def test_get_all_applications_configs_registered(self):
        """Test that get_all_applications_configs is registered in the prompt registry."""
        self.assertIn(ApplicationSettingsPrompts.get_all_applications_configs, PROMPT_REGISTRY)

    def test_get_application_config_registered(self):
        """Test that get_application_config is registered in the prompt registry."""
        self.assertIn(ApplicationSettingsPrompts.get_application_config, PROMPT_REGISTRY)

    def test_get_all_endpoint_configs_registered(self):
        """Test that get_all_endpoint_configs is registered in the prompt registry."""
        self.assertIn(ApplicationSettingsPrompts.get_all_endpoint_configs, PROMPT_REGISTRY)

    def test_get_endpoint_config_registered(self):
        """Test that get_endpoint_config is registered in the prompt registry."""
        self.assertIn(ApplicationSettingsPrompts.get_endpoint_config, PROMPT_REGISTRY)

    def test_get_all_manual_service_configs_registered(self):
        """Test that get_all_manual_service_configs is registered in the prompt registry."""
        self.assertIn(ApplicationSettingsPrompts.get_all_manual_service_configs, PROMPT_REGISTRY)

    def test_add_manual_service_config_registered(self):
        """Test that add_manual_service_config is registered in the prompt registry."""
        self.assertIn(ApplicationSettingsPrompts.add_manual_service_config, PROMPT_REGISTRY)

    def test_get_service_config_registered(self):
        """Test that get_service_config is registered in the prompt registry."""
        self.assertIn(ApplicationSettingsPrompts.get_service_config, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = ApplicationSettingsPrompts.get_prompts()
        self.assertEqual(len(prompts), 7)
        self.assertEqual(prompts[0][0], 'get_all_applications_configs')
        self.assertEqual(prompts[1][0], 'get_application_config')
        self.assertEqual(prompts[2][0], 'get_all_endpoint_configs')
        self.assertEqual(prompts[3][0], 'get_endpoint_config')
        self.assertEqual(prompts[4][0], 'get_all_manual_service_configs')
        self.assertEqual(prompts[5][0], 'add_manual_service_config')
        self.assertEqual(prompts[6][0], 'get_service_config')


if __name__ == '__main__':
    unittest.main()


