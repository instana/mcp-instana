"""
Unit tests for the WebsiteAlertMCPTools class
"""

import asyncio
import json
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import AsyncMock, MagicMock, Mock, patch


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


logging.basicConfig(level=logging.ERROR)

app_logger = logging.getLogger("src.website.website_alert")
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Just pass the API client directly
            kwargs['api_client'] = self.config_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

sys.modules["instana_client"] = MagicMock()
sys.modules["instana_client.api"] = MagicMock()
sys.modules["instana_client.api.event_settings_api"] = MagicMock()
sys.modules["instana_client.models"] = MagicMock()
sys.modules["instana_client.models.website_alert_config_with_rbac_tag"] = MagicMock()
sys.modules["instana_client.configuration"] = MagicMock()
sys.modules["instana_client.api_client"] = MagicMock()


class FakeModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def to_dict(self):
        return self.kwargs


# Set up mock classes
mock_event_settings_api = MagicMock()
mock_event_settings_api.__name__ = "EventSettingsApi"

sys.modules["instana_client.api.event_settings_api"].EventSettingsApi = mock_event_settings_api
sys.modules["instana_client.models.website_alert_config_with_rbac_tag"].WebsiteAlertConfigWithRbacTag = FakeModel

# Patch the with_header_auth decorator before importing the class
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.website.website_alert import WebsiteAlertMCPTools

from src.core.utils import decode_response as _decode_response


class MockResponse:
    def __init__(self, payload, headers=None):
        self.data = payload
        self.headers = headers or {}


