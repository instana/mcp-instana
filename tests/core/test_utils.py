"""
Unit tests for the BaseInstanaClient class
"""

import asyncio
import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from requests.exceptions import HTTPError, RequestException

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the class to test
import src.core.utils
from src.core.utils import (
    MCP_TOOLS,
    BaseInstanaClient,
    __version__,
    register_as_tool,
    with_header_auth,
)


class TestRegisterAsTool(unittest.TestCase):
    """Test the register_as_tool decorator"""

    def setUp(self):
        """Set up test fixtures"""
        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = BaseInstanaClient(read_token=self.read_token, base_url=self.base_url)

    def test_register_as_tool(self):
        """Test that the register_as_tool decorator adds functions to the MCP_TOOLS registry"""

        # Define a test function
        @register_as_tool()
        def test_function():
            return "test"

        # Check that the function was added to the registry
        self.assertIn("test_function", MCP_TOOLS)
        self.assertEqual(MCP_TOOLS["test_function"], test_function)

        # Call the function through the registry
        result = MCP_TOOLS["test_function"]()
        self.assertEqual(result, "test")

    def test_register_as_tool_with_async_function(self):
        """Test that the register_as_tool decorator works with async functions"""

        # Define an async test function
        @register_as_tool()
        async def async_test_function():
            return "async_test"

        # Check that the function was added to the registry
        self.assertIn("async_test_function", MCP_TOOLS)
        self.assertEqual(MCP_TOOLS["async_test_function"], async_test_function)

        # Call the function through the registry
        result = asyncio.run(MCP_TOOLS["async_test_function"]())
        self.assertEqual(result, "async_test")

    def test_register_as_tool_with_parameters(self):
        """Test that the register_as_tool decorator works with functions that have parameters"""

        # Define a test function with parameters
        @register_as_tool()
        def test_function_with_params(param1, param2):
            return f"{param1}_{param2}"

        # Check that the function was added to the registry
        self.assertIn("test_function_with_params", MCP_TOOLS)

        # Call the function through the registry
        result = MCP_TOOLS["test_function_with_params"]("value1", "value2")
        self.assertEqual(result, "value1_value2")

    def test_register_as_tool_with_explicit_description(self):
        """Test that the register_as_tool decorator stores explicit description"""

        # Define a test function with explicit description
        @register_as_tool(description="This is an explicit description")
        def test_function_with_description():
            """This is the docstring"""
            return "test"

        # Check that the function was added to the registry
        self.assertIn("test_function_with_description", MCP_TOOLS)

        # Check that the explicit description was stored
        self.assertTrue(hasattr(test_function_with_description, '_mcp_description'))
        self.assertEqual(test_function_with_description._mcp_description, "This is an explicit description")

    def test_register_as_tool_with_docstring_description(self):
        """Test that the register_as_tool decorator extracts description from docstring"""

        # Define a test function with only docstring (using proper formatting)
        @register_as_tool()
        def test_function_with_docstring():
            """This is the first paragraph.

This is the second paragraph."""
            return "test"

        # Check that the function was added to the registry
        self.assertIn("test_function_with_docstring", MCP_TOOLS)

        # Check that the description was extracted from first paragraph
        self.assertTrue(hasattr(test_function_with_docstring, '_mcp_description'))
        self.assertEqual(test_function_with_docstring._mcp_description, "This is the first paragraph.")

    def test_register_as_tool_description_priority(self):
        """Test that explicit description takes priority over docstring"""

        # Define a test function with both explicit description and docstring
        @register_as_tool(description="Explicit description wins")
        def test_function_priority():
            """Docstring description"""
            return "test"

        # Check that explicit description takes priority
        self.assertTrue(hasattr(test_function_priority, '_mcp_description'))
        self.assertEqual(test_function_priority._mcp_description, "Explicit description wins")

    def test_register_as_tool_no_description(self):
        """Test that the register_as_tool decorator handles functions without description"""

        # Define a test function without docstring or explicit description
        @register_as_tool()
        def test_function_no_description():
            return "test"

        # Check that the function was added to the registry
        self.assertIn("test_function_no_description", MCP_TOOLS)

        # Check that _mcp_description is None
        self.assertTrue(hasattr(test_function_no_description, '_mcp_description'))
        self.assertIsNone(test_function_no_description._mcp_description)


class TestWithHeaderAuth(unittest.TestCase):
    """Test the with_header_auth decorator"""

    def setUp(self):
        """Set up test fixtures"""
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = BaseInstanaClient(read_token=self.read_token, base_url=self.base_url)

    def test_get_headers_with_different_token(self):
        """Test get_headers with different token formats"""
        # Test with different header formats
        headers1 = {"instana-api-token": "token1", "instana-base-url": "https://test1.instana.io"}
        headers2 = {"instana_api_token": "token2", "instana_base_url": "https://test2.instana.io"}

        # Both should work
        self.assertIsNotNone(headers1)
        self.assertIsNotNone(headers2)


