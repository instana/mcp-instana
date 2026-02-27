"""
Smart Router Tool for Events Monitoring

This module provides a unified MCP tool that routes events monitoring queries
to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool
from src.core.validation import EventsValidator, TimeValidator

logger = logging.getLogger(__name__)

# Constants for valid operations
OPERATION_GET_EVENT = "get_event"
OPERATION_GET_KUBERNETES_INFO_EVENTS = "get_kubernetes_info_events"
OPERATION_GET_AGENT_MONITORING_EVENTS = "get_agent_monitoring_events"
OPERATION_GET_ISSUES = "get_issues"
OPERATION_GET_INCIDENTS = "get_incidents"
OPERATION_GET_CHANGES = "get_changes"
OPERATION_GET_EVENTS_BY_IDS = "get_events_by_ids"

EVENTS_VALID_OPERATIONS = [
    OPERATION_GET_EVENT,
    OPERATION_GET_KUBERNETES_INFO_EVENTS,
    OPERATION_GET_AGENT_MONITORING_EVENTS,
    OPERATION_GET_ISSUES,
    OPERATION_GET_INCIDENTS,
    OPERATION_GET_CHANGES,
    OPERATION_GET_EVENTS_BY_IDS
]

# Operations that require time parameters
TIME_REQUIRED_OPERATIONS = [
    OPERATION_GET_KUBERNETES_INFO_EVENTS,
    OPERATION_GET_AGENT_MONITORING_EVENTS,
    OPERATION_GET_ISSUES,
    OPERATION_GET_INCIDENTS,
    OPERATION_GET_CHANGES
]

# Parameter name constants
PARAM_EVENT_ID = "event_id"
PARAM_EVENT_IDS = "event_ids"
PARAM_FROM_TIME = "from_time"
PARAM_TO_TIME = "to_time"
PARAM_TIME_RANGE = "time_range"
PARAM_QUERY = "query"
PARAM_MAX_EVENTS = "max_events"
PARAM_FILTER_EVENT_UPDATES = "filter_event_updates"
PARAM_EXCLUDE_TRIGGERED_BEFORE = "exclude_triggered_before"

# Default values
DEFAULT_MAX_EVENTS = 50

class SmartRouterEventsMCPTool(BaseInstanaClient):
    """
    Smart router for events monitoring operations.
    Routes queries to Events tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Smart Router Events MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
        from src.event.events_tools import AgentMonitoringEventsMCPTools

        # Initialize the events client
        self.events_client = AgentMonitoringEventsMCPTools(read_token, base_url)

        logger.info("Smart Router Events initialized")

    @register_as_tool(
        title="Manage Instana Events Resources",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    async def manage_events_resources(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        Unified Instana events resource manager for events monitoring operations.

        Operations:
        - "get_event": Get a specific event by ID
        - "get_kubernetes_info_events": Get Kubernetes info events with detailed analysis
        - "get_agent_monitoring_events": Get agent monitoring events with detailed analysis
        - "get_issues": Get issue events
        - "get_incidents": Get incident events
        - "get_changes": Get change events
        - "get_events_by_ids": Get multiple events by their IDs

        Parameters (params dict):
        - event_id: Event ID (required for get_event)
        - event_ids: List of event IDs or comma-separated string (required for get_events_by_ids)
        - from_time: Start timestamp in milliseconds since epoch (optional)
        - to_time: End timestamp in milliseconds since epoch (optional)
        - time_range: Natural language time range like "last 24 hours", "last 2 days"
        - max_events: Maximum number of events to process for analysis (optional, default 50)
            NOTE: This is a post-processing limit, not an API parameter
        - filter_event_updates: Boolean flag to filter results to only show events with state changes within timeframe (optional)
        - exclude_triggered_before: Boolean flag to exclude events triggered before the timeframe (optional)
            NOTE: This is a boolean flag, not a timestamp

        Args:
            operation: Operation to perform
            params: Operation-specific parameters (optional)
            ctx: MCP context (internal)

        Returns:
            Dictionary with results from the appropriate tool

        Examples:
            # Get a specific event
            operation="get_event", params={"event_id": "1a2b3c4d5e6f"}

            # Get Kubernetes events from last 24 hours
            operation="get_kubernetes_info_events", params={"time_range": "last 24 hours"}

            # Get agent monitoring events with filtering
            operation="get_agent_monitoring_events", params={
                "time_range": "last 2 days",
                "max_events": 100,
                "filter_event_updates": True
            }

            # Get issue events excluding those triggered before timeframe
            operation="get_issues", params={
                "time_range": "last week",
                "exclude_triggered_before": True
            }

            # Get incident events with specific timestamps
            operation="get_incidents", params={
                "from_time": 1234567890000,
                "to_time": 1234567900000,
                "max_events": 25
            }

            # Get change events
            operation="get_changes", params={"time_range": "last 24 hours"}

            # Get multiple events by IDs
            operation="get_events_by_ids", params={"event_ids": ["1a2b3c4d5e6f", "7g8h9i0j1k2l"]}
        """
        try:
            logger.debug(f"[manage_events_resources] Received operation: {operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate operation
            if operation not in EVENTS_VALID_OPERATIONS:
                logger.warning(f"[manage_events_resources] Invalid operation: {operation}")
                return {
                    "error": f"Invalid operation '{operation}'",
                    "valid_operations": EVENTS_VALID_OPERATIONS
                }

            # Extract common parameters using constants
            event_id = params.get(PARAM_EVENT_ID)
            event_ids = params.get(PARAM_EVENT_IDS)
            from_time = params.get(PARAM_FROM_TIME)
            to_time = params.get(PARAM_TO_TIME)
            time_range = params.get(PARAM_TIME_RANGE)
            query = params.get(PARAM_QUERY)
            max_events = params.get(PARAM_MAX_EVENTS, DEFAULT_MAX_EVENTS)
            filter_event_updates = params.get(PARAM_FILTER_EVENT_UPDATES)
            exclude_triggered_before = params.get(PARAM_EXCLUDE_TRIGGERED_BEFORE)

            logger.debug(
                f"[manage_events_resources] Parameters extracted - "
                f"operation: {operation}, time_range: {time_range}, "
                f"from_time: {from_time}, to_time: {to_time}, max_events: {max_events}"
            )

            # Validate time-related parameters for operations that use them
            if operation in TIME_REQUIRED_OPERATIONS:
                logger.debug(f"[manage_events_resources] Validating time parameters for operation: {operation}")

                # Validate time parameters
                time_validation = TimeValidator.validate_time_parameters(
                    from_time=from_time,
                    to_time=to_time,
                    time_range=time_range
                )

                if not time_validation.is_valid():
                    logger.warning(
                        f"[manage_events_resources] Time parameter validation failed for operation: {operation}, "
                        f"errors: {time_validation.to_dict()}"
                    )
                    return {
                        "operation": operation,
                        "validation_failed": True,
                        **time_validation.to_dict()
                    }

                # Validate max_events
                max_events_error = EventsValidator.validate_max_events(max_events)
                if max_events_error:
                    logger.warning(
                        f"[manage_events_resources] max_events validation failed: {max_events_error.message}, "
                        f"provided value: {max_events}"
                    )
                    return {
                        "operation": operation,
                        "validation_failed": True,
                        "valid": False,
                        "error_count": 1,
                        "errors": [max_events_error.to_dict()],
                        "message": "Parameter validation failed. Please correct the following fields and try again."
                    }

            # Route to the events client
            logger.debug(f"[manage_events_resources] Routing to Events client for operation: {operation}")

            if operation == OPERATION_GET_EVENT:
                result = await self.events_client.get_event(
                    event_id=event_id,
                    ctx=ctx
                )

            elif operation == OPERATION_GET_KUBERNETES_INFO_EVENTS:
                result = await self.events_client.get_kubernetes_info_events(
                    from_time=from_time,
                    to_time=to_time,
                    time_range=time_range,
                    max_events=max_events,
                    ctx=ctx
                )

            elif operation == OPERATION_GET_AGENT_MONITORING_EVENTS:
                result = await self.events_client.get_agent_monitoring_events(
                    query=query,
                    from_time=from_time,
                    to_time=to_time,
                    max_events=max_events,
                    time_range=time_range,
                    ctx=ctx
                )

            elif operation == OPERATION_GET_ISSUES:
                result = await self.events_client.get_issues(
                    query=query,
                    from_time=from_time,
                    to_time=to_time,
                    filter_event_updates=filter_event_updates,
                    exclude_triggered_before=exclude_triggered_before,
                    max_events=max_events,
                    time_range=time_range,
                    ctx=ctx
                )

            elif operation == OPERATION_GET_INCIDENTS:
                result = await self.events_client.get_incidents(
                    query=query,
                    from_time=from_time,
                    to_time=to_time,
                    filter_event_updates=filter_event_updates,
                    exclude_triggered_before=exclude_triggered_before,
                    max_events=max_events,
                    time_range=time_range,
                    ctx=ctx
                )

            elif operation == OPERATION_GET_CHANGES:
                result = await self.events_client.get_changes(
                    query=query,
                    from_time=from_time,
                    to_time=to_time,
                    filter_event_updates=filter_event_updates,
                    exclude_triggered_before=exclude_triggered_before,
                    max_events=max_events,
                    time_range=time_range,
                    ctx=ctx
                )

            elif operation == OPERATION_GET_EVENTS_BY_IDS:
                result = await self.events_client.get_events_by_ids(
                    event_ids=event_ids,
                    ctx=ctx
                )

            logger.debug(f"[manage_events_resources] Successfully completed operation: {operation}")
            return {
                "operation": operation,
                "results": result
            }

        except Exception as e:
            logger.error(
                f"[manage_events_resources] Error processing operation: {operation}, "
                f"error: {e!s}",
                exc_info=True
            )
            return {
                "error": f"Events smart router error: {e!s}",
                "operation": operation
            }
