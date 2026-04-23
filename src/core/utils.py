"""
Base Instana API Client Module

This module provides the base client for interacting with the Instana API.
"""

import logging
import sys
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

import requests

from src.core.api_headers import build_instana_api_headers

# Set up logger
logger = logging.getLogger(__name__)

# Import MCP dependencies
from fastmcp import Context
from mcp.types import ToolAnnotations

# Default charset for response decoding
DEFAULT_CHARSET = 'utf-8'

# Constants for error messages
AUTH_FAILED_MSG = "Authentication failed: %s"

# Import for getting package version from meta data rather than server.py
try:
    from importlib.metadata import version
    __version__ = version("mcp-instana")
except Exception:
    # Fallback version if package metadata is not available
    __version__ = "0.9.7"

# Registry to store all tools
MCP_TOOLS = {}

def register_as_tool(title=None, annotations=None, description=None):
    """
    Enhanced decorator that registers both in MCP_TOOLS and with @mcp.tool

    Args:
        title: Title for the MCP tool (optional, defaults to function name)
        annotations: ToolAnnotations for the MCP tool (optional)
        description: Explicit description for the tool (optional, uses docstring if not provided)
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

        # Use provided description or extract from docstring
        tool_description = description
        if not tool_description and func.__doc__:
            # Extract first paragraph from docstring as description
            tool_description = func.__doc__.strip().split('\n\n')[0].strip()

        # Store the metadata for later use by the server
        func._mcp_title = tool_title
        func._mcp_annotations = tool_annotations
        func._mcp_description = tool_description

        # Register in MCP_TOOLS (existing functionality)
        MCP_TOOLS[func_name] = func

        return func

    return decorator

def _validate_http_headers(instana_token, instana_base_url):
    """Validate HTTP mode headers."""
    if not instana_token or not instana_base_url:
        missing = []
        if not instana_token:
            missing.append("instana-api-token")
        if not instana_base_url:
            missing.append("instana-base-url")
        error_msg = f"HTTP mode detected but missing required headers: {', '.join(missing)}"
        print(f" {error_msg}", file=sys.stderr)
        return {"error": error_msg}

    if not instana_base_url.startswith("http://") and not instana_base_url.startswith("https://"):
        error_msg = "Instana base URL must start with http:// or https://"
        print(f" {error_msg}", file=sys.stderr)
        return {"error": error_msg}

    return None


def _validate_http_auth_headers(instana_api_token, instana_auth_token, instana_csrf_token, instana_base_url):
    """Validate HTTP authentication headers."""
    # Check for API token auth (needs token + base_url)
    has_api_token_auth = instana_api_token and instana_base_url

    # Check for session token auth (needs auth_token + csrf_token + base_url)
    has_session_auth = instana_auth_token and instana_csrf_token and instana_base_url

    if not has_api_token_auth and not has_session_auth:
        missing = []
        if not instana_base_url:
            missing.append("instana-base-url")
        if not instana_api_token and not (instana_auth_token and instana_csrf_token):
            missing.append("either (instana-api-token) OR (instana-auth-token + instana-csrf-token)")
        error_msg = f"HTTP mode detected but missing required headers: {', '.join(missing)}"
        logger.error(AUTH_FAILED_MSG, error_msg)
        return {"error": error_msg}

    # Validate URL format - HTTP protocol is allowed for development/testing environments
    # In production, HTTPS should always be used for security
    if not instana_base_url.startswith("http://") and not instana_base_url.startswith("https://"):  # NOSONAR - HTTP allowed for dev/test
        error_msg = "Instana base URL must start with http:// or https://"
        logger.error(AUTH_FAILED_MSG, error_msg)
        return {"error": error_msg}

    return None


def _create_api_client_with_config(base_url, instana_api_token, auth_headers):
    """Create API client with configuration based on auth type."""
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration

    configuration = Configuration()
    configuration.host = base_url

    # Configure based on auth type
    if "Authorization" in auth_headers:
        # API token mode
        if instana_api_token is None:
            error_msg = "API token is required but not provided"
            logger.error(AUTH_FAILED_MSG, error_msg)
            return None, {"error": error_msg}
        configuration.api_key['ApiKeyAuth'] = instana_api_token
        configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'
        logger.debug("Using API token authentication")
    else:
        # Session token mode
        logger.debug("Using session token authentication")

    # Create API client instance
    api_client_instance = ApiClient(configuration=configuration)
    user_agent_value = f"MCP-server/{__version__}"
    api_client_instance.set_default_header("User-Agent", header_value=user_agent_value)

    # For session auth, add CSRF and Cookie headers
    if "X-CSRF-TOKEN" in auth_headers:
        api_client_instance.set_default_header("X-CSRF-TOKEN", auth_headers["X-CSRF-TOKEN"])
        api_client_instance.set_default_header("Cookie", auth_headers["Cookie"])
        logger.debug("Set session auth headers")

    return api_client_instance, None


def _try_http_mode_auth(api_class):
    """Attempt HTTP mode authentication."""
    try:
        from fastmcp.server.dependencies import get_http_headers
        headers = get_http_headers()

        # Extract all possible authentication headers
        instana_api_token = headers.get("instana-api-token")
        instana_auth_token = headers.get("instana-auth-token")
        instana_csrf_token = headers.get("instana-csrf-token")
        instana_base_url = headers.get("instana-base-url")
        instana_cookie_name = headers.get("instana-cookie-name")

        # Check if we're in HTTP mode
        if not (instana_api_token or instana_auth_token or instana_csrf_token or instana_base_url):
            return None

        # Validate headers
        validation_error = _validate_http_auth_headers(
            instana_api_token, instana_auth_token, instana_csrf_token, instana_base_url
        )
        if validation_error:
            return validation_error

        # Build auth headers
        auth_headers = build_instana_api_headers(
            auth_token=instana_auth_token,
            csrf_token=instana_csrf_token,
            api_token=instana_api_token,
            cookie_name=instana_cookie_name
        )

        # Create API client
        api_client_instance, error = _create_api_client_with_config(
            instana_base_url, instana_api_token, auth_headers
        )
        if error:
            return error

        return api_class(api_client=api_client_instance)

    except (ImportError, AttributeError) as e:
        logger.error("Header detection failed, using STDIO mode: %s", e)
        return None


def _create_api_client_from_config(base_url, api_token):
    """Create API client from configuration (for STDIO mode)."""
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration

    configuration = Configuration()
    configuration.host = base_url
    configuration.api_key['ApiKeyAuth'] = api_token
    configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'

    api_client_instance = ApiClient(configuration=configuration)
    user_agent_value = f"MCP-server/{__version__}"
    api_client_instance.set_default_header("User-Agent", header_value=user_agent_value)

    return api_client_instance


def _validate_stdio_credentials(self):
    """Validate STDIO mode credentials."""
    if not self.read_token or not self.base_url:
        error_msg = "Authentication failed: Missing credentials "
        if not self.read_token:
            error_msg += " - INSTANA_API_TOKEN is missing"
        if not self.base_url:
            error_msg += " - INSTANA_BASE_URL is missing"
        print(f" {error_msg}", file=sys.stderr)
        return {"error": error_msg}
    return None


def _find_existing_api_client(self, api_class):
    """Find existing API client in self attributes."""
    api_class_name = getattr(api_class, '__name__', str(api_class))
    for attr_name in dir(self):
        if attr_name.endswith('_api'):
            attr = getattr(self, attr_name)
            if hasattr(attr, '__class__') and attr.__class__.__name__ == api_class_name:
                print(f"🔐 Found existing API client: {attr_name}", file=sys.stderr)
                return getattr(self, attr_name)
    return None


def _create_stdio_api_client(self, api_class):
    """Create new API client using STDIO credentials."""
    print(" Creating new API client with constructor credentials", file=sys.stderr)
    api_client_instance = _create_api_client_from_config(self.base_url, self.read_token)
    print(f"✅ Set User-Agent header: MCP-server/{__version__}", file=sys.stderr)
    return api_class(api_client=api_client_instance)


def _auth_check_mock(allow_mock, kwargs):
    """Check if mock client should be used."""
    if allow_mock and kwargs.get('api_client') is not None:
        print(" Using mock client for testing", file=sys.stderr)
        return True
    return False


def _auth_try_http(api_class):
    """Try HTTP mode authentication and return (api_instance, error)."""
    api_instance = _try_http_mode_auth(api_class)
    if isinstance(api_instance, dict) and "error" in api_instance:
        return None, api_instance
    return api_instance, None


def _auth_try_stdio(self, api_class):
    """Try STDIO mode authentication and return (api_instance, error)."""
    print(" Using constructor-based authentication (STDIO mode)", file=sys.stderr)
    print(f" self.base_url: {self.base_url}", file=sys.stderr)

    validation_error = _validate_stdio_credentials(self)
    if validation_error:
        return None, validation_error

    api_instance = _find_existing_api_client(self, api_class)
    if not api_instance:
        api_instance = _create_stdio_api_client(self, api_class)

    return api_instance, None


async def _auth_wrapper_logic(func, self, args, kwargs, api_class, allow_mock):
    """Execute authentication logic for the wrapper function."""
    # Check for mock client
    if _auth_check_mock(allow_mock, kwargs):
        return await func(self, *args, **kwargs)

    # Try HTTP mode first
    api_instance, error = _auth_try_http(api_class)
    if error:
        return error

    if api_instance:
        kwargs['api_client'] = api_instance
        return await func(self, *args, **kwargs)

    # Fall back to STDIO mode
    api_instance, error = _auth_try_stdio(self, api_class)
    if error:
        return error

    kwargs['api_client'] = api_instance
    return await func(self, *args, **kwargs)


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
        from typing import Any, Optional
        from fastmcp import Context

        @with_header_auth(YourApiClass)
        async def your_tool_method(self, param1, param2, ctx: Optional[Context] = None, api_client: Any = None):
            # The decorator automatically injects 'api_client' into the method
            result = api_client.your_api_method(param1, param2)
            return self._convert_to_dict(result)

    Note: Always type-annotate both 'ctx' (with Optional[Context]) and 'api_client' (with Any)
    to exclude them from the published schema. These are internal parameters injected by the decorator.
    """
    def decorator(func: Callable) -> Callable:
        import inspect
        sig = inspect.signature(func)

        new_params = [
            param for name, param in sig.parameters.items()
            if name not in ('api_client',)
        ]

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                return await _auth_wrapper_logic(func, self, args, kwargs, api_class, allow_mock)
            except Exception as e:
                print(f"Error in header auth decorator: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                error_msg = f"Authentication error: {e}" if isinstance(e, str) else f"Authentication error: {e!s}"
                return {"error": error_msg}

        wrapper.__signature__ = sig.replace(parameters=new_params)
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
            "Accept": "application/json",
            "User-Agent": f"MCP-server/{__version__}",
        }

    def handle_api_error_response(self, response, operation_name: str, logger) -> Dict[str, Any]:
        """
        Handle API error responses in a standardized way.

        Args:
            response: The API response object
            operation_name: Name of the operation for error messages
            logger: Logger instance for logging errors

        Returns:
            Dictionary with error information
        """
        error_message = f"Failed to {operation_name}: HTTP {response.status}"
        logger.error(f"[{operation_name}] {error_message}")

        try:
            error_body = decode_response(response)
            logger.error(f"[{operation_name}] API Error Response: {error_body}")
            return {
                "error": error_message,
                "details": error_body,
                "status_code": response.status
            }
        except Exception:
            return {"error": error_message, "status_code": response.status}

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

