"""
E2E tests for Application Resources MCP Tools with patched API methods
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    mock_client = MagicMock()
    mock_client.get_application_endpoints = MagicMock()
    mock_client.get_applications = MagicMock()
    mock_client.get_application_services = MagicMock()
    mock_client.get_services = MagicMock()
    return mock_client


class TestApplicationResourcesE2E:
    """End-to-end tests for Application Resources MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.skip(reason="Module already imported, can't test initialization errors")
    async def test_client_initialization_error_handling(self):
        """Test client initialization error handling."""
        # This test is skipped because the module is already imported
        # and we can't properly test initialization errors in this context
        pass

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.skip(reason="Module already imported, can't test import errors")
    async def test_import_error_handling(self):
        """Test import error handling during client initialization."""
        # This test is skipped because the module is already imported
        # and we can't properly test import errors in this context
        pass

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_endpoints(self, instana_credentials):
        """Test get_application_endpoints with patched API."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_application_endpoints') as mock_method:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "endpoints": [{"id": "endpoint-1", "name": "Test Endpoint"}]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_application_endpoints()

            # Verify the result
            assert isinstance(result, dict)
            assert "endpoints" in result
            assert result["endpoints"][0]["id"] == "endpoint-1"
            assert result["endpoints"][0]["name"] == "Test Endpoint"
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_endpoints_with_params(self, instana_credentials):
        """Test get_application_endpoints with all parameters."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_application_endpoints') as mock_method:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {"endpoints": []}
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method with all parameters
            result = await client.get_application_endpoints(
                name_filter="test-endpoint",
                types=["HTTP", "GRPC"],
                technologies=["Java", "Python"],
                window_size=3600000,
                to_time=1234567890,
                page=1,
                page_size=10,
                application_boundary_scope="INBOUND"
            )

            # Verify the result
            assert isinstance(result, dict)
            mock_method.assert_called_once()
            # Check that parameters were passed correctly
            args, kwargs = mock_method.call_args
            assert kwargs["name_filter"] == "test-endpoint"
            assert kwargs["types"] == ["HTTP", "GRPC"]
            assert kwargs["technologies"] == ["Java", "Python"]
            assert kwargs["window_size"] == 3600000
            assert kwargs["to"] == 1234567890
            assert kwargs["page"] == 1
            assert kwargs["page_size"] == 10
            assert kwargs["application_boundary_scope"] == "INBOUND"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_endpoints_error_handling(self, instana_credentials):
        """Test error handling in get_application_endpoints."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_application_endpoints',
                  side_effect=Exception("API Error")):

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_application_endpoints()

            # Verify the result
            assert isinstance(result, dict)
            assert "error" in result
            assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications(self, instana_credentials):
        """Test get_applications with patched API."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_applications') as mock_method:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "items": [
                    {"label": "App 1"},
                    {"label": "App 2"},
                    {"label": "App 3"}
                ]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_applications()

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 3
            assert "App 1" in result
            assert "App 2" in result
            assert "App 3" in result
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications_with_object_items(self, instana_credentials):
        """Test get_applications with object items."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_applications') as mock_method:
            # Create mock items
            mock_item1 = MagicMock()
            mock_item1.label = "App 1"
            mock_item2 = MagicMock()
            mock_item2.label = "App 2"

            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "items": [mock_item1, mock_item2]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_applications()

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 2
            assert "App 1" in result
            assert "App 2" in result
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications_with_params(self, instana_credentials):
        """Test get_applications with parameters and patched API."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_applications') as mock_method:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {"items": []}
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method with parameters
            result = await client.get_applications(
                name_filter="test-app",
                window_size=3600000,
                to_time=1234567890,
                page=1,
                page_size=10,
                application_boundary_scope="ALL"
            )

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 0
            mock_method.assert_called_once()
            # Check that parameters were passed correctly
            args, kwargs = mock_method.call_args
            assert kwargs["name_filter"] == "test-app"
            assert kwargs["window_size"] == 3600000
            assert kwargs["to"] == 1234567890
            assert kwargs["page"] == 1
            assert kwargs["page_size"] == 10
            assert kwargs["application_boundary_scope"] == "ALL"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications_error_handling(self, instana_credentials):
        """Test error handling in get_applications with patched API."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_applications',
                  side_effect=Exception("API Error")):

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_applications()

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 1
            assert "Error:" in result[0]
            assert "API Error" in result[0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications_more_than_15_items(self, instana_credentials):
        """Test get_applications with more than 15 items (should limit to 15)."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_applications') as mock_method:
            # Set up the mock response with 20 items
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "items": [{"label": f"App {i}"} for i in range(1, 21)]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_applications()

            # Verify the result
            assert isinstance(result, list)
            assert len(result) == 15  # Should limit to 15
            # Check that items are sorted alphabetically
            assert result == sorted(result)
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_services(self, instana_credentials):
        """Test get_application_services with patched API."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_application_services') as mock_method:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "items": [
                    {
                        "id": "service-1",
                        "label": "Test Service 1",
                        "technologies": ["Java", "Spring"]
                    },
                    {
                        "id": "service-2",
                        "label": "Test Service 2",
                        "technologies": ["Python", "Django"]
                    }
                ]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_application_services()

            # Verify the result
            assert isinstance(result, dict)
            assert "services" in result
            assert "service_labels" in result
            assert "message" in result
            assert len(result["services"]) == 2
            assert result["services"][0]["id"] == "service-1"
            assert result["services"][0]["label"] == "Test Service 1"
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_services_with_object_items(self, instana_credentials):
        """Test get_application_services with object items."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_application_services') as mock_method:
            # Create mock items
            mock_item1 = MagicMock()
            mock_item1.id = "service-1"
            mock_item1.label = "Service 1"
            mock_item1.technologies = ["Java"]

            mock_item2 = MagicMock()
            mock_item2.id = "service-2"
            mock_item2.label = "Service 2"
            mock_item2.technologies = ["Python"]

            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "items": [mock_item1, mock_item2]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_application_services()

            # Verify the result
            assert isinstance(result, dict)
            assert "services" in result
            assert len(result["services"]) == 2
            assert result["services"][0]["id"] == "service-1"
            assert result["services"][0]["label"] == "Service 1"
            assert result["services"][1]["id"] == "service-2"
            assert result["services"][1]["label"] == "Service 2"
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_services_with_params(self, instana_credentials):
        """Test get_application_services with all parameters."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_application_services') as mock_method:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {"items": []}
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method with all parameters
            result = await client.get_application_services(
                name_filter="test-service",
                window_size=3600000,
                to_time=1234567890,
                page=1,
                page_size=10,
                application_boundary_scope="INBOUND",
                include_snapshot_ids=True
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "services" in result
            assert len(result["services"]) == 0
            mock_method.assert_called_once()
            # Check that parameters were passed correctly
            args, kwargs = mock_method.call_args
            assert kwargs["name_filter"] == "test-service"
            assert kwargs["window_size"] == 3600000
            assert kwargs["to"] == 1234567890
            assert kwargs["page"] == 1
            assert kwargs["page_size"] == 10
            assert kwargs["application_boundary_scope"] == "INBOUND"
            assert kwargs["include_snapshot_ids"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_services_error_handling(self, instana_credentials):
        """Test error handling in get_application_services."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_application_services',
                  side_effect=Exception("API Error")):

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_application_services()

            # Verify the result
            assert isinstance(result, dict)
            assert "error" in result
            assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_services_more_than_15_items(self, instana_credentials):
        """Test get_application_services with more than 15 items (should limit to 15)."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_application_services') as mock_method:
            # Set up the mock response with 20 items
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "items": [
                    {"id": f"service-{i}", "label": f"Service {i}", "technologies": ["Java"]}
                    for i in range(1, 21)
                ]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_application_services()

            # Verify the result
            assert isinstance(result, dict)
            assert len(result["services"]) == 15  # Should limit to 15
            assert result["total_available"] == 20
            assert result["showing"] == 15
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_services(self, instana_credentials):
        """Test get_services with patched API."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_services') as mock_method:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "items": [
                    {"label": "Service 1"},
                    {"label": "Service 2"},
                    {"label": "Service 3"}
                ]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_services()

            # Verify the result
            assert isinstance(result, str)
            assert "Services found in your environment:" in result
            assert "Service 1" in result
            assert "Service 2" in result
            assert "Service 3" in result
            assert "Showing 3 out of 3 total services." in result
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_services_with_object_items(self, instana_credentials):
        """Test get_services with object items."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_services') as mock_method:
            # Create mock items
            mock_item1 = MagicMock()
            mock_item1.label = "Service 1"
            mock_item2 = MagicMock()
            mock_item2.label = "Service 2"

            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "items": [mock_item1, mock_item2]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_services()

            # Verify the result
            assert isinstance(result, str)
            assert "Service 1" in result
            assert "Service 2" in result
            mock_method.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_services_with_params(self, instana_credentials):
        """Test get_services with all parameters."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_services') as mock_method:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {"items": []}
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method with all parameters
            result = await client.get_services(
                name_filter="test-service",
                window_size=3600000,
                to_time=1234567890,
                page=1,
                page_size=10,
                include_snapshot_ids=True
            )

            # Verify the result
            assert isinstance(result, str)
            assert "Services found in your environment:" in result
            assert "Showing 0 out of 0 total services." in result
            mock_method.assert_called_once()
            # Check that parameters were passed correctly
            args, kwargs = mock_method.call_args
            assert kwargs["name_filter"] == "test-service"
            assert kwargs["window_size"] == 3600000
            assert kwargs["to"] == 1234567890
            assert kwargs["page"] == 1
            assert kwargs["page_size"] == 10
            assert kwargs["include_snapshot_ids"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_services_error_handling(self, instana_credentials):
        """Test error handling in get_services."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_services',
                  side_effect=Exception("API Error")):

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_services()

            # Verify the result
            assert isinstance(result, str)
            assert "Error:" in result
            assert "API Error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_services_more_than_10_items(self, instana_credentials):
        """Test get_services with more than 10 items (should limit to 10)."""
        # Patch the actual API method at the module level
        with patch('instana_client.api.application_resources_api.ApplicationResourcesApi.get_services') as mock_method:
            # Set up the mock response with 15 items
            mock_response = MagicMock()
            mock_response.to_dict.return_value = {
                "items": [{"label": f"Service {i}"} for i in range(1, 16)]
            }
            mock_method.return_value = mock_response

            # Import and create the client
            from src.application.application_resources import (
                ApplicationResourcesMCPTools,
            )
            client = ApplicationResourcesMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Call the method
            result = await client.get_services()

            # Verify the result
            assert isinstance(result, str)
            assert "Service 1" in result
            assert "Showing 10 out of 15 total services." in result
            # Check that exactly 10 services are shown
            lines = result.split('\n')
            service_lines = [line for line in lines if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.'))]
            assert len(service_lines) == 10
            mock_method.assert_called_once()

