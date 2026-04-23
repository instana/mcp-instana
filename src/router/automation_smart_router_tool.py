"""
Automation Smart Router Tool

This module provides a unified MCP tool that routes queries to the appropriate
Automation-specific tools for Instana monitoring.
"""
import logging
from typing import Any, Dict, Optional, Union

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.timestamp_utils import convert_datetime_param
from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)

# Resource type constants
RESOURCE_TYPE_CATALOG= "catalog"
RESOURCE_TYPE_HISTORY = "history"

# Valid resource types
VALID_RESOURCE_TYPES = [
    RESOURCE_TYPE_CATALOG,
    RESOURCE_TYPE_HISTORY
]

# Catalog operation constants
CATALOG_OP_GET_ACTIONS = "get_actions"
CATALOG_OP_GET_ACTION_DETAILS = "get_action_details"
CATALOG_OP_GET_ACTION_MATCHES = "get_action_matches"
CATALOG_OP_GET_ACTION_MATCHES_BY_ID = "get_action_matches_by_id_and_time_window"
CATALOG_OP_GET_ACTION_TYPES = "get_action_types"
CATALOG_OP_GET_ACTION_TAGS = "get_action_tags"

# Valid catalog operations
CATALOG_VALID_OPERATIONS = [
    CATALOG_OP_GET_ACTIONS,
    CATALOG_OP_GET_ACTION_DETAILS,
    CATALOG_OP_GET_ACTION_MATCHES,
    CATALOG_OP_GET_ACTION_MATCHES_BY_ID,
    CATALOG_OP_GET_ACTION_TYPES,
    CATALOG_OP_GET_ACTION_TAGS,
]

# History operation constants (read-only operations only)
HISTORY_OP_LIST = "list"
HISTORY_OP_GET_DETAILS = "get_details"

# Valid history operations
HISTORY_VALID_OPERATIONS = [
    HISTORY_OP_LIST,
    HISTORY_OP_GET_DETAILS,
]

# Parameter name constants
PARAM_ACTION_ID = "action_id"
PARAM_PAYLOAD = "payload"
PARAM_TARGET_SNAPSHOT_ID = "target_snapshot_id"
PARAM_APPLICATION_ID = "application_id"
PARAM_SNAPSHOT_ID = "snapshot_id"
PARAM_ACTION_INSTANCE_ID = "action_instance_id"
PARAM_WINDOW_SIZE = "window_size"
PARAM_TO = "to"
PARAM_FROM_TIME = "from_time"
PARAM_TO_TIME = "to_time"
PARAM_PAGE = "page"
PARAM_PAGE_SIZE = "page_size"
PARAM_EVENT_ID = "event_id"
PARAM_EVENT_SPECIFICATION_ID = "event_specification_id"
PARAM_SEARCH = "search"
PARAM_TYPES = "types"
PARAM_ACTION_STATUSES = "action_statuses"
PARAM_ORDER_BY = "order_by"
PARAM_ORDER_DIRECTION = "order_direction"

class AutomationSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for Instana Automation operations.
    Routes queries to Action Catalog and Action History tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Automation Smart Router MCP tool."""

        super().__init__(read_token=read_token, base_url=base_url)

        # Initialize the automation tool clients
        from src.automation.action_catalog import ActionCatalogMCPTools
        from src.automation.action_history import ActionHistoryMCPTools

        self.action_catalog_client = ActionCatalogMCPTools(read_token, base_url)
        self.action_history_client = ActionHistoryMCPTools(read_token, base_url)

        logger.info("[AutomationSmartRouter.__init__] Smart Router initialized with Automation tools")

    @register_as_tool(
        title="Manage Instana Automation Actions",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        description="""Unified Instana automation action manager for catalog and execution history.

Resource Types:
- "catalog": Browse and search automation actions
- "history": View action execution history

CATALOG (resource_type="catalog"):
    operations: get_actions, get_action_details, get_action_matches, get_action_matches_by_id_and_time_window, get_action_types, get_action_tags

    List all actions:
    operation="get_actions"

    Get action details:
    operation="get_action_details", params={"action_id": "action-uuid"}

    Search for matching actions:
    operation="get_action_matches"
    params:
        - payload (required): dict with "name" and/or "description" fields
        - target_snapshot_id (optional): snapshot ID to filter results
    Example: params={"payload": {"name": "CPU spends significant time waiting for input/output", "description": "Checks whether the system spends significant time waiting for input/output."}, "target_snapshot_id": "snapshot-id"}

    Get action matches by ID and time window:
    operation="get_action_matches_by_id_and_time_window"
    params:
        - application_id (optional): application ID (either this or snapshot_id required)
        - snapshot_id (optional): snapshot ID (either this or application_id required)
        - to (optional): timestamp - milliseconds OR datetime string (e.g., "19 March 2026, 2:47 PM|IST")
            If timezone not specified, defaults to UTC
        - window_size (optional): time window in milliseconds
    Example: params={"application_id": "app-123", "snapshot_id": "snap-456", "to": "19 March 2026, 2:47 PM|IST", "window_size": 3600000}

    Get action types:
    operation="get_action_types"

    Get action tags:
    operation="get_action_tags"

