"""
Unit tests for the MobileAppSessionReplayMCPTools class
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

app_logger = logging.getLogger("src.mobile_app.mobile_app_session_replay")
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

sys.modules["instana_client"] = MagicMock()
sys.modules["instana_client.api"] = MagicMock()
sys.modules["instana_client.api.mobile_app_catalog_api"] = MagicMock()
sys.modules["instana_client.models"] = MagicMock()
sys.modules["instana_client.models.get_action_beacons_result"] = MagicMock()
sys.modules["instana_client.configuration"] = MagicMock()
sys.modules["instana_client.api_client"] = MagicMock()


class FakeModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def to_dict(self):
        return self.kwargs

sys.modules["instana_client.api.mobile_app_catalog_api"].MobileAppCatalogApi = MagicMock()

from src.mobile_app.mobile_app_session_replay import (
    MobileAppSessionReplayMCPTools,
    clean_nan_values,
)


class MockResponse:
    def __init__(self, payload, headers=None, status=200):
        self.data = payload
        self.headers = headers or {}
        self.status = status

class TestMobileAppSessionReplayMCPTools(unittest.IsolatedAsyncioTestCase):
    """Test MobileAppSessionReplayMCPTools"""

    def setUp(self):
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = MobileAppSessionReplayMCPTools(read_token=self.read_token, base_url=self.base_url)
        self.mock_api = MagicMock()

    def test_clean_nan_values(self):
        input_data = {
            "a": "NaN",
            "b": [1, "NaN", 3],
            "c": {"x": "NaN", "y": 5},
        }
        result = clean_nan_values(input_data)
        self.assertEqual(result["a"], None)
        self.assertEqual(result["b"], [1, None, 3])
        self.assertEqual(result["c"]["x"], None)

    async def test_elicitate_missing_mobile_app_id(self):
        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id=None,
            session_id="test-session-id",
            cursor=None,
            page_size=None,
            api_client=self.mock_api
        )
        self.assertTrue(result.get("elicitation_needed"))

    async def test_elicitate_missing_session_id(self):
        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-mobile-app-id",
            session_id=None,
            cursor=None,
            page_size=None,
            api_client=self.mock_api
        )
        self.assertTrue(result.get("elicitation_needed"))

    async def test_both_required_params_missing(self):
        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id=None,
            session_id=None,
            api_client=self.mock_api
        )

        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(len(result["missing_parameters"]), 2)

    async def test_validate_cursor(self):
        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-mobile-app-id",
            session_id="test-session-id",
            cursor=-1,
            page_size=None,
            api_client=self.mock_api
        )
        self.assertTrue(result.get("validation_failed"))

    async def test_validate_page_size(self):
        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-mobile-app-id",
            session_id="test-session-id",
            cursor=None,
            page_size=0,
            api_client=self.mock_api
        )
        self.assertTrue(result.get("validation_failed"))

        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-mobile-app-id",
            session_id="test-session-id",
            cursor=None,
            page_size=1001,
            api_client=self.mock_api
        )
        self.assertTrue(result.get("validation_failed"))

    async def test_multiple_validation_errors(self):
        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-app",
            session_id="test-session",
            cursor=-1,
            page_size=2000,
            api_client=self.mock_api
        )

        self.assertTrue(result.get("validation_failed"))
        self.assertEqual(len(result["errors"]), 2)

    async def test_pagination_parameters_optional(self):
        # Mock a successful response
        self.mock_api.get_action_beacons_without_preload_content.return_value = MockResponse(
            json.dumps({"beacons": [], "hasMore": False}).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-mobile-app-id",
            session_id="test-session-id",
            cursor=None,
            page_size=None,
            api_client=self.mock_api
        )
        self.assertFalse(result.get("validation_failed"))
        self.assertIn("beacons", result)

    async def test_cursor_default(self):
        self.mock_api.get_action_beacons_without_preload_content.return_value = MockResponse(
            json.dumps({"beacons": [], "hasMore": False}).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-mobile-app-id",
            session_id="test-session-id",
            cursor=None,
            page_size=None,
            api_client=self.mock_api,
        )

        self.mock_api.get_action_beacons_without_preload_content.assert_called_once()

        call_args = self.mock_api.get_action_beacons_without_preload_content.call_args
        self.assertEqual(call_args.kwargs['cursor'], 0)

    async def test_paramter_values_passed(self):
        self.mock_api.get_action_beacons_without_preload_content.return_value = MockResponse(
            json.dumps({"beacons": [], "hasMore": False}).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-mobile-app-id",
            session_id="test-session-id",
            cursor=10,
            page_size=50,
            api_client=self.mock_api,
        )

        self.mock_api.get_action_beacons_without_preload_content.assert_called_once()

        call_args = self.mock_api.get_action_beacons_without_preload_content.call_args
        self.assertEqual(call_args.kwargs['mobile_app_id'], 'test-mobile-app-id')
        self.assertEqual(call_args.kwargs['session_id'], 'test-session-id')
        self.assertEqual(call_args.kwargs['cursor'], 10)
        self.assertEqual(call_args.kwargs['page_size'], 50)

    async def test_get_mobile_app_action_beacons_success(self):
        payload = {
            "beacons": [],
            "hasMore": True,
            "nextCursor": 10
        }
        self.mock_api.get_action_beacons_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-mobile-app-id",
            session_id="test-session-id",
            cursor=None,
            page_size=None,
            api_client=self.mock_api
        )

        self.assertIn("beacons", result)
        self.assertIsInstance(result["beacons"], list)
        self.assertEqual(len(result["beacons"]), 0)

        self.assertEqual(result["hasMore"], True)
        self.assertIsInstance(result["hasMore"], bool)

        self.assertEqual(result["nextCursor"], 10)
        self.assertIsInstance(result["nextCursor"], int)

    async def test_action_beacons_non_200_response(self):
        self.mock_api.get_action_beacons_without_preload_content.return_value = MockResponse(
            b'{"errors": ["Metric type unknown"]}',
            {"Content-Type": "application/json"},
        )
        self.mock_api.get_action_beacons_without_preload_content.return_value.status = 400

        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-mobile-app-id",
            session_id="test-session-id",
            cursor=None,
            page_size=None,
            api_client=self.mock_api
        )

        self.assertTrue(result.get("error"))
        self.assertEqual(result["status_code"], 400)

    async def test_invalid_json_response(self):
        self.mock_api.get_action_beacons_without_preload_content.return_value = MockResponse(
            b'{"invalid json',  # Malformed JSON
            status=200
        )

        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-app",
            session_id="test-session",
            api_client=self.mock_api
        )

        self.assertIn("error", result)

    async def test_api_exception(self):
        self.mock_api.get_action_beacons_without_preload_content.side_effect = Exception("API connection failed")

        result = await self.client.get_session_replay_action_beacons(
            mobile_app_id="test-app",
            session_id="test-session",
            api_client=self.mock_api
        )

        self.assertIn("error", result)
        self.assertIn("API connection failed", result["error"])


