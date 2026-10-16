"""
Base Instana API Client Module

This module provides the base client for interacting with the Instana API.
"""

import ast
import functools
import http.client
import inspect
import json
import logging
import os
import ssl
import sys
from email.message import Message
from typing import Any, Callable, Dict, Optional, Union

import anyio
import requests
import urllib3
from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.auth_helper import _auth_wrapper_logic, _ssl_verify_from_env

# Default wall-clock timeout for every Instana SDK call (seconds).
# Override at the process level with INSTANA_API_TIMEOUT=<seconds>.
_DEFAULT_API_TIMEOUT: int = 180


def _api_timeout() -> int:
    """Return the per-call API timeout in seconds.

    Reads ``INSTANA_API_TIMEOUT`` from the environment.  Falls back to
    ``_DEFAULT_API_TIMEOUT`` (180 s) when the variable is absent or non-integer.
    """
    raw = os.getenv("INSTANA_API_TIMEOUT", "").strip()
    if raw:
        try:
            val = int(raw)
            if val > 0:
                return val
        except ValueError:
            pass
    return _DEFAULT_API_TIMEOUT

# Set up logger
logger = logging.getLogger(__name__)


async def call_sdk_fn(fn: Callable, **kwargs) -> Any:
    """Invoke a synchronous Instana SDK method off the event-loop thread.

    The Instana Python SDK uses the ``requests`` library under the hood, so
    every ``api_client.*()`` call is a blocking network I/O operation.  When
    called directly inside an ``async`` handler it monopolises the asyncio
    event loop for the duration of the HTTP round-trip, which has two bad
    consequences in a multi-user MCP deployment:

    1. All other in-flight requests are stalled until the call returns.
    2. The MCP transport layer (SSE / streamable-HTTP) cannot flush keepalive
       frames while the loop is blocked, so idle-timeout timers on intermediate
       proxies and load-balancers fire and drop the connection.

    This helper fixes both problems:

    * **Production path** — ``anyio.to_thread.run_sync`` runs the synchronous
      SDK function in a worker thread, leaving the event loop free to process
      other requests and send keepalive notifications.  ``anyio`` is the async
      backend used by FastMCP/Starlette, so this integrates correctly with the
      server's task scheduler — unlike ``asyncio.to_thread``, which does not
      participate in anyio's structured-concurrency machinery.

    * **Test path** — when ``fn`` is an ``AsyncMock`` (or any coroutine
      function), it is awaited directly so unit tests do not need a thread
      pool.

    Usage::

        response = await call_sdk_fn(api_client.get_events_without_preload_content,
                                     from_time=t0, to_time=t1)

    Args:
        fn: The synchronous (or async-mock) SDK callable.
        **kwargs: Keyword arguments forwarded verbatim to ``fn``.

    Returns:
        Whatever ``fn`` returns.
    """
    if inspect.iscoroutinefunction(fn):
        return await fn(**kwargs)
    # anyio.to_thread.run_sync integrates with anyio's event loop (used by
    # FastMCP / Starlette / uvicorn) and correctly yields control back to the
    # scheduler while the blocking SDK call runs in a worker thread.
    #
    # abandon_on_cancel=True: if the containing task group is cancelled while
    # the SDK call is in-flight (e.g. client disconnected), release the capacity
    # limiter token immediately instead of holding the thread slot until the
    # blocking requests call eventually times out.
    return await anyio.to_thread.run_sync(functools.partial(fn, **kwargs), abandon_on_cancel=True)


def _build_log_prefix(
    operation_name: str,
    tool_name: Optional[str],
    resource_type: Optional[str],
) -> str:
    """Build the ``[tool:resource] operation`` log prefix string."""
    if tool_name and resource_type:
        return "[%s:%s] %s" % (tool_name, resource_type, operation_name)
    if tool_name:
        return "[%s] %s" % (tool_name, operation_name)
    if resource_type:
        return "[%s] %s" % (resource_type, operation_name)
    return "[%s]" % operation_name


_PREVIEW = 500  # Maximum number of characters shown in a response-body preview.


