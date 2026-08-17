"""
Base Instana API Client Module

This module provides the base client for interacting with the Instana API.
"""

import json
import logging
import os
import sys
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

import requests

from src.core.api_headers import build_instana_api_headers

# Set up logger
logger = logging.getLogger(__name__)


def parse_payload(payload: Union[Dict[str, Any], str, None]) -> Union[Dict[str, Any], Dict[str, str]]:
    """
    Parse payload from string or dict format.

    This utility function handles payload parsing with multiple fallback strategies:
    1. If payload is None or empty, returns error
    2. If payload is already a dict, returns it as-is
    3. If payload is a string, attempts to parse as JSON
    4. If JSON parsing fails, attempts to parse as Python literal (ast.literal_eval)
    5. If all parsing fails, returns error dict

    Args:
        payload: Payload as dict, JSON string, or Python literal string

    Returns:
        Parsed dict if successful, error dict with 'error' key otherwise

    Examples:
        >>> parse_payload('{"key": "value"}')
        {'key': 'value'}

        >>> parse_payload("{'key': 'value'}")
        {'key': 'value'}

        >>> parse_payload({'key': 'value'})
        {'key': 'value'}

        >>> parse_payload(None)
        {'error': 'payload is required'}
    """
    if not payload:
        return {"error": "payload is required"}

    if isinstance(payload, dict):
        return payload

    if isinstance(payload, str):
        # Try JSON parsing first
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            # Fall back to Python literal evaluation
            try:
                import ast
                return ast.literal_eval(payload)
            except (ValueError, SyntaxError) as e:
                return {"error": f"Invalid payload format: {e!s}"}

    return {"error": f"Payload must be dict or JSON string, got {type(payload).__name__}"}

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
    __version__ = "1.0.0"

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

def _validate_http_auth_headers(instana_api_token, instana_jwt_token, instana_auth_token, instana_csrf_token, instana_base_url):
    """Validate HTTP authentication headers."""
    # Check for API token auth (needs token + base_url)
    has_api_token_auth = instana_api_token and instana_base_url
    # Check for JWT token auth (needs jwt_token + csrf_token + base_url)
    # JWT requires CSRF since it's treated as UI user for POST/PUT/DELETE operations
    has_jwt_token_auth = instana_jwt_token and instana_csrf_token and instana_base_url
    # Check for session token auth (needs auth_token + csrf_token + base_url)
    has_session_auth = instana_auth_token and instana_csrf_token and instana_base_url

    if not has_api_token_auth and not has_jwt_token_auth and not has_session_auth:
        missing = []
        if not instana_base_url:
            missing.append("instana-base-url")
        if not instana_api_token and not (instana_jwt_token and instana_csrf_token) and not (instana_auth_token and instana_csrf_token):
            missing.append("either (instana-api-token) OR (instana-jwt-token + instana-csrf-token) OR (instana-auth-token + instana-csrf-token)")
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


def _configure_auth_type(configuration, auth_headers, instana_api_token, instana_jwt_token):
    """Configure authentication type and validate tokens."""
    if "Authorization" not in auth_headers:
        logger.debug("Using session token authentication")
        return None

    auth_value = auth_headers["Authorization"]

    if auth_value.startswith("Bearer "):
        return _configure_jwt_auth(instana_jwt_token)

    if auth_value.startswith("apiToken "):
        return _configure_api_token_auth(configuration, instana_api_token)

    return None


def _configure_jwt_auth(instana_jwt_token):
    """Configure JWT token authentication."""
    if instana_jwt_token is None:
        error_msg = "JWT token is required but not provided"
        logger.error(AUTH_FAILED_MSG, error_msg)
        return {"error": error_msg}
    logger.debug("Using JWT token authentication")
    return None


def _configure_api_token_auth(configuration, instana_api_token):
    """Configure API token authentication.

    Note: For API token auth, we use the SDK's built-in api_key configuration
    instead of manually setting the Authorization header. This prevents conflicts
    where both methods might be used simultaneously.
    """
    if instana_api_token is None:
        error_msg = "API token is required but not provided"
        logger.error(AUTH_FAILED_MSG, error_msg)
        return {"error": error_msg}
    configuration.api_key['ApiKeyAuth'] = instana_api_token
    configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'
    logger.debug("Using API token authentication via SDK configuration")
    return None


def _mask_token_for_logging(token_value):
    """Mask token value for secure logging."""
    if len(token_value) > 30:
        return f"{token_value[:20]}...{token_value[-10:]}"
    return token_value[:10] + "..."


