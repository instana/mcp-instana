"""
Smart Router Tool for Events Monitoring

This module provides a unified MCP tool that routes events monitoring queries
to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.timestamp_utils import convert_datetime_params
from src.core.utils import BaseInstanaClient, register_as_tool
from src.core.validation import BooleanCoercer, EventsValidator

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

_VALID_SEVERITIES = frozenset({-1, 5, 10})
_VALID_EVENT_TYPES = frozenset({"INCIDENT", "ISSUE", "CHANGE"})


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

    @staticmethod
    def _extract_event_filters_from_params(operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the unified filters dict from raw params, handling get_events nesting."""
        source = params.get("filters", {}) if operation == OPERATION_GET_EVENTS else params
        return {
            PARAM_EVENT_ID: source.get(PARAM_EVENT_ID),
            PARAM_EVENT_IDS: source.get(PARAM_EVENT_IDS),
            PARAM_FROM_TIME: source.get(PARAM_FROM_TIME),
            PARAM_TO_TIME: source.get(PARAM_TO_TIME),
            PARAM_TIME_RANGE: source.get(PARAM_TIME_RANGE),
            PARAM_QUERY: source.get(PARAM_QUERY),
            PARAM_MAX_EVENTS: source.get(PARAM_MAX_EVENTS, DEFAULT_MAX_EVENTS),
            PARAM_FILTER_EVENT_UPDATES: source.get(PARAM_FILTER_EVENT_UPDATES),
            PARAM_EXCLUDE_TRIGGERED_BEFORE: source.get(PARAM_EXCLUDE_TRIGGERED_BEFORE),
            PARAM_EVENT_TYPE_FILTERS: source.get(PARAM_EVENT_TYPE_FILTERS),
            PARAM_ENTITY_TYPE: source.get(PARAM_ENTITY_TYPE),
            PARAM_ENTITY_NAME: source.get(PARAM_ENTITY_NAME),
            PARAM_ENTITY_LABEL: source.get(PARAM_ENTITY_LABEL),
            PARAM_STATE: source.get(PARAM_STATE),
            PARAM_PROBLEM: source.get(PARAM_PROBLEM),
            PARAM_SEVERITY: source.get(PARAM_SEVERITY),
            PARAM_EVENT_SPECIFICATION_ID: source.get(PARAM_EVENT_SPECIFICATION_ID),
            PARAM_RCA: source.get(PARAM_RCA),
        }

    @staticmethod
    def _preflight_events_operation(operation: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate operation-specific required params; return elicitation dict or None."""
        if operation == OPERATION_GET_EVENT:
            if not filters[PARAM_EVENT_ID] or not str(filters[PARAM_EVENT_ID]).strip():
                return {
                    "elicitation_needed": True,
                    "reason": "get_event: event_id is required",
                    "api_error": ["event_id: required — provide the event ID string (obtain one from get_events or get_events_by_ids)"],
                    "message": "event_id is required for 'get_event'. Obtain one from the 'get_events' operation first.",
                }

        if operation == OPERATION_GET_EVENTS_BY_IDS:
            raw_ids = filters[PARAM_EVENT_IDS]
            if not raw_ids or (isinstance(raw_ids, list) and len(raw_ids) == 0):
                return {
                    "elicitation_needed": True,
                    "reason": "get_events_by_ids: event_ids is required",
                    "api_error": ['event_ids: required — provide a list of event ID strings. Example: ["1a2b3c4d5e6f", "7g8h9i0j1k2l"]'],
                    "message": 'event_ids is required for \'get_events_by_ids\'. Example: {"event_ids": ["1a2b3c4d5e6f", "7g8h9i0j1k2l"]}',
                }

        if operation == OPERATION_GET_EVENTS:
            return EventsSmartRouterMCPTool._validate_get_events_filters(filters)

        return None

    @staticmethod
    def _validate_get_events_filters(filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate get_events-specific filter fields; mutates bool flags in-place. Returns elicitation dict or None."""
        errors: list = []

        severity = filters[PARAM_SEVERITY]
        if severity is not None and severity not in _VALID_SEVERITIES:
            errors.append(
                f"filters.severity: {severity!r} is not valid. "
                "Allowed values: -1 (change/informational), 5 (warning), 10 (critical)"
            )

        event_type_filters = filters[PARAM_EVENT_TYPE_FILTERS]
        if event_type_filters is not None:
            if not isinstance(event_type_filters, list):
                errors.append("filters.event_type_filters: must be a list. " 'Example: ["INCIDENT", "ISSUE"]')
            else:
                for i, et in enumerate(event_type_filters):
                    if not isinstance(et, str) or et.upper() not in _VALID_EVENT_TYPES:
                        errors.append(f"filters.event_type_filters[{i}]: {et!r} is not valid. Must be one of: {sorted(_VALID_EVENT_TYPES)}")

        max_events = filters[PARAM_MAX_EVENTS]
        if max_events is not None:
            if not isinstance(max_events, int):
                errors.append(f"filters.max_events: must be an integer, got {type(max_events).__name__!r}")
            elif max_events < 1 or max_events > 1000:
                errors.append(f"filters.max_events: {max_events} is out of range. Must be 1-1000")

        for flag in (PARAM_FILTER_EVENT_UPDATES, PARAM_EXCLUDE_TRIGGERED_BEFORE):
            raw = filters[flag]
            if raw is not None:
                coerced = BooleanCoercer.coerce(raw)
                if coerced is None:
                    errors.append(f"filters.{flag}: {raw!r} cannot be interpreted as a boolean. Use true or false")
                else:
                    filters[flag] = coerced

        if not errors:
            return None
        return {
            "elicitation_needed": True,
            "reason": f"get_events filters have {len(errors)} validation problem(s)",
            "api_error": errors,
            "message": (
                f"The get_events filters have {len(errors)} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    def _validate_time_and_max_events(
        self,
        operation: str,
        filters: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Validate max_events for time-requiring operations; return error dict or None."""
        max_events_error = EventsValidator.validate_max_events(filters[PARAM_MAX_EVENTS])
        if max_events_error:
            logger.warning(f"[manage_events] max_events validation failed: {max_events_error.message}, provided value: {filters[PARAM_MAX_EVENTS]}")
            return {
                "operation": operation,
                "validation_failed": True,
                "valid": False,
                "error_count": 1,
                "errors": [max_events_error.to_dict()],
                "message": "Parameter validation failed. Please correct the following fields and try again.",
            }
        return None

    async def _dispatch_events_operation(
        self,
        operation: str,
        filters: Dict[str, Any],
        from_time: Any,
        to_time: Any,
        ctx: Any,
    ) -> Dict[str, Any]:
        """Route a validated events operation to the appropriate client method."""
        if operation == OPERATION_GET_EVENT:
            return await self.events_client.get_event(event_id=filters[PARAM_EVENT_ID], ctx=ctx)
        if operation == OPERATION_GET_KUBERNETES_INFO_EVENTS:
            return await self.events_client.get_kubernetes_info_events(
                from_time=from_time, to_time=to_time,
                time_range=filters[PARAM_TIME_RANGE], max_events=filters[PARAM_MAX_EVENTS], ctx=ctx,
            )
        if operation == OPERATION_GET_AGENT_MONITORING_EVENTS:
            return await self.events_client.get_agent_monitoring_events(
                query=filters[PARAM_QUERY], from_time=from_time, to_time=to_time,
                max_events=filters[PARAM_MAX_EVENTS], time_range=filters[PARAM_TIME_RANGE], ctx=ctx,
            )
        if operation == OPERATION_GET_EVENTS:
            return await self.events_client.get_events(filters={
                "query": filters[PARAM_QUERY], "from_time": from_time, "to_time": to_time,
                "filter_event_updates": filters[PARAM_FILTER_EVENT_UPDATES],
                "exclude_triggered_before": filters[PARAM_EXCLUDE_TRIGGERED_BEFORE],
                "max_events": filters[PARAM_MAX_EVENTS], "time_range": filters[PARAM_TIME_RANGE],
                "event_type_filters": filters[PARAM_EVENT_TYPE_FILTERS],
                "entity_type": filters[PARAM_ENTITY_TYPE], "entity_name": filters[PARAM_ENTITY_NAME],
                "entity_label": filters[PARAM_ENTITY_LABEL], "state": filters[PARAM_STATE],
                "problem": filters[PARAM_PROBLEM], "severity": filters[PARAM_SEVERITY],
                "event_specification_id": filters[PARAM_EVENT_SPECIFICATION_ID], "rca": filters[PARAM_RCA],
            }, ctx=ctx)
        if operation == OPERATION_GET_EVENTS_BY_IDS:
            return await self.events_client.get_events_by_ids(event_ids=filters[PARAM_EVENT_IDS], ctx=ctx)
        return {"error": f"Unrouted operation '{operation}'", "operation": operation}

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
- MANDATORY: If NONE of from_time, to_time, or time_range are provided, defaults to the last 10 minutes
- For "get_event" and "get_events_by_ids", pass flat params:
    - event_id: Event ID (required for get_event)
    - event_ids: List of event IDs or comma-separated string (required for get_events_by_ids)
- For "get_kubernetes_info_events" and "get_agent_monitoring_events", pass flat params:
    - from_time: Start timestamp - milliseconds OR datetime string (e.g., "19 March 2026, 2:47 PM|IST" or "19 March 2026, 2:47 PM")
        If timezone not specified in datetime string, defaults to UTC
    - to_time: End timestamp - milliseconds OR datetime string (e.g., "19 March 2026, 2:47 PM|IST" or "19 March 2026, 2:47 PM")
        If timezone not specified in datetime string, defaults to UTC
    - time_range: Natural language time range (e.g., "last 10 minutes", "last 2 days"). DEFAULT when omitted: "last 10 minutes"
    - query: Optional query string for agent monitoring events
    - max_events: Maximum number of events to process for analysis (optional, default 50)
        NOTE: This is a post-processing limit, not an API parameter
- For "get_events", pass a nested filters object:
    - filters: Dictionary containing event filters.
        - from_time: Start timestamp - milliseconds OR datetime string
        - to_time: End timestamp - milliseconds OR datetime string
        - time_range: Natural language time range (e.g., "last 10 minutes", "last 2 days"). DEFAULT when omitted: "last 10 minutes"
        - query: Optional query string
        - max_events: Maximum number of events to process for analysis (optional, default 50)
        - filter_event_updates: Boolean flag to filter results to only show events with state changes within timeframe (optional, default True)
        - exclude_triggered_before: Boolean flag to exclude events triggered before the timeframe (optional, default True)
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
    operation="get_kubernetes_info_events", params={"time_range": "last 2 hours", "max_events": 50}
    operation="get_agent_monitoring_events", params={"query": "Monitoring issue", "from_time": "19 March 2026, 2:47 PM|IST", "to_time": "20 March 2026, 2:47 PM|IST", "max_events": 100}
    operation="get_events", params={"filters": {"event_type_filters": ["INCIDENT"]}}  # no time_range → defaults to last 10 minutes
    operation="get_events", params={"filters": {"event_type_filters": ["INCIDENT"], "entity_type": "service", "entity_name": "payment-service", "entity_label": "payment-service-v2", "state": "open", "problem": "High error rate", "severity": 10, "max_events": 50, "filter_event_updates": True, "exclude_triggered_before": False}}
    operation="get_events_by_ids", params={"event_ids": ["1a2b3c4d5e6f", "7g8h9i0j1k2l"]}"""
    )
    async def manage_events(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Unified Instana events resource manager for events monitoring operations."""
        try:
            logger.debug(f"[manage_events] Received operation: {operation}")
            params = params or {}

            if operation not in EVENTS_VALID_OPERATIONS:
                logger.warning(f"[manage_events] Invalid operation: {operation}")
                return {
                    "elicitation_needed": True,
                    "reason": f"Invalid operation: {operation!r}",
                    "api_error": [f"operation: {operation!r} is not valid for events. Must be one of: {EVENTS_VALID_OPERATIONS}"],
                    "message": f"operation {operation!r} is not valid. Accepted values are: {EVENTS_VALID_OPERATIONS}.",
                }

            filters = self._extract_event_filters_from_params(operation, params)

            preflight = self._preflight_events_operation(operation, filters)
            if preflight:
                return preflight

            conversion_result = convert_datetime_params(
                {PARAM_FROM_TIME: filters[PARAM_FROM_TIME], PARAM_TO_TIME: filters[PARAM_TO_TIME]},
                [PARAM_FROM_TIME, PARAM_TO_TIME],
                default_timezone="UTC",
            )
            if "error" in conversion_result:
                return {
                    "elicitation_needed": True,
                    "reason": "datetime conversion failed for from_time or to_time",
                    "api_error": [conversion_result["error"]],
                    "message": (
                        "Could not parse the provided datetime value. "
                        "Use a Unix timestamp in milliseconds or a datetime string "
                        'like "19 March 2026, 2:47 PM|IST".\n'
                        f"  - {conversion_result['error']}"
                    ),
                }

            from_time = conversion_result["params"][PARAM_FROM_TIME]
            to_time = conversion_result["params"][PARAM_TO_TIME]

            if operation in TIME_REQUIRED_OPERATIONS:
                time_error = self._validate_time_and_max_events(operation, filters)
                if time_error:
                    return time_error

            logger.debug(f"[manage_events] Routing to Events client for operation: {operation}")
            result = await self._dispatch_events_operation(operation, filters, from_time, to_time, ctx)

            logger.debug(f"[manage_events] Successfully completed operation: {operation}")
            return {"operation": operation, "results": result}

        except Exception as e:
            logger.error(f"[manage_events] Error processing operation: {operation}, error: {e!s}", exc_info=True)
            return {"error": f"Events smart router error: {e!s}", "operation": operation}
