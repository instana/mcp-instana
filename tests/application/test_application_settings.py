"""
Unit tests for the ApplicationSettingsMCPTools class
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
app_logger = logging.getLogger('src.application.application_settings')
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
            kwargs['api_client'] = self.settings_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.application_settings_api'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.application_config'] = MagicMock()
sys.modules['instana_client.models.endpoint_config'] = MagicMock()
sys.modules['instana_client.models.manual_service_config'] = MagicMock()
sys.modules['instana_client.models.new_application_config'] = MagicMock()
sys.modules['instana_client.models.new_manual_service_config'] = MagicMock()
sys.modules['instana_client.models.service_config'] = MagicMock()
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
mock_settings_api = MagicMock()
mock_application_config = MagicMock()
mock_endpoint_config = MagicMock()
mock_manual_service_config = MagicMock()
mock_new_application_config = MagicMock()
mock_new_manual_service_config = MagicMock()
mock_service_config = MagicMock()

# Add __name__ attribute to mock classes
mock_settings_api.__name__ = "ApplicationSettingsApi"
mock_application_config.__name__ = "ApplicationConfig"
mock_endpoint_config.__name__ = "EndpointConfig"
mock_manual_service_config.__name__ = "ManualServiceConfig"
mock_new_application_config.__name__ = "NewApplicationConfig"
mock_new_manual_service_config.__name__ = "NewManualServiceConfig"
mock_service_config.__name__ = "ServiceConfig"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.application_settings_api'].ApplicationSettingsApi = mock_settings_api
sys.modules['instana_client.models.application_config'].ApplicationConfig = mock_application_config
sys.modules['instana_client.models.endpoint_config'].EndpointConfig = mock_endpoint_config
sys.modules['instana_client.models.manual_service_config'].ManualServiceConfig = mock_manual_service_config
sys.modules['instana_client.models.new_application_config'].NewApplicationConfig = mock_new_application_config
sys.modules['instana_client.models.new_manual_service_config'].NewManualServiceConfig = mock_new_manual_service_config
sys.modules['instana_client.models.service_config'].ServiceConfig = mock_service_config

# Import the class to test
from src.application.application_settings import ApplicationSettingsMCPTools


class TestApplicationSettingsMCPTools(unittest.TestCase):
    """Test the ApplicationSettingsMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_settings_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.settings_api = mock_settings_api

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"

        # Patch the with_header_auth decorator
        self.patcher = patch('src.core.utils.with_header_auth', mock_with_header_auth)
        self.patcher.start()

        self.client = ApplicationSettingsMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.settings_api = mock_settings_api

        # Patch the logger to prevent logging during tests
        patcher = patch('src.application.application_settings.debug_print')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        """Tear down test fixtures"""
        # Stop the with_header_auth patcher
        self.patcher.stop()
        # No need to stop patchers since we're directly mocking the module imports
        pass

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        # Since we're mocking at the module level, we can't easily test the initialization
        # Just verify that the client was created with the correct values
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_all_applications_configs(self):
        """Test get_all_applications_configs with default parameters"""
        # Set up the mock response
        mock_result = [MagicMock()]
        mock_result[0].to_dict = MagicMock(return_value={"id": "app123", "label": "Test App"})
        self.settings_api.get_application_configs = MagicMock(return_value=mock_result)

        # Call the method
        result = asyncio.run(self.client.get_all_applications_configs())

        # Check that the API was called
        self.settings_api.get_application_configs.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, [{"id": "app123", "label": "Test App"}])

    def test_get_all_applications_configs_error_handling(self):
        """Test get_all_applications_configs error handling"""
        # Set up the mock to raise an exception
        self.settings_api.get_application_configs = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_all_applications_configs())

        # Check that the result contains an error message
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertIn("Failed to get all applications", result[0]["error"])

    def test_add_application_config(self):
        """Test add_application_config with required parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"id": "app123", "label": "Test App"})
        self.settings_api.add_application_config = MagicMock(return_value=mock_result)

        # Set up test parameters
        access_rules = [{"key": "value"}]
        boundary_scope = "INBOUND"
        label = "Test App"
        scope = "test-scope"

        # Call the method
        result = asyncio.run(self.client.add_application_config(
            access_rules=access_rules,
            boundary_scope=boundary_scope,
            label=label,
            scope=scope
        ))

        # Check that the API was called
        self.settings_api.add_application_config.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"id": "app123", "label": "Test App"})

    def test_add_application_config_missing_params(self):
        """Test add_application_config with missing parameters"""
        # Call the method with missing parameters
        result = asyncio.run(self.client.add_application_config(
            access_rules=None,
            boundary_scope=None,
            label=None,
            scope=None
        ))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Required enitities are missing or invalid", result["error"])

    def test_delete_application_config(self):
        """Test delete_application_config with valid ID"""
        # Set up the mock
        self.settings_api.delete_application_config = MagicMock()

        # Call the method
        result = asyncio.run(self.client.delete_application_config(id="app123"))

        # Check that the API was called with the correct ID
        self.settings_api.delete_application_config.assert_called_once_with(id="app123")

        # Check that the result indicates success
        self.assertTrue(result["success"])
        self.assertIn("app123", result["message"])

    def test_delete_application_config_missing_id(self):
        """Test delete_application_config with missing ID"""
        # Call the method with missing ID
        result = asyncio.run(self.client.delete_application_config(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Application perspective ID is required", result["error"])

    def test_get_application_config(self):
        """Test get_application_config with valid ID"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"id": "app123", "label": "Test App"})
        self.settings_api.get_application_config = MagicMock(return_value=mock_result)

        # Call the method
        result = asyncio.run(self.client.get_application_config(id="app123"))

        # Check that the API was called with the correct ID
        self.settings_api.get_application_config.assert_called_once_with(id="app123")

        # Check that the result is correct
        self.assertEqual(result, {"id": "app123", "label": "Test App"})

    def test_get_all_endpoint_configs(self):
        """Test get_all_endpoint_configs"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"endpoints": [{"id": "ep123"}]})
        self.settings_api.get_endpoint_configs = MagicMock(return_value=mock_result)

        # Call the method
        result = asyncio.run(self.client.get_all_endpoint_configs())

        # Check that the API was called
        self.settings_api.get_endpoint_configs.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"endpoints": [{"id": "ep123"}]})

    def test_create_endpoint_config(self):
        """Test create_endpoint_config with required parameters"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"serviceId": "svc123"})
        self.settings_api.create_endpoint_config = MagicMock(return_value=mock_result)

        # Call the method
        result = asyncio.run(self.client.create_endpoint_config(
            endpoint_case="ORIGINAL",
            service_id="svc123"
        ))

        # Check that the API was called
        self.settings_api.create_endpoint_config.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"serviceId": "svc123"})

    def test_get_all_manual_service_configs(self):
        """Test get_all_manual_service_configs"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"configs": [{"id": "ms123"}]})
        self.settings_api.get_all_manual_service_configs = MagicMock(return_value=mock_result)

        # Call the method
        result = asyncio.run(self.client.get_all_manual_service_configs())

        # Check that the API was called
        self.settings_api.get_all_manual_service_configs.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"configs": [{"id": "ms123"}]})

    def test_get_all_service_configs(self):
        """Test get_all_service_configs"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"services": [{"id": "svc123"}]})
        self.settings_api.get_service_configs = MagicMock(return_value=mock_result)

        # Call the method
        result = asyncio.run(self.client.get_all_service_configs())

        # Check that the API was called
        self.settings_api.get_service_configs.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, {"services": [{"id": "svc123"}]})

    def test_order_service_config(self):
        """Test order_service_config"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={"success": True})
        self.settings_api.order_service_config = MagicMock(return_value=mock_result)

        # Call the method
        result = asyncio.run(self.client.order_service_config(
            request_body=["svc1", "svc2", "svc3"]
        ))

        # Check that the API was called with the correct parameters
        self.settings_api.order_service_config.assert_called_once_with(
            request_body=["svc1", "svc2", "svc3"]
        )

        # Check that the result is correct
        self.assertEqual(result, {"success": True})

    def test_order_service_config_empty_list(self):
        """Test order_service_config with empty list"""
        # Call the method with an empty list
        result = asyncio.run(self.client.order_service_config(request_body=[]))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("cannot be empty", result["error"])

if __name__ == '__main__':
    unittest.main()


