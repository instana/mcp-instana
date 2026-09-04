"""
Smart Router Tool for Website Monitoring

This module provides a unified MCP tool that routes website monitoring queries
to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, List, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.timestamp_utils import convert_nested_datetime_param
from src.core.utils import (
    WEBSITE_BEACON_TYPE_MAP,
    BaseInstanaClient,
    normalize_beacon_type,
    register_as_tool,
)
from src.core.validation import (
    VALID_WEBSITE_BEACON_TYPES,
    StructureValidator,
)

logger = logging.getLogger(__name__)

# Define valid operations for each resource type at module level
ANALYZE_VALID_OPERATIONS = ["get_beacon_groups", "get_beacons"]
CATALOG_VALID_OPERATIONS = ["get_metrics", "get_tag_catalog"]
CONFIGURATION_VALID_OPERATIONS = ["get_all", "get"]
ADVANCED_CONFIG_VALID_OPERATIONS = ["get_geo_config", "get_ip_masking", "get_geo_rules"]
ALERT_VALID_OPERATIONS = ["find_active_website_alert_configs", "find_website_alert_config"]

# Define parameter key constants to avoid typos
PARAM_METRICS = "metrics"
PARAM_GROUP = "group"
PARAM_TAG_FILTER_EXPRESSION = "tag_filter_expression"
PARAM_TIME_FRAME = "time_frame"
PARAM_BEACON_TYPE = "beacon_type"
PARAM_FILL_TIME_SERIES = "fill_time_series"
PARAM_PAGINATION = "pagination"
PARAM_ORDER = "order"
PARAM_USE_CASE = "use_case"
PARAM_WEBSITE_ID = "website_id"
PARAM_WEBSITE_NAME = "website_name"
PARAM_NAME = "name"
PARAM_PAYLOAD = "payload"
PARAM_ALERT_ID = "id"
PARAM_VALID_ON = "valid_on"
PARAM_ALERT_IDS = "alert_ids"


class WebsiteSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for website monitoring operations.
    Routes queries to Website Analyze tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Smart Router Website MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
        from src.website.website_alert import WebsiteAlertMCPTools
        from src.website.website_analyze import WebsiteAnalyzeMCPTools
        from src.website.website_catalog import WebsiteCatalogMCPTools
        from src.website.website_configuration import WebsiteConfigurationMCPTools

        # Initialize the website clients
        self.website_analyze_client = WebsiteAnalyzeMCPTools(read_token, base_url)
        self.website_catalog_client = WebsiteCatalogMCPTools(read_token, base_url)
        self.website_configuration_client = WebsiteConfigurationMCPTools(read_token, base_url)
        self.website_alert_client = WebsiteAlertMCPTools(read_token, base_url)

        logger.info("Smart Router Website initialized with Analyze, Catalog, Configuration and Alert tools")

    @register_as_tool(
        title="Manage Instana Website Resources",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        description="""Unified Instana website resource manager for beacon monitoring, catalog, configuration and alert operations.

Resource Types:
    - "analyze": Query website beacon data with grouping or filtering
    - "catalog": Get available metrics and tags for website monitoring
    - "configuration": Get website configurations
    - "advanced_config": Retrieve advanced configurations (geo-location, IP masking, geo rules) - READ ONLY
    - "alert": Get mobile app alert configurations

CRITICAL WORKFLOW:
    BEFORE calling analyze operations, you MUST call get_tag_catalog to get valid tag names.
    Default beacon_type: "PAGELOAD" | Default use_case: get_beacon_groups="GROUPING", get_beacons="FILTERING"

