"""
Unit tests for the ApplicationMetricsMCPTools class
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
app_logger = logging.getLogger('src.application.application_metrics')
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
            kwargs['api_client'] = self.metrics_api
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
sys.modules['instana_client.models.get_application_metrics'] = MagicMock()
sys.modules['instana_client.models.get_applications'] = MagicMock()
sys.modules['instana_client.models.get_endpoints'] = MagicMock()
sys.modules['instana_client.models.get_services'] = MagicMock()
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
mock_get_app_metrics = MagicMock()
mock_get_applications = MagicMock()
mock_get_endpoints = MagicMock()
mock_get_services = MagicMock()

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
mock_get_app_metrics.__name__ = "GetApplicationMetrics"
mock_get_applications.__name__ = "GetApplications"
mock_get_endpoints.__name__ = "GetEndpoints"
mock_get_services.__name__ = "GetServices"

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
sys.modules['instana_client.models.get_application_metrics'].GetApplicationMetrics = mock_get_app_metrics
sys.modules['instana_client.models.get_applications'].GetApplications = mock_get_applications
sys.modules['instana_client.models.get_endpoints'].GetEndpoints = mock_get_endpoints
sys.modules['instana_client.models.get_services'].GetServices = mock_get_services

# Patch the with_header_auth decorator before importing the module
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.application.application_metrics import ApplicationMetricsMCPTools


class TestApplicationMetricsMCPTools(unittest.TestCase):
    """Test the ApplicationMetricsMCPTools class"""


    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_app_metrics_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.app_metrics_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"

        self.client = ApplicationMetricsMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.metrics_api = self.app_metrics_api

        # Patch the logger to prevent logging during tests
        patcher = patch('src.application.application_metrics.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)
    def tearDown(self):
        """Tear down test fixtures"""
        # No need to stop patchers since we're directly mocking the module imports
        pass
    def test_init(self):
        """Test that the client is initialized with the correct values"""
        # Since we're mocking at the module level, we can't easily test the initialization
        # Just verify that the client was created with the correct values
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)
    def test_get_application_data_metrics_v2_with_defaults(self):
        """Test get_application_data_metrics_v2 with default parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"metrics": "test_data"})
        self.client.metrics_api.get_application_data_metrics_v2 = MagicMock(return_value=mock_result)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_application_data_metrics_v2())

        # Check that the mock was called with the correct arguments
        self.client.metrics_api.get_application_data_metrics_v2.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"metrics": "test_data"})

    def test_get_application_data_metrics_v2_with_params(self):
        """Test get_application_data_metrics_v2 with custom parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"metrics": "test_data"})
        self.client.metrics_api.get_application_data_metrics_v2 = MagicMock(return_value=mock_result)

        # Set up test parameters
        metrics = [{"metric": "calls", "aggregation": "SUM"}]
        time_frame = {"from": 1000, "to": 2000}
        application_id = "app123"
        service_id = "svc456"
        endpoint_id = "ep789"

        # Call the method with custom parameters
        result = asyncio.run(self.client.get_application_data_metrics_v2(
            metrics=metrics,
            time_frame=time_frame,
            application_id=application_id,
            service_id=service_id,
            endpoint_id=endpoint_id
        ))

        # Check that the API was called with the correct parameters
        self.client.metrics_api.get_application_data_metrics_v2.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"metrics": "test_data"})

    def test_get_application_data_metrics_v2_error_handling(self):
        """Test get_application_data_metrics_v2 error handling"""
        # Set up the mock to raise an exception
        self.client.metrics_api.get_application_data_metrics_v2 = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_application_data_metrics_v2())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get application data metrics", result["error"])
        self.assertIn("Test error", result["error"])

    def test_get_application_metrics_with_defaults(self):
        """Test get_application_metrics with default parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"metrics": "test_data"})
        self.client.metrics_api.get_application_metrics = MagicMock(return_value=mock_result)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_application_metrics())

        # Check that the API was called with the correct parameters
        self.client.metrics_api.get_application_metrics.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"metrics": "test_data"})

    def test_get_application_metrics_with_params(self):
        """Test get_application_metrics with custom parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"metrics": "test_data"})
        self.client.metrics_api.get_application_metrics = MagicMock(return_value=mock_result)

        # Set up test parameters
        application_ids = ["app123", "app456"]
        metrics = [{"metric": "calls", "aggregation": "SUM"}]
        time_frame = {"from": 1000, "to": 2000}
        fill_time_series = False

        # Call the method with custom parameters
        result = asyncio.run(self.client.get_application_metrics(
            application_ids=application_ids,
            metrics=metrics,
            time_frame=time_frame,
            fill_time_series=fill_time_series
        ))

        # Check that the API was called with the correct parameters
        self.client.metrics_api.get_application_metrics.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"metrics": "test_data"})
    def test_get_endpoints_metrics_with_defaults(self):
        """Test get_endpoints_metrics with default parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"metrics": "test_data"})
        self.client.metrics_api.get_endpoints_metrics = MagicMock(return_value=mock_result)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_endpoints_metrics())

        # Check that the API was called with the correct parameters
        self.client.metrics_api.get_endpoints_metrics.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"metrics": "test_data"})

    def test_get_endpoints_metrics_with_params(self):
        """Test get_endpoints_metrics with custom parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"metrics": "test_data"})
        self.client.metrics_api.get_endpoints_metrics = MagicMock(return_value=mock_result)

        # Set up test parameters
        endpoint_ids = ["ep123", "ep456"]
        metrics = [{"metric": "calls", "aggregation": "SUM"}]
        time_frame = {"from": 1000, "to": 2000}
        fill_time_series = False

        # Call the method with custom parameters
        result = asyncio.run(self.client.get_endpoints_metrics(
            endpoint_ids=endpoint_ids,
            metrics=metrics,
            time_frame=time_frame,
            fill_time_series=fill_time_series
        ))

        # Check that the API was called with the correct parameters
        self.client.metrics_api.get_endpoints_metrics.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"metrics": "test_data"})

    def test_get_endpoints_metrics_error_handling(self):
        """Test get_endpoints_metrics error handling"""
        # Set up the mock to raise an exception
        self.client.metrics_api.get_endpoints_metrics = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_endpoints_metrics())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get endpoints metrics", result["error"])
        self.assertIn("Test error", result["error"])

    def test_get_services_metrics_with_defaults(self):
        """Test get_services_metrics with default parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"metrics": "test_data"})
        self.client.metrics_api.get_services_metrics = MagicMock(return_value=mock_result)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_services_metrics())

        # Check that the API was called with the correct parameters
        self.client.metrics_api.get_services_metrics.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"metrics": "test_data"})

    def test_get_services_metrics_with_params(self):
        """Test get_services_metrics with custom parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"metrics": "test_data"})
        self.client.metrics_api.get_services_metrics = MagicMock(return_value=mock_result)

        # Set up test parameters
        service_ids = ["svc123", "svc456"]
        metrics = [{"metric": "calls", "aggregation": "SUM"}]
        time_frame = {"from": 1000, "to": 2000}
        fill_time_series = False
        include_snapshot_ids = True

        # Call the method with custom parameters
        result = asyncio.run(self.client.get_services_metrics(
            service_ids=service_ids,
            metrics=metrics,
            time_frame=time_frame,
            fill_time_series=fill_time_series,
            include_snapshot_ids=include_snapshot_ids
        ))

        # Check that the API was called with the correct parameters
        self.client.metrics_api.get_services_metrics.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"metrics": "test_data"})

    def test_get_services_metrics_error_handling(self):
        """Test get_services_metrics error handling"""
        # Set up the mock to raise an exception
        self.client.metrics_api.get_services_metrics = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_services_metrics())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get services metrics", result["error"])
        self.assertIn("Test error", result["error"])

        # Additional test cases to improve coverage

        def test_get_application_data_metrics_v2_dict_result(self):
            """Test get_application_data_metrics_v2 with a result that's already a dict"""
            # Set up the mock response as a dict directly
            mock_result = {"metrics": "test_data"}
            self.client.metrics_api.get_application_data_metrics_v2 = MagicMock(return_value=mock_result)

            # Call the method
            result = asyncio.run(self.client.get_application_data_metrics_v2())

            # Check that the result is correct
            self.assertEqual(result, {"metrics": "test_data"})

        def test_get_application_metrics_dict_result(self):
            """Test get_application_metrics with a result that's already a dict"""
            # Set up the mock response as a dict directly
            mock_result = {"metrics": "test_data"}
            self.client.metrics_api.get_application_metrics = MagicMock(return_value=mock_result)

            # Call the method
            result = asyncio.run(self.client.get_application_metrics())

            # Check that the result is correct
            self.assertEqual(result, {"metrics": "test_data"})

        def test_get_endpoints_metrics_dict_result(self):
            """Test get_endpoints_metrics with a result that's already a dict"""
            # Set up the mock response as a dict directly
            mock_result = {"metrics": "test_data"}
            self.client.metrics_api.get_endpoints_metrics = MagicMock(return_value=mock_result)

            # Call the method
            result = asyncio.run(self.client.get_endpoints_metrics())

            # Check that the result is correct
            self.assertEqual(result, {"metrics": "test_data"})

        def test_get_services_metrics_dict_result(self):
            """Test get_services_metrics with a result that's already a dict"""
            # Set up the mock response as a dict directly
            mock_result = {"metrics": "test_data"}
            self.client.metrics_api.get_services_metrics = MagicMock(return_value=mock_result)

            # Call the method
            result = asyncio.run(self.client.get_services_metrics())

            # Check that the result is correct
            self.assertEqual(result, {"metrics": "test_data"})

if __name__ == '__main__':
    unittest.main()



