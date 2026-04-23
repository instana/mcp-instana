"""
Smart Router Tool for Releases Management

This module provides a unified MCP tool that routes release management queries
to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, List, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.timestamp_utils import convert_datetime_param, convert_datetime_params
from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)

# Constants for valid operations
OPERATION_GET_ALL_RELEASES = "get_all_releases"
OPERATION_GET_RELEASE = "get_release"
OPERATION_CREATE_RELEASE = "create_release"
OPERATION_UPDATE_RELEASE = "update_release"
OPERATION_DELETE_RELEASE = "delete_release"

RELEASES_VALID_OPERATIONS = [
    OPERATION_GET_ALL_RELEASES,
    OPERATION_GET_RELEASE,
    OPERATION_CREATE_RELEASE,
    OPERATION_UPDATE_RELEASE,
    OPERATION_DELETE_RELEASE
]


class ReleasesSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for releases management operations.
    Routes queries to Releases tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Smart Router Releases MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
        from src.releases.releases_tools import ReleasesMCPTools

        # Initialize the releases client
        self.releases_client = ReleasesMCPTools(read_token, base_url)

        logger.info("Smart Router Releases initialized")

    @register_as_tool(
        title="Manage Instana Releases",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
        description="""Unified releases manager for tracking deployments and analyzing release impact.

Operations: get_all_releases, get_release, create_release, update_release, delete_release

GET_ALL_RELEASES - List releases in time range with pagination and filtering
    params: from_time, to_time, name_filter, page_number, page_size
    Time params support: milliseconds (1742369820000) OR "datetime|timezone" ("19 March 2026, 2:47 PM|IST")
    name_filter: Filter releases by name (case-insensitive substring match)
    page_number: Page number (1-based, use with page_size)
    page_size: Results per page (default: 50)

GET_RELEASE - Get release by ID
    params: release_id (required)
    Returns: id, name, start, applications, services, scopes
    Use release.start with manage_applications/manage_events to analyze post-release performance/incidents

CREATE_RELEASE - Create new release
    params: name (required), start (required), applications, services
    name: Release identifier (e.g., "frontend/release-2000")
    start: Deployment timestamp - milliseconds OR "datetime|timezone"
    applications: [{"name": "app_name"}]
    services: [{"name": "service_name", "scopedTo": {...}}]

UPDATE_RELEASE - Update existing release
    params: release_id (required), name (required), start (required), applications, services
    Same format as create_release

DELETE_RELEASE - Delete release
    params: release_id (required)

