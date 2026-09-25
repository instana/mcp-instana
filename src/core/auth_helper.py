"""
Authentication helpers for the Instana MCP server.

Contains all private functions that support the ``with_header_auth`` decorator
in ``utils.py``: HTTP/STDIO credential resolution, SDK API client construction,
MCP tracking-header building, and the async wrapper logic.
"""

import importlib.metadata
import inspect
import logging
import os
from typing import Callable, Dict, Optional

from fastmcp.server.dependencies import get_http_headers
from instana_client.api_client import ApiClient
from instana_client.configuration import Configuration

from src.core.api_headers import build_instana_api_headers

logger = logging.getLogger(__name__)

AUTH_FAILED_MSG = "Authentication failed: %s"


# ---------------------------------------------------------------------------
# SSL helper
# ---------------------------------------------------------------------------

def _ssl_verify_from_env() -> bool:
    """Return SSL verification flag from INSTANA_SSL_VERIFY env var.

    Defaults to True (verify SSL) when the variable is absent or unrecognised.
    Set INSTANA_SSL_VERIFY=false / 0 / no to disable verification.
    """
    raw = os.getenv("INSTANA_SSL_VERIFY", "true").strip().lower()
    return raw not in ("0", "false", "no")


# ---------------------------------------------------------------------------
# HTTP header validation & auth configuration
# ---------------------------------------------------------------------------

def _validate_http_auth_headers(
    instana_api_token, instana_jwt_token, instana_auth_token,
    instana_csrf_token, instana_base_url,
):
    """Validate HTTP authentication headers.

    Returns ``{"error": ...}`` on failure, ``None`` when all required fields
    are present.
    """
    has_api_token_auth = instana_api_token and instana_base_url
    has_jwt_token_auth = instana_jwt_token and instana_csrf_token and instana_base_url
    has_session_auth = instana_auth_token and instana_csrf_token and instana_base_url

    if not (has_api_token_auth or has_jwt_token_auth or has_session_auth):
        missing = []
        if not instana_base_url:
            missing.append("instana-base-url")
        if not instana_api_token and not (instana_jwt_token and instana_csrf_token) and not (instana_auth_token and instana_csrf_token):
            missing.append(
                "either (instana-api-token) OR "
                "(instana-jwt-token + instana-csrf-token) OR "
                "(instana-auth-token + instana-csrf-token)"
            )
        error_msg = f"HTTP mode detected but missing required headers: {', '.join(missing)}"
        logger.error(AUTH_FAILED_MSG, error_msg)
        return {"error": error_msg}

    # HTTP protocol is permitted for dev/test; HTTPS required in production.
    if not instana_base_url.startswith("http://") and not instana_base_url.startswith("https://"):  # NOSONAR
        error_msg = "Instana base URL must start with http:// or https://"
        logger.error(AUTH_FAILED_MSG, error_msg)
        return {"error": error_msg}

    return None


def _configure_auth_type(configuration, auth_headers, instana_api_token, instana_jwt_token):
    """Configure authentication type on the SDK *configuration* object."""
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
    """Validate that a JWT token is present."""
    if instana_jwt_token is None:
        error_msg = "JWT token is required but not provided"
        logger.error(AUTH_FAILED_MSG, error_msg)
        return {"error": error_msg}
    logger.debug("Using JWT token authentication")
    return None


def _configure_api_token_auth(configuration, instana_api_token):
    """Configure API token authentication via the SDK's built-in api_key mechanism."""
    if instana_api_token is None:
        error_msg = "API token is required but not provided"
        logger.error(AUTH_FAILED_MSG, error_msg)
        return {"error": error_msg}
    configuration.api_key["ApiKeyAuth"] = instana_api_token
    configuration.api_key_prefix["ApiKeyAuth"] = "apiToken"
    logger.debug("Using API token authentication via SDK configuration")
    return None


# ---------------------------------------------------------------------------
# Header-stamping helpers
# ---------------------------------------------------------------------------

def _set_authorization_header(api_client_instance, auth_headers):
    """Set the Authorization header on *api_client_instance*.

    Skipped for API-token auth because the SDK configuration already handles
    that via ``api_key`` — setting it manually would conflict.
    """
    if "Authorization" not in auth_headers:
        return

    auth_header_value = auth_headers["Authorization"]
    if auth_header_value.startswith("apiToken "):
        logger.debug("Skipping Authorization header for API token (using SDK configuration)")
        return

    scheme = auth_header_value.split(" ", 1)[0]
    api_client_instance.set_default_header("Authorization", auth_header_value)
    logger.debug("Set Authorization header scheme: %s", scheme)


