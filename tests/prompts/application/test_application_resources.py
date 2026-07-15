"""Tests for the ApplicationResourcesPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_resources import ApplicationResourcesPrompts


class TestApplicationResourcesPrompts(unittest.TestCase):
    """Test cases for the ApplicationResourcesPrompts class."""

    def test_application_insights_summary_registered(self):
        """Test that application_insights_summary is registered in the prompt registry."""
        func = ApplicationResourcesPrompts.application_insights_summary
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = ApplicationResourcesPrompts.get_prompts()
        self.assertEqual(len(prompts), 5)
        self.assertEqual(prompts[0][0], 'application_insights_summary')
        self.assertEqual(prompts[1][0], 'get_applications')
        self.assertEqual(prompts[2][0], 'get_services')
        self.assertEqual(prompts[3][0], 'get_application_services')
        self.assertEqual(prompts[4][0], 'get_application_endpoints')

    def test_prompt_methods_return_expected_strings(self):
        """Test that each prompt method returns a non-empty descriptive string."""
        application_insights_summary = ApplicationResourcesPrompts.application_insights_summary(
            window_size=3600000,
            to_time=1672531200000,
            name_filter='TestApp',
            application_boundary_scope='ALL'
        )
        self.assertIn('Get application insights summary', application_insights_summary)
        self.assertIn('Name filter: TestApp', application_insights_summary)
        self.assertIn('Boundary scope: ALL', application_insights_summary)

        get_applications = ApplicationResourcesPrompts.get_applications(
            name_filter='TestApp',
            application_boundary_scope='ALL'
        )
        self.assertIn('Get application perspectives', get_applications)
        self.assertIn('Name filter: TestApp', get_applications)

        get_services = ApplicationResourcesPrompts.get_services(
            name_filter='TestService',
            include_snapshot_ids=True
        )
        self.assertIn('Get application services', get_services)
        self.assertIn('Name filter: TestService', get_services)
        self.assertIn('Include snapshot IDs: True', get_services)

        get_application_services = ApplicationResourcesPrompts.get_application_services(
            application_id='app-1',
            service_id='service-1',
            name_filter='TestService',
            application_boundary_scope='ALL',
            include_snapshot_ids=False
        )
        self.assertIn('Get services for application', get_application_services)
        self.assertIn('Application ID: app-1', get_application_services)
        self.assertIn('Include snapshot IDs: False', get_application_services)

        get_application_endpoints = ApplicationResourcesPrompts.get_application_endpoints(
            application_id='app-1',
            service_id='service-1',
            endpoint_id='endpoint-1',
            name_filter='TestEndpoint',
            types=['HTTP'],
            technologies=['python'],
            application_boundary_scope='ALL'
        )
        self.assertIn('Get application endpoints with', get_application_endpoints)
        self.assertIn('Endpoint ID: endpoint-1', get_application_endpoints)
        self.assertIn('Types: [\'HTTP\']', get_application_endpoints)
        self.assertIn('Technologies: [\'python\']', get_application_endpoints)


if __name__ == '__main__':
    unittest.main()
