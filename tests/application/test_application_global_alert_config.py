"""
Unit tests for the ApplicationGlobalAlertMCPTools class
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
app_logger = logging.getLogger('src.application.application_global_alert_config')
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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

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
sys.modules['instana_client.api.global_application_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.global_applications_alert_config'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_alert_config_api = MagicMock()
mock_global_applications_alert_config = MagicMock()

# Add __name__ attribute to mock classes
mock_alert_config_api.__name__ = "GlobalApplicationAlertConfigurationApi"
mock_global_applications_alert_config.__name__ = "GlobalApplicationsAlertConfig"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.global_application_alert_configuration_api'].GlobalApplicationAlertConfigurationApi = mock_alert_config_api
sys.modules['instana_client.models.global_applications_alert_config'].GlobalApplicationsAlertConfig = mock_global_applications_alert_config

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.application.application_global_alert_config import (
        ApplicationGlobalAlertMCPTools,
    )


def _make_streaming_response(body: bytes, status: int = 200):
    """Return a mock HTTPResponse whose .read(n) yields chunks like a real stream.

    ``stream_json_array_page`` reads the body via ``.read(n)`` rather than
    ``.data``, so tests must provide a mock that responds to .read() correctly.
    """
    buf = bytearray(body)
    pos = [0]

    def _read(n=-1):
        if pos[0] >= len(buf):
            return b""
        if n < 0:
            chunk = bytes(buf[pos[0]:])
            pos[0] = len(buf)
        else:
            chunk = bytes(buf[pos[0]:pos[0] + n])
            pos[0] += len(chunk)
        return chunk

    mock = MagicMock()
    mock.status = status
    mock.data = body
    mock.headers = {}
    mock.read = _read
    return mock


class TestApplicationGlobalAlertMCPTools(unittest.TestCase):
    """Test the ApplicationGlobalAlertMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_alert_config_api.reset_mock()
        mock_global_applications_alert_config.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.alert_config_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = ApplicationGlobalAlertMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.alert_config_api = self.alert_config_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_find_active_global_application_alert_configs_success(self):
        """Test find_active_global_application_alert_configs with successful response"""
        import json
        mock_data = [{"id": "alert1", "name": "Test Alert"}]
        mock_response = _make_streaming_response(json.dumps(mock_data).encode('utf-8'))
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content = MagicMock()
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.find_active_global_application_alert_configs(application_id="app1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content.assert_called_once_with(
            application_id="app1",
            alert_ids=None
        )

        # Check that the result is correct (method returns a dict with configs key)
        self.assertIsInstance(result, dict)
        self.assertIn("configs", result)
        self.assertEqual(result["configs"], mock_data)
        self.assertIn("count", result)
        self.assertIn("total", result)
        self.assertIn("showing", result)
        self.assertIn("message", result)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["total"], 1)

    def test_find_active_global_application_alert_configs_empty_result(self):
        """Test find_active_global_application_alert_configs with empty result"""
        import json
        mock_data = []
        mock_response = _make_streaming_response(json.dumps(mock_data).encode('utf-8'))
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content = MagicMock()
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.find_active_global_application_alert_configs(application_id="app1"))

        # Check that the result is correct
        self.assertIsInstance(result, dict)
        self.assertIn("configs", result)
        self.assertEqual(result["configs"], [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["total"], 0)
        self.assertIn("message", result)
        self.assertIn("No active global alert configurations found", result["message"])

    def test_find_active_global_application_alert_configs_limit_to_10(self):
        """Test find_active_global_application_alert_configs limits results to 10"""
        import json
        mock_data = [{"id": f"alert{i}", "name": f"Test Alert {i}"} for i in range(15)]
        mock_response = _make_streaming_response(json.dumps(mock_data).encode('utf-8'))
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content = MagicMock()
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.find_active_global_application_alert_configs(application_id="app1"))

        # Check that only 10 results are returned
        self.assertIsInstance(result, dict)
        self.assertIn("configs", result)
        self.assertEqual(len(result["configs"]), 10)
        self.assertEqual(result["count"], 10)
        self.assertEqual(result["total"], 15)
        self.assertEqual(result["showing"], 10)
        self.assertIn("Showing first 10", result["message"])

    def test_find_active_global_application_alert_configs_missing_app_id(self):
        """Test find_active_global_application_alert_configs with missing application ID"""
        # Call the method without application ID
        result = asyncio.run(self.client.find_active_global_application_alert_configs(application_id=None))

        # Check that the result contains an error message (method returns a dict)
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "application_id is required")

    def test_find_active_global_application_alert_configs_error(self):
        """Test find_active_global_application_alert_configs error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content = MagicMock()
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.find_active_global_application_alert_configs(application_id="app1"))

        # Check that the result contains an error message (method returns a dict)
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to get active global application alert config", result["error"])

    def test_find_global_application_alert_config_versions_success(self):
        """Test find_global_application_alert_config_versions with successful response"""
        # Set up the mock response
        mock_result = [{"id": "alert1", "version": 1}, {"id": "alert1", "version": 2}]
        mock_obj1 = MagicMock()
        mock_obj1.to_dict.return_value = mock_result[0]
        mock_obj2 = MagicMock()
        mock_obj2.to_dict.return_value = mock_result[1]
        self.alert_config_api.find_global_application_alert_config_versions.return_value = [mock_obj1, mock_obj2]

        # Call the method
        result = asyncio.run(self.client.find_global_application_alert_config_versions(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.find_global_application_alert_config_versions.assert_called_once_with(id="alert1")

        # Check that the result is correct
        self.assertEqual(result, {"versions": mock_result})

    def test_find_global_application_alert_config_versions_missing_id(self):
        """Test find_global_application_alert_config_versions with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.find_global_application_alert_config_versions(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_find_global_application_alert_config_versions_error(self):
        """Test find_global_application_alert_config_versions error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.find_global_application_alert_config_versions.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.find_global_application_alert_config_versions(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get global application alert config versions", result["error"])

    def test_find_global_application_alert_config_success(self):
        """Test find_global_application_alert_config with successful response"""
        # Set up the mock response
        mock_result = {"id": "alert1", "name": "Test Alert"}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.find_global_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.find_global_application_alert_config(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.find_global_application_alert_config.assert_called_once_with(
            id="alert1",
            valid_on=None
        )

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_find_global_application_alert_config_error(self):
        """Test find_global_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.find_global_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.find_global_application_alert_config(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get global application alert configs", result["error"])

    def test_delete_global_application_alert_config_success(self):
        """Test delete_global_application_alert_config with successful response"""
        # Set up the mock response (delete returns None)
        self.alert_config_api.delete_global_application_alert_config.return_value = None

        # Call the method
        result = asyncio.run(self.client.delete_global_application_alert_config(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.delete_global_application_alert_config.assert_called_once_with(id="alert1")

        # Check that the result is correct
        self.assertTrue(result["success"])
        self.assertIn("alert1", result["message"])

    def test_delete_global_application_alert_config_missing_id(self):
        """Test delete_global_application_alert_config with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.delete_global_application_alert_config(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_delete_global_application_alert_config_error(self):
        """Test delete_global_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.delete_global_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.delete_global_application_alert_config(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to delete global application alert config", result["error"])

    def test_enable_global_application_alert_config_success(self):
        """Test enable_global_application_alert_config with successful response"""
        # Set up the mock response
        mock_result = {"id": "alert1", "enabled": True}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.enable_global_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.enable_global_application_alert_config(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.enable_global_application_alert_config.assert_called_once_with(id="alert1")

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_enable_global_application_alert_config_missing_id(self):
        """Test enable_global_application_alert_config with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.enable_global_application_alert_config(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_enable_global_application_alert_config_error(self):
        """Test enable_global_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.enable_global_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.enable_global_application_alert_config(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to enable global application alert config", result["error"])

    def test_disable_global_application_alert_config_success(self):
        """Test disable_global_application_alert_config with successful response"""
        # Set up the mock response
        mock_result = {"id": "alert1", "enabled": False}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.disable_global_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.disable_global_application_alert_config(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.disable_global_application_alert_config.assert_called_once_with(id="alert1")

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_disable_global_application_alert_config_missing_id(self):
        """Test disable_global_application_alert_config with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.disable_global_application_alert_config(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_disable_global_application_alert_config_error(self):
        """Test disable_global_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.disable_global_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.disable_global_application_alert_config(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to disable global application alert config", result["error"])

    def test_restore_global_application_alert_config_success(self):
        """Test restore_global_application_alert_config with successful response"""
        # Set up the mock response
        mock_result = {"id": "alert1", "restored": True}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.restore_global_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.restore_global_application_alert_config(id="alert1", created=123456789))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.restore_global_application_alert_config.assert_called_once_with(
            id="alert1",
            created=123456789
        )

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_restore_global_application_alert_config_missing_id(self):
        """Test restore_global_application_alert_config with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.restore_global_application_alert_config(id=None, created=123456789))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_restore_global_application_alert_config_missing_created(self):
        """Test restore_global_application_alert_config with missing created timestamp"""
        # Call the method without created timestamp
        result = asyncio.run(self.client.restore_global_application_alert_config(id="alert1", created=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "created timestamp is required")

    def test_restore_global_application_alert_config_error(self):
        """Test restore_global_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.restore_global_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.restore_global_application_alert_config(id="alert1", created=123456789))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to restore global application alert config", result["error"])

    def test_create_global_application_alert_config_success(self):
        """Test create_global_application_alert_config with successful response"""
        # Set up the payload and mock response
        payload = {"name": "Test Alert", "description": "Test description"}
        mock_result = {"id": "alert1", "name": "Test Alert"}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.create_global_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.create_global_application_alert_config(payload=payload))

        # Check that the mock was called
        self.alert_config_api.create_global_application_alert_config.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_create_global_application_alert_config_missing_payload(self):
        """Test create_global_application_alert_config with missing payload"""
        # Call the method without payload
        result = asyncio.run(self.client.create_global_application_alert_config(payload=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Payload is required")

    def test_create_global_application_alert_config_error(self):
        """Test create_global_application_alert_config error handling"""
        # Set up the payload and mock to raise an exception
        payload = {"name": "Test Alert"}
        self.alert_config_api.create_global_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.create_global_application_alert_config(payload=payload))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to create global application alert config", result["error"])

    def test_update_global_application_alert_config_success(self):
        """Test update_global_application_alert_config with successful response"""
        # Set up the payload and mock response
        payload = {"name": "Updated Alert", "description": "Updated description"}
        mock_result = {"id": "alert1", "name": "Updated Alert"}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.update_global_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.update_global_application_alert_config(id="alert1", payload=payload))

        # Check that the mock was called
        self.alert_config_api.update_global_application_alert_config.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_update_global_application_alert_config_missing_id(self):
        """Test update_global_application_alert_config with missing ID"""
        # Call the method without ID
        payload = {"name": "Updated Alert"}
        result = asyncio.run(self.client.update_global_application_alert_config(id=None, payload=payload))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_update_global_application_alert_config_missing_payload(self):
        """Test update_global_application_alert_config with missing payload"""
        # Call the method without payload
        result = asyncio.run(self.client.update_global_application_alert_config(id="alert1", payload=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "payload is required")

    def test_update_global_application_alert_config_error(self):
        """Test update_global_application_alert_config error handling"""
        # Set up the payload and mock to raise an exception
        payload = {"name": "Updated Alert"}
        self.alert_config_api.update_global_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.update_global_application_alert_config(id="alert1", payload=payload))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to update global application alert config", result["error"])


    # Tests for execute_alert_config_operation dispatcher
    def test_execute_alert_config_operation_find_active(self):
        """Test execute_alert_config_operation with find_active operation"""
        import json
        mock_data = [{"id": "alert1", "name": "Test Alert"}]
        mock_response = _make_streaming_response(json.dumps(mock_data).encode('utf-8'))
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content = MagicMock()
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content.return_value = mock_response

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="find_active",
            application_id="app1"
        ))

        # Check result
        self.assertIn("configs", result)

    def test_execute_alert_config_operation_find_versions(self):
        """Test execute_alert_config_operation with find_versions operation"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1", "version": 1}
        self.alert_config_api.find_global_application_alert_config_versions.return_value = [mock_obj]

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="find_versions",
            id="alert1"
        ))

        # Check result
        self.assertIn("versions", result)

    def test_execute_alert_config_operation_find(self):
        """Test execute_alert_config_operation with find operation"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1"}
        self.alert_config_api.find_global_application_alert_config.return_value = mock_obj

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="find",
            id="alert1"
        ))

        # Check result
        self.assertIsInstance(result, dict)

    def test_execute_alert_config_operation_create(self):
        """Test execute_alert_config_operation with create operation"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1"}
        self.alert_config_api.create_global_application_alert_config.return_value = mock_obj

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="create",
            payload={"name": "Test"}
        ))

        # Check result
        self.assertIsInstance(result, dict)

    def test_execute_alert_config_operation_update(self):
        """Test execute_alert_config_operation with update operation"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1"}
        self.alert_config_api.update_global_application_alert_config.return_value = mock_obj

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="update",
            id="alert1",
            payload={"name": "Updated"}
        ))

        # Check result
        self.assertIsInstance(result, dict)

    def test_execute_alert_config_operation_delete(self):
        """Test execute_alert_config_operation with delete operation"""
        # Set up mock response
        self.alert_config_api.delete_global_application_alert_config.return_value = None

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="delete",
            id="alert1"
        ))

        # Check result
        self.assertIn("success", result)

    def test_execute_alert_config_operation_enable(self):
        """Test execute_alert_config_operation with enable operation"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1", "enabled": True}
        self.alert_config_api.enable_global_application_alert_config.return_value = mock_obj

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="enable",
            id="alert1"
        ))

        # Check result
        self.assertIsInstance(result, dict)

    def test_execute_alert_config_operation_disable(self):
        """Test execute_alert_config_operation with disable operation"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1", "enabled": False}
        self.alert_config_api.disable_global_application_alert_config.return_value = mock_obj

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="disable",
            id="alert1"
        ))

        # Check result
        self.assertIsInstance(result, dict)

    def test_execute_alert_config_operation_restore(self):
        """Test execute_alert_config_operation with restore operation"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1", "restored": True}
        self.alert_config_api.restore_global_application_alert_config.return_value = mock_obj

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="restore",
            id="alert1",
            created=123456789
        ))

        # Check result
        self.assertIsInstance(result, dict)

    def test_execute_alert_config_operation_unsupported(self):
        """Test execute_alert_config_operation with unsupported operation"""
        # Call the dispatcher with unsupported operation
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="unsupported_op"
        ))

        # Check result contains error
        self.assertIn("error", result)
        self.assertIn("not supported", result["error"])

    def test_execute_alert_config_operation_exception(self):
        """Test execute_alert_config_operation exception handling"""
        # Set up mock to raise exception
        self.alert_config_api.find_global_application_alert_config.side_effect = Exception("Test error")

        # Call the dispatcher
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="find",
            id="alert1"
        ))

        # Check result contains error (the actual error message from the method)
        self.assertIn("error", result)
        self.assertIn("Failed to get global application alert configs", result["error"])

    # Tests for helper method validation errors
    def test_find_active_configs_missing_application_id(self):
        """Test _find_active_configs with missing application_id"""
        result = asyncio.run(self.client._find_active_configs(
            application_id=None,
            alert_ids=None
        ))

        self.assertIn("error", result)
        self.assertIn("application_id is required", result["error"])

    def test_find_config_versions_missing_id(self):
        """Test _find_config_versions with missing id"""
        result = asyncio.run(self.client._find_config_versions(id=None))

        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_create_config_missing_payload(self):
        """Test _create_config with missing payload"""
        result = asyncio.run(self.client._create_config(payload=None))

        self.assertIn("error", result)
        self.assertIn("payload is required", result["error"])

    def test_update_config_missing_id(self):
        """Test _update_config with missing id"""
        result = asyncio.run(self.client._update_config(
            id=None,
            payload={"name": "Test"}
        ))

        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_update_config_missing_payload(self):
        """Test _update_config with missing payload"""
        result = asyncio.run(self.client._update_config(
            id="alert1",
            payload=None
        ))

        self.assertIn("error", result)
        self.assertIn("payload is required", result["error"])

    def test_delete_config_missing_id(self):
        """Test _delete_config with missing id"""
        result = asyncio.run(self.client._delete_config(id=None))

        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_enable_config_missing_id(self):
        """Test _enable_config with missing id"""
        result = asyncio.run(self.client._enable_config(id=None))

        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_disable_config_missing_id(self):
        """Test _disable_config with missing id"""
        result = asyncio.run(self.client._disable_config(id=None))

        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_restore_config_missing_id(self):
        """Test _restore_config with missing id"""
        result = asyncio.run(self.client._restore_config(
            id=None,
            created=123456789
        ))

        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_restore_config_missing_created(self):
        """Test _restore_config with missing created"""
        result = asyncio.run(self.client._restore_config(
            id="alert1",
            created=None
        ))

        self.assertIn("error", result)
        self.assertIn("created timestamp is required", result["error"])

    # Tests for JSON decode errors / non-array bodies
    def test_find_active_configs_json_decode_error(self):
        """Test find_active_global_application_alert_configs with malformed (non-array) body.

        stream_json_array_page cannot locate an opening '[' in the body, so it
        returns ([], 0).  The method treats this the same as an empty result.
        """
        mock_response = _make_streaming_response(b"invalid json {")
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content = MagicMock()
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.find_active_global_application_alert_configs(application_id="app1"))

        # Non-array body → treated as empty result
        self.assertIn("configs", result)
        self.assertEqual(result["configs"], [])
        self.assertEqual(result["total"], 0)
        self.assertIn("No active global alert configurations found", result["message"])

    # Tests for response handling edge cases
    def test_find_active_configs_single_dict_result(self):
        """Test find_active_global_application_alert_configs with single dict (non-array) response.

        stream_json_array_page requires a JSON array.  A bare object response
        (no '[') is treated as an empty result rather than wrapped in a list.
        """
        import json
        mock_data = {"id": "alert1", "name": "Test Alert"}
        mock_response = _make_streaming_response(json.dumps(mock_data).encode('utf-8'))
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content = MagicMock()
        self.alert_config_api.find_active_global_application_alert_configs_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.find_active_global_application_alert_configs(application_id="app1"))

        # Non-array body → empty result (stream_json_array_page requires '[')
        self.assertIn("configs", result)
        self.assertEqual(result["configs"], [])
        self.assertEqual(result["total"], 0)

    def test_find_config_versions_dict_result(self):
        """Test find_global_application_alert_config_versions with dict result"""
        # Set up mock response as dict (not list)
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1", "version": 1}
        self.alert_config_api.find_global_application_alert_config_versions.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.find_global_application_alert_config_versions(id="alert1"))

        # Check result
        self.assertIsInstance(result, dict)

    def test_find_config_versions_plain_dict_result(self):
        """Test find_global_application_alert_config_versions with plain dict result"""
        # Set up mock response as plain dict
        self.alert_config_api.find_global_application_alert_config_versions.return_value = {"data": "test"}

        # Call the method
        result = asyncio.run(self.client.find_global_application_alert_config_versions(id="alert1"))

        # Check result - plain dict is returned as-is when it's already a dict
        self.assertEqual(result, {"data": "test"})

    def test_find_config_list_result(self):
        """Test find_global_application_alert_config with list result"""
        # Set up mock response as list
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1"}
        self.alert_config_api.find_global_application_alert_config.return_value = [mock_obj]

        # Call the method
        result = asyncio.run(self.client.find_global_application_alert_config(id="alert1"))

        # Check result wraps list
        self.assertIn("configs", result)

    def test_find_config_plain_dict_result(self):
        """Test find_global_application_alert_config with plain dict result"""
        # Set up mock response as plain dict
        self.alert_config_api.find_global_application_alert_config.return_value = {"data": "test"}

        # Call the method
        result = asyncio.run(self.client.find_global_application_alert_config(id="alert1"))

        # Check result - plain dict is returned as-is when it's already a dict
        self.assertEqual(result, {"data": "test"})

    def test_enable_config_no_result(self):
        """Test enable_global_application_alert_config with no result"""
        # Set up mock to return None
        self.alert_config_api.enable_global_application_alert_config.return_value = None

        # Call the method
        result = asyncio.run(self.client.enable_global_application_alert_config(id="alert1"))

        # Check default success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])

    def test_disable_config_no_result(self):
        """Test disable_global_application_alert_config with no result"""
        # Set up mock to return None
        self.alert_config_api.disable_global_application_alert_config.return_value = None

        # Call the method
        result = asyncio.run(self.client.disable_global_application_alert_config(id="alert1"))

        # Check default success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])

    def test_restore_config_no_result(self):
        """Test restore_global_application_alert_config with no result"""
        # Set up mock to return None
        self.alert_config_api.restore_global_application_alert_config.return_value = None

        # Call the method
        result = asyncio.run(self.client.restore_global_application_alert_config(id="alert1", created=123456789))

        # Check default success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])

    # Tests for string payload parsing in create
    def test_create_config_string_payload_json(self):
        """Test create_global_application_alert_config with JSON string payload"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1"}
        self.alert_config_api.create_global_application_alert_config.return_value = mock_obj

        # Call with JSON string
        import json
        payload_str = json.dumps({"name": "Test Alert"})
        result = asyncio.run(self.client.create_global_application_alert_config(payload=payload_str))

        # Check result
        self.assertIsInstance(result, dict)

    def test_create_config_string_payload_single_quotes(self):
        """Test create_global_application_alert_config with single-quoted string payload"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1"}
        self.alert_config_api.create_global_application_alert_config.return_value = mock_obj

        # Call with single-quoted string
        payload_str = "{'name': 'Test Alert'}"
        result = asyncio.run(self.client.create_global_application_alert_config(payload=payload_str))

        # Check result
        self.assertIsInstance(result, dict)

    def test_create_config_string_payload_invalid(self):
        """Test create_global_application_alert_config with invalid string payload"""
        # Call with invalid string
        payload_str = "invalid {{{ payload"
        result = asyncio.run(self.client.create_global_application_alert_config(payload=payload_str))

        # Check error
        self.assertIn("error", result)
        self.assertIn("Invalid payload format", result["error"])

    def test_create_config_plain_dict_result(self):
        """Test create_global_application_alert_config with plain dict result"""
        # Set up mock to return plain dict
        self.alert_config_api.create_global_application_alert_config.return_value = {"id": "alert1"}

        # Call the method
        result = asyncio.run(self.client.create_global_application_alert_config(payload={"name": "Test"}))

        # Check result
        self.assertEqual(result, {"id": "alert1"})

    # Tests for string payload parsing in update
    def test_update_config_string_payload_json(self):
        """Test update_global_application_alert_config with JSON string payload"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1"}
        self.alert_config_api.update_global_application_alert_config.return_value = mock_obj

        # Call with JSON string
        import json
        payload_str = json.dumps({"name": "Updated Alert"})
        result = asyncio.run(self.client.update_global_application_alert_config(id="alert1", payload=payload_str))

        # Check result
        self.assertIsInstance(result, dict)

    def test_update_config_string_payload_single_quotes(self):
        """Test update_global_application_alert_config with single-quoted string payload"""
        # Set up mock response
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"id": "alert1"}
        self.alert_config_api.update_global_application_alert_config.return_value = mock_obj

        # Call with single-quoted string
        payload_str = "{'name': 'Updated Alert'}"
        result = asyncio.run(self.client.update_global_application_alert_config(id="alert1", payload=payload_str))

        # Check result
        self.assertIsInstance(result, dict)

    def test_update_config_string_payload_invalid(self):
        """Test update_global_application_alert_config with invalid string payload"""
        # Call with invalid string
        payload_str = "invalid {{{ payload"
        result = asyncio.run(self.client.update_global_application_alert_config(id="alert1", payload=payload_str))

        # Check error
        self.assertIn("error", result)
        self.assertIn("Invalid payload format", result["error"])

    def test_update_config_no_result(self):
        """Test update_global_application_alert_config with no result"""
        # Set up mock to return None
        self.alert_config_api.update_global_application_alert_config.return_value = None

        # Call the method
        result = asyncio.run(self.client.update_global_application_alert_config(id="alert1", payload={"name": "Test"}))

        # Check default success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])


    # ------------------------------------------------------------------
    # Tests for execute_global_alert_config_operation — "find" requires id
    # ------------------------------------------------------------------

    def test_execute_global_alert_config_find_missing_id_returns_elicitation(self):
        """'find' without id must return elicitation_needed (SDK requires id)."""
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="find",
            application_id=None,
            id=None,
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("id" in e for e in result["api_error"]))

    def test_execute_global_alert_config_find_with_id_proceeds(self):
        """'find' with a valid id skips the elicitation gate."""
        mock_result = {"id": "alert-1", "name": "Test"}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.find_global_application_alert_config.return_value = mock_obj

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="find",
            id="alert-1",
        ))
        self.assertFalse(result.get("elicitation_needed", False))


if __name__ == '__main__':
    unittest.main()
