"""
Tests for Website Analyze Module

Tests website beacon analysis functionality using unittest.
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
def mock_with_header_auth(api_class, allow_mock=True):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if 'api_client' in kwargs and kwargs['api_client'] is not None:
                return await func(self, *args, **kwargs)
            kwargs['api_client'] = MagicMock()
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create a real base class
class MockBaseInstanaClient:
    def __init__(self, read_token=None, base_url=None, **kwargs):
        self.read_token = read_token
        self.base_url = base_url

# Create mock classes
class MockGetWebsiteBeaconGroups:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def to_dict(self):
        result = {}
        for key, value in self.kwargs.items():
            if hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result

class MockTagFilterExpressionElement:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def to_dict(self):
        return self.kwargs

# Set up mocks
mock_mcp = MagicMock()
mock_mcp_types = MagicMock()
mock_instana_client = MagicMock()
mock_instana_api = MagicMock()
mock_website_analyze_api = MagicMock()
mock_instana_models = MagicMock()

mock_get_website_beacon_groups = MagicMock()
mock_get_website_beacon_groups.GetWebsiteBeaconGroups = MockGetWebsiteBeaconGroups

mock_tag_filter_element = MagicMock()
mock_tag_filter_element.TagFilterExpressionElement = MockTagFilterExpressionElement

mock_cursor_pagination = MagicMock()
mock_cursor_pagination.CursorPagination = MagicMock

mock_get_website_beacons = MagicMock()
mock_get_website_beacons.GetWebsiteBeacons = MagicMock

mock_deprecated_tag_filter = MagicMock()
mock_deprecated_tag_filter.DeprecatedTagFilter = MagicMock

# Create mock modules (but NOT src.core or src.core.utils - use real ones)
sys.modules['mcp'] = mock_mcp
sys.modules['mcp.types'] = mock_mcp_types
sys.modules['instana_client'] = mock_instana_client
sys.modules['instana_client.api'] = mock_instana_api
sys.modules['instana_client.api.website_analyze_api'] = mock_website_analyze_api
sys.modules['instana_client.models'] = mock_instana_models
sys.modules['instana_client.models.get_website_beacon_groups'] = mock_get_website_beacon_groups
sys.modules['instana_client.models.tag_filter_expression_element'] = mock_tag_filter_element
sys.modules['instana_client.models.cursor_pagination'] = mock_cursor_pagination
sys.modules['instana_client.models.get_website_beacons'] = mock_get_website_beacons
sys.modules['instana_client.models.deprecated_tag_filter'] = mock_deprecated_tag_filter
sys.modules['instana_client.api.website_catalog_api'] = MagicMock()

# Patch the decorator and base class in the real src.core.utils module
from src.core import utils as real_utils

_orig_with_header_auth = real_utils.with_header_auth
_orig_base_instana_client = real_utils.BaseInstanaClient

real_utils.with_header_auth = mock_with_header_auth
real_utils.BaseInstanaClient = MockBaseInstanaClient

# Now import the module to test
from src.core.utils import DEFAULT_CHARSET
from src.core.utils import decode_response as _decode_response
from src.website.website_analyze import (
    DEFAULT_GROUP_BY_TAG,
    DEFAULT_GROUP_BY_TAG_ENTITY,
    WebsiteAnalyzeMCPTools,
    clean_nan_values,
)

# Restore real utils so subsequent test modules are not affected
real_utils.with_header_auth = _orig_with_header_auth
real_utils.BaseInstanaClient = _orig_base_instana_client

VALID_WEBSITE_CATALOG = [
    {
        "metricId": "beaconCount",
        "label": "Beacon Count",
        "aggregations": ["SUM"],
        "beaconTypes": ["pageLoad", "pageChange", "httpRequest", "error", "custom", "resourceLoad"],
        "formatter": "number",
    },
    {
        "metricId": "onLoadTime",
        "label": "On Load Time",
        "aggregations": ["MEAN", "P50", "P90", "P95", "P99", "MAX", "MIN", "SUM"],
        "beaconTypes": ["pageLoad"],
        "formatter": "millis",
    },
]

PATCH_CATALOG = patch(
    "src.core.metric_validation.fetch_metric_catalog_internal",
    return_value=VALID_WEBSITE_CATALOG,
)


class TestCleanNanValues(unittest.TestCase):
    """Test clean_nan_values function"""

    def test_clean_nan_in_dict(self):
        """Test cleaning NaN values in dictionary"""
        data = {"key1": "NaN", "key2": "value", "key3": "NaN"}
        result = clean_nan_values(data)

        self.assertIsNone(result["key1"])
        self.assertEqual(result["key2"], "value")
        self.assertIsNone(result["key3"])

    def test_clean_nan_in_list(self):
        """Test cleaning NaN values in list"""
        data = ["NaN", "value", "NaN", 123]
        result = clean_nan_values(data)

        self.assertIsNone(result[0])
        self.assertEqual(result[1], "value")
        self.assertIsNone(result[2])
        self.assertEqual(result[3], 123)

    def test_clean_nan_in_nested_structure(self):
        """Test cleaning NaN values in nested structures"""
        data = {
            "level1": {
                "level2": ["NaN", {"level3": "NaN"}]
            },
            "other": "NaN"
        }
        result = clean_nan_values(data)

        self.assertIsNone(result["level1"]["level2"][0])
        self.assertIsNone(result["level1"]["level2"][1]["level3"])
        self.assertIsNone(result["other"])

    def test_clean_nan_preserves_other_values(self):
        """Test that non-NaN values are preserved"""
        data = {
            "string": "test",
            "number": 123,
            "float": 45.67,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"}
        }
        result = clean_nan_values(data)

        self.assertEqual(result, data)

    def test_clean_nan_with_nan_string_case_sensitive(self):
        """Test that only exact 'NaN' string is cleaned"""
        data = {"NaN": "NaN", "nan": "nan", "NAN": "NAN"}
        result = clean_nan_values(data)

        self.assertIsNone(result["NaN"])
        self.assertEqual(result["nan"], "nan")
        self.assertEqual(result["NAN"], "NAN")


class TestDecodeResponse(unittest.TestCase):
    """Test _decode_response function"""

    def test_decode_with_utf8(self):
        """Test decoding with UTF-8 charset"""
        response = Mock()
        response.data = "test data".encode('utf-8')
        response.headers = {'Content-Type': 'application/json; charset=utf-8'}

        result = _decode_response(response)
        self.assertEqual(result, "test data")

    def test_decode_with_custom_charset(self):
        """Test decoding with custom charset"""
        response = Mock()
        response.data = "test data".encode('iso-8859-1')
        response.headers = {'Content-Type': 'application/json; charset=iso-8859-1'}

        result = _decode_response(response)
        self.assertEqual(result, "test data")

    def test_decode_without_charset(self):
        """Test decoding without charset (defaults to UTF-8)"""
        response = Mock()
        response.data = "test data".encode('utf-8')
        response.headers = {'Content-Type': 'application/json'}

        result = _decode_response(response)
        self.assertEqual(result, "test data")

    def test_decode_without_headers(self):
        """Test decoding without headers"""
        response = Mock()
        response.data = "test data".encode('utf-8')
        response.headers = None

        result = _decode_response(response)
        self.assertEqual(result, "test data")

    def test_decode_with_invalid_charset_fallback(self):
        """Test decoding with invalid charset falls back to UTF-8"""
        response = Mock()
        response.data = "test data".encode('utf-8')
        response.headers = {'Content-Type': 'application/json; charset=invalid-charset'}

        result = _decode_response(response)
        self.assertEqual(result, "test data")

    def test_decode_with_unicode_decode_error(self):
        """Test decoding with unicode decode error uses replacement"""
        response = Mock()
        response.data = b'\x80\x81\x82'
        response.headers = {'Content-Type': 'application/json; charset=utf-8'}

        result = _decode_response(response)
        self.assertIsInstance(result, str)


class TestWebsiteAnalyzeMCPTools(unittest.TestCase):
    """Test WebsiteAnalyzeMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        self.tools_instance = WebsiteAnalyzeMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.mock_api_client = Mock()
        self.mock_api_client.get_beacon_groups_without_preload_content = Mock()
        self.mock_api_client.get_beacons_without_preload_content = Mock()

    def test_initialization(self):
        """Test WebsiteAnalyzeMCPTools initialization"""
        self.assertEqual(self.tools_instance.read_token, "test_token")
        self.assertEqual(self.tools_instance.base_url, "https://test.instana.io")

    @PATCH_CATALOG
    def test_get_beacon_groups_with_all_params(self, _mock_catalog):
        """Test get_website_beacon_groups with all parameters"""
        metrics = [{"metric": "beaconCount", "aggregation": "SUM"}]
        group = {"groupByTag": "beacon.page.name"}
        tag_filter = {
            "type": "TAG_FILTER",
            "name": "beacon.website.name",
            "operator": "EQUALS",
            "entity": "NOT_APPLICABLE",
            "value": "test-site"
        }
        time_frame = {"windowSize": 3600000}
        beacon_type = "PAGELOAD"

        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": []}).encode('utf-8')
        self.mock_api_client.get_beacon_groups_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacon_groups(
            metrics=metrics,
            group=group,
            tag_filter_expression=tag_filter,
            time_frame=time_frame,
            beacon_type=beacon_type,
            api_client=self.mock_api_client
        ))

        self.assertIn("items", result)
        self.mock_api_client.get_beacon_groups_without_preload_content.assert_called_once()

    @PATCH_CATALOG
    def test_get_beacon_groups_with_defaults(self, _mock_catalog):
        """Test get_website_beacon_groups applies defaults"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": []}).encode('utf-8')
        self.mock_api_client.get_beacon_groups_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group={"groupByTag": "beacon.page.name"},
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        self.assertIn("items", result)

    @PATCH_CATALOG
    def test_get_beacon_groups_http_error(self, _mock_catalog):
        """Test get_website_beacon_groups with HTTP error"""
        metrics = [{"metric": "beaconCount", "aggregation": "SUM"}]
        group = {"groupByTag": "beacon.page.name"}

        mock_response = Mock()
        mock_response.status = 500
        mock_response.data = b'Internal Server Error'
        self.mock_api_client.get_beacon_groups_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacon_groups(
            metrics=metrics,
            group=group,
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("HTTP 500", result["error"])

    @PATCH_CATALOG
    def test_get_beacon_groups_invalid_metric_error(self, _mock_catalog):
        """Test get_website_beacon_groups with invalid metric — now caught
        by pre-flight catalog validation before reaching the API."""
        metrics = [{"metric": "invalidMetric", "aggregation": "SUM"}]
        group = {"groupByTag": "beacon.page.name"}

        result = asyncio.run(self.tools_instance.get_website_beacon_groups(
            metrics=metrics,
            group=group,
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        self.assertIn("elicitation_needed", result)
        self.assertIn("invalid", result["reason"].lower())
        self.mock_api_client.get_beacon_groups_without_preload_content.assert_not_called()

    @PATCH_CATALOG
    def test_get_beacon_groups_api_exception(self, _mock_catalog):
        """Test get_website_beacon_groups when API raises exception"""
        metrics = [{"metric": "beaconCount", "aggregation": "SUM"}]
        group = {"groupByTag": "beacon.page.name"}

        self.mock_api_client.get_beacon_groups_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.tools_instance.get_website_beacon_groups(
            metrics=metrics,
            group=group,
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        self.assertIn("error", result)

    @PATCH_CATALOG
    def test_get_beacon_groups_invalid_tag_filter(self, _mock_catalog):
        """Test get_website_beacon_groups with invalid tag filter expression"""
        metrics = [{"metric": "beaconCount", "aggregation": "SUM"}]
        group = {"groupByTag": "beacon.page.name"}
        tag_filter = {"invalid": "structure"}

        with patch('instana_client.models.tag_filter_expression_element.TagFilterExpressionElement') as mock_tag_filter:
            mock_tag_filter.from_dict.side_effect = Exception("Invalid tag filter")

            result = asyncio.run(self.tools_instance.get_website_beacon_groups(
                metrics=metrics,
                group=group,
                tag_filter_expression=tag_filter,
                beacon_type="PAGELOAD",
                api_client=self.mock_api_client
            ))

            self.assertIn("error", result)
            self.assertIn("Invalid tag filter expression", result["error"])

    def test_get_beacons_missing_beacon_type(self):
        """Test get_website_beacons without beacon_type triggers elicitation"""
        result = asyncio.run(self.tools_instance.get_website_beacons(
            api_client=self.mock_api_client
        ))

        self.assertIn("elicitation_needed", result)
        self.assertIn("missing_parameters", result)
        self.assertTrue(any(p["name"] == "beacon_type" for p in result["missing_parameters"]))

    def test_get_beacons_with_beacon_type(self):
        """Test get_website_beacons with beacon_type"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({
            "items": [],
            "totalHits": 0
        }).encode('utf-8')
        self.mock_api_client.get_beacons_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        # The response should have either summary or beacons key after summarization
        self.assertTrue("summary" in result or "beacons" in result or "items" in result)

    def test_summarize_valid_response(self):
        """Test summarizing valid beacons response"""
        response_data = {
            "totalHits": 100,
            "totalRepresentedItemCount": 50,
            "totalRetainedItemCount": 50,
            "canLoadMore": True,
            "adjustedTimeframe": {"from": 1000, "to": 2000},
            "items": [
                {
                    "beacon": {
                        "websiteLabel": "Test Site",
                        "timestamp": 1234567890,
                        "duration": 1500,
                        "page": "/home",
                        "errorCount": 0
                    }
                }
            ]
        }

        result = self.tools_instance._summarize_beacons_response(response_data)

        self.assertIn("summary", result)
        self.assertEqual(result["summary"]["totalHits"], 100)
        self.assertTrue(result["summary"]["canLoadMore"])
        self.assertIn("beacons", result)
        self.assertEqual(len(result["beacons"]), 1)
        self.assertEqual(result["beacons"][0]["websiteLabel"], "Test Site")

    def test_check_elicitation_all_params_missing(self):
        """Test elicitation when all parameters are missing"""
        result = self.tools_instance._check_elicitation_for_beacon_groups(None, None, None)

        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_required"])
        self.assertEqual(len(result["missing_parameters"]), 3)

    def test_check_elicitation_metrics_example_uses_current_page_load_metric(self):
        """Missing-parameter guidance should advertise the catalog-backed page load metric."""
        result = self.tools_instance._check_elicitation_for_beacon_groups(None, {"groupByTag": "beacon.page.name"}, "PAGELOAD")
        metrics_param = next(param for param in result["missing_parameters"] if param["name"] == "metrics")
        stale_metric = "page" + "LoadTime"

        self.assertIn({"metric": "onLoadTime", "aggregation": "MEAN"}, metrics_param["examples"])
        self.assertNotIn({"metric": stale_metric, "aggregation": "MEAN"}, metrics_param["examples"])

    def test_validate_valid_tags(self):
        """Test validation with valid beacon.* tags"""
        tag_filter = {
            "type": "TAG_FILTER",
            "name": "beacon.website.name",
            "operator": "EQUALS",
            "entity": "NOT_APPLICABLE",
            "value": "test"
        }
        group = {"groupByTag": "beacon.page.name"}

        result = self.tools_instance._validate_tag_names(tag_filter, group, "PAGELOAD")

        self.assertIsNone(result)

    def test_validate_invalid_tag_name(self):
        """Test validation with invalid tag name"""
        tag_filter = {
            "type": "TAG_FILTER",
            "name": "invalid.tag.name",
            "operator": "EQUALS",
            "entity": "NOT_APPLICABLE",
            "value": "test"
        }
        group = {"groupByTag": "beacon.page.name"}

        result = self.tools_instance._validate_tag_names(tag_filter, group, "PAGELOAD")

        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_validate_tag_with_expression_type(self):
        """Test validation with EXPRESSION type containing TAG_FILTERs"""
        tag_filter = {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [
                {
                    "type": "TAG_FILTER",
                    "name": "beacon.page.name",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "home"
                }
            ]
        }
        group = {"groupByTag": "beacon.user.name"}

        result = self.tools_instance._validate_tag_names(tag_filter, group, "PAGELOAD")

        self.assertIsNone(result)

    def test_validate_tag_missing_entity_in_expression(self):
        """Test validation detects missing entity in EXPRESSION elements"""
        tag_filter = {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [
                {
                    "type": "TAG_FILTER",
                    "name": "beacon.page.name",
                    "operator": "EQUALS",
                    "value": "home"
                    # Missing entity field
                }
            ]
        }

        result = self.tools_instance._validate_tag_names(tag_filter, None, "PAGELOAD")

        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_validate_tag_no_tags_extracted(self):
        """Test validation when no tag names are extracted"""
        tag_filter = {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": []
        }
        group = {}

        result = self.tools_instance._validate_tag_names(tag_filter, group, "PAGELOAD")

        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_get_beacons_with_tag_filter_single(self):
        """Test get_website_beacons with single TAG_FILTER"""
        tag_filter = {
            "type": "TAG_FILTER",
            "name": "beacon.website.name",
            "operator": "EQUALS",
            "entity": "NOT_APPLICABLE",
            "value": "test-site"
        }

        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": [], "totalHits": 0}).encode('utf-8')
        self.mock_api_client.get_beacons_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="PAGELOAD",
            tag_filter_expression=tag_filter,
            api_client=self.mock_api_client
        ))

        self.assertIn("summary", result)

    def test_get_beacons_with_expression_type(self):
        """Test get_website_beacons with EXPRESSION type"""
        tag_filter = {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [
                {
                    "type": "TAG_FILTER",
                    "name": "beacon.page.name",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "home"
                }
            ]
        }

        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": [], "totalHits": 0}).encode('utf-8')
        self.mock_api_client.get_beacons_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="PAGELOAD",
            tag_filter_expression=tag_filter,
            api_client=self.mock_api_client
        ))

        self.assertIn("summary", result)

    def test_get_beacons_pagination_limits(self):
        """Test get_website_beacons pagination size limits"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": [], "totalHits": 0}).encode('utf-8')
        self.mock_api_client.get_beacons_without_preload_content.return_value = mock_response

        # Test below minimum
        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="PAGELOAD",
            pagination={"retrievalSize": -5},
            api_client=self.mock_api_client
        ))
        self.assertIn("summary", result)

        # Test above maximum
        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="PAGELOAD",
            pagination={"retrievalSize": 500},
            api_client=self.mock_api_client
        ))
        self.assertIn("summary", result)

    def test_get_beacons_invalid_tag_filter(self):
        """Test get_website_beacons with invalid tag filter"""
        tag_filter = {
            "type": "TAG_FILTER",
            "name": "beacon.page.name",
            "operator": "EQUALS"
            # Missing value and entity fields
        }

        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="PAGELOAD",
            tag_filter_expression=tag_filter,
            api_client=self.mock_api_client
        ))

        # Should trigger elicitation for missing entity field
        self.assertIn("elicitation_needed", result)

    def test_summarize_beacons_with_empty_values(self):
        """Test summarizing beacons with empty/default values"""
        response_data = {
            "totalHits": 10,
            "items": [
                {
                    "beacon": {
                        "websiteLabel": "Test",
                        "timestamp": 1234567890,
                        "duration": 100,  # Non-zero value should be kept
                        "errorCount": 0,  # Should be skipped (0 for errorCount)
                        "page": "",  # Should be skipped (empty string)
                        "emptyList": [],  # Should be skipped
                        "emptyDict": {},  # Should be skipped
                        "nullValue": None,  # Should be skipped
                        "browserName": "Chrome"  # Essential field, should be kept
                    }
                }
            ]
        }

        result = self.tools_instance._summarize_beacons_response(response_data)

        self.assertIn("beacons", result)
        self.assertEqual(len(result["beacons"]), 1)
        # Check that empty values were filtered out and valid ones kept
        beacon = result["beacons"][0]
        self.assertIn("duration", beacon)  # Non-zero duration should be kept
        self.assertNotIn("errorCount", beacon)  # 0 errorCount should be skipped
        self.assertNotIn("page", beacon)  # Empty string should be skipped
        self.assertIn("browserName", beacon)  # Essential field should be kept

    def test_summarize_beacons_invalid_item_structure(self):
        """Test summarizing with invalid item structure"""
        response_data = {
            "totalHits": 2,
            "items": [
                "invalid_item",  # Not a dict
                {"no_beacon_key": "value"},  # Missing beacon key
                {"beacon": "not_a_dict"}  # Beacon is not a dict
            ]
        }

        result = self.tools_instance._summarize_beacons_response(response_data)

        self.assertIn("beacons", result)
        self.assertEqual(len(result["beacons"]), 0)

    @PATCH_CATALOG
    def test_get_beacon_groups_with_groupby_tag_lowercase(self, _mock_catalog):
        """Test get_website_beacon_groups with lowercase groupbyTag"""
        group = {"groupbyTag": "beacon.page.name"}

        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": []}).encode('utf-8')
        self.mock_api_client.get_beacon_groups_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group=group,
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        self.assertIn("items", result)

    @PATCH_CATALOG
    def test_get_beacon_groups_with_groupby_tag_entity(self, _mock_catalog):
        """Test get_website_beacon_groups with groupByTagEntity"""
        group = {
            "groupByTag": "beacon.page.name",
            "groupByTagEntity": "DESTINATION"
        }

        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": []}).encode('utf-8')
        self.mock_api_client.get_beacon_groups_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group=group,
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        self.assertIn("items", result)

    @PATCH_CATALOG
    def test_get_beacon_groups_nan_error(self, _mock_catalog):
        """Test get_website_beacon_groups with NaN error in response"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": []}).encode('utf-8')

        # Simulate NaN error
        self.mock_api_client.get_beacon_groups_without_preload_content.side_effect = Exception(
            "customMetric: NaN is not valid"
        )

        result = asyncio.run(self.tools_instance.get_website_beacon_groups(
            metrics=[{"metric": "beaconCount", "aggregation": "SUM"}],
            group={"groupByTag": "beacon.page.name"},
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("NaN", result["error"])

    def test_validate_tag_missing_entity(self):
        """Test validation with missing entity field"""
        tag_filter = {
            "type": "TAG_FILTER",
            "name": "beacon.website.name",
            "operator": "EQUALS",
            "value": "test"
            # Missing entity field
        }

        result = self.tools_instance._validate_tag_names(tag_filter, None, "PAGELOAD")

        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("missing_entity_tags", result)

    def test_get_beacons_list_response(self):
        """Test get_website_beacons with list response"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps([{"beacon": "data"}]).encode('utf-8')
        self.mock_api_client.get_beacons_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        # After summarization, list responses are converted to dict with beacons key
        self.assertIn("summary", result)
        self.assertIn("beacons", result)

    def test_get_beacons_non_dict_response(self):
        """Test get_website_beacons with non-dict response"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps("string response").encode('utf-8')
        self.mock_api_client.get_beacons_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="PAGELOAD",
            api_client=self.mock_api_client
        ))

        # After summarization, non-dict responses are wrapped
        self.assertIn("summary", result)

    def test_error_beacon_includes_stack_trace_fields(self):
        """Test that ERROR beacons include stackTrace, parsedStackTrace, errorId, stackTraceReadability, and sessionId"""
        # Create mock response with ERROR beacon data including all stack trace related fields
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({
            "totalHits": 1,
            "items": [
                {
                    "beacon": {
                        "websiteLabel": "Test Site",
                        "timestamp": 1234567890,
                        "beaconType": "ERROR",
                        "stackTrace": "Error: Something went wrong\n    at function1 (file.js:10:5)\n    at function2 (app.js:25:10)",
                        "parsedStackTrace": [
                            {
                                "file": "file.js",
                            },
                            {
                                "file": "app.js",
                            }
                        ],
                        "errorId": "error-123-456",
                        "stackTraceReadability": "READABLE",
                        "sessionId": "session-abc-def",
                        "errorMessage": "Something went wrong",
                        "page": "/checkout"
                    }
                }
            ]
        }).encode('utf-8')
        self.mock_api_client.get_beacons_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="ERROR",
            time_frame={"windowSize": 3600000},
            api_client=self.mock_api_client
        ))

        # Verify all stack trace related fields are present and not empty
        self.assertIn("beacons", result)
        beacon = result["beacons"][0]

        self.assertIn("stackTrace", beacon)
        self.assertIn("parsedStackTrace", beacon)
        self.assertIn("errorId", beacon)
        self.assertIn("stackTraceReadability", beacon)
        self.assertIn("sessionId", beacon)

        self.assertIsNotNone(beacon["stackTrace"])
        self.assertIsNotNone(beacon["parsedStackTrace"])
        self.assertIsNotNone(beacon["errorId"])
        self.assertIsNotNone(beacon["stackTraceReadability"])
        self.assertIsNotNone(beacon["sessionId"])

    def test_pageload_beacon_includes_back_trace_fields(self):
        """Test that PAGELOAD beacons include backendTraceId and sessionId fields"""
        # Create mock response with PAGELOAD beacon data including backendTraceId
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = json.dumps({
            "totalHits": 1,
            "items": [
                {
                    "beacon": {
                        "websiteLabel": "Test Site",
                        "timestamp": 1234567890,
                        "beaconType": "PAGELOAD",
                        "page": "/home",
                        "backendTraceId": "trace-abc-123-xyz",
                        "sessionId": "session-xyz-789",
                        "duration": 1500,
                        "onLoadTime": 1200
                    }
                }
            ]
        }).encode('utf-8')

        self.mock_api_client.get_beacons_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tools_instance.get_website_beacons(
            beacon_type="PAGELOAD",
            time_frame={"windowSize": 3600000},
            api_client=self.mock_api_client
        ))

        # Verify backendTraceId and sessionId fields are present
        self.assertIn("beacons", result)
        beacon = result["beacons"][0]

        self.assertIn("backendTraceId", beacon)
        self.assertIn("sessionId", beacon)

        self.assertIsNotNone(beacon["backendTraceId"])
        self.assertIsNotNone(beacon["sessionId"])

        # Verify stack ERROR beacon stack trace fields are not present
        self.assertNotIn("stackTrace", beacon)
        self.assertNotIn("parsedStackTrace", beacon)
        self.assertNotIn("errorId", beacon)
        self.assertNotIn("stackTraceReadability", beacon)



class TestConstants(unittest.TestCase):
    """Test module constants"""

    def test_default_charset(self):
        """Test DEFAULT_CHARSET constant"""
        self.assertEqual(DEFAULT_CHARSET, 'utf-8')

    def test_default_group_by_tag(self):
        """Test DEFAULT_GROUP_BY_TAG constant"""
        self.assertEqual(DEFAULT_GROUP_BY_TAG, 'beacon.location.path')

    def test_default_group_by_tag_entity(self):
        """Test DEFAULT_GROUP_BY_TAG_ENTITY constant"""
        self.assertEqual(DEFAULT_GROUP_BY_TAG_ENTITY, 'NOT_APPLICABLE')


if __name__ == '__main__':
    unittest.main()