class TestWebsiteAlertMCPTools(unittest.TestCase):
    """Test WebsiteAlertMCPTools"""

    def setUp(self):
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = WebsiteAlertMCPTools(read_token=self.read_token, base_url=self.base_url)
        self.mock_api = MagicMock()
        self.client.config_api = self.mock_api

    def test_initialization(self):
        """Test WebsiteAlertMCPTools initialization"""
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.io")

    def test_find_website_alert_config_with_id_success(self):
        """Test find_website_alert_config with id parameter"""
        mock_config = {
            "id": "alert1",
            "name": "Test Alert",
            "enabled": True
        }

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")
        self.assertEqual(result["name"], "Test Alert")

    def test_find_website_alert_config_with_valid_on_success(self):
        """Test find_website_alert_config with valid_on parameter"""
        mock_config = {
            "id": "alert1",
            "validFrom": 1609459200,
            "validTo": 1609545600
        }

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert1", valid_on=1609459200))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")
        self.assertIn("validFrom", result)

    def test_find_website_alert_config_list_response(self):
        """Test find_website_alert_config when API returns a list"""
        mock_configs = [{"id": "alert1", "name": "Alert 1"}, {"id": "alert2", "name": "Alert 2"}]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_find_website_alert_config_empty_list(self):
        """Test find_website_alert_config when API returns empty list"""
        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps([]).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, list)
        self.assertEqual(result, [])

    def test_find_website_alert_config_dict_response(self):
        """Test find_website_alert_config when API returns a dict directly"""
        expected_dict = {"id": "alert1", "name": "Test Alert"}

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(expected_dict).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")

    def test_find_website_alert_config_api_exception(self):
        """Test find_website_alert_config when API raises an exception"""
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to get website alert config", result["error"])

    def test_find_website_alert_config_connection_error(self):
        """Test find_website_alert_config when connection fails"""
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(
            side_effect=Exception("Connection timeout")
        )

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to get website alert config", result["error"])

    def test_find_website_alert_config_with_both_id_and_valid_on(self):
        """Test find_website_alert_config with both id and valid_on parameters"""
        mock_config = {
            "id": "alert1",
            "name": "Test Alert",
            "validFrom": 1609459200
        }

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(
            id="alert1",
            valid_on=1609459200
        ))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")
        # Verify both parameters were passed to the API
        self.client.config_api.find_website_alert_config_without_preload_content.assert_called_once_with(
            id="alert1",
            valid_on=1609459200
        )

    def test_find_website_alert_config_no_parameters(self):
        """Test find_website_alert_config without id parameter returns error"""
        result = asyncio.run(self.client.find_website_alert_config(id=None))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_find_website_alert_config_with_model_without_to_dict(self):
        """Test find_website_alert_config with valid response"""
        mock_config = {"id": "alert1", "name": "Test Alert"}

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")

    def test_find_website_alert_config_list_with_mixed_types(self):
        """Test find_website_alert_config when API returns array"""
        mock_configs = [{"id": "alert1"}, {"id": "alert2"}]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_find_website_alert_config_with_complex_config(self):
        """Test find_website_alert_config with complex alert configuration"""
        mock_config = {
            "id": "alert_complex",
            "name": "Complex Alert",
            "enabled": True,
            "conditions": [
                {
                    "metric": "response_time",
                    "threshold": 1000,
                    "operator": "greater_than"
                }
            ],
            "actions": [
                {
                    "type": "email",
                    "recipients": ["admin@example.com"]
                }
            ],
            "validFrom": 1609459200,
            "validTo": None
        }

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert_complex"))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert_complex")
        self.assertTrue(result["enabled"])
        self.assertEqual(len(result["conditions"]), 1)
        self.assertEqual(result["conditions"][0]["threshold"], 1000)

    def test_find_website_alert_config_large_list(self):
        """Test find_website_alert_config with a large list of configs"""
        configs = []
        for i in range(100):
            configs.append({
                "id": f"alert_{i}",
                "name": f"Alert {i}"
            })

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(configs).encode('utf-8'))
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 100)
        self.assertEqual(result[0]["id"], "alert_0")
        self.assertEqual(result[99]["id"], "alert_99")

    def test_find_website_alert_config_malformed_response(self):
        """Test find_website_alert_config with malformed JSON"""
        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(b"invalid json{")
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to parse response JSON", result["error"])

    # Tests for find_active_website_alert_configs

    def test_find_active_configs_success_with_results(self):
        """Test find_active_website_alert_configs with successful results"""
        mock_configs = [
            {"id": "alert1", "name": "Alert 1", "enabled": True},
            {"id": "alert2", "name": "Alert 2", "enabled": False}
        ]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_active_website_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_website_alert_configs(website_id="web123"))

        self.assertIsInstance(result, dict)
        self.assertIn("configs", result)
        self.assertEqual(len(result["configs"]), 2)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["total"], 2)
        self.assertIn("Found 2 active alert configuration", result["message"])

    def test_find_active_configs_empty_results(self):
        """Test find_active_website_alert_configs with no results"""
        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps([]).encode('utf-8'))
        self.client.config_api.find_active_website_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_website_alert_configs(website_id="web123"))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["configs"], [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["total"], 0)
        self.assertIn("No active alert configurations found", result["message"])
        self.assertIn("suggestion", result)

    def test_find_active_configs_missing_website_id(self):
        """Test find_active_website_alert_configs without website_id"""
        result = asyncio.run(self.client.find_active_website_alert_configs(website_id=""))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("website_id is required", result["error"])

    def test_find_active_configs_with_alert_ids_filter(self):
        """Test find_active_website_alert_configs with alert_ids filter"""
        mock_configs = [{"id": "alert1", "name": "Alert 1"}]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_active_website_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_website_alert_configs(
            website_id="web123",
            alert_ids=["alert1", "alert2"]
        ))

        self.assertIsInstance(result, dict)
        self.assertIn("configs", result)
        self.client.config_api.find_active_website_alert_configs_without_preload_content.assert_called_once_with(
            website_id="web123",
            alert_ids=["alert1", "alert2"]
        )

    def test_find_active_configs_pagination_limit(self):
        """Test find_active_website_alert_configs limits to 10 results"""
        mock_configs = [{"id": f"alert{i}", "name": f"Alert {i}"} for i in range(15)]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_active_website_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_website_alert_configs(website_id="web123"))

        self.assertEqual(len(result["configs"]), 10)
        self.assertEqual(result["count"], 10)
        self.assertEqual(result["total"], 15)
        self.assertEqual(result["showing"], 10)
        self.assertIn("Showing first 10", result["message"])

    def test_find_active_configs_single_object_response(self):
        """Test find_active_website_alert_configs when API returns single object"""
        mock_config = {"id": "alert1", "name": "Alert 1"}

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_active_website_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_website_alert_configs(website_id="web123"))

        self.assertIsInstance(result, dict)
        self.assertIn("configs", result)
        self.assertEqual(len(result["configs"]), 1)
        self.assertEqual(result["configs"][0]["id"], "alert1")

    def test_find_active_configs_json_decode_error(self):
        """Test find_active_website_alert_configs with invalid JSON"""
        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(b"invalid json{")
        self.client.config_api.find_active_website_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_website_alert_configs(website_id="web123"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to parse response JSON", result["error"])

    def test_find_active_configs_api_exception(self):
        """Test find_active_website_alert_configs when API raises exception"""
        self.client.config_api.find_active_website_alert_configs_without_preload_content = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.find_active_website_alert_configs(website_id="web123"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to get active website alert configs", result["error"])

    def test_find_active_configs_none_website_id(self):
        """Test find_active_website_alert_configs with None website_id"""
        result = asyncio.run(self.client.find_active_website_alert_configs(website_id=None))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("website_id is required", result["error"])

    def test_find_config_missing_id(self):
        """Test find_website_alert_config without id"""
        result = asyncio.run(self.client.find_website_alert_config(id=""))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_find_config_none_id(self):
        """Test find_website_alert_config with None id"""
        result = asyncio.run(self.client.find_website_alert_config(id=None))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_find_config_json_decode_error(self):
        """Test find_website_alert_config with invalid JSON"""
        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(b"invalid json{")
        self.client.config_api.find_website_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_website_alert_config(id="alert123"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to parse response JSON", result["error"])


if __name__ == "__main__":
    unittest.main()