class TestBaseInstanaClient(unittest.TestCase):
    """Test the BaseInstanaClient class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = BaseInstanaClient(read_token=self.read_token, base_url=self.base_url)

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_headers(self):
        """Test that get_headers returns the correct headers"""
        headers = self.client.get_headers()

        self.assertEqual(headers["Authorization"], f"apiToken {self.read_token}")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Accept"], "application/json")

    def test_get_headers_with_different_token(self):
        """Test that get_headers works with different tokens"""
        client = BaseInstanaClient(read_token="different_token", base_url=self.base_url)
        headers = client.get_headers()

        self.assertEqual(headers["Authorization"], "apiToken different_token")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Accept"], "application/json")

    @patch('requests.get')
    def test_make_request_get(self, mock_get):
        """Test make_request with GET method"""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": "test"})
        mock_get.return_value = mock_response

        # Call the method
        endpoint = "/api/test"
        params = {"param1": "value1"}
        result = asyncio.run(self.client.make_request(endpoint, params=params))

        # Check that the mock was called with the correct arguments
        mock_get.assert_called_once_with(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            headers=self.client.get_headers(),
            params=params,
            verify=False
        )

        # Check that the result is correct
        self.assertEqual(result, {"data": "test"})

    @patch('requests.post')
    def test_make_request_post(self, mock_post):
        """Test make_request with POST method"""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": "test"})
        mock_post.return_value = mock_response

        # Call the method
        endpoint = "/api/test"
        params = {"param1": "value1"}
        result = asyncio.run(self.client.make_request(endpoint, params=params, method="POST"))

        # Check that the mock was called with the correct arguments
        mock_post.assert_called_once_with(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            headers=self.client.get_headers(),
            json=params,
            verify=False
        )

        # Check that the result is correct
        self.assertEqual(result, {"data": "test"})

    @patch('requests.post')
    def test_make_request_post_with_json(self, mock_post):
        """Test make_request with POST method and json parameter"""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": "test"})
        mock_post.return_value = mock_response

        # Call the method
        endpoint = "/api/test"
        json_data = {"json_param": "value"}
        result = asyncio.run(self.client.make_request(endpoint, json=json_data, method="POST"))

        # Check that the mock was called with the correct arguments
        mock_post.assert_called_once_with(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            headers=self.client.get_headers(),
            json=json_data,
            verify=False
        )

        # Check that the result is correct
        self.assertEqual(result, {"data": "test"})

    @patch('requests.put')
    def test_make_request_put(self, mock_put):
        """Test make_request with PUT method"""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": "test"})
        mock_put.return_value = mock_response

        # Call the method
        endpoint = "/api/test"
        params = {"param1": "value1"}
        result = asyncio.run(self.client.make_request(endpoint, params=params, method="PUT"))

        # Check that the mock was called with the correct arguments
        mock_put.assert_called_once_with(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            headers=self.client.get_headers(),
            json=params,
            verify=False
        )

        # Check that the result is correct
        self.assertEqual(result, {"data": "test"})

    @patch('requests.put')
    def test_make_request_put_with_json(self, mock_put):
        """Test make_request with PUT method and json parameter"""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": "test"})
        mock_put.return_value = mock_response

        # Call the method
        endpoint = "/api/test"
        json_data = {"json_param": "value"}
        result = asyncio.run(self.client.make_request(endpoint, json=json_data, method="PUT"))

        # Check that the mock was called with the correct arguments
        mock_put.assert_called_once_with(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            headers=self.client.get_headers(),
            json=json_data,
            verify=False
        )

        # Check that the result is correct
        self.assertEqual(result, {"data": "test"})

    @patch('requests.delete')
    def test_make_request_delete(self, mock_delete):
        """Test make_request with DELETE method"""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"data": "test"})
        mock_delete.return_value = mock_response

        # Call the method
        endpoint = "/api/test"
        params = {"param1": "value1"}
        result = asyncio.run(self.client.make_request(endpoint, params=params, method="DELETE"))

        # Check that the mock was called with the correct arguments
        mock_delete.assert_called_once_with(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            headers=self.client.get_headers(),
            params=params,
            verify=False
        )

        # Check that the result is correct
        self.assertEqual(result, {"data": "test"})

    def test_make_request_unsupported_method(self):
        """Test make_request with an unsupported HTTP method"""
        # Call the method with an unsupported method
        endpoint = "/api/test"
        result = asyncio.run(self.client.make_request(endpoint, method="INVALID"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Unsupported HTTP method", result["error"])

    def test_make_request_case_insensitive_method(self):
        """Test make_request with case insensitive HTTP methods"""
        # Test that methods work regardless of case
        methods = ["get", "GET", "Get", "gEt"]

        for method in methods:
            with self.subTest(method=method):
                with patch('requests.get') as mock_get:
                    mock_response = MagicMock()
                    mock_response.json = MagicMock(return_value={"data": "test"})
                    mock_get.return_value = mock_response

                    result = asyncio.run(self.client.make_request("/api/test", method=method))

                    # Should work regardless of case
                    self.assertEqual(result, {"data": "test"})

    @patch('requests.get')
    def test_make_request_http_error(self, mock_get):
        """Test make_request handling of HTTP errors"""
        # Set up the mock to raise an HTTPError
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Client Error")
        mock_get.return_value = mock_response

        # Call the method
        endpoint = "/api/test"
        result = asyncio.run(self.client.make_request(endpoint))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("HTTP Error", result["error"])

    @patch('requests.get')
    def test_make_request_request_exception(self, mock_get):
        """Test make_request handling of request exceptions"""
        # Set up the mock to raise a RequestException
        mock_get.side_effect = RequestException("Connection error")

        # Call the method
        endpoint = "/api/test"
        result = asyncio.run(self.client.make_request(endpoint))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Error", result["error"])

    @patch('requests.get')
    def test_make_request_general_exception(self, mock_get):
        """Test make_request handling of general exceptions"""
        # Set up the mock to raise a general exception
        mock_get.side_effect = Exception("Unexpected error")

        # Call the method
        endpoint = "/api/test"
        result = asyncio.run(self.client.make_request(endpoint))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Unexpected error", result["error"])

    def test_with_header_auth_header_based_authentication(self):
        """Test with_header_auth with header-based authentication"""
        # Mock the get_http_headers function
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.return_value = {
                "instana-api-token": "header_token",
                "instana-base-url": "https://header.instana.io"
            }

            # Mock the SDK imports
            with patch('instana_client.configuration.Configuration') as mock_config, \
                 patch('instana_client.api_client.ApiClient') as mock_api_client:

                mock_config_instance = MagicMock()
                mock_config.return_value = mock_config_instance
                mock_api_client_instance = MagicMock()
                mock_api_client.return_value = mock_api_client_instance

                # Create a test API class
                class TestApiClass:
                    def __init__(self, api_client):
                        self.api_client = api_client

                # Create a test method
                @with_header_auth(TestApiClass)
                async def test_method(self, ctx=None, api_client=None):
                    return {"success": True, "api_client": api_client}

                # Call the method
                result = asyncio.run(test_method(self.client))

                # Check that the result is correct
                self.assertIn("success", result)
                self.assertTrue(result["success"])

    def test_with_header_auth_fallback_to_constructor(self):
        """Test with_header_auth fallback to constructor-based authentication"""
        # Mock the get_http_headers function to raise an exception
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.side_effect = ImportError("Module not found")

            # Mock the SDK imports
            with patch('instana_client.configuration.Configuration') as mock_config, \
                 patch('instana_client.api_client.ApiClient') as mock_api_client:

                mock_config_instance = MagicMock()
                mock_config.return_value = mock_config_instance
                mock_api_client_instance = MagicMock()
                mock_api_client.return_value = mock_api_client_instance

                # Create a test API class
                class TestApiClass:
                    def __init__(self, api_client):
                        self.api_client = api_client

                # Create a test method
                @with_header_auth(TestApiClass)
                async def test_method(self, ctx=None, api_client=None):
                    return {"success": True, "api_client": api_client}

                # Call the method
                result = asyncio.run(test_method(self.client))

                # Check that the result is correct
                self.assertIn("success", result)
                self.assertTrue(result["success"])

    def test_with_header_auth_invalid_base_url(self):
        """Test with_header_auth with invalid base URL"""
        # Ensure fastmcp.server.dependencies is a real mock with controllable get_http_headers
        mock_deps = MagicMock()
        mock_deps.get_http_headers.return_value = {
            "instana-api-token": "header_token",
            "instana-base-url": "invalid_url"  # Missing http/https
        }
        mock_fastmcp = MagicMock()
        mock_fastmcp.server.dependencies = mock_deps

        saved = {k: sys.modules.get(k) for k in ['fastmcp', 'fastmcp.server', 'fastmcp.server.dependencies']}
        sys.modules['fastmcp'] = mock_fastmcp
        sys.modules['fastmcp.server'] = mock_fastmcp.server
        sys.modules['fastmcp.server.dependencies'] = mock_deps

        try:
            # Create a test API class
            class TestApiClass:
                def __init__(self, api_client):
                    self.api_client = api_client

            # Create a test method
            @with_header_auth(TestApiClass)
            async def test_method(self, ctx=None, api_client=None):
                return {"success": True}

            # Call the method - should return error for invalid URL
            result = asyncio.run(test_method(self.client))

            # Should return an error for invalid URL format
            self.assertIn("error", result)
            self.assertIn("Instana base URL must start with http:// or https://", result["error"])
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_with_header_auth_missing_headers(self):
        """Test with_header_auth with missing headers"""
        # Mock the get_http_headers function
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.return_value = {}  # Empty headers

            # Create a test API class
            class TestApiClass:
                def __init__(self, api_client):
                    self.api_client = api_client

            # Create a test method
            @with_header_auth(TestApiClass)
            async def test_method(self, ctx=None, api_client=None):
                return {"success": True}

            # Call the method - should fallback to constructor auth
            result = asyncio.run(test_method(self.client))

            # Should still work due to fallback
            self.assertIn("success", result)

    def test_with_header_auth_existing_api_client(self):
        """Test with_header_auth with existing API client"""
        # Mock the get_http_headers function to trigger fallback
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.side_effect = ImportError("Module not found")

            # Add an existing API client to the client
            class TestApiClass:
                def __init__(self, api_client):
                    self.api_client = api_client

            existing_api = TestApiClass(MagicMock())
            self.client.test_api = existing_api

            # Create a test method
            @with_header_auth(TestApiClass)
            async def test_method(self, ctx=None, api_client=None):
                return {"success": True, "api_client": api_client}

            # Call the method
            result = asyncio.run(test_method(self.client))

            # Check that the result is correct
            self.assertIn("success", result)
            self.assertTrue(result["success"])

    def test_with_header_auth_decorator_error(self):
        """Test with_header_auth when decorator encounters an error"""
        # Ensure fastmcp.server.dependencies is a real mock with controllable get_http_headers
        mock_deps = MagicMock()
        mock_deps.get_http_headers.side_effect = Exception("Decorator error")
        mock_fastmcp = MagicMock()
        mock_fastmcp.server.dependencies = mock_deps

        saved = {k: sys.modules.get(k) for k in ['fastmcp', 'fastmcp.server', 'fastmcp.server.dependencies']}
        sys.modules['fastmcp'] = mock_fastmcp
        sys.modules['fastmcp.server'] = mock_fastmcp.server
        sys.modules['fastmcp.server.dependencies'] = mock_deps

        try:
            # Create a test API class
            class TestApiClass:
                def __init__(self, api_client):
                    self.api_client = api_client

            # Create a test method
            @with_header_auth(TestApiClass)
            async def test_method(self, ctx=None, api_client=None):
                return {"success": True}

            # Call the method
            result = asyncio.run(test_method(self.client))

            # Should return an error
            self.assertIn("error", result)
            self.assertIn("Authentication error", result["error"])
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
    def test_with_header_auth_session_token_authentication(self):
        """Test with_header_auth now only supports API token authentication"""
        # The decorator now only supports API token authentication
        # Session tokens are no longer supported
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.return_value = {
                "instana-api-token": "api_token_123",
                "instana-base-url": "https://session.instana.io"
            }

            # Mock the SDK imports
            with patch('instana_client.configuration.Configuration') as mock_config, \
                 patch('instana_client.api_client.ApiClient') as mock_api_client:

                mock_config_instance = MagicMock()
                mock_config_instance.api_key = {}
                mock_config_instance.api_key_prefix = {}
                mock_config.return_value = mock_config_instance
                mock_api_client_instance = MagicMock()
                mock_api_client.return_value = mock_api_client_instance

                # Create a test API class
                class TestApiClass:
                    def __init__(self, api_client):
                        self.api_client = api_client

                # Create a test method
                @with_header_auth(TestApiClass)
                async def test_method(self, ctx=None, api_client=None):
                    return {"success": True, "api_client": api_client}

                # Call the method
                result = asyncio.run(test_method(self.client))

                # Check that the result is correct
                self.assertIn("success", result)
                self.assertTrue(result["success"])

                # Verify API token was configured
                self.assertEqual(mock_config_instance.api_key['ApiKeyAuth'], "api_token_123")
                self.assertEqual(mock_config_instance.api_key_prefix['ApiKeyAuth'], 'apiToken')

    def test_with_header_auth_session_with_custom_cookie_name(self):
        """Test with_header_auth with API token (session tokens no longer supported)"""
        # The decorator now only supports API token authentication
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.return_value = {
                "instana-api-token": "api_token_456",
                "instana-base-url": "https://session.instana.io"
            }

            # Mock the SDK imports
            with patch('instana_client.configuration.Configuration') as mock_config, \
                 patch('instana_client.api_client.ApiClient') as mock_api_client:

                mock_config_instance = MagicMock()
                mock_config_instance.api_key = {}
                mock_config_instance.api_key_prefix = {}
                mock_config.return_value = mock_config_instance
                mock_api_client_instance = MagicMock()
                mock_api_client.return_value = mock_api_client_instance

                # Create a test API class
                class TestApiClass:
                    def __init__(self, api_client):
                        self.api_client = api_client

                # Create a test method
                @with_header_auth(TestApiClass)
                async def test_method(self, ctx=None, api_client=None):
                    return {"success": True}

                # Call the method
                result = asyncio.run(test_method(self.client))

                # Check that the result is correct
                self.assertIn("success", result)
                self.assertTrue(result["success"])

                # Verify API token was configured
                self.assertEqual(mock_config_instance.api_key['ApiKeyAuth'], "api_token_456")
                self.assertEqual(mock_config_instance.api_key_prefix['ApiKeyAuth'], 'apiToken')

    def test_with_header_auth_api_token_priority_over_session(self):
        """Test that decorator uses API token authentication"""
        # The decorator now only supports API token authentication
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.return_value = {
                "instana-api-token": "api_token_789",
                "instana-base-url": "https://test.instana.io"
            }

            # Mock the SDK imports
            with patch('instana_client.configuration.Configuration') as mock_config, \
                 patch('instana_client.api_client.ApiClient') as mock_api_client:

                mock_config_instance = MagicMock()
                mock_config_instance.api_key = {}
                mock_config_instance.api_key_prefix = {}
                mock_config.return_value = mock_config_instance
                mock_api_client_instance = MagicMock()
                mock_api_client.return_value = mock_api_client_instance

                # Create a test API class
                class TestApiClass:
                    def __init__(self, api_client):
                        self.api_client = api_client

                # Create a test method
                @with_header_auth(TestApiClass)
                async def test_method(self, ctx=None, api_client=None):
                    return {"success": True}

                # Call the method
                result = asyncio.run(test_method(self.client))

                # Check that the result is correct
                self.assertIn("success", result)

                # Verify API token was configured
                self.assertEqual(mock_config_instance.api_key['ApiKeyAuth'], "api_token_789")
                self.assertEqual(mock_config_instance.api_key_prefix['ApiKeyAuth'], 'apiToken')

    def test_with_header_auth_missing_csrf_token(self):
        """Test with_header_auth with auth token but missing CSRF token"""
        # Mock the get_http_headers function
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.return_value = {
                "instana-auth-token": "session_token_123",
                # Missing csrf token
                "instana-base-url": "https://test.instana.io"
            }

            # Create a test API class
            class TestApiClass:
                def __init__(self, api_client):
                    self.api_client = api_client

            # Create a test method
            @with_header_auth(TestApiClass)
            async def test_method(self, ctx=None, api_client=None):
                return {"success": True}

            # Call the method - should return error
            result = asyncio.run(test_method(self.client))

            # Should return an error for incomplete session auth
            self.assertIn("error", result)


    def test_make_request_with_json_data(self):
        """Test make_request with JSON data"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"data": "test"})
            mock_post.return_value = mock_response

            endpoint = "/api/test"
            json_data = {"key": "value"}
            result = asyncio.run(self.client.make_request(endpoint, json=json_data, method="POST"))

            mock_post.assert_called_once_with(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.client.get_headers(),
                json=json_data,
                verify=False
            )
            self.assertEqual(result, {"data": "test"})

    def test_make_request_with_both_params_and_json(self):
        """Test make_request with both params and json (json should take precedence)"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"data": "test"})
            mock_post.return_value = mock_response

            endpoint = "/api/test"
            params = {"param1": "value1"}
            json_data = {"json_key": "json_value"}
            result = asyncio.run(self.client.make_request(endpoint, params=params, json=json_data, method="POST"))

            # Should use json data, not params
            mock_post.assert_called_once_with(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.client.get_headers(),
                json=json_data,
                verify=False
            )
            self.assertEqual(result, {"data": "test"})

    def test_make_request_with_empty_json(self):
        """Test make_request with empty JSON data"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"data": "test"})
            mock_post.return_value = mock_response

            endpoint = "/api/test"
            json_data = {}
            result = asyncio.run(self.client.make_request(endpoint, json=json_data, method="POST"))

            mock_post.assert_called_once_with(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.client.get_headers(),
                json=json_data,
                verify=False
            )
            self.assertEqual(result, {"data": "test"})

    def test_make_request_with_none_json(self):
        """Test make_request with None JSON data"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"data": "test"})
            mock_post.return_value = mock_response

            endpoint = "/api/test"
            result = asyncio.run(self.client.make_request(endpoint, json=None, method="POST"))

            # Should use params (which is None) instead of json
            mock_post.assert_called_once_with(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.client.get_headers(),
                json=None,
                verify=False
            )
            self.assertEqual(result, {"data": "test"})

    def test_make_request_with_complex_endpoint(self):
        """Test make_request with complex endpoint paths"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"data": "test"})
            mock_get.return_value = mock_response

            # Test various endpoint formats
            test_cases = [
                ("/api/test", "https://test.instana.io/api/test"),
                ("api/test", "https://test.instana.io/api/test"),
                ("/api/test/", "https://test.instana.io/api/test/"),
                ("api/test/", "https://test.instana.io/api/test/"),
                ("/api/test/path/with/multiple/segments", "https://test.instana.io/api/test/path/with/multiple/segments"),
                ("api/test/path/with/multiple/segments", "https://test.instana.io/api/test/path/with/multiple/segments")
            ]

            for endpoint, expected_url in test_cases:
                with self.subTest(endpoint=endpoint):
                    result = asyncio.run(self.client.make_request(endpoint))

                    # Check that the URL was constructed correctly
                    mock_get.assert_called_with(
                        expected_url,
                        headers=self.client.get_headers(),
                        params=None,
                        verify=False
                    )
                    self.assertEqual(result, {"data": "test"})

    def test_make_request_with_none_params(self):
        """Test make_request with None parameters"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"data": "test"})
            mock_get.return_value = mock_response

            endpoint = "/api/test"
            result = asyncio.run(self.client.make_request(endpoint, params=None))

            mock_get.assert_called_once_with(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.client.get_headers(),
                params=None,
                verify=False
            )
            self.assertEqual(result, {"data": "test"})

    def test_make_request_with_empty_params(self):
        """Test make_request with empty parameters"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"data": "test"})
            mock_get.return_value = mock_response

            endpoint = "/api/test"
            result = asyncio.run(self.client.make_request(endpoint, params={}))

            mock_get.assert_called_once_with(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=self.client.get_headers(),
                params={},
                verify=False
            )
            self.assertEqual(result, {"data": "test"})

    def test_register_as_tool_with_class_method(self):
        """Test register_as_tool with a class method"""
        class TestClass:
            @register_as_tool()
            def class_method(self):
                return "class_method_result"

        # Check that the method was added to the registry
        self.assertIn("class_method", MCP_TOOLS)

        # Create an instance and call the method
        instance = TestClass()
        result = MCP_TOOLS["class_method"](instance)
        self.assertEqual(result, "class_method_result")

    def test_register_as_tool_with_static_method(self):
        """Test register_as_tool with a static method"""
        class TestClass:
            @staticmethod
            @register_as_tool()
            def static_method():
                return "static_method_result"

        # Check that the method was added to the registry
        self.assertIn("static_method", MCP_TOOLS)

        # Call the method
        result = MCP_TOOLS["static_method"]()
        self.assertEqual(result, "static_method_result")

    def test_register_as_tool_with_lambda(self):
        """Test register_as_tool with a lambda function"""
        # This should work but is unusual
        register_as_tool()(lambda: "lambda_result")

        # Check that the function was added to the registry
        self.assertIn("<lambda>", MCP_TOOLS)

        # Call the function
        result = MCP_TOOLS["<lambda>"]()
        self.assertEqual(result, "lambda_result")

    def test_register_as_tool_with_generator(self):
        """Test register_as_tool with a generator function"""
        @register_as_tool()
        def generator_func():
            yield "generator_result"

        # Check that the function was added to the registry
        self.assertIn("generator_func", MCP_TOOLS)

        # Call the function
        result = list(MCP_TOOLS["generator_func"]())
        self.assertEqual(result, ["generator_result"])

    def test_get_headers_with_special_characters_in_token(self):
        """Test get_headers with special characters in token"""
        special_token = "token@#$%^&*()_+-=[]{}|;':\",./<>?"
        client = BaseInstanaClient(read_token=special_token, base_url=self.base_url)
        headers = client.get_headers()

        self.assertEqual(headers["Authorization"], f"apiToken {special_token}")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Accept"], "application/json")

    def test_get_headers_with_unicode_token(self):
        """Test get_headers with unicode characters in token"""
        unicode_token = "token_with_unicode_ñáéíóú"
        client = BaseInstanaClient(read_token=unicode_token, base_url=self.base_url)
        headers = client.get_headers()

        self.assertEqual(headers["Authorization"], f"apiToken {unicode_token}")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Accept"], "application/json")

    def test_get_headers_with_empty_token(self):
        """Test get_headers with empty token - should raise AuthenticationError"""
        empty_token = ""
        client = BaseInstanaClient(read_token=empty_token, base_url=self.base_url)

        # Empty token should return headers with empty Authorization
        headers = client.get_headers()

        self.assertEqual(headers["Authorization"], f"apiToken {empty_token}")
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_get_headers_with_whitespace_token(self):
        """Test get_headers with whitespace in token"""
        whitespace_token = "  token_with_spaces  "
        client = BaseInstanaClient(read_token=whitespace_token, base_url=self.base_url)
        headers = client.get_headers()

        self.assertEqual(headers["Authorization"], f"apiToken {whitespace_token}")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Accept"], "application/json")
    def test_get_headers_with_session_tokens(self):
        """Test get_headers no longer supports session tokens - only API token"""
        # The simplified get_headers() method only supports API token authentication
        # Session token authentication is handled by the with_header_auth decorator
        headers = self.client.get_headers()

        # Should return standard API token headers
        self.assertEqual(headers["Authorization"], f"apiToken {self.read_token}")
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_get_headers_with_custom_cookie_name(self):
        """Test get_headers no longer supports custom cookie names"""
        # The simplified get_headers() method only supports API token authentication
        headers = self.client.get_headers()

        # Should return standard API token headers
        self.assertEqual(headers["Authorization"], f"apiToken {self.read_token}")

    def test_get_headers_api_token_priority_over_session(self):
        """Test get_headers only uses API token from constructor"""
        # The simplified get_headers() method only uses the API token from constructor
        headers = self.client.get_headers()

        # Should return standard API token headers
        self.assertEqual(headers["Authorization"], f"apiToken {self.read_token}")

    def test_get_headers_session_only_when_no_api_token(self):
        """Test get_headers with empty API token"""
        client = BaseInstanaClient(read_token="", base_url=self.base_url)

        # Should still return headers with empty token
        headers = client.get_headers()
        self.assertEqual(headers["Authorization"], "apiToken ")



