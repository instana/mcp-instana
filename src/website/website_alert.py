"""
Website Alert MCP Tools Module

This module provides website alert-specific MCP tools for Instana monitoring.
Uses the api/event-settings endpoints.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import urllib3
from mcp.types import ToolAnnotations

from src.core.alert_config_utils import (
    parse_alert_config_response,
    parse_single_alert_config_response,
)
from src.core.elicitation import missing_param
from src.core.utils import (
    BaseInstanaClient,
    _api_timeout,
    call_sdk_fn,
    decode_response,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)

# Import the necessary classes from the SDK
try:
    from instana_client.api.event_settings_api import (
        EventSettingsApi,
    )
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("Failed to import website app alert configuration API", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

_NO_ERROR_DETAILS = "No error details available (empty response body)"

# Operations that change live alerting; a timeout on these leaves the outcome unknown.
_WRITE_OPERATIONS = frozenset({
    "create_website_alert_config",
    "update_website_alert_config",
    "delete_website_alert_config",
    "enable_website_alert_config",
    "disable_website_alert_config",
    "restore_website_alert_config",
})

# Fields the server owns. They are echoed by GET but must not be sent back on update.
# `rbacTags` is read-only: the SDK's writable WebsiteAlertConfig model has no such property.
_SERVER_ONLY_FIELDS = ("id", "created", "initialCreated", "readOnly", "displayUrl", "rbacTags")
# Legacy single-rule fields. GET returns them, but sending them back next to `rules`
# is rejected with 422, so they are dropped on update.
_LEGACY_RULE_FIELDS = ("rule", "threshold", "severity")


def _strip_baselines(body: Dict[str, Any]) -> Dict[str, Any]:
    """Return ``body`` with ``baseline`` removed from every ``rules[*].thresholds.*`` entry.

    The baseline is computed by the server and is very large, so it is not sent back.
    """
    rules = body.get("rules")
    if not isinstance(rules, list):
        return body
    cleaned = []
    for item in rules:
        thresholds = item.get("thresholds") if isinstance(item, dict) else None
        if isinstance(thresholds, dict):
            thresholds = {
                sev: ({k: v for k, v in t.items() if k != "baseline"} if isinstance(t, dict) else t)
                for sev, t in thresholds.items()
            }
            item = {**item, "thresholds": thresholds}
        cleaned.append(item)
    return {**body, "rules": cleaned}


# Longest API error body returned to the caller.
_MAX_ERROR_TEXT = 2000

# Failures where the request provably never left the client, so a retry is safe.
_NOT_SENT = (urllib3.exceptions.NewConnectionError, urllib3.exceptions.ConnectTimeoutError)

_ID_HINT = "Use resource_type='alert', operation='find_active_website_alert_configs' to list alert config IDs"


def _unknown_outcome_warning(operation_name: str) -> str:
    """Return the operation-specific advice for a write whose outcome is unknown after a timeout."""
    if operation_name == "create_website_alert_config":
        check = "find_active_website_alert_configs (with the website_id)"
    else:
        check = "find_website_alert_config or find_versions (with the alert id)"
    return f"The outcome of this write is unknown. Check with {check} before retrying."


def _is_unreadable(result: Any) -> bool:
    """True if a 2xx response body could not be parsed into a config dict."""
    return not isinstance(result, dict) or set(result) == {"error"}


def _write_failure(operation_name: str, e: Exception) -> Dict[str, Any]:
    """Error dict for an unexpected exception; flags an unknown outcome for writes.

    A transport error raised mid-request (reset, protocol error, read timeout) may have reached
    the server, so the caller must not blindly retry.
    """
    result: Dict[str, Any] = {"error": f"Failed to {operation_name.replace('_', ' ')}: {e!s}"}
    if (
        operation_name in _WRITE_OPERATIONS
        and isinstance(e, urllib3.exceptions.HTTPError)
        and not isinstance(e, _NOT_SENT)
    ):
        result["warning"] = _unknown_outcome_warning(operation_name)
    return result


def _raw_call(api_client, serialize_name: str, **kwargs):
    """Send a raw dict body through the SDK transport and return the HTTP response.

    The SDK's typed ``WebsiteAlertConfig`` model cannot represent everything the server
    accepts (for example the full adaptive-baseline fields), so create/update bypass the
    model and reuse the SDK's own request serializer and transport instead.

    This relies on private SDK methods (``_*_serialize`` and the ``call_api`` tuple shape).
    ``instana-client`` is pinned to an exact version in pyproject.toml, and
    ``tests/website_real_sdk/test_website_alert_sdk_contract.py`` fails if an upgrade breaks this.
    """
    param = getattr(api_client, serialize_name)(
        _request_auth=None, _content_type=None, _headers=None, _host_index=0, **kwargs
    )
    # HTTP-level timeout slightly above the wall-clock limit so the worker thread cannot outlive it for long.
    return api_client.api_client.call_api(*param, _request_timeout=float(_api_timeout() + 10)).response


async def _call(
    fn, ctx, operation_name: str, resource_type: Optional[str], tool_name: Optional[str], **kwargs
) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
    """Call the SDK; return (response, None) on success or (None, error_dict) on failure.

    Failures (timeout or HTTP status >= 400) are logged at WARNING level (status only; the
    response body can echo the payload and is logged at DEBUG). A timeout on a write
    operation additionally carries a ``warning`` saying the outcome is unknown.
    """
    response = await sdk_call_with_keepalive(
        call_sdk_fn(fn, **kwargs),
        ctx=ctx,
        operation_name=operation_name,
        resource_type=resource_type,
        tool_name=tool_name,
    )
    # sdk_call_with_keepalive returns an error dict (not a response) on timeout.
    if isinstance(response, dict):
        if operation_name in _WRITE_OPERATIONS and "timeout_seconds" in response:
            # The request runs in a worker thread and may still complete, so a retry could duplicate the write.
            logger.warning("%s timed out; the outcome of this write is unknown", operation_name)
            response = {**response, "warning": _unknown_outcome_warning(operation_name)}
        return None, response
    if response.status >= 400:
        text = decode_response(response) if response.data else _NO_ERROR_DETAILS
        text = text[:_MAX_ERROR_TEXT]
        logger.warning("%s failed with status %s", operation_name, response.status)
        logger.debug("%s error body: %s", operation_name, text)
        return None, {"error": f"API error (status {response.status}): {text}", "status_code": response.status}
    return response, None


class _InvalidChannelsError(ValueError):
    """Raised for a malformed channel field; ``field`` names the offending payload key."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def _collect_channel_ids(payload: Dict[str, Any]) -> List[str]:
    """Return the unique channel IDs referenced by ``alertChannelIds`` and ``alertChannels``.

    Raises ``_InvalidChannelsError`` (a ``ValueError`` carrying the field name) if either
    field has the wrong type.
    """
    ids: List[str] = []
    channel_ids = payload.get("alertChannelIds") or []
    if not isinstance(channel_ids, list) or not all(isinstance(c, str) for c in channel_ids):
        raise _InvalidChannelsError("alertChannelIds", "alertChannelIds must be a list of channel ID strings")
    ids.extend(channel_ids)
    by_severity = payload.get("alertChannels") or {}
    if not isinstance(by_severity, dict):
        raise _InvalidChannelsError(
            "alertChannels", 'alertChannels must be an object like {"WARNING": [ids], "CRITICAL": [ids]}'
        )
    for severity_ids in by_severity.values():
        severity_ids = severity_ids or []
        if not isinstance(severity_ids, list) or not all(isinstance(c, str) for c in severity_ids):
            raise _InvalidChannelsError("alertChannels", "alertChannels values must be lists of channel ID strings")
        ids.extend(severity_ids)
    return list(dict.fromkeys(ids))


