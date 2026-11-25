"""
Smart Router Tool

This module provides a unified MCP tool that routes queries to the appropriate
application-specific tools for Instana monitoring.
"""

import logging
import re
import time as _time

from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional, Union, Tuple, cast

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.pagination import apply_navigation, page_kwargs, paginate, stable_sort_key
from src.core.timestamp_utils import (
    convert_datetime_param,
    convert_nested_datetime_param,
)
from src.core.utils import BaseInstanaClient, register_as_tool
from src.core.timestamp_utils import TIMEZONE_ALIASES, convert_to_timestamp, parse_timezone

logger = logging.getLogger(__name__)
_MS_MINUTE = 60 * 1000
_MS_HOUR = 60 * _MS_MINUTE
_MS_DAY = 24 * _MS_HOUR
_MAX_WINDOW_MS = 31 * _MS_DAY  # largest windowSize the Instana TimeFrame accepts (2678400000)


# Rolling windows that end "now": canonical label -> window size in ms.
_ROLLING_TIME_RANGES = {
    "last minute": _MS_MINUTE,
    "last 5 minutes": 5 * _MS_MINUTE,
    "last 10 minutes": 10 * _MS_MINUTE,
    "last 30 minutes": 30 * _MS_MINUTE,
    "last hour": _MS_HOUR,
    "last 6 hours": 6 * _MS_HOUR,
    "last 12 hours": 12 * _MS_HOUR,
    "last 24 hours": _MS_DAY,
    "last seven days": 7 * _MS_DAY,
}
_CALENDAR_TIME_RANGES = ("today", "yesterday", "two days ago", "previous week")
DEFAULT_ERROR_TIME_RANGE = "last hour"
_ERROR_TRACE_FETCH_LIMIT = 1000  # max erroneous traces fetched per request


def invalid_timezone_error(timezone: Any) -> Optional[Dict[str, Any]]:
    """Return a structured error when *timezone* is set but not a usable IANA name or alias.

    ``parse_timezone`` silently falls back to UTC (and raises on non-strings), which would
    give wrong calendar-day boundaries without telling the user. ``None``/empty means UTC.
    """
    if timezone is None or timezone == "":
        return None
    if isinstance(timezone, str):
        name = TIMEZONE_ALIASES.get(timezone.strip().upper(), timezone.strip())
        try:
            ZoneInfo(name)
            return None
        except Exception:
            pass
    return {
        "error": f"Invalid timezone '{timezone}'.",
        "valid_time_zones": ["UTC", *sorted(TIMEZONE_ALIASES)[:20]],
        "hint": "Use an IANA name such as 'America/New_York' or 'Asia/Kolkata', or an alias such as 'IST'. "
                "Omit timezone to use UTC.",
    }


def resolve_time_range(
    time_range: Optional[str], timezone: Optional[str] = None
) -> Optional[Tuple[Dict[str, int], str]]:
    """Turn a time-range phrase into an Instana ``timeFrame`` and a display label.

    Every range returns an explicit ``to`` (epoch ms) and ``windowSize`` (ms); only these
    two fields exist in the API's TimeFrame (``focusedMoment`` / ``autoRefresh`` are UI-only).
    Rolling ranges ("last 5 minutes", "last hour", "last seven days", ...) end at the
    current time. Calendar ranges use exact day boundaries in *timezone* (default UTC):

    * ``today``         - local midnight until now
    * ``yesterday``     - the previous calendar day
    * ``two days ago``  - the calendar day before yesterday
    * ``previous week`` - the previous calendar week, Monday 00:00 until Monday 00:00

    Also accepts a generic "last N minutes/hours/days/weeks". Returns ``None`` when the
    phrase is not understood or the window exceeds the API maximum of 31 days.
    """
    from datetime import datetime, timedelta

    now_ms = int(_time.time() * 1000)
    # Accept "last_seven_days" / "last-seven-days" (metrics-style names) as "last seven days".
    text = re.sub(r"[\s_\-]+", " ", (time_range or "").strip().lower())
    if not text:
        return None
    text = {
        "last 1 minute": "last minute", "last 1 hour": "last hour",
        "last 7 days": "last seven days", "last week": "last seven days",
        "past 7 days": "last seven days", "last 1 day": "last 24 hours",
        "last day": "last 24 hours", "day before yesterday": "two days ago",
        "last 1 hours": "last hour", "previous 7 days": "last seven days",
        "past seven days": "last seven days", "past week": "last seven days",
        "this past week": "last seven days", "over the last week": "last seven days",
        "in the last 7 days": "last seven days", "over the last 7 days": "last seven days",
        "prior week": "previous week", "last calendar week": "previous week",
    }.get(text, text)

    if text in _ROLLING_TIME_RANGES:
        return {"to": now_ms, "windowSize": _ROLLING_TIME_RANGES[text]}, text

    generic = re.match(r"^(?:last|past)\s+(\d+)\s*(minute|min|hour|hr|day|week)s?$", text)
    if generic:
        unit_ms = {"minute": _MS_MINUTE, "min": _MS_MINUTE, "hour": _MS_HOUR,
                   "hr": _MS_HOUR, "day": _MS_DAY, "week": 7 * _MS_DAY}[generic.group(2)]
        count = int(generic.group(1))
        if count < 1 or count * unit_ms > _MAX_WINDOW_MS:
            return None
        return (
            {"to": now_ms, "windowSize": count * unit_ms},
            f"last {count} {generic.group(2)}{'s' if count != 1 else ''}",
        )

    if text not in _CALENDAR_TIME_RANGES:
        return None

    tz = parse_timezone(timezone or "UTC")
    now = datetime.now(tz)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if text == "today":
        start, end = midnight, now
    elif text == "yesterday":
        start, end = midnight - timedelta(days=1), midnight
    elif text == "two days ago":
        start, end = midnight - timedelta(days=2), midnight - timedelta(days=1)
    else:  # previous week: Monday..Monday before the current week
        this_monday = midnight - timedelta(days=midnight.weekday())
        start, end = this_monday - timedelta(days=7), this_monday
    start_ms, end_ms = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    return {"to": end_ms, "windowSize": max(1, end_ms - start_ms)}, text



class ApplicationSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router that routes queries to Application Metrics, Alert Configuration, and Catalog tools.
    The LLM agent determines the appropriate operation based on query understanding.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Smart Router MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Initialize the application tool clients
        from src.application.application_alert_config import ApplicationAlertMCPTools
        from src.application.application_analyze import ApplicationAnalyzeMCPTools
        from src.application.application_call_group import ApplicationCallGroupMCPTools
        from src.application.application_catalog import ApplicationCatalogMCPTools
        from src.application.application_global_alert_config import (
            ApplicationGlobalAlertMCPTools,
        )
        from src.application.application_resources import ApplicationResourcesMCPTools
        from src.application.application_settings import ApplicationSettingsMCPTools

        self.app_call_group_client = ApplicationCallGroupMCPTools(read_token, base_url)
        self.app_alert_config_client = ApplicationAlertMCPTools(read_token, base_url)
        self.app_global_alert_config_client = ApplicationGlobalAlertMCPTools(read_token, base_url)
        self.app_resources_client = ApplicationResourcesMCPTools(read_token, base_url)
        self.app_settings_client = ApplicationSettingsMCPTools(read_token, base_url)
        self.app_catalog_client = ApplicationCatalogMCPTools(read_token, base_url)
        self.app_analyze_client = ApplicationAnalyzeMCPTools(read_token, base_url)

        logger.info("Smart Router initialized with Application tools")

    @register_as_tool(
        title="Manage Instana Application Resources",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
        description="""Unified Instana application resource manager for metrics, alerts, configurations, and catalog.

SCOPE: HTTP/gRPC/DB call traces, trace and span details, application service
metrics, alert configs, and application perspectives.

LLM/GenAI agents: route by what's asked, not by the agent's name.
- Trace-level data (latency, errors, spans, prompt/output content, "most recently
  failed" calls) → analyze here. Prompt/output content is in span attributes.
  Not manage_events.
- Entity metrics (token usage, cost, throughput, "list GenAI apps") →
  manage_infrastructure (oTelLLM).
- Both (e.g. ".run.workflow traces with P95 latency and tokens"): get traces
  here, then token metrics from manage_infrastructure, joined on agent/service name.

Resource Types:
    - "metrics": Query application metrics, services, and endpoints
    - "alert_config": Manage application-specific alert configurations
    - "global_alert_config": Manage global application alert configurations
    - "settings": Manage application configurations
    - "catalog": Access application tag and metric catalog information
    - "resources": Query application resources, services, endpoints (HTTP/gRPC services only — NOT LLM agents)
    - "analyze": Analyze application traces and calls — individual traces, span details, trace groups

CRITICAL WORKFLOW - ALWAYS FOLLOW THIS ORDER BEFORE METRICS/ANALYZE QUERIES:
    1. FIRST: Call get_metric_catalog to get valid metrics
       - resource_type="catalog", operation="get_metric_catalog"
       - Returns: Available metrics with metricId, aggregations, and data sources

    2. SECOND: Call get_tag_catalog to get valid tag names
       - resource_type="catalog", operation="get_tag_catalog"
       - params: {"use_case": "GROUPING", "data_source": "CALLS"}

    3. THIRD: Use ONLY the tag names and metrics returned from catalog operations
       - Metric names must match those from get_metric_catalog
       - Tag names must match those from get_tag_catalog
       - NEVER guess or invent tag names or metric names

    4. FOURTH: Call metrics operations with validated tag names and metrics
       - Example invalid: "calls.error.count" (not in catalog)
       - Example valid: "calls" with aggregation "SUM"

METRICS (resource_type="metrics"):
    operation: get_grouped_calls_metrics
    params: {time_frame, metrics, tag_filter_expression, group, order, pagination, include_internal, include_synthetic}

    Aggregations: SUM, MEAN, MAX, MIN, P25, P50, P75, P90, P95, P98, P99, DISTINCT_COUNT, SUM_POSITIVE
    Operators: EQUALS, NOT_EQUAL, CONTAINS, NOT_CONTAIN, STARTS_WITH, ENDS_WITH, GREATER_THAN, GREATER_OR_EQUAL_THAN, LESS_THAN, LESS_OR_EQUAL_THAN, NOT_EMPTY, IS_EMPTY

    time_frame: {"to": <timestamp_or_datetime>, "windowSize": <milliseconds>}
        - to: Unix timestamp (ms) OR datetime string (e.g., "19 March 2026, 2:47 PM|IST")
        - windowSize: Duration in milliseconds (default: 3600000 = 1 hour)
        - CRITICAL: Never pass "to": 0. Zero is Unix epoch (1970-01-01) and returns no data.
          Omit "to" entirely when the user means "now", as "to" is OPTIONAL — the API defaults to the current time.

    tag_filter_expression: CRITICAL - Entity field is REQUIRED for ALL tag filters

    ENTITY FIELD VALUES:

    "SOURCE" or "DESTINATION" → Tag identifies an infrastructure/service component
      (what/where: hosts, services, containers, databases, endpoints)
      (catalog hint: canApplyToSource/canApplyToDestination = true)

    "NOT_APPLICABLE" → Tag describes call behavior or metadata
      (how/what happened: call metrics, trace properties, geo data, business context)
      (catalog hint: canApplyToSource/canApplyToDestination = false)

    Never omit entity field or set to null - it is MANDATORY.

    Examples:
      * Entity component: {"type": "TAG_FILTER", "name": "service.name", "entity": "DESTINATION", ...}
      * Call metadata: {"type": "TAG_FILTER", "name": "call.latency", "entity": "NOT_APPLICABLE", ...}
      * Geographic: {"type": "TAG_FILTER", "name": "geo.country", "entity": "NOT_APPLICABLE", ...}


ALERT_CONFIG (resource_type="alert_config"):
    operations: find_active, find_versions, find, create, update, delete, enable, disable, restore, update_baseline
    params: {application_id OR application_name, id, alert_ids, valid_on, created, payload, page, page_size}

GLOBAL_ALERT_CONFIG (resource_type="global_alert_config"):
    operations: find_active, find_versions, find, create, update, delete, enable, disable, restore
    params: {application_id OR application_name, id, alert_ids, valid_on, created, payload, page, page_size}

PAGINATION (alert_config / global_alert_config find_active, settings get_all):
    alert_config / global_alert_config find_active return page 1 (10 items) by default. settings get_all
    returns every item unless page/page_size is given. Paged responses carry a pagination envelope
    ({page, page_size, total_items, total_pages, has_more, has_previous, next_operation, previous_operation}).
    To change page, call the same resource_type with operation=<next_operation or previous_operation>
    (e.g. "page_2") and the same params. Do not track page numbers yourself.

SETTINGS (resource_type="settings"):
    operations: get_all, get, create, update, delete
    params: {resource_subtype, id, application_name, service_name, service_id, payload, request_body, page, page_size}
    get_all is paged only when page/page_size is given (see PAGINATION).
    resource_subtypes: "application"
    get_all / get (resource_subtype="application") results include a markdown "link" per application.
    ALWAYS show each application name using its 'link' field verbatim (markdown) so it opens in the
    Instana UI. NEVER shorten, rebuild or drop the URL.

    Creating application (resource_subtype="application", operation="create"):
    REQUIRED: label | OPTIONAL: scope, boundaryScope, accessRules, tagFilterExpression
    Minimal: params={"resource_subtype": "application", "payload": {"label": "My App"}}

RESOURCES (resource_type="resources"):
    ❌ NOT FOR LLM/GenAI agents — use manage_infrastructure with plugin="oTelLLM" for those.
       This covers HTTP/gRPC/database application services and endpoints only.
    operations: get_applications, get_services, get_application_services, get_application_endpoints
    params: {application_id, service_id, endpoint_id, name_filter, types, technologies, application_boundary_scope, include_snapshot_ids}
    get_applications - Get application perspectives (not LLM/GenAI entities)
        params: {name_filter, application_boundary_scope}
        Returns: Paginated list of applications with their configurations and metadata
    get_services - Get all services for application monitoring (HTTP/gRPC services only — NOT AI agents or GenAI apps)
        params: {name_filter, include_snapshot_ids}
        Returns: Paginated list of services across all applications
    get_application_services - Get services for a specific application perspective
        params: {application_id, service_id, name_filter, application_boundary_scope, include_snapshot_ids}
        Returns: Paginated services filtered by application context. Each service includes a markdown
        "link"; ALWAYS show service names using the 'link' field verbatim (markdown).
    get_application_endpoints - Get endpoints for an application service
        params: {application_id, service_id, endpoint_id, name_filter, types, technologies, application_boundary_scope}
        Returns: Paginated endpoints with type and technology metadata
    get_error_messages_by_application_name - List the erroneous endpoints (errors) of an application
        params: {application_name OR application_id (one required), time_range (optional), timezone (optional, default UTC)}
        ALWAYS use this (not manage_events get_events) for "show/list all error messages / errors for an
        application", whether the user gives an application name or an Instana application ID
        (e.g. "SZNCeB7YR_iR1xMZrlN2bw"). Put an ID in application_id, a name in application_name.
        time_range must be one of: "last minute", "last 5 minutes", "last 10 minutes", "last 30 minutes",
        "last hour" (default when the user gives none), "last 6 hours", "last 12 hours", "last 24 hours", "today", "yesterday",
        "two days ago", "last seven days", "previous week". "today"/"yesterday"/"two days ago" are calendar
        days in `timezone` ("previous week" = previous Monday-to-Monday); the others end now.
        Pass the user's phrase as time_range; do NOT convert it to window_size yourself.
        If the user does not state a time range, OMIT time_range entirely (the default is "last hour");
        never add a time_range such as "last seven days" on your own.
        Use this operation when the user asks to "list error messages for application", "what errors does
        <application> have", or "show errors for <application>". Do NOT use get_trace_groups for this.
        Resolves application_name (or IMAP code) to the application, then lists its erroneous calls grouped by
        endpoint (POST /api/application-monitoring/analyze/call-groups with
        call.inbound_of_application = <application>, call.erroneous = true,
        group by endpoint.name, metric erroneousCalls SUM), highest error count first.
        Returns: 10 endpoints per page, each with endpoint name and erroneous_calls count, plus
        total_hits, the standard pagination envelope and a pre-rendered 'display_markdown' to show verbatim.
        At most 1000 endpoints are fetched; if more matched, the response carries a "note" - show it.
        Navigate with operation = pagination.next_operation / previous_operation, which look like
        "error_page_2:<application_name>|<time_range>"; copy them exactly.



CATALOG (resource_type="catalog"):
    operations: get_tag_catalog, get_metric_catalog
    params: {use_case, data_source, var_from}

    get_metric_catalog - Get application metrics catalog with metadata (metricId, label, aggregations, beaconTypes)
    get_tag_catalog - Get valid tag names for use_case and data_source
        Valid use_case: "GROUPING", "FILTERING", "SERVICE_MAPPING", "SMART_ALERTS"
        Valid data_source: "CALLS", "TRACES"

ANALYZE (resource_type="analyze"):
    Use for individual distributed traces, span-level details, and trace group
    aggregations (P95 latency, error rate, call counts by endpoint or service).
    NOT for aggregated oTelLLM entity metrics (token counts, cost) — use
    manage_infrastructure for those.
    operations: get_all_traces, get_trace_details, get_trace_groups

    time_frame: {"to": <timestamp_or_datetime>, "windowSize": <milliseconds>}
        - to: Unix timestamp in milliseconds OR datetime string (e.g., "19 March 2026, 2:47 PM|IST")
        - If timezone not specified in datetime string, defaults to UTC
        - windowSize: Duration in milliseconds (default: 3600000 = 1 hour)
        - CRITICAL: Never pass "to": 0. Zero is Unix epoch (1970-01-01) and returns no data.
          Omit "to" entirely when the user means "now", as "to" is OPTIONAL — the API defaults to the current time.

    get_all_traces - params: {payload}
        payload: {timeFrame, includeInternal, includeSynthetic, tagFilterExpression, pagination, order}
        timeFrame.to: Unix timestamp (ms) OR datetime string with timezone

    get_trace_details - params: {id, retrievalSize, offset, ingestionTime}
        Returns: items, itemCount, canLoadMore, cursor for pagination

    get_trace_groups - params: {payload}
        payload: {group, metrics, timeFrame, tagFilterExpression, pagination, order, includeInternal, includeSynthetic}
        NOTE: 'group' and 'metrics' are mandatory payload fields.
        The 'group' object must include 'groupbyTag' and 'groupbyTagEntity'.
        Supported groupbyTag values are 'trace.endpoint.name' and 'trace.service.name'.
        Allowed groupbyTagEntity values are 'NOT_APPLICABLE', 'DESTINATION', and 'SOURCE'.

        CRITICAL: The "calls" metric is NOT supported for trace operations. Use "traces" or other trace-specific metrics.
        Use get_metric_catalog first to look up valid metric names and aggregations as described in the critical workflow.

Args:
    resource_type: "metrics", "alert_config", "global_alert_config", "settings", "catalog", "resources", or "analyze"
    operation: Specific operation for the resource type
    params: Operation-specific parameters (optional)
    ctx: MCP context (internal)

Returns:
    Dictionary with results from the appropriate tool

Examples:
    # CATALOG operations
    resource_type="catalog", operation="get_metric_catalog"
    resource_type="catalog", operation="get_tag_catalog", params={"use_case": "GROUPING", "data_source": "CALLS", "var_from": 1710658800000}

    # METRICS operations
    resource_type="metrics", operation="get_grouped_calls_metrics", params={"metrics": [{"metric": "calls", "aggregation": "SUM"}, {"metric": "latency", "aggregation": "MEAN"}], "tag_filter_expression": {"type": "TAG_FILTER", "name": "application.name", "operator": "EQUALS", "entity": "DESTINATION", "value": "All Services"}, "group": {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}, "time_frame": {"to": 1710658800000, "windowSize": 3600000}, "order": {"by": "calls", "direction": "DESC"}, "pagination": {"retrievalSize": 20}, "include_internal": False, "include_synthetic": False}

    # ALERT_CONFIG operations
    resource_type="alert_config", operation="find_active", params={"application_name": "All Services", "alert_ids": ["alert-1", "alert-2"]}
    resource_type="alert_config", operation="find_versions", params={"application_id": "app-123", "id": "alert-456"}
    resource_type="alert_config", operation="find", params={"application_id": "app-123", "id": "alert-456", "valid_on": 1710658800000}
    resource_type="alert_config", operation="create", params={"application_id": "app-123", "payload": {"name": "High Error Rate", "severity": 5}}
    resource_type="alert_config", operation="update", params={"application_id": "app-123", "id": "alert-456", "payload": {"name": "Updated Alert"}}
    resource_type="alert_config", operation="delete", params={"application_id": "app-123", "id": "alert-456"}
    resource_type="alert_config", operation="enable", params={"application_id": "app-123", "id": "alert-456"}
    resource_type="alert_config", operation="disable", params={"application_id": "app-123", "id": "alert-456"}
    resource_type="alert_config", operation="restore", params={"application_id": "app-123", "id": "alert-456", "created": 1710658800000}
    resource_type="alert_config", operation="update_baseline", params={"application_id": "app-123", "id": "alert-456"}

    # GLOBAL_ALERT_CONFIG operations
    resource_type="global_alert_config", operation="find_active", params={"application_name": "All Services"}
    resource_type="global_alert_config", operation="find_versions", params={"application_id": "app-123", "id": "alert-789"}
    resource_type="global_alert_config", operation="find", params={"application_id": "app-123", "id": "alert-789", "valid_on": 1710658800000}
    resource_type="global_alert_config", operation="create", params={"application_id": "app-123", "payload": {"name": "Global Alert"}}
    resource_type="global_alert_config", operation="update", params={"application_id": "app-123", "id": "alert-789", "payload": {"name": "Updated Global Alert"}}
    resource_type="global_alert_config", operation="delete", params={"application_id": "app-123", "id": "alert-789"}
    resource_type="global_alert_config", operation="enable", params={"application_id": "app-123", "id": "alert-789"}
    resource_type="global_alert_config", operation="disable", params={"application_id": "app-123", "id": "alert-789"}
    resource_type="global_alert_config", operation="restore", params={"application_id": "app-123", "id": "alert-789", "created": 1710658800000}

    # SETTINGS operations
    resource_type="settings", operation="get_all", params={"resource_subtype": "application"}
    resource_type="settings", operation="get", params={"resource_subtype": "application", "application_name": "My App"}
    resource_type="settings", operation="create", params={"resource_subtype": "application", "payload": {"label": "My App", "scope": "INCLUDE_ALL_DOWNSTREAM", "boundaryScope": "ALL"}}
    resource_type="settings", operation="update", params={"resource_subtype": "application", "id": "config-123", "payload": {"label": "Updated App"}}
    resource_type="settings", operation="delete", params={"resource_subtype": "application", "id": "config-123"}

    # RESOURCES operations
    resource_type="resources", operation="get_applications", params={"name_filter": "My App"}
    resource_type="resources", operation="get_services", params={"name_filter": "My Service", "include_snapshot_ids": True}
    resource_type="resources", operation="get_application_services", params={"application_id": "app-123", "service_id": "svc-456", "name_filter": "API"}
    resource_type="resources", operation="get_application_endpoints", params={"application_id": "app-123", "service_id": "svc-456", "endpoint_id": "ep-789", "name_filter": "/api/users", "types": ["HTTP"], "technologies": ["Java"]}

    # ANALYZE operations
    resource_type="analyze", operation="get_all_traces", params={"payload": {"timeFrame": {"windowSize": 3600000}, "includeInternal": True, "includeSynthetic": False, "pagination": {"retrievalSize": 200}}}
    resource_type="analyze", operation="get_trace_details", params={"id": "trace-123", "retrievalSize": 100, "offset": 0, "ingestionTime": 1725519793}
    resource_type="analyze", operation="get_trace_groups", params={"payload": {"group": {"groupbyTag": "trace.service.name", "groupbyTagEntity": "DESTINATION"},  "includeInternal": True, "includeSynthetic": False, "metrics": [{"metric": "traces", "aggregation": "SUM"}], "timeFrame": {"to": 1710658800000, "windowSize": 3600000}}}"""
    )
    async def manage_applications(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Unified Instana application resource manager for metrics, alerts, configurations, and catalog."""
        try:
            logger.info(f"Smart Router received: resource_type={resource_type}, operation={operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate resource_type
            _valid_resource_types = [
                "metrics", "alert_config", "global_alert_config",
                "settings", "catalog", "resources", "analyze",
            ]
            if resource_type not in _valid_resource_types:
                return {
                    "elicitation_needed": True,
                    "reason": "invalid_resource_type",
                    "api_error": [
                        {
                            "field": "resource_type",
                            "issue": f"'{resource_type}' is not a valid resource type",
                            "expected": _valid_resource_types
                        }
                    ],
                    "message": f"Invalid resource_type '{resource_type}'. Must be one of: {_valid_resource_types}"
                }

            # Route to the appropriate resource handler
            if resource_type == "metrics":
                return await self._handle_metrics(operation, params, ctx)
            elif resource_type == "alert_config":
                return await self._handle_alert_config(operation, params, ctx)
            elif resource_type == "global_alert_config":
                return await self._handle_global_alert_config(operation, params, ctx)
            elif resource_type == "settings":
                return await self._handle_settings(operation, params, ctx)
            elif resource_type == "catalog":
                return await self._handle_catalog(operation, params, ctx)
            elif resource_type == "resources":
                return await self._handle_resources(operation, params, ctx)
            elif resource_type == "analyze":
                return await self._handle_analyze(operation, params, ctx)
            else:
                return {
                    "elicitation_needed": True,
                    "reason": "invalid_resource_type",
                    "api_error": [
                        {
                            "field": "resource_type",
                            "issue": f"Unsupported resource_type: '{resource_type}'",
                            "expected": _valid_resource_types
                        }
                    ],
                    "message": f"Unsupported resource_type '{resource_type}'. Must be one of: {_valid_resource_types}"
                }

        except Exception as e:
            logger.error(f"Error in smart router: {e}", exc_info=True)
            return {
                "error": f"Smart router error: {e!s}",
                "resource_type": resource_type,
                "operation": operation
            }

    async def _handle_metrics(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle application metrics queries."""
        # Guard: "to": 0 means Unix epoch (1970), not "now". Strip it so the
        # API defaults to the current server time, which is the correct behaviour
        # when the user asks for a relative window like "last 1 hour".
        if isinstance(params.get("time_frame"), dict) and params["time_frame"].get("to") == 0:
            del params["time_frame"]["to"]

        # Convert datetime string for time_frame.to if provided
        conversion_result = convert_nested_datetime_param(
            params, "time_frame", "to", default_timezone="UTC"
        )
        if "error" in conversion_result:
            return {
                "elicitation_needed": True,
                "reason": "invalid_time_params",
                "api_error": [conversion_result["error"]],
                "message": conversion_result["error"],
            }
        if conversion_result["converted"]:
            params["time_frame"] = conversion_result["params"]["time_frame"]

        # Extract parameters
        time_frame = params.get("time_frame")
        metrics = params.get("metrics")
        tag_filter_expression = params.get("tag_filter_expression")
        group = params.get("group")
        order = params.get("order")
        pagination = params.get("pagination")
        include_internal = params.get("include_internal")
        include_synthetic = params.get("include_synthetic")

        # Route to Application Call Group Metrics
        logger.info(f"Routing to Application Call Group Metrics | operation={operation}")

        result = await self.app_call_group_client.get_grouped_calls_metrics(
            metrics=metrics,
            time_frame=time_frame,
            group=group,
            tag_filter_expression=tag_filter_expression,
            include_internal=include_internal,
            include_synthetic=include_synthetic,
            order=order,
            pagination=pagination,
            ctx=ctx,
            resource_type="metrics", tool_name="manage_applications",
        )

        return {
            "resource_type": "metrics",
            "operation": operation,
            "results": result
        }

    async def _handle_alert_config(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle Application Alert Config operations."""
        valid_operations = [
            "find_active", "find_versions", "find", "create", "update",
            "delete", "enable", "disable", "restore", "update_baseline"
        ]

        # Pagination navigation (shared, stateless - src/core/pagination.py):
        # page_N / next / previous / go_to_page re-run find_active on that page.
        operation, params, _nav_error = apply_navigation(operation, params, "find_active")
        if _nav_error:
            return _nav_error

        if operation not in valid_operations:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid alert_config operation",
                        "expected": valid_operations
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'alert_config'. Valid operations: {valid_operations}"
            }

        # Extract parameters
        application_id = params.get("application_id")
        application_name = params.get("application_name")
        id = params.get("id")
        alert_ids = params.get("alert_ids")
        valid_on = params.get("valid_on")
        created = params.get("created")
        payload = params.get("payload")

        # If application_name is provided but not application_id, resolve it
        if application_name and not application_id:
            logger.info(f"Resolving application name '{application_name}' to application ID")
            app_id_result = await self._get_application_id_by_name(application_name, ctx)

            if "error" in app_id_result:
                return {
                    "resource_type": "alert_config",
                    "operation": operation,
                    "error": f"Failed to resolve application name '{application_name}': {app_id_result['error']}"
                }

            application_id = app_id_result.get("application_id")
            logger.info(f"Resolved application '{application_name}' to ID: {application_id}")

        # Route to the alert config client
        result = await self.app_alert_config_client.execute_alert_config_operation(
            operation=operation,
            application_id=application_id,
            id=id,
            alert_ids=alert_ids,
            valid_on=valid_on,
            created=created,
            payload=payload,
            ctx=ctx,
            resource_type="alert_config", tool_name="manage_applications",
            **page_kwargs(params),
        )

        return {
            "resource_type": "alert_config",
            "operation": operation,
            "application_name": application_name,
            "application_id": application_id,
            "results": result
        }

    async def _handle_global_alert_config(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle Global Application Alert Config operations."""
        valid_operations = [
            "find_active", "find_versions", "find", "create", "update",
            "delete", "enable", "disable", "restore"
        ]

        # Pagination navigation (shared, stateless - src/core/pagination.py)
        operation, params, _nav_error = apply_navigation(operation, params, "find_active")
        if _nav_error:
            return _nav_error

        if operation not in valid_operations:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid global_alert_config operation",
                        "expected": valid_operations
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'global_alert_config'. Valid operations: {valid_operations}"
            }

        # Extract parameters
        application_id = params.get("application_id")
        application_name = params.get("application_name")
        id = params.get("id")
        alert_ids = params.get("alert_ids")
        valid_on = params.get("valid_on")
        created = params.get("created")
        payload = params.get("payload")

        # If application_name is provided but not application_id, resolve it
        if application_name and not application_id:
            logger.info(f"Resolving application name '{application_name}' to application ID")
            app_id_result = await self._get_application_id_by_name(application_name, ctx)

            if "error" in app_id_result:
                return {
                    "resource_type": "global_alert_config",
                    "operation": operation,
                    "error": f"Failed to resolve application name '{application_name}': {app_id_result['error']}"
                }

            application_id = app_id_result.get("application_id")
            logger.info(f"Resolved application '{application_name}' to ID: {application_id}")

        # Route to the global alert config client
        result = await self.app_global_alert_config_client.execute_alert_config_operation(
            operation=operation,
            application_id=application_id,
            id=id,
            alert_ids=alert_ids,
            valid_on=valid_on,
            created=created,
            payload=payload,
            ctx=ctx,
            resource_type="global_alert_config", tool_name="manage_applications",
            **page_kwargs(params),
        )

        return {
            "resource_type": "global_alert_config",
            "operation": operation,
            "application_name": application_name,
            "application_id": application_id,
            "results": result
        }

    async def _resolve_application_name(
        self,
        application_name: str,
        resource_subtype: str,
        operation: str,
        ctx
    ) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Resolve application name to application ID. Returns (resolved_id, error_response)."""
        logger.info(f"Resolving application name '{application_name}' to application config ID")

        all_configs_result = await self.app_settings_client.execute_settings_operation(
            operation="get_all",
            resource_subtype="application",
            ctx=ctx
        )

        if not isinstance(all_configs_result, list):
            error = {
                "resource_type": "settings",
                "resource_subtype": resource_subtype,
                "operation": operation,
                "error": "Failed to retrieve application perspectives for name resolution"
            }
            return None, error

        for config in all_configs_result:
            if not isinstance(config, dict):
                continue

            config_label = config.get('label', '')
            config_id = config.get('id', '')

            if config_label.lower() == application_name.lower() and config_id:
                logger.info(f"Found application config '{config_label}' with ID: {config_id}")
                return config_id, None

        error = {
            "resource_type": "settings",
            "resource_subtype": resource_subtype,
            "operation": operation,
            "error": f"No application perspective found with name '{application_name}'"
        }
        return None, error

    async def _handle_settings(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle Application Settings operations."""
        valid_operations = [
            "get_all", "get", "create", "update", "delete"
        ]

        # Pagination navigation (shared, stateless - src/core/pagination.py):
        # page_N / next / previous / go_to_page re-run get_all on that page.
        _requested_op = operation
        operation, params, _nav_error = apply_navigation(operation, params, "get_all")
        if _nav_error:
            return _nav_error
        if operation != _requested_op:
            params.setdefault("resource_subtype", "application")

        if operation not in valid_operations:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid settings operation",
                        "expected": valid_operations
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'settings'. Valid operations: {valid_operations}"
            }

        # Extract parameters
        resource_subtype = params.get("resource_subtype")
        settings_id = params.get("id")
        application_name = params.get("application_name")
        payload = params.get("payload")
        request_body = params.get("request_body")

        valid_subtypes = ["application", "endpoint", "service", "manual_service"]

        if resource_subtype not in valid_subtypes:
            return {
                "elicitation_needed": True,
                "reason": f"Invalid or missing resource_subtype: {resource_subtype!r}",
                "api_error": [
                    f"resource_subtype: {resource_subtype!r} is not valid. "
                    f"Must be one of: {valid_subtypes}"
                ],
                "message": (
                    f"'resource_subtype' value {resource_subtype!r} is not valid. "
                    f"Accepted values are: {valid_subtypes}."
                ),
            }

        # If application_name is provided, resolve it to application ID
        if resource_subtype == "application" and operation == "get" and application_name and not settings_id:
            settings_id, error = await self._resolve_application_name(
                application_name=application_name,
                resource_subtype=resource_subtype,
                operation=operation,
                ctx=ctx
            )
            if error:
                return error

        # Route to the settings client
        # Note: payload validation for create/update is handled inside the service layer
        # (_validate_settings_payload is called in each _add_* / _update_* method).
        # No duplicate validation here.
        result = await self.app_settings_client.execute_settings_operation(
            operation=operation,
            resource_subtype=resource_subtype,
            id=settings_id,
            payload=payload,
            request_body=request_body,
            ctx=ctx,
            resource_type="settings", tool_name="manage_applications",
        )

        response = {
            "resource_type": "settings",
            "resource_subtype": resource_subtype,
            "operation": operation,
            "application_name": application_name if application_name else None,
            "resolved_id": settings_id if application_name else None,
            "results": result
        }

        # get_all is paginated only when page/page_size is requested (opt-in)
        if (
            operation == "get_all"
            and isinstance(result, list)
            and (params.get("page") is not None or params.get("page_size") is not None)
        ):
            page_items, pagination = paginate(
                result,
                params.get("page"),
                params.get("page_size"),
                max_page_size=100,
                sort_key=stable_sort_key,
                list_id=f"{resource_subtype}_settings",
            )
            response["results"] = page_items
            response["pagination"] = pagination

        return response

    async def _get_application_id_by_name(
        self,
        application_name: str,
        ctx
    ) -> Dict[str, Any]:
        """
        Get application ID by application name using the Application Resources API.

        Args:
            application_name: Name of the application
            ctx: MCP context

        Returns:
            Dictionary with application_id or error
        """
        try:
            from datetime import datetime

            logger.info(f"Resolving application name '{application_name}' to application ID using Application Resources API")

            # Set time range (last hour)
            to_time = int(datetime.now().timestamp() * 1000)
            window_size = 60 * 60 * 1000  # 1 hour

            # Use the app_resources_client to get applications
            result = await self.app_resources_client._get_applications_internal(
                name_filter=application_name,
                window_size=window_size,
                to_time=to_time,
                ctx=ctx
            )

            logger.debug(f"Application Resources API result: {result}")

            # Extract items from the result
            items = result.get('items', []) if isinstance(result, dict) else []

            if not items:
                logger.warning(f"No application found with name filter '{application_name}'")
                return {"error": f"No application found with name '{application_name}'"}

            # Find exact match (case-insensitive)
            for item in items:
                if isinstance(item, dict):
                    label = item.get('label', '')
                    app_id = item.get('id', '')

                    if label.lower() == application_name.lower() and app_id:
                        logger.info(f"Found application '{label}' with ID: {app_id}")
                        return {
                            "application_id": app_id,
                            "application_name": label
                        }

            # If no exact match, return the first result
            first_item = items[0]
            if isinstance(first_item, dict):
                label = first_item.get('label', '')
                app_id = first_item.get('id', '')

                if app_id:
                    logger.info(f"Using closest match: '{label}' with ID: {app_id}")
                    return {
                        "application_id": app_id,
                        "application_name": label
                    }

            return {"error": f"No application found with name '{application_name}'"}

        except Exception as e:
            logger.error(f"Error fetching application ID: {e}", exc_info=True)
            return {"error": f"Failed to fetch application ID: {e!s}"}

    def _convert_analyze_time_params(
        self, operation: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Convert datetime strings in analyze params in-place.
        Returns an error dict if conversion fails, otherwise None.
        """
        # Convert datetime string for timeFrame.to in payload
        payload = params.get("payload")
        if isinstance(payload, dict):
            time_frame = payload.get("timeFrame")
            if isinstance(time_frame, dict):
                # Guard: "to": 0 means Unix epoch (1970), not "now". Strip it so the
                # API defaults to the current server time, which is the correct behaviour
                # when the user asks for a relative window like "last 1 hour".
                if time_frame.get("to") == 0:
                    del time_frame["to"]
                conversion_result = convert_nested_datetime_param(
                    payload, "timeFrame", "to", default_timezone="UTC"
                )
                if "error" in conversion_result:
                    return {"error": conversion_result["error"], "operation": operation, "resource_type": "analyze"}
                params["payload"] = conversion_result["params"]

        # Convert datetime string for ingestionTime in get_trace_details
        if operation == "get_trace_details" and "ingestionTime" in params:
            conversion_result = convert_datetime_param(
                params["ingestionTime"],
                "ingestionTime",
                default_timezone="UTC",
                output_unit="seconds"
            )
            if "error" in conversion_result:
                return {"error": conversion_result["error"], "operation": operation, "resource_type": "analyze"}
            if conversion_result["converted"]:
                params["ingestionTime"] = conversion_result["value"]

        return None

    async def _handle_analyze(
        self, operation: str, params: Dict[str, Any], ctx
    ) -> Dict[str, Any]:
        """Handle Application Analyze operations."""
        valid_operations = ["get_all_traces", "get_trace_details", "get_trace_groups"]

        if operation not in valid_operations:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid analyze operation",
                        "expected": valid_operations
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'analyze'. Valid operations: {valid_operations}"
            }

        time_error = self._convert_analyze_time_params(operation, params)
        if time_error:
            return time_error

        # Route to the analyze client with params
        result = await self.app_analyze_client.execute_analyze_operation(
            operation=operation, params=params, ctx=ctx,
            resource_type="analyze", tool_name="manage_applications",
        )

        return {
            "resource_type": "analyze",
            "operation": operation,
            "results": result,
        }

    async def _handle_catalog(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle Application Catalog operations."""
        valid_operations = ["get_tag_catalog", "get_metric_catalog"]

        if operation not in valid_operations:
            return {
                "elicitation_needed": True,
                "reason": f"Invalid operation {operation!r} for catalog",
                "api_error": [
                    f"operation: {operation!r} is not valid for resource_type 'catalog'. "
                    f"Must be one of: {valid_operations}"
                ],
                "message": (
                    f"operation {operation!r} is not valid for resource_type 'catalog'. "
                    f"Accepted values are: {valid_operations}."
                ),
            }

        # Extract parameters
        use_case = params.get("use_case")
        data_source = params.get("data_source")
        var_from = params.get("var_from")

        # Route to the appropriate catalog method
        if operation == "get_tag_catalog":
            logger.info("Routing to Application Tag Catalog")
            result = await self.app_catalog_client.get_application_tag_catalog(
                use_case=use_case,
                data_source=data_source,
                var_from=var_from,
                ctx=ctx,
                resource_type="catalog", tool_name="manage_applications",
            )

            return {
                "resource_type": "catalog",
                "operation": operation,
                "results": result
            }

        elif operation == "get_metric_catalog":
            logger.info("Routing to Application Metric Catalog")
            result = await self.app_catalog_client.get_application_metric_catalog(
                ctx=ctx,
                resource_type="catalog", tool_name="manage_applications",
            )

            return {
                "resource_type": "catalog",
                "operation": operation,
                "results": result
            }

        return {
            "elicitation_needed": True,
            "reason": "invalid_operation",
            "api_error": [
                {
                    "field": "operation",
                    "issue": f"'{operation}' is not a valid catalog operation",
                    "expected": valid_operations
                }
            ],
            "message": f"Invalid operation '{operation}' for resource_type 'catalog'. Valid operations: {valid_operations}"
        }

    async def _get_error_messages_by_application_name(
        self, params: Dict[str, Any], ctx
    ) -> Dict[str, Any]:
        """List the erroneous endpoints of an application for a time range.

        Uses POST /api/application-monitoring/analyze/call-groups (via
        ``query_call_groups``) filtered to erroneous inbound calls of the application
        (``call.inbound_of_application``, ``call.erroneous``), grouped by ``endpoint.name``,
        ordered by ``erroneousCalls`` (SUM) descending.
        """
        operation = "get_error_messages_by_application_name"
        app_name = params.get("application_name")
        app_id = params.get("application_id")
        if not app_name and not app_id:
            return {
                "error": (
                    f"{operation} requires 'application_name' or 'application_id' in params. "
                    "For next/previous/page_N, use pagination.next_operation / previous_operation "
                    "from the last Error messages response."
                ),
                "operation": operation,
            }

        # Accept either a name or an Instana application ID (the ID may also arrive in
        # application_name). Try the name first, then fall back to an ID lookup.
        resolved: Dict[str, Any] = {}
        if app_name:
            resolved = await self._get_application_id_by_name(app_name, ctx)
        if "error" in resolved or not resolved:
            candidate_id = app_id or app_name
            config = await self.app_settings_client.execute_settings_operation(
                operation="get", resource_subtype="application", id=candidate_id, ctx=ctx,
                resource_type="settings", tool_name="manage_applications",
            )
            if isinstance(config, dict) and config.get("label"):
                resolved = {"application_id": candidate_id, "application_name": config["label"]}
            elif not resolved:
                return {
                    "error": f"No application found with id '{candidate_id}'",
                    "operation": operation,
                }
        if "error" in resolved:
            return resolved
        resolved_app_name = resolved["application_name"]

        # Time range: a phrase such as "last 5 minutes" / "yesterday" / "previous week".
        # An explicit window_size (ms) still works; with neither, default to the last hour.
        time_range = params.get("time_range")
        timezone = params.get("timezone")
        if time_range:
            _tz_error = invalid_timezone_error(timezone)
            if _tz_error:
                return {**_tz_error, "operation": operation}
            resolved_range = resolve_time_range(time_range, timezone)
            if resolved_range is None:
                return {
                    "error": f"Unsupported time_range '{time_range}'.",
                    "operation": operation,
                    "valid_time_ranges": list(_ROLLING_TIME_RANGES) + list(_CALENDAR_TIME_RANGES),
                    "hint": "Use one of valid_time_ranges (or 'last N minutes/hours/days', at most 31 days).",
                }
            time_frame, time_range_label = resolved_range
        elif params.get("window_size"):
            time_frame = {"to": int(_time.time() * 1000), "windowSize": int(params["window_size"])}
            time_range_label = f"last {round(time_frame['windowSize'] / _MS_HOUR, 2)} hours"
        else:
            time_frame, time_range_label = cast(
                Tuple[Dict[str, int], str], resolve_time_range(DEFAULT_ERROR_TIME_RANGE)
            )

        # Call groups, grouped by endpoint: one row per endpoint with its erroneous-call count.
        result = await self.app_call_group_client.query_call_groups(
            payload={
                "tagFilterExpression": {
                    "type": "EXPRESSION",
                    "logicalOperator": "AND",
                    "elements": [
                        {"type": "TAG_FILTER", "name": "call.inbound_of_application", "operator": "EQUALS",
                         "entity": "NOT_APPLICABLE", "value": resolved_app_name},
                        {"type": "TAG_FILTER", "name": "call.erroneous", "operator": "EQUALS",
                         "entity": "NOT_APPLICABLE", "value": True},
                    ],
                },
                "metrics": [
                    {"metric": "erroneousCalls", "aggregation": "SUM"},
                ],
                "includeInternal": True,
                "includeSynthetic": True,
                "timeFrame": time_frame,
                "order": {"by": "erroneousCalls", "direction": "DESC"},
                "group": {"groupbyTag": "endpoint.name", "groupbyTagEntity": "DESTINATION"},
            },
            max_items=_ERROR_TRACE_FETCH_LIMIT,
            ctx=ctx,
        )

        raw_items = result.get("items") if isinstance(result, dict) else None
        if not isinstance(raw_items, list):
            err = result.get("error") if isinstance(result, dict) else None
            return {
                "error": err or "Unexpected response while retrieving error call groups",
                "operation": operation,
                "application_name": resolved_app_name,
            }

        def _metric_value(metrics: Any, prefix: str) -> Optional[float]:
            # Keys look like "erroneousCalls.sum" (optionally ".<granularity>"); value is [[timestamp, value]].
            if not isinstance(metrics, dict):
                return None
            series = next((v for k, v in metrics.items() if k.startswith(prefix + ".")), None)
            if series and isinstance(series[0], list) and len(series[0]) >= 2:
                return series[0][1]
            return None

        errors = []
        for _it in raw_items:
            if not isinstance(_it, dict):
                continue
            _erroneous = _metric_value(_it.get("metrics"), "erroneousCalls")
            errors.append({
                "endpoint": str(_it.get("name") or "").strip(),
                "erroneous_calls": int(_erroneous) if _erroneous is not None else None,
            })
        total_hits = result.get("totalHits") if isinstance(result, dict) else None
        truncated = bool(result.get("canLoadMore")) if isinstance(result, dict) else False

        page_items, pagination_meta = paginate(
            errors,
            params.get("page_number") or params.get("page") or 1,
            params.get("page_size"),
            list_id="application_error_messages",
        )
        # Own navigation prefix + application name (+ time range) so next/previous work statelessly.
        _nav_suffix = f":{resolved_app_name}" + (f"|{time_range}" if time_range else "")
        for _k in ("next_operation", "previous_operation"):
            if pagination_meta.get(_k):
                pagination_meta[_k] = f"error_{pagination_meta[_k]}{_nav_suffix}"
        nav_params = {"application_name": resolved_app_name}
        if time_range:
            nav_params["time_range"] = time_range
            if timezone:
                nav_params["timezone"] = timezone
        elif params.get("window_size"):
            nav_params["window_size"] = params["window_size"]
        pagination_meta["nav_params"] = nav_params

        response = {
            "resource_type": "resources",
            "operation": operation,
            "application_name": resolved_app_name,
            "time_range": time_range_label,
            "total_hits": total_hits,
            "results": {"items": page_items},
            "pagination": pagination_meta,
        }
        if truncated:
            response["note"] = (
                f"More than {_ERROR_TRACE_FETCH_LIMIT} erroneous endpoints matched; only the most recent "
                f"{len(errors)} are listed. Narrow the time range to see the rest."
            )
        if page_items:
            _start = (pagination_meta["page"] - 1) * pagination_meta["page_size"] + 1
            _lines = []
            for _i, _e in enumerate(page_items, start=_start):
                _label = " ".join(_e["endpoint"].split())
                if len(_label) > 200:
                    _label = _label[:200] + "…"
                _suffix = f" — {_e['erroneous_calls']} erroneous calls" if _e.get("erroneous_calls") is not None else ""
                _lines.append(f"{_i}. {_label}{_suffix}")
            _end = _start + len(page_items) - 1
            _total = pagination_meta.get("total_items", len(errors))
            _footer = (
                f"Showing {_start}-{_end} of {_total} erroneous endpoints "
                f"(page {pagination_meta['page']} of {pagination_meta.get('total_pages', 1)}, {time_range_label})."
            )
            _nav = [w for w, on in (
                ("next", pagination_meta.get("has_more")),
                ("previous", pagination_meta.get("has_previous")),
            ) if on]
            if _nav:
                _footer += f" Reply {', '.join(_nav)}, or page N to navigate."
            response["display_markdown"] = "\n".join(_lines) + "\n\n" + _footer
            response["display_instruction"] = (
                "Show the user the 'display_markdown' exactly as-is under the 'Application error "
                "messages' header, including the final 'Showing ...' line with the total and navigation "
                "hint. Do not drop that line, and do not invent or reword entries. When the user replies "
                "next / previous / page N, call this tool again with operation = pagination.next_operation / "
                "previous_operation (or 'error_page_N:<application_name>[|<time_range>]')."
            )
        return response

    async def _handle_resources(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle Application Resources operations."""
        # ── Error-message list navigation: "error_page_N:<application_name>" ──
        # get_error_messages_by_application_name is paginated separately from the services
        # list, so its next/previous operations use their own prefix to avoid ambiguity.
        _err_nav = re.match(r"^error_page_(\d+)(?::(.+))?$", (operation or "").strip(), re.IGNORECASE)
        if _err_nav:
            operation = "get_error_messages_by_application_name"
            params["page_number"] = int(_err_nav.group(1))
            # The time range rides along after a "|": "error_page_2:<application_name>|<time_range>".
            _nav_app, _, _nav_range = (_err_nav.group(2) or "").partition("|")
            if _nav_app.strip() and not params.get("application_name"):
                params["application_name"] = _nav_app.strip()
            if _nav_range.strip() and not params.get("time_range"):
                params["time_range"] = _nav_range.strip()
                
        valid_operations = [
            "get_application_endpoints",
            "get_application_services",
            "get_applications",
            "get_error_messages_by_application_name",
            "get_services",
        ]

        if operation not in valid_operations:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid resources operation",
                        "expected": valid_operations
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'resources'. Valid operations: {valid_operations}"
            }

        try:
            if operation == "get_error_messages_by_application_name":
                return await self._get_error_messages_by_application_name(params, ctx)

            # Extract all parameters
            application_id = params.get("application_id")
            service_id = params.get("service_id")
            endpoint_id = params.get("endpoint_id")
            name_filter = params.get("name_filter")
            types = params.get("types")
            technologies = params.get("technologies")
            application_boundary_scope = params.get("application_boundary_scope")
            include_snapshot_ids = params.get("include_snapshot_ids")

            # Route to the resources client dispatcher
            result = await self.app_resources_client.execute_resources_operation(
                operation=operation,
                application_id=application_id,
                service_id=service_id,
                endpoint_id=endpoint_id,
                name_filter=name_filter,
                types=types,
                technologies=technologies,
                application_boundary_scope=application_boundary_scope,
                include_snapshot_ids=include_snapshot_ids,
                ctx=ctx,
                resource_type="resources", tool_name="manage_applications",
            )

        except Exception as e:
            logger.error(
                "[manage_applications] _handle_resources error: operation=%s error=%s",
                operation, e, exc_info=True
            )
            return {"error": f"Resources operation failed: {e!s}", "operation": operation}

        return {
            "resource_type": "resources",
            "operation": operation,
            "results": result
        }