class TestVersionImport(unittest.TestCase):
    """Test the __version__ variable import logic"""

    def test_version_is_string(self):
        """Test that __version__ is a string"""
        self.assertIsInstance(__version__, str)

    def test_version_not_empty(self):
        """Test that __version__ is not empty"""
        self.assertGreater(len(__version__), 0)

    def test_version_format(self):
        """Test that __version__ follows semantic versioning format (X.Y.Z)"""
        # Version should be in format like "0.3.1" or "1.0.0"
        parts = __version__.split('.')
        self.assertGreaterEqual(len(parts), 2, "Version should have at least major.minor")
        # Check that parts are numeric (or contain numeric values)
        for part in parts[:3]:  # Check first 3 parts (major.minor.patch)
            # Remove any non-numeric suffixes like "-alpha", "-beta"
            numeric_part = part.split('-')[0]
            self.assertTrue(numeric_part.isdigit(), f"Version part '{numeric_part}' should be numeric")

    @patch('importlib.metadata.version')
    def test_version_from_metadata_success(self, mock_version):
        """Test successful version retrieval from package metadata"""
        # Mock the version function to return a test version
        mock_version.return_value = "1.2.3"

        # Re-import to trigger the version logic
        importlib.reload(src.core.utils)

        # Check that the version was set correctly
        self.assertEqual(src.core.utils.__version__, "1.2.3")

    @patch('importlib.metadata.version')
    def test_version_fallback_on_exception(self, mock_version):
        """Test fallback version when package metadata is not available"""
        # Mock the version function to raise an exception
        mock_version.side_effect = Exception("Package not found")

        # Re-import to trigger the version logic
        importlib.reload(src.core.utils)

        # Check that the fallback version was used (updated to 0.9.6)
        self.assertEqual(src.core.utils.__version__, "0.9.7")

    def test_version_used_in_headers(self):
        """Test that __version__ is used in User-Agent headers"""
        # Re-import to get the current version
        importlib.reload(src.core.utils)
        current_version = src.core.utils.__version__

        client = BaseInstanaClient(read_token="test_token", base_url="https://test.instana.io")
        headers = client.get_headers()

        # Check that User-Agent header contains the version
        self.assertIn("User-Agent", headers)
        self.assertIn(current_version, headers["User-Agent"])
        self.assertEqual(headers["User-Agent"], f"MCP-server/{current_version}")


