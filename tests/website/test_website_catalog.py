"""
Tests for Website Catalog Module

Tests website catalog functionality using unittest.
"""

import asyncio
import json
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, Mock, patch

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Just pass the API client directly
            kwargs['api_client'] = self.catalog_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.website_catalog_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_website_catalog_api = MagicMock()

# Add __name__ attribute to mock classes
mock_website_catalog_api.__name__ = "WebsiteCatalogApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.website_catalog_api'].WebsiteCatalogApi = mock_website_catalog_api

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.core.utils import decode_response as _decode_response
    from src.website.website_catalog import WebsiteCatalogMCPTools


class TestDecodeResponse(unittest.TestCase):
    """Test _decode_response function"""

    def test_decode_with_utf8(self):
        """Test decoding with UTF-8 charset"""
        response = Mock()
        response.data = "test data".encode('utf-8')
        response.headers = {'Content-Type': 'application/json; charset=utf-8'}

        result = _decode_response(response)
        self.assertEqual(result, "test data")

    def test_decode_without_charset(self):
        """Test decoding without charset (defaults to UTF-8)"""
        response = Mock()
        response.data = "test data".encode('utf-8')
        response.headers = {'Content-Type': 'application/json'}

        result = _decode_response(response)
        self.assertEqual(result, "test data")

    def test_decode_with_invalid_charset_fallback(self):
        """Test decoding with invalid charset falls back to UTF-8"""
        response = Mock()
        response.data = "test data".encode('utf-8')
        response.headers = {'Content-Type': 'application/json; charset=invalid-charset'}

        result = _decode_response(response)
        self.assertEqual(result, "test data")


