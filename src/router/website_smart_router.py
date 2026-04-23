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
from src.core.utils import BaseInstanaClient, normalize_beacon_type, register_as_tool

logger = logging.getLogger(__name__)

# Define valid operations for each resource type at module level
ANALYZE_VALID_OPERATIONS = ["get_beacon_groups", "get_beacons"]
CATALOG_VALID_OPERATIONS = ["get_metrics", "get_tag_catalog"]
CONFIGURATION_VALID_OPERATIONS = ["get_all", "get"]
ADVANCED_CONFIG_VALID_OPERATIONS = ["get_geo_config", "get_ip_masking", "get_geo_rules"]

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


class WebsiteSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for website monitoring operations.
    Routes queries to Website Analyze tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Smart Router Website MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
        from src.website.website_analyze import WebsiteAnalyzeMCPTools
        from src.website.website_catalog import WebsiteCatalogMCPTools
        from src.website.website_configuration import WebsiteConfigurationMCPTools

        # Initialize the website clients
        self.website_analyze_client = WebsiteAnalyzeMCPTools(read_token, base_url)
        self.website_catalog_client = WebsiteCatalogMCPTools(read_token, base_url)
        self.website_configuration_client = WebsiteConfigurationMCPTools(read_token, base_url)

        logger.info("Smart Router Website initialized with Analyze, Catalog, and Configuration tools")

    @register_as_tool(
        title="Manage Instana Website Resources",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        description="""Unified Instana website resource manager for beacon monitoring, catalog, and configuration operations.

Resource Types:
    - "analyze": Query website beacon data with grouping or filtering
    - "catalog": Get available metrics and tags for website monitoring
    - "configuration": Get website configurations
    - "advanced_config": Retrieve advanced configurations (geo-location, IP masking, geo rules) - READ ONLY

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
        metrics: [{"metric": "beaconCount", "aggregation": "SUM"}, {"metric": "pageLoadTime", "aggregation": "P95"}]
        tag_filter_expression: {"type": "TAG_FILTER", "name": "beacon.page.name", "operator": "CONTAINS", "entity": "NOT_APPLICABLE", "value": "checkout"}

    get_beacon_groups - Use for grouped/aggregated data (e.g., "beacon count per page")
    get_beacons - Use for individual beacon data (e.g., "list all page load beacons")

CATALOG (resource_type="catalog"):
    operations: get_metrics, get_tag_catalog
    params: {beacon_type, use_case}

    get_metrics - Get website metrics catalog with full metadata (metricId, label, description, formatter, aggregations, beaconTypes)
    get_tag_catalog - Get valid tag names for beacon_type and use_case
        Valid beacon_type: "PAGELOAD", "PAGECHANGE", "RESOURCELOAD", "CUSTOM", "HTTPREQUEST", "ERROR"
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

Args:
    resource_type: "analyze", "catalog", "configuration", or "advanced_config"
    operation: Specific operation for the resource type
    params: Operation-specific parameters (optional)
    ctx: MCP context (internal)

Returns:
    Dictionary with results from the appropriate tool

Examples:
    resource_type="catalog", operation="get_tag_catalog", params={"beacon_type": "PAGELOAD", "use_case": "GROUPING"}
    resource_type="analyze", operation="get_beacon_groups", params={"metrics": [{"metric": "beaconCount", "aggregation": "SUM"}], "group": {"groupByTag": "beacon.page.name"}, "time_frame": {"to": "19 March 2026, 2:47 PM|IST", "windowSize": 3600000}, "beacon_type": "PAGELOAD"}
    resource_type="analyze", operation="get_beacons", params={"time_frame": {"to": 1234567890000, "windowSize": 3600000}, "beacon_type": "PAGELOAD", "pagination": {"retrievalSize": 50}}
    resource_type="catalog", operation="get_metrics"
    resource_type="configuration", operation="get_all"
    resource_type="configuration", operation="get", params={"website_name": "robot-shop"}
    resource_type="advanced_config", operation="get_geo_config", params={"website_name": "robot-shop"}"""
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
            if resource_type not in ["analyze", "catalog", "configuration", "advanced_config"]:
                return {
                    "error": f"Invalid resource_type '{resource_type}'. Valid types: 'analyze', 'catalog', 'configuration', 'advanced_config'",
                    "valid_types": ["analyze", "catalog", "configuration", "advanced_config"]
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
            else:
                return {
                    "error": f"Unsupported resource_type: {resource_type}",
                    "supported_types": ["analyze", "catalog", "configuration", "advanced_config"]
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
                "error": f"Invalid operation '{operation}' for analyze",
                "valid_operations": ANALYZE_VALID_OPERATIONS
            }

        # Extract individual parameters from params dict
        # This is the key difference - we extract each parameter separately
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
                "error": conversion_result["error"],
                "resource_type": "analyze",
                "operation": operation,
                "original_params": params,
                "hint": "Provide time_frame.to as Unix timestamp (ms) or datetime string with timezone (e.g., '10 March 2026, 2:00 PM|IST')"
            }

        # Update time_frame with converted value if conversion occurred
        if conversion_result["converted"]:
            time_frame = conversion_result["params"][PARAM_TIME_FRAME]

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
            result = await self.website_analyze_client.get_website_beacon_groups(
                metrics=metrics,
                group=group,
                tag_filter_expression=tag_filter_expression,
                time_frame=time_frame,
                beacon_type=beacon_type,
                fill_time_series=fill_time_series,
                order=order,
                pagination=pagination,
                ctx=ctx
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
            result = await self.website_analyze_client.get_website_beacons(
                tag_filter_expression=tag_filter_expression,
                time_frame=time_frame,
                beacon_type=beacon_type,
                pagination=pagination,
                ctx=ctx
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
                "error": f"Invalid operation '{operation}' for catalog",
                "valid_operations": CATALOG_VALID_OPERATIONS
            }

        #Route to specific operation
        if operation == "get_metrics":
            logger.debug("Routing to Website Catalog Metrics")
            result = await self.website_catalog_client.get_website_catalog_metrics(ctx = ctx)

        elif operation == "get_tag_catalog":
            # Extract required parameters
            beacon_type = params.get(PARAM_BEACON_TYPE)
            use_case = params.get(PARAM_USE_CASE)

            logger.debug(
                f"Routing to Website Tag Catalog | "
                f"beacon_type={beacon_type}, use_case={use_case}"
            )

            # Normalize beacon_type to camelCase format (API expects camelCase)
            beacon_type_map = {
                "PAGELOAD": "pageLoad",
                "PAGECHANGE": "pageChange",
                "RESOURCELOAD": "resourceLoad",
                "CUSTOM": "custom",
                "HTTPREQUEST": "httpRequest",
                "ERROR": "error"
            }

            normalized_beacon_type = normalize_beacon_type(beacon_type, beacon_type_map)
            if beacon_type != normalized_beacon_type:
                logger.debug(f"Normalized beacon_type from '{beacon_type}' to '{normalized_beacon_type}'")
                beacon_type = normalized_beacon_type

            # Pass parameters to the client
            result = await self.website_catalog_client.get_website_tag_catalog(
                beacon_type=beacon_type,
                use_case=use_case,
                ctx=ctx
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
                "error": f"Invalid operation '{operation}' for configuration",
                "valid_operations": CONFIGURATION_VALID_OPERATIONS
            }

        # Extract parameters
        website_id = params.get(PARAM_WEBSITE_ID)
        website_name = params.get(PARAM_WEBSITE_NAME)
        name = params.get(PARAM_NAME)
        payload = params.get(PARAM_PAYLOAD)

        # Route to the configuration client
        result = await self.website_configuration_client.execute_website_operation(
            operation=operation,
            website_id=website_id,
            website_name=website_name,
            name=name,
            payload=payload,
            ctx=ctx
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
                "error": f"Invalid operation '{operation}' for advanced_config",
                "valid_operations": ADVANCED_CONFIG_VALID_OPERATIONS,
                "note": "Only GET operations are supported. Use Instana UI for modifications."
            }

        # Extract parameters
        website_id = params.get(PARAM_WEBSITE_ID)
        website_name = params.get(PARAM_WEBSITE_NAME)

        # Route to the configuration client's advanced config executor
        result = await self.website_configuration_client.execute_advanced_config_operation(
            operation=operation,
            website_id=website_id,
            website_name=website_name,
            ctx=ctx
        )

        return {
            "resource_type": "advanced_config",
            "operation": operation,
            "website_name": website_name if website_name else None,
            "website_id": website_id if website_id else None,
            "results": result
        }
