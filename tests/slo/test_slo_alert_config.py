"""
Unit tests for SLO Alert Configuration MCP Tools.

Tests the SLOAlertConfigMCPTools which manages SLO alert configurations.
"""

import asyncio
import json
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch

from src.core.utils import parse_payload


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level
logging.basicConfig(level=logging.ERROR)

# Get the SLO logger and replace its handlers
slo_logger = logging.getLogger('src.slo.slo_alert_config')
slo_logger.handlers = []
slo_logger.addHandler(NullHandler())
slo_logger.propagate = False

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator that passes through to actual method
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Resolve the mock API client dynamically because this patched decorator
            # may be reused by other SLO test modules depending on import order.
            for attr_name in ("alert_config_api", "slo_config_api", "correction_api", "report_api"):
                api_client = getattr(self, attr_name, None)
                if api_client is not None:
                    kwargs["api_client"] = api_client
                    break
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.service_levels_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.api.service_levels_objective_slo_configurations_api'] = MagicMock()
sys.modules['instana_client.api.slo_correction_configurations_api'] = MagicMock()
sys.modules['instana_client.api.service_levels_objective_slo_report_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.alerting_time_window'] = MagicMock()
sys.modules['instana_client.models.error_budget_alert_rule'] = MagicMock()
sys.modules['instana_client.models.service_level_objective_alert_rule'] = MagicMock()
sys.modules['instana_client.models.service_levels_alert_config'] = MagicMock()
sys.modules['instana_client.models.service_levels_burn_rate_time_windows'] = MagicMock()
sys.modules['instana_client.models.service_levels_time_threshold'] = MagicMock()
sys.modules['instana_client.models.static_string_field'] = MagicMock()
sys.modules['instana_client.models.static_threshold'] = MagicMock()
sys.modules['instana_client.models.application_slo_entity'] = MagicMock()
sys.modules['instana_client.models.service_level_indicator'] = MagicMock()
sys.modules['instana_client.models.slo_config_with_rbac_tag'] = MagicMock()
sys.modules['instana_client.models.time_window'] = MagicMock()
sys.modules['instana_client.models.correction_configuration'] = MagicMock()
sys.modules['instana_client.models.correction_scheduling'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client_class = MagicMock()
mock_alert_config_api = MagicMock()

# Add __name__ attribute to mock classes
mock_alert_config_api.__name__ = "ServiceLevelsAlertConfigurationApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client_class
sys.modules['instana_client.api.service_levels_alert_configuration_api'].ServiceLevelsAlertConfigurationApi = mock_alert_config_api

# Import with patched decorator
import src.core.utils

original_with_header_auth = src.core.utils.with_header_auth
src.core.utils.with_header_auth = mock_with_header_auth

from src.slo.slo_alert_config import SLOAlertConfigMCPTools

# Restore original decorator
src.core.utils.with_header_auth = original_with_header_auth


class TestSLOAlertConfigMCPTools(unittest.TestCase):
    """Test cases for SLO Alert Config MCP Tools."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client_class.reset_mock()
        mock_alert_config_api.reset_mock()

        # Create the client
        self.client = SLOAlertConfigMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com"
        )

        # Create a mock API client instance
        self.mock_api = MagicMock()
        self.client.alert_config_api = self.mock_api

    def test_initialization(self):
        """Test client initialization."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.com")

    # Validation Tests
    def test_validate_id_parameter_valid(self):
        """Test ID parameter validation with valid ID."""
        result = self.client._validate_id_parameter("alert-123")
        self.assertIsNone(result)

    def test_validate_id_parameter_none(self):
        """Test ID parameter validation with None."""
        result = self.client._validate_id_parameter(None)
        self.assertIn("error", result)
        self.assertIn("required", result["error"])

    def test_validate_id_parameter_empty(self):
        """Test ID parameter validation with empty string."""
        result = self.client._validate_id_parameter("   ")
        self.assertIn("error", result)
        self.assertIn("cannot be empty", result["error"])

    def test_parse_payload_dict(self):
        """Test payload parsing with dict input."""
        payload = {"name": "Test Alert"}
        result = parse_payload(payload)
        self.assertEqual(result, payload)

    def test_parse_payload_json_string(self):
        """Test payload parsing with JSON string."""
        payload = '{"name": "Test Alert"}'
        result = parse_payload(payload)
        self.assertEqual(result, {"name": "Test Alert"})

    def test_parse_payload_invalid_json(self):
        """Test payload parsing with invalid JSON."""
        payload = '{invalid json}'
        result = parse_payload(payload)
        self.assertIn("error", result)

    def test_validate_alert_config_payload_missing_name(self):
        """Test alert config validation with missing name."""
        payload = {
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("elicitation_needed", result)
        self.assertIn("name", result["missing_parameters"])

    def test_validate_alert_config_payload_invalid_severity(self):
        """Test alert config validation with invalid severity."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 7,  # Invalid - must be 5 or 10
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("elicitation_needed", result)

    def test_validate_alert_config_payload_valid(self):
        """Test alert config validation with valid payload."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000},
            "burnRateTimeWindows": {
                "longTimeWindow": {"duration": 1, "durationType": "hour"},
                "shortTimeWindow": {"duration": 5, "durationType": "minute"}
            }
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNone(result)

    def test_clean_alert_config_data(self):
        """Test cleaning alert config data."""
        config = {
            "id": "alert-123",
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "extra_field": "should be removed"
        }
        cleaned = self.client._clean_alert_config_data(config)
        self.assertIn("id", cleaned)
        self.assertIn("name", cleaned)
        self.assertNotIn("extra_field", cleaned)

    # find_active_alert_configs Tests
    def test_find_active_alert_configs_success(self):
        """Test finding active alert configs successfully."""
        async def run_test():
            # Mock the API response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([
                {"id": "alert-1", "name": "Alert 1"},
                {"id": "alert-2", "name": "Alert 2"}
            ]).encode('utf-8')

            self.mock_api.find_active_service_levels_alert_configs_without_preload_content.return_value = mock_response

            result = await self.client.find_active_alert_configs(slo_id="slo-123")

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertIn("configs", result)
            self.assertEqual(len(result["configs"]), 2)

        asyncio.run(run_test())

    def test_find_active_alert_configs_api_error(self):
        """Test finding active alert configs with API error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 404
            mock_response.data = b"Not found"

            self.mock_api.find_active_service_levels_alert_configs_without_preload_content.return_value = mock_response

            result = await self.client.find_active_alert_configs(slo_id="slo-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    # find_alert_config Tests
    def test_find_alert_config_success(self):
        """Test finding alert config by ID successfully."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"id": "alert-123", "name": "Test Alert"}).encode('utf-8')

            self.mock_api.find_service_levels_alert_config_without_preload_content.return_value = mock_response

            result = await self.client.find_alert_config(id="alert-123")

            self.assertIn("id", result)
            self.assertEqual(result["id"], "alert-123")

        asyncio.run(run_test())

    def test_find_alert_config_invalid_id(self):
        """Test finding alert config with invalid ID."""
        async def run_test():
            result = await self.client.find_alert_config(id=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_find_alert_config_with_valid_on(self):
        """Test finding alert config with valid_on timestamp."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"id": "alert-123", "name": "Test Alert"}).encode('utf-8')

            self.mock_api.find_service_levels_alert_config_without_preload_content.return_value = mock_response

            result = await self.client.find_alert_config(id="alert-123", valid_on=1609459200000)

            self.assertIn("id", result)

        asyncio.run(run_test())

    # find_alert_config_versions Tests
    def test_find_alert_config_versions_success(self):
        """Test finding alert config versions successfully."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([
                {"created": 1609459200000, "version": 1},
                {"created": 1612137600000, "version": 2}
            ]).encode('utf-8')

            self.mock_api.find_service_levels_alert_config_versions_without_preload_content.return_value = mock_response

            result = await self.client.find_alert_config_versions(id="alert-123")

            self.assertIn("success", result)
            self.assertIn("versions", result)
            self.assertEqual(result["count"], 2)

        asyncio.run(run_test())

    # create_alert_config Tests
    def test_create_alert_config_missing_fields(self):
        """Test creating alert config with missing required fields."""
        async def run_test():
            payload = {"name": "Test Alert"}  # Missing many required fields

            result = await self.client.create_alert_config(payload=payload)

            self.assertIn("elicitation_needed", result)
            self.assertIn("missing_parameters", result)

        asyncio.run(run_test())

    # delete_alert_config Tests
    def test_delete_alert_config_success(self):
        """Test deleting alert config successfully."""
        async def run_test():
            self.mock_api.delete_service_levels_alert_config.return_value = None

            result = await self.client.delete_alert_config(id="alert-123")

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertIn("deleted", result["message"])

        asyncio.run(run_test())

    def test_delete_alert_config_invalid_id(self):
        """Test deleting alert config with invalid ID."""
        async def run_test():
            result = await self.client.delete_alert_config(id="")
            self.assertIn("error", result)

        asyncio.run(run_test())

    # disable_alert_config Tests
    def test_disable_alert_config_success(self):
        """Test disabling alert config successfully."""
        async def run_test():
            self.mock_api.disable_service_levels_alert_config.return_value = None

            result = await self.client.disable_alert_config(id="alert-123")

            self.assertIn("success", result)
            self.assertIn("disabled", result["message"])

        asyncio.run(run_test())

    # enable_alert_config Tests
    def test_enable_alert_config_success(self):
        """Test enabling alert config successfully."""
        async def run_test():
            self.mock_api.enable_service_levels_alert_config.return_value = None

            result = await self.client.enable_alert_config(id="alert-123")

            self.assertIn("success", result)
            self.assertIn("enabled", result["message"])

        asyncio.run(run_test())

    # restore_alert_config Tests
    def test_restore_alert_config_success(self):
        """Test restoring alert config successfully."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 204

            self.mock_api.restore_service_levels_alert_config_without_preload_content.return_value = mock_response

            result = await self.client.restore_alert_config(id="alert-123", created=1609459200000)

            self.assertIn("success", result)
            self.assertIn("restored", result["message"])

        asyncio.run(run_test())

    def test_restore_alert_config_missing_created(self):
        """Test restoring alert config with missing created timestamp."""
        async def run_test():
            result = await self.client.restore_alert_config(id="alert-123", created=None)
            self.assertIn("error", result)
            self.assertIn("required", result["error"])

        asyncio.run(run_test())

    # Error Handling Tests
    def test_exception_handling_in_find_active(self):
        """Test exception handling in find_active_alert_configs."""
        async def run_test():
            self.mock_api.find_active_service_levels_alert_configs_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.find_active_alert_configs()

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_exception_handling_in_find_config(self):
        """Test exception handling in find_alert_config."""
        async def run_test():
            self.mock_api.find_service_levels_alert_config_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.find_alert_config(id="alert-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_exception_handling_in_delete(self):
        """Test exception handling in delete_alert_config."""
        async def run_test():
            self.mock_api.delete_service_levels_alert_config.side_effect = Exception("Test error")

            result = await self.client.delete_alert_config(id="alert-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_exception_handling_in_disable(self):
        """Test exception handling in disable_alert_config."""
        async def run_test():
            self.mock_api.disable_service_levels_alert_config.side_effect = Exception("Test error")

            result = await self.client.disable_alert_config(id="alert-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_exception_handling_in_enable(self):
        """Test exception handling in enable_alert_config."""
        async def run_test():
            self.mock_api.enable_service_levels_alert_config.side_effect = Exception("Test error")

            result = await self.client.enable_alert_config(id="alert-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_exception_handling_in_restore(self):
        """Test exception handling in restore_alert_config."""
        async def run_test():
            self.mock_api.restore_service_levels_alert_config_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.restore_alert_config(id="alert-123", created=1609459200000)

            self.assertIn("error", result)

        asyncio.run(run_test())

    # Additional validation tests
    def test_validate_id_parameter_not_string(self):
        """Test ID parameter validation with non-string type."""
        result = self.client._validate_id_parameter(123)
        self.assertIn("error", result)
        self.assertIn("must be a string", result["error"])

    def test_parse_payload_none(self):
        """Test payload parsing with None."""
        result = parse_payload(None)
        self.assertIn("error", result)
        self.assertIn("required", result["error"])

    def test_parse_payload_python_literal(self):
        """Test payload parsing with Python literal string."""
        payload = "{'name': 'Test Alert'}"
        result = parse_payload(payload)
        self.assertEqual(result, {"name": "Test Alert"})

    def test_parse_payload_invalid_type(self):
        """Test payload parsing with invalid type."""
        result = parse_payload(123)
        self.assertIn("error", result)

    def test_validate_alert_config_missing_description(self):
        """Test alert config validation with missing description."""
        payload = {
            "name": "Test Alert",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("description", result["missing_parameters"])

    def test_validate_alert_config_missing_slo_ids(self):
        """Test alert config validation with missing sloIds."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("sloIds", result["missing_parameters"])

    def test_validate_alert_config_missing_alert_channel_ids(self):
        """Test alert config validation with missing alertChannelIds."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("alertChannelIds", result["missing_parameters"])

    def test_validate_alert_config_missing_custom_payload_fields(self):
        """Test alert config validation with missing customPayloadFields."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("customPayloadFields", result["missing_parameters"])

    def test_validate_alert_config_missing_rule(self):
        """Test alert config validation with missing rule."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("rule", result["missing_parameters"])

    def test_validate_alert_config_missing_rule_alert_type(self):
        """Test alert config validation with missing rule.alertType."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("rule.alertType", result["missing_parameters"])

    def test_validate_alert_config_missing_rule_metric(self):
        """Test alert config validation with missing rule.metric for ERROR_BUDGET."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("rule.metric", result["missing_parameters"])

    def test_validate_alert_config_missing_burn_rate_time_windows(self):
        """Test alert config validation with missing burnRateTimeWindows for BURN_RATE metric."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("burnRateTimeWindows", result["missing_parameters"])

    def test_validate_alert_config_missing_time_threshold(self):
        """Test alert config validation with missing timeThreshold."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("timeThreshold", result["missing_parameters"])

    def test_validate_alert_config_missing_time_threshold_expiry(self):
        """Test alert config validation with missing timeThreshold.expiry."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
            "timeThreshold": {"timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("timeThreshold.expiry", result["missing_parameters"])

    def test_validate_alert_config_missing_time_threshold_time_window(self):
        """Test alert config validation with missing timeThreshold.timeWindow."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
            "timeThreshold": {"expiry": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("timeThreshold.timeWindow", result["missing_parameters"])

    def test_validate_alert_config_service_level_objective_rule(self):
        """Test alert config validation with SERVICE_LEVELS_OBJECTIVE rule type."""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "SERVICE_LEVELS_OBJECTIVE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNone(result)

    def test_find_alert_config_invalid_valid_on_type(self):
        """Test finding alert config with invalid valid_on type."""
        async def run_test():
            result = await self.client.find_alert_config(id="alert-123", valid_on="invalid")
            self.assertIn("error", result)
            self.assertIn("must be an integer", result["error"])

        asyncio.run(run_test())

    def test_find_alert_config_versions_invalid_id(self):
        """Test finding alert config versions with invalid ID."""
        async def run_test():
            result = await self.client.find_alert_config_versions(id=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_find_alert_config_versions_api_error(self):
        """Test finding alert config versions with API error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.data = b"Internal server error"

            self.mock_api.find_service_levels_alert_config_versions_without_preload_content.return_value = mock_response

            result = await self.client.find_alert_config_versions(id="alert-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_create_alert_config_empty_payload(self):
        """Test creating alert config with empty payload."""
        async def run_test():
            result = await self.client.create_alert_config(payload=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_create_alert_config_invalid_json_string(self):
        """Test creating alert config with invalid JSON string."""
        async def run_test():
            result = await self.client.create_alert_config(payload="{invalid json")
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_alert_config_missing_id(self):
        """Test updating alert config with missing ID."""
        async def run_test():
            payload = {"name": "Updated Alert"}
            result = await self.client.update_alert_config(id=None, payload=payload)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_alert_config_empty_payload(self):
        """Test updating alert config with empty payload."""
        async def run_test():
            result = await self.client.update_alert_config(id="alert-123", payload=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_disable_alert_config_invalid_id(self):
        """Test disabling alert config with invalid ID."""
        async def run_test():
            result = await self.client.disable_alert_config(id=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_enable_alert_config_invalid_id(self):
        """Test enabling alert config with invalid ID."""
        async def run_test():
            result = await self.client.enable_alert_config(id=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_restore_alert_config_invalid_id(self):
        """Test restoring alert config with invalid ID."""
        async def run_test():
            result = await self.client.restore_alert_config(id=None, created=1609459200000)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_restore_alert_config_invalid_created_type(self):
        """Test restoring alert config with invalid created type."""
        async def run_test():
            result = await self.client.restore_alert_config(id="alert-123", created="invalid")
            self.assertIn("error", result)
            self.assertIn("must be an integer", result["error"])

        asyncio.run(run_test())

    def test_restore_alert_config_api_error(self):
        """Test restoring alert config with API error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 404
            mock_response.data = b"Not found"

            self.mock_api.restore_service_levels_alert_config_without_preload_content.return_value = mock_response

            result = await self.client.restore_alert_config(id="alert-123", created=1609459200000)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_find_active_alert_configs_empty_list(self):
        """Test finding active alert configs with empty result."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([]).encode('utf-8')

            self.mock_api.find_active_service_levels_alert_configs_without_preload_content.return_value = mock_response

            result = await self.client.find_active_alert_configs()

            self.assertIn("success", result)
            self.assertEqual(result["count"], 0)

        asyncio.run(run_test())

    def test_find_active_alert_configs_with_alert_ids(self):
        """Test finding active alert configs with alert_ids filter."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([{"id": "alert-1", "name": "Alert 1"}]).encode('utf-8')

            self.mock_api.find_active_service_levels_alert_configs_without_preload_content.return_value = mock_response

            result = await self.client.find_active_alert_configs(alert_ids=["alert-1"])

            self.assertIn("success", result)
            self.assertEqual(len(result["configs"]), 1)

        asyncio.run(run_test())

    def test_find_alert_config_api_error(self):
        """Test finding alert config with API error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.data = b"Internal server error"

            self.mock_api.find_service_levels_alert_config_without_preload_content.return_value = mock_response

            result = await self.client.find_alert_config(id="alert-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_clean_alert_config_data_with_all_fields(self):
        """Test cleaning alert config data with all fields present."""
        config = {
            "id": "alert-123",
            "name": "Test Alert",
            "description": "Test description",
            "sloIds": ["slo-1", "slo-2"],
            "rule": {"alertType": "ERROR_BUDGET"},
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000},
            "threshold": {"value": 0.95},
            "burnRateConfig": {"factor": 2},
            "customPayloadFields": [{"key": "env", "value": "prod"}],
            "triggering": True,
            "extraField": "should be removed"
        }
        cleaned = self.client._clean_alert_config_data(config)
        self.assertIn("id", cleaned)
        self.assertIn("threshold", cleaned)
        self.assertIn("burnRateConfig", cleaned)
        self.assertIn("triggering", cleaned)
        self.assertNotIn("extraField", cleaned)


    def test_build_alert_config_object_error_budget_success(self):
        """Test building alert config object with ERROR_BUDGET rule"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }

        result = self.client._build_alert_config_object(request_body)

        # Should return a mock object (not an error dict)
        self.assertNotIsInstance(result, dict) or self.assertNotIn("error", result)

    def test_build_alert_config_object_service_level_objective_success(self):
        """Test building alert config object with SERVICE_LEVELS_OBJECTIVE rule"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "SERVICE_LEVELS_OBJECTIVE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }

        result = self.client._build_alert_config_object(request_body)

        # Should return a mock object (not an error dict)
        self.assertNotIsInstance(result, dict) or self.assertNotIn("error", result)

    def test_build_alert_config_object_missing_metric_for_error_budget(self):
        """Test building alert config object with ERROR_BUDGET but missing metric"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }

        result = self.client._build_alert_config_object(request_body)

        self.assertIn("error", result)
        self.assertIn("rule.metric is required", result["error"])

    def test_build_alert_config_object_missing_burn_rate_time_windows(self):
        """Test building alert config object with BURN_RATE but missing burnRateTimeWindows"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }

        result = self.client._build_alert_config_object(request_body)

        self.assertIn("error", result)
        self.assertIn("burnRateTimeWindows is required", result["error"])

    def test_build_alert_config_object_invalid_alert_type(self):
        """Test building alert config object with invalid alertType"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "INVALID_TYPE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }

        result = self.client._build_alert_config_object(request_body)

        self.assertIn("error", result)
        self.assertIn("Invalid alertType", result["error"])

    def test_build_alert_config_object_missing_time_threshold_fields(self):
        """Test building alert config object with incomplete timeThreshold"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
            "timeThreshold": {"expiry": 604800000}  # Missing timeWindow
        }

        result = self.client._build_alert_config_object(request_body)

        self.assertIn("error", result)
        self.assertIn("timeThreshold must include both", result["error"])

    def test_build_alert_config_object_with_threshold(self):
        """Test building alert config object with threshold"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000},
            "threshold": {"value": 0.95, "operator": ">="}
        }

        result = self.client._build_alert_config_object(request_body)

        # Should succeed
        self.assertNotIsInstance(result, dict) or self.assertNotIn("error", result)

    def test_build_alert_config_object_with_burn_rate_config(self):
        """Test building alert config object with burnRateConfig"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000},
            "burnRateTimeWindows": {
                "longTimeWindow": {"duration": 1, "durationType": "hour"},
                "shortTimeWindow": {"duration": 5, "durationType": "minute"}
            },
            "burnRateConfig": {"factor": 2}
        }

        result = self.client._build_alert_config_object(request_body)

        # Should succeed
        self.assertNotIsInstance(result, dict) or self.assertNotIn("error", result)

    def test_build_alert_config_object_with_triggering(self):
        """Test building alert config object with triggering field"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000},
            "triggering": True
        }

        result = self.client._build_alert_config_object(request_body)

        # Should succeed
        self.assertNotIsInstance(result, dict) or self.assertNotIn("error", result)

    def test_build_alert_config_object_with_static_string_custom_payload(self):
        """Test building alert config object with staticString custom payload fields"""
        request_body = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [
                {"type": "staticString", "key": "environment", "value": "production"}
            ],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }

        result = self.client._build_alert_config_object(request_body)

        # Should succeed
        self.assertNotIsInstance(result, dict) or self.assertNotIn("error", result)


    def test_create_alert_config_success(self):
        """Test creating alert config successfully"""
        async def run_test():
            payload = {
                "name": "Test Alert",
                "description": "Test",
                "sloIds": ["slo-1"],
                "severity": 10,
                "alertChannelIds": ["ch-1"],
                "customPayloadFields": [],
                "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
                "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
            }

            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.data = json.dumps({"id": "alert-123", "name": "Test Alert"}).encode('utf-8')

            self.mock_api.create_service_levels_alert_config_without_preload_content.return_value = mock_response

            result = await self.client.create_alert_config(payload=payload)

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertIn("data", result)

        asyncio.run(run_test())

    def test_create_alert_config_api_error(self):
        """Test creating alert config with API error"""
        async def run_test():
            payload = {
                "name": "Test Alert",
                "description": "Test",
                "sloIds": ["slo-1"],
                "severity": 10,
                "alertChannelIds": ["ch-1"],
                "customPayloadFields": [],
                "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
                "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
            }

            mock_response = MagicMock()
            mock_response.status = 400
            mock_response.data = b"Bad request"

            self.mock_api.create_service_levels_alert_config_without_preload_content.return_value = mock_response

            result = await self.client.create_alert_config(payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_create_alert_config_build_object_error(self):
        """Test creating alert config when building object fails"""
        async def run_test():
            payload = {
                "name": "Test Alert",
                "description": "Test",
                "sloIds": ["slo-1"],
                "severity": 10,
                "alertChannelIds": ["ch-1"],
                "customPayloadFields": [],
                "rule": {"alertType": "INVALID_TYPE"},
                "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
            }

            result = await self.client.create_alert_config(payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_alert_config_success(self):
        """Test updating alert config successfully"""
        async def run_test():
            payload = {
                "name": "Updated Alert",
                "description": "Updated",
                "sloIds": ["slo-1"],
                "severity": 5,
                "alertChannelIds": ["ch-1"],
                "customPayloadFields": [],
                "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
                "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
            }

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"id": "alert-123", "name": "Updated Alert"}).encode('utf-8')

            self.mock_api.update_service_levels_alert_config_without_preload_content.return_value = mock_response

            result = await self.client.update_alert_config(id="alert-123", payload=payload)

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertIn("updated", result["message"])

        asyncio.run(run_test())

    def test_update_alert_config_api_error(self):
        """Test updating alert config with API error"""
        async def run_test():
            payload = {
                "name": "Updated Alert",
                "description": "Updated",
                "sloIds": ["slo-1"],
                "severity": 10,
                "alertChannelIds": ["ch-1"],
                "customPayloadFields": [],
                "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
                "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
            }

            mock_response = MagicMock()
            mock_response.status = 404
            mock_response.data = b"Not found"

            self.mock_api.update_service_levels_alert_config_without_preload_content.return_value = mock_response

            result = await self.client.update_alert_config(id="alert-123", payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_alert_config_validation_message_updated(self):
        """Test that update validation message is customized"""
        async def run_test():
            payload = {"name": "Test"}  # Missing required fields

            result = await self.client.update_alert_config(id="alert-123", payload=payload)

            self.assertIn("elicitation_needed", result)
            self.assertIn("To update the SLO alert configuration", result["message"])

        asyncio.run(run_test())

    def test_exception_handling_in_create(self):
        """Test exception handling in create_alert_config"""
        async def run_test():
            self.mock_api.create_service_levels_alert_config_without_preload_content.side_effect = Exception("Test error")

            payload = {
                "name": "Test Alert",
                "description": "Test",
                "sloIds": ["slo-1"],
                "severity": 10,
                "alertChannelIds": ["ch-1"],
                "customPayloadFields": [],
                "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
                "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
            }

            result = await self.client.create_alert_config(payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_exception_handling_in_update(self):
        """Test exception handling in update_alert_config"""
        async def run_test():
            self.mock_api.update_service_levels_alert_config_without_preload_content.side_effect = Exception("Test error")

            payload = {
                "name": "Test Alert",
                "description": "Test",
                "sloIds": ["slo-1"],
                "severity": 10,
                "alertChannelIds": ["ch-1"],
                "customPayloadFields": [],
                "rule": {"alertType": "ERROR_BUDGET", "metric": "BURNED_PERCENTAGE"},
                "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
            }

            result = await self.client.update_alert_config(id="alert-123", payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_exception_handling_in_find_versions(self):
        """Test exception handling in find_alert_config_versions"""
        async def run_test():
            self.mock_api.find_service_levels_alert_config_versions_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.find_alert_config_versions(id="alert-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_find_active_alert_configs_non_list_response(self):
        """Test finding active alert configs with non-list response"""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"error": "unexpected format"}).encode('utf-8')

            self.mock_api.find_active_service_levels_alert_configs_without_preload_content.return_value = mock_response

            result = await self.client.find_active_alert_configs()

            self.assertIn("success", result)
            self.assertEqual(result["count"], 0)

        asyncio.run(run_test())

    def test_validate_alert_config_payload_with_burn_rate_v2_metric(self):
        """Test alert config validation with BURN_RATE_V2 metric (no burnRateTimeWindows required)"""
        payload = {
            "name": "Test Alert",
            "description": "Test",
            "sloIds": ["slo-1"],
            "severity": 10,
            "alertChannelIds": ["ch-1"],
            "customPayloadFields": [],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE_V2"},
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}
        }
        result = self.client._validate_alert_config_payload(payload)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