def _set_csrf_headers(api_client_instance, auth_headers):
    """Set CSRF and Cookie headers on *api_client_instance*."""
    if "X-CSRF-TOKEN" not in auth_headers:
        return

    csrf_value = auth_headers["X-CSRF-TOKEN"]
    masked = (
        f"{csrf_value[:10]}...{csrf_value[-5:]}"
        if len(csrf_value) > 15
        else csrf_value[:5] + "..."
    )
    api_client_instance.set_default_header("X-CSRF-TOKEN", csrf_value)
    logger.debug("Set X-CSRF-TOKEN header: %s", masked)

    if "Cookie" in auth_headers:
        api_client_instance.set_default_header("Cookie", auth_headers["Cookie"])
        logger.debug("Set session auth headers (CSRF + Cookie)")
    else:
        logger.debug("Set CSRF header for JWT auth (no Cookie)")


# ---------------------------------------------------------------------------
# MCP tracking context
# ---------------------------------------------------------------------------

def _get_ctx_session_id(ctx) -> Optional[str]:
    """Return ``ctx.session_id`` as a string, or ``None`` if unavailable."""
    try:
        sid = ctx.session_id
        return str(sid) if sid else None
    except Exception:
        return None


def _get_ctx_request_id(ctx) -> Optional[str]:
    """Return ``ctx.request_id`` as a string, or ``None`` if unavailable."""
    try:
        rid = ctx.request_id
        return str(rid) if rid else None
    except Exception:
        return None


def _get_ctx_client_name(ctx) -> Optional[str]:
    """Return the LLM client name from the MCP initialise handshake, or ``None``."""
    try:
        session = ctx.session
        client_params = getattr(session, "client_params", None) if session else None
        client_info = getattr(client_params, "clientInfo", None) if client_params else None
        name = getattr(client_info, "name", None)
        return str(name) if name else None
    except Exception:
        return None


