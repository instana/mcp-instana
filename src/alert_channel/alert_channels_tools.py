"""
Alert Channels MCP Tools Module.

Provides specialized operations to list, filter, and inspect Instana alert channels
using EventSettingsApi with automatic fail-closed secret masking.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastmcp import Context

from src.core.alert_channel_utils import (
    ALLOWED_FIELDS_BY_KIND,
    mask_channel,
    redact_for_log,
)
from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    sdk_call_with_keepalive,
    with_header_auth,
)

try:
    from instana_client.api.event_settings_api import EventSettingsApi
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("Failed to import EventSettingsApi from instana_client", exc_info=True)
    raise

logger = logging.getLogger(__name__)

_MAX_ERROR_BODY_CHARS = 500
MAX_PAGE_SIZE = 100
ACCESS_DENIED_ERROR = "Access denied: Missing required permission 'canConfigureIntegrations'"


def _parse_json_body(raw: Any) -> Any:
    """
    Deserialize an SDK response body (bytes/str) into Python data.

    Already-parsed values (dict/list) are returned unchanged. Returns None when the body is
    empty or not valid JSON, so callers can fail closed without leaking the raw payload.
    """
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = bytes(raw).decode("utf-8")
        except UnicodeDecodeError:
            return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    return raw


def _unexpected_body_error(operation: str, expected: type, parsed: Any, response: Any) -> Optional[Dict[str, Any]]:
    """
    Return an error dict when a successful response body is not valid JSON of the expected type.

    Returns None when ``parsed`` is usable. Never echoes the body itself.
    """
    if isinstance(parsed, expected):
        return None
    return {
        "error": f"Instana returned a non-JSON or unexpected response body for {operation}",
        "status_code": getattr(response, "status", 200),
    }


def _safe_error_body(data: Any) -> str:
    """
    Build a log/response-safe description of an upstream error body.

    JSON bodies are passed through ``redact_for_log`` and truncated; anything that cannot be
    parsed is omitted entirely (fail-closed) because it might echo submitted credentials.
    """
    if not data:
        return ""
    parsed = _parse_json_body(data)
    if parsed is None or isinstance(parsed, (bytes, bytearray, str)):
        return "<non-JSON error body omitted>"
    try:
        text = json.dumps(redact_for_log(parsed), default=str)
    except (TypeError, ValueError):
        return "<unserializable error body omitted>"
    if len(text) > _MAX_ERROR_BODY_CHARS:
        text = text[:_MAX_ERROR_BODY_CHARS] + "...(truncated)"
    return text


def _normalize_ids(raw_ids: Any) -> tuple[Optional[List[str]], Optional[Dict[str, Any]]]:
    """Normalize and validate channel IDs parameter."""
    if raw_ids is None:
        return None, None
    if isinstance(raw_ids, str):
        ids = [i.strip() for i in raw_ids.split(",") if i.strip()]
    elif isinstance(raw_ids, list):
        ids = [str(i).strip() for i in raw_ids if i is not None and str(i).strip()]
    else:
        return None, {
            "elicitation_needed": True,
            "reason": "invalid_parameters",
            "api_error": [{"field": "ids", "issue": "ids must be a list or comma-separated string"}],
            "message": "Parameter 'ids' must be a list of strings or a comma-separated string.",
        }
    return (ids if ids else None), None


def _validate_pagination(page: Any, page_size: Any) -> tuple[int, int, Optional[Dict[str, Any]]]:
    """Cast and validate pagination parameters."""
    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = int(page_size)
    except (ValueError, TypeError):
        page_size = 20

    if page < 1:
        return page, page_size, {
            "elicitation_needed": True,
            "reason": "invalid_parameters",
            "api_error": [{"field": "page", "issue": "page must be >= 1"}],
            "message": "Parameter 'page' must be greater than or equal to 1.",
        }
    if page_size < 1:
        return page, page_size, {
            "elicitation_needed": True,
            "reason": "invalid_parameters",
            "api_error": [{"field": "page_size", "issue": "page_size must be >= 1"}],
            "message": "Parameter 'page_size' must be greater than or equal to 1.",
        }
    return page, min(page_size, MAX_PAGE_SIZE), None


def _validate_kind(kind: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate alert channel kind filter against allowed kinds."""
    if not kind:
        return None
    if kind.strip().upper() not in ALLOWED_FIELDS_BY_KIND:
        valid_kinds = sorted(ALLOWED_FIELDS_BY_KIND)
        logger.warning("Unknown alert channel kind filter %.50r; rejecting request", kind)
        return {
            "elicitation_needed": True,
            "reason": "invalid_parameters",
            "api_error": [{"field": "kind", "issue": f"unknown kind; valid kinds: {', '.join(valid_kinds)}"}],
            "message": f"Unknown kind '{kind}'. Valid kinds: {', '.join(valid_kinds)}.",
            "valid_kinds": valid_kinds,
        }
    return None


