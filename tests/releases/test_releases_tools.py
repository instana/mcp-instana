"""
Unit tests for the ReleasesMCPTools class
"""

import asyncio
import json
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the releases logger and replace its handlers
releases_logger = logging.getLogger('src.releases.releases_tools')
releases_logger.handlers = []
releases_logger.addHandler(NullHandler())
releases_logger.propagate = False

# Suppress traceback printing for expected test exceptions
import traceback

original_print_exception = traceback.print_exception
original_print_exc = traceback.print_exc

def custom_print_exception(etype, value, tb, limit=None, file=None, chain=True):
    # Skip printing exceptions from the mock side_effect
    if isinstance(value, Exception) and str(value) == "Test error":
        return
    original_print_exception(etype, value, tb, limit, file, chain)

def custom_print_exc(limit=None, file=None, chain=True):
    # Just do nothing - this will suppress all traceback printing from print_exc
    pass

traceback.print_exception = custom_print_exception
traceback.print_exc = custom_print_exc

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Just pass the API client directly
            kwargs['api_client'] = self.releases_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
_original_instana_modules = {
    name: sys.modules.get(name)
    for name in [
        'instana_client',
        'instana_client.api',
        'instana_client.api.releases_api',
        'instana_client.models',
        'instana_client.models.release',
        'instana_client.configuration',
        'instana_client.api_client',
    ]
}

mock_instana_client = MagicMock()
mock_instana_api_pkg = MagicMock()
mock_instana_models_pkg = MagicMock()
mock_instana_configuration_pkg = MagicMock()
mock_instana_api_client_pkg = MagicMock()
mock_instana_releases_api_pkg = MagicMock()
mock_instana_release_model_pkg = MagicMock()

sys.modules['instana_client'] = mock_instana_client
sys.modules['instana_client.api'] = mock_instana_api_pkg
sys.modules['instana_client.api.releases_api'] = mock_instana_releases_api_pkg
sys.modules['instana_client.models'] = mock_instana_models_pkg
sys.modules['instana_client.models.release'] = mock_instana_release_model_pkg
sys.modules['instana_client.configuration'] = mock_instana_configuration_pkg
sys.modules['instana_client.api_client'] = mock_instana_api_client_pkg

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_releases_api = MagicMock()
mock_release = MagicMock()

# Add __name__ attribute to mock classes
mock_releases_api.__name__ = "ReleasesApi"
mock_release.__name__ = "Release"

mock_instana_configuration_pkg.Configuration = mock_configuration
mock_instana_api_client_pkg.ApiClient = mock_api_client
mock_instana_releases_api_pkg.ReleasesApi = mock_releases_api
mock_instana_release_model_pkg.Release = mock_release

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.releases.releases_tools import ReleasesMCPTools

for _module_name, _original_module in _original_instana_modules.items():
    if _original_module is not None:
        sys.modules[_module_name] = _original_module
    else:
        sys.modules.pop(_module_name, None)


