"""
E2E tests for Instana Client Base Module
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.utils import (
    BaseInstanaClient,
    register_as_tool,
    with_header_auth,
)


class MockApiClass:
    """Mock API class for testing the with_header_auth decorator."""
    def __init__(self, api_client=None):
        self.api_client = api_client

    def test_method(self):
        return {"result": "success"}

class TestInstanaClientBaseE2E:
    """End-to-end tests for the BaseInstanaClient class and related functions."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_register_as_tool_decorator(self):
        """Test that the register_as_tool decorator properly registers functions."""
        utils_module = importlib.import_module("src.core.utils")
        original_tools = utils_module.MCP_TOOLS.copy()
        utils_module.MCP_TOOLS.clear()

        try:
            # Define a test function and register it
            @register_as_tool()
            async def test_tool(ctx=None):
                return {"result": "success"}

            # Check that the function was registered
            assert "test_tool" in utils_module.MCP_TOOLS
            assert utils_module.MCP_TOOLS["test_tool"] == test_tool
        finally:
            # Restore the original tools
            utils_module.MCP_TOOLS.clear()
            utils_module.MCP_TOOLS.update(original_tools)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_base_client_initialization(self, instana_credentials):
        """Test that the BaseInstanaClient initializes correctly."""
        client = BaseInstanaClient(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_headers(self, instana_credentials):
        """Test that get_headers returns the correct headers."""
        client = BaseInstanaClient(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        headers = client.get_headers()
        assert headers["Authorization"] == (
            f"apiToken {instana_credentials['api_token']}"
        )
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    # Skip the context manager tests since they require complex mocking of relative imports
    # In a real-world scenario, we would use more advanced techniques to mock these imports
    # but for this demonstration, we'll skip these tests

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_header_auth_http_mode(self, instana_credentials):
        """Test with_header_auth decorator in HTTP mode."""

        mock_headers = {
            "instana-api-token": instana_credentials["api_token"],
            "instana-base-url": instana_credentials["base_url"]
        }

        class TestClient(BaseInstanaClient):
            def __init__(self, read_token, base_url):
                super().__init__(read_token, base_url)

            @with_header_auth(MockApiClass)
            async def test_method(self, param1, param2, ctx=None, api_client=None):
                assert api_client is not None
                assert isinstance(api_client, MockApiClass)
                return {"param1": param1, "param2": param2}

        mock_config = MagicMock()
        mock_config.api_key = {}
        mock_config.api_key_prefix = {}
        mock_api_client = MagicMock()

        with patch('src.core.auth_helper.get_http_headers', return_value=mock_headers), \
             patch('src.core.auth_helper.Configuration', return_value=mock_config), \
             patch('src.core.auth_helper.ApiClient', return_value=mock_api_client):

            client = TestClient(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )
            result = await client.test_method("value1", "value2")

            assert result == {"param1": "value1", "param2": "value2"}
            assert mock_config.host == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_header_auth_http_mode_missing_token(self, instana_credentials):
        """Test with_header_auth decorator in HTTP mode with missing token."""

        mock_headers = {
            "instana-base-url": instana_credentials["base_url"]
            # Missing token
        }

        class TestClient(BaseInstanaClient):
            def __init__(self, read_token, base_url):
                super().__init__(read_token, base_url)

            @with_header_auth(MockApiClass)
            async def test_method(self, param1, param2, ctx=None, api_client=None):
                return {"param1": param1, "param2": param2}

        with patch('src.core.auth_helper.get_http_headers', return_value=mock_headers):
            client = TestClient(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )
            result = await client.test_method("value1", "value2")

            assert "error" in result
            assert "missing required headers" in result["error"]
            assert "instana-api-token" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_header_auth_http_mode_missing_url(self, instana_credentials):
        """Test with_header_auth decorator in HTTP mode with missing URL."""

        mock_headers = {
            "instana-api-token": instana_credentials["api_token"]
            # Missing URL
        }

        class TestClient(BaseInstanaClient):
            def __init__(self, read_token, base_url):
                super().__init__(read_token, base_url)

            @with_header_auth(MockApiClass)
            async def test_method(self, param1, param2, ctx=None, api_client=None):
                return {"param1": param1, "param2": param2}

        with patch('src.core.auth_helper.get_http_headers', return_value=mock_headers):
            client = TestClient(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )
            result = await client.test_method("value1", "value2")

            assert "error" in result
            assert "missing required headers" in result["error"]
            assert "instana-base-url" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_header_auth_http_mode_invalid_url(self, instana_credentials):
        """Test with_header_auth decorator in HTTP mode with invalid URL format."""

        mock_headers = {
            "instana-api-token": instana_credentials["api_token"],
            "instana-base-url": "invalid-url-without-protocol"
        }

        class TestClient(BaseInstanaClient):
            def __init__(self, read_token, base_url):
                super().__init__(read_token, base_url)

            @with_header_auth(MockApiClass)
            async def test_method(self, param1, param2, ctx=None, api_client=None):
                return {"param1": param1, "param2": param2}

        with patch('src.core.auth_helper.get_http_headers', return_value=mock_headers):
            client = TestClient(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )
            result = await client.test_method("value1", "value2")

            assert "error" in result
            assert "must start with http:// or https://" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_header_auth_stdio_mode_import_error(self, instana_credentials):
        """Test with_header_auth decorator in STDIO mode when HTTP mode import fails."""

        class TestClient(BaseInstanaClient):
            def __init__(self, read_token, base_url):
                super().__init__(read_token, base_url)

            @with_header_auth(MockApiClass)
            async def test_method(self, param1, param2, ctx=None, api_client=None):
                assert api_client is not None
                assert isinstance(api_client, MockApiClass)
                return {"param1": param1, "param2": param2}

        mock_config = MagicMock()
        mock_config.api_key = {}
        mock_config.api_key_prefix = {}
        mock_api_client = MagicMock()

        # Simulate HTTP mode unavailable (AttributeError on get_http_headers)
        with patch('src.core.auth_helper.get_http_headers', side_effect=AttributeError), \
             patch('src.core.auth_helper.Configuration', return_value=mock_config), \
             patch('src.core.auth_helper.ApiClient', return_value=mock_api_client):

            client = TestClient(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )
            result = await client.test_method("value1", "value2")

            assert result == {"param1": "value1", "param2": "value2"}
            assert mock_config.host == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_header_auth_stdio_mode_missing_credentials(self):
        """Test with_header_auth decorator in STDIO mode with missing credentials."""

        # Create a test class with a decorated method
        class TestClient(BaseInstanaClient):
            def __init__(self, read_token, base_url):
                super().__init__(read_token, base_url)

            @with_header_auth(MockApiClass)
            async def test_method(self, param1, param2, ctx=None, api_client=None):
                return {"param1": param1, "param2": param2}

        with patch('src.core.auth_helper.get_http_headers', side_effect=AttributeError):
            client = TestClient(
                read_token="",  # Empty token
                base_url="https://example.com"
            )
            result = await client.test_method("value1", "value2")

            assert "error" in result
            assert "Authentication failed" in result["error"]
            assert "INSTANA_API_TOKEN is missing" in result["error"]

            client = TestClient(
                read_token="token",
                base_url=""  # Empty URL
            )
            result = await client.test_method("value1", "value2")

            assert "error" in result
            assert "Authentication failed" in result["error"]
            assert "INSTANA_BASE_URL is missing" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_header_auth_stdio_mode_existing_api_client(
        self, instana_credentials
    ):
        """Test with_header_auth decorator in STDIO mode with existing API client."""

        # Create a mock API instance
        mock_api_instance = MockApiClass()

        # Create a test class with a decorated method and existing API client
        class TestClient(BaseInstanaClient):
            def __init__(self, read_token, base_url):
                super().__init__(read_token, base_url)
                self.test_api = mock_api_instance  # Name must end with '_api'

            @with_header_auth(MockApiClass)
            async def test_method(self, param1, param2, ctx=None, api_client=None):
                assert api_client is not None
                assert api_client is mock_api_instance
                return {"param1": param1, "param2": param2}

        with patch('src.core.auth_helper.get_http_headers', side_effect=AttributeError):
            client = TestClient(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )
            result = await client.test_method("value1", "value2")

            assert result == {"param1": "value1", "param2": "value2"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_header_auth_exception_handling(self, instana_credentials):
        """Test exception handling in with_header_auth decorator."""

        class TestClient(BaseInstanaClient):
            def __init__(self, read_token, base_url):
                super().__init__(read_token, base_url)

            @with_header_auth(MockApiClass)
            async def test_method(self, param1, param2, ctx=None, api_client=None):
                raise Exception("Test exception")

        mock_config = MagicMock()
        mock_config.api_key = {}
        mock_config.api_key_prefix = {}
        mock_api_client = MagicMock()

        with patch('src.core.auth_helper.get_http_headers', side_effect=AttributeError), \
             patch('src.core.auth_helper.Configuration', return_value=mock_config), \
             patch('src.core.auth_helper.ApiClient', return_value=mock_api_client):

            client = TestClient(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )
            result = await client.test_method("value1", "value2")

            assert "error" in result
            assert "Authentication error" in result["error"]
            assert "Test exception" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_header_auth_sdk_import_error(self, instana_credentials):
        """Test with_header_auth decorator handling SDK import errors."""

        class TestClient(BaseInstanaClient):
            def __init__(self, read_token, base_url):
                super().__init__(read_token, base_url)

            @with_header_auth(MockApiClass)
            async def test_method(self, param1, param2, ctx=None, api_client=None):
                return {"param1": param1, "param2": param2}

        # Simulate HTTP mode unavailable and SDK raising on construction
        with patch('src.core.auth_helper.get_http_headers', side_effect=AttributeError), \
             patch('src.core.auth_helper.Configuration', side_effect=ImportError("SDK import error")):

            client = TestClient(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )
            result = await client.test_method("value1", "value2")

            assert "error" in result
            assert "Authentication error" in result["error"]


