"""
Smart Router Tool for Events Monitoring

This module provides a unified MCP tool that routes events monitoring queries
to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations
from opentelemetry.trace import Status, StatusCode

from src.core.timestamp_utils import convert_datetime_params
from src.core.utils import BaseInstanaClient, register_as_tool
from src.core.validation import EventsValidator, TimeValidator
from src.observability import get_tracer

logger = logging.getLogger(__name__)

# Constants for valid operations
OPERATION_GET_EVENT = "get_event"
OPERATION_GET_KUBERNETES_INFO_EVENTS = "get_kubernetes_info_events"
OPERATION_GET_AGENT_MONITORING_EVENTS = "get_agent_monitoring_events"
OPERATION_GET_EVENTS = "get_events"
OPERATION_GET_EVENTS_BY_IDS = "get_events_by_ids"

EVENTS_VALID_OPERATIONS = [
    OPERATION_GET_EVENT,
    OPERATION_GET_KUBERNETES_INFO_EVENTS,
    OPERATION_GET_AGENT_MONITORING_EVENTS,
    OPERATION_GET_EVENTS,
    OPERATION_GET_EVENTS_BY_IDS
]

# Operations that require time parameters
TIME_REQUIRED_OPERATIONS = [
    OPERATION_GET_KUBERNETES_INFO_EVENTS,
    OPERATION_GET_AGENT_MONITORING_EVENTS,
    OPERATION_GET_EVENTS
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
PARAM_EVENT_TYPE_FILTERS = "event_type_filters"
PARAM_ENTITY_TYPE = "entity_type"
PARAM_ENTITY_NAME = "entity_name"
PARAM_ENTITY_LABEL = "entity_label"
PARAM_STATE = "state"
PARAM_PROBLEM = "problem"
PARAM_SEVERITY = "severity"
PARAM_EVENT_SPECIFICATION_ID = "event_specification_id"
PARAM_RCA = "rca"

# Default values
DEFAULT_MAX_EVENTS = 50

class EventsSmartRouterMCPTool(BaseInstanaClient):
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
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
        description="""Unified Instana events resource manager for events monitoring operations.

Operations:
    - "get_events": Get all events
    - "get_event": Get a specific event by ID
    - "get_kubernetes_info_events": Get Kubernetes info events with detailed analysis
    - "get_agent_monitoring_events": Get agent monitoring events with detailed analysis
    - "get_events_by_ids": Get multiple events by their IDs

Parameters (params dict):
- For "get_event" and "get_events_by_ids", pass flat params:
    - event_id: Event ID (required for get_event)
    - event_ids: List of event IDs or comma-separated string (required for get_events_by_ids)
- For "get_kubernetes_info_events" and "get_agent_monitoring_events", pass flat params:
    - from_time: Start timestamp - milliseconds OR datetime string (e.g., "19 March 2026, 2:47 PM|IST" or "19 March 2026, 2:47 PM")
        If timezone not specified in datetime string, defaults to UTC
    - to_time: End timestamp - milliseconds OR datetime string (e.g., "19 March 2026, 2:47 PM|IST" or "19 March 2026, 2:47 PM")
        If timezone not specified in datetime string, defaults to UTC
    - time_range: Natural language time range like "last 24 hours", "last 2 days"
    - query: Optional query string for agent monitoring events
    - max_events: Maximum number of events to process for analysis (optional, default 50)
        NOTE: This is a post-processing limit, not an API parameter
- For "get_events", pass a nested filters object:
    - filters: Dictionary containing event filters.
        - from_time: Start timestamp - milliseconds OR datetime string
        - to_time: End timestamp - milliseconds OR datetime string
        - time_range: Natural language time range like "last 24 hours", "last 2 days"
        - query: Optional query string
        - max_events: Maximum number of events to process for analysis (optional, default 50)
        - filter_event_updates: Boolean flag to filter results to only show events with state changes within timeframe (optional)
        - exclude_triggered_before: Boolean flag to exclude events triggered before the timeframe (optional)
            NOTE: This is a boolean flag, not a timestamp
        - event_type_filters: List of event type filters (optional, e.g., ["INCIDENT", "ISSUE", "CHANGE"]).
            NOTE: Allowed values: INCIDENT, ISSUE, CHANGE. Invalid values will result in an error.
        - entity_type: Affected entity type to filter by (optional)
            * Allowed values (case-insensitive): "INFRASTRUCTURE", "SERVICE", "APPLICATION", "ENDPOINT"
            * For infrastructure incidents (hosts, docker, kubernetes, etc.): Use "INFRASTRUCTURE"
            * For application incidents: Use "APPLICATION"
            * For service incidents: Use "SERVICE"
            * For endpoint incidents: Use "ENDPOINT"
        - entity_name: Affected entity name (category/type) to filter by (optional, supports partial matches)
            * Examples: "Kubernetes Pod", "Kubernetes Deployment", "Process", "IBM MQ Subscription", "IBM MQ Queue Usage", "Service", "Application", "Endpoint"
            * This represents the human-readable category/type of the entity, not the specific instance name
        - entity_label: Specific entity instance identifier to filter by (optional, supports partial matches)
            * Examples: "qotd-load/qotd-load-7fd7f4c4b8-46z7c", "recommendation-agent", "POST /pay/{id}", "All Services"
            * This is the actual name/identifier of the specific entity instance
        - state: Event state to filter by (e.g., "open", "closed", "manually closed") (optional)
        - problem: Problem description to filter events by (e.g., "CPU usage high", "High error rate", "online") (optional)
        - severity: Event severity to filter by (exact match only). (optional)
            NOTE: Allowed values (strict): -1 → change (informational events), 5 → warning, 10 → critical.
        - event_specification_id: Filter events by event specification ID (optional)
        - rca: Boolean flag to filter events by root cause analysis availability (optional)
            * Set to true to return only events where probableCause.found is true (events with RCA)
            * Set to false to return only events where probableCause.found is false or missing (events without RCA)
            * If not provided, returns all events regardless of RCA status

