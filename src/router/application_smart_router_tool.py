"""
Smart Router Tool

This module provides a unified MCP tool that routes queries to the appropriate
application-specific tools for Instana monitoring.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.timestamp_utils import (
    convert_datetime_param,
    convert_nested_datetime_param,
)
from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)


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

Resource Types:
    - "metrics": Query application metrics, services, and endpoints
    - "alert_config": Manage application-specific alert configurations
    - "global_alert_config": Manage global application alert configurations
    - "settings": Manage application configurations
    - "catalog": Access application tag and metric catalog information
    - "resources": Query application resources, services, endpoints
    - "analyze": Analyze application traces and calls

CRITICAL WORKFLOW - ALWAYS FOLLOW THIS ORDER:
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
    params: {application_id OR application_name, id, alert_ids, valid_on, created, payload}

GLOBAL_ALERT_CONFIG (resource_type="global_alert_config"):
    operations: find_active, find_versions, find, create, update, delete, enable, disable, restore
    params: {application_id OR application_name, id, alert_ids, valid_on, created, payload}

SETTINGS (resource_type="settings"):
    operations: get_all, get, create, update, delete
    params: {resource_subtype, id, application_name, service_name, service_id, payload, request_body}
    resource_subtypes: "application"

    Creating application (resource_subtype="application", operation="create"):
    REQUIRED: label | OPTIONAL: scope, boundaryScope, accessRules, tagFilterExpression
    Minimal: params={"resource_subtype": "application", "payload": {"label": "My App"}}

RESOURCES (resource_type="resources"):
    operations: get_applications, get_services, get_application_services, get_application_endpoints
    params: {application_id, service_id, endpoint_id, name_filter, types, technologies, application_boundary_scope, include_snapshot_ids}

    get_applications - Get application perspectives
        params: {name_filter, application_boundary_scope}
        Returns: Paginated list of applications with their configurations and metadata

    get_services - Get all services for application monitoring
        params: {name_filter, include_snapshot_ids}
        Returns: Paginated list of services across all applications

    get_application_services - Get services for a specific application perspective
        params: {application_id, service_id, name_filter, application_boundary_scope, include_snapshot_ids}
        Returns: Paginated services filtered by application context

    get_application_endpoints - Get endpoints for an application service
        params: {application_id, service_id, endpoint_id, name_filter, types, technologies, application_boundary_scope}
        Returns: Paginated endpoints with type and technology metadata

CATALOG (resource_type="catalog"):
    operations: get_tag_catalog, get_metric_catalog
    params: {use_case, data_source, var_from}

    get_metric_catalog - Get application metrics catalog with metadata (metricId, label, aggregations, beaconTypes)
    get_tag_catalog - Get valid tag names for use_case and data_source
        Valid use_case: "GROUPING", "FILTERING", "SERVICE_MAPPING", "SMART_ALERTS"
        Valid data_source: "CALLS", "TRACES"

ANALYZE (resource_type="analyze"):
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
    resource_type="metrics", operation="get_grouped_calls_metrics", params={"metrics": [{"metric": "calls", "aggregation": "SUM"}, {"metric": "latency", "aggregation": "MEAN"}], "tag_filter_expression": {"type": "TAG_FILTER", "name": "application.name", "operator": "EQUALS", "entity": "DESTINATION", "value": "All Services"}, "group": {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}, "time_frame": {"to": 1710658800000, "windowSize": 3600000}, "order": {"by": "calls", "direction": "DESC"}, "pagination": {"page": 1, "pageSize": 50}, "include_internal": False, "include_synthetic": False}

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
    resource_type="settings", operation="order", params={"resource_subtype": "application", "request_body": ["config-1", "config-2", "config-3"]}

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

        return {
            "resource_type": "settings",
            "resource_subtype": resource_subtype,
            "operation": operation,
            "application_name": application_name if application_name else None,
            "resolved_id": settings_id if application_name else None,
            "results": result
        }

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

    async def _handle_resources(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle Application Resources operations."""
        valid_operations = [
            "get_application_endpoints",
            "get_application_services",
            "get_applications",
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

        return {
            "resource_type": "resources",
            "operation": operation,
            "results": result
        }
