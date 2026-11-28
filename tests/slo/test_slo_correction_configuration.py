"""
Unit tests for SLO Correction Configuration MCP Tools.

Tests the SLOCorrectionMCPTools which manages SLO correction window configurations.
"""

import asyncio
import json
import logging
import os
import sys
import unittest
from datetime import datetime, timezone
from functools import wraps
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level
logging.basicConfig(level=logging.ERROR)

# Get the SLO logger and replace its handlers
slo_logger = logging.getLogger('src.slo.slo_correction_configuration')
slo_logger.handlers = []
slo_logger.addHandler(NullHandler())
slo_logger.propagate = False

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            for attr_name in ("correction_api", "slo_config_api", "alert_config_api", "report_api"):
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
sys.modules['instana_client.api.slo_correction_configurations_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.correction_configuration'] = MagicMock()
sys.modules['instana_client.models.correction_scheduling'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client_class = MagicMock()
mock_correction_api = MagicMock()

mock_correction_api.__name__ = "SLOCorrectionConfigurationsApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client_class
sys.modules['instana_client.api.slo_correction_configurations_api'].SLOCorrectionConfigurationsApi = mock_correction_api

# Import with patched decorator
import src.core.utils

original_with_header_auth = src.core.utils.with_header_auth
src.core.utils.with_header_auth = mock_with_header_auth

from src.slo.slo_correction_configuration import SLOCorrectionMCPTools

# Restore original decorator
src.core.utils.with_header_auth = original_with_header_auth


class TestSLOCorrectionMCPTools(unittest.TestCase):
    """Test cases for SLO Correction Configuration MCP Tools."""

    def setUp(self):
        """Set up test fixtures."""
        mock_configuration.reset_mock()
        mock_api_client_class.reset_mock()
        mock_correction_api.reset_mock()

        self.client = SLOCorrectionMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com"
        )

        self.mock_api = MagicMock()
        self.client.correction_api = self.mock_api

    def test_initialization(self):
        """Test client initialization."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.com")

    # Validation Tests
    def test_validate_correction_payload_missing_name(self):
        """Test correction validation with missing name."""
        payload = {
            "sloIds": ["slo-1"],
            "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("elicitation_needed", result)
        self.assertIn("name", result["missing_parameters"])

    def test_validate_correction_payload_missing_slo_ids(self):
        """Test correction validation with missing sloIds."""
        payload = {
            "name": "Test Correction",
            "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("sloIds", result["missing_parameters"])

    def test_validate_correction_payload_missing_scheduling(self):
        """Test correction validation with missing scheduling."""
        payload = {
            "name": "Test Correction",
            "sloIds": ["slo-1"]
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("scheduling", result["missing_parameters"])

    def test_validate_correction_payload_missing_scheduling_duration(self):
        """Test correction validation with missing scheduling.duration."""
        payload = {
            "name": "Test Correction",
            "sloIds": ["slo-1"],
            "scheduling": {"durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("scheduling.duration", result["missing_parameters"])

    def test_validate_correction_payload_missing_scheduling_duration_unit(self):
        """Test correction validation with missing scheduling.durationUnit."""
        payload = {
            "name": "Test Correction",
            "sloIds": ["slo-1"],
            "scheduling": {"duration": 2, "startTime": "2026-03-10 14:00:00|IST"}
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("scheduling.durationUnit", result["missing_parameters"])

    def test_validate_correction_payload_valid(self):
        """Test correction validation with valid payload."""
        payload = {
            "name": "Test Correction",
            "sloIds": ["slo-1"],
            "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNone(result)

    def test_clean_correction_data(self):
        """Test cleaning correction data."""
        correction = {
            "id": "corr-123",
            "name": "Test Correction",
            "description": "Test",
            "sloIds": ["slo-1"],
            "scheduling": {"duration": 2},
            "tags": ["test"],
            "createdDate": 1609459200000,
            "lastUpdated": 1612137600000,
            "extraField": "should be removed"
        }
        cleaned = self.client._clean_correction_data(correction)
        self.assertIn("id", cleaned)
        self.assertIn("name", cleaned)
        self.assertIn("createdDate", cleaned)
        self.assertNotIn("extraField", cleaned)

    # get_all_corrections Tests
    def test_get_all_corrections_success(self):
        """Test getting all corrections successfully."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({
                "items": [
                    {"id": "corr-1", "name": "Correction 1"},
                    {"id": "corr-2", "name": "Correction 2"}
                ]
            }).encode('utf-8')

            self.mock_api.get_all_slo_correction_window_configs_without_preload_content.return_value = mock_response

            result = await self.client.get_all_corrections()

            self.assertIn("items", result)
            self.assertEqual(len(result["items"]), 2)

        asyncio.run(run_test())

    def test_get_all_corrections_with_filters(self):
        """Test getting all corrections with filters."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({
                "items": [{"id": "corr-1", "name": "Correction 1"}]
            }).encode('utf-8')

            self.mock_api.get_all_slo_correction_window_configs_without_preload_content.return_value = mock_response

            result = await self.client.get_all_corrections(
                page_size=10,
                page=1,
                query="test",
                tag=["maintenance"]
            )

            self.assertIn("items", result)

        asyncio.run(run_test())

    def test_get_all_corrections_api_error(self):
        """Test getting all corrections with API error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.data = b"Internal server error"

            self.mock_api.get_all_slo_correction_window_configs_without_preload_content.return_value = mock_response

            result = await self.client.get_all_corrections()

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_get_all_corrections_exception(self):
        """Test getting all corrections with exception."""
        async def run_test():
            self.mock_api.get_all_slo_correction_window_configs_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.get_all_corrections()

            self.assertIn("error", result)

        asyncio.run(run_test())

    # get_correction_by_id Tests
    def test_get_correction_by_id_success(self):
        """Test getting correction by ID successfully."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"id": "corr-123", "name": "Test Correction"}).encode('utf-8')

            self.mock_api.get_slo_correction_window_config_by_id_without_preload_content.return_value = mock_response

            result = await self.client.get_correction_by_id(id="corr-123")

            self.assertIn("id", result)
            self.assertEqual(result["id"], "corr-123")

        asyncio.run(run_test())

    def test_get_correction_by_id_missing_id(self):
        """Test getting correction by ID with missing ID."""
        async def run_test():
            result = await self.client.get_correction_by_id(id=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_get_correction_by_id_api_error(self):
        """Test getting correction by ID with API error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 404
            mock_response.data = b"Not found"

            self.mock_api.get_slo_correction_window_config_by_id_without_preload_content.return_value = mock_response

            result = await self.client.get_correction_by_id(id="corr-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_get_correction_by_id_exception(self):
        """Test getting correction by ID with exception."""
        async def run_test():
            self.mock_api.get_slo_correction_window_config_by_id_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.get_correction_by_id(id="corr-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    # create_correction Tests
    def test_create_correction_missing_payload(self):
        """Test creating correction with missing payload."""
        async def run_test():
            result = await self.client.create_correction(payload=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_create_correction_json_string(self):
        """Test creating correction with JSON string payload."""
        async def run_test():
            payload = json.dumps({
                "name": "Test Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
            })

            result = await self.client.create_correction(payload=payload)

            self.assertTrue("error" in result or "elicitation_needed" in result or "success" in result)

        asyncio.run(run_test())

    def test_create_correction_python_literal_string(self):
        """Test creating correction with Python literal string payload."""
        async def run_test():
            payload = "{'name': 'Test Correction', 'sloIds': ['slo-1']}"

            result = await self.client.create_correction(payload=payload)

            self.assertTrue("error" in result or "elicitation_needed" in result)

        asyncio.run(run_test())

    def test_create_correction_missing_fields(self):
        """Test creating correction with missing required fields."""
        async def run_test():
            payload = {"name": "Test Correction"}

            result = await self.client.create_correction(payload=payload)

            self.assertIn("elicitation_needed", result)
            self.assertIn("missing_parameters", result)

        asyncio.run(run_test())

    def test_create_correction_invalid_duration_unit(self):
        """Invalid durationUnit is now caught by the validator before hitting the API."""
        async def run_test():
            payload = {
                "name": "Test Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "invalid", "startTime": "2026-03-10 14:00:00|IST"}
            }

            result = await self.client.create_correction(payload=payload)

            # Validator returns elicitation_needed with the invalid field listed
            self.assertIn("elicitation_needed", result)
            self.assertIn("scheduling.durationUnit", result["missing_parameters"])

        asyncio.run(run_test())

    def test_create_correction_with_millisecond_timestamp(self):
        """Test creating correction with millisecond timestamp for startTime."""
        async def run_test():
            payload = {
                "name": "Test Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": 1609459200000}
            }

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"id": "corr-123", "name": "Test Correction"}).encode('utf-8')

            self.mock_api.create_slo_correction_window_config_without_preload_content.return_value = mock_response

            result = await self.client.create_correction(payload=payload)

            self.assertTrue("success" in result or "error" in result)

        asyncio.run(run_test())

    def test_create_correction_api_error(self):
        """Test creating correction with API error."""
        async def run_test():
            payload = {
                "name": "Test Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
            }

            mock_response = MagicMock()
            mock_response.status = 400
            mock_response.data = b"Bad request"

            self.mock_api.create_slo_correction_window_config_without_preload_content.return_value = mock_response

            result = await self.client.create_correction(payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_create_correction_exception(self):
        """Test creating correction with exception."""
        async def run_test():
            payload = {
                "name": "Test Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
            }

            self.mock_api.create_slo_correction_window_config_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.create_correction(payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    # update_correction Tests
    def test_update_correction_missing_id(self):
        """Test updating correction with missing ID."""
        async def run_test():
            payload = {"name": "Updated Correction"}
            result = await self.client.update_correction(id=None, payload=payload)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_correction_missing_payload(self):
        """Test updating correction with missing payload."""
        async def run_test():
            result = await self.client.update_correction(id="corr-123", payload=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_correction_missing_fields(self):
        """Test updating correction with missing required fields."""
        async def run_test():
            payload = {"name": "Updated Correction"}

            result = await self.client.update_correction(id="corr-123", payload=payload)

            self.assertIn("elicitation_needed", result)

        asyncio.run(run_test())

    def test_update_correction_json_string(self):
        """Test updating correction with JSON string payload."""
        async def run_test():
            payload = json.dumps({
                "name": "Updated Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
            })

            result = await self.client.update_correction(id="corr-123", payload=payload)

            self.assertTrue("error" in result or "elicitation_needed" in result or "success" in result)

        asyncio.run(run_test())

    def test_update_correction_with_millisecond_timestamp(self):
        """Test updating correction with millisecond timestamp for startTime."""
        async def run_test():
            payload = {
                "name": "Updated Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": 1609459200000}
            }

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"id": "corr-123", "name": "Updated Correction"}).encode('utf-8')

            self.mock_api.update_slo_correction_window_config_without_preload_content.return_value = mock_response

            result = await self.client.update_correction(id="corr-123", payload=payload)

            self.assertTrue("success" in result or "error" in result)

        asyncio.run(run_test())

    def test_update_correction_api_error(self):
        """Test updating correction with API error."""
        async def run_test():
            payload = {
                "name": "Updated Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
            }

            mock_response = MagicMock()
            mock_response.status = 404
            mock_response.data = b"Not found"

            self.mock_api.update_slo_correction_window_config_without_preload_content.return_value = mock_response

            result = await self.client.update_correction(id="corr-123", payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_correction_exception(self):
        """Test updating correction with exception."""
        async def run_test():
            payload = {
                "name": "Updated Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "2026-03-10 14:00:00|IST"}
            }

            self.mock_api.update_slo_correction_window_config_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.update_correction(id="corr-123", payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    # delete_correction Tests
    def test_delete_correction_success(self):
        """Test deleting correction successfully."""
        async def run_test():
            self.mock_api.delete_slo_correction_window_config.return_value = None

            result = await self.client.delete_correction(id="corr-123")

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertIn("deleted", result["message"])

        asyncio.run(run_test())

    def test_delete_correction_missing_id(self):
        """Test deleting correction with missing ID."""
        async def run_test():
            result = await self.client.delete_correction(id=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_delete_correction_exception(self):
        """Test deleting correction with exception."""
        async def run_test():
            self.mock_api.delete_slo_correction_window_config.side_effect = Exception("Test error")

            result = await self.client.delete_correction(id="corr-123")

            self.assertIn("error", result)

        asyncio.run(run_test())


    # ── New validation tests for enum / range checks ──────────────────────

    def test_validate_correction_payload_invalid_duration_unit(self):
        """scheduling.durationUnit with a bad value should be rejected by the validator."""
        payload = {
            "name": "Test Correction",
            "sloIds": ["slo-1"],
            "scheduling": {"duration": 2, "durationUnit": "month"}
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("scheduling.durationUnit", result["missing_parameters"])
        detail = next(p for p in result["parameter_details"] if p["name"] == "scheduling.durationUnit")
        self.assertIn("error", detail)

    def test_validate_correction_payload_calendar_month_is_valid(self):
        """calendar_month is the correct SDK value for monthly corrections."""
        payload = {
            "name": "Test Correction",
            "sloIds": ["slo-1"],
            "scheduling": {"duration": 1, "durationUnit": "calendar_month"}
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNone(result)

    def test_validate_correction_payload_non_positive_duration(self):
        """scheduling.duration <= 0 should be rejected."""
        payload = {
            "name": "Test Correction",
            "sloIds": ["slo-1"],
            "scheduling": {"duration": 0, "durationUnit": "hour"}
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("scheduling.duration", result["missing_parameters"])

    def test_validate_correction_payload_consolidated_errors(self):
        """Multiple scheduling errors should all appear in a single elicitation response."""
        payload = {
            "name": "Test Correction",
            "sloIds": ["slo-1"],
            "scheduling": {"duration": -1, "durationUnit": "month"}
        }
        result = self.client._validate_correction_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("scheduling.duration", result["missing_parameters"])
        self.assertIn("scheduling.durationUnit", result["missing_parameters"])

    def test_create_correction_invalid_duration_unit_now_caught_by_validator(self):
        """After the fix, an invalid durationUnit is caught by _validate_correction_payload,
        not the downstream safety-net check, and the response uses elicitation_needed."""
        async def run_test():
            payload = {
                "name": "Test Correction",
                "sloIds": ["slo-1"],
                "scheduling": {"duration": 2, "durationUnit": "month", "startTime": 1609459200000}
            }
            result = await self.client.create_correction(payload=payload)
            # Should return elicitation from the validator (not a bare error string)
            self.assertIn("elicitation_needed", result)
            self.assertIn("scheduling.durationUnit", result["missing_parameters"])

        asyncio.run(run_test())


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
    """sdk_call_with_keepalive returns an error dict on timeout; a delete must not report success."""

    def setUp(self):
        self.client = SLOCorrectionMCPTools(read_token="test_token", base_url="https://test.instana.com")
        self.client.correction_api = MagicMock()
        patcher = patch(
            "src.slo.slo_correction_configuration.sdk_call_with_keepalive",
            side_effect=_timeout_keepalive,
        )
        self.mock_keepalive = patcher.start()
        self.addCleanup(patcher.stop)

    def test_delete_correction_timeout(self):
        result = asyncio.run(self.client.delete_correction(id="corr-123"))

        self.assertIn("timed out", result["error"])
        self.assertEqual(result["timeout_seconds"], 180)
        self.assertNotIn("success", result)
        self.mock_keepalive.assert_called_once()


if __name__ == "__main__":
    unittest.main()

