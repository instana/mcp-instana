"""
Unit tests for the ApplicationResourcesMCPTools class
"""

import asyncio
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the application logger and replace its handlers
app_logger = logging.getLogger('src.application.application_resources')
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False  # Prevent logs from propagating to parent loggers

# Suppress traceback printing for expected test exceptions
import traceback

original_print_exception = traceback.print_exception
original_print_exc = traceback.print_exc

def custom_print_exception(etype, value, tb, limit=None, file=None, chain=True):
    # Skip printing exceptions from the mock side_effect
    if isinstance(value, Exception) and str(value) == "Test error":
        return
    original_print_exception(etype, value, tb, limit, file, chain)

def custom_print_exc(limit=None, file=None, chain=True):
    # Just do nothing - this will suppress all traceback printing from print_exc
    pass

traceback.print_exception = custom_print_exception
traceback.print_exc = custom_print_exc

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Just pass the API client directly
            kwargs['api_client'] = self.resources_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_topology_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_resources_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_catalog_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_analyze_api'] = MagicMock()
sys.modules['instana_client.api.application_resources_api'] = MagicMock()
sys.modules['instana_client.api.application_metrics_api'] = MagicMock()
sys.modules['instana_client.api.application_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.api.application_catalog_api'] = MagicMock()
sys.modules['instana_client.api.application_analyze_api'] = MagicMock()
sys.modules['instana_client.api.events_api'] = MagicMock()
sys.modules['instana_client.api.log_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.get_available_metrics_query'] = MagicMock()
sys.modules['instana_client.models.get_available_plugins_query'] = MagicMock()
sys.modules['instana_client.models.get_infrastructure_query'] = MagicMock()
sys.modules['instana_client.models.get_infrastructure_groups_query'] = MagicMock()
sys.modules['fastmcp'] = MagicMock()
sys.modules['fastmcp.server'] = MagicMock()
sys.modules['fastmcp.server.dependencies'] = MagicMock()
sys.modules['pydantic'] = MagicMock()

# Mock the get_http_headers function
mock_get_http_headers = MagicMock(return_value={})
sys.modules['fastmcp.server.dependencies'].get_http_headers = mock_get_http_headers

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_analyze_api = MagicMock()
mock_topology_api = MagicMock()
mock_resources_api = MagicMock()
mock_catalog_api = MagicMock()
mock_app_resources_api = MagicMock()
mock_app_metrics_api = MagicMock()
mock_app_alert_config_api = MagicMock()
mock_app_catalog_api = MagicMock()
mock_app_analyze_api = MagicMock()
mock_events_api = MagicMock()
mock_log_alert_config_api = MagicMock()
mock_metrics_query = MagicMock()
mock_plugins_query = MagicMock()
mock_infra_query = MagicMock()
mock_groups_query = MagicMock()

# Add __name__ attribute to mock classes
mock_analyze_api.__name__ = "InfrastructureAnalyzeApi"
mock_topology_api.__name__ = "InfrastructureTopologyApi"
mock_resources_api.__name__ = "InfrastructureResourcesApi"
mock_catalog_api.__name__ = "InfrastructureCatalogApi"
mock_app_resources_api.__name__ = "ApplicationResourcesApi"
mock_app_metrics_api.__name__ = "ApplicationMetricsApi"
mock_app_alert_config_api.__name__ = "ApplicationAlertConfigurationApi"
mock_app_catalog_api.__name__ = "ApplicationCatalogApi"
mock_app_analyze_api.__name__ = "ApplicationAnalyzeApi"
mock_events_api.__name__ = "EventsApi"
mock_log_alert_config_api.__name__ = "LogAlertConfigurationApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.infrastructure_analyze_api'].InfrastructureAnalyzeApi = mock_analyze_api
sys.modules['instana_client.api.infrastructure_topology_api'].InfrastructureTopologyApi = mock_topology_api
sys.modules['instana_client.api.infrastructure_resources_api'].InfrastructureResourcesApi = mock_resources_api
sys.modules['instana_client.api.infrastructure_catalog_api'].InfrastructureCatalogApi = mock_catalog_api
sys.modules['instana_client.api.application_resources_api'].ApplicationResourcesApi = mock_app_resources_api
sys.modules['instana_client.api.application_metrics_api'].ApplicationMetricsApi = mock_app_metrics_api
sys.modules['instana_client.api.application_alert_configuration_api'].ApplicationAlertConfigurationApi = mock_app_alert_config_api
sys.modules['instana_client.api.application_catalog_api'].ApplicationCatalogApi = mock_app_catalog_api
sys.modules['instana_client.api.application_analyze_api'].ApplicationAnalyzeApi = mock_app_analyze_api
sys.modules['instana_client.api.events_api'].EventsApi = mock_events_api
sys.modules['instana_client.api.log_alert_configuration_api'].LogAlertConfigurationApi = mock_log_alert_config_api
sys.modules['instana_client.models.get_available_metrics_query'].GetAvailableMetricsQuery = mock_metrics_query
sys.modules['instana_client.models.get_available_plugins_query'].GetAvailablePluginsQuery = mock_plugins_query
sys.modules['instana_client.models.get_infrastructure_query'].GetInfrastructureQuery = mock_infra_query
sys.modules['instana_client.models.get_infrastructure_groups_query'].GetInfrastructureGroupsQuery = mock_groups_query