class WebsiteAlertMCPTools(BaseInstanaClient):
    """Tools for website alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Website Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(EventSettingsApi)
    async def find_active_website_alert_configs(self,
                                                website_id: str,
                                                alert_ids: Optional[list] = None,
                                                ctx=None, api_client=None,
    resource_type: Optional[str] = None,
    tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all Website Smart Alert Configurations for a specific website.

        This tool retrieves all Smart Alert Configurations pertaining to a specific website,
        optionally filtered by specific alert IDs. Configurations are sorted by creation date
        in descending order.

        Args:
            website_id: The ID of the specific Website (required)
            alert_ids: Optional list of Smart Alert Configuration IDs to filter results
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configurations or error information
        """
        try:
            logger.debug(f"find_active_website_alert_configs called with website_id={website_id}, alert_ids={alert_ids}")

            # Validate required parameters
            if not website_id:
                return missing_param(
                    "website_id", "website_id is required for find_active_website_alert_configs",
                    "Use resource_type='configuration', operation='get_all' to list available website IDs")

            # Call the find_active_website_alert_configs_without_preload_content method from the SDK
            logger.debug(f"Calling find_active_website_alert_configs_without_preload_content with website_id={website_id}, alert_ids={alert_ids}")
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.find_active_website_alert_configs_without_preload_content,
                    website_id=website_id,
                    alert_ids=alert_ids),
                ctx=ctx,
                operation_name="find_active_website_alert_configs",
                resource_type=resource_type, tool_name=tool_name,
            )

            if (err := self.check_response_status(response, "get active website alert configs", logger)):
                return err

            return parse_alert_config_response(response, "website", website_id)

        except Exception as e:
            logger.error(f"Error in find_active_website_alert_configs: {e}", exc_info=True)
            return {"error": f"Failed to get active website alert configs: {e!s}"}

    @with_header_auth(EventSettingsApi)
    async def find_website_alert_config(self,
                                        id: str,
                                        valid_on: Optional[int] = None,
                                        ctx=None, api_client=None,
    resource_type: Optional[str] = None,
    tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Gets a specific Smart Alert Configuration for websites by ID. This may return a deleted Configuration.

        This tool retrieves a specific Smart Alert Configuration, filtered by id and valid_on timestamp.

        Args:
            id: ID of a specific Website Smart Alert Configuration to retrieve (required)
            valid_on: A Unix timestamp representing a specific time the Configuration was active. If no timestamp is provided, the latest active version will be retrieved.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"find_website_alert_config called with id={id}, valid_on={valid_on}")

            # Validate required parameters
            if not id:
                return missing_param("id", "id is required for find_website_alert_config", _ID_HINT)

            # Call the find_website_alert_config_without_preload_content method from the SDK
            # Using _without_preload_content to avoid SDK deserialization issues
            logger.debug(f"Calling find_website_alert_config_without_preload_content with id={id}, valid_on={valid_on}")
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.find_website_alert_config_without_preload_content,
                    id=id,
                    valid_on=valid_on),
                ctx=ctx,
                operation_name="find_website_alert_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            if (err := self.check_response_status(response, "get website alert config", logger)):
                return err

            return parse_single_alert_config_response(response)

        except Exception as e:
            logger.error(f"Error in find_website_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to get website alert config: {e!s}"}

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def _validate_channels(
        self, api_client, payload: Dict[str, Any], ctx, resource_type, tool_name,
        allow_unverified: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Check that every referenced alert channel exists. Returns ``(error, warning)``.

        The server accepts unknown channel IDs silently, which means alerts would never be
        delivered, so this fails closed: ``error`` is an error/elicitation dict when a channel
        is unknown or cannot be verified. With ``allow_unverified`` (used by update, where a
        config copied from ``find`` always carries channel IDs) a 403 on the channel lookup
        (missing ``canConfigureIntegrations``) is downgraded to a ``warning`` instead.
        """
        try:
            wanted = _collect_channel_ids(payload)
        except _InvalidChannelsError as e:
            return {
                "elicitation_needed": True,
                "reason": "invalid_payload",
                "api_error": [{"field": e.field, "issue": str(e)}],
                "message": f"Invalid alert payload. {e}.",
            }, None
        if not wanted:
            return None, None
        response, error = await _call(
            api_client.get_alerting_channels_without_preload_content,
            ctx, "get_alerting_channels", resource_type, tool_name, ids=wanted,
        )
        if error:
            if allow_unverified and error.get("status_code") == 403:
                logger.warning("Channel lookup denied (403); proceeding unverified")
                return None, "Alert channel IDs were not verified (missing canConfigureIntegrations permission)."
            return {
                "error": f"Could not verify alert channels, so the request was not sent. {error['error']}",
                "hint": "Alert channel lookup needs the canConfigureIntegrations permission.",
            }, None
        try:
            found = {c.get("id") for c in json.loads(decode_response(response))}
        except (json.JSONDecodeError, AttributeError, TypeError):
            return {
                "error": "Could not verify alert channels (unreadable response), so the request was not sent."
            }, None
        unknown = [cid for cid in wanted if cid not in found]
        if not unknown:
            return None, None
        return {
            "elicitation_needed": True,
            "reason": "invalid_alert_channels",
            "api_error": [
                {
                    "field": "alertChannelIds",
                    "issue": f"Unknown alert channel ID(s): {unknown}",
                    "hint": "Use manage_alert_channels with operation='get_overview' to list valid channel IDs",
                }
            ],
            "message": f"Alert channel ID(s) not found: {unknown}. Use manage_alert_channels get_overview to list valid IDs.",
        }, None

    @with_header_auth(EventSettingsApi)
    async def create_website_alert_config(self,
                                          payload: Optional[Dict[str, Any]] = None,
                                          ctx=None, api_client=None,
                                          resource_type: Optional[str] = None,
                                          tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Website Smart Alert Configuration.

        The payload is sent as-is (no SDK model validation); the server's validation messages
        are returned verbatim. ``rbacTags`` is read-only: if sent, the server ignores it and
        assigns the RBAC tags itself, so it should be omitted.

        Args:
            payload: Alert configuration (name, description, websiteId, rules, ...)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            The created configuration. If the server returns no body, ``{"success": True, "message": ...}``.
            On failure: ``{"error": ...}``, an elicitation dict (missing or invalid input, unknown
            channel IDs), or a timeout error carrying a ``warning`` that the outcome is unknown.
        """
        try:
            if not isinstance(payload, dict) or not payload:
                return missing_param("payload", "payload is required for create",
                                     "Provide the alert configuration as a JSON object.")

            channel_error, _ = await self._validate_channels(api_client, payload, ctx, resource_type, tool_name)
            if channel_error:
                return channel_error

            logger.info("Creating website alert config (websiteId=%s)", payload.get("websiteId"))
            response, error = await _call(
                lambda: _raw_call(api_client, "_create_website_alert_config_serialize", website_alert_config=payload),
                ctx, "create_website_alert_config", resource_type, tool_name,
            )
            if error:
                return error
            if response.status == 204 or not response.data:
                # A 2xx with no body means the write may have happened; do not report a parse failure,
                # because the caller would retry and create a duplicate.
                logger.info("Created website alert config (websiteId=%s); server returned no body",
                            payload.get("websiteId"))
                return {
                    "success": True,
                    "message": "Alert configuration created (the server returned no body). "
                               "Use find_active_website_alert_configs to get its id.",
                }
            result = parse_single_alert_config_response(response)
            if _is_unreadable(result):
                # The write succeeded (2xx); reporting an error would make the caller retry and duplicate it.
                logger.warning("Created website alert config (websiteId=%s) but the response was unreadable",
                               payload.get("websiteId"))
                return {
                    "success": True,
                    "message": "Alert configuration created, but the server response could not be parsed.",
                    "warning": "Use find_active_website_alert_configs to get its id; do NOT retry create.",
                }
            logger.info("Created website alert config (id=%s, websiteId=%s)",
                        result.get("id"), payload.get("websiteId"))
            return result

        except Exception as e:
            logger.error(f"Error in create_website_alert_config: {e}", exc_info=True)
            return _write_failure("create_website_alert_config", e)

    @with_header_auth(EventSettingsApi)
    async def update_website_alert_config(self,
                                          id: Optional[str] = None,
                                          payload: Optional[Dict[str, Any]] = None,
                                          ctx=None, api_client=None,
                                          resource_type: Optional[str] = None,
                                          tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Update a Website Smart Alert Configuration.

        The server requires the full configuration on update, so the caller must supply the
        complete configuration in ``payload``. It is sent as-is, except that server-managed
        fields (id, created, ``rbacTags``, ...), the legacy rule/threshold/severity fields and the
        server-computed threshold ``baseline`` are dropped so a config copied from ``find``
        can be reused. ``rbacTags`` cannot be changed through update; the server keeps the
        existing value.

        Args:
            id: ID of the alert configuration to update (required)
            payload: Complete alert configuration (required)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            The updated configuration. If the server returns no body, the stored configuration is
            fetched and returned; if that fetch fails, ``{"success": True, "message": ..., "warning": ...}``.
            On failure: ``{"error": ...}``, an elicitation dict (missing or invalid input, unknown
            channel IDs), or a timeout error carrying a ``warning`` that the outcome is unknown.
        """
        try:
            if not id:
                return missing_param("id", "id is required for update", _ID_HINT)
            if not isinstance(payload, dict) or not payload:
                return missing_param("payload", "payload is required for update",
                                     "Provide the complete alert configuration as a JSON object.")

            channel_error, channel_warning = await self._validate_channels(
                api_client, payload, ctx, resource_type, tool_name, allow_unverified=True)
            if channel_error:
                return channel_error

            drop = _SERVER_ONLY_FIELDS + _LEGACY_RULE_FIELDS
            body = _strip_baselines({k: v for k, v in payload.items() if k not in drop})
            logger.info("Updating website alert config (id=%s, websiteId=%s)", id, payload.get("websiteId"))
            response, error = await _call(
                lambda: _raw_call(api_client, "_update_website_alert_config_serialize",
                                  id=id, website_alert_config=body),
                ctx, "update_website_alert_config", resource_type, tool_name,
            )
            if error:
                return error
            logger.info("Updated website alert config (id=%s)", id)
            warnings = [channel_warning] if channel_warning else []
            if response.status == 204 or not response.data:
                # The server sometimes answers 204 with no body; return the stored config instead.
                refreshed, error = await _call(
                    api_client.find_website_alert_config_without_preload_content,
                    ctx, "find_website_alert_config", resource_type, tool_name, id=id,
                )
                if error:
                    logger.warning("Updated website alert config %s but could not re-read it: %s",
                                   id, error.get("error"))
                    warnings.append("The updated configuration could not be re-read. "
                                    "Use find_website_alert_config to verify it.")
                    return {
                        "success": True,
                        "message": f"Alert configuration '{id}' updated",
                        "warning": " ".join(warnings),
                    }
                result = parse_single_alert_config_response(refreshed)
            else:
                result = parse_single_alert_config_response(response)
            if _is_unreadable(result):
                logger.warning("Updated website alert config %s but the response was unreadable", id)
                warnings.append("The server response could not be parsed. "
                                "Use find_website_alert_config to verify the update.")
                return {
                    "success": True,
                    "message": f"Alert configuration '{id}' updated",
                    "warning": " ".join(warnings),
                }
            if warnings:
                result = {**result, "warning": " ".join(warnings)}
            return result

        except Exception as e:
            logger.error(f"Error in update_website_alert_config: {e}", exc_info=True)
            return _write_failure("update_website_alert_config", e)

    async def _lifecycle(self, api_client, sdk_method: str, past: str, id, ctx, resource_type, tool_name,
                         **extra) -> Dict[str, Any]:
        """Shared body for delete/enable/disable/restore (all answer 204 with no body).

        Args:
            api_client: The SDK ``EventSettingsApi`` client.
            sdk_method: SDK method name without the ``_without_preload_content`` suffix; also the
                operation name used in logs and timeout handling.
            past: Past-tense phrase used in the success message, e.g. ``"deleted"``.
            id: ID of the alert configuration.
            ctx: The MCP context (optional).
            resource_type: Router resource type, used only to correlate log lines.
            tool_name: Router tool name, used only to correlate log lines.
            **extra: Additional SDK arguments (``created`` for restore).

        Returns:
            ``{"success": True, "message": ...}``, or an elicitation dict when ``id`` is missing,
            or ``{"error": ...}``. A timeout error carries a ``warning`` that the outcome is unknown.
        """
        try:
            if not id:
                return missing_param("id", f"id is required for {sdk_method.split('_website')[0]}", _ID_HINT)
            logger.info("%s: id=%s %s", sdk_method, id, extra or "")
            _, error = await _call(
                getattr(api_client, f"{sdk_method}_without_preload_content"),
                ctx, sdk_method, resource_type, tool_name, id=id, **extra,
            )
            if error:
                return error
            logger.info("%s succeeded: id=%s", sdk_method, id)
            return {"success": True, "message": f"Alert configuration '{id}' {past}"}
        except Exception as e:
            logger.error(f"Error in {sdk_method}: {e}", exc_info=True)
            return _write_failure(sdk_method, e)

    @with_header_auth(EventSettingsApi)
    async def delete_website_alert_config(self, id: Optional[str] = None, ctx=None, api_client=None,
                                          resource_type: Optional[str] = None,
                                          tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Delete a Website Smart Alert Configuration (soft delete; it can be restored).

        Args:
            id: ID of the alert configuration to delete (required)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            ``{"success": True, "message": ...}``, or error / elicitation information.
            Use ``find_website_alert_config_versions`` and ``restore_website_alert_config`` to undo.
        """
        return await self._lifecycle(api_client, "delete_website_alert_config", "deleted",
                                     id, ctx, resource_type, tool_name)

    @with_header_auth(EventSettingsApi)
    async def enable_website_alert_config(self, id: Optional[str] = None, ctx=None, api_client=None,
                                          resource_type: Optional[str] = None,
                                          tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Enable a Website Smart Alert Configuration.

        Args:
            id: ID of the alert configuration to enable (required)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            ``{"success": True, "message": ...}``, or error / elicitation information.
        """
        return await self._lifecycle(api_client, "enable_website_alert_config", "enabled",
                                     id, ctx, resource_type, tool_name)

    @with_header_auth(EventSettingsApi)
    async def disable_website_alert_config(self, id: Optional[str] = None, ctx=None, api_client=None,
                                           resource_type: Optional[str] = None,
                                           tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Disable a Website Smart Alert Configuration.

        Args:
            id: ID of the alert configuration to disable (required)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            ``{"success": True, "message": ...}``, or error / elicitation information.
        """
        return await self._lifecycle(api_client, "disable_website_alert_config", "disabled",
                                     id, ctx, resource_type, tool_name)

    @with_header_auth(EventSettingsApi)
    async def restore_website_alert_config(self, id: Optional[str] = None, created: Optional[int] = None,
                                           ctx=None, api_client=None,
                                           resource_type: Optional[str] = None,
                                           tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Restore a Website Smart Alert Configuration to an earlier version.

        Args:
            id: ID of the alert configuration to restore (required)
            created: Creation timestamp (Unix ms) of the version to restore; take it from
                ``find_website_alert_config_versions`` (required)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            ``{"success": True, "message": ...}``, or error / elicitation information.
        """
        if id and created is None:
            return missing_param("created", "created is required for restore",
                                 "Use operation='find_versions' to list versions and take a 'created' timestamp")
        return await self._lifecycle(api_client, "restore_website_alert_config", f"restored to version {created}",
                                     id, ctx, resource_type, tool_name, created=created)

    @with_header_auth(EventSettingsApi)
    async def find_website_alert_config_versions(self, id: Optional[str] = None, ctx=None, api_client=None,
                                                 resource_type: Optional[str] = None,
                                                 tool_name: Optional[str] = None) -> Dict[str, Any]:
        """List all versions of a Website Smart Alert Configuration (the ``created`` values feed restore)."""
        try:
            if not id:
                return missing_param("id", "id is required for find_versions", _ID_HINT)
            response, error = await _call(
                api_client.find_website_alert_config_versions_without_preload_content,
                ctx, "find_website_alert_config_versions", resource_type, tool_name, id=id,
            )
            if error:
                return error
            versions = json.loads(decode_response(response)) if response.data else []
            if not isinstance(versions, list):
                return {"error": "Unexpected response from the versions endpoint (expected a list)."}
            return {"versions": versions, "count": len(versions)}
        except Exception as e:
            logger.error(f"Error in find_website_alert_config_versions: {e}", exc_info=True)
            return {"error": f"Failed to get website alert config versions: {e!s}"}
