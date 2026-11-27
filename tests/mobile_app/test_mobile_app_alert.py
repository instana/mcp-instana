"""
Unit tests for the MobileAppAlertMCPTools class
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

app_logger = logging.getLogger("src.mobile_app.mobile_app_alert")
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
sys.modules["instana_client.models.mobile_app_alert_config_with_rbac_tag"] = MagicMock()
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
sys.modules["instana_client.models.mobile_app_alert_config_with_rbac_tag"].MobileAppAlertConfigWithRbacTag = FakeModel

# Patch the with_header_auth decorator before importing the class
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.mobile_app.mobile_app_alert import MobileAppAlertMCPTools

from src.core.utils import decode_response as _decode_response


class MockResponse:
    def __init__(self, payload, headers=None):
        self.data = payload
        self.headers = headers or {}


class TestMobileAppAlertMCPTools(unittest.TestCase):
    """Test MobileAppAlertMCPTools"""

    def setUp(self):
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = MobileAppAlertMCPTools(read_token=self.read_token, base_url=self.base_url)
        self.mock_api = MagicMock()
        self.client.config_api = self.mock_api

    def test_initialization(self):
        """Test MobileAppAlertMCPTools initialization"""
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.io")

    def test_find_mobile_app_alert_config_with_id_success(self):
        """Test find_mobile_app_alert_config with id parameter"""
        mock_config = {
            "id": "alert1",
            "name": "Test Alert",
            "enabled": True
        }

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")
        self.assertEqual(result["name"], "Test Alert")

    def test_find_mobile_app_alert_config_with_valid_on_success(self):
        """Test find_mobile_app_alert_config with valid_on parameter"""
        mock_config = {
            "id": "alert1",
            "validFrom": 1609459200,
            "validTo": 1609545600
        }

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert1", valid_on=1609459200))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")
        self.assertIn("validFrom", result)

    def test_find_mobile_app_alert_config_list_response(self):
        """Test find_mobile_app_alert_config when API returns a list"""
        mock_configs = [{"id": "alert1", "name": "Alert 1"}, {"id": "alert2", "name": "Alert 2"}]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert1"))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_find_mobile_app_alert_config_empty_list(self):
        """Test find_mobile_app_alert_config when API returns empty list"""
        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps([]).encode('utf-8'))
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert1"))

        self.assertIsInstance(result, list)
        self.assertEqual(result, [])

    def test_find_mobile_app_alert_config_dict_response(self):
        """Test find_mobile_app_alert_config when API returns a dict directly"""
        expected_dict = {"id": "alert1", "name": "Test Alert"}

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(expected_dict).encode('utf-8'))
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")

    def test_find_mobile_app_alert_config_api_exception(self):
        """Test find_mobile_app_alert_config when API raises an exception"""
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to get mobile app alert config", result["error"])

    def test_find_mobile_app_alert_config_connection_error(self):
        """Test find_mobile_app_alert_config when connection fails"""
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(
            side_effect=Exception("Connection timeout")
        )

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to get mobile app alert config", result["error"])

    def test_find_mobile_app_alert_config_with_both_id_and_valid_on(self):
        """Test find_mobile_app_alert_config with both id and valid_on parameters"""
        mock_config = {
            "id": "alert1",
            "name": "Test Alert",
            "validFrom": 1609459200
        }

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_mobile_app_alert_config(
            id="alert1",
            valid_on=1609459200
        ))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")
        # Verify both parameters were passed to the API
        self.client.config_api.find_mobile_app_alert_config_without_preload_content.assert_called_once_with(
            id="alert1",
            valid_on=1609459200
        )

    def test_find_mobile_app_alert_config_no_parameters(self):
        """Test find_mobile_app_alert_config without id parameter returns elicitation"""
        result = asyncio.run(self.client.find_mobile_app_alert_config(id=None))

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("id", result["message"])

    def test_find_mobile_app_alert_config_with_model_without_to_dict(self):
        """Test find_mobile_app_alert_config with valid response"""
        mock_config = {"id": "alert1", "name": "Test Alert"}

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert1"))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "alert1")

    def test_find_mobile_app_alert_config_list_with_mixed_types(self):
        """Test find_mobile_app_alert_config when API returns array"""
        mock_configs = [{"id": "alert1"}, {"id": "alert2"}]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert1"))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    # Tests for find_active_mobile_app_alert_configs

    def test_find_active_configs_success_with_results(self):
        """Test find_active_mobile_app_alert_configs with successful results"""
        mock_configs = [
            {"id": "alert1", "name": "Alert 1", "enabled": True},
            {"id": "alert2", "name": "Alert 2", "enabled": False}
        ]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_active_mobile_app_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_mobile_app_alert_configs(mobile_app_id="app123"))

        self.assertIsInstance(result, dict)
        self.assertIn("configs", result)
        self.assertEqual(len(result["configs"]), 2)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["total"], 2)
        self.assertIn("Found 2 active alert configuration", result["message"])

    def test_find_active_configs_empty_results(self):
        """Test find_active_mobile_app_alert_configs with no results"""
        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps([]).encode('utf-8'))
        self.client.config_api.find_active_mobile_app_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_mobile_app_alert_configs(mobile_app_id="app123"))

        self.assertIsInstance(result, dict)
        self.assertEqual(result["configs"], [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["total"], 0)
        self.assertIn("No active alert configurations found", result["message"])
        self.assertIn("suggestion", result)

    def test_find_active_configs_missing_mobile_app_id(self):
        """Test find_active_mobile_app_alert_configs without mobile_app_id"""
        result = asyncio.run(self.client.find_active_mobile_app_alert_configs(mobile_app_id=""))

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("mobile_app_id", result["message"])

    def test_find_active_configs_with_alert_ids_filter(self):
        """Test find_active_mobile_app_alert_configs with alert_ids filter"""
        mock_configs = [{"id": "alert1", "name": "Alert 1"}]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_active_mobile_app_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_mobile_app_alert_configs(
            mobile_app_id="app123",
            alert_ids=["alert1", "alert2"]
        ))

        self.assertIsInstance(result, dict)
        self.assertIn("configs", result)
        self.client.config_api.find_active_mobile_app_alert_configs_without_preload_content.assert_called_once_with(
            mobile_app_id="app123",
            alert_ids=["alert1", "alert2"]
        )

    def test_find_active_configs_pagination_limit(self):
        """Test find_active_mobile_app_alert_configs limits to 10 results"""
        mock_configs = [{"id": f"alert{i}", "name": f"Alert {i}"} for i in range(15)]

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_configs).encode('utf-8'))
        self.client.config_api.find_active_mobile_app_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_mobile_app_alert_configs(mobile_app_id="app123"))

        self.assertEqual(len(result["configs"]), 10)
        self.assertEqual(result["count"], 10)
        self.assertEqual(result["total"], 15)
        self.assertEqual(result["showing"], 10)
        self.assertIn("Showing first 10", result["message"])

    def test_find_active_configs_single_object_response(self):
        """Test find_active_mobile_app_alert_configs when API returns single object"""
        mock_config = {"id": "alert1", "name": "Alert 1"}

        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(json.dumps(mock_config).encode('utf-8'))
        self.client.config_api.find_active_mobile_app_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_mobile_app_alert_configs(mobile_app_id="app123"))

        self.assertIsInstance(result, dict)
        self.assertIn("configs", result)
        self.assertEqual(len(result["configs"]), 1)
        self.assertEqual(result["configs"][0]["id"], "alert1")

    def test_find_active_configs_json_decode_error(self):
        """Test find_active_mobile_app_alert_configs with invalid JSON"""
        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(b"invalid json{")
        self.client.config_api.find_active_mobile_app_alert_configs_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_active_mobile_app_alert_configs(mobile_app_id="app123"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to parse response JSON", result["error"])

    def test_find_active_configs_api_exception(self):
        """Test find_active_mobile_app_alert_configs when API raises exception"""
        self.client.config_api.find_active_mobile_app_alert_configs_without_preload_content = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.find_active_mobile_app_alert_configs(mobile_app_id="app123"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to get active mobile app alert configs", result["error"])

    def test_find_active_configs_none_mobile_app_id(self):
        """Test find_active_mobile_app_alert_configs with None mobile_app_id"""
        result = asyncio.run(self.client.find_active_mobile_app_alert_configs(mobile_app_id=None))

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("mobile_app_id", result["message"])

    def test_find_config_missing_id(self):
        """Test find_mobile_app_alert_config without id returns elicitation"""
        result = asyncio.run(self.client.find_mobile_app_alert_config(id=""))

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("id", result["message"])

    def test_find_config_none_id(self):
        """Test find_mobile_app_alert_config with None id returns elicitation"""
        result = asyncio.run(self.client.find_mobile_app_alert_config(id=None))

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("id", result["message"])

    def test_find_config_json_decode_error(self):
        """Test find_mobile_app_alert_config with invalid JSON"""
        class MockResponse:
            def __init__(self, data):
                self.data = data

        mock_response = MockResponse(b"invalid json{")
        self.client.config_api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.find_mobile_app_alert_config(id="alert123"))

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Failed to parse response JSON", result["error"])


class Resp:
    """Minimal HTTP response double."""

    def __init__(self, status=200, body=b"", headers=None):
        self.status = status
        self.data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.headers = headers or {}


class TestMobileAppAlertWriteOperations(unittest.TestCase):
    """create / update / delete / enable / disable / restore / find_versions"""

    CURRENT = {
        "id": "alert1", "created": 5, "initialCreated": 1, "readOnly": False, "displayUrl": "u", "rbacTags": [],
        "name": "Old", "description": "d", "mobileAppId": "app-1", "enabled": False,
        "rule": {"alertType": "slowness"}, "threshold": {"value": 1}, "severity": 10,
        "rules": [{"rule": {"alertType": "slowness"}, "thresholds": {"CRITICAL": {"value": 1}}}],
        "alertChannelIds": ["ch1"], "alertChannels": {"CRITICAL": ["ch1"]},
    }

    def setUp(self):
        self.client = MobileAppAlertMCPTools(read_token="t", base_url="https://test.instana.io")
        self.api = MagicMock()
        self.client.config_api = self.api
        # raw requests go through api.api_client.call_api(...).response
        self.sent = []

        def fake_call_api(*args, **kwargs):
            return MagicMock(response=self.raw_response)

        self.api.api_client.call_api = fake_call_api
        self.raw_response = Resp(200, {"id": "alert-new"})

        def record(**kwargs):
            self.sent.append(kwargs)
            return ()

        self.api._create_mobile_app_alert_config_serialize = record
        self.api._update_mobile_app_alert_config_serialize = record
        self.api.get_alerting_channels_without_preload_content = Mock(
            side_effect=lambda ids=None: Resp(200, [{"id": i} for i in ids if i.startswith("ch")])
        )
        self.api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=Resp(200, self.CURRENT))

    def run_async(self, coro):
        return asyncio.run(coro)

    # --- create ---

    def test_create_sends_raw_payload(self):
        payload = {"name": "n", "description": "d", "mobileAppId": "app-1", "rules": [{}]}

        result = self.run_async(self.client.create_mobile_app_alert_config(payload=payload))

        self.assertEqual(result, {"id": "alert-new"})
        self.assertEqual(self.sent[0]["mobile_app_alert_config"], payload)

    def test_create_requires_payload(self):
        result = self.run_async(self.client.create_mobile_app_alert_config(payload=None))

        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(self.sent, [])

    def test_create_surfaces_server_error_verbatim(self):
        self.raw_response = Resp(403, {"errors": ["Missing permission canConfigureMobileAppSmartAlerts"]})

        result = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        self.assertIn("403", result["error"])
        self.assertIn("canConfigureMobileAppSmartAlerts", result["error"])

    def test_create_error_with_empty_body(self):
        self.raw_response = Resp(500, b"")

        result = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        self.assertIn("No error details available", result["error"])

    def test_create_unknown_channel_is_rejected_before_write(self):
        payload = {"name": "n", "alertChannelIds": ["ch1", "bogus"]}

        result = self.run_async(self.client.create_mobile_app_alert_config(payload=payload))

        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(result["reason"], "invalid_alert_channels")
        self.assertIn("bogus", result["message"])
        self.assertEqual(self.sent, [])

    def test_create_checks_channels_in_alert_channels_map(self):
        payload = {"name": "n", "alertChannels": {"WARNING": ["ch1"], "CRITICAL": ["ch2", "nope"]}}

        result = self.run_async(self.client.create_mobile_app_alert_config(payload=payload))

        self.assertEqual(result["reason"], "invalid_alert_channels")
        self.assertIn("nope", result["message"])
        self.assertNotIn("ch2", result["message"])
        self.assertEqual(self.sent, [])

    def test_create_known_channels_pass(self):
        payload = {"name": "n", "alertChannelIds": ["ch1", "ch2"]}

        result = self.run_async(self.client.create_mobile_app_alert_config(payload=payload))

        self.assertEqual(result, {"id": "alert-new"})
        self.api.get_alerting_channels_without_preload_content.assert_called_once_with(ids=["ch1", "ch2"])

    def test_create_without_channels_skips_lookup(self):
        self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        self.api.get_alerting_channels_without_preload_content.assert_not_called()

    def test_create_channel_lookup_failure_fails_closed(self):
        self.api.get_alerting_channels_without_preload_content = Mock(return_value=Resp(403, {"errors": ["nope"]}))

        result = self.run_async(self.client.create_mobile_app_alert_config(
            payload={"name": "n", "alertChannelIds": ["ch1"]}))

        self.assertIn("Could not verify alert channels", result["error"])
        self.assertEqual(self.sent, [])

    # --- update ---

    FULL_PAYLOAD = {
        "name": "New", "description": "d", "mobileAppId": "app-1", "enabled": False,
        "rules": [{"rule": {"alertType": "slowness"}, "thresholds": {"CRITICAL": {"value": 1}}}],
        "alertChannelIds": ["ch1"],
    }

    def test_update_sends_payload_as_is_and_strips_server_only_fields(self):
        payload = {**self.FULL_PAYLOAD, "id": "alert1", "created": 1, "initialCreated": 1,
                   "readOnly": False, "displayUrl": "u", "rbacTags": []}

        result = self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=payload))

        self.assertEqual(self.sent[0]["id"], "alert1")
        self.assertEqual(self.sent[0]["mobile_app_alert_config"], self.FULL_PAYLOAD)
        self.assertEqual(result, {"id": "alert-new"})

    def test_update_strips_legacy_rule_fields(self):
        payload = {**self.FULL_PAYLOAD, "rule": {"alertType": "slowness"}, "threshold": {"value": 1}, "severity": 10}

        self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=payload))

        self.assertEqual(self.sent[0]["mobile_app_alert_config"], self.FULL_PAYLOAD)

    def test_update_strips_threshold_baselines(self):
        payload = {
            **self.FULL_PAYLOAD,
            "rules": [{
                "rule": {"alertType": "slowness"},
                "thresholds": {
                    "WARNING": {"type": "historicBaseline", "seasonality": "WEEKLY", "deviationFactor": 1.5,
                                "baseline": [[1, 2, 3]]},
                    "CRITICAL": {"type": "staticThreshold", "value": 1},
                },
            }],
        }

        self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=payload))

        thresholds = self.sent[0]["mobile_app_alert_config"]["rules"][0]["thresholds"]
        self.assertEqual(thresholds["WARNING"],
                         {"type": "historicBaseline", "seasonality": "WEEKLY", "deviationFactor": 1.5})
        self.assertEqual(thresholds["CRITICAL"], {"type": "staticThreshold", "value": 1})
        # the caller's payload is not mutated
        self.assertIn("baseline", payload["rules"][0]["thresholds"]["WARNING"])

    def test_update_without_channels_does_not_fetch_current_config(self):
        payload = {k: v for k, v in self.FULL_PAYLOAD.items() if k != "alertChannelIds"}

        self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=payload))

        self.api.find_mobile_app_alert_config_without_preload_content.assert_not_called()

    def test_update_skips_validation_of_channels_already_attached(self):
        # ch1 is already stored on the alert, so it is not looked up even if it was deleted since.
        self.api.get_alerting_channels_without_preload_content = Mock(return_value=Resp(403, {"errors": ["nope"]}))

        result = self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=self.FULL_PAYLOAD))

        self.assertEqual(result, {"id": "alert-new"})
        self.api.get_alerting_channels_without_preload_content.assert_not_called()

    def test_update_validates_only_newly_added_channels(self):
        payload = {**self.FULL_PAYLOAD, "alertChannelIds": ["ch1", "ch2"]}

        self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=payload))

        self.api.get_alerting_channels_without_preload_content.assert_called_once_with(ids=["ch2"])

    def test_update_rejects_new_unknown_channel_even_if_others_are_attached(self):
        payload = {**self.FULL_PAYLOAD, "alertChannelIds": ["ch1", "bogus"]}

        result = self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=payload))

        self.assertEqual(result["reason"], "invalid_alert_channels")
        self.assertIn("bogus", result["message"])
        self.assertEqual(self.sent, [])

    def test_update_validates_all_channels_when_stored_config_cannot_be_read(self):
        self.api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=Resp(500, b""))

        self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=self.FULL_PAYLOAD))

        self.api.get_alerting_channels_without_preload_content.assert_called_once_with(ids=["ch1"])

    def test_update_without_channels_skips_lookup(self):
        payload = {k: v for k, v in self.FULL_PAYLOAD.items() if k != "alertChannelIds"}

        self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=payload))

        self.api.get_alerting_channels_without_preload_content.assert_not_called()

    def test_update_empty_channel_ids_are_sent_as_given(self):
        payload = {**self.FULL_PAYLOAD, "alertChannelIds": []}

        self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=payload))

        self.assertEqual(self.sent[0]["mobile_app_alert_config"]["alertChannelIds"], [])

    def test_update_unknown_channel_is_rejected_before_write(self):
        result = self.run_async(self.client.update_mobile_app_alert_config(
            id="alert1", payload={**self.FULL_PAYLOAD, "alertChannelIds": ["bogus"]}))

        self.assertEqual(result["reason"], "invalid_alert_channels")
        self.assertEqual(self.sent, [])

    def test_update_204_returns_refetched_config(self):
        self.raw_response = Resp(204, b"")

        result = self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=self.FULL_PAYLOAD))

        self.assertEqual(result["id"], "alert1")
        # once to read the attached channels, once to re-read the updated config
        self.assertEqual(self.api.find_mobile_app_alert_config_without_preload_content.call_count, 2)

    def test_update_204_with_failed_refetch_still_reports_success(self):
        self.raw_response = Resp(204, b"")
        self.api.find_mobile_app_alert_config_without_preload_content = Mock(return_value=Resp(500, b""))

        result = self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=self.FULL_PAYLOAD))

        self.assertTrue(result["success"])
        self.assertIn("could not be re-read", result["warning"])

    def test_update_server_error_is_surfaced(self):
        self.raw_response = Resp(404, {"errors": ["Can not find config"]})

        result = self.run_async(self.client.update_mobile_app_alert_config(id="missing", payload=self.FULL_PAYLOAD))

        self.assertIn("404", result["error"])

    def test_update_requires_id_and_payload(self):
        no_id = self.run_async(self.client.update_mobile_app_alert_config(id=None, payload={"name": "x"}))
        no_payload = self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=None))

        self.assertEqual(no_id["api_error"][0]["field"], "id")
        self.assertEqual(no_payload["api_error"][0]["field"], "payload")

    # --- delete / enable / disable ---

    def test_delete_enable_disable_report_success(self):
        for method, sdk, word in (
            ("delete_mobile_app_alert_config", "delete_mobile_app_alert_config_without_preload_content", "deleted"),
            ("enable_mobile_app_alert_config", "enable_mobile_app_alert_config_without_preload_content", "enabled"),
            ("disable_mobile_app_alert_config", "disable_mobile_app_alert_config_without_preload_content", "disabled"),
        ):
            with self.subTest(method=method):
                setattr(self.api, sdk, Mock(return_value=Resp(204, b"")))

                result = self.run_async(getattr(self.client, method)(id="alert1"))

                self.assertTrue(result["success"])
                self.assertIn(word, result["message"])
                getattr(self.api, sdk).assert_called_once_with(id="alert1")

    def test_lifecycle_requires_id(self):
        for method in ("delete_mobile_app_alert_config", "enable_mobile_app_alert_config",
                       "disable_mobile_app_alert_config", "find_mobile_app_alert_config_versions"):
            with self.subTest(method=method):
                result = self.run_async(getattr(self.client, method)(id=None))

                self.assertTrue(result["elicitation_needed"])

    def test_lifecycle_surfaces_errors(self):
        self.api.delete_mobile_app_alert_config_without_preload_content = Mock(
            return_value=Resp(404, {"errors": ["Can not find config"]}))

        result = self.run_async(self.client.delete_mobile_app_alert_config(id="missing"))

        self.assertIn("404", result["error"])
        self.assertIn("Can not find config", result["error"])

    def test_lifecycle_sdk_exception_is_caught(self):
        self.api.enable_mobile_app_alert_config_without_preload_content = Mock(side_effect=Exception("down"))

        result = self.run_async(self.client.enable_mobile_app_alert_config(id="alert1"))

        self.assertIn("error", result)

    # --- restore / versions ---

    def test_restore_passes_created(self):
        self.api.restore_mobile_app_alert_config_without_preload_content = Mock(return_value=Resp(204, b""))

        result = self.run_async(self.client.restore_mobile_app_alert_config(id="alert1", created=123))

        self.assertTrue(result["success"])
        self.api.restore_mobile_app_alert_config_without_preload_content.assert_called_once_with(id="alert1", created=123)

    def test_restore_requires_created(self):
        result = self.run_async(self.client.restore_mobile_app_alert_config(id="alert1", created=None))

        self.assertEqual(result["api_error"][0]["field"], "created")

    def test_find_versions_returns_all_versions_uncapped(self):
        versions = [{"id": "alert1", "created": i, "enabled": True, "deleted": False} for i in range(25)]
        self.api.find_mobile_app_alert_config_versions_without_preload_content = Mock(return_value=Resp(200, versions))

        result = self.run_async(self.client.find_mobile_app_alert_config_versions(id="alert1"))

        self.assertEqual(result["count"], 25)
        self.assertEqual(len(result["versions"]), 25)

    # --- review fixes ---

    def test_create_empty_2xx_body_is_success_not_parse_error(self):
        for status in (200, 201, 204):
            with self.subTest(status=status):
                self.raw_response = Resp(status, b"")

                result = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

                self.assertTrue(result["success"])
                self.assertNotIn("error", result)

    def test_find_versions_empty_body_is_empty_list(self):
        self.api.find_mobile_app_alert_config_versions_without_preload_content = Mock(return_value=Resp(200, b""))

        result = self.run_async(self.client.find_mobile_app_alert_config_versions(id="alert1"))

        self.assertEqual(result, {"versions": [], "count": 0})

    def test_find_versions_non_list_body_is_error(self):
        self.api.find_mobile_app_alert_config_versions_without_preload_content = Mock(
            return_value=Resp(200, {"unexpected": 1}))

        result = self.run_async(self.client.find_mobile_app_alert_config_versions(id="alert1"))

        self.assertIn("error", result)
        self.assertNotIn("versions", result)

    def test_collect_channel_ids_rejects_wrong_types(self):
        from src.mobile_app.mobile_app_alert import _collect_channel_ids

        for bad in ({"alertChannelIds": "abc"},
                    {"alertChannelIds": [{"a": 1}]},
                    {"alertChannels": ["a"]},
                    {"alertChannels": {"WARNING": "ch1"}}):
            with self.subTest(payload=bad):
                with self.assertRaises(ValueError):
                    _collect_channel_ids(bad)

    def test_create_wrong_channel_type_returns_invalid_payload_without_calls(self):
        for payload, field in (({"name": "n", "alertChannelIds": "abc"}, "alertChannelIds"),
                               ({"name": "n", "alertChannels": ["a"]}, "alertChannels")):
            with self.subTest(field=field):
                result = self.run_async(self.client.create_mobile_app_alert_config(payload=payload))

                self.assertTrue(result["elicitation_needed"])
                self.assertEqual(result["reason"], "invalid_payload")
                self.assertEqual(result["api_error"][0]["field"], field)
        self.api.get_alerting_channels_without_preload_content.assert_not_called()
        self.assertEqual(self.sent, [])

    def test_write_timeout_warns_outcome_unknown(self):
        timeout = {"error": "Instana API call timed out after 1s (create_mobile_app_alert_config).",
                   "operation": "create_mobile_app_alert_config", "timeout_seconds": 1}

        async def fake_keepalive(coro, **kwargs):
            coro.close()
            return dict(timeout)

        with patch("src.mobile_app.mobile_app_alert.sdk_call_with_keepalive", fake_keepalive):
            result = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        self.assertIn("timed out", result["error"])
        self.assertIn("outcome of this write is unknown", result["warning"])

    def test_timeout_warning_is_operation_specific(self):
        timeout = {"error": "timed out", "timeout_seconds": 1}

        async def fake_keepalive(coro, **kwargs):
            coro.close()
            return dict(timeout)

        with patch("src.mobile_app.mobile_app_alert.sdk_call_with_keepalive", fake_keepalive):
            created = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))
            deleted = self.run_async(self.client.delete_mobile_app_alert_config(id="alert1"))

        self.assertIn("find_active_mobile_app_alert_configs", created["warning"])
        self.assertIn("find_mobile_app_alert_config", deleted["warning"])
        self.assertNotIn("find_active_mobile_app_alert_configs", deleted["warning"])

    def test_failed_write_is_logged_and_error_text_truncated(self):
        self.raw_response = Resp(500, "x" * 5000)

        # Patch the module logger: assertLogs breaks when another test module mocks `logging`.
        with patch("src.mobile_app.mobile_app_alert.logger") as mock_logger:
            result = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        args = mock_logger.warning.call_args.args
        self.assertEqual(args[1:3], ("create_mobile_app_alert_config", 500))
        self.assertLess(len(result["error"]), 2100)

    def test_successful_writes_are_logged_at_info(self):
        self.api.delete_mobile_app_alert_config_without_preload_content = Mock(return_value=Resp(204, b""))

        with patch("src.mobile_app.mobile_app_alert.logger") as mock_logger:
            self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n", "mobileAppId": "app-1"}))
            self.run_async(self.client.delete_mobile_app_alert_config(id="alert1"))

        messages = [call.args for call in mock_logger.info.call_args_list]
        self.assertTrue(any(a[0].startswith("Created mobile app alert config") for a in messages))
        self.assertIn(("%s succeeded: id=%s", "delete_mobile_app_alert_config", "alert1"), messages)

    def test_malformed_channel_field_is_reported_by_name(self):
        result = self.run_async(self.client.create_mobile_app_alert_config(
            payload={"name": "n", "alertChannelIds": "abc"}))

        self.assertEqual(result["api_error"][0]["field"], "alertChannelIds")

    def test_read_timeout_has_no_write_warning(self):
        timeout = {"error": "timed out", "operation": "find_mobile_app_alert_config_versions", "timeout_seconds": 1}

        async def fake_keepalive(coro, **kwargs):
            coro.close()
            return dict(timeout)

        with patch("src.mobile_app.mobile_app_alert.sdk_call_with_keepalive", fake_keepalive):
            result = self.run_async(self.client.find_mobile_app_alert_config_versions(id="alert1"))

        self.assertNotIn("warning", result)

    def test_update_strips_complete_tag_filter_expression(self):
        payload = {**self.FULL_PAYLOAD, "completeTagFilterExpression": {"type": "TAG_FILTER"}}

        self.run_async(self.client.update_mobile_app_alert_config(id="alert1", payload=payload))

        self.assertEqual(self.sent[0]["mobile_app_alert_config"], self.FULL_PAYLOAD)



    # --- PR review fixes ---

    def test_write_connection_reset_warns_outcome_unknown(self):
        def boom(*a, **k):
            raise ConnectionResetError("reset by peer")

        self.api.api_client.call_api = boom

        result = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        self.assertIn("reset by peer", result["error"])
        self.assertIn("outcome of this write is unknown", result["warning"])
        self.assertIn("find_active_mobile_app_alert_configs", result["warning"])

    def test_write_connection_reset_on_update_warns_with_alert_lookup(self):
        def boom(*a, **k):
            raise ConnectionResetError("reset by peer")

        self.api.api_client.call_api = boom

        result = self.run_async(self.client.update_mobile_app_alert_config(
            id="alert1", payload={k: v for k, v in self.FULL_PAYLOAD.items() if k != "alertChannelIds"}))

        self.assertIn("find_mobile_app_alert_config", result["warning"])
        self.assertNotIn("find_active", result["warning"])

    def test_write_not_sent_connection_error_has_no_unknown_outcome_warning(self):
        from urllib3.exceptions import NewConnectionError

        def refused(*a, **k):
            raise NewConnectionError(None, "connection refused")

        self.api.api_client.call_api = refused

        result = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        self.assertIn("error", result)
        self.assertNotIn("warning", result)

    def test_write_not_sent_error_wrapped_by_max_retry_is_recognised(self):
        from urllib3.exceptions import MaxRetryError, NewConnectionError

        def refused(*a, **k):
            try:
                raise NewConnectionError(None, "connection refused")
            except NewConnectionError as inner:
                raise MaxRetryError(None, "/x", inner) from inner

        self.api.api_client.call_api = refused

        result = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        self.assertNotIn("warning", result)

    def test_lifecycle_connection_reset_warns_outcome_unknown(self):
        self.api.delete_mobile_app_alert_config_without_preload_content = Mock(
            side_effect=ConnectionResetError("reset by peer"))

        result = self.run_async(self.client.delete_mobile_app_alert_config(id="alert1"))

        self.assertIn("outcome of this write is unknown", result["warning"])

    def test_read_connection_error_has_no_write_warning(self):
        self.api.find_mobile_app_alert_config_versions_without_preload_content = Mock(
            side_effect=ConnectionResetError("reset by peer"))

        result = self.run_async(self.client.find_mobile_app_alert_config_versions(id="alert1"))

        self.assertIn("error", result)
        self.assertNotIn("warning", result)

    def test_raw_call_passes_http_timeout_longer_than_async_deadline(self):
        seen = {}

        def capture(*args, **kwargs):
            seen.update(kwargs)
            return MagicMock(response=self.raw_response)

        self.api.api_client.call_api = capture

        with patch("src.mobile_app.mobile_app_alert._api_timeout", return_value=30):
            self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        self.assertEqual(seen["_request_timeout"], 35)

    def test_create_unparsable_2xx_body_is_not_reported_as_failure(self):
        self.raw_response = Resp(200, b"not json{")

        result = self.run_async(self.client.create_mobile_app_alert_config(payload={"name": "n"}))

        self.assertTrue(result["success"])
        self.assertNotIn("error", result)
        self.assertIn("do not retry", result["warning"])

    def test_update_unparsable_2xx_body_is_not_reported_as_failure(self):
        self.raw_response = Resp(200, b"not json{")

        result = self.run_async(self.client.update_mobile_app_alert_config(
            id="alert1", payload={k: v for k, v in self.FULL_PAYLOAD.items() if k != "alertChannelIds"}))

        self.assertTrue(result["success"])
        self.assertNotIn("error", result)

    def test_lifecycle_missing_id_message_names_the_verb(self):
        for method, verb in (("delete_mobile_app_alert_config", "delete"),
                             ("enable_mobile_app_alert_config", "enable"),
                             ("disable_mobile_app_alert_config", "disable"),
                             ("restore_mobile_app_alert_config", "restore")):
            with self.subTest(method=method):
                result = self.run_async(getattr(self.client, method)(id=None, **(
                    {"created": 1} if verb == "restore" else {})))

                self.assertEqual(result["api_error"][0]["issue"], f"id is required for {verb}")

    def test_raw_call_matches_sdk_serializer_contract(self):
        """The raw write path calls private SDK serializers; fail loudly if an upgrade changes them."""
        import importlib
        import inspect

        real_api = importlib.import_module("instana_client.api.event_settings_api")
        if isinstance(real_api, MagicMock):  # another test module replaced the SDK with a mock
            self.skipTest("instana_client is mocked in this test session")
        for name in ("_create_mobile_app_alert_config_serialize", "_update_mobile_app_alert_config_serialize"):
            params = inspect.signature(getattr(real_api.EventSettingsApi, name)).parameters
            for required in ("mobile_app_alert_config", "_request_auth", "_content_type", "_headers", "_host_index"):
                self.assertIn(required, params, f"{name} no longer accepts '{required}'")
        call_params = inspect.signature(real_api.ApiClient.call_api).parameters if hasattr(
            real_api, "ApiClient") else None
        if call_params is not None:
            self.assertIn("_request_timeout", call_params)


if __name__ == "__main__":
    unittest.main()