def decode_response(response) -> str:
    """
    Safely decode response data using the response's charset or UTF-8 as fallback.

    Args:
        response: The HTTP response object

    Returns:
        Decoded response text
    """
    from email.message import Message

    # Try to get charset from response headers using standard library parsing
    charset = DEFAULT_CHARSET  # Default fallback

    # Check if response has charset information
    if hasattr(response, 'headers') and response.headers:
        content_type = response.headers.get('Content-Type', '')
        if content_type:
            # Use email.message.Message for proper RFC-compliant Content-Type parsing
            # This handles quoted values, whitespace, case-insensitivity, etc.
            msg = Message()
            msg['content-type'] = content_type
            parsed_charset = msg.get_content_charset()
            if parsed_charset:
                charset = parsed_charset

    try:
        return response.data.decode(charset)
    except (UnicodeDecodeError, LookupError):
        # Fallback to DEFAULT_CHARSET if specified charset fails
        return response.data.decode(DEFAULT_CHARSET, errors='replace')


def extract_tag_names_from_tree(node, tag_names=None):
    """
    Recursively extract tag names from nested tree structure.

    Args:
        node: The tree node (dict or list) to extract tag names from
        tag_names: List to collect tag names (created if None)

    Returns:
        List of extracted tag names
    """
    if tag_names is None:
        tag_names = []

    if isinstance(node, dict):
        # If this node has a tagName, add it
        if node.get("tagName"):
            tag_names.append(node["tagName"])

        # Recursively process children
        if "children" in node and isinstance(node["children"], list):
            for child in node["children"]:
                extract_tag_names_from_tree(child, tag_names)
    elif isinstance(node, list):
        # If it's a list, process each item
        for item in node:
            extract_tag_names_from_tree(item, tag_names)

    return tag_names


