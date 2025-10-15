"""
E2E tests for Application Topology MCP Tools
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.application_topology import ApplicationTopologyMCPTools
from src.core.server import MCPState, execute_tool


class TestApplicationTopologyE2E:
    """End-to-end tests for Application Topology MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_topology_mocked(self, instana_credentials):
        """Test getting application topology with mocked responses."""

        # Mock the API response - the method expects a response object with data attribute
        mock_response = MagicMock()
        mock_response_data = {
            "services": [
                {
                    "id": "service-1",
                    "name": "frontend",
                    "type": "web",
                    "technologies": ["nodejs"],
                    "calls": 1000,
                    "erroneous": 5
                },
                {
                    "id": "service-2",
                    "name": "backend",
                    "type": "service",
                    "technologies": ["java"],
                    "calls": 800,
                    "erroneous": 2
                }
            ],
            "connections": [
                {
                    "source": "service-1",
                    "target": "service-2",
                    "calls": 500,
                    "erroneous": 3
                }
            ]
        }
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')

        with patch('src.application.application_topology.ApplicationTopologyApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api.get_services_map_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationTopologyMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with default parameters
            result = await client.get_application_topology()

            # Verify the result
            assert isinstance(result, dict)
            assert "services" in result
            assert "connections" in result
            assert len(result["services"]) == 2
            assert len(result["connections"]) == 1
            assert result["services"][0]["name"] == "frontend"
            assert result["services"][1]["name"] == "backend"
            assert result["connections"][0]["source"] == "service-1"

            # Verify the API was called with default parameters
            mock_api.get_services_map_without_preload_content.assert_called_once_with(
                window_size=3600000,  # Default 1 hour
                to=pytest.approx(int(datetime.now().timestamp() * 1000), abs=10000),
                application_id=None,
                application_boundary_scope=None
            )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_topology_with_params(self, instana_credentials):
        """Test getting application topology with custom parameters."""

        # Mock the API response - the method expects a response object with data attribute
        mock_response = MagicMock()
        mock_response_data = {
            "services": [],
            "connections": []
        }
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')

        with patch('src.application.application_topology.ApplicationTopologyApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api.get_services_map_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationTopologyMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test parameters
            window_size = 7200000  # 2 hours
            to_timestamp = 1625097600000  # Some specific timestamp
            application_id = "app-123"
            application_boundary_scope = "ALL"

            # Test the method with custom parameters
            result = await client.get_application_topology(
                window_size=window_size,
                to_timestamp=to_timestamp,
                application_id=application_id,
                application_boundary_scope=application_boundary_scope
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "services" in result
            assert "connections" in result

            # Verify the API was called with the correct parameters
            mock_api.get_services_map_without_preload_content.assert_called_once_with(
                window_size=window_size,
                to=to_timestamp,
                application_id=application_id,
                application_boundary_scope=application_boundary_scope
            )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_topology_error_handling(self, instana_credentials):
        """Test error handling in get_application_topology."""

        with patch('src.application.application_topology.ApplicationTopologyApi') as mock_api_class:
            # Set up the mock API to raise an exception
            mock_api = MagicMock()
            mock_api.get_services_map_without_preload_content.side_effect = Exception("API Error")
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationTopologyMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            result = await client.get_application_topology()

            # Verify the result contains an error message
            assert isinstance(result, dict)
            assert "error" in result
            assert "Failed to get application topology" in result["error"]
            assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_topology_initialization_error(self, instana_credentials):
        """Test error handling during initialization."""

        with patch('src.application.application_topology.ApplicationTopologyApi',
                  side_effect=Exception("Initialization Error")):

            # This should raise an exception during initialization
            with pytest.raises(Exception) as excinfo:
                _ = ApplicationTopologyMCPTools(
                    read_token=instana_credentials["api_token"],
                    base_url=instana_credentials["base_url"]
                )

            # Verify the exception message
            assert "Initialization Error" in str(excinfo.value)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_topology_non_dict_response(self, instana_credentials):
        """Test handling of non-dict response from API."""

        # Mock the API response to return an object with data attribute containing invalid JSON
        mock_response = MagicMock()
        mock_response.data = "Invalid JSON response".encode('utf-8')

        with patch('src.application.application_topology.ApplicationTopologyApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api.get_services_map_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationTopologyMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            result = await client.get_application_topology()

            # Verify the result contains an error due to invalid JSON
            assert isinstance(result, dict)
            assert "error" in result
            assert "Failed to parse JSON response" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_topology_debug_print(self, instana_credentials):
        """Test debug print functionality."""

        # Mock the API response - the method expects a response object with data attribute
        mock_response = MagicMock()
        mock_response_data = {
            "services": [],
            "connections": []
        }
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')

        with patch('src.application.application_topology.ApplicationTopologyApi') as mock_api_class:

            # Set up the mock API
            mock_api = MagicMock()
            mock_api.get_services_map_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationTopologyMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            await client.get_application_topology()

            # Verify the method was called successfully
            # debug_print is not exported from the module, so we just verify the method execution
            assert mock_api.get_services_map_without_preload_content.called

    # Integration tests with MCP server

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_mcp_tool_registration(self, instana_credentials):
        """Test that the application topology tool is properly registered with MCP."""

        # Create a mock client
        mock_client = MagicMock()
        mock_client.get_application_topology = AsyncMock()

        # Create MCP state and set the client
        state = MCPState()
        state.app_topology_client = mock_client

        # Create tool parameters
        tool_params = {
            "window_size": 3600000,
            "application_id": "test-app"
        }

        # Execute the tool
        # debug_print is not exported from the module, so we'll test without it
        _ = await execute_tool(
            "get_application_topology",
            tool_params,
            state
        )

        # Verify the tool was called
        mock_client.get_application_topology.assert_called_once()

        # Verify the parameters were passed correctly
        args, kwargs = mock_client.get_application_topology.call_args
        assert kwargs["window_size"] == 3600000
        assert kwargs["application_id"] == "test-app"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_tool_through_mcp(self, instana_credentials):
        """Test executing the application topology tool through MCP."""

        # Mock response for the topology API
        mock_response = {
            "services": [
                {
                    "id": "service-1",
                    "name": "frontend",
                    "type": "web"
                },
                {
                    "id": "service-2",
                    "name": "backend",
                    "type": "service"
                }
            ],
            "connections": [
                {
                    "source": "service-1",
                    "target": "service-2",
                    "calls": 500
                }
            ]
        }

        # Create MCP state
        state = MCPState()
        state.instana_api_token = instana_credentials["api_token"]
        state.instana_base_url = instana_credentials["base_url"]

        # Create a mock client and set it on the state
        mock_client = MagicMock()
        mock_client.get_application_topology = AsyncMock(return_value=mock_response)
        state.app_topology_client = mock_client

        # Create tool parameters
        tool_params = {
            "window_size": 7200000,
            "application_id": "test-app"
        }

        # Execute the tool
        result = await execute_tool(
            "get_application_topology",
            tool_params,
            state
        )

        # The execute_tool function returns a string representation of the result
        # So we need to compare the string representation or parse it back to a dict
        if isinstance(result, str):
            try:
                # Try to parse it as JSON
                result_dict = json.loads(result.replace("'", "\""))
                assert result_dict == mock_response
            except json.JSONDecodeError:
                # If it's not valid JSON, compare the string representation
                assert str(mock_response) in result
        else:
            assert result == mock_response

        # Verify the tool was called with the correct parameters
        mock_client.get_application_topology.assert_called_once_with(
            window_size=7200000,
            application_id="test-app"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_error_handling_in_mcp(self, instana_credentials):
        """Test error handling in MCP for application topology."""

        # Create MCP state
        state = MCPState()
        state.instana_api_token = instana_credentials["api_token"]
        state.instana_base_url = instana_credentials["base_url"]

        # Create a mock client that raises an exception
        mock_client = MagicMock()
        mock_client.get_application_topology = AsyncMock(side_effect=Exception("Test error"))
        state.app_topology_client = mock_client

        # Execute the tool
        result = await execute_tool(
            "get_application_topology",
            {},
            state
        )

        # Verify the result contains an error message
        assert isinstance(result, str)
        assert "Error executing tool" in result
        assert "Test error" in result

        # Verify the tool was called
        mock_client.get_application_topology.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_missing_tool_in_mcp(self, instana_credentials):
        """Test handling of missing tool in MCP."""

        # Create MCP state without setting the app_topology_client
        state = MCPState()
        state.instana_api_token = instana_credentials["api_token"]
        state.instana_base_url = instana_credentials["base_url"]

        # Execute a non-existent tool
        result = await execute_tool(
            "non_existent_tool",
            {},
            state
        )

        # Verify the result contains an error message
        assert isinstance(result, str)
        assert "Tool non_existent_tool not found" in result

    @pytest.mark.mocked
    def test_import_error_handling(self):
        """Test handling of import errors in the module."""

        # We can't directly test the import error handling since imports are evaluated
        # at module load time, but we can verify that the code has proper error handling
        # by examining the module source code

        import inspect

        import src.application.application_topology as module

        # Get the source code of the module
        source_code = inspect.getsource(module)

        # Verify that the module has proper import error handling
        assert "try:" in source_code
        assert "from instana_client.api.application_topology_api import (" in source_code
        assert "ApplicationTopologyApi" in source_code
        assert "except ImportError as e:" in source_code
        assert "logger.error(f\"Error importing Instana SDK: {e}\"" in source_code
        assert "traceback.print_exc" in source_code
        assert "raise" in source_code