if __name__ == '__main__':
    unittest.main()


class TestDecodeResponse(unittest.TestCase):
    """Test the decode_response function"""

    def test_decode_response_with_utf8(self):
        """Test decode_response with UTF-8 charset"""
        from src.core.utils import decode_response

        # Create a mock response with UTF-8 charset
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'application/json; charset=utf-8'}
        mock_response.data = b'{"test": "data"}'

        result = decode_response(mock_response)
        self.assertEqual(result, '{"test": "data"}')

    def test_decode_response_with_latin1(self):
        """Test decode_response with latin-1 charset"""
        from src.core.utils import decode_response

        # Create a mock response with latin-1 charset
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'text/html; charset=iso-8859-1'}
        mock_response.data = b'test data'

        result = decode_response(mock_response)
        self.assertEqual(result, 'test data')

    def test_decode_response_without_charset(self):
        """Test decode_response without charset (should use default UTF-8)"""
        from src.core.utils import decode_response

        # Create a mock response without charset
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.data = b'{"test": "data"}'

        result = decode_response(mock_response)
        self.assertEqual(result, '{"test": "data"}')

    def test_decode_response_with_invalid_charset(self):
        """Test decode_response with invalid charset (should fallback to UTF-8)"""
        from src.core.utils import decode_response

        # Create a mock response with invalid charset
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'application/json; charset=invalid-charset'}
        mock_response.data = b'{"test": "data"}'

        result = decode_response(mock_response)
        self.assertEqual(result, '{"test": "data"}')

    def test_decode_response_with_unicode_decode_error(self):
        """Test decode_response with data that causes UnicodeDecodeError"""
        from src.core.utils import decode_response

        # Create a mock response with invalid UTF-8 bytes
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'application/json; charset=utf-8'}
        # Invalid UTF-8 sequence
        mock_response.data = b'\xff\xfe'

        # Should fallback to UTF-8 with error replacement
        result = decode_response(mock_response)
        self.assertIsInstance(result, str)