def process_tag_catalog_response(full_response: Dict[str, Any], beacon_type: str, use_case: str) -> Dict[str, Any]:
    """
    Process tag catalog API response to extract tag names.

    This shared function reduces code duplication between website and mobile app catalog modules.

    Args:
        full_response: The full API response containing tagTree and/or tags
        beacon_type: The beacon type for the catalog
        use_case: The use case for the catalog

    Returns:
        Dictionary with tag_names, count, beacon_type, and use_case
    """
    tag_names = []

    # Extract from tagTree using shared utility function
    if "tagTree" in full_response:
        extract_tag_names_from_tree(full_response["tagTree"], tag_names)

    # Extract from flat tags list (using 'name' field)
    if "tags" in full_response and isinstance(full_response["tags"], list):
        for tag in full_response["tags"]:
            if isinstance(tag, dict) and "name" in tag and tag["name"]:
                tag_names.append(tag["name"])

    # Remove duplicates and sort
    tag_names = sorted(set(tag_names))

    return {
        "tag_names": tag_names,
        "count": len(tag_names),
        "beacon_type": beacon_type,
        "use_case": use_case
    }


def normalize_beacon_type(beacon_type: str, beacon_type_map: Dict[str, str]) -> str:
    """
    Normalize beacon type from uppercase to camelCase format.

    This shared function reduces code duplication between website and mobile app routers.

    Args:
        beacon_type: The beacon type to normalize (e.g., "SESSION_START", "PAGELOAD")
        beacon_type_map: Mapping of uppercase to camelCase formats

    Returns:
        Normalized beacon type in camelCase format
    """
    if beacon_type and isinstance(beacon_type, str) and beacon_type.upper() in beacon_type_map:
        return beacon_type_map[beacon_type.upper()]
    return beacon_type
