"""
Custom Dashboard Smart Router Tool

This module provides a unified MCP tool that routes queries to the appropriate
custom dashboard-specific tools for Instana monitoring.
"""

import logging
from typing import Any, Dict, Optional

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
        ctx=None
    ) -> Dict[str, Any]:
        """
        Unified Instana custom dashboard manager for CRUD operations.

        Operations:
        - "get_all": Get all custom dashboards
        - "get": Get a specific dashboard by ID
        - "create": Create a new custom dashboard
        - "update": Update an existing custom dashboard
        - "delete": Delete a custom dashboard
        - "get_shareable_users": Get shareable users for a dashboard
        - "get_shareable_api_tokens": Get shareable API tokens for a dashboard

        Parameters (params dict):
        - dashboard_id: Dashboard ID (required for get, update, delete, get_shareable_users, get_shareable_api_tokens)
        - custom_dashboard: Dashboard configuration payload (required for create, update)

        Args:
            operation: Operation to perform
            params: Operation-specific parameters (optional)
            ctx: MCP context (internal)

        Returns:
            Dictionary with results from the appropriate tool

        Examples:
            # Get all dashboards
            operation="get_all"

            # Get specific dashboard
            operation="get", params={"dashboard_id": "abc123"}

            # Create dashboard
            operation="create", params={"custom_dashboard": {"title": "My Dashboard", "widgets": []}}

            # Update dashboard
            operation="update", params={"dashboard_id": "abc123", "custom_dashboard": {"title": "Updated Dashboard"}}

            # Delete dashboard
            operation="delete", params={"dashboard_id": "abc123"}

            # Get shareable users
            operation="get_shareable_users", params={"dashboard_id": "abc123"}

            # Get shareable API tokens
            operation="get_shareable_api_tokens", params={"dashboard_id": "abc123"}
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

            # Extract parameters
            dashboard_id = params.get("dashboard_id")
            custom_dashboard = params.get("custom_dashboard")

            # Route to the dashboard client
            logger.info(f"Routing to Custom Dashboard client for operation: {operation}")

            result = await self.dashboard_client.execute_dashboard_operation(
                operation=operation,
                dashboard_id=dashboard_id,
                custom_dashboard=custom_dashboard,
                ctx=ctx
            )

            return {
                "operation": operation,
                "dashboard_id": dashboard_id if dashboard_id else None,
                "results": result
            }

        except Exception as e:
            logger.error(f"Error in custom dashboard smart router: {e}", exc_info=True)
            return {
                "error": f"Custom dashboard smart router error: {e!s}",
                "operation": operation
            }
