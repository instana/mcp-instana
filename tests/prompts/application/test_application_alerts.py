"""Tests for the ApplicationAlertsPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_alerts import ApplicationAlertsPrompts


class TestApplicationAlertsPrompts(unittest.TestCase):
    """Test cases for the ApplicationAlertsPrompts class."""

    def test_app_alerts_list_registered(self):
        """Test that app_alerts_list is registered in the prompt registry."""
        self.assertIn(ApplicationAlertsPrompts.app_alerts_list, PROMPT_REGISTRY)

    def test_app_alert_details_registered(self):
        """Test that app_alert_details is registered in the prompt registry."""
        self.assertIn(ApplicationAlertsPrompts.app_alert_details, PROMPT_REGISTRY)

    def test_app_alert_config_delete_registered(self):
        """Test that app_alert_config_delete is registered in the prompt registry."""
        self.assertIn(ApplicationAlertsPrompts.app_alert_config_delete, PROMPT_REGISTRY)

    def test_app_alert_config_enable_registered(self):
        """Test that app_alert_config_enable is registered in the prompt registry."""
        self.assertIn(ApplicationAlertsPrompts.app_alert_config_enable, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = ApplicationAlertsPrompts.get_prompts()
        self.assertEqual(len(prompts), 4)
        self.assertEqual(prompts[0][0], 'app_alerts_list')
        self.assertEqual(prompts[1][0], 'app_alert_details')
        self.assertEqual(prompts[2][0], 'app_alert_config_delete')
        self.assertEqual(prompts[3][0], 'app_alert_config_enable')


if __name__ == '__main__':
    unittest.main()


