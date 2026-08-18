"""
Unit tests for Synthetic Settings Module

Tests get_synthetic_test, get_synthetic_tests, get_locations,
get_location_by_id, and get_all_datacenters.
"""

import asyncio
import json
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            kwargs['api_client'] = self.settings_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.synthetic_settings_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.types'] = MagicMock()
sys.modules['fastmcp'] = MagicMock()

mock_settings_api = MagicMock()
mock_settings_api.__name__ = "SyntheticSettingsApi"
sys.modules['instana_client.api.synthetic_settings_api'].SyntheticSettingsApi = mock_settings_api

with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.synthetic.synthetic_settings import SyntheticSettingsMCPTools


SAMPLE_TESTS = [
    {"id": "test-001", "label": "Login Flow", "description": "End-to-end login check"},
    {"id": "test-002", "label": "API Health Check", "description": "REST API smoke test"},
]

SAMPLE_LOCATIONS = [
    {
        "id": "loc-managed-1",
        "label": "instana-aws-us-east-1",
        "displayLabel": "us-east-1(N. Virginia)",
        "locationType": "Managed",
        "status": "Online",
        "geoPoint": {"cityName": "Ashburn", "countryName": "United States", "latitude": 39.0, "longitude": -77.5},
        "customProperties": {"datacenterFlag": "aws-us-east-1-virginia"},
        "totalTests": 10,
    },
    {
        "id": "loc-private-1",
        "label": "my-private-pop",
        "displayLabel": "My Private PoP",
        "locationType": "Private",
        "status": "Online",
        "geoPoint": {},
        "totalTests": 3,
    },
    {
        "id": "loc-managed-2",
        "label": "instana-aws-ap-south-1",
        "displayLabel": "ap-south-1(Mumbai)",
        "locationType": "Managed",
        "status": "Offline",
        "geoPoint": {"cityName": "Mumbai", "countryName": "India"},
        "totalTests": 5,
    },
]


def _ok_response(payload):
    """Helper: build a mock 200 response with JSON payload."""
    r = Mock()
    r.status = 200
    r.data = json.dumps(payload).encode('utf-8')
    r.headers = {'Content-Type': 'application/json; charset=utf-8'}
    return r


def _error_response(status, body=b'Error'):
    r = Mock()
    r.status = status
    r.data = body
    r.headers = {'Content-Type': 'text/plain'}
    return r