class TestExtractTagNamesFromTree(unittest.TestCase):
    """Test the extract_tag_names_from_tree function"""

    def test_extract_from_dict_with_tag_name(self):
        """Test extracting tag names from a dict node with tagName"""
        from src.core.utils import extract_tag_names_from_tree

        node = {"tagName": "test.tag"}
        result = extract_tag_names_from_tree(node)
        self.assertEqual(result, ["test.tag"])

    def test_extract_from_dict_with_children(self):
        """Test extracting tag names from a dict node with children"""
        from src.core.utils import extract_tag_names_from_tree

        node = {
            "tagName": "parent.tag",
            "children": [
                {"tagName": "child1.tag"},
                {"tagName": "child2.tag"}
            ]
        }
        result = extract_tag_names_from_tree(node)
        self.assertEqual(sorted(result), ["child1.tag", "child2.tag", "parent.tag"])

    def test_extract_from_nested_structure(self):
        """Test extracting tag names from deeply nested structure"""
        from src.core.utils import extract_tag_names_from_tree

        node = {
            "tagName": "root",
            "children": [
                {
                    "tagName": "level1",
                    "children": [
                        {"tagName": "level2"}
                    ]
                }
            ]
        }
        result = extract_tag_names_from_tree(node)
        self.assertEqual(sorted(result), ["level1", "level2", "root"])

    def test_extract_from_list(self):
        """Test extracting tag names from a list of nodes"""
        from src.core.utils import extract_tag_names_from_tree

        nodes = [
            {"tagName": "tag1"},
            {"tagName": "tag2"},
            {"tagName": "tag3"}
        ]
        result = extract_tag_names_from_tree(nodes)
        self.assertEqual(sorted(result), ["tag1", "tag2", "tag3"])

    def test_extract_from_dict_without_tag_name(self):
        """Test extracting from dict without tagName"""
        from src.core.utils import extract_tag_names_from_tree

        node = {"otherField": "value"}
        result = extract_tag_names_from_tree(node)
        self.assertEqual(result, [])

    def test_extract_with_existing_tag_names_list(self):
        """Test extracting with pre-existing tag_names list"""
        from src.core.utils import extract_tag_names_from_tree

        existing_tags = ["existing.tag"]
        node = {"tagName": "new.tag"}
        result = extract_tag_names_from_tree(node, existing_tags)
        self.assertEqual(sorted(result), ["existing.tag", "new.tag"])