HISTORY (resource_type="history")
    operations: list, get_details

    List action instances:
    operation="list"
    params (all optional):
        - window_size: time window in milliseconds
        - to: timestamp - milliseconds OR datetime string (e.g., "19 March 2026, 2:47 PM|IST")
            If timezone not specified, defaults to UTC
        - page: page number
        - page_size: items per page
        - target_snapshot_id: filter by snapshot ID
        - event_id: filter by event ID
        - event_specification_id: filter by event specification ID
        - search: search text
        - types: list of action types
        - action_statuses: list of statuses (e.g., ["SUCCESS", "FAILED"])
        - order_by: column name for sorting
        - order_direction: "ASC" or "DESC"
    Example: params={"window_size": 3600000, "to": 1234567890000, "page": 1, "page_size": 50, "target_snapshot_id": "snapshot-id", "event_id": "event-id", "event_specification_id": "spec-id", "search": "search text", "types": ["type1", "type2"], "action_statuses": ["SUCCESS", "FAILED"], "order_by": "column_name", "order_direction": "ASC"}

    Get action instance details:
    operation="get_details"
    params:
        - action_instance_id (required): instance UUID
        - window_size (optional): time window in milliseconds (default: 10 minutes)
        - to (optional): timestamp - milliseconds OR datetime string (e.g., "19 March 2026, 2:47 PM|IST")
            If timezone not specified, defaults to UTC
    Example: params={"action_instance_id": "instance-uuid", "window_size": 600000, "to": "19 March 2026, 2:47 PM|IST"}

Args:
    resource_type: "catalog" or "history"
    operation: Specific operation for the resource type
    params: Operation-specific parameters (optional)
    ctx: MCP context (internal)

Returns:
    Dictionary with results from the appropriate tool