def _set_authorization_header(api_client_instance, auth_headers):
    """Set Authorization header on API client.

    Note: This should only be called for JWT and Session auth.
    For API token auth, the SDK's configuration handles authentication.
    """
    if "Authorization" not in auth_headers:
        return

    auth_header_value = auth_headers["Authorization"]

    # Skip setting Authorization header if it's an API token
    # (SDK configuration handles this via api_key)
    if auth_header_value.startswith("apiToken "):
        logger.debug("Skipping Authorization header for API token (using SDK configuration)")
        return

    # Set header for JWT Bearer tokens and other auth types.
    # Log only the scheme (e.g. "Bearer"), never any part of the token value.
    scheme = auth_header_value.split(" ", 1)[0]
    api_client_instance.set_default_header("Authorization", auth_header_value)
    logger.debug("Set Authorization header scheme: %s", scheme)


def _set_csrf_headers(api_client_instance, auth_headers):
    """Set CSRF and Cookie headers on API client."""
    if "X-CSRF-TOKEN" not in auth_headers:
        return

    csrf_value = auth_headers["X-CSRF-TOKEN"]
    masked_csrf = f"{csrf_value[:10]}...{csrf_value[-5:]}" if len(csrf_value) > 15 else csrf_value[:5] + "..."
    api_client_instance.set_default_header("X-CSRF-TOKEN", csrf_value)
    logger.debug(f"Set X-CSRF-TOKEN header: {masked_csrf}")

    if "Cookie" in auth_headers:
        api_client_instance.set_default_header("Cookie", auth_headers["Cookie"])
        logger.debug("Set session auth headers (CSRF + Cookie)")
    else:
        logger.debug("Set CSRF header for JWT auth (no Cookie)")


def _ssl_verify_from_env() -> bool:
    """Return SSL verification flag from INSTANA_SSL_VERIFY env var.

    Defaults to False (skip verification) when the variable is absent or unrecognised.
    Set INSTANA_SSL_VERIFY=true / 1 / yes to enable verification.
    """
    raw = os.getenv("INSTANA_SSL_VERIFY", "false").strip().lower()
    return raw not in ("0", "false", "no")


def _get_ctx_session_id(ctx) -> Optional[str]:
    """Return ctx.session_id as a string, or None if unavailable."""
    try:
        sid = ctx.session_id
        return str(sid) if sid else None
    except Exception:
        return None


def _get_ctx_request_id(ctx) -> Optional[str]:
    """Return ctx.request_id as a string, or None if unavailable."""
    try:
        rid = ctx.request_id
        return str(rid) if rid else None
    except Exception:
        return None


def _get_ctx_client_name(ctx) -> Optional[str]:
    """Return the LLM client name from the MCP initialize handshake, or None."""
    try:
        session = ctx.session
        client_params = getattr(session, "client_params", None) if session else None
        client_info = getattr(client_params, "clientInfo", None) if client_params else None
        name = getattr(client_info, "name", None)
        return str(name) if name else None
    except Exception:
        return None