Examples:
    # List all
    operation="get_all_releases"

    # List with time range
    operation="get_all_releases", params={"from_time": "19 March 2026, 2:00 PM|IST", "to_time": "19 March 2026, 5:00 PM|IST"}

    # List with name filter
    operation="get_all_releases", params={"name_filter": "frontend"}

    # List with pagination
    operation="get_all_releases", params={"page_number": 1, "page_size": 50}

    # List with all filters
    operation="get_all_releases", params={"from_time": "19 March 2026, 2:00 PM|IST", "to_time": "19 March 2026, 5:00 PM|IST", "name_filter": "release", "page_number": 1, "page_size": 20}

    # Get by ID
    operation="get_release", params={"release_id": "l1wgr3DsQkGLf8u18JiGsg"}

    # Create
    operation="create_release", params={"name": "frontend/release-2000", "start": "19 March 2026, 2:47 PM|IST", "applications": [{"name": "My App"}]}

    # Update
    operation="update_release", params={"release_id": "l1wgr3DsQkGLf8u18JiGsg", "name": "frontend/release-2001", "start": 1742349976000}

    # Delete
    operation="delete_release", params={"release_id": "l1wgr3DsQkGLf8u18JiGsg"}"""
    )
    async def manage_releases(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Unified releases manager for tracking deployments and analyzing release impact."""
        try:
            logger.debug(f"[manage_releases] Received operation: {operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate operation
            if operation not in RELEASES_VALID_OPERATIONS:
                logger.warning(f"[manage_releases] Invalid operation: {operation}")
                return {
                    "error": f"Invalid operation '{operation}'",
                    "valid_operations": RELEASES_VALID_OPERATIONS
                }

            # Route to the appropriate operation
            logger.debug(f"[manage_releases] Routing to Releases client for operation: {operation}")

            if operation == OPERATION_GET_ALL_RELEASES:
                from_time = params.get("from_time")
                to_time = params.get("to_time")
                name_filter = params.get("name_filter")
                page_number = params.get("page_number")
                page_size = params.get("page_size")

                # Convert datetime strings to timestamps for from_time and to_time
                conversion_result = convert_datetime_params(
                    {"from_time": from_time, "to_time": to_time},
                    ["from_time", "to_time"],
                    default_timezone="UTC"
                )

                if "error" in conversion_result:
                    return {
                        "error": conversion_result["error"],
                        "operation": operation
                    }

                # Update the converted values
                from_time = conversion_result["params"]["from_time"]
                to_time = conversion_result["params"]["to_time"]

                result = await self.releases_client.get_all_releases(
                    from_time=from_time,
                    to_time=to_time,
                    name_filter=name_filter,
                    page_number=page_number,
                    page_size=page_size,
                    ctx=ctx
                )

            elif operation == OPERATION_GET_RELEASE:
                release_id = params.get("release_id")

                if not release_id:
                    return {
                        "operation": operation,
                        "error": "Missing required parameter: release_id"
                    }

                result = await self.releases_client.get_release(
                    release_id=release_id,
                    ctx=ctx
                )

            elif operation == OPERATION_CREATE_RELEASE:
                name = params.get("name")
                start = params.get("start")
                applications = params.get("applications")
                services = params.get("services")

                if not name:
                    return {
                        "operation": operation,
                        "error": "Missing required parameter: name"
                    }

                if not start:
                    return {
                        "operation": operation,
                        "error": "Missing required parameter: start"
                    }

                # Convert datetime string to timestamp for start time
                conversion_result = convert_datetime_param(
                    start,
                    "start",
                    default_timezone="UTC"
                )

                if "error" in conversion_result:
                    return {
                        "error": conversion_result["error"],
                        "operation": operation
                    }

                # Update the converted value
                start = conversion_result["value"]

                result = await self.releases_client.create_release(
                    name=name,
                    start=start,
                    applications=applications,
                    services=services,
                    ctx=ctx
                )

            elif operation == OPERATION_UPDATE_RELEASE:
                release_id = params.get("release_id")
                name = params.get("name")
                start = params.get("start")
                applications = params.get("applications")
                services = params.get("services")

                if not release_id:
                    return {
                        "operation": operation,
                        "error": "Missing required parameter: release_id"
                    }

                if not name:
                    return {
                        "operation": operation,
                        "error": "Missing required parameter: name"
                    }

                if not start:
                    return {
                        "operation": operation,
                        "error": "Missing required parameter: start"
                    }

                # Convert datetime string to timestamp for start time
                conversion_result = convert_datetime_param(
                    start,
                    "start",
                    default_timezone="UTC"
                )

                if "error" in conversion_result:
                    return {
                        "error": conversion_result["error"],
                        "operation": operation
                    }

                # Update the converted value
                start = conversion_result["value"]

                result = await self.releases_client.update_release(
                    release_id=release_id,
                    name=name,
                    start=start,
                    applications=applications,
                    services=services,
                    ctx=ctx
                )

            elif operation == OPERATION_DELETE_RELEASE:
                release_id = params.get("release_id")

                if not release_id:
                    return {
                        "operation": operation,
                        "error": "Missing required parameter: release_id"
                    }

                result = await self.releases_client.delete_release(
                    release_id=release_id,
                    ctx=ctx
                )

            else:
                return {
                    "error": f"Unsupported operation: {operation}",
                    "valid_operations": RELEASES_VALID_OPERATIONS
                }

            logger.debug(f"[manage_releases] Successfully completed operation: {operation}")
            return {
                "operation": operation,
                "results": result
            }

        except Exception as e:
            logger.error(
                f"[manage_releases] Error processing operation: {operation}, "
                f"error: {e!s}",
                exc_info=True
            )
            return {
                "error": f"Releases smart router error: {e!s}",
                "operation": operation
            }
