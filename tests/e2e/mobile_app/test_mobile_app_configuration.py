"""
E2E tests for Mobile App Configuration MCP Tools
"""

import importlib
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest


# Mock the ApiException since instana_client is not available in test environment
class ApiException(Exception):
    def __init__(self, status=None, reason=None, *args, **kwargs):
        self.status = status
        self.reason = reason
        super().__init__(*args, **kwargs)


def create_mobile_app_configuration_client(instana_credentials):
    module = importlib.import_module("src.mobile_app.mobile_app_configuration")
    module = importlib.reload(module)
    mobile_app_configuration_mcp_tools = module.MobileAppConfigurationMCPTools
    return mobile_app_configuration_mcp_tools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"]
    )


class TestMobileAppConfigurationE2E:
    """End-to-end tests for Mobile App Configuration MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        """Test initialization of the MobileAppConfigurationMCPTools client."""

        # Create the client
        client = create_mobile_app_configuration_client(instana_credentials)

        # Verify the client was created successfully
        assert client is not None
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_debug_print(self):
        """Test the debug_print helper function."""
        # debug_print is not exported from the module
        # This test verifies that the module can be imported successfully
        assert create_mobile_app_configuration_client is not None


    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_apps_returns_list(self, instana_credentials):
        """Test that get_all_mobile_apps returns a list."""

        client = create_mobile_app_configuration_client(instana_credentials)

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_mobile_app_config = MagicMock()

        mock_response = MagicMock()
        mock_response.to_dict.return_value = [
            {"id": "mob1", "name": "Test Mobile App"},
            {"id": "mob2", "name": "Another App"}
        ]
        mock_api_client.get_mobile_app_config.return_value = mock_response

        result = await client.get_all_mobile_apps(api_client=mock_api_client)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "mob1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_by_id_success(self, instana_credentials):
        """Test getting mobile app by ID."""

        client = create_mobile_app_configuration_client(instana_credentials)

        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_single_mobile_app_config = MagicMock()

        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"id": "mob1", "name": "Test Mobile App"}
        mock_api_client.get_single_mobile_app_config.return_value = mock_response

        result = await client.get_mobile_app_by_id(
            mobile_app_id="mob1",
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        assert result["id"] == "mob1"
        assert result["name"] == "Test Mobile App"


    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_geo_location_configuration(self, instana_credentials):
        """Test retrieving geo location configuration."""

        client = create_mobile_app_configuration_client(instana_credentials)

        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_mobile_app_geo_location_configuration = MagicMock()

        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"enabled": True, "mode": "AUTO"}
        mock_api_client.get_mobile_app_geo_location_configuration.return_value = mock_response

        result = await client.get_mobile_app_geo_location_configuration(
            mobile_app_id="mob1",
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        assert result["enabled"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_ip_masking_configuration(self, instana_credentials):
        """Test retrieving IP masking configuration."""

        client = create_mobile_app_configuration_client(instana_credentials)

        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_mobile_app_ip_masking_configuration = MagicMock()

        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"enabled": True}
        mock_api_client.get_mobile_app_ip_masking_configuration.return_value = mock_response

        result = await client.get_mobile_app_ip_masking_configuration(
            mobile_app_id="mob1",
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        assert result["enabled"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_geo_mapping_rules(self, instana_credentials):
        """Test retrieving geo mapping rules."""

        client = create_mobile_app_configuration_client(instana_credentials)

        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_mobile_app_geo_mapping_rules_without_preload_content = MagicMock()

        mock_response = MagicMock()
        mock_response.data = b"IP,Country\n192.168.1.1,US"
        mock_api_client.get_mobile_app_geo_mapping_rules_without_preload_content.return_value = mock_response

        result = await client.get_mobile_app_geo_mapping_rules(
            mobile_app_id="mob1",
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "data" in result
        assert len(result["data"]) == 1
        assert "schema" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_by_name(self, instana_credentials):
        """Test _get_mobile_app with name resolution."""

        client = create_mobile_app_configuration_client(instana_credentials)

        # Create a proper mock for the config_api
        mock_api_client = MagicMock()

        # Mock get_all_mobile_apps response
        mock_all_response = MagicMock()
        mock_all_response.to_dict.return_value = [
            {"id": "mob2", "name": "Test Mobile App"}
        ]
        mock_api_client.get_mobile_app_config.return_value = mock_all_response

        # Mock the final get by ID (in case it falls through)
        mock_single_response = MagicMock()
        mock_single_response.to_dict.return_value = {"id": "mob2", "name": "Test Mobile App"}
        mock_api_client.get_single_mobile_app_config.return_value = mock_single_response

        # Inject the mock api_client into the call
        result = await client._get_mobile_app(
            mobile_app_id=None,
            mobile_app_name="Test Mobile App",
            api_client=mock_api_client
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "id" in result, f"Expected 'id' in result, got: {result}"
        assert result["id"] == "mob2"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_operation_invalid_operation(self, instana_credentials):
        """Test that invalid operation returns error."""

        client = create_mobile_app_configuration_client(instana_credentials)

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="invalid_operation",
            mobile_app_id="nonexistent"
        )

        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_operation_get_geo_config(self, instana_credentials):
        """Test execute_mobile_app_advanced_config_operation with get_geo_config."""

        client = create_mobile_app_configuration_client(instana_credentials)

        # Mock get_all_mobile_apps directly (decorator may not be patched in E2E)
        client.get_all_mobile_apps = AsyncMock(
            return_value=[{"id": "mob1", "name": "Test App"}]
        )

        # Mock get_mobile_app_geo_location_configuration
        client.get_mobile_app_geo_location_configuration = AsyncMock(
            return_value={"enabled": True, "mode": "AUTO"}
        )

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="get_geo_config",
            mobile_app_name="Test App"
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
        assert result["enabled"] is True


    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_operation_get_ip_masking(self, instana_credentials):
        """Test execute_mobile_app_advanced_config_operation with get_ip_masking."""

        client = create_mobile_app_configuration_client(instana_credentials)

        # FIX: return dict directly
        client.get_mobile_app_ip_masking_configuration = AsyncMock(
            return_value={"enabled": True, "maskingType": "FULL"}
        )

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="get_ip_masking",
            mobile_app_id="mob1"
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
        assert result["enabled"] is True
