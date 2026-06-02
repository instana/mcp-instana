"""
Unit tests for the ApplicationAlertMCPTools class
"""

import asyncio
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import ANY, AsyncMock, MagicMock, patch


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

    def test_find_active_application_alert_configs_success(self):
        """Test find_active_application_alert_configs with successful response"""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.data = b'[{"id": "alert1", "name": "Test Alert"}]'
        self.alert_config_api.find_all_active_application_alert_configs_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.find_active_application_alert_configs(application_id="app1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.find_all_active_application_alert_configs_without_preload_content.assert_called_once_with(
            application_id="app1",
            alert_ids=None
        )

        # Check that the result is correct
        self.assertIn("configs", result)
        self.assertEqual(len(result["configs"]), 1)

    def test_find_active_application_alert_configs_missing_application_id(self):
        """Test find_active_application_alert_configs with missing application_id"""
        # Call the method without application_id
        result = asyncio.run(self.client.find_active_application_alert_configs(application_id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "application_id is required")

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

    def test_disable_application_alert_config_success(self):
        """Test disable_application_alert_config with successful response"""
        # Set up the mock response
        mock_result = {"id": "alert1", "enabled": False}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.disable_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.disable_application_alert_config(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.disable_application_alert_config.assert_called_once_with(id="alert1")

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_disable_application_alert_config_missing_id(self):
        """Test disable_application_alert_config with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.disable_application_alert_config(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_disable_application_alert_config_error(self):
        """Test disable_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.disable_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.disable_application_alert_config(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to disable application alert config", result["error"])

    def test_restore_application_alert_config_success(self):
        """Test restore_application_alert_config with successful response"""
        # Set up the mock response
        mock_result = {"id": "alert1", "restored": True}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.restore_application_alert_config.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.restore_application_alert_config(id="alert1", created=1234567890))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.restore_application_alert_config.assert_called_once_with(id="alert1", created=1234567890)

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_restore_application_alert_config_missing_id(self):
        """Test restore_application_alert_config with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.restore_application_alert_config(id=None, created=1234567890))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_restore_application_alert_config_missing_created(self):
        """Test restore_application_alert_config with missing created timestamp"""
        # Call the method without created timestamp
        result = asyncio.run(self.client.restore_application_alert_config(id="alert1", created=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "created timestamp is required")

    def test_restore_application_alert_config_error(self):
        """Test restore_application_alert_config error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.restore_application_alert_config.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.restore_application_alert_config(id="alert1", created=1234567890))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to restore application alert config", result["error"])

    def test_update_application_alert_config_baseline_success(self):
        """Test update_application_alert_config_baseline with successful response"""
        # Set up the mock response
        mock_result = {"id": "alert1", "baseline_updated": True}
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_result
        self.alert_config_api.update_application_historic_baseline.return_value = mock_obj

        # Call the method
        result = asyncio.run(self.client.update_application_alert_config_baseline(id="alert1"))

        # Check that the mock was called with the correct arguments
        self.alert_config_api.update_application_historic_baseline.assert_called_once_with(id="alert1")

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_update_application_alert_config_baseline_missing_id(self):
        """Test update_application_alert_config_baseline with missing ID"""
        # Call the method without ID
        result = asyncio.run(self.client.update_application_alert_config_baseline(id=None))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "id is required")

    def test_update_application_alert_config_baseline_error(self):
        """Test update_application_alert_config_baseline error handling"""
        # Set up the mock to raise an exception
        self.alert_config_api.update_application_historic_baseline.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.update_application_alert_config_baseline(id="alert1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to update application alert config baseline", result["error"])

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

    def test_execute_operation_find_active(self):
        """Test execute_operation with find_active operation"""

        self.client._find_active_configs = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="find_active",
            application_id="app1",
            alert_ids=["alert1", "alert2"]
        ))

        self.client._find_active_configs.assert_called_once_with("app1", ["alert1", "alert2"], None)
        self.assertEqual(result, {"success": True})

    def test_execute_operation_invalid_operation(self):
        """Test execute_operation with invalid operation"""
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="invalid_op"
        ))

        self.assertIn("error", result)
        self.assertEqual(result["error"], "Operation 'invalid_op' not supported")

    def test_execute_operation_find_versions(self):
        """Test execute_operation with find_versions operation"""

        self.client._find_config_versions = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="find_versions",
            id="alert1"
        ))

        self.client._find_config_versions.assert_called_once_with("alert1", None)
        self.assertEqual(result, {"success": True})

    def test_execute_operation_find(self):
        """Test execute_operation with find operation"""

        self.client._find_config = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="find",
            id="alert1",
            valid_on=1234567890
        ))

        self.client._find_config.assert_called_once_with("alert1", 1234567890, None)
        self.assertEqual(result, {"success": True})

    def test_execute_operation_create(self):
        """Test execute_operation with create operation"""

        self.client._create_config = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="create",
            payload={"name": "test"}
        ))

        self.client._create_config.assert_called_once_with({"name": "test"}, None)
        self.assertEqual(result, {"success": True})

    def test_execute_operation_update(self):
        """Test execute_operation with update operation"""

        self.client._update_config = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="update",
            id="alert1",
            payload={"name": "Updated Alert"}
        ))

        self.client._update_config.assert_called_once_with("alert1", {"name": "Updated Alert"}, None)
        self.assertEqual(result, {"success": True})

    def test_execute_operation_delete(self):
        """Test execute_operation with delete operation"""

        self.client._delete_config = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="delete",
            id="alert1"
        ))

        self.client._delete_config.assert_called_once_with("alert1", None)
        self.assertEqual(result, {"success": True})

    def test_execute_operation_enable(self):
        """Test execute_operation with enable operation"""

        self.client._enable_config = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="enable",
            id="alert1"
        ))

        self.client._enable_config.assert_called_once_with("alert1", None)
        self.assertEqual(result, {"success": True})

    def test_execute_operation_disable(self):
        """Test execute_operation with disable operation"""

        self.client._disable_config = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="disable",
            id="alert1"
        ))

        self.client._disable_config.assert_called_once_with("alert1", None)
        self.assertEqual(result, {"success": True})

    def test_execute_operation_restore(self):
        """Test execute_operation with restore operation"""

        self.client._restore_config = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="restore",
            id="alert1",
            created=1234567890
        ))

        self.client._restore_config.assert_called_once_with("alert1", 1234567890, None)
        self.assertEqual(result, {"success": True})

    def test_execute_operation_update_baseline(self):
        """Test execute_operation with update baseline operation"""

        self.client._update_baseline = AsyncMock(return_value={"success": True})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation="update_baseline",
            id="alert1"
        ))

        self.client._update_baseline.assert_called_once_with("alert1", None)
        self.assertEqual(result, {"success": True})

    def test_find_active_configs_no_application_id(self):
        result = asyncio.run(
            self.client._find_active_configs(
                application_id=None,
                alert_ids=["alert1"]
            )
        )

        self.assertEqual(
            result,
            {"error": "application_id is required for find_active operation"}
        )

    def test_find_active_configs_success(self):
        self.client.find_active_application_alert_configs = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._find_active_configs(
                application_id="app1",
                alert_ids=["alert1"]
            )
        )

        self.client.find_active_application_alert_configs.assert_called_once_with(
            application_id="app1",
            alert_ids=["alert1"],
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_find_config_versions_no_id(self):
        result = asyncio.run(
            self.client._find_config_versions(
                id=None
            )
        )

        self.assertEqual(
            result,
            {"error": "id is required for find_versions operation"}
        )

    def test_find_config_versions_success(self):
        self.client.find_application_alert_config_versions = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._find_config_versions(
                id="alert1"
            )
        )

        self.client.find_application_alert_config_versions.assert_called_once_with(
            id="alert1",
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_create_config_no_payload(self):
        result = asyncio.run(
            self.client._create_config(
                payload=None
            )
        )

        self.assertEqual(
            result,
            {"error": "payload is required for create operation"}
        )

    def test_create_config_success(self):
        self.client.create_application_alert_config = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._create_config(
                payload={"name": "Test Alert"}
            )
        )

        self.client.create_application_alert_config.assert_called_once_with(
            payload={"name": "Test Alert"},
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_find_config_no_id(self):
        """Test _find_config when id is None"""
        self.client.find_application_alert_config = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._find_config(
                id=None,
                valid_on=None
            )
        )

        self.client.find_application_alert_config.assert_called_once_with(
            id=None,
            valid_on=None,
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_update_config_no_id(self):
        """Test _update_config with missing ID"""
        result = asyncio.run(
            self.client._update_config(
                id=None,
                payload={"name": "Updated Alert"}
            )
        )

        self.assertEqual(
            result,
            {"error": "id is required for update operation"}
        )

    def test_update_config_no_payload(self):
        """Test _update_config with missing payload"""
        result = asyncio.run(
            self.client._update_config(
                id="alert1",
                payload=None
            )
        )

        self.assertEqual(
            result,
            {"error": "payload is required for update operation"}
        )

    def test_update_config_success(self):
        """Test _update_config with valid parameters"""
        self.client.update_application_alert_config = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._update_config(
                id="alert1",
                payload={"name": "Updated Alert"}
            )
        )

        self.client.update_application_alert_config.assert_called_once_with(
            id="alert1",
            payload={"name": "Updated Alert"},
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_delete_config_no_id(self):
        """Test _delete_config with missing ID"""
        result = asyncio.run(
            self.client._delete_config(
                id=None
            )
        )

        self.assertEqual(
            result,
            {"error": "id is required for delete operation"}
        )

    def test_delete_config_success(self):
        """Test _delete_config with valid ID"""
        self.client.delete_application_alert_config = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._delete_config(
                id="alert1"
            )
        )

        self.client.delete_application_alert_config.assert_called_once_with(
            id="alert1",
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_enable_config_no_id(self):
        """Test _enable_config with missing ID"""
        result = asyncio.run(
            self.client._enable_config(
                id=None
            )
        )

        self.assertEqual(
            result,
            {"error": "id is required for enable operation"}
        )

    def test_enable_config_success(self):
        """Test _enable_config with valid ID"""
        self.client.enable_application_alert_config = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._enable_config(
                id="alert1"
            )
        )

        self.client.enable_application_alert_config.assert_called_once_with(
            id="alert1",
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_disable_config_no_id(self):
        """Test _disable_config with missing ID"""
        result = asyncio.run(
            self.client._disable_config(
                id=None
            )
        )

        self.assertEqual(
            result,
            {"error": "id is required for disable operation"}
        )

    def test_disable_config_success(self):
        """Test _disable_config with valid ID"""
        self.client.disable_application_alert_config = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._disable_config(
                id="alert1"
            )
        )

        self.client.disable_application_alert_config.assert_called_once_with(
            id="alert1",
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_restore_config_no_id(self):
        """Test _restore_config with missing ID"""
        result = asyncio.run(
            self.client._restore_config(
                id=None,
                created=1234567890
            )
        )

        self.assertEqual(
            result,
            {"error": "id is required for restore operation"}
        )

    def test_restore_config_no_created(self):
        """Test _restore_config with missing created timestamp"""
        result = asyncio.run(
            self.client._restore_config(
                id="alert1",
                created=None
            )
        )

        self.assertEqual(
            result,
            {"error": "created timestamp is required for restore operation"}
        )

    def test_restore_config_success(self):
        """Test _restore_config with valid parameters"""
        self.client.restore_application_alert_config = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._restore_config(
                id="alert1",
                created=1234567890
            )
        )

        self.client.restore_application_alert_config.assert_called_once_with(
            id="alert1",
            created=1234567890,
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_update_baseline_no_id(self):
        """Test _update_baseline with missing ID"""
        result = asyncio.run(
            self.client._update_baseline(
                id=None
            )
        )

        self.assertEqual(
            result,
            {"error": "id is required for update_baseline operation"}
        )

    def test_update_baseline_success(self):
        """Test _update_baseline with valid ID"""
        self.client.update_application_alert_config_baseline = AsyncMock(
            return_value={"success": True}
        )

        result = asyncio.run(
            self.client._update_baseline(
                id="alert1"
            )
        )

        self.client.update_application_alert_config_baseline.assert_called_once_with(
            id="alert1",
            ctx=None,
            api_client=ANY
        )

        self.assertEqual(result, {"success": True})

    def test_find_active_application_alert_configs_empty_result(self):
        """Test find_active_application_alert_configs with empty result"""
        # Set up the mock response with empty list
        mock_response = MagicMock()
        mock_response.data = b'[]'
        self.alert_config_api.find_all_active_application_alert_configs_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.find_active_application_alert_configs(application_id="app1"))

        # Check that the result contains the expected message
        self.assertIn("configs", result)
        self.assertEqual(len(result["configs"]), 0)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["total"], 0)
        self.assertIn("No active alert configurations found", result["message"])
        self.assertIn("suggestion", result)

    def test_find_active_application_alert_configs_json_decode_error(self):
        """Test find_active_application_alert_configs with JSON decode error"""
        # Set up the mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.data = b'invalid json {'
        self.alert_config_api.find_all_active_application_alert_configs_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.find_active_application_alert_configs(application_id="app1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to parse response JSON", result["error"])

    def test_find_active_application_alert_configs_general_exception(self):
        """Test find_active_application_alert_configs with general exception"""
        # Set up the mock to raise an exception
        self.alert_config_api.find_all_active_application_alert_configs_without_preload_content.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.find_active_application_alert_configs(application_id="app1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get active application alert config", result["error"])

    def test_create_application_alert_config_string_payload_json(self):
        """Test create_application_alert_config with JSON string payload"""
        # Set up the payload as JSON string and mock response
        payload = '{"name": "Test Alert", "description": "Test description"}'
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

    def test_create_application_alert_config_string_payload_single_quotes(self):
        """Test create_application_alert_config with single-quoted string payload"""
        # Set up the payload with single quotes and mock response
        payload = "{'name': 'Test Alert', 'description': 'Test description'}"
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

    def test_create_application_alert_config_string_payload_invalid(self):
        """Test create_application_alert_config with invalid string payload"""
        # Set up the payload with invalid format
        payload = "invalid {{{ payload"

        # Call the method
        result = asyncio.run(self.client.create_application_alert_config(payload=payload))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Invalid payload format", result["error"])

    def test_update_application_alert_config_string_payload_json(self):
        """Test update_application_alert_config with JSON string payload"""
        # Set up the payload as JSON string and mock response
        payload = '{"name": "Updated Alert", "description": "Updated description"}'
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

    def test_update_application_alert_config_string_payload_single_quotes(self):
        """Test update_application_alert_config with single-quoted string payload"""
        # Set up the payload with single quotes and mock response
        payload = "{'name': 'Updated Alert', 'description': 'Updated description'}"
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

    def test_update_application_alert_config_string_payload_invalid(self):
        """Test update_application_alert_config with invalid string payload"""
        # Set up the payload with invalid format
        payload = "invalid {{{ payload"

        # Call the method
        result = asyncio.run(self.client.update_application_alert_config(id="alert1", payload=payload))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Invalid payload format", result["error"])

if __name__ == '__main__':
    unittest.main()