Args:
    operation: Operation to perform
    params: Operation-specific parameters (optional)
    ctx: MCP context (internal)

Returns:
    Dictionary with results from the appropriate tool

Examples:
    operation="get_event", params={"event_id": "1a2b3c4d5e6f"}
    operation="get_kubernetes_info_events", params={"time_range": "last 24 hours", "max_events": 50}
    operation="get_agent_monitoring_events", params={"query": "Monitoring issue", "from_time": "19 March 2026, 2:47 PM|IST", "to_time": "20 March 2026, 2:47 PM|IST", "max_events": 100}
    operation="get_events", params={"filters": {"time_range": "last 24 hours", "event_type_filters": ["INCIDENT"], "entity_type": "service", "entity_name": "payment-service", "entity_label": "payment-service-v2", "state": "open", "problem": "High error rate", "severity": 10, "max_events": 50, "filter_event_updates": True, "exclude_triggered_before": False}}
    operation="get_events_by_ids", params={"event_ids": ["1a2b3c4d5e6f", "7g8h9i0j1k2l"]}"""
    )
    async def manage_events(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Unified Instana events resource manager for events monitoring operations."""
        tracer = get_tracer()
        _span = (
            tracer.start_span(
                "tools/call manage_events",
                attributes={
                    "gen_ai.tool.name": "manage_events",
                    "mcp.method.name": "tools/call",
                    "instana.tool.operation": operation or "",
                },
            )
            if tracer else None
        )
        try:
            logger.debug(f"[manage_events] Received operation: {operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate operation
            if operation not in EVENTS_VALID_OPERATIONS:
                logger.warning(f"[manage_events] Invalid operation: {operation}")
                return {
                    "error": f"Invalid operation '{operation}'",
                    "valid_operations": EVENTS_VALID_OPERATIONS
                }

            source_params = params.get("filters", {}) if operation == OPERATION_GET_EVENTS else params

            filters = {
                PARAM_EVENT_ID: source_params.get(PARAM_EVENT_ID),
                PARAM_EVENT_IDS: source_params.get(PARAM_EVENT_IDS),
                PARAM_FROM_TIME: source_params.get(PARAM_FROM_TIME),
                PARAM_TO_TIME: source_params.get(PARAM_TO_TIME),
                PARAM_TIME_RANGE: source_params.get(PARAM_TIME_RANGE),
                PARAM_QUERY: source_params.get(PARAM_QUERY),
                PARAM_MAX_EVENTS: source_params.get(PARAM_MAX_EVENTS, DEFAULT_MAX_EVENTS),
                PARAM_FILTER_EVENT_UPDATES: source_params.get(PARAM_FILTER_EVENT_UPDATES),
                PARAM_EXCLUDE_TRIGGERED_BEFORE: source_params.get(PARAM_EXCLUDE_TRIGGERED_BEFORE),
                PARAM_EVENT_TYPE_FILTERS: source_params.get(PARAM_EVENT_TYPE_FILTERS),
                PARAM_ENTITY_TYPE: source_params.get(PARAM_ENTITY_TYPE),
                PARAM_ENTITY_NAME: source_params.get(PARAM_ENTITY_NAME),
                PARAM_ENTITY_LABEL: source_params.get(PARAM_ENTITY_LABEL),
                PARAM_STATE: source_params.get(PARAM_STATE),
                PARAM_PROBLEM: source_params.get(PARAM_PROBLEM),
                PARAM_SEVERITY: source_params.get(PARAM_SEVERITY),
                PARAM_EVENT_SPECIFICATION_ID: source_params.get(PARAM_EVENT_SPECIFICATION_ID),
                PARAM_RCA: source_params.get(PARAM_RCA),
            }

            logger.debug(
                f"[manage_events] Parameters extracted - "
                f"operation: {operation}, time_range: {filters[PARAM_TIME_RANGE]}, "
                f"from_time: {filters[PARAM_FROM_TIME]}, to_time: {filters[PARAM_TO_TIME]}, max_events: {filters[PARAM_MAX_EVENTS]}, "
                f"event_type_filters: {filters[PARAM_EVENT_TYPE_FILTERS]}, entity_type: {filters[PARAM_ENTITY_TYPE]}, entity_name: {filters[PARAM_ENTITY_NAME]}, entity_label: {filters[PARAM_ENTITY_LABEL]}, state: {filters[PARAM_STATE]}, problem: {filters[PARAM_PROBLEM]}, severity: {filters[PARAM_SEVERITY]}, rca: {filters[PARAM_RCA]}"
            )

            # Convert datetime strings to timestamps for from_time and to_time
            conversion_result = convert_datetime_params(
                {PARAM_FROM_TIME: filters[PARAM_FROM_TIME], PARAM_TO_TIME: filters[PARAM_TO_TIME]},
                [PARAM_FROM_TIME, PARAM_TO_TIME],
                default_timezone="UTC"
            )

            if "error" in conversion_result:
                return {
                    "error": conversion_result["error"],
                    "operation": operation
                }

            # Update the converted values
            from_time = conversion_result["params"][PARAM_FROM_TIME]
            to_time = conversion_result["params"][PARAM_TO_TIME]

            # Validate time-related parameters for operations that use them
            if operation in TIME_REQUIRED_OPERATIONS:
                logger.debug(f"[manage_events] Validating time parameters for operation: {operation}")

                # Validate time parameters
                time_validation = TimeValidator.validate_time_parameters(
                    from_time=from_time,
                    to_time=to_time,
                    time_range=filters[PARAM_TIME_RANGE]
                )

                if not time_validation.is_valid():
                    logger.warning(
                        f"[manage_events] Time parameter validation failed for operation: {operation}, "
                        f"errors: {time_validation.to_dict()}"
                    )
                    return {
                        "operation": operation,
                        "validation_failed": True,
                        **time_validation.to_dict()
                    }

                # Validate max_events
                max_events_error = EventsValidator.validate_max_events(filters[PARAM_MAX_EVENTS])
                if max_events_error:
                    logger.warning(
                        f"[manage_events] max_events validation failed: {max_events_error.message}, "
                        f"provided value: {filters[PARAM_MAX_EVENTS]}"
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
            logger.debug(f"[manage_events] Routing to Events client for operation: {operation}")

            if operation == OPERATION_GET_EVENT:
                result = await self.events_client.get_event(
                    event_id=filters[PARAM_EVENT_ID],
                    ctx=ctx
                )

            elif operation == OPERATION_GET_KUBERNETES_INFO_EVENTS:
                result = await self.events_client.get_kubernetes_info_events(
                    from_time=from_time,
                    to_time=to_time,
                    time_range=filters[PARAM_TIME_RANGE],
                    max_events=filters[PARAM_MAX_EVENTS],
                    ctx=ctx
                )

            elif operation == OPERATION_GET_AGENT_MONITORING_EVENTS:
                result = await self.events_client.get_agent_monitoring_events(
                    query=filters[PARAM_QUERY],
                    from_time=from_time,
                    to_time=to_time,
                    max_events=filters[PARAM_MAX_EVENTS],
                    time_range=filters[PARAM_TIME_RANGE],
                    ctx=ctx
                )

            elif operation == OPERATION_GET_EVENTS:
                event_filters = {
                    "query": filters[PARAM_QUERY],
                    "from_time": from_time,
                    "to_time": to_time,
                    "filter_event_updates": filters[PARAM_FILTER_EVENT_UPDATES],
                    "exclude_triggered_before": filters[PARAM_EXCLUDE_TRIGGERED_BEFORE],
                    "max_events": filters[PARAM_MAX_EVENTS],
                    "time_range": filters[PARAM_TIME_RANGE],
                    "event_type_filters": filters[PARAM_EVENT_TYPE_FILTERS],
                    "entity_type": filters[PARAM_ENTITY_TYPE],
                    "entity_name": filters[PARAM_ENTITY_NAME],
                    "entity_label": filters[PARAM_ENTITY_LABEL],
                    "state": filters[PARAM_STATE],
                    "problem": filters[PARAM_PROBLEM],
                    "severity": filters[PARAM_SEVERITY],
                    "event_specification_id": filters[PARAM_EVENT_SPECIFICATION_ID],
                    "rca": filters[PARAM_RCA],
                }

                result = await self.events_client.get_events(
                    filters=event_filters,
                    ctx=ctx
                )


            elif operation == OPERATION_GET_EVENTS_BY_IDS:
                result = await self.events_client.get_events_by_ids(
                    event_ids=filters[PARAM_EVENT_IDS],
                    ctx=ctx
                )

            else:
                return {
                    "error": f"Unrouted operation '{operation}'",
                    "operation": operation
                }

            logger.debug(f"[manage_events] Successfully completed operation: {operation}")
            return {
                "operation": operation,
                "results": result
            }

        except Exception as e:
            if _span:
                _span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(
                f"[manage_events] Error processing operation: {operation}, "
                f"error: {e!s}",
                exc_info=True
            )
            return {
                "error": f"Events smart router error: {e!s}",
                "operation": operation
            }
        finally:
            if _span:
                _span.end()