def _json_preview(obj: Any) -> str:
    """Serialize *obj* to a JSON string, truncated to ``_PREVIEW`` chars."""
    try:
        raw = json.dumps(obj, default=str)
    except Exception:
        raw = repr(obj)
    return raw[:_PREVIEW] + ("…" if len(raw) > _PREVIEW else "")


def _result_summary(result: Any) -> str:
    """Return a compact, safe summary string for *result* suitable for debug logging."""
    if hasattr(result, "status"):          # raw HTTPResponse (without_preload_content)
        # Never access .data via getattr here: on a without_preload_content response
        # .data is a urllib3 property that buffers the entire body on first access.
        # If the caller intends to stream the body via .read(n) (e.g.
        # stream_filter_events), touching .data would exhaust the stream before
        # parsing begins.  Only peek when .data has already been materialised as a
        # plain bytes instance in the instance __dict__ (preload_content responses).
        body = result.__dict__.get("data") if hasattr(result, "__dict__") else None
        if not isinstance(body, bytes) or not body:
            return f"HTTPResponse status={result.status}"
        try:
            decoded = body.decode("utf-8", errors="replace")
        except Exception:
            decoded = repr(body[:_PREVIEW])
        suffix = "…" if len(decoded) > _PREVIEW else ""
        return f"HTTPResponse status={result.status} body={decoded[:_PREVIEW]}{suffix}"
    if isinstance(result, list):
        first = f" first={_json_preview(result[0])}" if result else ""
        return f"list len={len(result)}{first}"
    if isinstance(result, dict):
        return f"dict {_json_preview(result)}"
    if hasattr(result, "to_dict"):         # Pydantic/SDK model
        return f"{type(result).__name__} {_json_preview(result.to_dict())}"
    return type(result).__name__


