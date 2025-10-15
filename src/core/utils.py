"""
Base Instana API Client Module

This module provides the base client for interacting with the Instana API.
"""

import sys
from functools import wraps
from typing import Any, Callable, Dict, Union

import requests

# Import MCP dependencies
from mcp.types import ToolAnnotations

# Registry to store all tools
MCP_TOOLS = {}

def register_as_tool(title=None, annotations=None):
    """
    Enhanced decorator that registers both in MCP_TOOLS and with @mcp.tool

    Args:
        title: Title for the MCP tool (optional, defaults to function name)
        annotations: ToolAnnotations for the MCP tool (optional)
    """
    def decorator(func):
        # Get function metadata
        func_name = func.__name__

        # Use provided title or generate from function name
        tool_title = title or func_name.replace('_', ' ').title()

        # Use provided annotations or default
        tool_annotations = annotations or ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False
        )

        # Store the metadata for later use by the server
        func._mcp_title = tool_title
        func._mcp_annotations = tool_annotations

        # Register in MCP_TOOLS (existing functionality)
        MCP_TOOLS[func_name] = func

        return func

    return decorator

def with_header_auth(api_class, allow_mock=True):
    """
    Universal decorator for Instana MCP tools that provides flexible authentication.

    This decorator automatically handles authentication for any Instana API tool method.
    It supports both HTTP mode (using headers) and STDIO mode (using environment variables),
    with strict mode separation to prevent cross-mode fallbacks.

    Features:
    - HTTP Mode: Extracts credentials from HTTP headers (fails if missing)
    - STDIO Mode: Uses constructor-based authentication (fails if missing)
    - Mock Mode: Allows injection of mock clients for testing (when allow_mock=True)

    Args:
        api_class: The Instana API class to instantiate (e.g., InfrastructureTopologyApi,
                  ApplicationMetricsApi, InfrastructureCatalogApi, etc.)
        allow_mock: If True, allows mock clients to be passed directly (for testing). Defaults to True.

    Usage:
        @with_header_auth(YourApiClass)
        async def your_tool_method(self, param1, param2, ctx=None, api_client=None):
            # The decorator automatically injects 'api_client' into the method
            result = api_client.your_api_method(param1, param2)
            return self._convert_to_dict(result)

    Note: Always include 'api_client=None' in your method signature to receive the
    injected API client from the decorator.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                # Check if a mock client is being passed (for testing)
                if allow_mock and 'api_client' in kwargs and kwargs['api_client'] is not None:
                    print(" Using mock client for testing", file=sys.stderr)
                    # Call the original function with the mock client
                    return await func(self, *args, **kwargs)

                # Try to get headers first to determine mode
                try:
                    from fastmcp.server.dependencies import get_http_headers
                    headers = get_http_headers()

                    instana_token = headers.get("instana-api-token")
                    instana_base_url = headers.get("instana-base-url")

                    # Check if we're in HTTP mode (headers are present)
                    if instana_token or instana_base_url:
                        # HTTP mode detected - both headers must be present
                        if not instana_token or not instana_base_url:
                            missing = []
                            if not instana_token:
                                missing.append("instana-api-token")
                            if not instana_base_url:
                                missing.append("instana-base-url")
                            error_msg = f"HTTP mode detected but missing required headers: {', '.join(missing)}"
                            print(f" {error_msg}", file=sys.stderr)
                            return {"error": error_msg}

                        # Validate URL format
                        if not instana_base_url.startswith("http://") and not instana_base_url.startswith("https://"):
                            error_msg = "Instana base URL must start with http:// or https://"
                            print(f" {error_msg}", file=sys.stderr)
                            return {"error": error_msg}

                        print(" Using header-based authentication (HTTP mode)", file=sys.stderr)
                        print(" instana_base_url: ", instana_base_url)

                        # Import SDK components
                        from instana_client.api_client import ApiClient
                        from instana_client.configuration import Configuration

                        # Create API client from headers
                        configuration = Configuration()
                        configuration.host = instana_base_url
                        configuration.api_key['ApiKeyAuth'] = instana_token
                        configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'
                        configuration.default_headers = {"User-Agent": "MCP-server/0.1.0"}

                        api_client_instance = ApiClient(configuration=configuration)
                        api_instance = api_class(api_client=api_client_instance)

                        # Add the API instance to kwargs so the decorated function can use it
                        kwargs['api_client'] = api_instance

                        # Call the original function
                        return await func(self, *args, **kwargs)

                except (ImportError, AttributeError) as e:
                    print(f"Header detection failed, using STDIO mode: {e}", file=sys.stderr)

                # STDIO mode - use constructor-based authentication
                print(" Using constructor-based authentication (STDIO mode)", file=sys.stderr)
                print(f" self.base_url: {self.base_url}", file=sys.stderr)

                # Validate constructor credentials before proceeding
                if not self.read_token or not self.base_url:
                    error_msg = "Authentication failed: Missing credentials "
                    if not self.read_token:
                        error_msg += " - INSTANA_API_TOKEN is missing"
                    if not self.base_url:
                        error_msg += " - INSTANA_BASE_URL is missing"
                    print(f" {error_msg}", file=sys.stderr)
                    return {"error": error_msg}

                # Check if the class has the expected API attribute
                api_attr_name = None
                for attr_name in dir(self):
                    if attr_name.endswith('_api'):
                        attr = getattr(self, attr_name)
                        if hasattr(attr, '__class__') and attr.__class__.__name__ == api_class.__name__:
                            api_attr_name = attr_name
                            print(f"🔐 Found existing API client: {attr_name}", file=sys.stderr)
                            break

                if api_attr_name:
                    # Use the existing API client from constructor
                    api_instance = getattr(self, api_attr_name)
                    kwargs['api_client'] = api_instance
                    return await func(self, *args, **kwargs)
                else:
                    # Create a new API client using constructor credentials
                    print(" Creating new API client with constructor credentials", file=sys.stderr)
                    from instana_client.api_client import ApiClient
                    from instana_client.configuration import Configuration

                    configuration = Configuration()
                    configuration.host = self.base_url
                    configuration.api_key['ApiKeyAuth'] = self.read_token
                    configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'
                    configuration.default_headers = {"User-Agent": "MCP-server/0.1.0"}

                    api_client_instance = ApiClient(configuration=configuration)
                    api_instance = api_class(api_client=api_client_instance)

                    kwargs['api_client'] = api_instance
                    return await func(self, *args, **kwargs)

            except Exception as e:
                print(f"Error in header auth decorator: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                # Handle the specific case where e might be a string
                if isinstance(e, str):
                    error_msg = f"Authentication error: {e}"
                else:
                    error_msg = f"Authentication error: {e!s}"
                return {"error": error_msg}

        return wrapper
    return decorator

class BaseInstanaClient:
    """Base client for Instana API with common functionality."""

    def __init__(self, read_token: str, base_url: str):
        self.read_token = read_token
        self.base_url = base_url

    def get_headers(self):
        """Get standard headers for Instana API requests."""
        return {
            "Authorization": f"apiToken {self.read_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def make_request(self, endpoint: str, params: Union[Dict[str, Any], None] = None, method: str = "GET", json: Union[Dict[str, Any], None] = None) -> Dict[str, Any]:
        """Make a request to the Instana API."""
        if endpoint is None:
            return {"error": "Endpoint cannot be None"}
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self.get_headers()

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, verify=False)
            elif method.upper() == "POST":
                # Use the json parameter if provided, otherwise use params
                data_to_send = json if json is not None else params
                response = requests.post(url, headers=headers, json=data_to_send, verify=False)
            elif method.upper() == "PUT":
                data_to_send = json if json is not None else params
                response = requests.put(url, headers=headers, json=data_to_send, verify=False)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params, verify=False)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}", file=sys.stderr)
            return {"error": f"HTTP Error: {err}"}
        except requests.exceptions.RequestException as err:
            print(f"Error: {err}", file=sys.stderr)
            return {"error": f"Error: {err}"}
        except Exception as e:
            print(f"Unexpected error: {e!s}", file=sys.stderr)
            return {"error": f"Unexpected error: {e!s}"}
