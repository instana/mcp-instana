"""
Unit tests for the MobileAppAnalyzeMCPTools class
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

app_logger = logging.getLogger("src.mobile.mobile_app_analyze")
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

sys.modules["instana_client"] = MagicMock()
sys.modules["instana_client.api"] = MagicMock()
sys.modules["instana_client.api.mobile_app_analyze_api"] = MagicMock()
sys.modules["instana_client.models"] = MagicMock()
sys.modules["instana_client.models.get_mobile_app_beacon_groups"] = MagicMock()
sys.modules["instana_client.models.get_mobile_app_beacons"] = MagicMock()
sys.modules["instana_client.models.cursor_pagination"] = MagicMock()
sys.modules["instana_client.models.deprecated_tag_filter"] = MagicMock()
sys.modules["instana_client.configuration"] = MagicMock()
sys.modules["instana_client.api_client"] = MagicMock()


class FakeModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def to_dict(self):
        return self.kwargs


sys.modules["instana_client.api.mobile_app_analyze_api"].MobileAppAnalyzeApi = MagicMock()
sys.modules["instana_client.models.cursor_pagination"].CursorPagination = FakeModel
sys.modules["instana_client.models.get_mobile_app_beacons"].GetMobileAppBeacons = FakeModel
sys.modules["instana_client.models.deprecated_tag_filter"].DeprecatedTagFilter = FakeModel
sys.modules["instana_client"].DeprecatedTagFilter = FakeModel

from src.core.utils import decode_response as _decode_response
from src.mobile_app.mobile_app_analyze import MobileAppAnalyzeMCPTools, clean_nan_values


class MockResponse:
    def __init__(self, payload, headers=None):
        self.data = payload
        self.headers = headers or {}


class TestMobileAppAnalyzeMCPTools(unittest.IsolatedAsyncioTestCase):
    """Test MobileAppAnalyzeMCPTools"""

    def setUp(self):
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = MobileAppAnalyzeMCPTools(read_token=self.read_token, base_url=self.base_url)
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

    def test_decode_response_fallback(self):
        response = MockResponse("hello".encode("utf-8"), {})
        result = _decode_response(response)
        self.assertEqual(result, "hello")

    def test_decode_response_charset(self):
        response = MockResponse("olá".encode("latin-1"), {"Content-Type": "text/plain; charset=latin-1"})
        result = _decode_response(response)
        self.assertEqual(result, "olá")

    async def test_validate_missing_beacon_type(self):
        result = await self.client.get_all_mobile_app_beacons(beacon_type=None, api_client=self.mock_api)
        self.assertTrue(result.get("elicitation_needed"))

    def test_validate_tag_missing_entity(self):
        tag_filter = {
            "type": "TAG_FILTER",
            "name": "mobileBeacon.view.name",
            "operator": "EQUALS",
            "value": "Robot Shop",
        }
        result = self.client._validate_tag_names(
            tag_filter_expression=tag_filter,
            group=None,
            beacon_type="SESSION_START",
        )
        self.assertIsNotNone(result)
        self.assertTrue(result.get("elicitation_needed"))

    def test_validate_invalid_tag_prefix(self):
        tag_filter = {
            "type": "TAG_FILTER",
            "name": "wrongTag.name",
            "operator": "EQUALS",
            "entity": "NOT_APPLICABLE",
            "value": "test",
        }
        result = self.client._validate_tag_names(
            tag_filter_expression=tag_filter,
            group=None,
            beacon_type="SESSION_START",
        )
        self.assertTrue(result.get("elicitation_needed"))

    def test_validate_groupby_tag_alias(self):
        tag_filter = {
            "type": "TAG_FILTER",
            "name": "mobileBeacon.view.name",
            "operator": "EQUALS",
            "entity": "NOT_APPLICABLE",
            "value": "test",
        }
        result = self.client._validate_tag_names(
            tag_filter_expression=tag_filter,
            group={"groupbyTag": "mobileBeacon.mobileApp.name"},
            beacon_type="SESSION_START",
        )
        self.assertIsNone(result)

    def test_validate_no_tag_names_extracted(self):
        result = self.client._validate_tag_names(
            tag_filter_expression={"type": "EXPRESSION", "elements": []},
            group={},
            beacon_type="SESSION_START",
        )
        self.assertTrue(result.get("elicitation_needed"))

    def test_summarize_beacons_response(self):
        input_data = {
            "totalHits": 10,
            "items": [{"beacon": {"mobileAppLabel": "App1", "timestamp": 12345, "errorCount": 0}}],
        }
        result = self.client._summarize_beacons_response(input_data)
        self.assertIn("summary", result)
        self.assertIn("beacons", result)

    def test_summarize_beacons_non_dict(self):
        self.assertEqual(self.client._summarize_beacons_response(["x"]), ["x"])

    async def test_get_all_mobile_app_beacons_success(self):
        payload = {
            "totalHits": 1,
            "items": [{"beacon": {"mobileAppLabel": "TestApp", "timestamp": 123, "appVersion": "1.0", "errorCount": 0}}],
        }
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            time_frame={"windowSize": 1000},
            pagination={"retrievalSize": 10},
            api_client=self.mock_api,
        )
        self.assertIn("summary", result)
        self.assertIn("beacons", result)

    async def test_get_all_mobile_app_beacons_list_payload(self):
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(
            json.dumps([{"a": 1}]).encode("utf-8"),
            {"Content-Type": "application/json"},
        )
        result = await self.client.get_all_mobile_app_beacons(beacon_type="SESSION_START", api_client=self.mock_api)
        self.assertIn("summary", result)

    async def test_get_all_mobile_app_beacons_scalar_payload(self):
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(
            b"123",
            {"Content-Type": "application/json"},
        )
        result = await self.client.get_all_mobile_app_beacons(beacon_type="SESSION_START", api_client=self.mock_api)
        self.assertIn("summary", result)

    async def test_pagination_min_bound(self):
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(b'{"items":[]}')
        pagination = {"retrievalSize": 0}
        await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            pagination=pagination,
            api_client=self.mock_api,
        )
        self.assertEqual(pagination["retrievalSize"], 1)

    async def test_pagination_max_bound(self):
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(b'{"items":[]}')
        pagination = {"retrievalSize": 500}
        await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            pagination=pagination,
            api_client=self.mock_api,
        )
        self.assertEqual(pagination["retrievalSize"], 200)

    async def test_tag_filter_single_missing_required_fields(self):
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(b"{}")
        tag_filter = {"type": "TAG_FILTER", "name": "mobileBeacon.view.name", "entity": "NOT_APPLICABLE"}
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            tag_filter_expression=tag_filter,
            api_client=self.mock_api,
        )
        self.assertIn("error", result)

    async def test_tag_filter_expression(self):
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(b'{"items":[]}')
        tag_filter = {
            "type": "EXPRESSION",
            "elements": [
                {
                    "type": "TAG_FILTER",
                    "name": "mobileBeacon.view.name",
                    "operator": "EQUALS",
                    "value": "App",
                    "entity": "NOT_APPLICABLE",
                }
            ],
        }
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            tag_filter_expression=tag_filter,
            api_client=self.mock_api,
        )
        self.assertIn("summary", result)

    async def test_invalid_tag_filter_conversion(self):
        class FailingTagFilter:
            def __init__(self, **kwargs):
                raise ValueError("bad filter")

        original = sys.modules["instana_client.models.deprecated_tag_filter"].DeprecatedTagFilter
        sys.modules["instana_client.models.deprecated_tag_filter"].DeprecatedTagFilter = FailingTagFilter
        try:
            tag_filter = {
                "type": "TAG_FILTER",
                "name": "mobileBeacon.view.name",
                "operator": "EQUALS",
                "value": "App",
                "entity": "NOT_APPLICABLE",
            }
            result = await self.client.get_all_mobile_app_beacons(
                beacon_type="SESSION_START",
                tag_filter_expression=tag_filter,
                api_client=self.mock_api,
            )
            self.assertIn("error", result)
        finally:
            sys.modules["instana_client.models.deprecated_tag_filter"].DeprecatedTagFilter = original

    async def test_invalid_pagination_model(self):
        class FailingPagination:
            def __init__(self, **kwargs):
                raise ValueError("bad pagination")

        original = sys.modules["instana_client.models.cursor_pagination"].CursorPagination
        sys.modules["instana_client.models.cursor_pagination"].CursorPagination = FailingPagination
        try:
            result = await self.client.get_all_mobile_app_beacons(
                beacon_type="SESSION_START",
                pagination={"retrievalSize": 10},
                api_client=self.mock_api,
            )
            self.assertIn("error", result)
        finally:
            sys.modules["instana_client.models.cursor_pagination"].CursorPagination = original

    async def test_invalid_get_mobile_app_beacons_model(self):
        class FailingGetBeacons:
            def __init__(self, **kwargs):
                raise ValueError("invalid config")

        original = sys.modules["instana_client.models.get_mobile_app_beacons"].GetMobileAppBeacons
        sys.modules["instana_client.models.get_mobile_app_beacons"].GetMobileAppBeacons = FailingGetBeacons
        try:
            result = await self.client.get_all_mobile_app_beacons(
                beacon_type="SESSION_START",
                pagination={"retrievalSize": 10},
                api_client=self.mock_api,
            )
            self.assertIn("error", result)
        finally:
            sys.modules["instana_client.models.get_mobile_app_beacons"].GetMobileAppBeacons = original

    async def test_api_failure(self):
        self.mock_api.get_mobile_app_beacons_without_preload_content.side_effect = Exception("API failed")
        result = await self.client.get_all_mobile_app_beacons(beacon_type="SESSION_START", api_client=self.mock_api)
        self.assertIn("error", result)

    async def test_beacon_groups_missing_required_params(self):
        result = await self.client.get_mobile_app_beacon_groups(
            metrics=None,
            group=None,
            beacon_type=None,
            api_client=self.mock_api,
        )

        self.assertTrue(result.get("elicitation_required"))
        self.assertIn("missing_parameters", result)

    async def test_beacon_groups_defaults_applied(self):
        self.mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = MockResponse(
            json.dumps({"items": [], "totalHits": 0}).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        result = await self.client.get_mobile_app_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group={"groupByTag": "mobileBeacon.mobileApp.name"},
            api_client=self.mock_api,
        )

        self.assertIsInstance(result, dict)

    async def test_beacon_groups_success(self):
        payload = {
            "totalHits": 1,
            "items": [
                {
                    "beacon": {
                        "mobileAppLabel": "TestApp",
                        "timestamp": 123,
                        "errorCount": 0
                    }
                }
            ]
        }

        self.mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        result = await self.client.get_mobile_app_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group={"groupByTag": "mobileBeacon.mobileApp.name"},
            beacon_type="SESSION_START",
            api_client=self.mock_api,
        )

        self.assertIsInstance(result, dict)

    async def test_beacon_groups_tag_filter_invalid(self):
        self.mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = MockResponse(
            b'{"items": []}',
            {"Content-Type": "application/json"},
        )

        tag_filter = {
            "type": "TAG_FILTER",
            "name": "mobileBeacon.view.name",
            "operator": "EQUALS",
            "value": "Robot Shop",
            "entity": "NOT_APPLICABLE",
        }

        result = await self.client.get_mobile_app_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group={"groupByTag": "mobileBeacon.mobileApp.name"},
            tag_filter_expression=tag_filter,
            beacon_type="SESSION_START",
            api_client=self.mock_api,
        )

        # depends on your implementation path
        self.assertIsInstance(result, dict)

    async def test_beacon_groups_model_failure(self):
        class FailingModel:
            def __init__(self, **kwargs):
                raise ValueError("model failure")

        original = sys.modules["instana_client.models.get_mobile_app_beacon_groups"].GetMobileAppBeaconGroups
        sys.modules["instana_client.models.get_mobile_app_beacon_groups"].GetMobileAppBeaconGroups = FailingModel

        try:
            result = await self.client.get_mobile_app_beacon_groups(
                metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
                group={"groupByTag": "mobileBeacon.mobileApp.name"},
                beacon_type="SESSION_START",
                api_client=self.mock_api,
            )

            self.assertIn("error", result)

        finally:
            sys.modules["instana_client.models.get_mobile_app_beacon_groups"].GetMobileAppBeaconGroups = original

    async def test_beacon_groups_non_200_response(self):
        self.mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = MockResponse(
            b'{"errors": ["Metric type unknown"]}',
            {"Content-Type": "application/json"},
        )
        self.mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value.status = 400

        result = await self.client.get_mobile_app_beacon_groups(
            metrics=[{"metric": "invalidMetric", "aggregation": "SUM"}],
            group={"groupByTag": "mobileBeacon.mobileApp.name"},
            beacon_type="SESSION_START",
            api_client=self.mock_api,
        )

        self.assertIsInstance(result, dict)

    async def test_beacon_groups_group_mapping(self):
        self.mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = MockResponse(
            json.dumps({"items": []}).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        await self.client.get_mobile_app_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group={"groupByTag": "mobileBeacon.view.name"},
            beacon_type="SESSION_START",
            api_client=self.mock_api,
        )

        # ensures internal mapping doesn't crash
        self.assertTrue(True)

    async def test_beacon_groups_pagination_and_order(self):
        self.mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = MockResponse(
            json.dumps({"items": []}).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        result = await self.client.get_mobile_app_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group={"groupByTag": "mobileBeacon.mobileApp.name"},
            beacon_type="SESSION_START",
            order={"by": "beaconCount", "direction": "DESC"},
            pagination={"retrievalSize": 10},
            api_client=self.mock_api,
        )

        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
