"""
Unit tests for the MobileAppAnalyzeMCPTools class
"""

import json
import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch


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
sys.modules["instana_client.api.mobile_app_catalog_api"] = MagicMock()


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


VALID_MOBILE_CATALOG = [
    {
        "metricId": "beaconCount",
        "label": "Beacon Count",
        "description": "Number of beacons",
        "aggregations": ["SUM"],
        "beaconTypes": ["sessionStart", "viewChange", "httpRequest", "custom", "crash", "perf", "dropBeacon"],
        "formatter": "number",
    },
]

PATCH_CATALOG = patch(
    "src.core.metric_validation.fetch_metric_catalog_internal",
    return_value=VALID_MOBILE_CATALOG,
)


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

    def test_summarize_includes_custom_event_meta(self):
        input_data = {
            "totalHits": 1,
            "items": [
                {
                    "beacon": {
                        "mobileAppLabel": "App1",
                        "timestamp": 12345,
                        "type": "custom",
                        "meta": {"flow": "onboarding", "step": "signup"},
                    }
                }
            ],
        }
        result = self.client._summarize_beacons_response(input_data)
        self.assertEqual(len(result["beacons"]), 1)
        self.assertEqual(
            result["beacons"][0]["meta"],
            {"flow": "onboarding", "step": "signup"},
        )

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
        """Out-of-range retrievalSize is now rejected by pre-flight validation."""
        pagination = {"retrievalSize": 0}
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            pagination=pagination,
            api_client=self.mock_api,
        )
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("retrievalSize" in e for e in result.get("api_error", [])))

    async def test_pagination_max_bound(self):
        """Out-of-range retrievalSize is now rejected by pre-flight validation."""
        pagination = {"retrievalSize": 500}
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            pagination=pagination,
            api_client=self.mock_api,
        )
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("retrievalSize" in e for e in result.get("api_error", [])))

    async def test_tag_filter_single_missing_required_fields(self):
        """TAG_FILTER missing 'operator' is caught by StructureValidator pre-flight."""
        tag_filter = {"type": "TAG_FILTER", "name": "mobileBeacon.view.name", "entity": "NOT_APPLICABLE"}
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            tag_filter_expression=tag_filter,
            api_client=self.mock_api,
        )
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("operator" in e for e in result.get("api_error", [])))

    async def test_tag_filter_expression(self):
        """EXPRESSION missing logicalOperator is caught by StructureValidator pre-flight."""
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
        # Missing logicalOperator — caught by pre-flight validation
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("logicalOperator" in e for e in result.get("api_error", [])))

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

    @PATCH_CATALOG
    async def test_beacon_groups_success(self, _mock_fetch):
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

    @PATCH_CATALOG
    async def test_beacon_groups_tag_filter_invalid(self, _mock_fetch):
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

    @PATCH_CATALOG
    async def test_beacon_groups_model_failure(self, _mock_fetch):
        class FailingModel:
            def __init__(self, **kwargs):
                raise ValueError("model failure")

        original = sys.modules["instana_client.models.get_mobile_app_beacon_groups"].GetMobileAppBeaconGroups
        sys.modules["instana_client.models.get_mobile_app_beacon_groups"].GetMobileAppBeaconGroups = FailingModel

        try:
            result = await self.client.get_mobile_app_beacon_groups(
                metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
                group={"groupbyTag": "mobileBeacon.mobileApp.name", "groupbyTagEntity": "NOT_APPLICABLE"},
                beacon_type="SESSION_START",
                api_client=self.mock_api,
            )

            self.assertIn("error", result)

        finally:
            sys.modules["instana_client.models.get_mobile_app_beacon_groups"].GetMobileAppBeaconGroups = original

    @PATCH_CATALOG
    async def test_beacon_groups_non_200_response(self, _mock_fetch):
        self.mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = MockResponse(
            b'{"errors": ["Server error"]}',
            {"Content-Type": "application/json"},
        )
        self.mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value.status = 400

        result = await self.client.get_mobile_app_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group={"groupByTag": "mobileBeacon.mobileApp.name"},
            beacon_type="SESSION_START",
            api_client=self.mock_api,
        )

        self.assertIsInstance(result, dict)

    @PATCH_CATALOG
    async def test_beacon_groups_group_mapping(self, _mock_fetch):
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

    @PATCH_CATALOG
    async def test_beacon_groups_pagination_and_order(self, _mock_fetch):
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

    async def test_filter_fields_default_true_filters_beacons(self):
        """Test that filter_fields defaults to True and filters out non-essential fields"""
        payload = {
            "totalHits": 1,
            "items": [
                {
                    "beacon": {
                        "mobileAppLabel": "TestApp",
                        "timestamp": 123456789,
                        "beaconId": "beacon-123",
                        "sessionId": "session-456",
                        "view": "HomeScreen",
                        "platform": "iOS",
                        "osVersion": "17.0",
                        # Fields that should be filtered out
                        "unusedField1": "value1",
                        "unusedField2": "value2",
                        "emptyField": "",
                        "negativeOneField": -1,
                        "errorCount": 0,  # Should be filtered (0 for error count)
                    }
                }
            ],
        }
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        # Don't specify filter_fields - should default to True
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            api_client=self.mock_api,
        )

        self.assertIn("summary", result)
        self.assertIn("beacons", result)
        self.assertEqual(len(result["beacons"]), 1)

        beacon = result["beacons"][0]
        # Essential fields should be present
        self.assertIn("mobileAppLabel", beacon)
        self.assertIn("timestamp", beacon)
        self.assertIn("beaconId", beacon)
        self.assertIn("sessionId", beacon)
        self.assertIn("view", beacon)
        self.assertIn("platform", beacon)
        self.assertIn("osVersion", beacon)

        # Non-essential fields should be filtered out
        self.assertNotIn("unusedField1", beacon)
        self.assertNotIn("unusedField2", beacon)
        self.assertNotIn("emptyField", beacon)
        self.assertNotIn("negativeOneField", beacon)
        self.assertNotIn("errorCount", beacon)  # Filtered because it's 0

    async def test_filter_fields_false_returns_all_fields(self):
        """Test that filter_fields=False returns all beacon fields unfiltered"""
        payload = {
            "totalHits": 1,
            "items": [
                {
                    "beacon": {
                        "mobileAppLabel": "TestApp",
                        "timestamp": 123456789,
                        "beaconId": "beacon-123",
                        "unusedField1": "value1",
                        "unusedField2": "value2",
                        "emptyField": "",
                        "negativeOneField": -1,
                        "errorCount": 0,
                    }
                }
            ],
        }
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            filter_fields=False,  # Explicitly disable filtering
            api_client=self.mock_api,
        )

        self.assertIn("summary", result)
        self.assertIn("beacons", result)
        self.assertEqual(len(result["beacons"]), 1)

        beacon = result["beacons"][0]
        # ALL fields should be present when filter_fields=False
        self.assertIn("mobileAppLabel", beacon)
        self.assertIn("timestamp", beacon)
        self.assertIn("beaconId", beacon)
        self.assertIn("unusedField1", beacon)
        self.assertIn("unusedField2", beacon)
        self.assertIn("emptyField", beacon)
        self.assertIn("negativeOneField", beacon)
        self.assertIn("errorCount", beacon)

    async def test_filter_fields_true_explicitly_filters_beacons(self):
        """filter_fields=True explicitly must behave the same as the default — filtering happens."""
        payload = {
            "totalHits": 1,
            "items": [
                {
                    "beacon": {
                        "mobileAppLabel": "TestApp",
                        "timestamp": 123456789,
                        "unusedField1": "value1",
                        "errorCount": 0,
                    }
                }
            ],
        }
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            filter_fields=True,
            api_client=self.mock_api,
        )

        beacon = result["beacons"][0]
        self.assertIn("mobileAppLabel", beacon)
        self.assertIn("timestamp", beacon)
        self.assertNotIn("unusedField1", beacon)
        self.assertNotIn("errorCount", beacon)  # 0 → skipped by _should_skip_field_value

    async def test_filter_fields_none_behaves_like_true(self):
        """filter_fields=None must default to True — non-essential fields must still be filtered out."""
        payload = {
            "totalHits": 1,
            "items": [
                {
                    "beacon": {
                        "mobileAppLabel": "TestApp",
                        "timestamp": 123456789,
                        "unusedField1": "value1",
                        "errorCount": 0,
                    }
                }
            ],
        }
        self.mock_api.get_mobile_app_beacons_without_preload_content.return_value = MockResponse(
            json.dumps(payload).encode("utf-8"),
            {"Content-Type": "application/json"},
        )

        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            filter_fields=None,  # None must be normalised to True
            api_client=self.mock_api,
        )

        beacon = result["beacons"][0]
        self.assertIn("mobileAppLabel", beacon)
        self.assertIn("timestamp", beacon)
        # These must be absent — proving filtering ran, not skipped due to None being falsy
        self.assertNotIn("unusedField1", beacon)
        self.assertNotIn("errorCount", beacon)  # 0 → skipped by _should_skip_field_value


    async def test_get_beacons_invalid_beacon_type(self):
        """Test get_all_mobile_app_beacons with an invalid beacon_type returns elicitation"""
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="INVALID_TYPE",
            api_client=self.mock_api,
        )
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("INVALID_TYPE" in e for e in result.get("api_error", [])))

    async def test_get_beacons_invalid_time_frame(self):
        """Test get_all_mobile_app_beacons with invalid windowSize returns elicitation"""
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            time_frame={"windowSize": 9_999_999_999},
            api_client=self.mock_api,
        )
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("windowSize" in e for e in result.get("api_error", [])))

    async def test_get_beacons_multiple_validation_errors_consolidated(self):
        """Test get_all_mobile_app_beacons collects all validation errors in one response"""
        result = await self.client.get_all_mobile_app_beacons(
            beacon_type="INVALID_TYPE",
            pagination={"retrievalSize": 999},
            time_frame={"windowSize": 9_999_999_999},
            api_client=self.mock_api,
        )
        self.assertTrue(result.get("elicitation_needed"))
        # All three errors must be present in one response
        self.assertGreaterEqual(len(result.get("api_error", [])), 3)


if __name__ == "__main__":
    unittest.main()