def _handle_overview_response_error(response: Any) -> Optional[Dict[str, Any]]:
    """Check and handle HTTP error responses for get_overview."""
    if not hasattr(response, "status") or response.status < 400:
        return None
    if response.status == 401:
        logger.warning("get_overview: 401 Unauthorized - API token is missing, invalid, or expired")
        return {
            "error": ACCESS_DENIED_ERROR,
            "status_code": response.status,
        }
    if response.status == 403:
        logger.warning("get_overview: 403 Forbidden - API token lacks 'canConfigureIntegrations' permission")
        return {
            "error": ACCESS_DENIED_ERROR,
            "status_code": response.status,
        }
    err_body = _safe_error_body(getattr(response, "data", None))
    return {
        "error": f"Failed to retrieve alert channels overview: {err_body}",
        "status_code": response.status,
    }


def _filter_and_sort_channels(
    parsed: Any,
    kind: Optional[str],
    name_filter: Optional[str],
) -> List[Dict[str, Any]]:
    """Filter channels by kind and name, then sort deterministically."""
    items: List[Dict[str, Any]] = [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []

    if kind:
        target_kind = kind.strip().upper()
        items = [item for item in items if str(item.get("kind", "")).upper() == target_kind]

    if name_filter:
        target_name = name_filter.strip().lower()
        items = [item for item in items if target_name in str(item.get("name", "")).lower()]

    items.sort(key=lambda item: (str(item.get("name", "")).lower(), str(item.get("id", ""))))
    return items


def _paginate_items(items: List[Dict[str, Any]], page: int, page_size: int) -> Dict[str, Any]:
    """Slice and mask page items, returning paginated metadata."""
    total_count = len(items)
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = items[start_idx:end_idx]

    masked_items = mask_channel(page_items)

    return {
        "items": masked_items,
        "count": len(masked_items),
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }


def _match_channel_by_name(
    all_channels: List[Dict[str, Any]], name: str
) -> tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Match channel from overview list by exact or substring name."""
    target_name = name.strip().lower()
    exact_matches = [
        ch for ch in all_channels
        if str(ch.get("name", "")).strip().lower() == target_name
    ]
    if len(exact_matches) == 1:
        return exact_matches[0].get("id"), None, None
    if len(exact_matches) > 1:
        return None, None, {
            "elicitation_needed": True,
            "reason": "ambiguous_name",
            "message": f"Multiple alert channels match name '{name}'. Please specify the channel ID.",
            "candidates": [
                {"id": c.get("id"), "name": c.get("name"), "kind": c.get("kind")}
                for c in exact_matches
            ],
        }

    substring_matches = [
        ch for ch in all_channels
        if target_name in str(ch.get("name", "")).strip().lower()
    ]
    if len(substring_matches) == 1:
        resolved_id = substring_matches[0].get("id")
        name_resolution = {
            "match_type": "substring",
            "requested_name": name,
            "resolved_name": substring_matches[0].get("name"),
            "resolved_id": resolved_id,
            "note": (
                "No exact name match; resolved via unique substring match. "
                "Verify this is the intended channel or use 'id'."
            ),
        }
        return resolved_id, name_resolution, None
    if len(substring_matches) > 1:
        return None, None, {
            "elicitation_needed": True,
            "reason": "ambiguous_name",
            "message": f"Multiple alert channels match substring '{name}'. Please specify the channel ID.",
            "candidates": [
                {"id": c.get("id"), "name": c.get("name"), "kind": c.get("kind")}
                for c in substring_matches
            ],
        }

    return None, None, {
        "error": f"No alert channel found with name '{name}'",
        "status_code": 404,
    }


async def _fetch_and_resolve_name(
    api_client: Any,
    name: str,
    ctx: Optional[Context],
    resource_type: Optional[str],
    tool_name: Optional[str],
) -> tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Fetch overview list and resolve channel by name."""
    target_name = name.strip().lower()
    if not target_name:
        return None, None, {
            "error": "Parameter 'name' must not be empty or whitespace-only",
            "status_code": 400,
        }

    overview_resp = await sdk_call_with_keepalive(
        call_sdk_fn(api_client.get_alerting_channels_overview_without_preload_content),
        ctx=ctx,
        operation_name="get_alerting_channels_overview_for_lookup",
        resource_type=resource_type,
        tool_name=tool_name,
    )
    if isinstance(overview_resp, dict):
        return None, None, overview_resp

    if hasattr(overview_resp, "status") and overview_resp.status >= 400:
        if overview_resp.status == 401:
            logger.warning("get (name lookup): 401 Unauthorized - API token is missing, invalid, or expired")
            return None, None, {
                "error": ACCESS_DENIED_ERROR,
                "status_code": overview_resp.status,
            }
        if overview_resp.status == 403:
            logger.warning(
                "get (name lookup): 403 Forbidden - API token lacks 'canConfigureIntegrations' permission"
            )
            return None, None, {
                "error": ACCESS_DENIED_ERROR,
                "status_code": overview_resp.status,
            }
        return None, None, {
            "error": f"Failed to resolve channel name: HTTP {overview_resp.status}",
            "status_code": overview_resp.status,
        }

    parsed_overview = _parse_json_body(getattr(overview_resp, "data", None))
    body_error = _unexpected_body_error("name lookup", list, parsed_overview, overview_resp)
    if body_error:
        return None, None, body_error

    all_channels: List[Dict[str, Any]] = [ch for ch in parsed_overview if isinstance(ch, dict)]
    return _match_channel_by_name(all_channels, name)


def _handle_get_response_error(response: Any, resolved_id: str) -> Optional[Dict[str, Any]]:
    """Check and handle HTTP error responses for get channel by ID."""
    if not hasattr(response, "status") or response.status < 400:
        return None
    if response.status == 404:
        return {
            "error": f"Alert channel '{resolved_id}' not found",
            "status_code": 404,
        }
    if response.status == 401:
        logger.warning("get: 401 Unauthorized - API token is missing, invalid, or expired")
        return {
            "error": ACCESS_DENIED_ERROR,
            "status_code": response.status,
        }
    if response.status == 403:
        logger.warning("get: 403 Forbidden - API token lacks 'canConfigureIntegrations' permission")
        return {
            "error": ACCESS_DENIED_ERROR,
            "status_code": response.status,
        }
    err_body = _safe_error_body(getattr(response, "data", None))
    return {
        "error": f"Failed to get alert channel '{resolved_id}': {err_body}",
        "status_code": response.status,
    }


class AlertChannelsMCPTools(BaseInstanaClient):
    """Client for managing and inspecting Instana alert channels."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Alert Channels MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(EventSettingsApi)
    async def get_overview(
        self,
        ids: str | List[str] | None = None,
        kind: Optional[str] = None,
        name_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        ctx: Optional[Context] = None,
        api_client: Optional[Any] = None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get an overview list of alert channels with filtering and pagination.

        Args:
            ids: Optional channel IDs to filter by upstream (list, or comma-separated string).
            kind: Optional integration kind filter (e.g. 'WEB_HOOK', 'EMAIL', 'SLACK').
            name_filter: Optional substring filter on channel name.
            page: 1-based page index (default: 1).
            page_size: Number of items per page (default: 20, max: 100).
            ctx: Optional FastMCP context.
            api_client: Injected EventSettingsApi instance.
            resource_type: Observability resource type.
            tool_name: Observability tool name.

        Returns:
            Paginated dictionary with masked integration overview items.
        """
        try:
            normalized_ids, ids_error = _normalize_ids(ids)
            if ids_error:
                return ids_error

            page, page_size, pag_error = _validate_pagination(page, page_size)
            if pag_error:
                return pag_error

            logger.debug(
                "get_overview called (ids=%s, kind=%s, name_filter=%s, page=%s, page_size=%s)",
                bool(normalized_ids), kind, bool(name_filter), page, page_size
            )

            kind_error = _validate_kind(kind)
            if kind_error:
                return kind_error

            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_alerting_channels_overview_without_preload_content,
                    ids=normalized_ids,
                ),
                ctx=ctx,
                operation_name="get_alerting_channels_overview",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            # sdk_call_with_keepalive returns an error dict (e.g. on timeout) instead of a response
            if isinstance(response, dict):
                return response

            http_error = _handle_overview_response_error(response)
            if http_error:
                return http_error

            parsed = _parse_json_body(getattr(response, "data", None))
            body_error = _unexpected_body_error("get_overview", list, parsed, response)
            if body_error:
                return body_error

            filtered_items = _filter_and_sort_channels(parsed, kind, name_filter)
            return _paginate_items(filtered_items, page, page_size)

        except Exception as e:
            logger.error("Error in get_overview: %s", e, exc_info=True)
            return {"error": f"Failed to get alert channels overview: {e!s}"}

    @with_header_auth(EventSettingsApi)
    async def get(
        self,
        channel_id: Optional[str] = None,
        name: Optional[str] = None,
        ctx: Optional[Context] = None,
        api_client: Optional[Any] = None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed configuration for a specific alert channel by ID or name.

        Args:
            channel_id: ID of the alert channel.
            name: Name of the alert channel (resolved automatically).
            ctx: Optional FastMCP context.
            api_client: Injected EventSettingsApi instance.
            resource_type: Observability resource type.
            tool_name: Observability tool name.

        Returns:
            Sanitized dictionary containing complete masked channel configuration.
        """
        try:
            logger.debug("get called (channel_id=%s, name=%s)", bool(channel_id), bool(name))

            if not channel_id and not name:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "id",
                            "issue": "Either 'id' or 'name' must be provided",
                            "hint": "Use operation='get_overview' to find channel IDs and names",
                        }
                    ],
                    "message": "Missing required parameter: provide either 'id' or 'name'.",
                }

            resolved_id = channel_id
            name_resolution: Optional[Dict[str, Any]] = None

            if not resolved_id and name:
                resolved_id, name_resolution, lookup_err = await _fetch_and_resolve_name(
                    api_client, name, ctx, resource_type, tool_name
                )
                if lookup_err:
                    return lookup_err

            if not resolved_id:
                return {
                    "error": f"Could not resolve alert channel ID for '{name}'",
                    "status_code": 404,
                }

            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_alerting_channel_without_preload_content,
                    id=resolved_id,
                ),
                ctx=ctx,
                operation_name="get_alerting_channel",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            # sdk_call_with_keepalive returns an error dict (e.g. on timeout) instead of a response
            if isinstance(response, dict):
                return response

            http_error = _handle_get_response_error(response, resolved_id)
            if http_error:
                return http_error

            parsed_channel = _parse_json_body(getattr(response, "data", None))
            body_error = _unexpected_body_error("get", dict, parsed_channel, response)
            if body_error:
                return body_error

            masked_channel = mask_channel(parsed_channel)
            if name_resolution and isinstance(masked_channel, dict):
                masked_channel["name_resolution"] = name_resolution
            return masked_channel

        except Exception as e:
            logger.error("Error in get alert channel: %s", e, exc_info=True)
            return {"error": f"Failed to get alert channel: {e!s}"}
