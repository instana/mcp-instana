"""
Mobile App Alert MCP Tools Module

This module provides mobile app alert-specific MCP tools for Instana monitoring.
Uses the api/event-settings endpoints.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from mcp.types import ToolAnnotations
from urllib3.exceptions import (
    ConnectTimeoutError,
    NameResolutionError,
    NewConnectionError,
    SSLError,
)

from src.core.alert_config_utils import (
    parse_alert_config_response,
    parse_single_alert_config_response,
)
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
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import mobile app alert configuration API", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

_NO_ERROR_DETAILS = "No error details available (empty response body)"

# Operations that change live alerting; a timeout on these leaves the outcome unknown.
_WRITE_OPERATIONS = frozenset({
    "create_mobile_app_alert_config",
    "update_mobile_app_alert_config",
    "delete_mobile_app_alert_config",
    "enable_mobile_app_alert_config",
    "disable_mobile_app_alert_config",
    "restore_mobile_app_alert_config",
})

# Fields the server owns. They are echoed by GET but must not be sent back on update.
# `completeTagFilterExpression` is derived by the server from `mobileAppId` + `tagFilterExpression`.
_SERVER_ONLY_FIELDS = (
    "id", "created", "initialCreated", "readOnly", "displayUrl", "rbacTags", "completeTagFilterExpression",
)
# Legacy single-rule fields. GET returns them, but sending them back next to `rules`
# is rejected with 422, so they are dropped on update.
_LEGACY_RULE_FIELDS = ("rule", "threshold", "severity")

# Longest API error body returned to the caller or written to the log.
_MAX_ERROR_TEXT = 2000

# Transport failures that happen before any request bytes are sent (connect, DNS, TLS handshake).
# After any other exception on a write, the server may already have committed it.
_NOT_SENT = (NewConnectionError, NameResolutionError, ConnectTimeoutError, SSLError)

# Extra seconds the HTTP request may outlive the async deadline, so the worker thread always ends.
_HTTP_TIMEOUT_MARGIN = 5


def _request_not_sent(exc: BaseException) -> bool:
    """True if ``exc`` (or the exception it wraps) proves the request never left this host."""
    cause = exc.__cause__ or exc.__context__
    return isinstance(exc, _NOT_SENT) or isinstance(cause, _NOT_SENT)


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


def _missing_param(field: str, issue: str, hint: str) -> Dict[str, Any]:
    """Build the structured elicitation response for a missing required parameter."""
    return {
        "elicitation_needed": True,
        "reason": "missing_required_params",
        "api_error": [{"field": field, "issue": issue, "hint": hint}],
        "message": f"Missing required parameter '{field}'. {hint}",
    }


def _unknown_outcome_warning(operation_name: str) -> str:
    """Return the operation-specific advice for a write whose outcome is unknown after a timeout."""
    if operation_name == "create_mobile_app_alert_config":
        check = "find_active_mobile_app_alert_configs (with the mobile_app_id)"
    else:
        check = "find_mobile_app_alert_config or find_versions (with the alert id)"
    return f"The outcome of this write is unknown. Check with {check} before retrying."


def _raw_call(api_client, serialize_name: str, **kwargs):
    """Send a raw dict body through the SDK transport and return the HTTP response.

    The SDK's typed ``MobileAppAlertConfig`` model cannot represent everything the server
    accepts (for example the full adaptive-baseline fields), so create/update bypass the
    model and reuse the SDK's own request serializer and transport instead.

    The request carries an HTTP timeout slightly longer than the async deadline in
    ``sdk_call_with_keepalive``; without it an abandoned worker thread would keep blocking on the socket.
    """
    param = getattr(api_client, serialize_name)(
        _request_auth=None, _content_type=None, _headers=None, _host_index=0, **kwargs
    )
    return api_client.api_client.call_api(*param, _request_timeout=_api_timeout() + _HTTP_TIMEOUT_MARGIN).response


async def _call(
    fn, ctx, operation_name: str, resource_type: Optional[str], tool_name: Optional[str], **kwargs
) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
    """Call the SDK; return (response, None) on success or (None, error_dict) on failure.

    Failures (timeout or HTTP status >= 400) are logged at WARNING level. A timeout on a write
    operation additionally carries a ``warning`` saying the outcome is unknown. So does any
    exception on a write that does not prove the request was never sent (for example a connection
    reset after the request went out); other exceptions propagate to the caller.
    """
    try:
        response = await sdk_call_with_keepalive(
            call_sdk_fn(fn, **kwargs),
            ctx=ctx,
            operation_name=operation_name,
            resource_type=resource_type,
            tool_name=tool_name,
        )
    except Exception as e:
        if operation_name in _WRITE_OPERATIONS and not _request_not_sent(e):
            logger.warning("%s failed after the request may have been sent: %s", operation_name, e)
            return None, {
                "error": f"{operation_name} failed: {e!s}",
                "warning": _unknown_outcome_warning(operation_name),
            }
        raise
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
        logger.warning("%s failed with status %s: %s", operation_name, response.status, text)
        return None, {"error": f"API error (status {response.status}): {text}", "status_code": response.status}
    return response, None


def _parse_write_response(response, operation_name: str) -> Dict[str, Any]:
    """Parse the body of a successful (2xx) create/update response.

    A 2xx means the server committed the write, so an unreadable body must not be reported as a
    failure: the caller would retry and create a duplicate.
    """
    result = parse_single_alert_config_response(response)
    if isinstance(result, dict) and set(result) == {"error"}:
        logger.warning("%s succeeded but the response body could not be parsed: %s", operation_name, result["error"])
        return {
            "success": True,
            "message": "The server accepted the request but returned an unreadable body.",
            "warning": "The write was accepted but its result was not returned. Use "
                       "find_active_mobile_app_alert_configs or find_mobile_app_alert_config to check it; "
                       "do not retry the write.",
        }
    return result


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


class MobileAppAlertMCPTools(BaseInstanaClient):
    """Tools for mobile app alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Mobile App Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(EventSettingsApi)
    async def find_active_mobile_app_alert_configs(self,
                                                   mobile_app_id: str,
                                                   alert_ids: Optional[list] = None,
                                                   ctx=None, api_client=None,
                                                   resource_type: Optional[str] = None,
                                                   tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all Mobile Smart Alert Configurations for a specific mobile app.

        This tool retrieves all Smart Alert Configurations pertaining to a specific mobile app,
        optionally filtered by specific alert IDs. Configurations are sorted by creation date
        in descending order.

        Args:
            mobile_app_id: The ID of the specific Mobile Application (required)
            alert_ids: Optional list of Smart Alert Configuration IDs to filter results
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configurations or error information
        """
        try:
            logger.debug(f"find_active_mobile_app_alert_configs called with mobile_app_id={mobile_app_id}, alert_ids={alert_ids}")

            # Validate required parameters
            if not mobile_app_id:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "mobile_app_id",
                            "issue": "mobile_app_id is required for find_active_mobile_app_alert_configs",
                            "hint": "Use resource_type='configuration', operation='get_all' to list available mobile app IDs"
                        }
                    ],
                    "message": "Missing required parameter 'mobile_app_id'. Use configuration/get_all to list available mobile app IDs."
                }

            # Call the find_active_mobile_app_alert_configs_without_preload_content method from the SDK
            logger.debug(f"Calling find_active_mobile_app_alert_configs_without_preload_content with mobile_app_id={mobile_app_id}, alert_ids={alert_ids}")
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.find_active_mobile_app_alert_configs_without_preload_content,
                    mobile_app_id=mobile_app_id,
                    alert_ids=alert_ids),
                ctx=ctx,
                operation_name="find_active_mobile_app_alert_configs",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            return parse_alert_config_response(response, "mobile app", mobile_app_id)

        except Exception as e:
            logger.error(f"Error in find_active_mobile_app_alert_configs: {e}", exc_info=True)
            return {"error": f"Failed to get active mobile app alert configs: {e!s}"}

    @with_header_auth(EventSettingsApi)
    async def find_mobile_app_alert_config(self,
                                           id: str,
                                           valid_on: Optional[int] = None,
                                           ctx=None, api_client=None,
                                           resource_type: Optional[str] = None,
                                           tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Gets a specific Smart Alert Configuration for mobile apps by ID. This may return a deleted Configuration.

        This tool retrieves a specific Smart Alert Configuration, filtered by id and valid_on timestamp.

        Args:
            id: ID of a specific Mobile Smart Alert Configuration to retrieve (required)
            valid_on: A Unix timestamp representing a specific time the Configuration was active. If no timestamp is provided, the latest active version will be retrieved.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"find_mobile_app_alert_config called with id={id}, valid_on={valid_on}")

            # Validate required parameters
            if not id:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "id",
                            "issue": "id is required for find_mobile_app_alert_config",
                            "hint": "Use resource_type='alert', operation='find_active_mobile_app_alert_configs' to list available alert config IDs"
                        }
                    ],
                    "message": "Missing required parameter 'id'. Use alert/find_active_mobile_app_alert_configs to list available IDs."
                }

            # Call the find_mobile_app_alert_config_without_preload_content method from the SDK
            # Using _without_preload_content to avoid SDK deserialization issues
            logger.debug(f"Calling find_mobile_app_alert_config_without_preload_content with id={id}, valid_on={valid_on}")
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.find_mobile_app_alert_config_without_preload_content,
                    id=id,
                    valid_on=valid_on),
                ctx=ctx,
                operation_name="find_mobile_app_alert_config",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            return parse_single_alert_config_response(response)

        except Exception as e:
            logger.error(f"Error in find_mobile_app_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to get mobile app alert config: {e!s}"}

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def _attached_channel_ids(
        self, api_client, id: str, ctx, resource_type, tool_name
    ) -> frozenset:
        """Return the channel IDs already stored on alert ``id`` (empty if they cannot be read).

        Used on update so channels the alert already carries are not re-validated: a channel
        deleted since it was attached must not block an unrelated edit. On any failure the
        result is empty, which makes the caller validate every ID (fail closed).
        """
        try:
            current, error = await _call(
                api_client.find_mobile_app_alert_config_without_preload_content,
                ctx, "find_mobile_app_alert_config", resource_type, tool_name, id=id,
            )
            if error:
                return frozenset()
            return frozenset(_collect_channel_ids(json.loads(decode_response(current))))
        except Exception:
            return frozenset()

    async def _validate_channels(
        self, api_client, payload: Dict[str, Any], ctx, resource_type, tool_name,
        already_attached: frozenset = frozenset(),
    ) -> Optional[Dict[str, Any]]:
        """Fail closed if any newly referenced alert channel cannot be verified.

        The server accepts unknown channel IDs silently, which means alerts would never be
        delivered. IDs in ``already_attached`` (already stored on the alert being updated) are
        skipped. Returns None when all IDs exist (or none need checking), otherwise an
        error/elicitation dict.
        """
        try:
            wanted = [c for c in _collect_channel_ids(payload) if c not in already_attached]
        except _InvalidChannelsError as e:
            return {
                "elicitation_needed": True,
                "reason": "invalid_payload",
                "api_error": [{"field": e.field, "issue": str(e)}],
                "message": f"Invalid alert payload. {e}.",
            }
        if not wanted:
            return None
        response, error = await _call(
            api_client.get_alerting_channels_without_preload_content,
            ctx, "get_alerting_channels", resource_type, tool_name, ids=wanted,
        )
        if error:
            return {
                "error": f"Could not verify alert channels, so the request was not sent. {error['error']}",
                "hint": "Alert channel lookup needs the canConfigureIntegrations permission.",
            }
        try:
            found = {c.get("id") for c in json.loads(decode_response(response))}
        except (json.JSONDecodeError, AttributeError, TypeError):
            return {"error": "Could not verify alert channels (unreadable response), so the request was not sent."}
        unknown = [cid for cid in wanted if cid not in found]
        if not unknown:
            return None
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
        }

    @with_header_auth(EventSettingsApi)
    async def create_mobile_app_alert_config(self,
                                             payload: Optional[Dict[str, Any]] = None,
                                             ctx=None, api_client=None,
                                             resource_type: Optional[str] = None,
                                             tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Mobile App Smart Alert Configuration.

        The payload is sent as-is (no SDK model validation); the server's validation messages
        are returned verbatim.

        Args:
            payload: Alert configuration (name, description, mobileAppId, rules, ...)
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
                return _missing_param("payload", "payload is required for create",
                                      "Provide the alert configuration as a JSON object.")

            channel_error = await self._validate_channels(api_client, payload, ctx, resource_type, tool_name)
            if channel_error:
                return channel_error

            logger.info("Creating mobile app alert config (mobileAppId=%s)", payload.get("mobileAppId"))
            response, error = await _call(
                lambda: _raw_call(api_client, "_create_mobile_app_alert_config_serialize",
                                  mobile_app_alert_config=payload),
                ctx, "create_mobile_app_alert_config", resource_type, tool_name,
            )
            if error:
                return error
            if response.status == 204 or not response.data:
                # A 2xx with no body means the write may have happened; do not report a parse failure,
                # because the caller would retry and create a duplicate.
                logger.info("Created mobile app alert config (mobileAppId=%s); server returned no body",
                            payload.get("mobileAppId"))
                return {
                    "success": True,
                    "message": "Alert configuration created (the server returned no body). "
                               "Use find_active_mobile_app_alert_configs to get its id.",
                }
            result = _parse_write_response(response, "create_mobile_app_alert_config")
            logger.info("Created mobile app alert config (id=%s, mobileAppId=%s)",
                        result.get("id"), payload.get("mobileAppId"))
            return result

        except Exception as e:
            logger.error(f"Error in create_mobile_app_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to create mobile app alert config: {e!s}"}

    @with_header_auth(EventSettingsApi)
    async def update_mobile_app_alert_config(self,
                                             id: Optional[str] = None,
                                             payload: Optional[Dict[str, Any]] = None,
                                             ctx=None, api_client=None,
                                             resource_type: Optional[str] = None,
                                             tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Update a Mobile App Smart Alert Configuration.

        The server requires the full configuration on update, so the caller must supply the
        complete configuration in ``payload``. It is sent as-is, except that server-managed
        fields (id, created, completeTagFilterExpression, ...), the legacy rule/threshold/severity
        fields and the server-computed threshold ``baseline`` are dropped so a config copied from
        ``find`` can be reused.

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
                return _missing_param("id", "id is required for update",
                                      "Use resource_type='alert', operation='find_active_mobile_app_alert_configs' to list alert config IDs")
            if not isinstance(payload, dict) or not payload:
                return _missing_param("payload", "payload is required for update",
                                      "Provide the complete alert configuration as a JSON object.")

            attached = frozenset()
            try:
                has_channels = bool(_collect_channel_ids(payload))
            except _InvalidChannelsError:
                has_channels = False  # _validate_channels reports the malformed field
            if has_channels:
                attached = await self._attached_channel_ids(api_client, id, ctx, resource_type, tool_name)
            channel_error = await self._validate_channels(
                api_client, payload, ctx, resource_type, tool_name, attached)
            if channel_error:
                return channel_error

            drop = _SERVER_ONLY_FIELDS + _LEGACY_RULE_FIELDS
            body = _strip_baselines({k: v for k, v in payload.items() if k not in drop})
            logger.info("Updating mobile app alert config (id=%s, mobileAppId=%s)", id, payload.get("mobileAppId"))
            response, error = await _call(
                lambda: _raw_call(api_client, "_update_mobile_app_alert_config_serialize",
                                  id=id, mobile_app_alert_config=body),
                ctx, "update_mobile_app_alert_config", resource_type, tool_name,
            )
            if error:
                return error
            logger.info("Updated mobile app alert config (id=%s)", id)
            if response.status == 204 or not response.data:
                # The server sometimes answers 204 with no body; return the stored config instead.
                refreshed, error = await _call(
                    api_client.find_mobile_app_alert_config_without_preload_content,
                    ctx, "find_mobile_app_alert_config", resource_type, tool_name, id=id,
                )
                if error:
                    logger.warning("Updated mobile app alert config %s but could not re-read it: %s",
                                   id, error.get("error"))
                    return {
                        "success": True,
                        "message": f"Alert configuration '{id}' updated",
                        "warning": "The updated configuration could not be re-read. "
                                   "Use find_mobile_app_alert_config to verify it.",
                    }
                return parse_single_alert_config_response(refreshed)
            return _parse_write_response(response, "update_mobile_app_alert_config")

        except Exception as e:
            logger.error(f"Error in update_mobile_app_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to update mobile app alert config: {e!s}"}

    async def _lifecycle(self, api_client, sdk_method: str, verb: str, past: str, id, ctx, resource_type, tool_name,
                         **extra) -> Dict[str, Any]:
        """Shared body for delete/enable/disable/restore (all answer 204 with no body).

        Args:
            api_client: The SDK ``EventSettingsApi`` client.
            sdk_method: SDK method name without the ``_without_preload_content`` suffix; also the
                operation name used in logs and timeout handling.
            verb: Operation verb used in the missing-parameter message, e.g. ``"delete"``.
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
                return _missing_param("id", f"id is required for {verb}",
                                      "Use resource_type='alert', operation='find_active_mobile_app_alert_configs' to list alert config IDs")
            if "created" in extra and extra["created"] is None:
                return _missing_param("created", f"created is required for {verb}",
                                      "Use operation='find_versions' to list versions and take a 'created' timestamp")
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
            return {"error": f"Failed to {sdk_method.replace('_', ' ')}: {e!s}"}

    @with_header_auth(EventSettingsApi)
    async def delete_mobile_app_alert_config(self, id: Optional[str] = None, ctx=None, api_client=None,
                                             resource_type: Optional[str] = None,
                                             tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Delete a Mobile App Smart Alert Configuration (soft delete; it can be restored).

        Args:
            id: ID of the alert configuration to delete (required)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            ``{"success": True, "message": ...}``, or error / elicitation information.
            Use ``find_mobile_app_alert_config_versions`` and ``restore_mobile_app_alert_config`` to undo.
        """
        return await self._lifecycle(api_client, "delete_mobile_app_alert_config", "delete", "deleted",
                                     id, ctx, resource_type, tool_name)

    @with_header_auth(EventSettingsApi)
    async def enable_mobile_app_alert_config(self, id: Optional[str] = None, ctx=None, api_client=None,
                                             resource_type: Optional[str] = None,
                                             tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Enable a Mobile App Smart Alert Configuration.

        Args:
            id: ID of the alert configuration to enable (required)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            ``{"success": True, "message": ...}``, or error / elicitation information.
        """
        return await self._lifecycle(api_client, "enable_mobile_app_alert_config", "enable", "enabled",
                                     id, ctx, resource_type, tool_name)

    @with_header_auth(EventSettingsApi)
    async def disable_mobile_app_alert_config(self, id: Optional[str] = None, ctx=None, api_client=None,
                                              resource_type: Optional[str] = None,
                                              tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Disable a Mobile App Smart Alert Configuration.

        Args:
            id: ID of the alert configuration to disable (required)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            ``{"success": True, "message": ...}``, or error / elicitation information.
        """
        return await self._lifecycle(api_client, "disable_mobile_app_alert_config", "disable", "disabled",
                                     id, ctx, resource_type, tool_name)

    @with_header_auth(EventSettingsApi)
    async def restore_mobile_app_alert_config(self, id: Optional[str] = None, created: Optional[int] = None,
                                              ctx=None, api_client=None,
                                              resource_type: Optional[str] = None,
                                              tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Restore a Mobile App Smart Alert Configuration to an earlier version.

        Args:
            id: ID of the alert configuration to restore (required)
            created: Creation timestamp (Unix ms) of the version to restore; take it from
                ``find_mobile_app_alert_config_versions`` (required)
            ctx: The MCP context (optional)
            resource_type: Router resource type, used only to correlate log lines (optional)
            tool_name: Router tool name, used only to correlate log lines (optional)

        Returns:
            ``{"success": True, "message": ...}``, or error / elicitation information.
        """
        return await self._lifecycle(api_client, "restore_mobile_app_alert_config", "restore",
                                     f"restored to version {created}",
                                     id, ctx, resource_type, tool_name, created=created)

    @with_header_auth(EventSettingsApi)
    async def find_mobile_app_alert_config_versions(self, id: Optional[str] = None, ctx=None, api_client=None,
                                                    resource_type: Optional[str] = None,
                                                    tool_name: Optional[str] = None) -> Dict[str, Any]:
        """List all versions of a Mobile App Smart Alert Configuration (the ``created`` values feed restore)."""
        try:
            if not id:
                return _missing_param("id", "id is required for find_versions",
                                      "Use resource_type='alert', operation='find_active_mobile_app_alert_configs' to list alert config IDs")
            response, error = await _call(
                api_client.find_mobile_app_alert_config_versions_without_preload_content,
                ctx, "find_mobile_app_alert_config_versions", resource_type, tool_name, id=id,
            )
            if error:
                return error
            versions = json.loads(decode_response(response)) if response.data else []
            if not isinstance(versions, list):
                return {"error": "Unexpected response from the versions endpoint (expected a list)."}
            return {"versions": versions, "count": len(versions)}
        except Exception as e:
            logger.error(f"Error in find_mobile_app_alert_config_versions: {e}", exc_info=True)
            return {"error": f"Failed to get mobile app alert config versions: {e!s}"}
