"""
Unit tests for the MobileAppSessionMCPTools class (session lifecycle — get_session_beacons)
"""

import json
import logging
import os
import sys
import unittest
from unittest.mock import MagicMock


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


logging.basicConfig(level=logging.ERROR)

app_logger = logging.getLogger("src.mobile_app.mobile_app_session")
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

sys.modules["instana_client"] = MagicMock()
sys.modules["instana_client.api"] = MagicMock()
sys.modules["instana_client.api.mobile_app_session_replay_api"] = MagicMock()
sys.modules["instana_client.api.mobile_app_metrics_api"] = MagicMock()
sys.modules["instana_client.models"] = MagicMock()
sys.modules["instana_client.configuration"] = MagicMock()
sys.modules["instana_client.api_client"] = MagicMock()

sys.modules["instana_client.api.mobile_app_session_replay_api"].MobileAppSessionReplayApi = MagicMock()
sys.modules["instana_client.api.mobile_app_metrics_api"].MobileAppMetricsApi = MagicMock()

from src.mobile_app.mobile_app_session import MobileAppSessionMCPTools


class MockResponse:
    def __init__(self, payload, headers=None, status=200):
        self.data = payload
        self.headers = headers or {}
        self.status = status


class TestGetSessionBeacons(unittest.IsolatedAsyncioTestCase):
    """Tests for MobileAppSessionMCPTools.get_session_beacons"""

    def setUp(self):
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = MobileAppSessionMCPTools(read_token=self.read_token, base_url=self.base_url)
        self.mock_api = MagicMock()

    # ── elicitation ────────────────────────────────────────────────────────────

    async def test_elicitate_missing_session_id(self):
        result = await self.client.get_session_beacons(
            session_id=None,
            timestamp=1785786779333,
            api_client=self.mock_api
        )
        self.assertTrue(result.get("elicitation_needed"))
        params = [p["name"] for p in result["missing_parameters"]]
        self.assertIn("session_id", params)

    async def test_elicitate_missing_timestamp(self):
        result = await self.client.get_session_beacons(
            session_id="29b14605-9ee5-47fd-91bc-f269ac2c6ced",
            timestamp=None,
            api_client=self.mock_api
        )
        self.assertTrue(result.get("elicitation_needed"))
        params = [p["name"] for p in result["missing_parameters"]]
        self.assertIn("timestamp", params)

    async def test_elicitate_both_required_params_missing(self):
        result = await self.client.get_session_beacons(
            session_id=None,
            timestamp=None,
            api_client=self.mock_api
        )
        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(len(result["missing_parameters"]), 2)

    # ── success ────────────────────────────────────────────────────────────────

    async def test_success_returns_dict_with_beacons(self):
        """API returns a bare JSON array — result should be wrapped as {"beacons": [...]}."""
        payload = [
            {"sessionId": "29b14605-9ee5-47fd-91bc-f269ac2c6ced", "type": "sessionStart", "timestamp": 1785786779332},
            {"sessionId": "29b14605-9ee5-47fd-91bc-f269ac2c6ced", "type": "viewChange", "timestamp": 1785786780000},
        ]
        self.mock_api.get_session_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        result = await self.client.get_session_beacons(
            session_id="29b14605-9ee5-47fd-91bc-f269ac2c6ced",
            timestamp=1785786779333,
            api_client=self.mock_api
        )
        self.assertIsInstance(result, dict)
        self.assertIn("beacons", result)
        self.assertEqual(len(result["beacons"]), 2)
        self.assertEqual(result["beacons"][0]["type"], "sessionStart")

    async def test_correct_sdk_params_passed(self):
        """Verifies id= (not session_id=) is forwarded to the SDK method."""
        payload = [{"sessionId": "test-session", "type": "sessionStart"}]
        self.mock_api.get_session_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        await self.client.get_session_beacons(
            session_id="test-session",
            timestamp=1785786779333,
            api_client=self.mock_api
        )
        self.mock_api.get_session_without_preload_content.assert_called_once()
        call_kwargs = self.mock_api.get_session_without_preload_content.call_args.kwargs
        self.assertEqual(call_kwargs["id"], "test-session")
        self.assertEqual(call_kwargs["timestamp"], 1785786779333)

    async def test_nan_values_cleaned(self):
        payload = [{"sessionId": "s1", "latitude": "NaN", "longitude": -84.77}]
        self.mock_api.get_session_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        result = await self.client.get_session_beacons(
            session_id="s1",
            timestamp=1785786779333,
            api_client=self.mock_api
        )
        self.assertIsNone(result["beacons"][0]["latitude"])
        self.assertEqual(result["beacons"][0]["longitude"], -84.77)

    async def test_empty_list_response(self):
        """Empty list is valid — no error should be raised."""
        self.mock_api.get_session_without_preload_content.return_value = MockResponse(
            b"[]",
            {"Content-Type": "application/json"},
        )
        result = await self.client.get_session_beacons(
            session_id="test-session",
            timestamp=1785786779333,
            api_client=self.mock_api
        )
        self.assertIsInstance(result, dict)
        self.assertIn("beacons", result)
        self.assertEqual(len(result["beacons"]), 0)

    # ── error handling ─────────────────────────────────────────────────────────

    async def test_non_200_response(self):
        self.mock_api.get_session_without_preload_content.return_value = MockResponse(
            b'{"errors": ["Missing session id"]}',
            {"Content-Type": "application/json"},
            status=400,
        )
        result = await self.client.get_session_beacons(
            session_id="bad-session",
            timestamp=1785786779333,
            api_client=self.mock_api
        )
        self.assertIn("error", result)
        self.assertEqual(result["status_code"], 400)

    async def test_invalid_json_response(self):
        self.mock_api.get_session_without_preload_content.return_value = MockResponse(
            b'{"invalid json',
            status=200
        )
        result = await self.client.get_session_beacons(
            session_id="test-session",
            timestamp=1785786779333,
            api_client=self.mock_api
        )
        self.assertIn("error", result)

    async def test_api_exception(self):
        self.mock_api.get_session_without_preload_content.side_effect = Exception("connection refused")
        result = await self.client.get_session_beacons(
            session_id="test-session",
            timestamp=1785786779333,
            api_client=self.mock_api
        )
        self.assertIn("error", result)
        self.assertIn("connection refused", result["error"])

    async def test_outer_exception_handler(self):
        """Covers the outer except in get_session_beacons."""
        self.client._execute_beacons_call = MagicMock(side_effect=Exception("unexpected outer error"))

        result = await self.client.get_session_beacons(
            session_id="test-session",
            timestamp=1785786779333,
            api_client=self.mock_api
        )

        self.assertIn("error", result)
        self.assertIn("unexpected outer error", result["error"])

    async def test_zero_timestamp_is_valid(self):
        """timestamp=0 is a valid epoch value and must NOT trigger elicitation."""
        payload = [{"sessionId": "s1", "type": "sessionStart"}]
        self.mock_api.get_session_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        result = await self.client.get_session_beacons(
            session_id="s1",
            timestamp=0,
            api_client=self.mock_api
        )
        self.assertNotIn("elicitation_needed", result)
        self.assertIn("beacons", result)
        self.assertEqual(len(result["beacons"]), 1)


if __name__ == "__main__":
    unittest.main()
