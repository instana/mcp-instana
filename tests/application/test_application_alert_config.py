"""
Unit tests for the ApplicationAlertMCPTools class
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
app_logger = logging.getLogger('src.application.application_alert_config')
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
            kwargs['api_client'] = self.alert_config_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.application_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.application_alert_config'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_alert_config_api = MagicMock()
mock_application_alert_config = MagicMock()

# Add __name__ attribute to mock classes
mock_alert_config_api.__name__ = "ApplicationAlertConfigurationApi"
mock_application_alert_config.__name__ = "ApplicationAlertConfig"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.application_alert_configuration_api'].ApplicationAlertConfigurationApi = mock_alert_config_api
sys.modules['instana_client.models.application_alert_config'].ApplicationAlertConfig = mock_application_alert_config

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.application.application_alert_config import ApplicationAlertMCPTools

class TestApplicationAlertMCPTools(unittest.TestCase):
    """Test the ApplicationAlertMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_alert_config_api.reset_mock()
        mock_application_alert_config.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.alert_config_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = ApplicationAlertMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.alert_config_api = self.alert_config_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_find_application_alert_config_success(self):
        """Test find_application_alert_config with successful response"""
        # Set up the mock response
        mock_result = {"id": "alert1", "name": "Test Alert"}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.find_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.find_application_alert_config(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.find_application_alert_config.assert_called_once_with(
            id="alert1",
            valid_on=None
        )

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_find_application_alert_config_missing_id(self):
        """Test find_application_alert_config with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.find_application_alert_config(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_find_application_alert_config_error(self):
        """Test find_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.find_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.find_application_alert_config(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get application alert config", result["error"])

    def test_find_application_alert_config_versions_success(self):
        """Test find_application_alert_config_versions with successful response"""
        # Set up the mock response
        mock_result = [{"id": "alert1", "version": 1}, {"id": "alert1", "version": 2}]
        mock_obj1 = MagicMock()
        mock_obj1.to_dict.return_value = mock_result[0]
        mock_obj2 = MagicMock()
        mock_obj2.to_dict.return_value = mock_result[1]
        self.alert_config_api.find_application_alert_config_versions.return_value = [mock_obj1, mock_obj2]

        # Call the method
        result = asyncio.run(self.client.find_application_alert_config_versions(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.find_application_alert_config_versions.assert_called_once_with(id="alert1")

        # Check that the result is correct
        self.assertEqual(result, {"versions": mock_result})

    def test_find_application_alert_config_versions_missing_id(self):
        """Test find_application_alert_config_versions with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.find_application_alert_config_versions(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_find_application_alert_config_versions_error(self):
        """Test find_application_alert_config_versions error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.find_application_alert_config_versions.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.find_application_alert_config_versions(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get application alert config versions", result["error"])

    def test_get_application_alert_configs_success(self):
        """Test get_application_alert_configs with successful response"""
        # Set up the mock response
        mock_result = [{"id": "alert1"}, {"id": "alert2"}]
        mock_obj1 = MagicMock()
        mock_obj1.to_dict.return_value = mock_result[0]
        mock_obj2 = MagicMock()
        mock_obj2.to_dict.return_value = mock_result[1]
        self.alert_config_api.find_active_application_alert_configs.return_value = [mock_obj1, mock_obj2]

        # Call the method
        result = asyncio.run(self.client.get_application_alert_configs())

        # Check that the mock was called with the correct arguments
        self.alert_config_api.find_active_application_alert_configs.assert_called_once_with(
            application_id=None,
            alert_ids=None
        )

        # Check that the result is correct
        self.assertEqual(result, {"configs": mock_result})

    def test_get_application_alert_configs_error(self):
        """Test get_application_alert_configs error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.find_active_application_alert_configs.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_application_alert_configs())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get application alert configs", result["error"])

    def test_delete_application_alert_config_success(self):
        """Test delete_application_alert_config with successful response"""
        # Set up the mock response (delete returns None)
        self.alert_config_api.delete_application_alert_config.return_value = None

        # Call the method
        result = asyncio.run(self.client.delete_application_alert_config(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.delete_application_alert_config.assert_called_once_with(id="alert1")

        # Check that the result is correct
        self.assertTrue(result["success"])
        self.assertIn("alert1", result["message"])

    def test_delete_application_alert_config_missing_id(self):
        """Test delete_application_alert_config with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.delete_application_alert_config(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_delete_application_alert_config_error(self):
        """Test delete_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.delete_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.delete_application_alert_config(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to delete application alert config", result["error"])

    def test_enable_application_alert_config_success(self):
        """Test enable_application_alert_config with successful response"""
        # Set up the mock response
        mock_result = {"id": "alert1", "enabled": True}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.enable_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.enable_application_alert_config(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.enable_application_alert_config.assert_called_once_with(id="alert1")

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_enable_application_alert_config_missing_id(self):
        """Test enable_application_alert_config with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.enable_application_alert_config(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_enable_application_alert_config_error(self):
        """Test enable_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.enable_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.enable_application_alert_config(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to enable application alert config", result["error"])

    def test_create_application_alert_config_success(self):
        """Test create_application_alert_config with successful response"""
        # Set up the payload and mock response
        payload = {"name": "Test Alert", "description": "Test description"}
        mock_result = {"id": "alert1", "name": "Test Alert"}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.create_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.create_application_alert_config(payload=payload))

        # Check that the mock was called
        self.alert_config_api.create_application_alert_config.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_create_application_alert_config_missing_payload(self):
        """Test create_application_alert_config with missing payload"""
        # Call the method without payload
        result = asyncio.run(self.client.create_application_alert_config(payload=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Payload is required")

    def test_create_application_alert_config_error(self):
        """Test create_application_alert_config error handling"""
        # Set up the payload and mock to raise an exception
        payload = {"name": "Test Alert"}
        self.alert_config_api.create_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.create_application_alert_config(payload=payload))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to create application alert config", result["error"])

    def test_update_application_alert_config_success(self):
        """Test update_application_alert_config with successful response"""
        # Set up the payload and mock response
        payload = {"name": "Updated Alert", "description": "Updated description"}
        mock_result = {"id": "alert1", "name": "Updated Alert"}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.update_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.update_application_alert_config(id="alert1", payload=payload))

        # Check that the mock was called
        self.alert_config_api.update_application_alert_config.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_update_application_alert_config_missing_id(self):
        """Test update_application_alert_config with missing ID"""
        # Call the method without ID
        payload = {"name": "Updated Alert"}
        result = asyncio.run(self.client.update_application_alert_config(id=None, payload=payload))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_update_application_alert_config_missing_payload(self):
        """Test update_application_alert_config with missing payload"""
        # Call the method without payload
        result = asyncio.run(self.client.update_application_alert_config(id="alert1", payload=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "payload is required")

    def test_update_application_alert_config_error(self):
        """Test update_application_alert_config error handling"""
        # Set up the payload and mock to raise an exception
        payload = {"name": "Updated Alert"}
        self.alert_config_api.update_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.update_application_alert_config(id="alert1", payload=payload))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to update application alert config", result["error"])


if __name__ == '__main__':
    unittest.main()