def _build_mcp_tracking_context(ctx=None, http_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Build MCP tracking headers for outgoing Instana API calls (HTTP mode).

    Sources (all opportunistic — missing values are silently omitted):
      ctx.session_id                         → X-MCP-Session-ID  (stable per conversation)
      ctx.request_id                         → X-MCP-Request-ID  (unique per tool call)
      ctx.session.client_params.clientInfo   → X-MCP-Client      (LLM product name from MCP handshake)
      http_headers["x-mcp-user-id"]          → X-MCP-User-ID     (injected by upstream coordinator)
    """
    tracking: Dict[str, str] = {}

    if ctx is not None:
        sid = _get_ctx_session_id(ctx)
        if sid:
            tracking["X-MCP-Session-ID"] = sid

        rid = _get_ctx_request_id(ctx)
        if rid:
            tracking["X-MCP-Request-ID"] = rid

        client = _get_ctx_client_name(ctx)
        if client:
            tracking["X-MCP-Client"] = client

    if http_headers:
        user_id = http_headers.get("x-mcp-user-id", "")
        if user_id:
            tracking["X-MCP-User-ID"] = user_id

    return tracking


def _stamp_tracking_headers(api_client_instance, tracking: Dict[str, str]) -> None:
    """Set MCP tracking headers on an SDK ApiClient as default headers."""
    for name, value in tracking.items():
        if value:
            api_client_instance.set_default_header(name, value)


def _create_api_client_with_config(base_url, instana_api_token, instana_jwt_token, auth_headers,
                                    tracking: Optional[Dict[str, str]] = None):
    """Create API client with configuration based on auth type."""
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration

    configuration = Configuration()
    configuration.host = base_url
    configuration.verify_ssl = _ssl_verify_from_env()
    if configuration.verify_ssl:
        ca_bundle = os.getenv("INSTANA_CA_BUNDLE")
        if ca_bundle:
            configuration.ssl_ca_cert = ca_bundle
            logger.info("SSL verification is ENABLED (custom CA bundle: %s)", ca_bundle)
        else:
            logger.info("SSL verification is ENABLED (system CA bundle)")
    else:
        logger.warning("SSL verification is DISABLED. Set INSTANA_SSL_VERIFY=true or pass --verify-ssl to enable.")

    # Configure authentication type
    error = _configure_auth_type(configuration, auth_headers, instana_api_token, instana_jwt_token)
    if error:
        return None, error

    # Create API client instance
    api_client_instance = ApiClient(configuration=configuration)
    user_agent_value = f"MCP-server/{__version__}"
    api_client_instance.set_default_header("User-Agent", header_value=user_agent_value)

    # Set authentication headers
    _set_authorization_header(api_client_instance, auth_headers)
    _set_csrf_headers(api_client_instance, auth_headers)

    # Stamp MCP tracking headers so every outgoing Instana REST call carries them
    if tracking:
        _stamp_tracking_headers(api_client_instance, tracking)

    return api_client_instance, None


def _try_http_mode_auth(api_class, tracking: Optional[Dict[str, str]] = None):
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
        instana_jwt_token = headers.get("instana-jwt-token")

        # Check if we're in HTTP mode
        if not (instana_api_token or instana_jwt_token or instana_auth_token or instana_csrf_token or instana_base_url):
            return None

        # Validate headers
        validation_error = _validate_http_auth_headers(
            instana_api_token, instana_jwt_token, instana_auth_token, instana_csrf_token, instana_base_url
        )
        if validation_error:
            return validation_error

        # Build auth headers
        auth_headers = build_instana_api_headers(
            auth_token=instana_auth_token,
            csrf_token=instana_csrf_token,
            jwt_token=instana_jwt_token,
            api_token=instana_api_token,
            cookie_name=instana_cookie_name
        )

        # Enrich tracking with x-mcp-user-id forwarded by the upstream coordinator.
        # get_http_headers() returns all non-auth request headers, so this is safe.
        if tracking is not None:
            user_id = headers.get("x-mcp-user-id", "")
            if user_id:
                tracking["X-MCP-User-ID"] = user_id

        # Create API client, stamping tracking headers onto it
        api_client_instance, error = _create_api_client_with_config(
            instana_base_url, instana_api_token, instana_jwt_token, auth_headers, tracking
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
    configuration.verify_ssl = _ssl_verify_from_env()
    if configuration.verify_ssl:
        ca_bundle = os.getenv("INSTANA_CA_BUNDLE")
        if ca_bundle:
            configuration.ssl_ca_cert = ca_bundle
            logger.info("SSL verification is ENABLED (custom CA bundle: %s)", ca_bundle)
        else:
            logger.info("SSL verification is ENABLED (system CA bundle)")
    else:
        logger.warning("SSL verification is DISABLED. Set INSTANA_SSL_VERIFY=true or pass --verify-ssl to enable.")
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


def _auth_try_http(api_class, tracking: Optional[Dict[str, str]] = None):
    """Try HTTP mode authentication and return (api_instance, error)."""
    api_instance = _try_http_mode_auth(api_class, tracking)
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

    # Extract the FastMCP Context injected by FastMCP for tools that declare
    # `ctx: Optional[Context]`. Used to read session_id, request_id, and clientInfo.
    #
    # ctx can arrive two ways:
    #   1. As a keyword argument  → kwargs["ctx"]          (top-level router tools)
    #   2. As a positional argument → args[n]              (internal helpers called as
    #      `await self._method(id, ctx)` without an explicit keyword)
    # We check kwargs first, then fall back to inspecting the function signature to
    # locate the positional index of the `ctx` parameter.
    ctx = kwargs.get("ctx")
    if ctx is None:
        import inspect as _inspect
        try:
            _param_names = list(_inspect.signature(func).parameters.keys())
            # param_names[0] is always 'self'; args starts after self
            _ctx_pos = _param_names.index("ctx") - 1  # -1 to skip 'self'
            if 0 <= _ctx_pos < len(args):
                ctx = args[_ctx_pos]
        except (ValueError, TypeError):
            pass  # 'ctx' not in signature or inspection failed — leave ctx as None

    # Build per-call tracking context for the HTTP path.
    # x-mcp-user-id is read later inside _try_http_mode_auth where we have the
    # raw HTTP request headers from get_http_headers().
    tracking = _build_mcp_tracking_context(ctx=ctx)

    logger.info(
        "MCP tool call | tool=%s session_id=%s request_id=%s client=%s user_id=%s",
        func.__name__,
        tracking.get("X-MCP-Session-ID", "-"),
        tracking.get("X-MCP-Request-ID", "-"),
        tracking.get("X-MCP-Client", "-"),
        tracking.get("X-MCP-User-ID", "-"),
    )

    # Try HTTP mode first — passes tracking so headers are stamped on the ApiClient
    api_instance, error = _auth_try_http(api_class, tracking)
    if error:
        return error

    if api_instance:
        kwargs['api_client'] = api_instance
        return await func(self, *args, **kwargs)

    # Fall back to STDIO mode (tracking not applied for POC scope)
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
        self.ssl_verify = _ssl_verify_from_env()

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
            ssl_verify = self.ssl_verify
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, verify=ssl_verify)
            elif method.upper() == "POST":
                # Use the json parameter if provided, otherwise use params
                data_to_send = json if json is not None else params
                response = requests.post(url, headers=headers, json=data_to_send, verify=ssl_verify)
            elif method.upper() == "PUT":
                data_to_send = json if json is not None else params
                response = requests.put(url, headers=headers, json=data_to_send, verify=ssl_verify)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params, verify=ssl_verify)
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


def _extract_tag_name_from_dict(node, tag_names):
    """Extract tag name from a dict node if present."""
    tag_name = node.get("tagName")
    if not tag_name:
        return

    # For infrastructure catalog format with type TAG
    if node.get("type") == "TAG":
        if tag_name not in tag_names:
            tag_names.append(tag_name)
    else:
        # For website/mobile app catalogs
        tag_names.append(tag_name)


def _process_dict_children(node, tag_names):
    """Process children, tagTree, and tags arrays in a dict node."""
    # Process children array
    children = node.get("children")
    if isinstance(children, list):
        for child in children:
            extract_tag_names_from_tree(child, tag_names)

    # Process tagTree (infrastructure catalog)
    if "tagTree" in node:
        extract_tag_names_from_tree(node["tagTree"], tag_names)

    # Process tags array (alternative structure)
    tags = node.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            extract_tag_names_from_tree(tag, tag_names)


def extract_tag_names_from_tree(node, tag_names=None):
    """
    Recursively extract tag names from nested tree structure.
    Handles multiple tag catalog formats (infrastructure, website, mobile app).

    Args:
        node: The tree node (dict or list) to extract tag names from
        tag_names: List to collect tag names (created if None)

    Returns:
        List of extracted tag names
    """
    if tag_names is None:
        tag_names = []

    if isinstance(node, dict):
        _extract_tag_name_from_dict(node, tag_names)
        _process_dict_children(node, tag_names)
    elif isinstance(node, list):
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


def project_metric_card(metric: Dict[str, Any]) -> Dict[str, Any]:
    """
    Project a raw metric catalog entry to a compact card for query planning.

    Keeps fields that help a planner build valid analyze calls (metricId, label,
    description, aggregations, beaconTypes, formatter) and drops internal SDK
    fields (pathToValueInBeacon, tagName, defaultAggregation) that bloat the
    payload or mislead the planner.

    Args:
        metric: A single metric entry from the Instana metric catalog.

    Returns:
        Compact metric card with a stable schema (keys present even when value is None).
    """
    return {
        "metricId": metric.get("metricId"),
        "label": metric.get("label"),
        "description": metric.get("description"),
        "aggregations": metric.get("aggregations") or [],
        "beaconTypes": metric.get("beaconTypes") or [],
        "formatter": metric.get("formatter"),
    }


WEBSITE_BEACON_TYPE_MAP = {
    "PAGELOAD": "pageLoad",
    "PAGE_CHANGE": "pageChange",
    "RESOURCELOAD": "resourceLoad",
    "CUSTOM": "custom",
    "HTTPREQUEST": "httpRequest",
    "ERROR": "error",
}

MOBILE_BEACON_TYPE_MAP = {
    "SESSION_START": "sessionStart",
    "VIEW_CHANGE": "viewChange",
    "HTTP_REQUEST": "httpRequest",
    "CUSTOM": "custom",
    "CRASH": "crash",
    "PERF": "perf",
    "DROP_BEACON": "dropBeacon",
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
