"""
Tests for Website Metrics Module

Tests website metrics functionality using unittest.
"""

import asyncio
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, Mock, patch

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            kwargs["api_client"] = self.metrics_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


# Create mock modules
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.website_metrics_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.get_website_metrics_v2'] = MagicMock()

mock_website_metrics_api = MagicMock()
mock_website_metrics_api.__name__ = "WebsiteMetricsApi"


class MockGetWebsiteMetricsV2:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def to_dict(self):
        return self.kwargs


sys.modules['instana_client.api.website_metrics_api'].WebsiteMetricsApi = mock_website_metrics_api
sys.modules['instana_client.models.get_website_metrics_v2'].GetWebsiteMetricsV2 = MockGetWebsiteMetricsV2

with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.website.website_metrics import WebsiteMetricsMCPTools


class TestWebsiteMetricsMCPTools(unittest.TestCase):
    """Test WebsiteMetricsMCPTools class"""

    def setUp(self):
        self.metrics_api = MagicMock()
        self.client = WebsiteMetricsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.metrics_api = self.metrics_api

    def test_initialization(self):
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.io")

    def test_get_website_page_load_missing_page_id(self):
        result = asyncio.run(self.client.get_website_page_load(page_id="", timestamp=123))
        self.assertEqual(result, [{"error": "page_id parameter is required"}])

    def test_get_website_page_load_missing_timestamp(self):
        result = asyncio.run(self.client.get_website_page_load(page_id="page-1", timestamp=0))
        self.assertEqual(result, [{"error": "timestamp parameter is required"}])

    def test_get_website_page_load_list_result_with_to_dict(self):
        mock_item = Mock()
        mock_item.to_dict.return_value = {"id": "item-1"}
        self.metrics_api.get_page_load.return_value = [mock_item, {"id": "item-2"}]

        result = asyncio.run(self.client.get_website_page_load(page_id="page-1", timestamp=123))

        self.metrics_api.get_page_load.assert_called_once_with(id="page-1", timestamp=123)
        self.assertEqual(result, [{"id": "item-1"}, {"id": "item-2"}])

    def test_get_website_page_load_single_result_with_to_dict(self):
        mock_result = Mock()
        mock_result.to_dict.return_value = {"id": "single-item"}
        self.metrics_api.get_page_load.return_value = mock_result

        result = asyncio.run(self.client.get_website_page_load(page_id="page-1", timestamp=123))

        self.assertEqual(result, [{"id": "single-item"}])

    def test_get_website_page_load_passthrough_result(self):
        self.metrics_api.get_page_load.return_value = [{"id": "already-list"}]

        result = asyncio.run(self.client.get_website_page_load(page_id="page-1", timestamp=123))

        self.assertEqual(result, [{"id": "already-list"}])

    def test_get_website_page_load_timeout_returns_list(self):
        from src.core.utils import SdkCallTimeout

        timeout = SdkCallTimeout({"error": "Instana API call timed out after 1s (get_website_page_load)."})
        self.metrics_api.get_page_load.return_value = timeout

        result = asyncio.run(self.client.get_website_page_load(page_id="page-1", timestamp=123))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("timed out", result[0]["error"])

    def test_get_website_page_load_exception(self):
        self.metrics_api.get_page_load.side_effect = Exception("API Error")

        result = asyncio.run(self.client.get_website_page_load(page_id="page-1", timestamp=123))

        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertIn("API Error", result[0]["error"])

    def test_get_website_beacon_metrics_v2_with_dict_payload(self):
        mock_result = Mock()
        mock_result.to_dict.return_value = {"items": [{"metric": "beaconCount"}]}
        self.metrics_api.get_beacon_metrics_v2.return_value = mock_result

        payload = {
            "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
            "type": "PAGELOAD",
            "tagFilterExpression": {"type": "EXPRESSION"},
            "timeFrame": {"windowSize": 60000},
        }

        result = asyncio.run(self.client.get_website_beacon_metrics_v2(payload=payload))

        self.assertIn("items", result)
        call_kwargs = self.metrics_api.get_beacon_metrics_v2.call_args.kwargs
        config_object = call_kwargs["get_website_metrics_v2"]
        self.assertEqual(
            config_object.kwargs,
            {
                "metrics": payload["metrics"],
                "type": "PAGELOAD",
                "tag_filter_expression": payload["tagFilterExpression"],
                "time_frame": payload["timeFrame"],
            }
        )

    def test_get_website_beacon_metrics_v2_capital_t_tag_filter_is_normalised(self):
        """TagFilterExpression must reach the SDK model as tag_filter_expression."""
        mock_result = Mock()
        mock_result.to_dict.return_value = {"items": []}
        self.metrics_api.get_beacon_metrics_v2.return_value = mock_result

        tag_filter = {"type": "TAG_FILTER", "name": "beacon.website.name", "operator": "EQUALS",
                      "entity": "NOT_APPLICABLE", "value": "site"}
        payload = {
            "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
            "type": "PAGELOAD",
            "TagFilterExpression": tag_filter,
        }

        asyncio.run(self.client.get_website_beacon_metrics_v2(payload=payload))

        config_object = self.metrics_api.get_beacon_metrics_v2.call_args.kwargs["get_website_metrics_v2"]
        self.assertEqual(config_object.kwargs["tag_filter_expression"], tag_filter)



    def test_get_website_beacon_metrics_v2_with_json_string_payload(self):
        mock_result = {"success": True}
        self.metrics_api.get_beacon_metrics_v2.return_value = mock_result

        payload = (
            '{"metrics":[{"metric":"beaconCount","aggregation":"SUM"}],'
            '"type":"PAGELOAD"}'
        )

        result = asyncio.run(self.client.get_website_beacon_metrics_v2(payload=payload))

        self.assertEqual(result, {"success": True})

    def test_get_website_beacon_metrics_v2_with_single_quote_payload(self):
        self.metrics_api.get_beacon_metrics_v2.return_value = {"ok": True}
        payload = "{'metrics':[{'metric':'beaconCount','aggregation':'SUM'}],'type':'PAGELOAD'}"

        result = asyncio.run(self.client.get_website_beacon_metrics_v2(payload=payload))

        self.assertEqual(result, {"ok": True})

    def test_get_website_beacon_metrics_v2_with_python_literal_payload(self):
        self.metrics_api.get_beacon_metrics_v2.return_value = {"ok": True}
        payload = "{'metrics': [{'metric': 'beaconCount', 'aggregation': 'SUM'}], 'type': 'PAGELOAD',}"

        result = asyncio.run(self.client.get_website_beacon_metrics_v2(payload=payload))

        self.assertEqual(result, {"ok": True})

    def test_get_website_beacon_metrics_v2_invalid_payload_format(self):
        payload = "{bad json"

        result = asyncio.run(self.client.get_website_beacon_metrics_v2(payload=payload))

        self.assertIn("error", result)
        self.assertIn("payload", result)

    def test_get_website_beacon_metrics_v2_missing_metrics(self):
        result = asyncio.run(
            self.client.get_website_beacon_metrics_v2(payload={"type": "PAGELOAD"})
        )

        self.assertEqual(result["error"], "Required field 'metrics' is missing from payload")

    def test_get_website_beacon_metrics_v2_missing_type(self):
        result = asyncio.run(
            self.client.get_website_beacon_metrics_v2(
                payload={"metrics": [{"metric": "beaconCount", "aggregation": "SUM"}]}
            )
        )

        self.assertEqual(result["error"], "Required field 'type' is missing from payload")

    def test_get_website_beacon_metrics_v2_uses_snake_case_fields(self):
        self.metrics_api.get_beacon_metrics_v2.return_value = {"ok": True}
        payload = {
            "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
            "type": "PAGELOAD",
            "tag_filter_expression": {"name": "beacon.website.name"},
            "time_frame": {"windowSize": 60000},
        }

        result = asyncio.run(self.client.get_website_beacon_metrics_v2(payload=payload))

        self.assertEqual(result, {"ok": True})
        call_kwargs = self.metrics_api.get_beacon_metrics_v2.call_args.kwargs
        config_object = call_kwargs["get_website_metrics_v2"]
        self.assertEqual(
            config_object.kwargs["tag_filter_expression"],
            {"name": "beacon.website.name"}
        )
        self.assertEqual(config_object.kwargs["time_frame"], {"windowSize": 60000})

    def test_get_website_beacon_metrics_v2_config_creation_failure(self):
        original_model = sys.modules['instana_client.models.get_website_metrics_v2'].GetWebsiteMetricsV2
        sys.modules['instana_client.models.get_website_metrics_v2'].GetWebsiteMetricsV2 = MagicMock(
            side_effect=Exception("bad config")
        )
        try:
            result = asyncio.run(
                self.client.get_website_beacon_metrics_v2(
                    payload={
                        "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                        "type": "PAGELOAD",
                    }
                )
            )
        finally:
            sys.modules['instana_client.models.get_website_metrics_v2'].GetWebsiteMetricsV2 = original_model

        self.assertIn("error", result)
        self.assertIn("bad config", result["error"])

    def test_get_website_beacon_metrics_v2_returns_default_success_when_result_none(self):
        self.metrics_api.get_beacon_metrics_v2.return_value = None

        result = asyncio.run(
            self.client.get_website_beacon_metrics_v2(
                payload={
                    "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                    "type": "PAGELOAD",
                }
            )
        )

        self.assertEqual(
            result,
            {"success": True, "message": "Get website beacon metrics"}
        )

    def test_get_website_beacon_metrics_v2_api_exception(self):
        self.metrics_api.get_beacon_metrics_v2.side_effect = Exception("API boom")

        result = asyncio.run(
            self.client.get_website_beacon_metrics_v2(
                payload={
                    "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                    "type": "PAGELOAD",
                }
            )
        )

        self.assertIn("error", result)
        self.assertIn("API boom", result["error"])


if __name__ == '__main__':
    unittest.main()