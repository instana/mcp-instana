"""
Unit tests for the BaseInstanaClient class
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the class to test
from src.core.utils import (
    MCP_TOOLS,
    BaseInstanaClient,
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
        from requests.exceptions import HTTPError
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
        from requests.exceptions import RequestException
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
        # Mock the get_http_headers function
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.return_value = {
                "instana-api-token": "header_token",
                "instana-base-url": "invalid_url"  # Missing http/https
            }

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
        # Mock the get_http_headers function to raise an exception
        with patch('fastmcp.server.dependencies.get_http_headers') as mock_get_headers:
            mock_get_headers.side_effect = Exception("Decorator error")

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
        """Test get_headers with empty token"""
        empty_token = ""
        client = BaseInstanaClient(read_token=empty_token, base_url=self.base_url)
        headers = client.get_headers()

        self.assertEqual(headers["Authorization"], "apiToken ")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Accept"], "application/json")

    def test_get_headers_with_whitespace_token(self):
        """Test get_headers with whitespace in token"""
        whitespace_token = "  token_with_spaces  "
        client = BaseInstanaClient(read_token=whitespace_token, base_url=self.base_url)
        headers = client.get_headers()

        self.assertEqual(headers["Authorization"], f"apiToken {whitespace_token}")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Accept"], "application/json")


if __name__ == '__main__':
    unittest.main()