# Patch the with_header_auth decorator before importing the module
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.application.application_resources import ApplicationResourcesMCPTools


class TestApplicationResourcesMCPTools(unittest.TestCase):
    """Test the ApplicationResourcesMCPTools class"""


    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_app_resources_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.app_resources_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"

        self.client = ApplicationResourcesMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.resources_api = self.app_resources_api

        # Patch the logger to prevent logging during tests
        patcher = patch('src.application.application_resources.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)
    def tearDown(self):
        """Tear down test fixtures"""
        # No need to stop patchers since we're directly mocking the module imports
        pass
    @patch('src.application.application_resources.datetime')
    def test_get_application_endpoints_with_defaults(self, mock_datetime):
        """Test get_application_endpoints with default parameters"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "endpoint1", "name": "Endpoint 1", "type": "HTTP"},
                {"id": "endpoint2", "name": "Endpoint 2", "type": "HTTP"}
            ],
            "page": 1,
            "pageSize": 10,
            "totalItems": 2
        }
        self.client.resources_api.get_application_endpoints = MagicMock(return_value=mock_result)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_application_endpoints())

        # Check that the mock was called with the correct arguments
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_window_size = 60 * 60 * 1000  # 1 hour in milliseconds

        self.client.resources_api.get_application_endpoints.assert_called_once_with(
            name_filter=None,
            types=None,
            technologies=None,
            window_size=expected_window_size,
            to=expected_to_time,
            page=None,
            page_size=None,
            application_boundary_scope=None
        )

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_application_endpoints_with_params(self):
        """Test get_application_endpoints with specific parameters"""
        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "endpoint1", "name": "Endpoint 1", "type": "HTTP"}
            ],
            "page": 1,
            "pageSize": 10,
            "totalItems": 1
        }
        self.client.resources_api.get_application_endpoints = MagicMock(return_value=mock_result)

        # Call the method with specific parameters
        name_filter = "test"
        types = ["HTTP"]
        technologies = ["Java"]
        window_size = 3600000  # 1 hour in milliseconds
        to_time = 1625097600000  # Example timestamp
        page = 1
        page_size = 10
        application_boundary_scope = "INBOUND"

        result = asyncio.run(self.client.get_application_endpoints(
            name_filter=name_filter,
            types=types,
            technologies=technologies,
            window_size=window_size,
            to_time=to_time,
            page=page,
            page_size=page_size,
            application_boundary_scope=application_boundary_scope
        ))

        # Check that the mock was called with the correct arguments
        self.client.resources_api.get_application_endpoints.assert_called_once_with(
            name_filter=name_filter,
            types=types,
            technologies=technologies,
            window_size=window_size,
            to=to_time,
            page=page,
            page_size=page_size,
            application_boundary_scope=application_boundary_scope
        )

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_application_endpoints_error(self):
        """Test get_application_endpoints error handling"""
        # Set up the mock to raise an exception
        self.client.resources_api.get_application_endpoints = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_application_endpoints())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get application endpoints", result["error"])
        self.assertIn("Test error", result["error"])

    @patch('src.application.application_resources.datetime')
    def test_get_application_services_with_defaults(self, mock_datetime):
        """Test get_application_services with default parameters"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "service1", "label": "Service A", "technologies": ["Java"]},
                {"id": "service2", "label": "Service B", "technologies": ["Node.js"]},
                {"id": "service3", "label": "Service C", "technologies": ["Python"]}
            ],
            "page": 1,
            "pageSize": 10,
            "totalItems": 3
        }
        self.client.resources_api.get_application_services = MagicMock(return_value=mock_result)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_application_services())

        # Check that the mock was called with the correct arguments
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_window_size = 60 * 60 * 1000  # 1 hour in milliseconds

        self.client.resources_api.get_application_services.assert_called_once_with(
            name_filter=None,
            window_size=expected_window_size,
            to=expected_to_time,
            page=None,
            page_size=None,
            application_boundary_scope=None,
            include_snapshot_ids=None
        )

        # Check that the result contains the expected data
        self.assertIn("message", result)
        self.assertIn("service_labels", result)
        self.assertIn("services", result)
        self.assertEqual(len(result["services"]), 3)
        self.assertEqual(result["services"][0]["label"], "Service A")
        self.assertEqual(result["services"][1]["label"], "Service B")
        self.assertEqual(result["services"][2]["label"], "Service C")
        self.assertEqual(result["total_available"], 3)
        self.assertEqual(result["showing"], 3)

    def test_get_application_services_with_params(self):
        """Test get_application_services with specific parameters"""
        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "service1", "label": "Service A", "technologies": ["Java"]}
            ],
            "page": 1,
            "pageSize": 10,
            "totalItems": 1
        }
        self.client.resources_api.get_application_services = MagicMock(return_value=mock_result)

        # Call the method with specific parameters
        name_filter = "Service A"
        window_size = 3600000  # 1 hour in milliseconds
        to_time = 1625097600000  # Example timestamp
        page = 1
        page_size = 10
        application_boundary_scope = "INBOUND"
        include_snapshot_ids = True

        result = asyncio.run(self.client.get_application_services(
            name_filter=name_filter,
            window_size=window_size,
            to_time=to_time,
            page=page,
            page_size=page_size,
            application_boundary_scope=application_boundary_scope,
            include_snapshot_ids=include_snapshot_ids
        ))

        # Check that the mock was called with the correct arguments
        self.client.resources_api.get_application_services.assert_called_once_with(
            name_filter=name_filter,
            window_size=window_size,
            to=to_time,
            page=page,
            page_size=page_size,
            application_boundary_scope=application_boundary_scope,
            include_snapshot_ids=include_snapshot_ids
        )

        # Check that the result contains the expected data
        self.assertIn("services", result)
        self.assertEqual(len(result["services"]), 1)
        self.assertEqual(result["services"][0]["label"], "Service A")

    def test_get_application_services_error(self):
        """Test get_application_services error handling"""
        # Set up the mock to raise an exception
        self.client.resources_api.get_application_services = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_application_services())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get application services", result["error"])
        self.assertIn("Test error", result["error"])

    @patch('src.application.application_resources.datetime')
    def test_get_applications_with_defaults(self, mock_datetime):
        """Test get_applications with default parameters"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "app1", "label": "Application A"},
                {"id": "app2", "label": "Application B"},
                {"id": "app3", "label": "Application C"}
            ],
            "page": 1,
            "pageSize": 10,
            "totalItems": 3
        }
        self.client.resources_api.get_applications = MagicMock(return_value=mock_result)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_applications())

        # Check that the mock was called with the correct arguments
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_window_size = 60 * 60 * 1000  # 1 hour in milliseconds

        self.client.resources_api.get_applications.assert_called_once_with(
            name_filter=None,
            window_size=expected_window_size,
            to=expected_to_time,
            page=None,
            page_size=None,
            application_boundary_scope=None
        )

        # Check that the result contains the expected data
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "Application A")
        self.assertEqual(result[1], "Application B")
        self.assertEqual(result[2], "Application C")

    def test_get_applications_with_params(self):
        """Test get_applications with specific parameters"""
        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "app1", "label": "Application A"}
            ],
            "page": 1,
            "pageSize": 10,
            "totalItems": 1
        }
        self.client.resources_api.get_applications = MagicMock(return_value=mock_result)

        # Call the method with specific parameters
        name_filter = "Application A"
        window_size = 3600000  # 1 hour in milliseconds
        to_time = 1625097600000  # Example timestamp
        page = 1
        page_size = 10
        application_boundary_scope = "INBOUND"

        result = asyncio.run(self.client.get_applications(
            name_filter=name_filter,
            window_size=window_size,
            to_time=to_time,
            page=page,
            page_size=page_size,
            application_boundary_scope=application_boundary_scope
        ))

        # Check that the mock was called with the correct arguments
        self.client.resources_api.get_applications.assert_called_once_with(
            name_filter=name_filter,
            window_size=window_size,
            to=to_time,
            page=page,
            page_size=page_size,
            application_boundary_scope=application_boundary_scope
        )

        # Check that the result contains the expected data
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "Application A")

    def test_get_applications_error(self):
        """Test get_applications error handling"""
        # Set up the mock to raise an exception
        self.client.resources_api.get_applications = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_applications())

        # Check that the result contains an error message
        self.assertEqual(len(result), 1)
        self.assertIn("Error: Failed to get applications", result[0])
        self.assertIn("Test error", result[0])

    @patch('src.application.application_resources.datetime')
    def test_get_services_with_defaults(self, mock_datetime):
        """Test get_services with default parameters"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "service1", "label": "Service A"},
                {"id": "service2", "label": "Service B"},
                {"id": "service3", "label": "Service C"}
            ],
            "page": 1,
            "pageSize": 10,
            "totalItems": 3
        }
        self.client.resources_api.get_services = MagicMock(return_value=mock_result)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_services())

        # Check that the mock was called with the correct arguments
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_window_size = 60 * 60 * 1000  # 1 hour in milliseconds

        self.client.resources_api.get_services.assert_called_once_with(
            name_filter=None,
            window_size=expected_window_size,
            to=expected_to_time,
            page=None,
            page_size=None,
            include_snapshot_ids=None
        )

        # Check that the result contains the expected data
        self.assertIn("Services found in your environment:", result)
        self.assertIn("Service A", result)
        self.assertIn("Service B", result)
        self.assertIn("Service C", result)
        self.assertIn("Showing 3 out of 3 total services.", result)

    def test_get_services_with_params(self):
        """Test get_services with specific parameters"""
        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "service1", "label": "Service A"}
            ],
            "page": 1,
            "pageSize": 10,
            "totalItems": 1
        }
        self.client.resources_api.get_services = MagicMock(return_value=mock_result)

        # Call the method with specific parameters
        name_filter = "Service A"
        window_size = 3600000  # 1 hour in milliseconds
        to_time = 1625097600000  # Example timestamp
        page = 1
        page_size = 10
        include_snapshot_ids = True

        result = asyncio.run(self.client.get_services(
            name_filter=name_filter,
            window_size=window_size,
            to_time=to_time,
            page=page,
            page_size=page_size,
            include_snapshot_ids=include_snapshot_ids
        ))

        # Check that the mock was called with the correct arguments
        self.client.resources_api.get_services.assert_called_once_with(
            name_filter=name_filter,
            window_size=window_size,
            to=to_time,
            page=page,
            page_size=page_size,
            include_snapshot_ids=include_snapshot_ids
        )

        # Check that the result contains the expected data
        self.assertIn("Services found in your environment:", result)
        self.assertIn("Service A", result)
        self.assertIn("Showing 1 out of 1 total services.", result)

    def test_get_services_error(self):
        """Test get_services error handling"""
        # Set up the mock to raise an exception
        self.client.resources_api.get_services = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_services())

        # Check that the result contains an error message
        self.assertIn("Error: Failed to get services", result)
        self.assertIn("Test error", result)


if __name__ == '__main__':
    unittest.main()

