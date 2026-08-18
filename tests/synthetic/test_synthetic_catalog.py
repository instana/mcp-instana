"""
Unit tests for Synthetic Catalog Module

Tests synthetic catalog functionality using unittest.
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
            kwargs['api_client'] = self.catalog_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


# Mock modules that are not installed in test environment
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.synthetic_catalog_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.types'] = MagicMock()
sys.modules['fastmcp'] = MagicMock()

mock_catalog_api = MagicMock()
mock_catalog_api.__name__ = "SyntheticCatalogApi"
sys.modules['instana_client.api.synthetic_catalog_api'].SyntheticCatalogApi = mock_catalog_api

with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.synthetic.synthetic_catalog import SyntheticCatalogMCPTools


class TestSyntheticCatalogMCPTools(unittest.TestCase):
    """Unit tests for SyntheticCatalogMCPTools."""

    def setUp(self):
        """Set up test fixtures."""
        self.catalog_api = MagicMock()
        self.client = SyntheticCatalogMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.catalog_api = self.catalog_api

    def test_initialization(self):
        """Test SyntheticCatalogMCPTools initializes correctly."""
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.io")


    def test_get_synthetic_catalog_metrics_success_planner_view(self):
        """Planner (default) view should return compact metric cards."""
        raw_metrics = [
            {
                "metricId": "synthetic.metricsResponseTime",
                "label": "Response Time",
                "description": "Response time in ms",
                "formatter": "LATENCY",
                "aggregations": ["MEAN", "P95", "P99"],
                "beaconTypes": ["HTTP_REQUEST"],
                "pathToValueInBeacon": ["responseTime"],
                "tagName": "synthetic.responseTime",
                "defaultAggregation": "MEAN",
            },
            {
                "metricId": "synthetic.metricsStatus",
                "label": "Status",
                "description": "Test execution status",
                "formatter": "NUMBER",
                "aggregations": ["SUM"],
                "beaconTypes": ["HTTP_REQUEST", "SESSION_START"],
            },
        ]
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps(raw_metrics).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json; charset=utf-8'}
        self.catalog_api.get_synthetic_catalog_metrics_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_synthetic_catalog_metrics())

        self.assertIn("metrics", result)
        self.assertIn("count", result)
        self.assertIn("description", result)
        self.assertEqual(result["count"], 2)
        # Compact view should strip internal fields
        m = result["metrics"][0]
        self.assertEqual(m["metricId"], "synthetic.metricsResponseTime")
        self.assertNotIn("pathToValueInBeacon", m)
        self.assertNotIn("tagName", m)
        self.assertNotIn("defaultAggregation", m)

    def test_get_synthetic_catalog_metrics_full_view_preserves_internal_fields(self):
        """view='full' should return raw SDK fields including internal ones."""
        raw_metrics = [
            {
                "metricId": "synthetic.metricsResponseTime",
                "label": "Response Time",
                "pathToValueInBeacon": ["responseTime"],
                "tagName": "synthetic.responseTime",
                "defaultAggregation": "MEAN",
            }
        ]
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps(raw_metrics).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json; charset=utf-8'}
        self.catalog_api.get_synthetic_catalog_metrics_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_synthetic_catalog_metrics(view="full"))

        self.assertEqual(result["description"], "Synthetic monitoring metrics catalog with full metadata")
        m = result["metrics"][0]
        self.assertIn("pathToValueInBeacon", m)
        self.assertIn("tagName", m)

    def test_get_synthetic_catalog_metrics_invalid_view(self):
        """Invalid view should return error without calling the API."""
        self.catalog_api.get_synthetic_catalog_metrics_without_preload_content = Mock()

        result = asyncio.run(self.client.get_synthetic_catalog_metrics(view="unknown"))

        self.assertIn("error", result)
        self.assertIn("unknown", result["error"])
        self.assertEqual(result["valid_views"], ["planner", "full"])
        self.catalog_api.get_synthetic_catalog_metrics_without_preload_content.assert_not_called()

    def test_get_synthetic_catalog_metrics_http_error(self):
        """HTTP error response should be propagated as error dict."""
        mock_response = Mock()
        mock_response.status = 500
        mock_response.data = b'Internal Server Error'
        mock_response.headers = {'Content-Type': 'text/plain'}
        self.catalog_api.get_synthetic_catalog_metrics_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_synthetic_catalog_metrics())

        self.assertIn("error", result)
        self.assertIn("HTTP 500", result["error"])

    def test_get_synthetic_catalog_metrics_http_error_decode_fails(self):
        """When decode_response raises on an error response, status_code is still returned."""
        mock_response = Mock()
        mock_response.status = 503
        mock_response.data = None  # causes decode_response to raise
        mock_response.headers = {}
        self.catalog_api.get_synthetic_catalog_metrics_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_synthetic_catalog_metrics())

        self.assertIn("error", result)
        self.assertIn("HTTP 503", result["error"])
        self.assertEqual(result["status_code"], 503)

    def test_get_synthetic_catalog_metrics_exception(self):
        """API exception should be caught and returned as error dict."""
        self.catalog_api.get_synthetic_catalog_metrics_without_preload_content = Mock(
            side_effect=Exception("Connection refused")
        )

        result = asyncio.run(self.client.get_synthetic_catalog_metrics())

        self.assertIn("error", result)
        self.assertIn("Connection refused", result["error"])

    def test_get_synthetic_tag_catalog_success(self):
        """Successful tag catalog call should return tag_names, count, use_case."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({
            "tagTree": [
                {
                    "tagName": "synthetic.testName",
                    "children": [
                        {"tagName": "synthetic.locationId"},
                        {"tagName": "synthetic.applicationId"},
                    ]
                }
            ],
            "tags": [
                {"name": "synthetic.metricsStatus"},
                {"name": "synthetic.errors"},
            ]
        }).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json; charset=utf-8'}
        self.catalog_api.get_synthetic_tag_catalog_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_synthetic_tag_catalog(use_case="FILTERING"))

        self.assertIn("tag_names", result)
        self.assertIn("count", result)
        self.assertIn("use_case", result)
        self.assertEqual(result["use_case"], "FILTERING")
        self.assertGreater(result["count"], 0)
        self.assertIn("synthetic.testName", result["tag_names"])
        self.assertIn("synthetic.locationId", result["tag_names"])
        self.assertIn("synthetic.metricsStatus", result["tag_names"])

    def test_get_synthetic_tag_catalog_missing_use_case(self):
        """Missing use_case should return an error without calling the API."""
        self.catalog_api.get_synthetic_tag_catalog_without_preload_content = Mock()

        result = asyncio.run(self.client.get_synthetic_tag_catalog(use_case=None))

        self.assertIn("error", result)
        self.catalog_api.get_synthetic_tag_catalog_without_preload_content.assert_not_called()

    def test_get_synthetic_tag_catalog_http_error(self):
        """HTTP error response should be propagated as error dict."""
        mock_response = Mock()
        mock_response.status = 404
        mock_response.data = b'Not Found'
        mock_response.headers = {'Content-Type': 'text/plain'}
        self.catalog_api.get_synthetic_tag_catalog_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_synthetic_tag_catalog(use_case="GROUPING"))

        self.assertIn("error", result)
        self.assertIn("HTTP 404", result["error"])

    def test_get_synthetic_tag_catalog_http_error_decode_fails(self):
        """When decode_response raises on an error response, status_code is still returned."""
        mock_response = Mock()
        mock_response.status = 502
        mock_response.data = None  # causes decode_response to raise
        mock_response.headers = {}
        self.catalog_api.get_synthetic_tag_catalog_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_synthetic_tag_catalog(use_case="GROUPING"))

        self.assertIn("error", result)
        self.assertIn("HTTP 502", result["error"])
        self.assertEqual(result["status_code"], 502)

    def test_get_synthetic_tag_catalog_exception(self):
        """API exception should be caught and returned as error dict."""
        self.catalog_api.get_synthetic_tag_catalog_without_preload_content = Mock(
            side_effect=RuntimeError("Timeout")
        )

        result = asyncio.run(self.client.get_synthetic_tag_catalog(use_case="GROUPING"))

        self.assertIn("error", result)
        self.assertIn("Timeout", result["error"])

    def test_get_synthetic_tag_catalog_empty_response(self):
        """Empty catalog response should return zero-count result without error."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({}).encode('utf-8')
        mock_response.headers = {'Content-Type': 'application/json; charset=utf-8'}
        self.catalog_api.get_synthetic_tag_catalog_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_synthetic_tag_catalog(use_case="SMART_ALERTS"))

        self.assertIn("tag_names", result)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["tag_names"], [])


if __name__ == '__main__':
    unittest.main()
