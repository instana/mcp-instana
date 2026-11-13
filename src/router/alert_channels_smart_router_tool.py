"""
Alert Channels Smart Router Tool Module.

Provides a unified single-resource MCP tool `manage_alert_channels` to inspect
outbound notification integrations (Webhooks, Slack, Teams, Email, PagerDuty, etc.)
with automatic fail-closed secret masking.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)

OPERATION_GET_OVERVIEW = "get_overview"
OPERATION_GET = "get"

ALERT_CHANNELS_VALID_OPERATIONS = [
    OPERATION_GET_OVERVIEW,
    OPERATION_GET,
]


class AlertChannelsSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for Instana alert channels management.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Alert Channels Smart Router MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
        from src.alert_channel.alert_channels_tools import AlertChannelsMCPTools

        self.alert_channels_client = AlertChannelsMCPTools(read_token, base_url)
        logger.info("AlertChannelsSmartRouterMCPTool initialized")

    @register_as_tool(
        title="Manage Instana Alert Channels",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        description="""Unified Instana alert channels manager for inspecting outbound notification integrations (Webhooks, Slack, Teams, Email, PagerDuty, Opsgenie, ServiceNow, etc.).

Operations: get_overview, get

GET_OVERVIEW - List summary of all alert channels with filtering and pagination
    params: {ids, kind, name_filter, page, page_size}
    ids: List (or comma-separated string) of specific channel IDs to retrieve (optional)
    kind: Filter by integration type (e.g. 'WEB_HOOK', 'EMAIL', 'SLACK', 'PAGER_DUTY', 'OPS_GENIE', 'SERVICE_NOW_WEBHOOK') (optional)
    name_filter: Case-insensitive substring match on channel name (optional)
    page: 1-based page number (default: 1)
    page_size: Number of channels per page (default: 20, max: 100). Results are sorted by name, then id.
    Returns: Paginated items containing id, kind, name, properties, and rbacTags (team associations). Credentials and secrets are masked; URLs are reduced to scheme://host/***.

GET - Get detailed configuration for a specific alert channel by ID or name
    params: {id, name}
    id: Channel ID (e.g. 'chan-123')
    name: Channel name (e.g. 'Production Alerts Webhook') - resolved to ID automatically
    Returns: Complete channel configuration with all sensitive secrets and tokens securely masked.

Examples:
    # List all channels
    operation="get_overview"

    # Filter channels by type
    operation="get_overview", params={"kind": "WEB_HOOK"}

    # Search channels by name
    operation="get_overview", params={"name_filter": "Slack"}

    # Paginate overview
    operation="get_overview", params={"page": 1, "page_size": 10}

    # Get channel details by ID
    operation="get", params={"id": "chan-abc123"}

    # Get channel details by name
    operation="get", params={"name": "SRE Team Webhook"}"""
    )
    async def manage_alert_channels(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Unified Instana alert channels manager."""
        TOOL_NAME = "manage_alert_channels"

        try:
            logger.debug("[%s] Received operation: %s", TOOL_NAME, operation)
            params = params or {}

            if operation not in ALERT_CHANNELS_VALID_OPERATIONS:
                logger.warning("[%s] Invalid operation: %s", TOOL_NAME, operation)
                return {
                    "elicitation_needed": True,
                    "reason": "invalid_operation",
                    "api_error": [
                        {
                            "field": "operation",
                            "issue": f"'{operation}' is not a valid alert channels operation",
                            "expected": ALERT_CHANNELS_VALID_OPERATIONS,
                        }
                    ],
                    "message": f"Invalid operation '{operation}'. Valid operations: {ALERT_CHANNELS_VALID_OPERATIONS}",
                }

            _routing = {"resource_type": "alert_channels", "tool_name": TOOL_NAME}

            if operation == OPERATION_GET_OVERVIEW:
                return await self.alert_channels_client.get_overview(
                    ids=params.get("ids") or params.get("channel_ids") or params.get("channelIds"),
                    kind=params.get("kind"),
                    name_filter=params.get("name_filter") or params.get("nameFilter") or params.get("query"),
                    page=params.get("page") or params.get("pageNumber") or 1,
                    page_size=params.get("page_size") or params.get("pageSize") or 20,
                    ctx=ctx,
                    **_routing,
                )

            if operation == OPERATION_GET:
                channel_id = params.get("id") or params.get("channel_id") or params.get("channelId")
                name = params.get("name") or params.get("channel_name") or params.get("channelName")
                if not channel_id and not name:
                    return {
                        "elicitation_needed": True,
                        "reason": "missing_required_params",
                        "api_error": [
                            {
                                "field": "id",
                                "issue": "Either 'id' or 'name' must be provided for get operation",
                                "expected": "Valid channel ID or channel name",
                            }
                        ],
                        "message": "Missing required parameter: provide either 'id' or 'name' for operation 'get'.",
                    }

                return await self.alert_channels_client.get(
                    channel_id=channel_id,
                    name=name,
                    ctx=ctx,
                    **_routing,
                )

            return {
                "error": f"Unhandled operation '{operation}'",
                "operation": operation,
            }

        except Exception as e:
            logger.error("[%s] Unhandled router error: %s", TOOL_NAME, e, exc_info=True)
            return {
                "error": f"Alert channels smart router error: {e!s}",
                "operation": operation,
            }
