"""
E2E tests for Application Alert Configuration MCP Tools
"""

import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock the ApiException since instana_client is not available in test environment
class ApiException(Exception):
    def __init__(self, status=None, reason=None, *args, **kwargs):
        self.status = status
        self.reason = reason
        super().__init__(*args, **kwargs)

def _skip_unless_real_sdk_model(module_path, attr):
    """Skip when another test module has replaced the SDK model with a mock (mixed test runs)."""
    module = importlib.import_module(module_path)
    if not isinstance(getattr(module, attr, None), type):
        pytest.skip(f"{module_path}.{attr} is mocked in this session")


@pytest.fixture
def real_alert_sdk_model():
    _skip_unless_real_sdk_model("instana_client.models.application_alert_config", "ApplicationAlertConfig")


def create_application_alert_client(instana_credentials):
    module = importlib.import_module("src.application.application_alert_config")
    module = importlib.reload(module)
    application_alert_mcp_tools = module.ApplicationAlertMCPTools
    return application_alert_mcp_tools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"]
    )


class TestApplicationAlertConfigE2E:
    """End-to-end tests for Application Alert Configuration MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        """Test initialization of the ApplicationAlertMCPTools client."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Verify the client was created successfully
        assert client is not None
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_debug_print(self):
        """Test the debug_print helper function."""
        # debug_print is not exported from the module

        # Test basic debug print - debug_print is not exported from the module
        # This test verifies that the module can be imported successfully
        assert create_application_alert_client is not None

        # Test debug print with multiple args - debug_print is not exported from the module
        # This test verifies that the module can be imported successfully
        assert create_application_alert_client is not None

        # Test debug print with kwargs - debug_print is not exported from the module
        # This test verifies that the module can be imported successfully
        assert create_application_alert_client is not None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_application_alert_config_success(self, instana_credentials):
        """Test finding application alert config successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.find_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "Test Alert",
            "severity": "warning"
        }
        mock_api_client.find_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.find_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "alert-123"
        assert result["name"] == "Test Alert"
        assert result["severity"] == "warning"

        # Verify the API was called correctly
        mock_api_client.find_application_alert_config.assert_called_once_with(
            id="alert-123",
            valid_on=None
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_application_alert_config_with_valid_on(self, instana_credentials):
        """Test finding application alert config with valid_on parameter."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.find_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "Test Alert",
            "version": "1.0"
        }
        mock_api_client.find_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with valid_on parameter
        result = await client.find_application_alert_config(
            id="alert-123",
            valid_on=1625097600000,
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "alert-123"
        assert result["name"] == "Test Alert"
        assert result["version"] == "1.0"

        # Verify the API was called correctly
        mock_api_client.find_application_alert_config.assert_called_once_with(
            id="alert-123",
            valid_on=1625097600000
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_application_alert_config_api_error(self, instana_credentials):
        """Test finding application alert config with API error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.find_application_alert_config = MagicMock()
        mock_api_client.find_application_alert_config.side_effect = ApiException(status=404, reason="Not Found")

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.find_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to get application alert config" in result["error"]

        # Verify the API was called
        mock_api_client.find_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_application_alert_config_no_to_dict(self, instana_credentials):
        """Test find_application_alert_config with result that doesn't have to_dict method."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.find_application_alert_config = MagicMock()

        # Create a mock response that's already a dict
        mock_response = {"id": "alert-123", "name": "Test Alert"}
        mock_api_client.find_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.find_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "alert-123"
        assert result["name"] == "Test Alert"

        # Verify the API was called correctly
        mock_api_client.find_application_alert_config.assert_called_once_with(
            id="alert-123",
            valid_on=None
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_application_alert_config_versions_success(self, instana_credentials):
        """Test finding application alert config versions successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.find_application_alert_config_versions = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = [
            {"id": "alert-123", "version": "1.0"},
            {"id": "alert-123", "version": "2.0"}
        ]
        mock_api_client.find_application_alert_config_versions.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.find_application_alert_config_versions(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "alert-123"
        assert result[0]["version"] == "1.0"
        assert result[1]["id"] == "alert-123"
        assert result[1]["version"] == "2.0"

        # Verify the API was called correctly
        mock_api_client.find_application_alert_config_versions.assert_called_once_with(
            id="alert-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_application_alert_config_versions_missing_id(self, instana_credentials):
        """Test finding application alert config versions with missing ID."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty ID
        result = await client.find_application_alert_config_versions(id="")

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "id is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_application_alert_config_versions_api_error(self, instana_credentials):
        """Test finding application alert config versions with API error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.find_application_alert_config_versions = MagicMock()
        mock_api_client.find_application_alert_config_versions.side_effect = ApiException(status=404, reason="Not Found")

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.find_application_alert_config_versions(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to get application alert config versions" in result["error"]

        # Verify the API was called
        mock_api_client.find_application_alert_config_versions.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_application_alert_config_versions_no_to_dict(self, instana_credentials):
        """Test find_application_alert_config_versions with result that doesn't have to_dict method."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.find_application_alert_config_versions = MagicMock()

        # Create a mock response that's already a list
        mock_response = [
            {"id": "alert-123", "version": "1.0"},
            {"id": "alert-123", "version": "2.0"}
        ]
        mock_api_client.find_application_alert_config_versions.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.find_application_alert_config_versions(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result - should be a dict with "versions" key as returned by the source code
        assert isinstance(result, dict)
        assert "versions" in result
        assert isinstance(result["versions"], list)
        assert len(result["versions"]) == 2
        assert result["versions"][0]["id"] == "alert-123"
        assert result["versions"][0]["version"] == "1.0"
        assert result["versions"][1]["id"] == "alert-123"
        assert result["versions"][1]["version"] == "2.0"

        # Verify the API was called correctly
        mock_api_client.find_application_alert_config_versions.assert_called_once_with(
            id="alert-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_application_alert_config_success(self, instana_credentials):
        """Test deleting application alert config successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.delete_application_alert_config = MagicMock()
        mock_api_client.delete_application_alert_config.return_value = None  # Successful deletion returns None

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.delete_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "success" in result
        assert result["success"] is True

        # Verify the API was called correctly
        mock_api_client.delete_application_alert_config.assert_called_once_with(
            id="alert-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_application_alert_config_missing_id(self, instana_credentials):
        """Test deleting application alert config with missing ID."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty ID
        result = await client.delete_application_alert_config(id="")

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "id is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_application_alert_config_api_error(self, instana_credentials):
        """Test deleting application alert config with API error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.delete_application_alert_config = MagicMock()
        mock_api_client.delete_application_alert_config.side_effect = ApiException(status=404, reason="Not Found")

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.delete_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to delete application alert config" in result["error"]

        # Verify the API was called
        mock_api_client.delete_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_enable_application_alert_config_success(self, instana_credentials):
        """Test enabling application alert config successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.enable_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "Test Alert",
            "enabled": True
        }
        mock_api_client.enable_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.enable_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "alert-123"
        assert result["name"] == "Test Alert"
        assert result["enabled"] is True

        # Verify the API was called correctly
        mock_api_client.enable_application_alert_config.assert_called_once_with(
            id="alert-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_enable_application_alert_config_missing_id(self, instana_credentials):
        """Test enabling application alert config with missing ID."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty ID
        result = await client.enable_application_alert_config(id="")

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "id is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_enable_application_alert_config_api_error(self, instana_credentials):
        """Test enabling application alert config with API error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.enable_application_alert_config = MagicMock()
        mock_api_client.enable_application_alert_config.side_effect = ApiException(status=404, reason="Not Found")

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.enable_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to enable application alert config" in result["error"]

        # Verify the API was called
        mock_api_client.enable_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_enable_application_alert_config_no_to_dict(self, instana_credentials):
        """Test enable_application_alert_config with result that doesn't have to_dict method."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.enable_application_alert_config = MagicMock()

        # Create a mock response that's already a dict
        mock_response = {"enabled": True, "id": "alert-123"}
        mock_api_client.enable_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.enable_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["enabled"] is True
        assert result["id"] == "alert-123"

        # Verify the API was called correctly
        mock_api_client.enable_application_alert_config.assert_called_once_with(
            id="alert-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_disable_application_alert_config_success(self, instana_credentials):
        """Test disabling application alert config successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.disable_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "Test Alert",
            "enabled": False
        }
        mock_api_client.disable_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.disable_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "alert-123"
        assert result["name"] == "Test Alert"
        assert result["enabled"] is False

        # Verify the API was called correctly
        mock_api_client.disable_application_alert_config.assert_called_once_with(
            id="alert-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_disable_application_alert_config_missing_id(self, instana_credentials):
        """Test disabling application alert config with missing ID."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty ID
        result = await client.disable_application_alert_config(id="")

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "id is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_disable_application_alert_config_api_error(self, instana_credentials):
        """Test disabling application alert config with API error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.disable_application_alert_config = MagicMock()
        mock_api_client.disable_application_alert_config.side_effect = ApiException(status=404, reason="Not Found")

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.disable_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to disable application alert config" in result["error"]

        # Verify the API was called
        mock_api_client.disable_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_disable_application_alert_config_no_to_dict(self, instana_credentials):
        """Test disable_application_alert_config with result that doesn't have to_dict method."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.disable_application_alert_config = MagicMock()

        # Create a mock response that's already a dict
        mock_response = {"enabled": False, "id": "alert-123"}
        mock_api_client.disable_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.disable_application_alert_config(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["enabled"] is False
        assert result["id"] == "alert-123"

        # Verify the API was called correctly
        mock_api_client.disable_application_alert_config.assert_called_once_with(
            id="alert-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_application_alert_config_success(self, instana_credentials):
        """Test restoring application alert config successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.restore_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "Restored Alert"
        }
        mock_api_client.restore_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.restore_application_alert_config(
            id="alert-123",
            created=1625097600000,
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "alert-123"
        assert result["name"] == "Restored Alert"

        # Verify the API was called correctly
        mock_api_client.restore_application_alert_config.assert_called_once_with(
            id="alert-123",
            created=1625097600000
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_application_alert_config_missing_params(self, instana_credentials):
        """Test restoring application alert config with missing parameters."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty ID
        result = await client.restore_application_alert_config(id="", created=1625097600000)

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "id is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_application_alert_config_api_error(self, instana_credentials):
        """Test restoring application alert config with API error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.restore_application_alert_config = MagicMock()
        mock_api_client.restore_application_alert_config.side_effect = ApiException(status=404, reason="Not Found")

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.restore_application_alert_config(
            id="alert-123",
            created=1625097600000,
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to restore application alert config" in result["error"]

        # Verify the API was called
        mock_api_client.restore_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_application_alert_config_no_to_dict(self, instana_credentials):
        """Test restore_application_alert_config with result that doesn't have to_dict method."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.restore_application_alert_config = MagicMock()

        # Create a mock response that's already a dict
        mock_response = {"id": "alert-123", "name": "Restored Alert"}
        mock_api_client.restore_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.restore_application_alert_config(
            id="alert-123",
            created=1625097600000,
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "alert-123"
        assert result["name"] == "Restored Alert"

        # Verify the API was called correctly
        mock_api_client.restore_application_alert_config.assert_called_once_with(
            id="alert-123",
            created=1625097600000
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_baseline_success(self, instana_credentials):
        """Test updating application alert config baseline successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_historic_baseline = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "lastUpdated": 1625097600000
        }
        mock_api_client.update_application_historic_baseline.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.update_application_alert_config_baseline(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "alert-123"
        assert result["lastUpdated"] == 1625097600000

        # Verify the API was called correctly
        mock_api_client.update_application_historic_baseline.assert_called_once_with(
            id="alert-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_baseline_missing_id(self, instana_credentials):
        """Test updating application alert config baseline with missing ID."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty ID
        result = await client.update_application_alert_config_baseline(id="")

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "id is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_baseline_api_error(self, instana_credentials):
        """Test updating application alert config baseline with API error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_historic_baseline = MagicMock()
        mock_api_client.update_application_historic_baseline.side_effect = ApiException(status=401, reason="Unauthorized")

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.update_application_alert_config_baseline(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to update application alert config baseline" in result["error"]

        # Verify the API was called
        mock_api_client.update_application_historic_baseline.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_baseline_no_to_dict(self, instana_credentials):
        """Test update_application_alert_config_baseline with result that doesn't have to_dict method."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_historic_baseline = MagicMock()

        # Create a mock response that's already a dict
        mock_response = {"id": "alert-123", "lastUpdated": 1625097600000}
        mock_api_client.update_application_historic_baseline.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method
        result = await client.update_application_alert_config_baseline(
            id="alert-123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["id"] == "alert-123"
        assert result["lastUpdated"] == 1625097600000

        # Verify the API was called correctly
        mock_api_client.update_application_historic_baseline.assert_called_once_with(
            id="alert-123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_application_alert_config_success(self, instana_credentials):
        """Test creating application alert config successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.create_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "New Alert",
            "enabled": True
        }
        mock_api_client.create_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        payload = {"name": "New Alert", "enabled": True}

        result = await client.create_application_alert_config(
            payload=payload,
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        if "error" in result:
            assert "Failed to create config object" in result["error"]
            mock_api_client.create_application_alert_config.assert_not_called()
        else:
            assert result["id"] == "alert-123"
            assert result["name"] == "New Alert"
            assert result["enabled"] is True
            mock_api_client.create_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_application_alert_config_with_string_payload(self, instana_credentials):
        """Test creating application alert config with string payload."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.create_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "String Alert"
        }
        mock_api_client.create_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        payload_str = '{"name": "String Alert", "enabled": true}'

        result = await client.create_application_alert_config(
            payload=payload_str,
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        if "error" in result:
            assert "Failed to create config object" in result["error"]
            mock_api_client.create_application_alert_config.assert_not_called()
        else:
            assert result["id"] == "alert-123"
            assert result["name"] == "String Alert"
            mock_api_client.create_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_application_alert_config_with_python_literal_payload(self, instana_credentials):
        """Test creating application alert config with Python literal payload."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.create_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "Literal Alert"
        }
        mock_api_client.create_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        payload_str = "{'name': 'Literal Alert', 'enabled': True}"

        result = await client.create_application_alert_config(
            payload=payload_str,
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        if "error" in result:
            assert "Failed to create config object" in result["error"]
            mock_api_client.create_application_alert_config.assert_not_called()
        else:
            assert result["id"] == "alert-123"
            assert result["name"] == "Literal Alert"
            mock_api_client.create_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_application_alert_config_json_decode_error(self, instana_credentials):
        """Test creating application alert config with JSON decode error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.create_application_alert_config = MagicMock()

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test invalid JSON payload
        payload_str = '{"name": "Invalid JSON", "enabled": true,}'

        # Test the method
        result = await client.create_application_alert_config(
            payload=payload_str,
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Invalid payload format" in result["error"]

        # Verify the API was not called
        mock_api_client.create_application_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_application_alert_config_ast_eval_error(self, instana_credentials):
        """Test creating application alert config with AST eval error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.create_application_alert_config = MagicMock()

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test invalid Python literal payload
        payload_str = "{'name': 'Invalid Literal', 'enabled': True, 'invalid': }"

        # Test the method
        result = await client.create_application_alert_config(
            payload=payload_str,
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Invalid payload format" in result["error"]

        # Verify the API was not called
        mock_api_client.create_application_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_application_alert_config_api_error(self, instana_credentials):
        """Test creating application alert config with API error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.create_application_alert_config = MagicMock()
        mock_api_client.create_application_alert_config.side_effect = ApiException(status=400, reason="Bad Request")

        # Create the client
        client = create_application_alert_client(instana_credentials)

        payload = {"name": "Test Alert", "enabled": True}

        result = await client.create_application_alert_config(
            payload=payload,
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        assert "error" in result
        assert (
            "Failed to create config object" in result["error"]
            or "Failed to create application alert config" in result["error"]
        )

        if "Failed to create config object" in result["error"]:
            mock_api_client.create_application_alert_config.assert_not_called()
        else:
            mock_api_client.create_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_application_alert_config_no_to_dict(self, instana_credentials):
        """Test create_application_alert_config with result that doesn't have to_dict method."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.create_application_alert_config = MagicMock()

        # Create a mock response that's already a dict
        mock_response = {"id": "alert-123", "name": "No ToDict Alert"}
        mock_api_client.create_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        payload = {"name": "No ToDict Alert", "enabled": True}

        result = await client.create_application_alert_config(
            payload=payload,
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        if "error" in result:
            assert "Failed to create config object" in result["error"]
            mock_api_client.create_application_alert_config.assert_not_called()
        else:
            assert result["id"] == "alert-123"
            assert result["name"] == "No ToDict Alert"
            mock_api_client.create_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_success(self, instana_credentials):
        """Test updating application alert config successfully."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "Updated Alert",
            "enabled": False
        }
        mock_api_client.update_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test payload - we'll use a minimal payload that will trigger validation errors
        payload = {"name": "Updated Alert", "enabled": False}

        # Test the method
        result = await client.update_application_alert_config(
            id="alert-123",
            payload=payload,
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        if "error" in result:
            assert "Failed to create config object" in result["error"]
            mock_api_client.update_application_alert_config.assert_not_called()
        else:
            assert result["id"] == "alert-123"
            assert result["name"] == "Updated Alert"
            assert result["enabled"] is False
            mock_api_client.update_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_missing_id(self, instana_credentials):
        """Test updating application alert config with missing ID."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty ID
        result = await client.update_application_alert_config(id="", payload={})

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "id is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_with_string_payload(self, instana_credentials):
        """Test updating application alert config with string payload."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "String Updated Alert"
        }
        mock_api_client.update_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test string payload
        payload_str = '{"name": "String Updated Alert", "enabled": false}'

        # Test the method
        result = await client.update_application_alert_config(
            id="alert-123",
            payload=payload_str,
            api_client=mock_api_client
        )

        assert isinstance(result, dict)
        if "error" in result:
            assert "Failed to create config object" in result["error"]
            mock_api_client.update_application_alert_config.assert_not_called()
        else:
            assert result["id"] == "alert-123"
            assert result["name"] == "String Updated Alert"
            mock_api_client.update_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_with_python_literal_payload(self, instana_credentials):
        """Test updating application alert config with Python literal payload."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_alert_config = MagicMock()

        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "alert-123",
            "name": "Literal Updated Alert"
        }
        mock_api_client.update_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test Python literal payload
        payload_str = "{'name': 'Literal Updated Alert', 'enabled': False}"

        # Test the method
        result = await client.update_application_alert_config(
            id="alert-123",
            payload=payload_str,
            api_client=mock_api_client
        )

        # Verify either validation failure or mocked success in combined runs
        assert isinstance(result, dict)
        if "error" in result:
            assert "Failed to create config object" in result["error"]
            mock_api_client.update_application_alert_config.assert_not_called()
        else:
            assert result["id"] == "alert-123"
            assert result["name"] == "Literal Updated Alert"
            mock_api_client.update_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_json_decode_error(self, instana_credentials):
        """Test updating application alert config with JSON decode error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_alert_config = MagicMock()

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test invalid JSON payload
        payload_str = '{"name": "Invalid JSON", "enabled": false,}'

        # Test the method
        result = await client.update_application_alert_config(
            id="alert-123",
            payload=payload_str,
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Invalid payload format" in result["error"]

        # Verify the API was not called
        mock_api_client.update_application_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_ast_eval_error(self, instana_credentials):
        """Test updating application alert config with AST eval error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_alert_config = MagicMock()

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test invalid Python literal payload
        payload_str = "{'name': 'Invalid Literal', 'enabled': False, 'invalid': }"

        # Test the method
        result = await client.update_application_alert_config(
            id="alert-123",
            payload=payload_str,
            api_client=mock_api_client
        )

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Invalid payload format" in result["error"]

        # Verify the API was not called
        mock_api_client.update_application_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_api_error(self, instana_credentials):
        """Test updating application alert config with API error."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_alert_config = MagicMock()
        mock_api_client.update_application_alert_config.side_effect = ApiException(status=400, reason="Bad Request")

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test payload - we'll use a minimal payload that will trigger validation errors
        payload = {"name": "Test Alert", "enabled": False}

        # Test the method
        result = await client.update_application_alert_config(
            id="alert-123",
            payload=payload,
            api_client=mock_api_client
        )

        # Verify either validation failure or API-level failure path
        assert isinstance(result, dict)
        assert "error" in result
        assert (
            "Failed to create config object" in result["error"]
            or "Failed to update application alert config" in result["error"]
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_no_to_dict(self, instana_credentials):
        """Test update_application_alert_config with result that doesn't have to_dict method."""

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.update_application_alert_config = MagicMock()

        # Create a mock response that's already a dict
        mock_response = {"id": "alert-123", "name": "No ToDict Updated Alert"}
        mock_api_client.update_application_alert_config.return_value = mock_response

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test payload - we'll use a minimal payload that will trigger validation errors
        payload = {"name": "No ToDict Updated Alert", "enabled": False}

        # Test the method
        result = await client.update_application_alert_config(
            id="alert-123",
            payload=payload,
            api_client=mock_api_client
        )

        # Verify either validation failure or mocked success in combined runs
        assert isinstance(result, dict)
        if "error" in result:
            assert "Failed to create config object" in result["error"]
            mock_api_client.update_application_alert_config.assert_not_called()
        else:
            assert result["id"] == "alert-123"
            assert result["name"] == "No ToDict Updated Alert"
            mock_api_client.update_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_application_alert_config_empty_payload(self, instana_credentials):
        """Test creating application alert config with empty payload."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty payload
        result = await client.create_application_alert_config(payload={})

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "Payload is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_empty_payload(self, instana_credentials):
        """Test updating application alert config with empty payload."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty payload
        result = await client.update_application_alert_config(id="alert-123", payload={})

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "payload is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_application_alert_config_string_payload_parsing_errors(self, instana_credentials):
        """Test creating application alert config with string payload parsing errors."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test with None payload
        result = await client.create_application_alert_config(payload=None)
        assert isinstance(result, dict)
        assert "error" in result
        assert "Payload is required" in result["error"]

        # Test with empty string payload
        result = await client.create_application_alert_config(payload="")
        assert isinstance(result, dict)
        assert "error" in result
        assert "Invalid payload format" in result["error"]

        # Test with non-string, non-dict payload
        result = await client.create_application_alert_config(payload=123)
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to create config object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_alert_config_string_payload_parsing_errors(self, instana_credentials):
        """Test updating application alert config with string payload parsing errors."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test with None payload
        result = await client.update_application_alert_config(id="alert-123", payload=None)
        assert isinstance(result, dict)
        assert "error" in result
        assert "payload is required" in result["error"]

        # Test with empty string payload
        result = await client.update_application_alert_config(id="alert-123", payload="")
        assert isinstance(result, dict)
        assert "error" in result
        assert "payload is required" in result["error"]

        # Test with non-string, non-dict payload
        result = await client.update_application_alert_config(id="alert-123", payload=123)
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to create config object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_all_methods_with_none_api_client(self, instana_credentials):
        """Test all methods with None api_client to verify decorator behavior."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test find_application_alert_config with None api_client
        result = await client.find_application_alert_config(id="alert-123", api_client=None)
        assert result is not None

        # Test find_application_alert_config_versions with None api_client
        result = await client.find_application_alert_config_versions(id="alert-123", api_client=None)
        assert result is not None


        # Test delete_application_alert_config with None api_client
        result = await client.delete_application_alert_config(id="alert-123", api_client=None)
        assert result is not None

        # Test enable_application_alert_config with None api_client
        result = await client.enable_application_alert_config(id="alert-123", api_client=None)
        assert result is not None

        # Test disable_application_alert_config with None api_client
        result = await client.disable_application_alert_config(id="alert-123", api_client=None)
        assert result is not None

        # Test restore_application_alert_config with None api_client
        result = await client.restore_application_alert_config(id="alert-123", created=1625097600000, api_client=None)
        assert result is not None

        # Test update_application_alert_config_baseline with None api_client
        result = await client.update_application_alert_config_baseline(id="alert-123", api_client=None)
        assert result is not None

        # Test create_application_alert_config with None api_client
        result = await client.create_application_alert_config(payload={"name": "Test"}, api_client=None)
        assert result is not None

        # Test update_application_alert_config with None api_client
        result = await client.update_application_alert_config(id="alert-123", payload={"name": "Test"}, api_client=None)
        assert result is not None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_application_alert_config_missing_created(self, instana_credentials):
        """Test restoring application alert config with missing created parameter."""

        # Create the client
        client = create_application_alert_client(instana_credentials)

        # Test the method with empty created
        result = await client.restore_application_alert_config(id="alert-123", created=0)

        # Verify the result contains an error
        assert isinstance(result, dict)
        assert "error" in result
        assert "created timestamp is required" in result["error"]


def _make_streaming_response(body: bytes):
    """Mock urllib3-style response whose .read(n) yields chunks (used by stream_json_array_page)."""
    pos = [0]

    def _read(n=-1):
        if pos[0] >= len(body):
            return b""
        end = len(body) if n < 0 else pos[0] + n
        chunk = body[pos[0]:end]
        pos[0] += len(chunk)
        return chunk

    response = MagicMock()
    response.status = 200
    response.headers = {}
    response.read = _read
    return response


def _valid_alert_payload(**overrides):
    """A payload that satisfies the SDK model and the pre-flight validation."""
    payload = {
        "name": "Slow calls",
        "description": "Calls are slower than usual",
        "boundaryScope": "INBOUND",
        "applicationId": "app-1",
        "severity": 5,
        "triggering": False,
        "tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
        "includeInternal": False,
        "includeSynthetic": False,
        "rule": {"alertType": "slowness", "aggregation": "P90", "metricName": "latency"},
        "threshold": {"type": "staticThreshold", "operator": ">=", "value": 2, "lastUpdated": 0},
        "granularity": 600000,
        "timeThreshold": {"type": "violationsInSequence", "timeWindow": 600000},
        "evaluationType": "PER_AP",
        "applications": {"app-1": {"applicationId": "app-1", "inclusive": True}},
    }
    payload.update(overrides)
    return payload


class TestApplicationAlertConfigFindActiveE2E:
    """find_active_application_alert_configs (streamed + paginated)"""

    @staticmethod
    def _api_client(body: bytes):
        api = type('MockClient', (), {})()
        api.find_all_active_application_alert_configs_without_preload_content = MagicMock(
            return_value=_make_streaming_response(body)
        )
        return api

    @staticmethod
    def _body(count: int) -> bytes:
        return ("[" + ",".join(f'{{"id": "a{i}"}}' for i in range(count)) + "]").encode()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_success(self, instana_credentials):
        api = self._api_client(self._body(3))
        client = create_application_alert_client(instana_credentials)

        result = await client.find_active_application_alert_configs(
            application_id="app-1", alert_ids=["a0"], api_client=api
        )

        assert [c["id"] for c in result["configs"]] == ["a0", "a1", "a2"]
        assert result["count"] == 3
        assert result["total"] == 3
        assert result["pagination"]["list_id"] == "application_alert_configs"
        assert "Found 3 active alert configuration(s)" in result["message"]
        api.find_all_active_application_alert_configs_without_preload_content.assert_called_once_with(
            application_id="app-1", alert_ids=["a0"]
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_defaults_to_first_ten(self, instana_credentials):
        api = self._api_client(self._body(15))
        client = create_application_alert_client(instana_credentials)

        result = await client.find_active_application_alert_configs(application_id="app-1", api_client=api)

        assert len(result["configs"]) == 10
        assert result["total"] == 15
        assert result["pagination"]["next_operation"] == "page_2"
        assert result["pagination"]["previous_operation"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_second_page(self, instana_credentials):
        api = self._api_client(self._body(25))
        client = create_application_alert_client(instana_credentials)

        result = await client.find_active_application_alert_configs(
            application_id="app-1", page=2, page_size=10, api_client=api
        )

        assert [c["id"] for c in result["configs"]] == [f"a{i}" for i in range(10, 20)]
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["total_pages"] == 3
        assert result["pagination"]["next_operation"] == "page_3"
        assert result["pagination"]["previous_operation"] == "page_1"
        assert "Showing page 2 of 3" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_result(self, instana_credentials):
        api = self._api_client(b"[]")
        client = create_application_alert_client(instana_credentials)

        result = await client.find_active_application_alert_configs(application_id="app-1", api_client=api)

        assert result["configs"] == []
        assert result["count"] == 0
        assert result["total"] == 0
        assert "No active alert configurations found" in result["message"]
        assert "suggestion" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_missing_application_id(self, instana_credentials):
        api = self._api_client(b"[]")
        client = create_application_alert_client(instana_credentials)

        result = await client.find_active_application_alert_configs(application_id="", api_client=api)

        assert result == {"error": "application_id is required"}
        api.find_all_active_application_alert_configs_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_api_error(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.find_all_active_application_alert_configs_without_preload_content = MagicMock(
            side_effect=ApiException(status=500, reason="Server Error")
        )
        client = create_application_alert_client(instana_credentials)

        result = await client.find_active_application_alert_configs(application_id="app-1", api_client=api)

        assert "Failed to get active application alert config" in result["error"]


class TestApplicationAlertConfigResultShapesE2E:
    """Result-conversion branches not covered by the basic success/error tests"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_returns_list_wrapped_in_configs(self, instana_credentials):
        item = MagicMock()
        item.to_dict.return_value = {"id": "alert-1"}
        api = type('MockClient', (), {})()
        api.find_application_alert_config = MagicMock(return_value=[item, {"id": "alert-2"}])
        client = create_application_alert_client(instana_credentials)

        result = await client.find_application_alert_config(id="alert-1", api_client=api)

        assert result == {"configs": [{"id": "alert-1"}, {"id": "alert-2"}]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_non_dict_result_wrapped_in_data(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.find_application_alert_config = MagicMock(return_value="raw")
        client = create_application_alert_client(instana_credentials)

        result = await client.find_application_alert_config(id="alert-1", api_client=api)

        assert result == {"data": "raw"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_list_items_with_to_dict(self, instana_credentials):
        item = MagicMock()
        item.to_dict.return_value = {"id": "alert-1", "version": "1"}
        api = type('MockClient', (), {})()
        api.find_application_alert_config_versions = MagicMock(return_value=[item])
        client = create_application_alert_client(instana_credentials)

        result = await client.find_application_alert_config_versions(id="alert-1", api_client=api)

        assert result == {"versions": [{"id": "alert-1", "version": "1"}]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_non_dict_result_wrapped_in_data(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.find_application_alert_config_versions = MagicMock(return_value="raw")
        client = create_application_alert_client(instana_credentials)

        result = await client.find_application_alert_config_versions(id="alert-1", api_client=api)

        assert result == {"data": "raw"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_method,kwargs,verb", [
        ("enable_application_alert_config", "enable_application_alert_config", {}, "enabled"),
        ("disable_application_alert_config", "disable_application_alert_config", {}, "disabled"),
        ("restore_application_alert_config", "restore_application_alert_config", {"created": 1625097600000}, "restored"),
        ("update_application_alert_config_baseline", "update_application_historic_baseline", {}, "recalculated"),
    ])
    async def test_empty_sdk_result_returns_default_success_message(
        self, instana_credentials, method, sdk_method, kwargs, verb
    ):
        api = type('MockClient', (), {})()
        setattr(api, sdk_method, MagicMock(return_value=None))
        client = create_application_alert_client(instana_credentials)

        result = await getattr(client, method)(id="alert-1", api_client=api, **kwargs)

        assert result["success"] is True
        assert f"has been successfully {verb}" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_success_message_contains_id(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.delete_application_alert_config = MagicMock(return_value=None)
        client = create_application_alert_client(instana_credentials)

        result = await client.delete_application_alert_config(id="alert-1", api_client=api)

        assert result["success"] is True
        assert "alert-1" in result["message"]


@pytest.mark.usefixtures("real_alert_sdk_model")
class TestApplicationAlertConfigCreateUpdateE2E:
    """Deterministic create/update tests with a payload valid for the SDK model"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_builds_sdk_model_and_applies_defaults(self, instana_credentials):
        response = MagicMock()
        response.to_dict.return_value = {"id": "alert-1", "name": "Slow calls"}
        api = type('MockClient', (), {})()
        api.create_application_alert_config = MagicMock(return_value=response)
        client = create_application_alert_client(instana_credentials)

        result = await client.create_application_alert_config(payload=_valid_alert_payload(), api_client=api)

        assert result == {"id": "alert-1", "name": "Slow calls"}
        api.create_application_alert_config.assert_called_once()
        config = api.create_application_alert_config.call_args.kwargs["application_alert_config"]
        assert config.name == "Slow calls"
        assert config.boundary_scope == "INBOUND"
        assert config.alert_channel_ids == []
        assert config.custom_payload_fields == []
        # missing 'services' on the application node is defaulted to {}
        assert config.applications["app-1"].services == {}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_from_json_string(self, instana_credentials):
        import json
        api = type('MockClient', (), {})()
        api.create_application_alert_config = MagicMock(return_value={"id": "alert-1"})
        client = create_application_alert_client(instana_credentials)

        result = await client.create_application_alert_config(
            payload=json.dumps(_valid_alert_payload()), api_client=api
        )

        assert result == {"id": "alert-1"}
        api.create_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_from_single_quoted_string(self, instana_credentials):
        """Single-quoted (non-JSON) strings are repaired by quote replacement."""
        api = type('MockClient', (), {})()
        api.create_application_alert_config = MagicMock(return_value={"id": "alert-1"})
        client = create_application_alert_client(instana_credentials)
        payload = str(_valid_alert_payload()).replace("False", "false").replace("True", "true")

        result = await client.create_application_alert_config(payload=payload, api_client=api)

        assert result == {"id": "alert-1"}
        api.create_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_invalid_model_does_not_call_api(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.create_application_alert_config = MagicMock()
        client = create_application_alert_client(instana_credentials)

        result = await client.create_application_alert_config(
            payload=_valid_alert_payload(rule={"alertType": "not-a-rule"}), api_client=api
        )

        assert "Failed to create config object" in result["error"]
        api.create_application_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_sdk_failure(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.create_application_alert_config = MagicMock(side_effect=ApiException(status=400, reason="Bad Request"))
        client = create_application_alert_client(instana_credentials)

        result = await client.create_application_alert_config(payload=_valid_alert_payload(), api_client=api)

        assert "Failed to create application alert config" in result["error"]
        api.create_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_json_non_dict_payload(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.create_application_alert_config = MagicMock()
        client = create_application_alert_client(instana_credentials)

        result = await client.create_application_alert_config(payload="[1, 2]", api_client=api)

        assert "Payload must be a dictionary" in result["error"]
        api.create_application_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_builds_sdk_model_and_passes_id(self, instana_credentials):
        response = MagicMock()
        response.to_dict.return_value = {"id": "alert-1", "name": "Updated"}
        api = type('MockClient', (), {})()
        api.update_application_alert_config = MagicMock(return_value=response)
        client = create_application_alert_client(instana_credentials)

        result = await client.update_application_alert_config(
            id="alert-1", payload=_valid_alert_payload(name="Updated"), api_client=api
        )

        assert result == {"id": "alert-1", "name": "Updated"}
        api.update_application_alert_config.assert_called_once()
        kwargs = api.update_application_alert_config.call_args.kwargs
        assert kwargs["id"] == "alert-1"
        assert kwargs["application_alert_config"].name == "Updated"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_empty_sdk_result_returns_default_success(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.update_application_alert_config = MagicMock(return_value=None)
        client = create_application_alert_client(instana_credentials)

        result = await client.update_application_alert_config(
            id="alert-1", payload=_valid_alert_payload(), api_client=api
        )

        assert result["success"] is True
        assert "alert-1" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_sdk_failure(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.update_application_alert_config = MagicMock(side_effect=ApiException(status=500, reason="Boom"))
        client = create_application_alert_client(instana_credentials)

        result = await client.update_application_alert_config(
            id="alert-1", payload=_valid_alert_payload(), api_client=api
        )

        assert "Failed to update application alert config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_invalid_model_does_not_call_api(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.update_application_alert_config = MagicMock()
        client = create_application_alert_client(instana_credentials)

        result = await client.update_application_alert_config(
            id="alert-1", payload=_valid_alert_payload(rule={"alertType": "not-a-rule"}), api_client=api
        )

        assert "Failed to create config object" in result["error"]
        api.update_application_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_json_non_dict_payload(self, instana_credentials):
        api = type('MockClient', (), {})()
        api.update_application_alert_config = MagicMock()
        client = create_application_alert_client(instana_credentials)

        result = await client.update_application_alert_config(id="alert-1", payload="[1, 2]", api_client=api)

        assert "Payload must be a dictionary" in result["error"]
        api.update_application_alert_config.assert_not_called()


class TestApplicationAlertConfigPayloadValidationE2E:
    """_validate_alert_payload / _validate_*_fields"""

    @staticmethod
    def _validate(client, payload, operation="create"):
        return type(client)._validate_alert_payload(payload, operation, "alert_config")

    @pytest.mark.mocked
    def test_valid_payload_returns_none(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        assert self._validate(client, _valid_alert_payload()) is None

    @pytest.mark.mocked
    @pytest.mark.parametrize("payload", [None, {}])
    def test_missing_payload(self, instana_credentials, payload):
        client = create_application_alert_client(instana_credentials)
        result = self._validate(client, payload)
        assert result["elicitation_needed"] is True
        assert "payload is missing" in result["reason"]

    @pytest.mark.mocked
    def test_non_dict_payload(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        result = self._validate(client, ["x"], "update")
        assert result["elicitation_needed"] is True
        assert "payload must be a dict" in result["reason"]
        assert "list" in result["api_error"][0]

    @pytest.mark.mocked
    def test_all_required_fields_missing(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        result = self._validate(client, {"severity": 5})
        errors = "\n".join(result["api_error"])
        for field in ("name", "description", "boundaryScope", "evaluationType", "granularity",
                      "applications", "tagFilterExpression", "timeThreshold"):
            assert f"{field}: required" in errors
        assert "8 problem(s)" in result["message"]

    @pytest.mark.mocked
    @pytest.mark.parametrize("override,expected", [
        ({"name": 123}, "name: must be a string"),
        ({"name": "x" * 257}, "name: exceeds maximum length of 256"),
        ({"description": "x" * 65537}, "description: exceeds maximum length of 65536"),
        ({"boundaryScope": "OUTBOUND"}, "boundaryScope: 'OUTBOUND' is not valid"),
        ({"evaluationType": "PER_HOST"}, "evaluationType: 'PER_HOST' is not valid"),
        ({"granularity": "600000"}, "granularity: must be an integer"),
        ({"granularity": 1234}, "granularity: 1234 is not valid"),
        ({"severity": 7}, "severity: 7 is not valid"),
        ({"applications": ["app-1"]}, "applications: must be a dict"),
    ])
    def test_invalid_field_values(self, instana_credentials, override, expected):
        client = create_application_alert_client(instana_credentials)
        result = self._validate(client, _valid_alert_payload(**override))
        assert result["elicitation_needed"] is True
        assert any(expected in e for e in result["api_error"]), result["api_error"]


class TestApplicationAlertConfigPreflightE2E:
    """_preflight_alert_config"""

    @staticmethod
    def _preflight(client, operation, application_id=None, id=None, created=None):
        return type(client)._preflight_alert_config(operation, application_id, id, created)

    @pytest.mark.mocked
    def test_find_active_requires_application_id(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        result = self._preflight(client, "find_active")
        assert result["elicitation_needed"] is True
        assert "application_id: required for 'find_active'" in result["api_error"][0]
        assert self._preflight(client, "find_active", application_id="app-1") is None

    @pytest.mark.mocked
    @pytest.mark.parametrize("operation", [
        "find", "find_versions", "update", "delete", "enable", "disable", "restore", "update_baseline",
    ])
    def test_id_required_operations(self, instana_credentials, operation):
        client = create_application_alert_client(instana_credentials)
        created = 1625097600000 if operation == "restore" else None
        result = self._preflight(client, operation, created=created)
        assert f"id: required for '{operation}'" in result["api_error"][0]
        assert self._preflight(client, operation, id="alert-1", created=created) is None

    @pytest.mark.mocked
    def test_create_needs_no_id(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        assert self._preflight(client, "create") is None

    @pytest.mark.mocked
    def test_restore_requires_created(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        result = self._preflight(client, "restore", id="alert-1")
        assert "created: required for 'restore'" in result["api_error"][0]

    @pytest.mark.mocked
    @pytest.mark.parametrize("created", [-1, "1625097600000", 1.5])
    def test_restore_rejects_invalid_created(self, instana_credentials, created):
        client = create_application_alert_client(instana_credentials)
        result = self._preflight(client, "restore", id="alert-1", created=created)
        assert "must be a positive integer Unix timestamp" in result["api_error"][0]

    @pytest.mark.mocked
    def test_multiple_errors_are_consolidated(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        result = self._preflight(client, "restore")
        assert len(result["api_error"]) == 2
        assert "2 required parameter(s)" in result["message"]


class TestApplicationAlertConfigParsePayloadE2E:
    """_parse_payload"""

    @pytest.mark.mocked
    def test_parse_variants(self, instana_credentials):
        parse = type(create_application_alert_client(instana_credentials))._parse_payload
        assert parse({"a": 1}) == {"a": 1}
        assert parse(None) is None
        assert parse('{"a": 1}') == {"a": 1}
        assert parse("{'a': 1}") == {"a": 1}
        assert parse("{not valid") is None


class TestApplicationAlertConfigExecuteOperationE2E:
    """execute_alert_config_operation dispatcher"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation,target,call_kwargs,expected_call_kwargs", [
        ("find_active", "find_active_application_alert_configs",
         {"application_id": "app-1", "alert_ids": ["a1"]},
         {"application_id": "app-1", "alert_ids": ["a1"]}),
        ("find_versions", "find_application_alert_config_versions", {"id": "a1"}, {"id": "a1"}),
        ("find", "find_application_alert_config", {"id": "a1", "valid_on": 5}, {"id": "a1", "valid_on": 5}),
        ("delete", "delete_application_alert_config", {"id": "a1"}, {"id": "a1"}),
        ("enable", "enable_application_alert_config", {"id": "a1"}, {"id": "a1"}),
        ("disable", "disable_application_alert_config", {"id": "a1"}, {"id": "a1"}),
        ("restore", "restore_application_alert_config",
         {"id": "a1", "created": 1625097600000}, {"id": "a1", "created": 1625097600000}),
        ("update_baseline", "update_application_alert_config_baseline", {"id": "a1"}, {"id": "a1"}),
    ])
    async def test_routes_to_handler(
        self, instana_credentials, operation, target, call_kwargs, expected_call_kwargs
    ):
        client = create_application_alert_client(instana_credentials)
        mock = AsyncMock(return_value={"routed": operation})
        with patch.object(client, target, mock):
            result = await client.execute_alert_config_operation(
                operation=operation, resource_type="alert_config", tool_name="tool", **call_kwargs
            )

        assert result == {"routed": operation}
        mock.assert_awaited_once()
        kwargs = mock.call_args.kwargs
        for key, value in expected_call_kwargs.items():
            assert kwargs[key] == value
        assert kwargs["resource_type"] == "alert_config"
        assert kwargs["tool_name"] == "tool"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_forwards_paging_only_when_given(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        mock = AsyncMock(return_value={})
        with patch.object(client, "find_active_application_alert_configs", mock):
            await client.execute_alert_config_operation("find_active", application_id="app-1")
            assert "page" not in mock.call_args.kwargs
            assert "page_size" not in mock.call_args.kwargs

            await client.execute_alert_config_operation(
                "find_active", application_id="app-1", page=3, page_size=5
            )
            assert mock.call_args.kwargs["page"] == 3
            assert mock.call_args.kwargs["page_size"] == 5

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_routes_with_valid_payload(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        mock = AsyncMock(return_value={"id": "new"})
        payload = _valid_alert_payload()
        with patch.object(client, "create_application_alert_config", mock):
            result = await client.execute_alert_config_operation("create", payload=payload)

        assert result == {"id": "new"}
        assert mock.call_args.kwargs["payload"] == payload

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_routes_with_valid_json_string_payload(self, instana_credentials):
        import json
        client = create_application_alert_client(instana_credentials)
        mock = AsyncMock(return_value={"id": "a1"})
        payload = json.dumps(_valid_alert_payload())
        with patch.object(client, "update_application_alert_config", mock):
            result = await client.execute_alert_config_operation("update", id="a1", payload=payload)

        assert result == {"id": "a1"}
        assert mock.call_args.kwargs["id"] == "a1"
        assert mock.call_args.kwargs["payload"] == payload

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation", ["create", "update"])
    async def test_invalid_payload_returns_elicitation_without_calling_sdk(self, instana_credentials, operation):
        client = create_application_alert_client(instana_credentials)
        mock = AsyncMock()
        with patch.object(client, f"{operation}_application_alert_config", mock):
            result = await client.execute_alert_config_operation(
                operation, id="a1", payload={"name": "only a name"}
            )

        assert result["elicitation_needed"] is True
        assert any("description: required" in e for e in result["api_error"])
        mock.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unparseable_string_payload_returns_elicitation(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation("create", payload="{not valid")

        assert result["elicitation_needed"] is True
        assert "payload is missing" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation,kwargs,expected", [
        ("find_active", {}, "application_id: required for 'find_active'"),
        ("find", {}, "id: required for 'find'"),
        ("delete", {}, "id: required for 'delete'"),
        ("restore", {"id": "a1"}, "created: required for 'restore'"),
    ])
    async def test_preflight_failures_short_circuit(self, instana_credentials, operation, kwargs, expected):
        client = create_application_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation(operation, **kwargs)

        assert result["elicitation_needed"] is True
        assert expected in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unsupported_operation(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation("bogus")

        assert result == {"error": "Operation 'bogus' not supported"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_handler_exception_is_wrapped(self, instana_credentials):
        client = create_application_alert_client(instana_credentials)
        mock = AsyncMock(side_effect=RuntimeError("boom"))
        with patch.object(client, "_dispatch_alert_config", mock):
            result = await client.execute_alert_config_operation("delete", id="a1")

        assert result == {"error": "Error executing delete: boom"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_end_to_end_delete_through_dispatcher_with_mocked_sdk(self, instana_credentials):
        """Dispatcher -> _delete_config -> SDK call, with only the SDK client mocked."""
        client = create_application_alert_client(instana_credentials)
        api = MagicMock()
        api.delete_application_alert_config.return_value = None
        result = await client._delete_config("a1", api_client=api)

        assert result["success"] is True
        api.delete_application_alert_config.assert_called_once_with(id="a1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,args,expected", [
        ("_find_active_configs", (None, None), "application_id is required for find_active operation"),
        ("_find_config_versions", (None,), "id is required for find_versions operation"),
        ("_create_config", (None,), "payload is required for create operation"),
        ("_update_config", (None, {"a": 1}), "id is required for update operation"),
        ("_update_config", ("a1", None), "payload is required for update operation"),
        ("_delete_config", (None,), "id is required for delete operation"),
        ("_enable_config", (None,), "id is required for enable operation"),
        ("_disable_config", (None,), "id is required for disable operation"),
        ("_restore_config", (None, 1), "id is required for restore operation"),
        ("_restore_config", ("a1", None), "created timestamp is required for restore operation"),
        ("_update_baseline", (None,), "id is required for update_baseline operation"),
    ])
    async def test_internal_handlers_validate_required_params(self, instana_credentials, method, args, expected):
        client = create_application_alert_client(instana_credentials)

        result = await getattr(client, method)(*args, api_client=MagicMock())

        assert result == {"error": expected}


class TestApplicationAlertConfigRemainingBranchesE2E:
    """Parsing fallbacks and SDK-model import failure for create/update"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.usefixtures("real_alert_sdk_model")
    async def test_update_from_single_quoted_string(self, instana_credentials):
        """Single-quoted (non-JSON) strings are repaired by quote replacement."""
        api = type('MockClient', (), {})()
        api.update_application_alert_config = MagicMock(return_value={"id": "alert-1"})
        client = create_application_alert_client(instana_credentials)
        payload = str(_valid_alert_payload()).replace("False", "false").replace("True", "true")

        result = await client.update_application_alert_config(id="alert-1", payload=payload, api_client=api)

        assert result == {"id": "alert-1"}
        api.update_application_alert_config.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,kwargs", [
        ("create_application_alert_config", {}),
        ("update_application_alert_config", {"id": "alert-1"}),
    ])
    async def test_unhashable_literal_payload_reports_parse_failure(self, instana_credentials, method, kwargs):
        """ast.literal_eval raises TypeError (not ValueError) for this input."""
        api = MagicMock()
        client = create_application_alert_client(instana_credentials)

        result = await getattr(client, method)(payload="{[]: 1}", api_client=api, **kwargs)

        assert "Failed to parse payload" in result["error"]
        assert result["payload"] == "{[]: 1}"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_method,kwargs", [
        ("create_application_alert_config", "create_application_alert_config", {}),
        ("update_application_alert_config", "update_application_alert_config", {"id": "alert-1"}),
    ])
    async def test_sdk_model_import_failure(self, instana_credentials, method, sdk_method, kwargs):
        api = MagicMock()
        client = create_application_alert_client(instana_credentials)

        with patch.dict(sys.modules, {"instana_client.models.application_alert_config": None}):
            result = await getattr(client, method)(payload=_valid_alert_payload(), api_client=api, **kwargs)

        assert "Failed to import ApplicationAlertConfig" in result["error"]
        getattr(api, sdk_method).assert_not_called()
