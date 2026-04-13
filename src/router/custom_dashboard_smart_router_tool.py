"""
Custom Dashboard Smart Router Tool

This module provides a unified MCP tool that routes queries to the appropriate
custom dashboard-specific tools for Instana monitoring.
"""

import logging
from typing import Any, Dict, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)


class CustomDashboardSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router that routes queries to Custom Dashboard tools.
    The LLM agent determines the appropriate operation based on query understanding.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Custom Dashboard Smart Router MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Initialize the custom dashboard tool client
        from src.custom_dashboard.custom_dashboard_tools import CustomDashboardMCPTools

        self.dashboard_client = CustomDashboardMCPTools(read_token, base_url)

        logger.info("Custom Dashboard Smart Router initialized")

    @register_as_tool(
        title="Manage Instana Custom Dashboards",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    async def manage_custom_dashboards(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Unified Instana custom dashboard manager for CRUD operations.

        Operations: get_all, get, create, update, delete, get_shareable_users, get_shareable_api_tokens

        Parameters (params dict):
        - dashboard_id: Dashboard ID (for get, update, delete only)
        - custom_dashboard: Dashboard config (for create, update) - see model below
        - query: Search filter (for get_all)
        - page_size: Items per page (for get_all)
        - page: Page number, 0-indexed (for get_all)
        - with_total_hits: Include total count (for get_all)

        Note: get_shareable_users and get_shareable_api_tokens return ALL users/tokens globally, not for a specific dashboard

        CustomDashboard Model:
        - title: string (min 1 char) - REQUIRED
        - accessRules: array[1-64] of {accessType: "READ"|"READ_WRITE", relationType: "USER"|"API_TOKEN"|"ROLE"|"TEAM"|"GLOBAL", relatedId: string|null} - defaults to global READ_WRITE if omitted
        - widgets: array[0-128] of {id: string(max 64), type: string(min 1), config: object} - defaults to [] if omitted

        Widget Fields (all optional except id, type, config): title (string), x (int 0-11), y (int >=0), width (int 1-12), height (int >=1)

        Examples:
        get_all: operation="get_all", params={"page_size": 20, "query": "prod"}
        get: operation="get", params={"dashboard_id": "abc123"}
        create: operation="create", params={"custom_dashboard": {"title": "My Dashboard", "accessRules": [{"accessType": "READ_WRITE", "relationType": "GLOBAL"}], "widgets": []}}
        create with widget: operation="create", params={"custom_dashboard": {"title": "Metrics", "accessRules": [{"accessType": "READ_WRITE", "relationType": "GLOBAL"}], "widgets": [{"id": "w1", "type": "chart", "config": {"metric": "latency"}, "x": 0, "y": 0, "width": 6, "height": 4}]}}
        update: operation="update", params={"dashboard_id": "abc123", "custom_dashboard": {"title": "Updated", "accessRules": [{"accessType": "READ_WRITE", "relationType": "GLOBAL"}], "widgets": []}}
        delete: operation="delete", params={"dashboard_id": "abc123"}
        """
        try:
            logger.info(f"Custom Dashboard Smart Router received: operation={operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate operation
            valid_operations = [
                "get_all", "get", "create", "update", "delete",
                "get_shareable_users", "get_shareable_api_tokens"
            ]

            if operation not in valid_operations:
                return {
                    "error": f"Invalid operation '{operation}'",
                    "valid_operations": valid_operations
                }

            # Route to the dashboard client
            logger.info(f"Routing to Custom Dashboard client for operation: {operation}")

            # Pass the entire params dict - let the operation dispatcher handle parameter mapping
            result = await self.dashboard_client.execute_dashboard_operation(
                operation=operation,
                params=params,
                ctx=ctx
            )

            return {
                "operation": operation,
                "dashboard_id": params.get("dashboard_id") if params.get("dashboard_id") else None,
                "results": result
            }

        except Exception as e:
            logger.error(f"Error in custom dashboard smart router: {e}", exc_info=True)
            return {
                "error": f"Custom dashboard smart router error: {e!s}",
                "operation": operation
            }
