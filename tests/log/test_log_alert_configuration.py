"""
Unit tests for the LogAlertConfigurationMCPTools class
"""

import asyncio
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # For testing, we need to ensure the API client is properly set
            # The decorator should inject the API client into kwargs
            if 'api_client' not in kwargs or kwargs['api_client'] is None:
                # Use the existing API client from the instance
                if hasattr(self, 'log_alert_api'):
                    kwargs['api_client'] = self.log_alert_api
                else:
                    # Fallback to the global mock
                    kwargs['api_client'] = mock_log_alert_config_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Save original modules to restore after import
_instana_module_names = [
    'instana_client',
    'instana_client.api',
    'instana_client.api.log_alert_configuration_api',
    'instana_client.configuration',
    'instana_client.api_client',
    'instana_client.models',
    'instana_client.models.log_alert_config',
]
_original_instana_modules = {name: sys.modules.get(name) for name in _instana_module_names}

# Create mock modules and classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_log_alert_config_api = MagicMock()
mock_log_alert_config = MagicMock()

mock_log_alert_config_api.__name__ = "LogAlertConfigurationApi"
mock_log_alert_config.__name__ = "LogAlertConfig"

mock_instana_client = MagicMock()
mock_instana_api_pkg = MagicMock()
mock_instana_models_pkg = MagicMock()
mock_instana_configuration_pkg = MagicMock()
mock_instana_api_client_pkg = MagicMock()
mock_instana_log_alert_api_pkg = MagicMock()
mock_instana_log_alert_model_pkg = MagicMock()

mock_instana_configuration_pkg.Configuration = mock_configuration
mock_instana_api_client_pkg.ApiClient = mock_api_client
mock_instana_log_alert_api_pkg.LogAlertConfigurationApi = mock_log_alert_config_api
mock_instana_log_alert_model_pkg.LogAlertConfig = mock_log_alert_config

sys.modules['instana_client'] = mock_instana_client
sys.modules['instana_client.api'] = mock_instana_api_pkg
sys.modules['instana_client.api.log_alert_configuration_api'] = mock_instana_log_alert_api_pkg
sys.modules['instana_client.configuration'] = mock_instana_configuration_pkg
sys.modules['instana_client.api_client'] = mock_instana_api_client_pkg
sys.modules['instana_client.models'] = mock_instana_models_pkg
sys.modules['instana_client.models.log_alert_config'] = mock_instana_log_alert_model_pkg

# Mock the LogAlertConfig instance returned on instantiation
mock_log_alert_config_instance = MagicMock()
mock_log_alert_config_instance.to_dict.return_value = {"id": "test_alert_id", "name": "Test Alert"}
mock_log_alert_config.return_value = mock_log_alert_config_instance

# Patch the decorator before importing the module
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test first
    from src.log.log_alert_configuration import LogAlertConfigurationMCPTools

# Restore original modules
for _mod_name, _orig_mod in _original_instana_modules.items():
    if _orig_mod is not None:
        sys.modules[_mod_name] = _orig_mod
    else:
        sys.modules.pop(_mod_name, None)