class TestSyntheticSettingsMCPTools(unittest.TestCase):
    """Unit tests for SyntheticSettingsMCPTools."""

    def setUp(self):
        self.settings_api = MagicMock()
        self.client = SyntheticSettingsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.settings_api = self.settings_api

    def test_initialization(self):
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.io")

    def test_get_synthetic_test_by_id_success(self):
        """Direct test_id lookup should return the test record."""
        self.settings_api.get_synthetic_test_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_TESTS[0])
        )

        result = asyncio.run(self.client.get_synthetic_test(test_id="test-001"))

        self.assertEqual(result["id"], "test-001")
        self.assertEqual(result["label"], "Login Flow")
        self.settings_api.get_synthetic_test_without_preload_content.assert_called_once_with(id="test-001")

    def test_get_synthetic_test_by_name_success(self):
        """Name resolution should list all tests, find the match, then fetch by ID."""
        self.settings_api.get_synthetic_tests_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_TESTS)
        )
        self.settings_api.get_synthetic_test_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_TESTS[1])
        )

        result = asyncio.run(self.client.get_synthetic_test(test_name="API Health Check"))

        self.assertEqual(result["id"], "test-002")
        self.settings_api.get_synthetic_test_without_preload_content.assert_called_once_with(id="test-002")

    def test_get_synthetic_test_by_name_case_insensitive(self):
        """Name resolution should be case-insensitive."""
        self.settings_api.get_synthetic_tests_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_TESTS)
        )
        self.settings_api.get_synthetic_test_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_TESTS[0])
        )

        result = asyncio.run(self.client.get_synthetic_test(test_name="login flow"))

        self.assertEqual(result["id"], "test-001")

    def test_get_synthetic_test_name_not_found(self):
        """Unmatched name should return error with available_test_names."""
        self.settings_api.get_synthetic_tests_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_TESTS)
        )

        result = asyncio.run(self.client.get_synthetic_test(test_name="Unknown Test"))

        self.assertIn("error", result)
        self.assertIn("Unknown Test", result["error"])
        self.assertIn("available_test_names", result)
        self.assertIn("Login Flow", result["available_test_names"])

    def test_get_synthetic_test_no_args(self):
        """Calling without test_id or test_name should return a validation error."""
        result = asyncio.run(self.client.get_synthetic_test())

        self.assertIn("error", result)
        self.assertIn("required", result["error"].lower())

    def test_get_synthetic_test_http_error(self):
        """HTTP error from get-by-id should propagate as error dict."""
        self.settings_api.get_synthetic_test_without_preload_content = Mock(
            return_value=_error_response(404)
        )

        result = asyncio.run(self.client.get_synthetic_test(test_id="missing-id"))

        self.assertIn("error", result)
        self.assertIn("HTTP 404", result["error"])

    def test_get_synthetic_test_exception(self):
        """Exception from API should be caught and returned as error dict."""
        self.settings_api.get_synthetic_test_without_preload_content = Mock(
            side_effect=RuntimeError("Network error")
        )

        result = asyncio.run(self.client.get_synthetic_test(test_id="test-001"))

        self.assertIn("error", result)
        self.assertIn("Network error", result["error"])

    def test_get_synthetic_tests_no_filters(self):
        """No filters should return all tests."""
        self.settings_api.get_synthetic_tests_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_TESTS)
        )

        result = asyncio.run(self.client.get_synthetic_tests())

        self.assertIn("items", result)
        self.assertIn("count", result)
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["items"]), 2)

    def test_get_synthetic_tests_with_limit(self):
        """Limit param should be forwarded to the API."""
        self.settings_api.get_synthetic_tests_without_preload_content = Mock(
            return_value=_ok_response([SAMPLE_TESTS[0]])
        )

        result = asyncio.run(self.client.get_synthetic_tests(limit=1))

        self.settings_api.get_synthetic_tests_without_preload_content.assert_called_once_with(
            application_id=None,
            location_id=None,
            credential_name=None,
            sort=None,
            offset=None,
            limit=1,
            filter=None,
        )
        self.assertEqual(result["count"], 1)

    def test_get_synthetic_tests_filter_auto_wrapped(self):
        """Filter without braces should be auto-wrapped to {filter} syntax."""
        self.settings_api.get_synthetic_tests_without_preload_content = Mock(
            return_value=_ok_response([SAMPLE_TESTS[0]])
        )

        result = asyncio.run(self.client.get_synthetic_tests(filter_param="label=test-march3-new"))

        self.settings_api.get_synthetic_tests_without_preload_content.assert_called_once_with(
            application_id=None,
            location_id=None,
            credential_name=None,
            sort=None,
            offset=None,
            limit=None,
            filter="{label=test-march3-new}",
        )
        self.assertEqual(result["count"], 1)

    def test_get_synthetic_tests_filter_already_wrapped(self):
        """Filter already wrapped in braces should be passed through unchanged."""
        self.settings_api.get_synthetic_tests_without_preload_content = Mock(
            return_value=_ok_response([SAMPLE_TESTS[0]])
        )

        result = asyncio.run(self.client.get_synthetic_tests(filter_param="{label=test-march3-new}"))

        self.settings_api.get_synthetic_tests_without_preload_content.assert_called_once_with(
            application_id=None,
            location_id=None,
            credential_name=None,
            sort=None,
            offset=None,
            limit=None,
            filter="{label=test-march3-new}",
        )
        self.assertEqual(result["count"], 1)

    def test_get_synthetic_tests_http_error(self):
        self.settings_api.get_synthetic_tests_without_preload_content = Mock(
            return_value=_error_response(500)
        )

        result = asyncio.run(self.client.get_synthetic_tests())

        self.assertIn("error", result)
        self.assertIn("HTTP 500", result["error"])

    def test_get_synthetic_tests_exception(self):
        self.settings_api.get_synthetic_tests_without_preload_content = Mock(
            side_effect=Exception("API unavailable")
        )

        result = asyncio.run(self.client.get_synthetic_tests())

        self.assertIn("error", result)
        self.assertIn("API unavailable", result["error"])

    def test_get_locations_no_filters(self):
        """No filters should return all locations."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )

        result = asyncio.run(self.client.get_locations())

        self.assertIn("items", result)
        self.assertIn("count", result)
        self.assertIn("filters_applied", result)
        self.assertEqual(result["count"], 3)

    def test_get_locations_filter_managed(self):
        """location_type='Managed' should return only Managed locations."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )

        result = asyncio.run(self.client.get_locations(location_type="Managed"))

        self.assertEqual(result["count"], 2)
        for loc in result["items"]:
            self.assertEqual(loc["locationType"], "Managed")

    def test_get_locations_filter_private(self):
        """location_type='Private' should return only Private locations."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )

        result = asyncio.run(self.client.get_locations(location_type="Private"))

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["locationType"], "Private")

    def test_get_locations_filter_online_status(self):
        """status='Online' filter should return only Online locations."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )

        result = asyncio.run(self.client.get_locations(status="Online"))

        self.assertEqual(result["count"], 2)
        for loc in result["items"]:
            self.assertEqual(loc["status"], "Online")

    def test_get_locations_combined_filters(self):
        """Combining location_type and status should apply both post-fetch filters."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )

        result = asyncio.run(self.client.get_locations(location_type="Managed", status="Online"))

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["id"], "loc-managed-1")

    def test_get_locations_http_error(self):
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_error_response(403)
        )

        result = asyncio.run(self.client.get_locations())

        self.assertIn("error", result)
        self.assertIn("HTTP 403", result["error"])

    def test_get_locations_exception(self):
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            side_effect=Exception("Timeout")
        )

        result = asyncio.run(self.client.get_locations())

        self.assertIn("error", result)

    def test_get_location_by_id_success(self):
        """Direct location_id lookup should return the location record."""
        self.settings_api.get_synthetic_location_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS[0])
        )

        result = asyncio.run(self.client.get_location_by_id(location_id="loc-managed-1"))

        self.assertEqual(result["id"], "loc-managed-1")
        self.settings_api.get_synthetic_location_without_preload_content.assert_called_once_with(
            id="loc-managed-1"
        )

    def test_get_location_by_name_via_label(self):
        """Name resolution via label field should work case-insensitively."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )
        self.settings_api.get_synthetic_location_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS[0])
        )

        result = asyncio.run(
            self.client.get_location_by_id(location_name="INSTANA-AWS-US-EAST-1")
        )

        self.assertEqual(result["id"], "loc-managed-1")

    def test_get_location_by_name_via_display_label(self):
        """Name resolution via displayLabel should work."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )
        self.settings_api.get_synthetic_location_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS[2])
        )

        result = asyncio.run(
            self.client.get_location_by_id(location_name="ap-south-1(Mumbai)")
        )

        self.assertEqual(result["id"], "loc-managed-2")

    def test_get_location_by_name_not_found(self):
        """Unmatched location name should return error with available_location_names."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )

        result = asyncio.run(self.client.get_location_by_id(location_name="nonexistent"))

        self.assertIn("error", result)
        self.assertIn("available_location_names", result)

    def test_get_location_by_id_no_args(self):
        """Calling without location_id or location_name should return error."""
        result = asyncio.run(self.client.get_location_by_id())

        self.assertIn("error", result)

    def test_get_location_by_id_http_error(self):
        self.settings_api.get_synthetic_location_without_preload_content = Mock(
            return_value=_error_response(404)
        )

        result = asyncio.run(self.client.get_location_by_id(location_id="missing"))

        self.assertIn("error", result)
        self.assertIn("HTTP 404", result["error"])


    def test_get_all_datacenters_no_filter(self):
        """Should return only Managed locations with total_online count."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )

        result = asyncio.run(self.client.get_all_datacenters())

        self.assertIn("items", result)
        self.assertIn("count", result)
        self.assertIn("total_online", result)
        self.assertEqual(result["count"], 2)  # two Managed locations
        self.assertEqual(result["total_online"], 1)  # one Online among those
        for dc in result["items"]:
            self.assertEqual(dc["locationType"], "Managed")

    def test_get_all_datacenters_online_only(self):
        """status='Online' should restrict to Online Managed locations."""
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_ok_response(SAMPLE_LOCATIONS)
        )

        result = asyncio.run(self.client.get_all_datacenters(status="Online"))

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["id"], "loc-managed-1")

    def test_get_all_datacenters_http_error(self):
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            return_value=_error_response(500)
        )

        result = asyncio.run(self.client.get_all_datacenters())

        self.assertIn("error", result)

    def test_get_all_datacenters_exception(self):
        self.settings_api.get_synthetic_locations_without_preload_content = Mock(
            side_effect=Exception("DB error")
        )

        result = asyncio.run(self.client.get_all_datacenters())

        self.assertIn("error", result)
        self.assertIn("DB error", result["error"])


if __name__ == '__main__':
    unittest.main()
