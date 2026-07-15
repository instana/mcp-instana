"""
Unit tests for the ApplicationResourcesMCPTools class
"""

import asyncio
import json
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch

import src


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use DEBUG level to see all logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get the application logger and enable it for debugging
app_logger = logging.getLogger('src.application.application_resources')
app_logger.setLevel(logging.DEBUG)

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

# Create mock modules and classes BEFORE importing anything from src
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.application_resources_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_resources_api = MagicMock()

# Add __name__ attribute to mock classes
mock_resources_api.__name__ = "ApplicationResourcesApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.application_resources_api'].ApplicationResourcesApi = mock_resources_api

with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Now import the class to test - it will use our mocked decorator
    from src.application.application_resources import ApplicationResourcesMCPTools


class TestApplicationResourcesMCPTools(unittest.TestCase):
    """Test the ApplicationResourcesMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_resources_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.resources_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = ApplicationResourcesMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.resources_api = self.resources_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_applications_internal_success_with_to_dict(self):
        """Test _get_applications_internal with successful response that has to_dict method"""
        # Mock the API response with to_dict method
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "items": [
                {
                    "id": "app-123",
                    "label": "Test Application",
                    "boundaryScope": "ALL"
                }
            ]
        }
        self.resources_api.get_applications.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client._get_applications_internal(
            name_filter="Test Application",
            window_size=3600000,
            to_time=1234567890000
        ))

        # Verify API was called with correct parameters
        self.resources_api.get_applications.assert_called_once_with(
            name_filter="Test Application",
            window_size=3600000,
            to=1234567890000,
            page=None,
            page_size=None,
            application_boundary_scope=None
        )

        # Verify result
        self.assertIn("items", result)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["label"], "Test Application")

    def test_get_applications_internal_success_without_to_dict(self):
        """Test _get_applications_internal with response that doesn't have to_dict method"""
        # Mock the API response as a plain dict
        mock_result = {
            "items": [
                {
                    "id": "app-456",
                    "label": "Another Application"
                }
            ]
        }
        self.resources_api.get_applications.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client._get_applications_internal(
            name_filter="Another Application"
        ))

        # Verify result
        self.assertIn("items", result)
        self.assertEqual(result["items"][0]["label"], "Another Application")

    def test_get_applications_internal_with_all_none_params(self):
        """Test _get_applications_internal with all None parameters"""
        # Mock the API response
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"items": []}
        self.resources_api.get_applications.return_value = mock_result

        # Call the method with no parameters
        result = asyncio.run(self.client._get_applications_internal())

        # Verify API was called with None values
        self.resources_api.get_applications.assert_called_once_with(
            name_filter=None,
            window_size=None,
            to=None,
            page=None,
            page_size=None,
            application_boundary_scope=None
        )

        # Verify result
        self.assertIn("items", result)

    def test_get_applications_internal_error_handling(self):
        """Test _get_applications_internal error handling"""
        # Mock the API to raise an exception
        self.resources_api.get_applications.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client._get_applications_internal(
            name_filter="Test"
        ))

        # Check that error is returned
        self.assertIn("error", result)
        self.assertIn("Failed to get applications", result["error"])
        self.assertIn("Test error", result["error"])

    def test_get_applications_internal_debug_logs_called(self):
        """Test that debug logs are called in _get_applications_internal"""
        # Mock the API response
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "items": [{"id": "app-1", "label": "App1"}]
        }
        self.resources_api.get_applications.return_value = mock_result

        # Patch the logger to verify it's called
        with patch('src.application.application_resources.logger') as mock_logger:
            # Call the method
            result = asyncio.run(self.client._get_applications_internal(
                name_filter="App1"
            ))

            # Verify the first debug log was called (line 63)
            mock_logger.debug.assert_any_call(
                "_get_applications_internal called with name_filter=App1"
            )

            # Verify the second debug log was called (line 81)
            # The exact format depends on the result_dict
            calls = [str(call) for call in mock_logger.debug.call_args_list]
            self.assertTrue(
                any("Result from _get_applications_internal" in str(call) for call in calls),
                "Second debug log should be called"
            )

            # Verify the method completed successfully
            self.assertIn("items", result)

    def test_get_applications_internal_with_empty_result(self):
        """Test _get_applications_internal with empty result"""
        # Mock the API response with empty items
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"items": []}
        self.resources_api.get_applications.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client._get_applications_internal(
            name_filter="NonExistent"
        ))

        # Verify result has empty items
        self.assertIn("items", result)
        self.assertEqual(len(result["items"]), 0)

    def test_get_applications_internal_with_multiple_applications(self):
        """Test _get_applications_internal with multiple applications"""
        # Mock the API response with multiple applications
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "items": [
                {"id": "app-1", "label": "App1"},
                {"id": "app-2", "label": "App2"},
                {"id": "app-3", "label": "App3"}
            ]
        }
        self.resources_api.get_applications.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client._get_applications_internal())

        # Verify result has all applications
        self.assertIn("items", result)
        self.assertEqual(len(result["items"]), 3)

    def test_get_applications_internal_with_specific_window_size(self):
        """Test _get_applications_internal with specific window_size"""
        # Mock the API response
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"items": []}
        self.resources_api.get_applications.return_value = mock_result

        # Call the method with specific window_size
        asyncio.run(self.client._get_applications_internal(
            window_size=7200000  # 2 hours
        ))

        # Verify API was called with correct window_size
        self.resources_api.get_applications.assert_called_once()
        call_args = self.resources_api.get_applications.call_args
        self.assertEqual(call_args[1]['window_size'], 7200000)

    def test_get_applications_internal_with_specific_to_time(self):
        """Test _get_applications_internal with specific to_time"""
        # Mock the API response
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"items": []}
        self.resources_api.get_applications.return_value = mock_result

        # Call the method with specific to_time
        to_time = 1609459200000  # 2021-01-01 00:00:00 UTC
        asyncio.run(self.client._get_applications_internal(
            to_time=to_time
        ))

        # Verify API was called with correct to_time
        self.resources_api.get_applications.assert_called_once()
        call_args = self.resources_api.get_applications.call_args
        self.assertEqual(call_args[1]['to'], to_time)

    def test_get_applications_internal_error_log_called(self):
        """Test that error log is called when exception occurs"""
        # Mock the API to raise an exception
        self.resources_api.get_applications.side_effect = Exception("API Error")

        # Patch the logger to verify error log is called
        with patch('src.application.application_resources.logger') as mock_logger:
            # Call the method
            result = asyncio.run(self.client._get_applications_internal())

            # Verify error log was called (line 85)
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            self.assertIn("Error in _get_applications_internal", str(error_call))
            self.assertIn("API Error", str(error_call))

            # Verify error is returned
            self.assertIn("error", result)

    def test_execute_resources_operation_dispatches_get_applications(self):
        """Test execute_resources_operation routes get_applications correctly"""
        expected = {"items": [{"id": "app-123"}]}
        with patch.object(self.client, 'get_applications', return_value=expected) as mock_get_apps:
            result = asyncio.run(self.client.execute_resources_operation(
                operation="get_applications",
                name_filter="Test Application"
            ))

            mock_get_apps.assert_called_once_with(
                name_filter="Test Application",
                application_boundary_scope=None,
                ctx=None
            )
            self.assertEqual(result, expected)

    def test_execute_resources_operation_dispatches_get_services(self):
        """Test execute_resources_operation routes get_services correctly"""
        expected = {"items": [{"id": "service-123"}]}
        with patch.object(self.client, 'get_services', return_value=expected) as mock_get_services:
            result = asyncio.run(self.client.execute_resources_operation(
                operation="get_services",
                name_filter="My Service",
                include_snapshot_ids=True
            ))

            mock_get_services.assert_called_once_with(
                name_filter="My Service",
                include_snapshot_ids=True,
                ctx=None
            )
            self.assertEqual(result, expected)

    def test_execute_resources_operation_dispatches_get_application_services(self):
        """Test execute_resources_operation routes get_application_services correctly"""
        expected = {"items": [{"id": "app-service-123"}]}
        with patch.object(self.client, 'get_application_services', return_value=expected) as mock_get_application_services:
            result = asyncio.run(self.client.execute_resources_operation(
                operation="get_application_services",
                application_id="app-1",
                service_id="service-1",
                name_filter="Test Service",
                application_boundary_scope="ALL",
                include_snapshot_ids=False
            ))

            mock_get_application_services.assert_called_once_with(
                application_id="app-1",
                service_id="service-1",
                name_filter="Test Service",
                application_boundary_scope="ALL",
                include_snapshot_ids=False,
                ctx=None
            )
            self.assertEqual(result, expected)

    def test_execute_resources_operation_dispatches_get_application_endpoints(self):
        """Test execute_resources_operation routes get_application_endpoints correctly"""
        expected = {"items": [{"id": "endpoint-123"}]}
        with patch.object(self.client, 'get_application_endpoints', return_value=expected) as mock_get_application_endpoints:
            result = asyncio.run(self.client.execute_resources_operation(
                operation="get_application_endpoints",
                application_id="app-1",
                service_id="service-1",
                endpoint_id="endpoint-1",
                name_filter="Test Endpoint",
                types=["HTTP"],
                technologies=["python"],
                application_boundary_scope="ALL"
            ))

            mock_get_application_endpoints.assert_called_once_with(
                application_id="app-1",
                service_id="service-1",
                endpoint_id="endpoint-1",
                name_filter="Test Endpoint",
                types=["HTTP"],
                technologies=["python"],
                application_boundary_scope="ALL",
                ctx=None
            )
            self.assertEqual(result, expected)

    def test_execute_resources_operation_returns_unsupported_operation_error(self):
        """Test execute_resources_operation returns an error for unsupported operations"""
        result = asyncio.run(self.client.execute_resources_operation(
            operation="invalid_operation"
        ))

        self.assertEqual(result, {"error": "Operation 'invalid_operation' not supported"})

    def test_get_application_endpoints_success_with_default_ids(self):
        """Test get_application_endpoints uses empty defaults and returns parsed JSON"""
        payload = {"items": [{"id": "endpoint-1", "name": "Sample"}]}
        response = MagicMock()
        response.data = json.dumps(payload).encode('utf-8')
        self.resources_api.get_application_endpoints_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_application_endpoints())

        self.resources_api.get_application_endpoints_without_preload_content.assert_called_once_with(
            application_id="",
            service_id="",
            endpoint_id="",
            name_filter=None,
            types=None,
            technologies=None,
            application_boundary_scope=None,
        )
        self.assertEqual(result, payload)

    def test_get_application_endpoints_error_handling(self):
        """Test get_application_endpoints error handling returns a meaningful error"""
        self.resources_api.get_application_endpoints_without_preload_content.side_effect = Exception("Endpoint failure")

        result = asyncio.run(self.client.get_application_endpoints())

        self.assertIn("error", result)
        self.assertIn("Failed to get application endpoints", result["error"])
        self.assertIn("Endpoint failure", result["error"])

    def test_get_application_services_sanitizes_technologies_none(self):
        """Test get_application_services sanitizes None technologies values to empty lists"""
        payload = {"items": [{"id": "service-1", "technologies": None}, {"id": "service-2"}]}
        response = MagicMock()
        response.data = json.dumps(payload).encode('utf-8')
        self.resources_api.get_application_services_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_application_services())

        self.resources_api.get_application_services_without_preload_content.assert_called_once_with(
            application_id=None,
            service_id="",
            name_filter=None,
            application_boundary_scope=None,
            include_snapshot_ids=None,
        )
        self.assertEqual(result["items"][0]["technologies"], [])
        self.assertEqual(result["items"][1].get("technologies"), [])

    def test_get_services_sanitizes_technologies_none(self):
        """Test get_services sanitizes None technologies values to empty lists"""
        payload = {"items": [{"id": "service-1", "technologies": None}]}
        response = MagicMock()
        response.data = json.dumps(payload).encode('utf-8')
        self.resources_api.get_services_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_services())

        self.resources_api.get_services_without_preload_content.assert_called_once_with(
            name_filter=None,
            include_snapshot_ids=None,
        )
        self.assertEqual(result["items"][0]["technologies"], [])

    def test_get_services_error_handling(self):
        """Test get_services returns a meaningful error message on exception"""
        self.resources_api.get_services_without_preload_content.side_effect = Exception("Services failure")

        result = asyncio.run(self.client.get_services())

        self.assertIn("error", result)
        self.assertIn("Failed to get services", result["error"])
        self.assertIn("Services failure", result["error"])

    def test_get_application_services_success_preserves_existing_technologies(self):
        """Test get_application_services preserves existing technologies lists"""
        payload = {"items": [{"id": "service-1", "technologies": ["python"]}, {"id": "service-2", "technologies": None}]}
        response = MagicMock()
        response.data = json.dumps(payload).encode('utf-8')
        self.resources_api.get_application_services_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_application_services(application_id="app-1", service_id="service-1"))

        self.assertEqual(result["items"][0]["technologies"], ["python"])
        self.assertEqual(result["items"][1]["technologies"], [])

    def test_get_application_services_error_handling(self):
        """Test get_application_services returns a meaningful error message on exception"""
        self.resources_api.get_application_services_without_preload_content.side_effect = Exception("Application services failure")

        result = asyncio.run(self.client.get_application_services())

        self.assertIn("error", result)
        self.assertIn("Failed to get application services", result["error"])
        self.assertIn("Application services failure", result["error"])

    def test_execute_resources_operation_handles_internal_exception(self):
        """Test execute_resources_operation catches internal method exceptions"""
        with patch.object(self.client, 'get_services', side_effect=Exception("Router failure")):
            result = asyncio.run(self.client.execute_resources_operation(
                operation="get_services"
            ))

            self.assertIn("error", result)
            self.assertIn("Error executing get_services", result["error"])

    def test_get_application_endpoints_success_with_explicit_ids(self):
        """Test get_application_endpoints with explicit id parameters"""
        payload = {"items": [{"id": "endpoint-2", "name": "Explicit"}]}
        response = MagicMock()
        response.data = json.dumps(payload).encode('utf-8')
        self.resources_api.get_application_endpoints_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_application_endpoints(
            application_id="app-1",
            service_id="service-1",
            endpoint_id="endpoint-2",
            name_filter="Explicit",
            types=["HTTP"],
            technologies=["python"],
            application_boundary_scope="ALL"
        ))

        self.resources_api.get_application_endpoints_without_preload_content.assert_called_once_with(
            application_id="app-1",
            service_id="service-1",
            endpoint_id="endpoint-2",
            name_filter="Explicit",
            types=["HTTP"],
            technologies=["python"],
            application_boundary_scope="ALL",
        )
        self.assertEqual(result, payload)

    def test_get_applications_success_without_to_dict(self):
        """Test get_applications returns plain dict responses unchanged"""
        payload = {"items": [{"id": "app-789", "label": "Plain App"}]}
        self.resources_api.get_applications.return_value = payload

        result = asyncio.run(self.client.get_applications(name_filter="Plain App"))

        self.assertEqual(result, payload)
        self.resources_api.get_applications.assert_called_once_with(
            name_filter="Plain App",
            application_boundary_scope=None
        )

    def test_get_applications_error_handling(self):
        """Test get_applications returns a meaningful error message on exception"""
        self.resources_api.get_applications.side_effect = Exception("Get applications failed")

        result = asyncio.run(self.client.get_applications())

        self.assertIn("error", result)
        self.assertIn("Failed to get applications", result["error"])
        self.assertIn("Get applications failed", result["error"])


if __name__ == '__main__':
    unittest.main()