class TestReleasesMCPTools(unittest.TestCase):
    """Test the ReleasesMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_releases_api.reset_mock()
        mock_release.reset_mock()

        # Create a test instance
        self.client = ReleasesMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )

        # Create a mock API client
        self.mock_api = MagicMock()
        self.client.releases_api = self.mock_api

    def test_initialization(self):
        """Test that the client initializes correctly"""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.io")

    def test_get_all_releases_success(self):
        """Test getting all releases successfully"""
        # Mock response
        mock_response = MagicMock()
        releases_data = [
            {"id": "rel-1", "name": "release-1", "start": 1000000},
            {"id": "rel-2", "name": "release-2", "start": 2000000},
            {"id": "rel-3", "name": "release-3", "start": 3000000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.get_all_releases())

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 3)
        self.assertEqual(len(result["releases"]), 3)
        self.assertEqual(result["releases"][0]["id"], "rel-1")

    def test_get_all_releases_with_time_range(self):
        """Test getting releases with time range filters"""
        # Mock response
        mock_response = MagicMock()
        releases_data = [
            {"id": "rel-1", "name": "release-1", "start": 1500000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call the method with time range
        result = asyncio.run(self.client.get_all_releases(
            from_time=1000000,
            to_time=2000000
        ))

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 1)

        # Verify API was called with correct parameters
        self.mock_api.get_all_releases_without_preload_content.assert_called_once_with(
            var_from=1000000,
            to=2000000
        )

    def test_get_all_releases_with_name_filter(self):
        """Test getting releases with name filter"""
        # Mock response with multiple releases
        mock_response = MagicMock()
        releases_data = [
            {"id": "rel-1", "name": "frontend-release-1", "start": 1000000},
            {"id": "rel-2", "name": "backend-release-2", "start": 2000000},
            {"id": "rel-3", "name": "frontend-release-3", "start": 3000000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call the method with name filter
        result = asyncio.run(self.client.get_all_releases(
            name_filter="frontend"
        ))

        # Verify the result - should only return frontend releases
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["releases"]), 2)
        self.assertTrue(all("frontend" in r["name"].lower() for r in result["releases"]))

    def test_get_all_releases_with_pagination(self):
        """Test getting releases with pagination"""
        # Mock response with 10 releases
        mock_response = MagicMock()
        releases_data = [
            {"id": f"rel-{i}", "name": f"release-{i}", "start": i * 1000000}
            for i in range(1, 11)
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call the method with pagination - page 1
        result = asyncio.run(self.client.get_all_releases(
            page_number=1,
            page_size=3
        ))

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 10)  # Total count
        self.assertEqual(result["page_number"], 1)
        self.assertEqual(result["page_size"], 3)
        self.assertEqual(result["total_pages"], 4)  # 10 items / 3 per page = 4 pages
        self.assertEqual(len(result["releases"]), 3)  # Current page items
        self.assertTrue(result["has_next_page"])
        self.assertFalse(result["has_previous_page"])

    def test_get_all_releases_pagination_page_2(self):
        """Test getting second page of releases"""
        # Mock response with 10 releases
        mock_response = MagicMock()
        releases_data = [
            {"id": f"rel-{i}", "name": f"release-{i}", "start": i * 1000000}
            for i in range(1, 11)
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call the method with pagination - page 2
        result = asyncio.run(self.client.get_all_releases(
            page_number=2,
            page_size=3
        ))

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["page_number"], 2)
        self.assertEqual(len(result["releases"]), 3)
        self.assertTrue(result["has_next_page"])
        self.assertTrue(result["has_previous_page"])
        # Verify we got the correct items (indices 3-5)
        self.assertEqual(result["releases"][0]["id"], "rel-4")

    def test_get_all_releases_pagination_last_page(self):
        """Test getting last page of releases"""
        # Mock response with 10 releases
        mock_response = MagicMock()
        releases_data = [
            {"id": f"rel-{i}", "name": f"release-{i}", "start": i * 1000000}
            for i in range(1, 11)
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call the method with pagination - last page
        result = asyncio.run(self.client.get_all_releases(
            page_number=4,
            page_size=3
        ))

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["page_number"], 4)
        self.assertEqual(len(result["releases"]), 1)  # Only 1 item on last page
        self.assertFalse(result["has_next_page"])
        self.assertTrue(result["has_previous_page"])

    def test_get_all_releases_pagination_invalid_page_number(self):
        """Test pagination with invalid page number"""
        # Mock response
        mock_response = MagicMock()
        mock_response.data = json.dumps([]).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call with invalid page number (0)
        result = asyncio.run(self.client.get_all_releases(
            page_number=0,
            page_size=10
        ))

        # Verify error response
        self.assertFalse(result["success"])
        self.assertIn("page_number must be >= 1", result["error"])

    def test_get_all_releases_pagination_invalid_page_size(self):
        """Test pagination with invalid page size"""
        # Mock response
        mock_response = MagicMock()
        mock_response.data = json.dumps([]).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call with invalid page size (0)
        result = asyncio.run(self.client.get_all_releases(
            page_number=1,
            page_size=0
        ))

        # Verify error response
        self.assertFalse(result["success"])
        self.assertIn("page_size must be >= 1", result["error"])

    def test_get_all_releases_combined_filters(self):
        """Test getting releases with combined filters and pagination"""
        # Mock response with multiple releases
        mock_response = MagicMock()
        releases_data = [
            {"id": "rel-1", "name": "frontend-release-1", "start": 1500000},
            {"id": "rel-2", "name": "backend-release-2", "start": 1600000},
            {"id": "rel-3", "name": "frontend-release-3", "start": 1700000},
            {"id": "rel-4", "name": "frontend-release-4", "start": 1800000},
            {"id": "rel-5", "name": "backend-release-5", "start": 1900000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call with time range, name filter, and pagination
        result = asyncio.run(self.client.get_all_releases(
            from_time=1000000,
            to_time=2000000,
            name_filter="frontend",
            page_number=1,
            page_size=2
        ))

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 3)  # 3 frontend releases
        self.assertEqual(len(result["releases"]), 2)  # Page size is 2
        self.assertEqual(result["total_pages"], 2)
        self.assertTrue(result["has_next_page"])

    def test_get_all_releases_empty_result(self):
        """Test getting releases with no results"""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.data = json.dumps([]).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.get_all_releases())

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["releases"]), 0)

    def test_get_all_releases_case_insensitive_filter(self):
        """Test that name filter is case-insensitive"""
        # Mock response
        mock_response = MagicMock()
        releases_data = [
            {"id": "rel-1", "name": "Frontend-Release", "start": 1000000},
            {"id": "rel-2", "name": "FRONTEND-APP", "start": 2000000},
            {"id": "rel-3", "name": "backend-release", "start": 3000000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call with lowercase filter
        result = asyncio.run(self.client.get_all_releases(
            name_filter="frontend"
        ))

        # Verify case-insensitive matching
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)

    def test_get_all_releases_error_handling(self):
        """Test error handling in get_all_releases"""
        # Mock API to raise an exception
        self.mock_api.get_all_releases_without_preload_content.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_all_releases())

        # Verify error response
        self.assertFalse(result["success"])
        self.assertIn("Failed to get releases", result["error"])

    def test_get_release_success(self):
        """Test getting a specific release successfully"""
        # Mock response
        mock_response = MagicMock()
        release_data = {
            "id": "rel-123",
            "name": "release-1",
            "start": 1000000,
            "applications": [{"name": "app1"}]
        }
        mock_response.data = json.dumps(release_data).encode('utf-8')
        self.mock_api.get_release_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.get_release(release_id="rel-123"))

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["release"]["id"], "rel-123")
        self.assertEqual(result["release"]["name"], "release-1")

    def test_get_release_error_handling(self):
        """Test error handling in get_release"""
        # Mock API to raise an exception
        self.mock_api.get_release_without_preload_content.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_release(release_id="rel-123"))

        # Verify error response
        self.assertFalse(result["success"])
        self.assertIn("Failed to get release", result["error"])
        self.assertEqual(result["release_id"], "rel-123")

    def test_create_release_success(self):
        """Test creating a release successfully"""
        # Mock Release.from_dict
        mock_release_obj = MagicMock()
        mock_release.from_dict.return_value = mock_release_obj

        # Mock response
        mock_response = MagicMock()
        release_data = {
            "id": "rel-new",
            "name": "new-release",
            "start": 1000000
        }
        mock_response.data = json.dumps(release_data).encode('utf-8')
        self.mock_api.post_release_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.create_release(
            name="new-release",
            start=1000000,
            applications=[{"name": "app1"}]
        ))

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["release"]["id"], "rel-new")

    def test_create_release_with_services(self):
        """Test creating a release with services"""
        # Mock Release.from_dict
        mock_release_obj = MagicMock()
        mock_release.from_dict.return_value = mock_release_obj

        # Mock response
        mock_response = MagicMock()
        release_data = {"id": "rel-new", "name": "new-release", "start": 1000000}
        mock_response.data = json.dumps(release_data).encode('utf-8')
        self.mock_api.post_release_without_preload_content.return_value = mock_response

        # Call the method with services
        result = asyncio.run(self.client.create_release(
            name="new-release",
            start=1000000,
            services=[{"name": "service1", "scopedTo": {}}]
        ))

        # Verify the result
        self.assertTrue(result["success"])

    def test_create_release_error_handling(self):
        """Test error handling in create_release"""
        # Mock Release.from_dict to return None
        mock_release.from_dict.return_value = None

        # Call the method
        result = asyncio.run(self.client.create_release(
            name="new-release",
            start=1000000
        ))

        # Verify error response
        self.assertFalse(result["success"])
        self.assertIn("Failed to create release", result["error"])

    def test_update_release_success(self):
        """Test updating a release successfully"""
        # Mock Release.from_dict
        mock_release_obj = MagicMock()
        mock_release.from_dict.return_value = mock_release_obj

        # Mock response
        mock_response = MagicMock()
        release_data = {
            "id": "rel-123",
            "name": "updated-release",
            "start": 2000000
        }
        mock_response.data = json.dumps(release_data).encode('utf-8')
        self.mock_api.put_release_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.update_release(
            release_id="rel-123",
            name="updated-release",
            start=2000000
        ))

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["release"]["name"], "updated-release")

    def test_update_release_error_handling(self):
        """Test error handling in update_release"""
        # Mock Release.from_dict to return None
        mock_release.from_dict.return_value = None

        # Call the method
        result = asyncio.run(self.client.update_release(
            release_id="rel-123",
            name="updated-release",
            start=2000000
        ))

        # Verify error response
        self.assertFalse(result["success"])
        self.assertIn("Failed to update release", result["error"])
        self.assertEqual(result["release_id"], "rel-123")

    def test_delete_release_success(self):
        """Test deleting a release successfully"""
        # Mock response
        mock_response = MagicMock()
        mock_response.data = b''
        self.mock_api.delete_release_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.delete_release(release_id="rel-123"))

        # Verify the result
        self.assertTrue(result["success"])
        self.assertIn("deleted successfully", result["message"])
        self.assertEqual(result["release_id"], "rel-123")

    def test_delete_release_error_handling(self):
        """Test error handling in delete_release"""
        # Mock API to raise an exception
        self.mock_api.delete_release_without_preload_content.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.delete_release(release_id="rel-123"))

        # Verify error response
        self.assertFalse(result["success"])
        self.assertIn("Failed to delete release", result["error"])
        self.assertEqual(result["release_id"], "rel-123")

    def test_get_all_releases_pagination_hint(self):
        """Test that pagination hint is provided for large result sets"""
        # Mock response with many releases
        mock_response = MagicMock()
        releases_data = [
            {"id": f"rel-{i}", "name": f"release-{i}", "start": i * 1000000}
            for i in range(1, 101)  # 100 releases
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        self.mock_api.get_all_releases_without_preload_content.return_value = mock_response

        # Call without pagination
        result = asyncio.run(self.client.get_all_releases())

        # Verify pagination hint is present
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 100)
        self.assertIn("pagination_hint", result)
        self.assertIn("Consider using pagination", result["pagination_hint"])


if __name__ == '__main__':
    unittest.main()