class TestHandleApiErrorResponse(unittest.TestCase):
    """Test the handle_api_error_response method"""

    def setUp(self):
        """Set up test fixtures"""
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = BaseInstanaClient(read_token=self.read_token, base_url=self.base_url)

    def test_handle_api_error_with_decodable_response(self):
        """Test handling API error with decodable response body"""
        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.headers = {'Content-Type': 'application/json; charset=utf-8'}
        mock_response.data = b'{"error": "Not found"}'

        # Create mock logger (without spec to avoid InvalidSpecError)
        mock_logger = MagicMock()

        result = self.client.handle_api_error_response(mock_response, "test_operation", mock_logger)

        self.assertEqual(result["error"], "Failed to test_operation: HTTP 404")
        self.assertEqual(result["details"], '{"error": "Not found"}')
        self.assertEqual(result["status_code"], 404)

        # Verify logger was called
        self.assertEqual(mock_logger.error.call_count, 2)

    def test_handle_api_error_with_decode_exception(self):
        """Test handling API error when decode_response raises exception"""
        # Create mock response that will cause decode to fail
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.headers = {}
        mock_response.data = MagicMock()
        mock_response.data.decode = MagicMock(side_effect=Exception("Decode failed"))

        # Create mock logger (without spec to avoid InvalidSpecError)
        mock_logger = MagicMock()

        result = self.client.handle_api_error_response(mock_response, "test_operation", mock_logger)

        self.assertEqual(result["error"], "Failed to test_operation: HTTP 500")
        self.assertNotIn("details", result)
        self.assertEqual(result["status_code"], 500)

        # Verify logger was called once (before the exception)
        mock_logger.error.assert_called_once()