def _build_mcp_tracking_context(
    ctx=None,
    tool_name: Optional[str] = None,
    resource_type: Optional[str] = None,
) -> Dict[str, str]:
    """Build MCP tracking headers for outgoing Instana API calls (HTTP mode).

    Sources (all opportunistic — missing values are silently omitted):
      ctx.session_id                         → X-MCP-Session-ID      (stable per conversation)
      ctx.request_id                         → X-MCP-Request-ID      (unique per tool call)
      ctx.session.client_params.clientInfo   → X-MCP-Client          (LLM product name from MCP handshake)
      tool_name                              → X-MCP-Tool            (e.g. "manage_applications")
      resource_type                          → X-MCP-Resource-Type   (e.g. "metrics")

    ``X-MCP-Environment-Type`` is resolved separately in ``_try_http_mode_auth``,
    where the raw HTTP headers are available, and mutates the returned dict
    in-place.
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

    if tool_name:
        tracking["X-MCP-Tool"] = tool_name

    if resource_type:
        tracking["X-MCP-Resource-Type"] = resource_type

    return tracking


def _stamp_tracking_headers(api_client_instance, tracking: Dict[str, str]) -> None:
    """Set MCP tracking headers on an SDK ApiClient as default headers."""
    for name, value in tracking.items():
        if value:
            api_client_instance.set_default_header(name, value)


# ---------------------------------------------------------------------------
# API client construction
# ---------------------------------------------------------------------------

def _get_mcp_version() -> str:
    """Return the installed mcp-instana package version, falling back to a default."""
    try:
        return importlib.metadata.version("mcp-instana")
    except Exception:
        return "0.12.100"


def _apply_ssl_config(configuration):
    """Apply SSL verification settings to *configuration* from env vars."""
    configuration.verify_ssl = _ssl_verify_from_env()
    if configuration.verify_ssl:
        ca_bundle = os.getenv("INSTANA_CA_BUNDLE")
        if ca_bundle:
            configuration.ssl_ca_cert = ca_bundle
            logger.info("SSL verification is ENABLED (custom CA bundle: %s)", ca_bundle)
        else:
            logger.info("SSL verification is ENABLED (system CA bundle)")
    else:
        logger.warning(
            "SSL verification is DISABLED. "
            "Set INSTANA_SSL_VERIFY=true or pass --verify-ssl to enable."
        )


def _create_api_client_with_config(
    base_url, instana_api_token, instana_jwt_token, auth_headers,
    tracking: Optional[Dict[str, str]] = None,
):
    """Create an SDK ApiClient configured for the given auth type (HTTP mode).

    Returns ``(api_client_instance, None)`` on success or ``(None, error_dict)``
    on failure.
    """
    configuration = Configuration()
    configuration.host = base_url
    _apply_ssl_config(configuration)

    error = _configure_auth_type(configuration, auth_headers, instana_api_token, instana_jwt_token)
    if error:
        return None, error

    api_client_instance = ApiClient(configuration=configuration)
    api_client_instance.set_default_header("User-Agent", f"MCP-server/{_get_mcp_version()}")

    _set_authorization_header(api_client_instance, auth_headers)
    _set_csrf_headers(api_client_instance, auth_headers)

    if tracking:
        _stamp_tracking_headers(api_client_instance, tracking)

    return api_client_instance, None


def _create_api_client_from_config(base_url, api_token):
    """Create an SDK ApiClient for STDIO mode (API-token only)."""
    configuration = Configuration()
    configuration.host = base_url
    _apply_ssl_config(configuration)
    configuration.api_key["ApiKeyAuth"] = api_token
    configuration.api_key_prefix["ApiKeyAuth"] = "apiToken"

    api_client_instance = ApiClient(configuration=configuration)
    api_client_instance.set_default_header("User-Agent", f"MCP-server/{_get_mcp_version()}")

    return api_client_instance


# ---------------------------------------------------------------------------
# HTTP mode auth
# ---------------------------------------------------------------------------

def _try_http_mode_auth(api_class, tracking: Optional[Dict[str, str]] = None):
    """Attempt HTTP-mode authentication and return an instantiated *api_class*.

    Returns:
      - An instance of *api_class* on success.
      - ``{"error": ...}`` dict on auth failure.
      - ``None`` when no HTTP headers are detected (caller falls back to STDIO).
    """
    try:
        headers = get_http_headers()

        instana_api_token = headers.get("instana-api-token")
        instana_auth_token = headers.get("instana-auth-token")
        instana_csrf_token = headers.get("instana-csrf-token")
        instana_base_url = headers.get("instana-base-url")
        instana_cookie_name = headers.get("instana-cookie-name")
        instana_jwt_token = headers.get("instana-jwt-token")

        # Not in HTTP mode — signal caller to fall back to STDIO
        if not (instana_api_token or instana_jwt_token or instana_auth_token
                or instana_csrf_token or instana_base_url):
            return None

        validation_error = _validate_http_auth_headers(
            instana_api_token, instana_jwt_token, instana_auth_token,
            instana_csrf_token, instana_base_url,
        )
        if validation_error:
            return validation_error

        auth_headers = build_instana_api_headers(
            auth_token=instana_auth_token,
            csrf_token=instana_csrf_token,
            jwt_token=instana_jwt_token,
            api_token=instana_api_token,
            cookie_name=instana_cookie_name,
        )

        # Resolve X-MCP-Environment-Type for Amplitude segmentation.
        #
        # Three distinct auth paths, three distinct values:
        #   JWT token  → "platform"  Concert platform coordinator flow
        #                             (platform → instana-coordinator → MCP)
        #   Session    → "SaaS"      Standalone Instana UI flow
        #                             (UI → ui-backend → instana-coordinator → MCP)
        #                             Identified by auth-token + csrf-token + cookie-name
        #   API token  → (omitted)   Direct / STDIO mode; no deploy signal available
        #
        # Values are never PII — they describe the calling integration, not the user.
        if tracking is not None:
            if instana_jwt_token:
                tracking["X-MCP-Environment-Type"] = "platform"
            elif instana_auth_token and instana_csrf_token and instana_cookie_name:
                tracking["X-MCP-Environment-Type"] = "SaaS"

        api_client_instance, error = _create_api_client_with_config(
            instana_base_url, instana_api_token, instana_jwt_token,
            auth_headers, tracking,
        )
        if error:
            return error

        return api_class(api_client=api_client_instance)

    except (ImportError, AttributeError) as e:
        logger.error("Header detection failed, using STDIO mode: %s", e)
        return None


# ---------------------------------------------------------------------------
# STDIO mode auth
# ---------------------------------------------------------------------------

def _validate_stdio_credentials(self):
    """Validate STDIO mode credentials on a ``BaseInstanaClient`` instance."""
    if not self.read_token or not self.base_url:
        error_msg = "Authentication failed: Missing credentials "
        if not self.read_token:
            error_msg += " - INSTANA_API_TOKEN is missing"
        if not self.base_url:
            error_msg += " - INSTANA_BASE_URL is missing"
        logger.error(AUTH_FAILED_MSG, error_msg)
        return {"error": error_msg}
    return None


def _find_existing_api_client(self, api_class):
    """Return a cached API client already attached to *self*, or ``None``."""
    api_class_name = getattr(api_class, "__name__", str(api_class))
    for attr_name in dir(self):
        if attr_name.endswith("_api"):
            attr = getattr(self, attr_name)
            if hasattr(attr, "__class__") and attr.__class__.__name__ == api_class_name:
                logger.debug("Found existing API client: %s", attr_name)
                return attr
    return None


def _create_stdio_api_client(self, api_class):
    """Create a new API client using STDIO credentials from *self*."""
    logger.debug("Creating new API client with constructor credentials")
    api_client_instance = _create_api_client_from_config(self.base_url, self.read_token)
    logger.debug("Set User-Agent header: MCP-server/%s", _get_mcp_version())
    return api_class(api_client=api_client_instance)


# ---------------------------------------------------------------------------
# Auth orchestration — called by with_header_auth in utils.py
# ---------------------------------------------------------------------------

def _auth_check_mock(allow_mock, kwargs):
    """Return ``True`` if a pre-built mock client should be used as-is."""
    if allow_mock and kwargs.get("api_client") is not None:
        logger.debug("Using mock client for testing")
        return True
    return False


def _auth_try_http(api_class, tracking: Optional[Dict[str, str]] = None):
    """Attempt HTTP auth and return ``(api_instance, error)``."""
    api_instance = _try_http_mode_auth(api_class, tracking)
    if isinstance(api_instance, dict) and "error" in api_instance:
        return None, api_instance
    return api_instance, None


def _auth_try_stdio(self, api_class):
    """Attempt STDIO auth and return ``(api_instance, error)``."""
    logger.debug("Using constructor-based authentication (STDIO mode)")
    logger.debug("self.base_url: %s", self.base_url)

    validation_error = _validate_stdio_credentials(self)
    if validation_error:
        return None, validation_error

    api_instance = _find_existing_api_client(self, api_class)
    if not api_instance:
        api_instance = _create_stdio_api_client(self, api_class)

    return api_instance, None


async def _auth_wrapper_logic(func, self, args, kwargs, api_class, allow_mock):
    """Core authentication logic executed by the ``with_header_auth`` wrapper."""
    # Short-circuit for test mocks
    if _auth_check_mock(allow_mock, kwargs):
        return await func(self, *args, **kwargs)

    # Resolve the FastMCP Context — arrives as a kwarg or positional arg.
    ctx = kwargs.get("ctx")
    if ctx is None:
        try:
            _param_names = list(inspect.signature(func).parameters.keys())
            # _param_names[0] == "self"; positional args start after that
            _ctx_pos = _param_names.index("ctx") - 1
            if 0 <= _ctx_pos < len(args):
                ctx = args[_ctx_pos]
        except (ValueError, TypeError):
            pass  # "ctx" not in signature — leave as None

    # tool_name and resource_type are injected as kwargs by every smart router
    tool_name = kwargs.get("tool_name")
    resource_type = kwargs.get("resource_type")

    # Build tracking dict — X-MCP-Environment-Type is filled in by _auth_try_http
    # (after JWT detection), so the log below reflects the final state.
    tracking = _build_mcp_tracking_context(
        ctx=ctx, tool_name=tool_name, resource_type=resource_type,
    )

    # HTTP mode — also stamps X-MCP-Environment-Type when a JWT token is present
    api_instance, error = _auth_try_http(api_class, tracking)

    if error:
        return error

    logger.info(
        "MCP tool call | tool=%s resource_type=%s method=%s "
        "session_id=%s request_id=%s client=%s environment_type=%s",
        tracking.get("X-MCP-Tool", "-"),
        tracking.get("X-MCP-Resource-Type", "-"),
        func.__name__,
        tracking.get("X-MCP-Session-ID", "-"),
        tracking.get("X-MCP-Request-ID", "-"),
        tracking.get("X-MCP-Client", "-"),
        tracking.get("X-MCP-Environment-Type", "-"),
    )

    if api_instance:
        kwargs["api_client"] = api_instance
        return await func(self, *args, **kwargs)

    # STDIO fallback (tracking not stamped — POC scope)
    api_instance, error = _auth_try_stdio(self, api_class)
    if error:
        return error

    kwargs["api_client"] = api_instance
    return await func(self, *args, **kwargs)