ANALYZE (resource_type="analyze"):
    operations: get_beacon_groups, get_beacons
    params: {metrics, group, tag_filter_expression, time_frame, beacon_type, fill_time_series, order, pagination}

    Aggregations: SUM, MEAN, MAX, MIN, P25, P50, P75, P90, P95, P98, P99, P99_9, P99_99, DISTINCT_COUNT, SUM_POSITIVE, PER_SECOND, INCREASE
    Operators: EQUALS, NOT_EQUAL, CONTAINS, NOT_CONTAIN, STARTS_WITH, ENDS_WITH, NOT_STARTS_WITH, NOT_ENDS_WITH, GREATER_THAN, GREATER_OR_EQUAL_THAN, LESS_THAN, LESS_OR_EQUAL_THAN, NOT_EMPTY, IS_EMPTY, NOT_BLANK, IS_BLANK, REGEX_MATCH

    tag_filter_expression: CRITICAL - Entity field REQUIRED for ALL tag filters. ALWAYS set "entity": "NOT_APPLICABLE" for website beacon tags.
    time_frame: {"to": <timestamp_or_datetime>, "windowSize": <milliseconds>} - Default: 3600000 (1 hour)
        to: Unix timestamp (ms) OR datetime string (e.g., "19 March 2026, 2:47 PM|IST")

    Examples:
        metrics: [{"metric": "beaconCount", "aggregation": "SUM"}, {"metric": "onLoadTime", "aggregation": "P95"}]
        tag_filter_expression: {"type": "TAG_FILTER", "name": "beacon.page.name", "operator": "CONTAINS", "entity": "NOT_APPLICABLE", "value": "checkout"}

    get_beacon_groups - Use for grouped/aggregated data (e.g., "beacon count per page")
    get_beacons - Use for individual beacon data (e.g., "list all page load beacons")

CATALOG (resource_type="catalog"):
    operations: get_metrics, get_tag_catalog
    params: {beacon_type, use_case}

    get_metrics - Get website metrics catalog with necessary metadata for query planning (metricId, label, description, formatter, aggregations, beaconTypes). Use returned metricId values exactly; they are authoritative over examples. Use params.view="full" to retrieve raw SDK metadata (rarely needed).
    get_tag_catalog - Get valid tag names for beacon_type and use_case
        Valid beacon_type: "PAGELOAD", "PAGE_CHANGE", "RESOURCELOAD", "CUSTOM", "HTTPREQUEST", "ERROR"
        Valid use_case: "GROUPING", "FILTERING", "SERVICE_MAPPING", "SMART_ALERTS", etc.

CONFIGURATION (resource_type="configuration"):
    operations: get_all, get
    params: {website_id, website_name}

    get_all - List all websites
    get - Get website by ID or name (supports name resolution)

    NOTE: Create, Update, Delete operations are not available.
          Use the Instana UI for website configuration modifications.

ADVANCED_CONFIG (resource_type="advanced_config"):
    operations: get_geo_config, get_ip_masking, get_geo_rules
    params: {website_id, website_name}

    NOTE: These are READ-ONLY operations for retrieving advanced configurations.
          Use the Instana UI for modifications.
          Source map operations are not currently available due to authentication limitations.

    get_geo_config - Get geo-location configuration
        Returns: geoDetailRemoval setting and geoMappingRules array
    get_ip_masking - Get IP masking configuration
        Returns: ipMasking setting (DEFAULT, ANONYMIZE_IP, etc.)
    get_geo_rules - Get custom geo mapping rules
        Returns: Array of geo mapping rules with CIDR ranges and location data

ALERT (resource_type="alert"):
    operations: find_active_website_alert_configs, find_website_alert_config
    params: {website_id, alert_ids, id, valid_on}

    find_active_website_alert_configs - Get all alert configurations for a website
        - website_id: Website ID to get alert configs for (required)
        - alert_ids: Optional list of specific alert IDs to filter (optional)

    find_website_alert_config - Get a specific alert configuration by ID
        - id: Specific alert configuration ID to retrieve (required)
        - valid_on: Unix timestamp (ms) to retrieve the configuration active at that time (optional, default is latest active version)


Args:
    resource_type: "analyze", "catalog", "configuration", "advanced_config", or "alert"
    operation: Specific operation for the resource type
    params: Operation-specific parameters (optional)