class TestLogAlertConfigurationMCPTools(unittest.TestCase):
    """Test the LogAlertConfigurationMCPTools class"""


    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_log_alert_config_api.reset_mock()
        mock_log_alert_config.reset_mock()

        # Reset the side_effect to None for normal operation
        mock_log_alert_config.side_effect = None

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.log_alert_config_api = mock_log_alert_config_api

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = LogAlertConfigurationMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.log_alert_api = mock_log_alert_config_api
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
    def test_create_log_alert_config_success(self):
        """Test create_log_alert_config with a successful response"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={
            "id": "test_alert_id",
            "name": "Test Alert",
            "query": "test query",
            "threshold": 5,
            "timeThreshold": 300000,
            "enabled": True
        })
        self.client.log_alert_api.create_log_alert_config = MagicMock(return_value=mock_result)

        # Set up the mock config object
        mock_config_instance = MagicMock()
        mock_log_alert_config.return_value = mock_config_instance

        # Call the method
        config = {
            "name": "Test Alert",
            "query": "test query",
            "threshold": 5,
            "timeThreshold": 300000,
            "rule": {"type": "count"}
        }

        result = asyncio.run(self.client.create_log_alert_config(config=config))

        # Check that the mock was called with the correct arguments
        mock_log_alert_config.assert_called_once_with(**config)
        self.client.log_alert_api.create_log_alert_config.assert_called_once_with(
            log_alert_config=mock_config_instance
        )

        # Check that the result is correct
        self.assertEqual(result["id"], "test_alert_id")
        self.assertEqual(result["name"], "Test Alert")
        self.assertEqual(result["query"], "test query")
        self.assertEqual(result["threshold"], 5)
        self.assertEqual(result["timeThreshold"], 300000)
        self.assertEqual(result["enabled"], True)

    def test_create_log_alert_config_error(self):
        """Test create_log_alert_config error handling"""
        # Set up the mock to raise an exception
        mock_log_alert_config.side_effect = Exception("Test error")

        # Call the method
        config = {
            "name": "Test Alert",
            "query": "test query",
            "threshold": 5,
            "timeThreshold": 300000,
            "rule": {"type": "count"}
        }

        result = asyncio.run(self.client.create_log_alert_config(config=config))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to create log alert configuration", result["error"])
        self.assertIn("Test error", result["error"])

    def test_delete_log_alert_config_success(self):
        """Test delete_log_alert_config with a successful response"""
        # Set up the mock to not raise an exception
        self.client.log_alert_api.delete_log_alert_config = MagicMock()

        # Call the method
        alert_id = "test_alert_id"

        result = asyncio.run(self.client.delete_log_alert_config(id=alert_id))

        # Check that the mock was called with the correct arguments
        self.client.log_alert_api.delete_log_alert_config.assert_called_once_with(id=alert_id)

        # Check that the result is correct - the implementation returns a success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn(alert_id, result["message"])

    def test_delete_log_alert_config_error(self):
        """Test delete_log_alert_config error handling"""
        # Set up the mock to raise an exception
        self.client.log_alert_api.delete_log_alert_config = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        alert_id = "test_alert_id"

        result = asyncio.run(self.client.delete_log_alert_config(id=alert_id))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to delete log alert configuration", result["error"])
        self.assertIn("Test error", result["error"])

    def test_disable_log_alert_config_success(self):
        """Test disable_log_alert_config with a successful response"""
        # Set up the mock to not raise an exception
        self.client.log_alert_api.disable_log_alert_config = MagicMock()

        # Call the method
        alert_id = "test_alert_id"

        result = asyncio.run(self.client.disable_log_alert_config(id=alert_id))

        # Check that the mock was called with the correct arguments
        self.client.log_alert_api.disable_log_alert_config.assert_called_once_with(id=alert_id)

        # Check that the result is correct - the implementation returns a success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn(alert_id, result["message"])
        self.assertIn("disabled", result["message"])

    def test_disable_log_alert_config_error(self):
        """Test disable_log_alert_config error handling"""
        # Set up the mock to raise an exception
        self.client.log_alert_api.disable_log_alert_config = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        alert_id = "test_alert_id"

        result = asyncio.run(self.client.disable_log_alert_config(id=alert_id))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to disable log alert configuration", result["error"])
        self.assertIn("Test error", result["error"])

    def test_enable_log_alert_config_success(self):
        """Test enable_log_alert_config with a successful response"""
        # Set up the mock to not raise an exception
        self.client.log_alert_api.enable_log_alert_config = MagicMock()

        # Call the method
        alert_id = "test_alert_id"

        result = asyncio.run(self.client.enable_log_alert_config(id=alert_id))

        # Check that the mock was called with the correct arguments
        self.client.log_alert_api.enable_log_alert_config.assert_called_once_with(id=alert_id)

        # Check that the result is correct - the implementation returns a success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn(alert_id, result["message"])
        self.assertIn("enabled", result["message"])

    def test_enable_log_alert_config_error(self):
        """Test enable_log_alert_config error handling"""
        # Set up the mock to raise an exception
        self.client.log_alert_api.enable_log_alert_config = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        alert_id = "test_alert_id"

        result = asyncio.run(self.client.enable_log_alert_config(id=alert_id))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to enable log alert configuration", result["error"])
        self.assertIn("Test error", result["error"])

    def test_find_log_alert_configs_http_error(self):
        """A non-2xx raw response is returned as an HTTP error, not parsed as data"""
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.data = b'{"errors": ["unauthorized"]}'
        api = self.client.log_alert_api
        api.find_active_log_alert_configs_without_preload_content = MagicMock(return_value=mock_response)
        api.find_log_alert_config_without_preload_content = MagicMock(return_value=mock_response)
        api.find_log_alert_config_versions_without_preload_content = MagicMock(return_value=mock_response)

        for result in (
            asyncio.run(self.client.find_active_log_alert_configs()),
            asyncio.run(self.client.find_log_alert_config(id="alert1")),
            asyncio.run(self.client.find_log_alert_config_versions(id="alert1")),
        ):
            self.assertEqual(result["status_code"], 401)
            self.assertIn("HTTP 401", result["error"])

    def test_find_active_log_alert_configs_success(self):
        """Test find_active_log_alert_configs with a successful response"""
        # Set up the mock response
        mock_config1 = MagicMock()
        mock_config1.to_dict = MagicMock(return_value={
            "id": "alert1",
            "name": "Alert 1",
            "enabled": True
        })

        mock_config2 = MagicMock()
        mock_config2.to_dict = MagicMock(return_value={
            "id": "alert2",
            "name": "Alert 2",
            "enabled": True
        })

        # Mock response object with data attribute
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [mock_config1.to_dict.return_value, mock_config2.to_dict.return_value]
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.client.log_alert_api.find_active_log_alert_configs_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method
        alert_ids = ["alert1", "alert2"]

        result = asyncio.run(self.client.find_active_log_alert_configs(alert_ids=alert_ids))

        # Check that the mock was called with the correct arguments
        self.client.log_alert_api.find_active_log_alert_configs_without_preload_content.assert_called_once_with(alert_ids=alert_ids)

        # Check that the result is correct
        self.assertIn("configs", result)
        self.assertEqual(len(result["configs"]), 2)
        self.assertEqual(result["configs"][0]["id"], "alert1")
        self.assertEqual(result["configs"][1]["id"], "alert2")

    def test_find_active_log_alert_configs_no_params(self):
        """Test find_active_log_alert_configs with no parameters"""
        # Set up the mock response
        mock_config = MagicMock()
        mock_config.to_dict = MagicMock(return_value={
            "id": "alert1",
            "name": "Alert 1",
            "enabled": True
        })

        # Mock response object with data attribute
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [mock_config.to_dict.return_value]
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.client.log_alert_api.find_active_log_alert_configs_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method with no parameters
        result = asyncio.run(self.client.find_active_log_alert_configs())

        # Check that the mock was called with the correct arguments
        self.client.log_alert_api.find_active_log_alert_configs_without_preload_content.assert_called_once_with(alert_ids=None)

        # Check that the result is correct
        self.assertIn("configs", result)
        self.assertEqual(len(result["configs"]), 1)
        self.assertEqual(result["configs"][0]["id"], "alert1")

    def test_find_active_log_alert_configs_error(self):
        """Test find_active_log_alert_configs error handling"""
        # Set up the mock to raise an exception
        self.client.log_alert_api.find_active_log_alert_configs_without_preload_content = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.find_active_log_alert_configs())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to find active log alert configurations", result["error"])
        self.assertIn("Test error", result["error"])

    def test_find_log_alert_config_success(self):
        """Test find_log_alert_config with a successful response"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={
            "id": "test_alert_id",
            "name": "Test Alert",
            "query": "test query",
            "threshold": 5,
            "timeThreshold": 300000,
            "enabled": True
        })
        # Mock response object with data attribute
        mock_response = MagicMock()
        mock_response.status = 200
        import json
        mock_response.data = json.dumps(mock_result.to_dict.return_value).encode('utf-8')
        self.client.log_alert_api.find_log_alert_config_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method
        alert_id = "test_alert_id"
        valid_on = 1625097600000  # Example timestamp

        result = asyncio.run(self.client.find_log_alert_config(id=alert_id, valid_on=valid_on))

        # Check that the mock was called with the correct arguments
        self.client.log_alert_api.find_log_alert_config_without_preload_content.assert_called_once_with(
            id=alert_id,
            valid_on=valid_on
        )

        # Check that the result is correct
        self.assertEqual(result["id"], "test_alert_id")
        self.assertEqual(result["name"], "Test Alert")
        self.assertEqual(result["query"], "test query")
        self.assertEqual(result["threshold"], 5)
        self.assertEqual(result["timeThreshold"], 300000)
        self.assertEqual(result["enabled"], True)

    def test_find_log_alert_config_error(self):
        """Test find_log_alert_config error handling"""
        # Set up the mock to raise an exception
        self.client.log_alert_api.find_log_alert_config_without_preload_content = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        alert_id = "test_alert_id"

        result = asyncio.run(self.client.find_log_alert_config(id=alert_id))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to find log alert configuration", result["error"])
        self.assertIn("Test error", result["error"])

    def test_find_log_alert_config_versions_success(self):
        """Test find_log_alert_config_versions with a successful response"""
        # Set up the mock response
        mock_version1 = MagicMock()
        mock_version1.to_dict = MagicMock(return_value={
            "id": "test_alert_id",
            "version": 1,
            "created": 1625097600000
        })

        mock_version2 = MagicMock()
        mock_version2.to_dict = MagicMock(return_value={
            "id": "test_alert_id",
            "version": 2,
            "created": 1625184000000
        })

        # Mock response object with data attribute
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [mock_version1.to_dict.return_value, mock_version2.to_dict.return_value]
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.client.log_alert_api.find_log_alert_config_versions_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method
        alert_id = "test_alert_id"

        result = asyncio.run(self.client.find_log_alert_config_versions(id=alert_id))

        # Check that the mock was called with the correct arguments
        self.client.log_alert_api.find_log_alert_config_versions_without_preload_content.assert_called_once_with(id=alert_id)

        # Check that the result is correct
        self.assertIn("versions", result)
        self.assertEqual(len(result["versions"]), 2)
        self.assertEqual(result["versions"][0]["id"], "test_alert_id")
        self.assertEqual(result["versions"][0]["version"], 1)
        self.assertEqual(result["versions"][1]["id"], "test_alert_id")
        self.assertEqual(result["versions"][1]["version"], 2)

    def test_find_log_alert_config_versions_error(self):
        """Test find_log_alert_config_versions error handling"""
        # Set up the mock to raise an exception
        self.client.log_alert_api.find_log_alert_config_versions_without_preload_content = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        alert_id = "test_alert_id"

        result = asyncio.run(self.client.find_log_alert_config_versions(id=alert_id))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to find log alert configuration versions", result["error"])
        self.assertIn("Test error", result["error"])

    def test_restore_log_alert_config_success(self):
        """Test restore_log_alert_config with a successful response"""
        # Set up the mock to not raise an exception
        self.client.log_alert_api.restore_log_alert_config = MagicMock()

        # Call the method
        alert_id = "test_alert_id"
        created = 1625097600000  # Example timestamp

        result = asyncio.run(self.client.restore_log_alert_config(id=alert_id, created=created))

        # Check that the mock was called with the correct arguments
        self.client.log_alert_api.restore_log_alert_config.assert_called_once_with(
            id=alert_id,
            created=created
        )

        # Check that the result is correct - the implementation returns a success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn(alert_id, result["message"])
        self.assertIn("restored", result["message"])

    def test_restore_log_alert_config_error(self):
        """Test restore_log_alert_config error handling"""
        # Set up the mock to raise an exception
        self.client.log_alert_api.restore_log_alert_config = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        alert_id = "test_alert_id"
        created = 1625097600000  # Example timestamp

        result = asyncio.run(self.client.restore_log_alert_config(id=alert_id, created=created))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to restore log alert configuration", result["error"])
        self.assertIn("Test error", result["error"])

    def test_update_log_alert_config_success(self):
        """Test update_log_alert_config with a successful response"""
        # Set up the mock response
        mock_result = MagicMock()
        mock_result.to_dict = MagicMock(return_value={
            "id": "test_alert_id",
            "name": "Updated Alert",
            "query": "updated query",
            "threshold": 10,
            "timeThreshold": 600000,
            "enabled": True
        })
        self.client.log_alert_api.update_log_alert_config = MagicMock(return_value=mock_result)

        # Set up the mock config object
        mock_config_instance = MagicMock()
        mock_log_alert_config.return_value = mock_config_instance

        # Call the method
        alert_id = "test_alert_id"
        config = {
            "name": "Updated Alert",
            "query": "updated query",
            "threshold": 10,
            "timeThreshold": 600000,
            "rule": {"type": "count"}
        }

        result = asyncio.run(self.client.update_log_alert_config(id=alert_id, config=config))

        # Check that the mock was called with the correct arguments
        mock_log_alert_config.assert_called_once_with(**config)
        self.client.log_alert_api.update_log_alert_config.assert_called_once_with(
            id=alert_id,
            log_alert_config=mock_config_instance
        )

        # Check that the result is correct
        self.assertEqual(result["id"], "test_alert_id")
        self.assertEqual(result["name"], "Updated Alert")
        self.assertEqual(result["query"], "updated query")
        self.assertEqual(result["threshold"], 10)
        self.assertEqual(result["timeThreshold"], 600000)
        self.assertEqual(result["enabled"], True)

    def test_update_log_alert_config_error(self):
        """Test update_log_alert_config error handling"""
        # Set up the mock to raise an exception
        mock_log_alert_config.side_effect = Exception("Test error")

        # Call the method
        alert_id = "test_alert_id"
        config = {
            "name": "Updated Alert",
            "query": "updated query",
            "threshold": 10,
            "timeThreshold": 600000,
            "rule": {"type": "count"}
        }

        result = asyncio.run(self.client.update_log_alert_config(id=alert_id, config=config))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to update log alert configuration", result["error"])
        self.assertIn("Test error", result["error"])

    def test_convert_to_dict_with_to_dict_method(self):
        """Test _convert_to_dict with an object that has a to_dict method"""
        # Create a mock object with a to_dict method
        mock_obj = MagicMock()
        mock_obj.to_dict = MagicMock(return_value={"key": "value"})

        # Call the method
        result = self.client._convert_to_dict(mock_obj)

        # Check that the result is correct
        self.assertEqual(result, {"key": "value"})
        mock_obj.to_dict.assert_called_once()

    def test_convert_to_dict_with_dict_attribute(self):
        """Test _convert_to_dict with an object that has a __dict__ attribute"""
        # Create a mock object with a __dict__ attribute
        class TestObj:
            def __init__(self):
                self.key = "value"

        test_obj = TestObj()

        # Call the method
        result = self.client._convert_to_dict(test_obj)

        # Check that the result is correct
        self.assertEqual(result, {"key": "value"})

    def test_convert_to_dict_with_other_object(self):
        """Test _convert_to_dict with an object that has neither to_dict nor __dict__"""
        # Call the method with a simple object
        obj = "test string"
        result = self.client._convert_to_dict(obj)

        # Check that the result is the object itself
        self.assertEqual(result, obj)

    def test_create_log_alert_config_api_error(self):
        """Test create_log_alert_config with API call error"""
        mock_config_instance = MagicMock()
        mock_log_alert_config.return_value = mock_config_instance
        self.client.log_alert_api.create_log_alert_config = MagicMock(side_effect=Exception("API Error"))

        config = {"name": "Test", "query": "test", "threshold": 5, "timeThreshold": 300000, "rule": {"type": "count"}}
        result = asyncio.run(self.client.create_log_alert_config(config=config))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_delete_log_alert_config_api_error(self):
        """Test delete_log_alert_config with API error"""
        self.client.log_alert_api.delete_log_alert_config = MagicMock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.delete_log_alert_config(id="alert1"))

        self.assertIn("error", result)

    def test_disable_log_alert_config_api_error(self):
        """Test disable_log_alert_config with API error"""
        self.client.log_alert_api.disable_log_alert_config = MagicMock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.disable_log_alert_config(id="alert1"))

        self.assertIn("error", result)

    def test_enable_log_alert_config_api_error(self):
        """Test enable_log_alert_config with API error"""
        self.client.log_alert_api.enable_log_alert_config = MagicMock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.enable_log_alert_config(id="alert1"))

        self.assertIn("error", result)

    def test_find_active_log_alert_configs_json_decode_error(self):
        """Test find_active_log_alert_configs with JSON decode error"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.client.log_alert_api.find_active_log_alert_configs_without_preload_content = MagicMock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_log_alert_configs())

        self.assertIn("error", result)
        self.assertIn("Failed to parse JSON response", result["error"])

    def test_find_active_log_alert_configs_attribute_error(self):
        """Test find_active_log_alert_configs with attribute error"""
        mock_response = MagicMock()
        mock_response.status = 200
        del mock_response.data
        self.client.log_alert_api.find_active_log_alert_configs_without_preload_content = MagicMock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_log_alert_configs())

        self.assertIn("error", result)

    def test_find_log_alert_config_json_decode_error(self):
        """Test find_log_alert_config with JSON decode error"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.client.log_alert_api.find_log_alert_config_without_preload_content = MagicMock(return_value=mock_response)

        result = asyncio.run(self.client.find_log_alert_config(id="alert1"))

        self.assertIn("error", result)

    def test_find_log_alert_config_versions_json_decode_error(self):
        """Test find_log_alert_config_versions with JSON decode error"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.client.log_alert_api.find_log_alert_config_versions_without_preload_content = MagicMock(return_value=mock_response)

        result = asyncio.run(self.client.find_log_alert_config_versions(id="alert1"))

        self.assertIn("error", result)

    def test_restore_log_alert_config_api_error(self):
        """Test restore_log_alert_config with API error"""
        self.client.log_alert_api.restore_log_alert_config = MagicMock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.restore_log_alert_config(id="alert1", created=1625097600000))

        self.assertIn("error", result)

    def test_update_log_alert_config_api_error(self):
        """Test update_log_alert_config with API error"""
        mock_config_instance = MagicMock()
        mock_log_alert_config.return_value = mock_config_instance
        self.client.log_alert_api.update_log_alert_config = MagicMock(side_effect=Exception("API Error"))

        config = {"name": "Updated", "query": "test", "threshold": 10, "timeThreshold": 600000, "rule": {"type": "count"}}
        result = asyncio.run(self.client.update_log_alert_config(id="alert1", config=config))

        self.assertIn("error", result)

    def test_create_log_alert_config_outer_exception(self):
        """Test create_log_alert_config with outer exception"""
        mock_log_alert_config.side_effect = Exception("Outer error")

        config = {"name": "Test", "query": "test", "threshold": 5, "timeThreshold": 300000, "rule": {"type": "count"}}

        # This should catch the outer exception
        result = asyncio.run(self.client.create_log_alert_config(config=config))

        self.assertIn("error", result)

    def test_delete_log_alert_config_outer_exception(self):
        """Test delete_log_alert_config with outer exception"""
        # Simulate an exception in the outer try block
        self.client.log_alert_api = None

        result = asyncio.run(self.client.delete_log_alert_config(id="alert1"))

        self.assertIn("error", result)

    def test_find_active_log_alert_configs_outer_exception(self):
        """Test find_active_log_alert_configs with outer exception"""
        self.client.log_alert_api = None

        result = asyncio.run(self.client.find_active_log_alert_configs())

        self.assertIn("error", result)

    def test_find_log_alert_config_outer_exception(self):
        """Test find_log_alert_config with outer exception"""
        self.client.log_alert_api = None

        result = asyncio.run(self.client.find_log_alert_config(id="alert1"))

        self.assertIn("error", result)

    def test_find_log_alert_config_versions_outer_exception(self):
        """Test find_log_alert_config_versions with outer exception"""
        self.client.log_alert_api = None

        result = asyncio.run(self.client.find_log_alert_config_versions(id="alert1"))

        self.assertIn("error", result)

    def test_restore_log_alert_config_outer_exception(self):
        """Test restore_log_alert_config with outer exception"""
        self.client.log_alert_api = None

        result = asyncio.run(self.client.restore_log_alert_config(id="alert1", created=1625097600000))

        self.assertIn("error", result)

    def test_update_log_alert_config_outer_exception(self):
        """Test update_log_alert_config with outer exception"""
        mock_log_alert_config.side_effect = Exception("Outer error")

        config = {"name": "Updated", "query": "test", "threshold": 10, "timeThreshold": 600000, "rule": {"type": "count"}}
        result = asyncio.run(self.client.update_log_alert_config(id="alert1", config=config))

        self.assertIn("error", result)


_TIMEOUT_DICT = {
    "error": "Instana API call timed out after 180s (op). The Instana server did not respond in time.",
    "operation": "op",
    "timeout_seconds": 180,
}


async def _timeout_keepalive(coro, *args, **kwargs):
    """Stand in for sdk_call_with_keepalive when the Instana API call times out."""
    if asyncio.iscoroutine(coro):
        coro.close()
    return dict(_TIMEOUT_DICT)


class TestSdkTimeoutHandling(unittest.TestCase):
    """sdk_call_with_keepalive returns an error dict on timeout; a mutating call must not report success."""

    def setUp(self):
        self.client = LogAlertConfigurationMCPTools(read_token="test_token", base_url="https://test.instana.io")
        self.client.log_alert_api = MagicMock()
        patcher = patch(
            "src.log.log_alert_configuration.sdk_call_with_keepalive",
            side_effect=_timeout_keepalive,
        )
        self.mock_keepalive = patcher.start()
        self.addCleanup(patcher.stop)

    def _assert_timeout_error(self, result):
        self.assertIn("timed out", result["error"])
        self.assertEqual(result["timeout_seconds"], 180)
        self.assertNotIn("success", result)
        self.mock_keepalive.assert_called_once()

    def test_delete_timeout(self):
        self._assert_timeout_error(asyncio.run(self.client.delete_log_alert_config(id="alert1")))

    def test_disable_timeout(self):
        self._assert_timeout_error(asyncio.run(self.client.disable_log_alert_config(id="alert1")))

    def test_enable_timeout(self):
        self._assert_timeout_error(asyncio.run(self.client.enable_log_alert_config(id="alert1")))

    def test_restore_timeout(self):
        self._assert_timeout_error(
            asyncio.run(self.client.restore_log_alert_config(id="alert1", created=1625097600000))
        )


if __name__ == '__main__':
    unittest.main()


