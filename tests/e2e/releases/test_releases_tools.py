"""
E2E tests for Releases MCP Tools
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


# Mock the ApiException since instana_client is not available in test environment
class ApiException(Exception):
    def __init__(self, status=None, reason=None, *args, **kwargs):
        self.status = status
        self.reason = reason
        super().__init__(*args, **kwargs)


api_module_name = "instana_client.api.releases_api"
models_module_name = "instana_client.models.release"

if api_module_name not in sys.modules:
    stub_api_module = types.ModuleType(api_module_name)

    class ReleasesApi:
        pass

    stub_api_module.ReleasesApi = ReleasesApi
    sys.modules[api_module_name] = stub_api_module

if models_module_name not in sys.modules:
    stub_models_module = types.ModuleType(models_module_name)

    class Release:
        @classmethod
        def from_dict(cls, data):
            instance = cls()
            for key, value in data.items():
                setattr(instance, key, value)
            return instance

    stub_models_module.Release = Release
    sys.modules[models_module_name] = stub_models_module

def create_releases_client(instana_credentials):
    module = importlib.import_module("src.releases.releases_tools")
    module = importlib.reload(module)
    releases_mcp_tools = module.ReleasesMCPTools
    return releases_mcp_tools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"]
    )


class TestReleasesMCPToolsE2E:
    """End-to-end tests for Releases MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        """Test initialization of the ReleasesMCPTools client."""

        # Create the client
        client = create_releases_client(instana_credentials)

        # Verify the client was created successfully
        assert client is not None
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_success(self, instana_credentials):
        """Test getting all releases successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()

        # Mock response
        mock_response = MagicMock()
        import json
        releases_data = [
            {"id": "rel-1", "name": "release-1", "start": 1000000},
            {"id": "rel-2", "name": "release-2", "start": 2000000},
            {"id": "rel-3", "name": "release-3", "start": 3000000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        mock_api_client.get_all_releases_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method
        result = await client.get_all_releases(api_client=mock_api_client)

        # Verify the result
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["releases"]) == 3
        assert result["releases"][0]["id"] == "rel-1"

        # Verify the API was called correctly
        mock_api_client.get_all_releases_without_preload_content.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_with_time_range(self, instana_credentials):
        """Test getting releases with time range filters."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()

        # Mock response
        mock_response = MagicMock()
        import json
        releases_data = [
            {"id": "rel-1", "name": "release-1", "start": 1500000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        mock_api_client.get_all_releases_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method with time range
        result = await client.get_all_releases(
            from_time=1000000,
            to_time=2000000,
            api_client=mock_api_client
        )

        # Verify the result
        assert result["success"] is True
        assert result["count"] == 1

        # Verify API was called with correct parameters
        call_args = mock_api_client.get_all_releases_without_preload_content.call_args
        assert call_args[1]["var_from"] == 1000000
        assert call_args[1]["to"] == 2000000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_with_name_filter(self, instana_credentials):
        """Test getting releases with name filter."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()

        # Mock response with multiple releases
        mock_response = MagicMock()
        import json
        releases_data = [
            {"id": "rel-1", "name": "frontend-release-1", "start": 1000000},
            {"id": "rel-2", "name": "backend-release-2", "start": 2000000},
            {"id": "rel-3", "name": "frontend-release-3", "start": 3000000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        mock_api_client.get_all_releases_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method with name filter
        result = await client.get_all_releases(
            name_filter="frontend",
            api_client=mock_api_client
        )

        # Verify the result - should only return frontend releases
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["releases"]) == 2
        assert all("frontend" in r["name"].lower() for r in result["releases"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_with_pagination(self, instana_credentials):
        """Test getting releases with pagination."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()

        # Mock response with 10 releases
        mock_response = MagicMock()
        import json
        releases_data = [
            {"id": f"rel-{i}", "name": f"release-{i}", "start": i * 1000000}
            for i in range(1, 11)
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        mock_api_client.get_all_releases_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method with pagination - page 1
        result = await client.get_all_releases(
            page_number=1,
            page_size=3,
            api_client=mock_api_client
        )

        # Verify the result
        assert result["success"] is True
        assert result["count"] == 10  # Total count
        assert result["page_number"] == 1
        assert result["page_size"] == 3
        assert result["total_pages"] == 4  # 10 items / 3 per page = 4 pages
        assert len(result["releases"]) == 3  # Current page items
        assert result["has_next_page"] is True
        assert result["has_previous_page"] is False

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_pagination_navigation(self, instana_credentials):
        """Test pagination navigation through multiple pages."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()

        # Mock response with 10 releases
        mock_response = MagicMock()
        import json
        releases_data = [
            {"id": f"rel-{i}", "name": f"release-{i}", "start": i * 1000000}
            for i in range(1, 11)
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        mock_api_client.get_all_releases_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test page 2
        result = await client.get_all_releases(
            page_number=2,
            page_size=3,
            api_client=mock_api_client
        )

        assert result["page_number"] == 2
        assert result["has_next_page"] is True
        assert result["has_previous_page"] is True
        assert result["releases"][0]["id"] == "rel-4"

        # Test last page
        result = await client.get_all_releases(
            page_number=4,
            page_size=3,
            api_client=mock_api_client
        )

        assert result["page_number"] == 4
        assert len(result["releases"]) == 1  # Only 1 item on last page
        assert result["has_next_page"] is False
        assert result["has_previous_page"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_combined_filters(self, instana_credentials):
        """Test getting releases with combined filters and pagination."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()

        # Mock response with multiple releases
        mock_response = MagicMock()
        import json
        releases_data = [
            {"id": "rel-1", "name": "frontend-release-1", "start": 1500000},
            {"id": "rel-2", "name": "backend-release-2", "start": 1600000},
            {"id": "rel-3", "name": "frontend-release-3", "start": 1700000},
            {"id": "rel-4", "name": "frontend-release-4", "start": 1800000},
            {"id": "rel-5", "name": "backend-release-5", "start": 1900000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        mock_api_client.get_all_releases_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test with time range, name filter, and pagination
        result = await client.get_all_releases(
            from_time=1000000,
            to_time=2000000,
            name_filter="frontend",
            page_number=1,
            page_size=2,
            api_client=mock_api_client
        )

        # Verify the result
        assert result["success"] is True
        assert result["count"] == 3  # 3 frontend releases
        assert len(result["releases"]) == 2  # Page size is 2
        assert result["total_pages"] == 2
        assert result["has_next_page"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_invalid_pagination(self, instana_credentials):
        """Test pagination with invalid parameters."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()

        mock_response = MagicMock()
        import json
        mock_response.data = json.dumps([]).encode('utf-8')
        mock_api_client.get_all_releases_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test with invalid page number
        result = await client.get_all_releases(
            page_number=0,
            page_size=10,
            api_client=mock_api_client
        )

        assert result["success"] is False
        assert "page_number must be >= 1" in result["error"]

        # Test with invalid page size
        result = await client.get_all_releases(
            page_number=1,
            page_size=0,
            api_client=mock_api_client
        )

        assert result["success"] is False
        assert "page_size must be >= 1" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_error_handling(self, instana_credentials):
        """Test error handling in get_all_releases."""

        # Create mock API client that raises an exception
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()
        mock_api_client.get_all_releases_without_preload_content.side_effect = Exception("API Error")

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method
        result = await client.get_all_releases(api_client=mock_api_client)

        # Verify error response
        assert result["success"] is False
        assert "Failed to get releases" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_release_success(self, instana_credentials):
        """Test getting a specific release successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_release_without_preload_content = MagicMock()

        # Mock response
        mock_response = MagicMock()
        import json
        release_data = {
            "id": "rel-123",
            "name": "release-1",
            "start": 1000000,
            "applications": [{"name": "app1"}]
        }
        mock_response.data = json.dumps(release_data).encode('utf-8')
        mock_api_client.get_release_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method
        result = await client.get_release(
            release_id="rel-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert result["success"] is True
        assert result["release"]["id"] == "rel-123"
        assert result["release"]["name"] == "release-1"

        # Verify the API was called correctly
        mock_api_client.get_release_without_preload_content.assert_called_once_with(
            release_id="rel-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_release_error_handling(self, instana_credentials):
        """Test error handling in get_release."""

        # Create mock API client that raises an exception
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_release_without_preload_content = MagicMock()
        mock_api_client.get_release_without_preload_content.side_effect = Exception("API Error")

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method
        result = await client.get_release(
            release_id="rel-123",
            api_client=mock_api_client
        )

        # Verify error response
        assert result["success"] is False
        assert "Failed to get release" in result["error"]
        assert result["release_id"] == "rel-123"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_release_success(self, instana_credentials):
        """Test creating a release successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.post_release_without_preload_content = MagicMock()

        # Mock response
        mock_response = MagicMock()
        import json
        release_data = {
            "id": "rel-new",
            "name": "new-release",
            "start": 1000000
        }
        mock_response.data = json.dumps(release_data).encode('utf-8')
        mock_api_client.post_release_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method
        result = await client.create_release(
            name="new-release",
            start=1000000,
            applications=[{"name": "app1"}],
            api_client=mock_api_client
        )

        # Verify the result
        assert result["success"] is True
        assert result["release"]["id"] == "rel-new"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_release_with_services(self, instana_credentials):
        """Test creating a release with services."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.post_release_without_preload_content = MagicMock()

        # Mock response
        mock_response = MagicMock()
        import json
        release_data = {"id": "rel-new", "name": "new-release", "start": 1000000}
        mock_response.data = json.dumps(release_data).encode('utf-8')
        mock_api_client.post_release_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method with services
        result = await client.create_release(
            name="new-release",
            start=1000000,
            services=[{"name": "service1", "scopedTo": {"applications": [{"name": "test-app"}]}}],
            api_client=mock_api_client
        )

        # Verify the result
        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_release_success(self, instana_credentials):
        """Test updating a release successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.put_release_without_preload_content = MagicMock()

        # Mock response
        mock_response = MagicMock()
        import json
        release_data = {
            "id": "rel-123",
            "name": "updated-release",
            "start": 2000000
        }
        mock_response.data = json.dumps(release_data).encode('utf-8')
        mock_api_client.put_release_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method
        result = await client.update_release(
            release_id="rel-123",
            name="updated-release",
            start=2000000,
            api_client=mock_api_client
        )

        # Verify the result
        assert result["success"] is True
        assert result["release"]["name"] == "updated-release"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_release_success(self, instana_credentials):
        """Test deleting a release successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.delete_release_without_preload_content = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.data = b''
        mock_api_client.delete_release_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method
        result = await client.delete_release(
            release_id="rel-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert result["success"] is True
        assert "deleted successfully" in result["message"]
        assert result["release_id"] == "rel-123"

        # Verify the API was called correctly
        mock_api_client.delete_release_without_preload_content.assert_called_once_with(
            release_id="rel-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_release_error_handling(self, instana_credentials):
        """Test error handling in delete_release."""

        # Create mock API client that raises an exception
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.delete_release_without_preload_content = MagicMock()
        mock_api_client.delete_release_without_preload_content.side_effect = Exception("API Error")

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test the method
        result = await client.delete_release(
            release_id="rel-123",
            api_client=mock_api_client
        )

        # Verify error response
        assert result["success"] is False
        assert "Failed to delete release" in result["error"]
        assert result["release_id"] == "rel-123"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_case_insensitive_name_filter(self, instana_credentials):
        """Test that name filter is case-insensitive."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()

        # Mock response
        mock_response = MagicMock()
        import json
        releases_data = [
            {"id": "rel-1", "name": "Frontend-Release", "start": 1000000},
            {"id": "rel-2", "name": "FRONTEND-APP", "start": 2000000},
            {"id": "rel-3", "name": "backend-release", "start": 3000000}
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        mock_api_client.get_all_releases_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test with lowercase filter
        result = await client.get_all_releases(
            name_filter="frontend",
            api_client=mock_api_client
        )

        # Verify case-insensitive matching
        assert result["success"] is True
        assert result["count"] == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_pagination_hint_for_large_results(self, instana_credentials):
        """Test that pagination hint is provided for large result sets."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_all_releases_without_preload_content = MagicMock()

        # Mock response with many releases
        mock_response = MagicMock()
        import json
        releases_data = [
            {"id": f"rel-{i}", "name": f"release-{i}", "start": i * 1000000}
            for i in range(1, 101)  # 100 releases
        ]
        mock_response.data = json.dumps(releases_data).encode('utf-8')
        mock_api_client.get_all_releases_without_preload_content.return_value = mock_response

        # Create the client
        client = create_releases_client(instana_credentials)

        # Test without pagination
        result = await client.get_all_releases(api_client=mock_api_client)

        # Verify pagination hint is present
        assert result["success"] is True
        assert result["count"] == 100
        assert "pagination_hint" in result
        assert "Consider using pagination" in result["pagination_hint"]