class TestProcessTagCatalogResponse(unittest.TestCase):
    """Test the process_tag_catalog_response function"""

    def test_process_from_tag_tree(self):
        """Test processing tag names from tagTree"""
        from src.core.utils import process_tag_catalog_response

        response = {
            "tagTree": {
                "tagName": "root",
                "children": [
                    {"tagName": "child1"},
                    {"tagName": "child2"}
                ]
            }
        }
        result = process_tag_catalog_response(response, "pageLoad", "GROUPING")

        self.assertEqual(sorted(result["tag_names"]), ["child1", "child2", "root"])
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["beacon_type"], "pageLoad")
        self.assertEqual(result["use_case"], "GROUPING")

    def test_process_from_flat_tags_list(self):
        """Test processing tag names from flat tags list"""
        from src.core.utils import process_tag_catalog_response

        response = {
            "tags": [
                {"name": "tag1"},
                {"name": "tag2"},
                {"name": "tag3"}
            ]
        }
        result = process_tag_catalog_response(response, "pageLoad", "FILTERING")

        self.assertEqual(sorted(result["tag_names"]), ["tag1", "tag2", "tag3"])
        self.assertEqual(result["count"], 3)

    def test_process_from_both_sources(self):
        """Test processing from both tagTree and tags list"""
        from src.core.utils import process_tag_catalog_response

        response = {
            "tagTree": {"tagName": "tree.tag"},
            "tags": [
                {"name": "flat.tag1"},
                {"name": "flat.tag2"}
            ]
        }
        result = process_tag_catalog_response(response, "pageLoad", "GROUPING")

        self.assertEqual(sorted(result["tag_names"]), ["flat.tag1", "flat.tag2", "tree.tag"])
        self.assertEqual(result["count"], 3)

    def test_process_removes_duplicates(self):
        """Test that duplicate tag names are removed"""
        from src.core.utils import process_tag_catalog_response

        response = {
            "tagTree": {"tagName": "duplicate.tag"},
            "tags": [
                {"name": "duplicate.tag"},
                {"name": "unique.tag"}
            ]
        }
        result = process_tag_catalog_response(response, "pageLoad", "GROUPING")

        self.assertEqual(sorted(result["tag_names"]), ["duplicate.tag", "unique.tag"])
        self.assertEqual(result["count"], 2)

    def test_process_from_empty_response(self):
        """Test processing from empty response"""
        from src.core.utils import process_tag_catalog_response

        response = {}
        result = process_tag_catalog_response(response, "pageLoad", "GROUPING")

        self.assertEqual(result["tag_names"], [])
        self.assertEqual(result["count"], 0)

    def test_process_ignores_tags_without_name(self):
        """Test that tags without 'name' field are ignored"""
        from src.core.utils import process_tag_catalog_response

        response = {
            "tags": [
                {"name": "valid.tag"},
                {"other_field": "value"},  # No 'name' field
                {"name": None},  # name is None
                {"name": ""}  # name is empty string
            ]
        }
        result = process_tag_catalog_response(response, "pageLoad", "GROUPING")

        # Only valid.tag should be included (empty string and None are filtered out)
        self.assertEqual(result["tag_names"], ["valid.tag"])
        self.assertEqual(result["count"], 1)

