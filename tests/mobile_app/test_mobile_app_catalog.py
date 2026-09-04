"""
Unit tests for the MobileAppCatalogMCPTools class
"""

import asyncio
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

app_logger = logging.getLogger("src.mobile_app.mobile_app_catalog")
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

sys.modules["instana_client"] = MagicMock()
sys.modules["instana_client.api"] = MagicMock()
sys.modules["instana_client.api.mobile_app_catalog_api"] = MagicMock()
sys.modules["instana_client.configuration"] = MagicMock()
sys.modules["instana_client.api_client"] = MagicMock()

mock_mobile_app_catalog_api = MagicMock()
mock_mobile_app_catalog_api.__name__ = "MobileAppCatalogApi"
sys.modules["instana_client.api.mobile_app_catalog_api"].MobileAppCatalogApi = mock_mobile_app_catalog_api

from src.core.utils import decode_response as _decode_response
from src.mobile_app.mobile_app_catalog import MobileAppCatalogMCPTools


class MockResponse:
    def __init__(self, payload: bytes, status: int = 200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {}


class TestMobileAppCatalogMCPTools(unittest.TestCase):
    """Test the MobileAppCatalogMCPTools class"""

    def setUp(self):
        mock_mobile_app_catalog_api.reset_mock()
        mock_mobile_app_catalog_api.side_effect = None
        mock_mobile_app_catalog_api.return_value = MagicMock()

        self.client = MobileAppCatalogMCPTools(read_token="test_token", base_url="https://test.instana.io")
        self.mock_api_client = MagicMock()

    def test_decode_response_fallback_utf8(self):
        response = MockResponse(b"hello")
        self.assertEqual(_decode_response(response), "hello")

    def test_decode_response_with_charset(self):
        response = MockResponse("olá".encode("latin-1"), headers={"Content-Type": "text/plain; charset=latin-1"})
        self.assertEqual(_decode_response(response), "olá")

    def test_decode_response_bad_charset_fallback(self):
        response = MockResponse(b"x", headers={"Content-Type": "text/plain; charset=invalid-charset"})
        self.assertEqual(_decode_response(response), "x")

    def test_get_mobile_app_tag_catalog_missing_beacon_type(self):
        result = asyncio.run(
            self.client.get_mobile_app_tag_catalog(
                beacon_type="",
                use_case="GROUPING",
                api_client=self.mock_api_client,
            )
        )
        self.assertEqual(result["error"], "beacon_type parameter is required")

    def test_get_mobile_app_tag_catalog_missing_use_case(self):
        result = asyncio.run(
            self.client.get_mobile_app_tag_catalog(
                beacon_type="SESSION_START",
                use_case="",
                api_client=self.mock_api_client,
            )
        )
        self.assertEqual(result["error"], "use_case parameter is required")

    def test_get_mobile_app_tag_catalog_success_tree_and_flat_tags(self):
        payload = {
            "tagTree": {
                "tagName": "mobileBeacon.root",
                "children": [
                    {"tagName": "mobileBeacon.view.name", "children": []},
                    {"tagName": "mobileBeacon.mobileApp.name"},
                ],
            },
            "tags": [
                {"name": "mobileBeacon.view.name"},
                {"name": "mobileBeacon.geo.city"},
                {"name": ""},
                {},
            ],
        }
        response = MockResponse(json.dumps(payload).encode("utf-8"), status=200, headers={"Content-Type": "application/json"})
        self.mock_api_client.get_mobile_app_tag_catalog_without_preload_content.return_value = response

        result = asyncio.run(
            self.client.get_mobile_app_tag_catalog(
                beacon_type="SESSION_START",
                use_case="GROUPING",
                api_client=self.mock_api_client,
            )
        )

        self.assertEqual(result["beacon_type"], "SESSION_START")
        self.assertEqual(result["use_case"], "GROUPING")
        self.assertEqual(result["count"], len(result["tag_names"]))
        self.assertIn("mobileBeacon.view.name", result["tag_names"])
        self.assertIn("mobileBeacon.geo.city", result["tag_names"])

    def test_get_mobile_app_tag_catalog_success_list_tree_node(self):
        payload = {
            "tagTree": [
                {"tagName": "mobileBeacon.a"},
                {"tagName": "mobileBeacon.b", "children": [{"tagName": "mobileBeacon.c"}]},
            ]
        }
        response = MockResponse(json.dumps(payload).encode("utf-8"), status=200, headers={"Content-Type": "application/json"})
        self.mock_api_client.get_mobile_app_tag_catalog_without_preload_content.return_value = response

        result = asyncio.run(
            self.client.get_mobile_app_tag_catalog(
                beacon_type="VIEW_CHANGE",
                use_case="FILTERING",
                api_client=self.mock_api_client,
            )
        )
        self.assertEqual(result["count"], 3)

    def test_get_mobile_app_tag_catalog_exception_path(self):
        self.mock_api_client.get_mobile_app_tag_catalog_without_preload_content.side_effect = RuntimeError("kaboom")
        result = asyncio.run(
            self.client.get_mobile_app_tag_catalog(
                beacon_type="SESSION_START",
                use_case="GROUPING",
                api_client=self.mock_api_client,
            )
        )
        self.assertIn("error", result)
        self.assertIn("kaboom", result["error"])

    def test_get_mobile_app_metric_catalog_http_error_with_details(self):
        response = MockResponse(b'{"message":"bad"}', status=400, headers={"Content-Type": "application/json"})
        self.mock_api_client.get_mobile_app_metric_catalog_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_mobile_app_metric_catalog(api_client=self.mock_api_client))
        self.assertIn("error", result)
        self.assertEqual(result["status_code"], 400)
        self.assertIn("details", result)

    def test_get_mobile_app_metric_catalog_http_error_without_details(self):
        # Raise on the second .data access (first is consumed by sdk_call_with_keepalive logging)
        call_count = [0]
        class BrokenDecodeResponse(MockResponse):
            @property
            def data(self):
                call_count[0] += 1
                if call_count[0] > 1:
                    raise ValueError("broken")
                return b""
            @data.setter
            def data(self, value):
                self._data = value

        response = BrokenDecodeResponse(b"", status=400)
        self.mock_api_client.get_mobile_app_metric_catalog_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_mobile_app_metric_catalog(api_client=self.mock_api_client))
        self.assertIn("error", result)
        self.assertEqual(result["status_code"], 400)
        self.assertNotIn("details", result)

    def test_get_mobile_app_metric_catalog_success(self):
        payload = [
            {"metricId": "metric.a"},
            {"metricId": "metric.b"},
            {"metricId": ""},
            {"name": "no-id"},
        ]
        response = MockResponse(json.dumps(payload).encode("utf-8"), status=200, headers={"Content-Type": "application/json"})
        self.mock_api_client.get_mobile_app_metric_catalog_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_mobile_app_metric_catalog(api_client=self.mock_api_client))
        self.assertIn("metrics", result)
        self.assertEqual(len(result["metrics"]), 4)
        self.assertEqual(result["metrics"][0]["metricId"], "metric.a")
        self.assertEqual(result["metrics"][1]["metricId"], "metric.b")
        self.assertEqual(result["count"], 2)
        self.assertIn("description", result)


    def test_get_mobile_app_metric_catalog_default_strips_internal_fields(self):
        payload = [
            {
                "metricId": "appLaunchTime",
                "label": "App launch time",
                "description": "Time to launch app.",
                "formatter": "LATENCY",
                "aggregations": ["MEAN", "P95"],
                "beaconTypes": ["sessionStart"],
                "pathToValueInBeacon": ["startupDuration"],
                "tagName": "mobileBeacon.startup",
                "defaultAggregation": None,
            }
        ]
        response = MockResponse(json.dumps(payload).encode("utf-8"), status=200, headers={"Content-Type": "application/json"})
        self.mock_api_client.get_mobile_app_metric_catalog_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_mobile_app_metric_catalog(api_client=self.mock_api_client))

        self.assertEqual(result["count"], 1)
        self.assertEqual(
            result["description"],
            "Mobile app monitoring metrics catalog with necessary metadata for query planning",
        )
        metric = result["metrics"][0]
        self.assertEqual(metric["metricId"], "appLaunchTime")
        self.assertNotIn("pathToValueInBeacon", metric)
        self.assertNotIn("tagName", metric)
        self.assertNotIn("defaultAggregation", metric)
        self.assertEqual(
            set(metric.keys()),
            {"metricId", "label", "description", "aggregations", "beaconTypes", "formatter"},
        )

    def test_get_mobile_app_metric_catalog_full_view_preserves_internal_fields(self):
        payload = [
            {
                "metricId": "appLaunchTime",
                "pathToValueInBeacon": ["startupDuration"],
                "tagName": "mobileBeacon.startup",
            }
        ]
        response = MockResponse(json.dumps(payload).encode("utf-8"), status=200, headers={"Content-Type": "application/json"})
        self.mock_api_client.get_mobile_app_metric_catalog_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_mobile_app_metric_catalog(api_client=self.mock_api_client, view="full"))

        self.assertEqual(
            result["description"],
            "Mobile app monitoring metrics catalog with full metadata",
        )
        metric = result["metrics"][0]
        self.assertEqual(metric["pathToValueInBeacon"], ["startupDuration"])
        self.assertEqual(metric["tagName"], "mobileBeacon.startup")

    def test_get_mobile_app_metric_catalog_invalid_view(self):
        result = asyncio.run(self.client.get_mobile_app_metric_catalog(api_client=self.mock_api_client, view="bogus"))
        self.assertIn("error", result)
        self.assertIn("bogus", result["error"])
        self.assertEqual(result["valid_views"], ["planner", "full"])
        self.mock_api_client.get_mobile_app_metric_catalog_without_preload_content.assert_not_called()

    def test_get_mobile_app_metric_catalog_exception_path(self):
        self.mock_api_client.get_mobile_app_metric_catalog_without_preload_content.side_effect = RuntimeError("explode")
        result = asyncio.run(self.client.get_mobile_app_metric_catalog(api_client=self.mock_api_client))
        self.assertIn("error", result)
        self.assertIn("explode", result["error"])


if __name__ == "__main__":
    unittest.main()