Returns:
    Dictionary with results from the appropriate tool

Examples:
    resource_type="catalog", operation="get_tag_catalog", params={"beacon_type": "PAGELOAD", "use_case": "GROUPING"}
    resource_type="analyze", operation="get_beacon_groups", params={"metrics": [{"metric": "beaconCount", "aggregation": "SUM"}], "group": {"groupByTag": "beacon.page.name", "groupbyTagEntity": "NOT_APPLICABLE"}, "time_frame": {"to": "19 March 2026, 2:47 PM|IST", "windowSize": 3600000}, "beacon_type": "PAGELOAD"}
    resource_type="analyze", operation="get_beacons", params={"time_frame": {"to": 1234567890000, "windowSize": 3600000}, "beacon_type": "PAGELOAD", "pagination": {"retrievalSize": 50}}
    resource_type="catalog", operation="get_metrics"
    resource_type="configuration", operation="get_all"
    resource_type="configuration", operation="get", params={"website_name": "robot-shop"}
    resource_type="advanced_config", operation="get_geo_config", params={"website_name": "robot-shop"}
    resource_type="alert", operation="find_active_website_alert_configs", params={"website_id": "website-abc123"}
    resource_type="alert", operation="find_website_alert_config", params={"id": "alert-123", "valid_on": 1234567890000}"""
    )
    async def manage_websites(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Unified Instana website resource manager for beacon monitoring, catalog, and configuration operations."""

        try:
            logger.debug(f"Website Router: resource_type={resource_type}, operation={operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate resource_type
            valid_types = ["analyze", "catalog", "configuration", "advanced_config", "alert"]
            if resource_type not in valid_types:
                return {
                    "elicitation_needed": True,
                    "reason": "invalid_resource_type",
                    "api_error": [
                        {
                            "field": "resource_type",
                            "issue": f"'{resource_type}' is not a valid resource type",
                            "expected": valid_types
                        }
                    ],
                    "message": f"Invalid resource_type '{resource_type}'. Must be one of: {valid_types}"
                }

            # Route to the appropriate resource handler
            if resource_type == "analyze":
                return await self._handle_analyze(operation, params, ctx)
            elif resource_type == "catalog":
                return await self._handle_catalog(operation, params, ctx)
            elif resource_type == "configuration":
                return await self._handle_configuration(operation, params, ctx)
            elif resource_type == "advanced_config":
                return await self._handle_advanced_config(operation, params, ctx)
            elif resource_type == "alert":
                return await self._handle_alert(operation, params, ctx)
            else:
                return {
                    "elicitation_needed": True,
                    "reason": "invalid_resource_type",
                    "api_error": [
                        {
                            "field": "resource_type",
                            "issue": f"Unsupported resource_type: {resource_type}",
                            "expected": ["analyze", "catalog", "configuration", "advanced_config", "alert"]
                        }
                    ],
                    "message": f"Unsupported resource_type '{resource_type}'. Must be one of: analyze, catalog, configuration, advanced_config, alert"
                }

        except Exception as e:
            logger.error(
                f"Error in website smart router: {e} | "
                f"resource_type={resource_type}, operation={operation}, params={params}",
                exc_info=True
            )
            return {
                "error": f"Smart router error: {e!s}",
                "resource_type": resource_type,
                "operation": operation
            }

    async def _handle_analyze(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle website analyze operations."""

        # Validate operation
        if operation not in ANALYZE_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid analyze operation",
                        "expected": ANALYZE_VALID_OPERATIONS
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'analyze'. Valid operations: {ANALYZE_VALID_OPERATIONS}"
            }

        # Extract individual parameters from params dict
        metrics = params.get(PARAM_METRICS)
        group = params.get(PARAM_GROUP)
        tag_filter_expression = params.get(PARAM_TAG_FILTER_EXPRESSION)
        time_frame = params.get(PARAM_TIME_FRAME)
        beacon_type = params.get(PARAM_BEACON_TYPE)
        fill_time_series = params.get(PARAM_FILL_TIME_SERIES, True)
        pagination = params.get(PARAM_PAGINATION)
        order = params.get(PARAM_ORDER)

        # Convert datetime string to timestamp for time_frame.to if provided
        conversion_result = convert_nested_datetime_param(
            params,
            PARAM_TIME_FRAME,
            "to",
            default_timezone="UTC"
        )

        if "error" in conversion_result:
            return {
                "elicitation_needed": True,
                "reason": "invalid_time_params",
                "api_error": [
                    {
                        "field": "time_frame.to",
                        "issue": conversion_result["error"],
                        "expected": "Unix timestamp (ms) or datetime string with timezone (e.g., '10 March 2026, 2:00 PM|IST')"
                    }
                ],
                "message": conversion_result["error"]
            }

        # Update time_frame with converted value if conversion occurred
        if conversion_result["converted"]:
            time_frame = conversion_result["params"][PARAM_TIME_FRAME]

        # --- Pre-flight structural validation: collect ALL errors in one pass ---
        # This prevents invalid payloads from ever reaching the service layer or
        # the API, avoiding unnecessary API calls and rate-limit exhaustion.
        _sv_errors: List[str] = []
        for _sv_fn, _sv_val, _sv_kw in [
            (StructureValidator.validate_beacon_type, beacon_type,
                {"valid_types": VALID_WEBSITE_BEACON_TYPES}),
            (StructureValidator.validate_metrics_array, metrics, {"required": False}),
            (StructureValidator.validate_group, group, {"required": False}),
            (StructureValidator.validate_tag_filter_expression, tag_filter_expression, {}),
            (StructureValidator.validate_time_frame, time_frame, {}),
            (StructureValidator.validate_order, order, {}),
            (StructureValidator.validate_pagination, pagination, {}),
        ]:
            _sv_res = _sv_fn(_sv_val, **_sv_kw)
            if _sv_res:
                _sv_errors.extend(_sv_res["api_error"])
        if _sv_errors:
            return {
                "elicitation_needed": True,
                "reason": f"analyze '{operation}' payload has {len(_sv_errors)} validation problem(s)",
                "api_error": _sv_errors,
                "message": (
                    f"The analyze '{operation}' payload has {len(_sv_errors)} problem(s). "
                    "Correct all issues below and retry:\n"
                    + "\n".join(f"  - {e}" for e in _sv_errors)
                ),
            }
        # --- End pre-flight validation ---

        # Route to specific operation
        if operation == "get_beacon_groups":
            logger.debug(
                f"Routing to Website Beacon Groups | "
                f"metrics={metrics}, group={group}, beacon_type={beacon_type}, "
                f"time_frame={time_frame}, fill_time_series={fill_time_series}",
                f"tag_filter_expression={tag_filter_expression}",
                f"order={order}, pagination: {pagination}"
            )

            # Pass individual parameters to the client
            _routing = {"resource_type": "analyze", "tool_name": "manage_websites"}
            result = await self.website_analyze_client.get_website_beacon_groups(
                metrics=metrics,
                group=group,
                tag_filter_expression=tag_filter_expression,
                time_frame=time_frame,
                beacon_type=beacon_type,
                fill_time_series=fill_time_series,
                order=order,
                pagination=pagination,
                ctx=ctx, **_routing,
            )

        elif operation == "get_beacons":
            logger.debug(
                f"Routing to Website Beacons | "
                f"metrics={metrics}, group={group}, beacon_type={beacon_type}, "
                f"time_frame={time_frame}, fill_time_series={fill_time_series}",
                f"tag_filter_expression={tag_filter_expression}",
                f"order={order}, pagination: {pagination}"
            )

            # Pass individual parameters to the client
            _routing = {"resource_type": "analyze", "tool_name": "manage_websites"}
            result = await self.website_analyze_client.get_website_beacons(
                tag_filter_expression=tag_filter_expression,
                time_frame=time_frame,
                beacon_type=beacon_type,
                pagination=pagination,
                ctx=ctx, **_routing,
            )

        # Return structured response
        return {
            "resource_type": "analyze",
            "operation": operation,
            "results": result
        }

    async def _handle_catalog(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
        ) -> Dict[str, Any]:
        """Handle Website catalog operations"""

        # Validate operation
        if operation not in CATALOG_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid catalog operation",
                        "expected": CATALOG_VALID_OPERATIONS
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'catalog'. Valid operations: {CATALOG_VALID_OPERATIONS}"
            }

        #Route to specific operation
        _cat_routing = {"resource_type": "catalog", "tool_name": "manage_websites"}
        if operation == "get_metrics":
            view = (params or {}).get("view", "planner")
            logger.debug(f"Routing to Website Catalog Metrics | view={view}")
            result = await self.website_catalog_client.get_website_catalog_metrics(ctx=ctx, view=view, **_cat_routing)

        elif operation == "get_tag_catalog":
            # Extract required parameters
            beacon_type = params.get(PARAM_BEACON_TYPE)
            use_case = params.get(PARAM_USE_CASE)

            logger.debug(
                f"Routing to Website Tag Catalog | "
                f"beacon_type={beacon_type}, use_case={use_case}"
            )

            # Pre-flight: collect all catalog errors before hitting the API
            _cat_errors = []

            # use_case is required by the API
            if not use_case:
                _cat_errors.append({
                    "field": "use_case",
                    "issue": "use_case is required for get_tag_catalog",
                    "expected": ["GROUPING", "FILTERING", "SERVICE_MAPPING", "SMART_ALERTS"]
                })

            # beacon_type: reject values that belong to mobile app, not website
            if beacon_type is not None and beacon_type not in VALID_WEBSITE_BEACON_TYPES:
                _cat_errors.append({
                    "field": "beacon_type",
                    "issue": f"'{beacon_type}' is not a valid website beacon type",
                    "expected": sorted(VALID_WEBSITE_BEACON_TYPES)
                })

            if _cat_errors:
                return {
                    "elicitation_needed": True,
                    "reason": f"get_tag_catalog has {len(_cat_errors)} invalid parameter(s)",
                    "api_error": _cat_errors,
                    "message": (
                        f"get_tag_catalog has {len(_cat_errors)} problem(s). "
                        "Correct all issues below and retry:\n"
                        + "\n".join(f"  - {e['field']}: {e['issue']}" for e in _cat_errors)
                    )
                }

            # Normalize beacon_type to camelCase format (API expects camelCase)
            normalized_beacon_type = normalize_beacon_type(beacon_type, WEBSITE_BEACON_TYPE_MAP)
            if beacon_type != normalized_beacon_type:
                logger.debug(f"Normalized beacon_type from '{beacon_type}' to '{normalized_beacon_type}'")
                beacon_type = normalized_beacon_type

            # Pass parameters to the client
            result = await self.website_catalog_client.get_website_tag_catalog(
                beacon_type=beacon_type,
                use_case=use_case,
                ctx=ctx, **_cat_routing,
            )

        # Return structured response
        return {
            "resource_type": "catalog",
            "operation": operation,
            "results": result
        }

    async def _handle_configuration(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Handle configuration-related operations for website monitoring.
        """
        if operation not in CONFIGURATION_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid configuration operation",
                        "expected": CONFIGURATION_VALID_OPERATIONS
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'configuration'. Valid operations: {CONFIGURATION_VALID_OPERATIONS}"
            }

        # Extract parameters
        website_id = params.get(PARAM_WEBSITE_ID)
        website_name = params.get(PARAM_WEBSITE_NAME)
        name = params.get(PARAM_NAME)
        payload = params.get(PARAM_PAYLOAD)

        # Route to the configuration client
        logger.info(f"Routing to {operation} [resource_type=configuration, tool_name=manage_websites]")
        result = await self.website_configuration_client.execute_website_operation(
            operation=operation,
            website_id=website_id,
            website_name=website_name,
            name=name,
            payload=payload,
            ctx=ctx,
            resource_type="configuration", tool_name="manage_websites",
        )

        return {
            "resource_type": "configuration",
            "operation": operation,
            "website_name": website_name if website_name else None,
            "website_id": website_id if website_id else None,
            "results": result
        }

    async def _handle_advanced_config(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Handle advanced configuration retrieval operations (read-only).
        Includes geo-location, IP masking, geo mapping rules, and source map configurations.
        """
        if operation not in ADVANCED_CONFIG_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid advanced_config operation",
                        "expected": ADVANCED_CONFIG_VALID_OPERATIONS,
                        "note": "Only GET operations are supported. Use Instana UI for modifications."
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'advanced_config'. Valid operations: {ADVANCED_CONFIG_VALID_OPERATIONS}"
            }

        # Extract parameters
        website_id = params.get(PARAM_WEBSITE_ID)
        website_name = params.get(PARAM_WEBSITE_NAME)

        # Route to the configuration client's advanced config executor
        result = await self.website_configuration_client.execute_advanced_config_operation(
            operation=operation,
            website_id=website_id,
            website_name=website_name,
            ctx=ctx,
            resource_type="advanced_config", tool_name="manage_websites",
        )

        return {
            "resource_type": "advanced_config",
            "operation": operation,
            "website_name": website_name if website_name else None,
            "website_id": website_id if website_id else None,
            "results": result
        }

    async def _handle_alert(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
        ) -> Dict[str, Any]:
        """Handle Website alert operations"""

        # Validate operation
        if operation not in ALERT_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid alert operation",
                        "expected": ALERT_VALID_OPERATIONS
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'alert'. Valid operations: {ALERT_VALID_OPERATIONS}"
            }

        # Initialize result to avoid unbound variable error
        result = None

        #Route to specific operation
        if operation == "find_active_website_alert_configs":
            website_id = params.get(PARAM_WEBSITE_ID)
            alert_ids = params.get(PARAM_ALERT_IDS)

            # Pre-flight: website_id is required
            if not website_id:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "website_id",
                            "issue": "website_id is required for find_active_website_alert_configs",
                            "hint": "Use resource_type='configuration', operation='get_all' to list available website IDs"
                        }
                    ],
                    "message": "Missing required parameter 'website_id'. Use configuration/get_all to list available website IDs."
                }

            logger.debug(f"Routing to find_active_website_alert_configs with website_id={website_id}")
            result = await self.website_alert_client.find_active_website_alert_configs(
                website_id=website_id,
                alert_ids=alert_ids,
                ctx=ctx,
                resource_type="alert", tool_name="manage_websites",
            )
        elif operation == "find_website_alert_config":
            alert_id = params.get(PARAM_ALERT_ID)
            valid_on = params.get(PARAM_VALID_ON)

            # Pre-flight: id is required
            if not alert_id:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "id",
                            "issue": "id is required for find_website_alert_config",
                            "hint": "Use resource_type='alert', operation='find_active_website_alert_configs' to list available alert config IDs"
                        }
                    ],
                    "message": "Missing required parameter 'id'. Use alert/find_active_website_alert_configs to list available IDs."
                }

            logger.debug(f"Routing to find_website_alert_config with id={alert_id}")
            result = await self.website_alert_client.find_website_alert_config(
                id=alert_id,
                valid_on=valid_on,
                ctx=ctx,
                resource_type="alert", tool_name="manage_websites",
            )
        else:
            # This should never happen due to validation above, but handle it gracefully
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"Unhandled operation '{operation}' for alert",
                        "expected": ALERT_VALID_OPERATIONS
                    }
                ],
                "message": f"Unhandled operation '{operation}' for resource_type 'alert'. Valid operations: {ALERT_VALID_OPERATIONS}"
            }

        # Return structured response
        return {
            "resource_type": "alert",
            "operation": operation,
            "results": result
        }