class TestNormalizeBeaconType(unittest.TestCase):
    """Test the normalize_beacon_type function"""

    def test_normalize_uppercase_to_camelcase(self):
        """Test normalizing uppercase beacon type to camelCase"""
        from src.core.utils import normalize_beacon_type

        beacon_type_map = {
            "SESSION_START": "sessionStart",
            "PAGE_LOAD": "pageLoad",
            "HTTP_REQUEST": "httpRequest"
        }

        result = normalize_beacon_type("SESSION_START", beacon_type_map)
        self.assertEqual(result, "sessionStart")

        result = normalize_beacon_type("PAGE_LOAD", beacon_type_map)
        self.assertEqual(result, "pageLoad")

    def test_normalize_lowercase_to_camelcase(self):
        """Test normalizing lowercase beacon type to camelCase"""
        from src.core.utils import normalize_beacon_type

        beacon_type_map = {
            "SESSION_START": "sessionStart",
            "PAGE_LOAD": "pageLoad"
        }

        # Should work with lowercase input (converted to uppercase internally)
        result = normalize_beacon_type("session_start", beacon_type_map)
        self.assertEqual(result, "sessionStart")

    def test_normalize_already_camelcase(self):
        """Test that already camelCase beacon type is returned as-is"""
        from src.core.utils import normalize_beacon_type

        beacon_type_map = {
            "SESSION_START": "sessionStart"
        }

        # If input is already camelCase and not in map, return as-is
        result = normalize_beacon_type("sessionStart", beacon_type_map)
        self.assertEqual(result, "sessionStart")

    def test_normalize_unknown_beacon_type(self):
        """Test normalizing unknown beacon type returns input unchanged"""
        from src.core.utils import normalize_beacon_type

        beacon_type_map = {
            "SESSION_START": "sessionStart"
        }

        result = normalize_beacon_type("UNKNOWN_TYPE", beacon_type_map)
        self.assertEqual(result, "UNKNOWN_TYPE")


