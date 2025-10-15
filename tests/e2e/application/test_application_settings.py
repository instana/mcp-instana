"""
E2E tests for Application Settings MCP Tools
"""

from unittest.mock import MagicMock

import pytest  #type: ignore

from src.application.application_settings import ApplicationSettingsMCPTools


class TestApplicationSettingsE2E:
    """End-to-end tests for Application Settings MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        """Test initialization of the ApplicationSettingsMCPTools client."""

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Verify the client was created successfully
        assert client is not None
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_applications_configs_success(self, instana_credentials):
        """Test getting all application configs successfully."""

        # Create mock API client
        mock_api_client = MagicMock()

        # Mock response - the method expects a response object with data attribute
        mock_response = MagicMock()
        mock_response_data = [
            {
                "id": "app-1",
                "label": "Test App 1",
                "scope": "INBOUND"
            },
            {
                "id": "app-2",
                "label": "Test App 2",
                "scope": "OUTBOUND"
            }
        ]
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        mock_api_client.get_application_configs_without_preload_content.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_all_applications_configs(api_client=mock_api_client)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "app-1"
        assert result[1]["id"] == "app-2"

        # Verify the API was called correctly
        mock_api_client.get_application_configs_without_preload_content.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_applications_configs_error(self, instana_credentials):
        """Test error handling in get_all_applications_configs."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_application_configs_without_preload_content.side_effect = Exception("API Error")

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_all_applications_configs(api_client=mock_api_client)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert "error" in result[0]
        assert "API Error" in result[0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_config_success(self, instana_credentials):
        """Test adding application config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.add_application_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "new-app-123",
            "label": "New Test App",
            "scope": "INBOUND",
            "boundary_scope": "ALL"
        }
        mock_api_client.add_application_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.add_application_config(
            payload={
                "accessRules": [{"accessType": "READ", "relationType": "GLOBAL", "value": "*"}],
                "boundaryScope": "ALL",
                "label": "New Test App",
                "scope": "INCLUDE_NO_DOWNSTREAM"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "new-app-123"
        assert result["label"] == "New Test App"

        # Verify the API was called correctly
        mock_api_client.add_application_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_config_missing_params(self, instana_credentials):
        """Test adding application config with missing parameters."""

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with missing parameters
        result = await client.add_application_config(
            payload={}
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "payload is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_config_api_error(self, instana_credentials):
        """Test error handling in add_application_config."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.add_application_config.side_effect = Exception("API Error")

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.add_application_config(
            payload={
                "accessRules": [{"accessType": "READ", "relationType": "GLOBAL", "value": "*"}],
                "boundaryScope": "ALL",
                "label": "Test App",
                "scope": "INCLUDE_NO_DOWNSTREAM"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_application_config_success(self, instana_credentials):
        """Test deleting application config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.delete_application_config = MagicMock()

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.delete_application_config(
            id="app-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "success" in result
        assert "deleted" in result["message"]

        # Verify the API was called correctly
        mock_api_client.delete_application_config.assert_called_once_with(id="app-123")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_application_config_missing_id(self, instana_credentials):
        """Test deleting application config with missing ID."""

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with missing ID
        result = await client.delete_application_config(id="")

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "Application perspective ID is required for deletion" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_application_config_api_error(self, instana_credentials):
        """Test error handling in delete_application_config."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.delete_application_config.side_effect = Exception("API Error")

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.delete_application_config(
            id="app-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_config_success(self, instana_credentials):
        """Test getting application config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_application_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "app-123",
            "label": "Test App",
            "scope": "INBOUND",
            "boundary_scope": "ALL"
        }
        mock_api_client.get_application_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_application_config(
            id="app-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "app-123"
        assert result["label"] == "Test App"

        # Verify the API was called correctly
        mock_api_client.get_application_config.assert_called_once_with(id="app-123")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_config_missing_id(self, instana_credentials):
        """Test getting application config with missing ID."""

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that returns actual data
        mock_api_client = MagicMock()
        mock_api_client.get_application_config.return_value = {"error": "Required entities are missing"}

        # Test the method with missing ID
        result = await client.get_application_config(id="", api_client=mock_api_client)

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "Required entities are missing" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_config_api_error(self, instana_credentials):
        """Test error handling in get_application_config."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_application_config.side_effect = Exception("API Error")

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_application_config(
            id="app-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_config_success(self, instana_credentials):
        """Test updating application config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.put_application_config = MagicMock()

        # Mock response
        mock_response = {
            "id": "app-123",
            "label": "Updated Test App",
            "scope": "OUTBOUND",
            "boundary_scope": "ALL"
        }
        mock_api_client.put_application_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.update_application_config(
            id="app-123",
            payload={
                "id": "app-123",
                "accessRules": [{"accessType": "READ", "relationType": "GLOBAL", "value": "*"}],
                "boundaryScope": "ALL",
                "label": "Updated Test App",
                "scope": "INCLUDE_NO_DOWNSTREAM"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "app-123"
        assert result["label"] == "Updated Test App"

        # Verify the API was called correctly
        mock_api_client.put_application_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_config_missing_params(self, instana_credentials):
        """Test updating application config with missing parameters."""

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with missing parameters
        result = await client.update_application_config(
            id="",
            payload={}
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "missing arguments" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_endpoint_configs_success(self, instana_credentials):
        """Test getting all endpoint configs successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_endpoint_configs = MagicMock()

        # Mock response - return list directly instead of MagicMock objects
        mock_response = [
            {
                "id": "endpoint-1",
                "name": "Test Endpoint 1",
                "type": "HTTP"
            },
            {
                "id": "endpoint-2",
                "name": "Test Endpoint 2",
                "type": "GRPC"
            }
        ]
        mock_api_client.get_endpoint_configs.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_all_endpoint_configs(api_client=mock_api_client)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "endpoint-1"
        assert result[1]["id"] == "endpoint-2"

        # Verify the API was called correctly
        mock_api_client.get_endpoint_configs.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_endpoint_config_success(self, instana_credentials):
        """Test creating endpoint config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.create_endpoint_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "new-endpoint-123",
            "name": "New Test Endpoint",
            "type": "HTTP"
        }
        mock_api_client.create_endpoint_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.create_endpoint_config(
            payload={
                "endpointCase": "ORIGINAL",
                "serviceId": "service-123"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "new-endpoint-123"
        assert result["name"] == "New Test Endpoint"

        # Verify the API was called correctly
        mock_api_client.create_endpoint_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_endpoint_config_missing_params(self, instana_credentials):
        """Test creating endpoint config with missing parameters."""

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with missing parameters
        result = await client.create_endpoint_config(payload={})

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "missing arguments" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_endpoint_config_success(self, instana_credentials):
        """Test deleting endpoint config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.delete_endpoint_config = MagicMock()

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.delete_endpoint_config(
            id="endpoint-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "success" in result
        assert "deleted" in result["message"]

        # Verify the API was called correctly
        mock_api_client.delete_endpoint_config.assert_called_once_with(id="endpoint-123")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_endpoint_config_success(self, instana_credentials):
        """Test getting endpoint config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_endpoint_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "endpoint-123",
            "name": "Test Endpoint",
            "type": "HTTP"
        }
        mock_api_client.get_endpoint_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_endpoint_config(
            id="endpoint-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "endpoint-123"
        assert result["name"] == "Test Endpoint"

        # Verify the API was called correctly
        mock_api_client.get_endpoint_config.assert_called_once_with(id="endpoint-123")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_endpoint_config_success(self, instana_credentials):
        """Test updating endpoint config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.update_endpoint_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "endpoint-123",
            "name": "Updated Test Endpoint",
            "type": "GRPC"
        }
        mock_api_client.update_endpoint_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.update_endpoint_config(
            id="endpoint-123",
            payload={
                "endpointCase": "LOWER",
                "serviceId": "service-123"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "endpoint-123"
        assert result["name"] == "Updated Test Endpoint"

        # Verify the API was called correctly
        mock_api_client.update_endpoint_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_manual_service_configs_success(self, instana_credentials):
        """Test getting all manual service configs successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_manual_service_configs = MagicMock()

        # Mock response - return list directly instead of MagicMock objects
        mock_response = [
            {
                "id": "service-1",
                "name": "Test Service 1",
                "type": "JAVA"
            },
            {
                "id": "service-2",
                "name": "Test Service 2",
                "type": "PYTHON"
            }
        ]
        # Return the list directly - it doesn't have to_dict method
        mock_api_client.get_all_manual_service_configs.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_all_manual_service_configs(api_client=mock_api_client)

        # Verify the result
        assert isinstance(result, (list, dict))
        if isinstance(result, list):
            assert len(result) == 2
            assert result[0]["id"] == "service-1"
            assert result[1]["id"] == "service-2"
        else:
            # If it's a dict, it should contain the data
            assert "data" in result or "items" in result

        # Verify the API was called correctly
        mock_api_client.get_all_manual_service_configs.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_manual_service_config_success(self, instana_credentials):
        """Test adding manual service config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.add_manual_service_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "new-service-123",
            "name": "New Test Service",
            "type": "JAVA"
        }
        mock_api_client.add_manual_service_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.add_manual_service_config(
            payload={
                "tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
                "unmonitoredServiceName": "New Test Service",
                "existingServiceId": "service-123"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "new-service-123"
        assert result["name"] == "New Test Service"

        # Verify the API was called correctly
        mock_api_client.add_manual_service_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_manual_service_config_success(self, instana_credentials):
        """Test deleting manual service config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.delete_manual_service_config = MagicMock()

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.delete_manual_service_config(
            id="service-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "success" in result
        assert "deleted" in result["message"]

        # Verify the API was called correctly
        mock_api_client.delete_manual_service_config.assert_called_once_with(id="service-123")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_manual_service_config_success(self, instana_credentials):
        """Test updating manual service config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.update_manual_service_config = MagicMock()

        # Mock response - return dict directly
        mock_response = {
            "id": "service-123",
            "name": "Updated Test Service",
            "type": "PYTHON"
        }
        mock_api_client.update_manual_service_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.update_manual_service_config(
            id="service-123",
            payload={
                "id": "service-123",
                "tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
                "unmonitoredServiceName": "Updated Test Service",
                "existingServiceId": "service-123"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "service-123"
        assert result["name"] == "Updated Test Service"

        # Verify the API was called correctly
        mock_api_client.update_manual_service_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_replace_all_manual_service_config_success(self, instana_credentials):
        """Test replacing all manual service configs successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.replace_all_manual_service_config = MagicMock()

        # Mock response - return list directly
        mock_response = [
            {"id": "service-1", "name": "Replaced Service 1", "type": "JAVA"},
            {"id": "service-2", "name": "Replaced Service 2", "type": "PYTHON"}
        ]
        mock_api_client.replace_all_manual_service_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.replace_all_manual_service_config(
            payload={
                "tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
                "unmonitoredServiceName": "Replaced Service 1",
                "existingServiceId": "service-123"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert len(result[0]) == 2
        assert result[0][0]["name"] == "Replaced Service 1"
        assert result[0][1]["name"] == "Replaced Service 2"

        # Verify the API was called correctly
        mock_api_client.replace_all_manual_service_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_service_configs_success(self, instana_credentials):
        """Test getting all service configs successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_service_configs = MagicMock()

        # Mock response - return list directly instead of MagicMock objects
        mock_response = [
            {
                "id": "service-1",
                "name": "Test Service 1",
                "type": "JAVA"
            },
            {
                "id": "service-2",
                "name": "Test Service 2",
                "type": "PYTHON"
            }
        ]
        mock_api_client.get_service_configs.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_all_service_configs(api_client=mock_api_client)

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "service-1"
        assert result[1]["id"] == "service-2"

        # Verify the API was called correctly
        mock_api_client.get_service_configs.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_service_config_success(self, instana_credentials):
        """Test adding service config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.add_service_config = MagicMock()

        # Mock response - return list directly
        mock_response = [
            {"id": "new-service-1", "name": "New Service 1", "type": "JAVA"},
            {"id": "new-service-2", "name": "New Service 2", "type": "PYTHON"}
        ]
        mock_api_client.add_service_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.add_service_config(
            payload={
                "enabled": True,
                "matchSpecification": [{"type": "TAG", "key": "service.name", "operator": "EQUALS", "value": "New Service 1"}],
                "name": "New Service 1",
                "label": "New Service 1",
                "id": "new-service-1"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "New Service 1"
        assert result[1]["name"] == "New Service 2"

        # Verify the API was called correctly
        mock_api_client.add_service_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_replace_all_service_configs_success(self, instana_credentials):
        """Test replacing all service configs successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.replace_all = MagicMock()

        # Mock response - return list directly
        mock_response = [
            {"id": "service-1", "name": "Replaced Service 1", "type": "JAVA"},
            {"id": "service-2", "name": "Replaced Service 2", "type": "PYTHON"}
        ]
        mock_api_client.replace_all.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.replace_all_service_configs(
            payload={
                "enabled": True,
                "matchSpecification": [{"type": "TAG", "key": "service.name", "operator": "EQUALS", "value": "Replaced Service 1"}],
                "name": "Replaced Service 1",
                "label": "Replaced Service 1",
                "id": "service-1"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert len(result[0]) == 2
        assert result[0][0]["name"] == "Replaced Service 1"
        assert result[0][1]["name"] == "Replaced Service 2"

        # Verify the API was called correctly
        mock_api_client.replace_all.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_order_service_config_success(self, instana_credentials):
        """Test ordering service config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.order_service_config = MagicMock()

        # Mock response - return list directly
        mock_response = [
            {
                "id": "service-1",
                "name": "Service 1",
                "order": 1
            },
            {
                "id": "service-2",
                "name": "Service 2",
                "order": 2
            }
        ]
        mock_api_client.order_service_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.order_service_config(
            request_body=["service-1", "service-2"],
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["order"] == 1
        assert result[1]["order"] == 2

        # Verify the API was called correctly
        mock_api_client.order_service_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_order_service_config_empty_list(self, instana_credentials):
        """Test ordering service config with empty list."""

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with empty list
        result = await client.order_service_config(request_body=[], api_client=MagicMock())

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "The list of service configuration IDs cannot be empty" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_service_config_success(self, instana_credentials):
        """Test deleting service config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.delete_service_config = MagicMock()

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.delete_service_config(
            id="service-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "success" in result
        assert "deleted" in result["message"]

        # Verify the API was called correctly
        mock_api_client.delete_service_config.assert_called_once_with(id="service-123")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_service_config_success(self, instana_credentials):
        """Test getting service config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_service_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "service-123",
            "name": "Test Service",
            "type": "JAVA"
        }
        mock_api_client.get_service_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_service_config(
            id="service-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "service-123"
        assert result["name"] == "Test Service"

        # Verify the API was called correctly
        mock_api_client.get_service_config.assert_called_once_with(id="service-123")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_service_config_success(self, instana_credentials):
        """Test updating service config successfully."""

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.put_service_config = MagicMock()

        # Mock response - return list directly
        mock_response = [
            {"id": "service-1", "name": "Updated Service 1", "type": "JAVA"},
            {"id": "service-2", "name": "Updated Service 2", "type": "PYTHON"}
        ]
        mock_api_client.put_service_config.return_value = mock_response

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.update_service_config(
            id="service-1",
            payload={
                "enabled": True,
                "matchSpecification": [{"type": "TAG", "key": "service.name", "operator": "EQUALS", "value": "Updated Service 1"}],
                "name": "Updated Service 1",
                "label": "Updated Service 1",
                "id": "service-1"
            },
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert len(result[0]) == 2
        assert result[0][0]["name"] == "Updated Service 1"
        assert result[0][1]["name"] == "Updated Service 2"

        # Verify the API was called correctly
        mock_api_client.put_service_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_all_methods_with_none_api_client(self, instana_credentials):
        """Test all methods with None api_client to ensure proper error handling."""

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test all methods with None api_client
        methods_to_test = [
            ("get_all_applications_configs", {}),
            ("add_application_config", {"payload": {"accessRules": [{"accessType": "READ", "relationType": "GLOBAL", "value": "*"}], "boundaryScope": "ALL", "label": "test", "scope": "INCLUDE_NO_DOWNSTREAM"}}),
            ("delete_application_config", {"id": "test"}),
            ("get_application_config", {"id": "test"}),
            ("update_application_config", {"id": "test", "payload": {"accessRules": [{"accessType": "READ", "relationType": "GLOBAL", "value": "*"}], "boundaryScope": "ALL", "label": "test", "scope": "INCLUDE_NO_DOWNSTREAM"}}),
            ("get_all_endpoint_configs", {}),
            ("create_endpoint_config", {"payload": {"endpointCase": "ORIGINAL", "serviceId": "test"}}),
            ("delete_endpoint_config", {"id": "test"}),
            ("get_endpoint_config", {"id": "test"}),
            ("update_endpoint_config", {"id": "test", "payload": {"endpointCase": "ORIGINAL", "serviceId": "test"}}),
            ("get_all_manual_service_configs", {}),
            ("add_manual_service_config", {"payload": {"tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}, "unmonitoredServiceName": "test", "existingServiceId": "test"}}),
            ("delete_manual_service_config", {"id": "test"}),
            ("update_manual_service_config", {"id": "test", "payload": {"tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}, "unmonitoredServiceName": "test", "existingServiceId": "test"}}),
            ("replace_all_manual_service_config", {"payload": {"tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}, "unmonitoredServiceName": "test", "existingServiceId": "test"}}),
            ("get_all_service_configs", {}),
            ("add_service_config", {"enabled": True, "match_specification": [{"type": "TAG", "key": "test"}], "name": "test", "label": "test", "id": "test"}),
            ("replace_all_service_configs", {"payload": {"enabled": True, "matchSpecification": [{"type": "TAG", "key": "test"}], "name": "test", "label": "test", "id": "test"}}),
            ("order_service_config", {"request_body": ["test"]}),
            ("delete_service_config", {"id": "test"}),
            ("get_service_config", {"id": "test"}),
            ("update_service_config", {"enabled": True, "match_specification": [{"type": "TAG", "key": "test"}], "name": "test", "label": "test", "id": "test", "payload": {"enabled": True, "matchSpecification": [{"type": "TAG", "key": "test"}], "name": "test", "label": "test", "id": "test"}})
        ]

        for method_name, params in methods_to_test:
            method = getattr(client, method_name)
            result = await method(**params, api_client=None)

            # All methods should return some form of result (success or error)
            assert result is not None
            assert isinstance(result, (dict, list))

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_error_handling_consistency(self, instana_credentials):
        """Test that all methods handle errors consistently."""

        # Create mock API client that raises exceptions
        mock_api_client = MagicMock()
        mock_api_client.get_application_configs.side_effect = Exception("Test Error")
        mock_api_client.add_application_config.side_effect = Exception("Test Error")
        mock_api_client.delete_application_config.side_effect = Exception("Test Error")
        mock_api_client.get_application_config.side_effect = Exception("Test Error")
        mock_api_client.update_application_config.side_effect = Exception("Test Error")

        # Create the client
        client = ApplicationSettingsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test error handling for various methods
        methods_to_test = [
            ("get_all_applications_configs", {}),
            ("add_application_config", {"payload": {"accessRules": [{"accessType": "READ", "relationType": "GLOBAL", "value": "*"}], "boundaryScope": "ALL", "label": "test", "scope": "INCLUDE_NO_DOWNSTREAM"}}),
            ("delete_application_config", {"id": "test"}),
            ("get_application_config", {"id": "test"}),
            ("update_application_config", {"id": "test", "payload": {"accessRules": [{"accessType": "READ", "relationType": "GLOBAL", "value": "*"}], "boundaryScope": "ALL", "label": "test", "scope": "INCLUDE_NO_DOWNSTREAM"}})
        ]

        for method_name, params in methods_to_test:
            method = getattr(client, method_name)
            result = await method(**params, api_client=mock_api_client)

            # All methods should return error information when exceptions occur
            if isinstance(result, dict):
                assert "error" in result
                # Some methods might have validation errors before reaching the API call
                assert "Test Error" in result["error"] or "Failed to" in result["error"]
            elif isinstance(result, list):
                assert len(result) == 1
                assert "error" in result[0]
                # Some methods might have validation errors before reaching the API call
                assert "Test Error" in result[0]["error"] or "Failed to" in result[0]["error"]
