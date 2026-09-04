"""
Unit tests for the metric catalog fetch helper (I/O layer).
"""

import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.metric_validation import fetch_metric_catalog_internal


def _make_response(payload, status=200, content_type="application/json"):
    resp = MagicMock()
    resp.status = status
    resp.data = json.dumps(payload).encode("utf-8") if isinstance(payload, (list, dict)) else payload
    resp.headers = {"Content-Type": content_type}
    return resp


class TestFetchMetricCatalogInternal(unittest.IsolatedAsyncioTestCase):

    def _make_api_client(self):
        api_client = MagicMock()
        api_client.api_client = MagicMock()
        return api_client

    async def test_successful_fetch(self):
        api_client = self._make_api_client()
        raw_catalog = [
            {
                "metricId": "onLoadTime",
                "label": "On Load Time",
                "description": "Page load time",
                "aggregations": ["MEAN", "SUM"],
                "beaconTypes": ["pageLoad"],
                "formatter": "millis",
            }
        ]
        mock_catalog_api = MagicMock()
        mock_catalog_instance = MagicMock()
        mock_catalog_api.return_value = mock_catalog_instance
        mock_catalog_instance.get_website_catalog_metrics_without_preload_content = AsyncMock(
            return_value=_make_response(raw_catalog)
        )

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "get_website_catalog_metrics_without_preload_content"
        )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["metricId"], "onLoadTime")
        self.assertIn("aggregations", result[0])
        self.assertIn("beaconTypes", result[0])

    async def test_missing_underlying_api_client(self):
        api_client = MagicMock(spec=[])  # no api_client attribute
        mock_catalog_api = MagicMock()

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "some_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("Cannot access underlying ApiClient", result["error"])
        # Must NOT be elicitation_needed — this is an infrastructure error
        self.assertNotIn("elicitation_needed", result)

    async def test_non_200_response(self):
        api_client = self._make_api_client()
        mock_catalog_api = MagicMock()
        mock_catalog_instance = MagicMock()
        mock_catalog_api.return_value = mock_catalog_instance
        mock_catalog_instance.fetch_method = AsyncMock(return_value=_make_response(
            {"error": "Internal Server Error"}, status=500
        ))

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "fetch_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("HTTP 500", result["error"])

    async def test_malformed_response_body(self):
        api_client = self._make_api_client()
        mock_catalog_api = MagicMock()
        mock_catalog_instance = MagicMock()
        mock_catalog_api.return_value = mock_catalog_instance

        resp = MagicMock()
        resp.status = 200
        resp.data = b"not json at all"
        resp.headers = {"Content-Type": "application/json"}
        mock_catalog_instance.fetch_method = AsyncMock(return_value=resp)

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "fetch_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("parse", result["error"].lower())

    async def test_projected_entry_with_none_metric_id(self):
        api_client = self._make_api_client()
        raw_catalog = [
            {
                "metricId": None,
                "label": "Bad Metric",
                "aggregations": ["SUM"],
                "beaconTypes": ["pageLoad"],
            }
        ]
        mock_catalog_api = MagicMock()
        mock_catalog_instance = MagicMock()
        mock_catalog_api.return_value = mock_catalog_instance
        mock_catalog_instance.fetch_method = AsyncMock(return_value=_make_response(raw_catalog))

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "fetch_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("malformed", result["error"].lower())

    async def test_projected_entry_with_non_list_beacon_types(self):
        api_client = self._make_api_client()
        raw_catalog = [
            {
                "metricId": "someMetric",
                "label": "Some Metric",
                "aggregations": ["SUM"],
                "beaconTypes": "not_a_list",
            }
        ]
        mock_catalog_api = MagicMock()
        mock_catalog_instance = MagicMock()
        mock_catalog_api.return_value = mock_catalog_instance
        mock_catalog_instance.fetch_method = AsyncMock(return_value=_make_response(raw_catalog))

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "fetch_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("malformed", result["error"].lower())

    async def test_projected_entry_with_non_list_aggregations(self):
        api_client = self._make_api_client()
        raw_catalog = [
            {
                "metricId": "someMetric",
                "label": "Some Metric",
                "aggregations": "not_a_list",
                "beaconTypes": ["pageLoad"],
            }
        ]
        mock_catalog_api = MagicMock()
        mock_catalog_instance = MagicMock()
        mock_catalog_api.return_value = mock_catalog_instance
        mock_catalog_instance.fetch_method = AsyncMock(return_value=_make_response(raw_catalog))

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "fetch_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("malformed", result["error"].lower())

    async def test_fetch_method_not_found(self):
        api_client = self._make_api_client()
        mock_catalog_api = MagicMock()
        mock_catalog_instance = MagicMock(spec=[])
        mock_catalog_api.return_value = mock_catalog_instance

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "nonexistent_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("no method", result["error"].lower())

    async def test_catalog_api_instantiation_failure(self):
        api_client = self._make_api_client()
        mock_catalog_api = MagicMock(side_effect=Exception("instantiation failed"))

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "some_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("instantiate", result["error"].lower())

    async def test_response_not_a_list(self):
        api_client = self._make_api_client()
        mock_catalog_api = MagicMock()
        mock_catalog_instance = MagicMock()
        mock_catalog_api.return_value = mock_catalog_instance
        mock_catalog_instance.fetch_method = AsyncMock(return_value=_make_response(
            {"metrics": "should be a list"}
        ))

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "fetch_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("not a list", result["error"].lower())

    async def test_non_dict_raw_catalog_entry(self):
        api_client = self._make_api_client()
        raw_catalog = [
            "not_a_dict",
            {"metricId": "validMetric", "aggregations": ["SUM"], "beaconTypes": ["pageLoad"]},
        ]
        mock_catalog_api = MagicMock()
        mock_catalog_instance = MagicMock()
        mock_catalog_api.return_value = mock_catalog_instance
        mock_catalog_instance.fetch_method = AsyncMock(return_value=_make_response(raw_catalog))

        result = await fetch_metric_catalog_internal(
            api_client, mock_catalog_api, "fetch_method"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("non-dict", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