async def sdk_call_with_keepalive(
    coro,
    ctx=None,
    operation_name: str = "operation",
    keepalive_interval: int = 5,
    resource_type: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> Any:
    """Run an SDK coroutine while sending periodic keepalive log messages.

    MCP clients connect over Server-Sent Events (SSE) or streamable HTTP.
    Both transports rely on a persistent TCP connection that passes through
    corporate proxies, AWS ALBs, and Cloudflare — each of which has its own
    idle-timeout (often 60 s).  If the server sends no bytes during a long
    Instana API call the connection is silently dropped.

    This helper runs the SDK coroutine and a keepalive ticker concurrently in
    an anyio task group.  While the SDK call is in-flight, an MCP
    ``notifications/message`` log frame is sent every *keepalive_interval*
    seconds via ``ctx.log``.  Unlike ``ctx.report_progress`` (which requires
    the client to include a ``progressToken``), ``ctx.log`` is an
    unconditional push — real bytes on the wire that reset every idle timer
    between client and server.

    A hard wall-clock timeout is also enforced.  When the SDK call does not
    complete within *timeout* seconds the task group is cancelled and an error
    dict is returned immediately — no more indefinitely hanging requests.  The
    timeout defaults to the ``INSTANA_API_TIMEOUT`` environment variable
    (integer seconds), falling back to 180 seconds when unset.

    Both the SDK task and the ticker run inside ``anyio.create_task_group``,
    which is the correct structured-concurrency primitive for the anyio runtime
    used by FastMCP.

    Usage::

        response = await sdk_call_with_keepalive(
            call_sdk_fn(api_client.get_events_without_preload_content, **params),
            ctx=ctx,
            operation_name="get_events",
            tool_name="manage_events",
            resource_type="events",
        )

    Args:
        coro: An awaitable / coroutine representing the SDK call.
        ctx: The FastMCP :class:`~fastmcp.Context` instance (may be ``None``
             when called from tests or non-MCP code paths).
        operation_name: Short label used in the log messages, e.g. ``"get_events"``.
            This name is also used for debug-level log entries that bracket the
            SDK call: ``"[<name>] Starting SDK call"`` and
            ``"[<name>] SDK call completed"``.
        keepalive_interval: Seconds between keepalive log messages (default 5).
        resource_type: Optional resource type from the smart router (e.g.
            ``"events"``, ``"metrics"``).  Included in debug log lines when
            provided so that log entries can be correlated back to the
            originating router dispatch.
        tool_name: Optional MCP tool name from the smart router (e.g.
            ``"manage_events"``).  Included in debug log lines when provided.

    Returns:
        The return value of ``coro``, or an error dict when the deadline fires.
    """
    effective_timeout = _api_timeout()
    prefix = _build_log_prefix(operation_name, tool_name, resource_type)
    result_holder: list[Any] = []

    logger.debug("%s Starting SDK call (timeout=%ds)", prefix, effective_timeout)

    async def _run_sdk(cancel_scope: anyio.CancelScope) -> None:
        result_holder.append(await coro)
        logger.debug("%s SDK call completed", prefix)
        # Cancel the task group scope so the keepalive ticker stops immediately
        # rather than waiting out its current sleep interval.
        cancel_scope.cancel()

    async def _run_keepalive() -> None:
        # Only called when ctx is truthy (see task group below).
        elapsed = 0
        while True:
            await anyio.sleep(keepalive_interval)
            elapsed += keepalive_interval
            try:
                # ctx.log → send_notification → write_stream.send() can block
                # indefinitely on a zero-buffer channel if the message_router
                # or SSE writer is itself blocked (common under simultaneous
                # stateless requests).  Wrap in a short deadline so a stalled
                # notification never prevents the SDK result from being returned.
                with anyio.move_on_after(2):
                    await ctx.log(
                        f"{prefix} Waiting for Instana API response… ({elapsed}s elapsed)",
                        level="info",
                        logger_name=operation_name,
                    )
            except Exception:
                pass  # Never allow keepalive errors to propagate.

    async def _run_with_task_group() -> None:
        """Run SDK + keepalive concurrently, unwrapping single-exception groups."""
        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(_run_sdk, tg.cancel_scope)
                tg.start_soon(_run_keepalive)
        except BaseExceptionGroup as eg:
            # anyio wraps a task's exception in an ExceptionGroup.
            # Unwrap and re-raise the original SDK exception directly so
            # callers (and their except-blocks) see the real error.
            if len(eg.exceptions) == 1:
                raise eg.exceptions[0] from None
            raise  # multiple failures - re-raise the group as-is

    sdk_coro = _run_with_task_group() if ctx else _run_sdk(anyio.CancelScope())
    with anyio.move_on_after(effective_timeout) as deadline_scope:
        await sdk_coro

    if deadline_scope.cancelled_caught:
        logger.error(
            "%s Instana API call timed out after %ds. "
            "Increase the limit with INSTANA_API_TIMEOUT env var.",
            prefix, effective_timeout,
        )
        return {
            "error": (
                f"Instana API call timed out after {effective_timeout}s "
                f"({operation_name}). The Instana server did not respond in time. "
                f"Increase the limit with the INSTANA_API_TIMEOUT environment variable."
            ),
            "operation": operation_name,
            "resource_type": resource_type,
            "timeout_seconds": effective_timeout,
        }

    if not result_holder:
        raise RuntimeError("SDK call completed without result — this should not happen")

    result = result_holder[0]
    logger.debug("%s Response: %s", prefix, _result_summary(result))
    return result


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
                return ast.literal_eval(payload)
            except (ValueError, SyntaxError) as e:
                return {"error": f"Invalid payload format: {e!s}"}

    return {"error": f"Payload must be dict or JSON string, got {type(payload).__name__}"}


_BUFFER_SIZE_UNITS = {
    "kb": 1024,
    "k":  1024,
    "mb": 1024 ** 2,
    "m":  1024 ** 2,
    "gb": 1024 ** 3,
    "g":  1024 ** 3,
}

DEFAULT_STREAM_READ_BUFFER_SIZE: int = 65536


def parse_buffer_size(value: str) -> int:
    """Parse a human-friendly buffer size string into an integer number of bytes.

    Accepted formats (case-insensitive):
        ``65536``        plain integer string
        ``64k`` / ``64kb``   kibibytes  (× 1 024)
        ``64m`` / ``64mb``   mebibytes  (× 1 048 576)
        ``64g`` / ``64gb``   gibibytes  (× 1 073 741 824)

    Returns:
        The size as a plain ``int`` (bytes).

    Raises:
        ``ValueError`` if the string cannot be parsed.
    """
    text = str(value).strip().lower()
    # Try longest suffix first so "mb" is matched before "m"
    for suffix in ("kb", "mb", "gb", "k", "m", "g"):
        if text.endswith(suffix):
            numeric_part = text[: -len(suffix)]
            try:
                return int(float(numeric_part) * _BUFFER_SIZE_UNITS[suffix])
            except ValueError:
                raise ValueError(
                    f"Invalid buffer size {value!r}: '{numeric_part}' is not a number"
                )
    # Plain integer
    try:
        return int(text)
    except ValueError:
        raise ValueError(
            f"Invalid buffer size {value!r}: expected a number optionally followed by "
            "k/kb, m/mb, or g/gb (e.g. 65536, 64k, 64kb, 64m, 64mb)"
        )


def _resolve_stream_chunk_size(chunk_size: Optional[int] = None) -> int:
    """Resolve stream chunk size from argument or STREAM_READ_BUFFER_SIZE env var.

    Falls back to DEFAULT_STREAM_READ_BUFFER_SIZE (65536 bytes) with a warning
    if the environment variable or chunk_size is invalid (e.g. non-positive).
    """
    if chunk_size is not None and chunk_size > 0:
        return chunk_size

    env_val = os.environ.get("STREAM_READ_BUFFER_SIZE")
    if env_val:
        try:
            parsed = parse_buffer_size(env_val)
            if parsed > 0:
                return parsed
            logger.warning(
                "Invalid STREAM_READ_BUFFER_SIZE=%r (must be > 0); falling back to default %d bytes",
                env_val,
                DEFAULT_STREAM_READ_BUFFER_SIZE,
            )
        except ValueError as exc:
            logger.warning(
                "Invalid STREAM_READ_BUFFER_SIZE=%r (%s); falling back to default %d bytes",
                env_val,
                exc,
                DEFAULT_STREAM_READ_BUFFER_SIZE,
            )
    return DEFAULT_STREAM_READ_BUFFER_SIZE


# Default charset for response decoding
DEFAULT_CHARSET = 'utf-8'


def _charset_from_content_type(content_type: str) -> str:
    """Return the charset parameter from a Content-Type header value, or DEFAULT_CHARSET."""
    if not isinstance(content_type, str):
        return DEFAULT_CHARSET
    for part in content_type.split(";"):
        key, _, value = part.strip().partition("=")
        if key.strip().lower() == "charset" and value.strip():
            return value.strip().strip('"')
    return DEFAULT_CHARSET

# Import for getting package version from metadata rather than server.py
try:
    from importlib.metadata import version
    __version__ = version("mcp-instana")
except Exception:
    # Fallback version if package metadata is not available
    __version__ = "0.12.100"

# Registry to store all tools
MCP_TOOLS = {}

def register_as_tool(title=None, annotations=None, description=None):
    """
    Enhanced decorator that registers both in MCP_TOOLS and with @mcp.tool

    Args:
        title: Title for the MCP tool (optional, defaults to function name)
        annotations: ToolAnnotations for the MCP tool (optional)
        description: Explicit description for the tool (optional, uses the docstring when no description is provided)
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

        @functools.wraps(func)
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
    # Try to get charset from response headers using standard library parsing
    charset = DEFAULT_CHARSET  # Default fallback

    # Check if response has charset information
    if hasattr(response, 'headers') and response.headers:
        content_type = response.headers.get('Content-Type', '')
        if isinstance(content_type, str) and content_type:
            charset = _charset_from_content_type(content_type)

    if hasattr(response, 'data'):
        data = response.data
        if isinstance(data, (bytes, bytearray)):
            try:
                return data.decode(charset)
            except (UnicodeDecodeError, LookupError):
                return data.decode(DEFAULT_CHARSET, errors='replace')
        elif hasattr(data, 'decode'):
            return data.decode(charset)
        elif isinstance(data, str):
            return data

    return ""


def _resolve_response_charset(response) -> str:
    """Return the charset declared in *response*'s Content-Type header, or UTF-8."""
    if hasattr(response, "headers") and response.headers:
        ct = response.headers.get("Content-Type", "")
        if ct:
            return _charset_from_content_type(ct)
    return DEFAULT_CHARSET


def _make_chunk_reader(response, chunk_size: int, charset: str):
    """Return a callable that reads the next decoded text chunk from *response*.

    The returned ``_read_chunk()`` calls ``response.read(chunk_size)`` for
    streaming responses. For pre-buffered responses without a callable ``read``
    attribute, it falls back to ``response.data``, draining it on the first call
    so subsequent calls return "".

    Network and I/O exceptions during ``read()`` are not swallowed so that
    callers can distinguish a broken stream from normal end-of-stream.
    """
    def _read_chunk() -> str:
        read_attr = getattr(response, "read", None)
        raw = None
        if callable(read_attr):
            try:
                result = response.read(chunk_size)
                if isinstance(result, (bytes, bytearray)):
                    raw = result
            except (requests.exceptions.ReadTimeout, urllib3.exceptions.ReadTimeoutError, TimeoutError) as e:
                logger.warning("Read timeout while streaming response chunk: %s", e)
                raise
            except (requests.exceptions.ChunkedEncodingError, urllib3.exceptions.IncompleteRead, http.client.IncompleteRead) as e:
                logger.warning("Incomplete or truncated response chunk received: %s", e)
                raise
            except (requests.exceptions.ConnectionError, urllib3.exceptions.ProtocolError, ConnectionError) as e:
                logger.warning("Connection closed or reset while streaming response: %s", e)
                raise
            except (requests.exceptions.SSLError, ssl.SSLError) as e:
                logger.warning("SSL/TLS error during stream read: %s", e)
                raise
            except requests.exceptions.RequestException as e:
                logger.warning("HTTP request exception during chunk read: %s", e)
                raise
            except OSError as e:
                logger.warning("Socket/I/O error during chunk read: %s", e)
                raise
            except Exception as e:
                logger.warning(
                    "Unexpected error reading chunk from response stream: %s",
                    e,
                    exc_info=True,
                )
                raise

        if raw is None:
            raw_data = getattr(response, "data", None)
            if isinstance(raw_data, (bytes, bytearray)):
                raw = bytes(raw_data)
                try:
                    response.data = b""
                except Exception:
                    pass
            elif isinstance(raw_data, str):
                raw = raw_data.encode(charset)
                try:
                    response.data = b""
                except Exception:
                    pass
            else:
                raw = b""

        if not raw:
            return ""
        try:
            return raw.decode(charset)
        except (UnicodeDecodeError, LookupError):
            return raw.decode(DEFAULT_CHARSET, errors="replace")

    return _read_chunk


def _iter_json_array(response, chunk_size: Optional[int] = None):
    """Yield items one by one from a streaming JSON array HTTP response.

    Reads the raw response in ``chunk_size`` byte chunks and uses
    ``json.JSONDecoder.raw_decode`` to peel objects off a rolling text buffer.
    If the response body is empty or non-array, iteration terminates immediately
    without yielding any items.
    """
    chunk_size = _resolve_stream_chunk_size(chunk_size)
    charset = _resolve_response_charset(response)
    _read_chunk = _make_chunk_reader(response, chunk_size, charset)

    decoder = json.JSONDecoder()
    buf = ""

    # Scan forward to the opening '['
    while "[" not in buf:
        chunk = _read_chunk()
        if not chunk:
            return
        buf += chunk

    bracket_pos = buf.index("[")
    buf = buf[bracket_pos + 1:]

    # Check for empty array [] before entering loop
    if buf.lstrip().startswith("]"):
        return

    # Peel one JSON object at a time
    while True:
        buf = buf.lstrip()
        while not buf:
            chunk = _read_chunk()
            if not chunk:
                break
            buf = chunk.lstrip()

        if not buf or buf[0] == "]":
            break

        if buf[0] == ",":
            buf = buf[1:].lstrip()
            while not buf:
                chunk = _read_chunk()
                if not chunk:
                    break
                buf = chunk.lstrip()

        if not buf or buf[0] == "]":
            break

        while True:
            try:
                obj, end_pos = decoder.raw_decode(buf)
                buf = buf[end_pos:]
                break
            except json.JSONDecodeError:
                chunk = _read_chunk()
                if not chunk:
                    return
                buf += chunk

        yield obj


def stream_json_array_page(
    response,
    start_idx: int,
    end_idx: int,
    chunk_size: Optional[int] = None,
) -> tuple:
    """Stream-parse an unbounded JSON array response, returning only the page slice.

    Instana ``find_active`` endpoints return an unbounded JSON array with no
    server-side pagination.  The naive approach — ``response.data`` then
    ``json.loads`` — buffers the entire response body and builds a full Python
    list before slicing, which is expensive for large tenants.

    This function avoids that by streaming the response and yielding objects
    one by one. Items before ``start_idx`` or after ``end_idx`` are not retained
    in memory, keeping peak memory to ``O(chunk_size + page_size x avg_item_size)``.

    Args:
        response: A ``urllib3.HTTPResponse`` whose ``.read(n)`` returns
            successive bytes chunks. Must not have been read yet
            (i.e. ``response.data`` must not have been accessed).
        start_idx: First 0-based index to include in the returned slice.
        end_idx:   One-past-last index (exclusive upper bound).
        chunk_size: Bytes per I/O call. 64 KiB balances syscall overhead
            against memory pressure.

    Returns:
        ``(page_items, total_seen)`` where ``page_items`` is the list of
        items at positions ``[start_idx, end_idx)`` and ``total_seen`` is
        the count of all items the parser encountered in the array.

        If the response body is empty or is a JSON ``null`` / ``{}`` rather
        than an array, ``([], 0)`` is returned.
    """
    logger.info("stream_json_array_page called")
    page_items: list = []
    total_seen = 0

    for obj in _iter_json_array(response, chunk_size):
        if start_idx <= total_seen < end_idx:
            page_items.append(obj)
        total_seen += 1

    return page_items, total_seen


def stream_filter_events(
    response,
    filter_fn,
    max_results: int,
    chunk_size: Optional[int] = None,
) -> tuple:
    """Stream-parse an Instana events array response, applying a filter per object.

    Unlike ``stream_json_array_page`` (which slices by index), this function
    applies a caller-supplied predicate to each decoded object and collects only
    matching items. Non-matching objects are decoded and immediately discarded,
    so peak memory is ``O(chunk_size + max_results x avg_item_size)`` regardless
    of how large the total response body is.

    IMPORTANT: ``response.data`` must NOT have been accessed before calling this
    function.  Accessing ``.data`` on a ``urllib3.HTTPResponse`` buffers the
    entire body, exhausting the stream.

    Args:
        response: A ``urllib3.HTTPResponse`` whose ``.read(n)`` returns successive
            byte chunks.  Must not have been read yet.
        filter_fn: Callable that accepts a single decoded dict and returns ``True``
            if the item should be included in the result.
        max_results: Stop collecting after this many matching items.
        chunk_size: Bytes per I/O read call (default 64 KiB).

    Returns:
        ``(matched_items, total_seen)`` where ``matched_items`` is the list of
        dicts for which ``filter_fn`` returned ``True`` (length <= ``max_results``)
        and ``total_seen`` is the total number of objects present in the array
        (matched + unmatched), useful for ``total_events`` metadata.

        Returns ``([], 0)`` for an empty body, a non-array JSON value, or any
        response whose array cannot be located.
    """
    logger.info("stream_filter_events called")
    matched: list = []
    total_seen = 0

    for obj in _iter_json_array(response, chunk_size):
        if len(matched) < max_results and filter_fn(obj):
            matched.append(obj)
        total_seen += 1

    return matched, total_seen


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


def process_tag_catalog_response(full_response: Dict[str, Any], beacon_type: Optional[str], use_case: str) -> Dict[str, Any]:
    """
    Process tag catalog API response to extract tag names.

    This shared function reduces code duplication between website, mobile app, and synthetic catalog modules.

    Args:
        full_response: The full API response containing tagTree and/or tags
        beacon_type: The beacon type for the catalog (None for synthetics, which has no beacon type)
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