class TestWebsiteCatalogMCPTools(unittest.TestCase):
    """Test WebsiteCatalogMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        self.catalog_api = MagicMock()
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = WebsiteCatalogMCPTools(read_token=self.read_token, base_url=self.base_url)
        self.client.catalog_api = self.catalog_api

    def test_initialization(self):
        """Test WebsiteCatalogMCPTools initialization"""
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.io")

    def test_get_website_catalog_metrics_success(self):
        """Test get_website_catalog_metrics with successful response including full metadata"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps([
            {
                "metricId": "beaconCount",
                "label": "Beacon Count",
                "description": "Number of beacons",
                "formatter": "NUMBER",
                "aggregations": ["SUM"],
                "beaconTypes": ["pageLoad", "error"]
            },
            {
                "metricId": "onLoadTime",
                "label": "Page Load Time",
                "description": "Time to load page",
                "formatter": "LATENCY",
                "aggregations": ["MEAN", "P95", "P99"],
                "beaconTypes": ["pageLoad"]
            },
            {
                "metricId": "errorCount",
                "label": "Error Count",
                "description": "Number of errors",
                "formatter": "NUMBER",
                "aggregations": ["SUM"],
                "beaconTypes": ["error"]
            }
        ]).encode('utf-8')
        self.catalog_api.get_website_catalog_metrics_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.get_website_catalog_metrics())

        # Verify response structure
        self.assertIn("metrics", result)
        self.assertIn("count", result)
        self.assertIn("description", result)
        self.assertEqual(result["count"], 3)

        # Verify full metadata is returned
        metrics = result["metrics"]
        self.assertEqual(len(metrics), 3)

        # Check first metric has all metadata fields
        beacon_count = metrics[0]
        self.assertEqual(beacon_count["metricId"], "beaconCount")
        self.assertEqual(beacon_count["label"], "Beacon Count")
        self.assertEqual(beacon_count["description"], "Number of beacons")
        self.assertEqual(beacon_count["formatter"], "NUMBER")
        self.assertIn("SUM", beacon_count["aggregations"])
        self.assertIn("pageLoad", beacon_count["beaconTypes"])

        # Check second metric has aggregations
        page_load = metrics[1]
        self.assertEqual(page_load["metricId"], "onLoadTime")
        self.assertIn("MEAN", page_load["aggregations"])
        self.assertIn("P95", page_load["aggregations"])
        self.assertIn("P99", page_load["aggregations"])

    def test_get_website_catalog_metrics_default_strips_internal_fields(self):
        """Default (planner) view should strip pathToValueInBeacon, tagName, defaultAggregation."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps([
            {
                "metricId": "uniqueUsers",
                "label": "Unique users",
                "description": "Number of unique user ids.",
                "formatter": "NUMBER",
                "aggregations": ["DISTINCT_COUNT"],
                "beaconTypes": ["pageLoad"],
                "pathToValueInBeacon": ["userId"],
                "tagName": "beacon.userId",
                "defaultAggregation": None,
            }
        ]).encode('utf-8')
        self.catalog_api.get_website_catalog_metrics_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.get_website_catalog_metrics())

        self.assertEqual(result["count"], 1)
        self.assertEqual(
            result["description"],
            "Website monitoring metrics catalog with necessary metadata for query planning",
        )
        metric = result["metrics"][0]
        self.assertEqual(metric["metricId"], "uniqueUsers")
        self.assertEqual(metric["aggregations"], ["DISTINCT_COUNT"])
        self.assertNotIn("pathToValueInBeacon", metric)
        self.assertNotIn("tagName", metric)
        self.assertNotIn("defaultAggregation", metric)
        # Stable schema: all six compact keys present
        self.assertEqual(
            set(metric.keys()),
            {"metricId", "label", "description", "aggregations", "beaconTypes", "formatter"},
        )

    def test_get_website_catalog_metrics_full_view_preserves_internal_fields(self):
        """view='full' should return the raw SDK fields including internal ones."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps([
            {
                "metricId": "uniqueUsers",
                "label": "Unique users",
                "description": "Number of unique user ids.",
                "pathToValueInBeacon": ["userId"],
                "tagName": "beacon.userId",
            }
        ]).encode('utf-8')
        self.catalog_api.get_website_catalog_metrics_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.get_website_catalog_metrics(view="full"))

        self.assertEqual(
            result["description"],
            "Website monitoring metrics catalog with full metadata",
        )
        metric = result["metrics"][0]
        self.assertEqual(metric["pathToValueInBeacon"], ["userId"])
        self.assertEqual(metric["tagName"], "beacon.userId")

    def test_get_website_catalog_metrics_invalid_view(self):
        """Unknown view should return a structured error without calling the API."""
        self.catalog_api.get_website_catalog_metrics_without_preload_content = Mock()

        result = asyncio.run(self.client.get_website_catalog_metrics(view="bogus"))

        self.assertIn("error", result)
        self.assertIn("bogus", result["error"])
        self.assertEqual(result["valid_views"], ["planner", "full"])
        self.catalog_api.get_website_catalog_metrics_without_preload_content.assert_not_called()

    def test_get_website_catalog_metrics_http_error(self):
        """Test get_website_catalog_metrics with HTTP error"""
        mock_response = Mock()
        mock_response.status = 500
        mock_response.data = b'Internal Server Error'
        self.catalog_api.get_website_catalog_metrics_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.get_website_catalog_metrics(

        ))

        self.assertIn("error", result)
        self.assertIn("HTTP 500", result["error"])

    def test_get_website_catalog_metrics_exception(self):
        """Test get_website_catalog_metrics when API raises exception"""
        self.catalog_api.get_website_catalog_metrics_without_preload_content = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.get_website_catalog_metrics(

        ))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_get_website_catalog_tags_success_list(self):
        """Test get_website_catalog_tags with list response"""
        mock_tag1 = Mock()
        mock_tag1.to_dict.return_value = {"name": "beacon.website.name", "type": "STRING"}
        mock_tag2 = Mock()
        mock_tag2.to_dict.return_value = {"name": "beacon.page.name", "type": "STRING"}

        self.catalog_api.get_website_catalog_tags = Mock(return_value=[mock_tag1, mock_tag2])

        result = asyncio.run(self.client.get_website_catalog_tags(

        ))

        self.assertIn("tags", result)
        self.assertIn("count", result)
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["tags"]), 2)

    def test_get_website_catalog_tags_success_dict(self):
        """Test get_website_catalog_tags with dict response"""
        mock_result = {"tags": [{"name": "beacon.website.name"}]}
        self.catalog_api.get_website_catalog_tags = Mock(return_value=mock_result)

        result = asyncio.run(self.client.get_website_catalog_tags(

        ))

        self.assertIn("data", result)

    def test_get_website_catalog_tags_exception(self):
        """Test get_website_catalog_tags when API raises exception"""
        self.catalog_api.get_website_catalog_tags = Mock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.get_website_catalog_tags(

        ))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_get_website_tag_catalog_success(self):
        """Test get_website_tag_catalog with successful response"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({
            "tagTree": [
                {
                    "tagName": "beacon.website.name",
                    "children": [
                        {"tagName": "beacon.page.name"},
                        {"tagName": "beacon.user.country"}
                    ]
                }
            ],
            "tags": [
                {"name": "beacon.browser.name"},
                {"name": "beacon.os.name"}
            ]
        }).encode('utf-8')
        self.catalog_api.get_website_tag_catalog_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.get_website_tag_catalog(
            beacon_type="PAGELOAD",
            use_case="GROUPING",

        ))

        self.assertIn("tag_names", result)
        self.assertIn("count", result)
        self.assertIn("beacon_type", result)
        self.assertIn("use_case", result)
        self.assertEqual(result["beacon_type"], "PAGELOAD")
        self.assertEqual(result["use_case"], "GROUPING")
        # Should have 5 unique tags
        self.assertEqual(result["count"], 5)
        self.assertIn("beacon.website.name", result["tag_names"])
        self.assertIn("beacon.page.name", result["tag_names"])
        self.assertIn("beacon.browser.name", result["tag_names"])

    def test_get_website_tag_catalog_missing_beacon_type(self):
        """Test get_website_tag_catalog without beacon_type"""
        result = asyncio.run(self.client.get_website_tag_catalog(
            beacon_type=None,
            use_case="GROUPING",

        ))

        self.assertIn("error", result)
        self.assertIn("beacon_type parameter is required", result["error"])

    def test_get_website_tag_catalog_missing_use_case(self):
        """Test get_website_tag_catalog without use_case"""
        result = asyncio.run(self.client.get_website_tag_catalog(
            beacon_type="PAGELOAD",
            use_case=None,

        ))

        self.assertIn("error", result)
        self.assertIn("use_case parameter is required", result["error"])

    def test_get_website_tag_catalog_http_error(self):
        """Test get_website_tag_catalog with HTTP error"""
        mock_response = Mock()
        mock_response.status = 404
        mock_response.data = b'Not Found'
        self.catalog_api.get_website_tag_catalog_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.get_website_tag_catalog(
            beacon_type="PAGELOAD",
            use_case="GROUPING",

        ))

        self.assertIn("error", result)
        self.assertIn("HTTP 404", result["error"])

    def test_get_website_tag_catalog_exception(self):
        """Test get_website_tag_catalog when API raises exception"""
        self.catalog_api.get_website_tag_catalog_without_preload_content = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.get_website_tag_catalog(
            beacon_type="PAGELOAD",
            use_case="GROUPING",

        ))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_get_website_tag_catalog_empty_response(self):
        """Test get_website_tag_catalog with empty response"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({}).encode('utf-8')
        self.catalog_api.get_website_tag_catalog_without_preload_content = Mock(return_value=mock_response)

        result = asyncio.run(self.client.get_website_tag_catalog(
            beacon_type="PAGELOAD",
            use_case="GROUPING",

        ))

        self.assertIn("tag_names", result)
        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["tag_names"]), 0)


if __name__ == '__main__':
    unittest.main()