Examples:
    resource_type="catalog", operation="get_actions"
    resource_type="catalog", operation="get_action_matches", params={"payload": {"name": "CPU", "description": "monitoring"}}
    resource_type="catalog", operation="get_action_matches_by_id_and_time_window", params={"application_id": "app-123", "to": "19 March 2026, 2:47 PM|IST", "window_size": 3600000}
    resource_type="history", operation="list", params={"window_size": 3600000, "to": 1234567890000, "page_size": 20}
    resource_type="history", operation="get_details", params={"action_instance_id": "instance-uuid", "to": "19 March 2026, 2:47 PM|IST"}"""
    )
    async def manage_automation(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Unified Instana automation action manager for catalog and execution history."""
        try:
            logger.info(f"Received: resource_type={resource_type}, operation={operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate resource_type
            if resource_type not in VALID_RESOURCE_TYPES:
                logger.warning(f"Invalid resource_type: {resource_type}")
                return {
                    "error": f"Invalid resource_type '{resource_type}'.",
                    "valid_resource_types": VALID_RESOURCE_TYPES,
                    "suggestion": f"Choose '{RESOURCE_TYPE_CATALOG}' for browsing actions or '{RESOURCE_TYPE_HISTORY}' for execution history"
                }

            # Route to the appropriate resource handler
            if resource_type == RESOURCE_TYPE_CATALOG:
                return await self._handle_catalog_operation(operation, params, ctx)
            elif resource_type == RESOURCE_TYPE_HISTORY:
                return await self._handle_history(operation, params, ctx)
            else:
                logger.error(f"Unsupported resource_type: {resource_type}")
                return {
                    "error": f"Unsupported resource_type: {resource_type}",
                    "supported_types": VALID_RESOURCE_TYPES
                }

        except Exception as e:
            logger.error(f"Error in smart router: {e}", exc_info=True)
            return {
                "error": f"Smart router error: {e!s}",
                "resource_type": resource_type,
                "operation": operation
            }

    async def _handle_catalog_operation(self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle automation action catalog operations."""
        logger.debug(f"Handling catalog operation: {operation} with params: {params}")

        if operation not in CATALOG_VALID_OPERATIONS:
            logger.warning(f"Invalid catalog operation: {operation}")
            return {
                "error": f"Invalid catalog operation '{operation}'.",
                "valid_operations": CATALOG_VALID_OPERATIONS
            }

        try:
            # Route to the appropriate catalog operation handler
            if operation == CATALOG_OP_GET_ACTIONS:
                logger.info("Routing to get_actions")
                result = await self.action_catalog_client.get_actions(ctx=ctx)
                return {
                    "resource_type": RESOURCE_TYPE_CATALOG,
                    "operation": operation,
                    "results": result
                }

            elif operation == CATALOG_OP_GET_ACTION_DETAILS:
                action_id = params.get(PARAM_ACTION_ID)

                if not action_id:
                    logger.warning(f"Missing required parameter: {PARAM_ACTION_ID}")
                    return {
                        "error": f"Missing required parameter: '{PARAM_ACTION_ID}'",
                        "resource_type": RESOURCE_TYPE_CATALOG,
                        "operation": operation
                    }
                logger.info(f"Routing to get_action_details with action_id: {action_id}")
                result = await self.action_catalog_client.get_action_details(
                    action_id=action_id,
                    ctx=ctx
                )
                return {
                    "resource_type": RESOURCE_TYPE_CATALOG,
                    "operation": operation,
                    "action_id": action_id,
                    "results": result
                }

            elif operation == CATALOG_OP_GET_ACTION_MATCHES:
                payload = params.get(PARAM_PAYLOAD)
                target_snapshot_id = params.get(PARAM_TARGET_SNAPSHOT_ID)

                if not payload:
                    logger.warning(f"Missing required parameter: {PARAM_PAYLOAD}")
                    return {
                        "error": f"Missing required parameter: '{PARAM_PAYLOAD}'",
                        "resource_type": RESOURCE_TYPE_CATALOG,
                        "operation": operation,
                        "example": {
                            "payload": {
                                "name": "Action name or search term",
                                "description": "Optional description"
                            }
                        }
                    }
                logger.info(f"Routing to get_action_matches with payload: {payload}")
                result = await self.action_catalog_client.get_action_matches(
                    payload=payload,
                    target_snapshot_id=target_snapshot_id,
                    ctx=ctx
                )

                return {
                    "resource_type": RESOURCE_TYPE_CATALOG,
                    "operation": operation,
                    "target_snapshot_id": target_snapshot_id,
                    "results": result
                }

            elif operation == CATALOG_OP_GET_ACTION_MATCHES_BY_ID:
                application_id = params.get(PARAM_APPLICATION_ID)
                snapshot_id = params.get(PARAM_SNAPSHOT_ID)
                to = params.get(PARAM_TO)
                window_size = params.get(PARAM_WINDOW_SIZE)

                # Convert datetime string to timestamp for 'to' if provided
                conversion_result = convert_datetime_param(
                    to,
                    PARAM_TO,
                    default_timezone="UTC"
                )

                if "error" in conversion_result:
                    return {
                        "error": conversion_result["error"],
                        "resource_type": RESOURCE_TYPE_CATALOG,
                        "operation": operation
                    }

                # Update the converted value
                to = conversion_result["value"]

                # Validate that at least one ID is provided
                if not application_id and not snapshot_id:
                    logger.warning(f"[_handle_catalog_operation] Missing required parameter: either {PARAM_APPLICATION_ID} or {PARAM_SNAPSHOT_ID}")
                    return {
                        "error": f"Either '{PARAM_APPLICATION_ID}' or '{PARAM_SNAPSHOT_ID}' must be provided",
                        "resource_type": RESOURCE_TYPE_CATALOG,
                        "operation": operation,
                        "example": {
                            "application_id": "app-123",
                            "window_size": 3600000
                        }
                    }

                logger.info(f"[_handle_catalog_operation] Routing to get_action_matches_by_id_and_time_window with application_id={application_id}, snapshot_id={snapshot_id}")
                result = await self.action_catalog_client.get_action_matches_by_id_and_time_window(
                    application_id=application_id,
                    snapshot_id=snapshot_id,
                    to=to,
                    window_size=window_size,
                    ctx=ctx
                )

                return {
                    "resource_type": RESOURCE_TYPE_CATALOG,
                    "operation": operation,
                    "filters": {
                        "application_id": application_id,
                        "snapshot_id": snapshot_id,
                        "to": to,
                        "window_size": window_size
                    },
                    "results": result
                }

            elif operation == CATALOG_OP_GET_ACTION_TYPES:
                logger.info("Routing to get_action_types")

                result = await self.action_catalog_client.get_action_types(ctx=ctx)
                return {
                    "resource_type": RESOURCE_TYPE_CATALOG,
                    "operation": operation,
                    "results": result
                }

            elif operation == CATALOG_OP_GET_ACTION_TAGS:
                logger.info("Routing to get_action_tags")

                result = await self.action_catalog_client.get_action_tags(ctx=ctx)
                return {
                    "resource_type": RESOURCE_TYPE_CATALOG,
                    "operation": operation,
                    "results": result
                }
            else:
                logger.error(f"Unhandled operation: {operation}")
                return {
                    "error": f"Unhandled catalog operation: {operation}",
                    "valid_operations": CATALOG_VALID_OPERATIONS
                }
        except Exception as e:
            logger.error(f"Error handling catalog operation '{operation}': {e}", exc_info=True)
            return {
                "error": f"Catalog operation error: {e!s}",
                "resource_type": RESOURCE_TYPE_CATALOG,
                "operation": operation
            }

    async def _handle_history(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle automation action history operations."""
        logger.debug(f"[_handle_history] Operation: {operation}, params: {params}")

        if operation not in HISTORY_VALID_OPERATIONS:
            logger.warning(f"[_handle_history] Invalid operation: {operation}")
            return {
                    "error": f"Invalid operation '{operation}' for history",
                    "valid_operations": HISTORY_VALID_OPERATIONS
                }
        try:
            # Route to specific history operation
            if operation == HISTORY_OP_LIST:
                # Extract all list parameters
                window_size = params.get(PARAM_WINDOW_SIZE)
                to = params.get(PARAM_TO)

                # Convert datetime string to timestamp for 'to' if provided
                conversion_result = convert_datetime_param(
                    to,
                    PARAM_TO,
                    default_timezone="UTC"
                )

                if "error" in conversion_result:
                    return {
                        "error": conversion_result["error"],
                        "resource_type": RESOURCE_TYPE_HISTORY,
                        "operation": operation
                    }

                # Update the converted value
                to = conversion_result["value"]

                page = params.get(PARAM_PAGE)
                page_size = params.get(PARAM_PAGE_SIZE)
                target_snapshot_id = params.get(PARAM_TARGET_SNAPSHOT_ID)
                event_id = params.get(PARAM_EVENT_ID)
                event_specification_id = params.get(PARAM_EVENT_SPECIFICATION_ID)
                search = params.get(PARAM_SEARCH)
                types = params.get(PARAM_TYPES)
                action_statuses = params.get(PARAM_ACTION_STATUSES)
                order_by = params.get(PARAM_ORDER_BY)
                order_direction = params.get(PARAM_ORDER_DIRECTION)
                logger.info("Routing to list_action_instances with filters")

                result = await self.action_history_client.list_action_instances(
                    window_size=window_size,
                    to=to,
                    page=page,
                    page_size=page_size,
                    target_snapshot_id=target_snapshot_id,
                    event_id=event_id,
                    event_specification_id=event_specification_id,
                    search=search,
                    types=types,
                    action_statuses=action_statuses,
                    order_by=order_by,
                    order_direction=order_direction,
                    ctx=ctx
                )

                return {
                    "resource_type": RESOURCE_TYPE_HISTORY,
                    "operation": operation,
                    "filters": {
                        "window_size": window_size,
                        "page": page,
                        "page_size": page_size
                    },
                    "results": result
                }

            elif operation == HISTORY_OP_GET_DETAILS:
                action_instance_id = params.get(PARAM_ACTION_INSTANCE_ID)
                window_size = params.get(PARAM_WINDOW_SIZE)
                to = params.get(PARAM_TO)

                # Convert datetime string to timestamp for 'to' if provided
                conversion_result = convert_datetime_param(
                    to,
                    PARAM_TO,
                    default_timezone="UTC"
                )

                if "error" in conversion_result:
                    return {
                        "error": conversion_result["error"],
                        "resource_type": RESOURCE_TYPE_HISTORY,
                        "operation": operation
                    }

                # Update the converted value
                to = conversion_result["value"]

                if not action_instance_id:
                    logger.warning(f"[_handle_history] Missing required parameter: {PARAM_ACTION_INSTANCE_ID}")
                    return {
                        "error": f"Missing required parameter: '{PARAM_ACTION_INSTANCE_ID}'",
                        "resource_type": RESOURCE_TYPE_HISTORY,
                        "operation": operation
                    }

                logger.info(f"Routing to get_action_instance_details with instance_id: {action_instance_id}")
                result = await self.action_history_client.get_action_instance_details(
                    action_instance_id=action_instance_id,
                    window_size=window_size,
                    to=to,
                    ctx=ctx
                )

                return {
                    "resource_type": RESOURCE_TYPE_HISTORY,
                    "operation": operation,
                    "action_instance_id": action_instance_id,
                    "results": result
                }

            else:
                logger.error(f"Unhandled operation: {operation}")
                return {
                    "error": f"Unhandled history operation: {operation}",
                    "valid_operations": HISTORY_VALID_OPERATIONS
                }

        except Exception as e:
            logger.error(f"Error handling history operation '{operation}': {e}", exc_info=True)
            return {
                "error": f"History operation error: {e!s}",
                "resource_type": RESOURCE_TYPE_HISTORY,
                "operation": operation
            }
