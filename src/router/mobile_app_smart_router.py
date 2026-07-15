"""
Smart Router Tool for Mobile App Monitoring

This module provides a unified MCP tool that routes mobile app monitoring queries
to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, List, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.timestamp_utils import convert_nested_datetime_param
from src.core.utils import (
    MOBILE_BEACON_TYPE_MAP,
    BaseInstanaClient,
    normalize_beacon_type,
    register_as_tool,
)

logger = logging.getLogger(__name__)

# Define valid operations for each resource type at module level
ANALYZE_VALID_OPERATIONS = ["get_all_mobile_app_beacons", "get_mobile_app_beacon_groups"]
CATALOG_VALID_OPERATIONS = ["get_mobile_app_tag_catalog", "get_mobile_app_metric_catalog"]
CONFIGURATION_VALID_OPERATIONS = ["get_all", "get"]
ADVANCED_CONFIG_VALID_OPERATIONS = ["get_geo_config", "get_ip_masking", "get_geo_rules", "get_source_map_upload_config", "get_mobile_app_source_map_upload_config_by_id"]
ALERT_VALID_OPERATIONS = ["find_active_mobile_app_alert_configs", "find_mobile_app_alert_config"]
SESSION_REPLAY_VALID_OPERATIONS = ["get_session_replay_action_beacons"]

# Define parameter key constants to avoid typos
PARAM_METRICS = "metrics"
PARAM_GROUP = "group"
PARAM_TAG_FILTER_EXPRESSION = "tag_filter_expression"
PARAM_TIME_FRAME = "time_frame"
PARAM_BEACON_TYPE = "beacon_type"
PARAM_FILL_TIME_SERIES = "fill_time_series"
PARAM_PAGINATION = "pagination"
PARAM_ORDER = "order"
PARAM_FILTER_FIELDS = "filter_fields"
PARAM_USE_CASE = "use_case"
PARAM_MOBILE_APP_ID = "mobile_app_id"
PARAM_MOBILE_APP_NAME = "mobile_app_name"
PARAM_CONFIG_ID = "config_id"
PARAM_ALERT_ID = "id"
PARAM_VALID_ON = "valid_on"
PARAM_ALERT_IDS = "alert_ids"
PARAM_SESSION_ID = "session_id"
PARAM_CURSOR = "cursor"
PARAM_PAGE_SIZE = "page_size"

class MobileAppSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart Router MCP Tool for Mobile App Monitoring operations.
    Routes queries to Mobile App Analyze tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Mobile App Smart Router MCP Tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        from src.mobile_app.mobile_app_alert import MobileAppAlertMCPTools
        from src.mobile_app.mobile_app_analyze import MobileAppAnalyzeMCPTools
        from src.mobile_app.mobile_app_catalog import MobileAppCatalogMCPTools
        from src.mobile_app.mobile_app_configuration import (
            MobileAppConfigurationMCPTools,
        )
        from src.mobile_app.mobile_app_session_replay import (
            MobileAppSessionReplayMCPTools,
        )

        self.mobile_app_analyze_client = MobileAppAnalyzeMCPTools(read_token, base_url)
        self.mobile_app_catalog_client = MobileAppCatalogMCPTools(read_token, base_url)
        self.mobile_app_configuration_client = MobileAppConfigurationMCPTools(read_token, base_url)
        self.mobile_app_alert_client = MobileAppAlertMCPTools(read_token, base_url)
        self.mobile_app_session_replay_client = MobileAppSessionReplayMCPTools(read_token, base_url)

        logger.info("Smart Router for Mobile App Monitoring initialized with analyze, catalog, configuration, alert, and session replay tools.")

    @register_as_tool(
        title="Manage Instana Mobile App Resources",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        description="""Unified Instana mobile app resource manager for beacon monitoring, catalog, configuration, and alert operations.

Resource Types:
    - "analyze": Query mobile app beacon data with grouping or filtering
    - "catalog": Get available metrics and tags for mobile app monitoring
    - "configuration": Get mobile app configurations
    - "advanced_config": Retrieve advanced configurations (geo-location, IP masking, geo rules, source map upload config, get_mobile_app_source_map_upload_config_by_id) - READ ONLY
    - "alert": Get available alert configurations for mobile app monitoring
    - "session_replay": Query mobile app session replay data

WORKFLOW DECISION:
├─ Are you using resource_type="analyze"?
   └─ YES → Adhere to ANALYZE WORKFLOW at all times when making decisions
   └─ NO → Ignore ANALYZE WORKFLOW entirely and adhere to resource description

ANALYZE WORKFLOW:
    1. FIRST: Call get_mobile_app_metric_catalog to get valid metrics
       - resource_type="catalog", operation="get_mobile_app_metric_catalog"
       - Returns: Available metrics with metricId, aggregations, and beacon types

    2. SECOND: Call get_mobile_app_tag_catalog to get valid tag names
       - resource_type="catalog", operation="get_mobile_app_tag_catalog"
       - params: {"beacon_type": "SESSION_START", "use_case": "FILTERING"}

    3. THIRD: Use ONLY the tag names and metrics returned from catalog operations
       - Tag names MUST start with "mobileBeacon." (e.g., "mobileBeacon.mobileApp.name")
       - Metric names must match those from get_mobile_app_metric_catalog
       - NEVER guess or invent tag names or metric names

    4. FOURTH: Call analyze operations with validated tag names and metrics
       - ALWAYS include "entity": "NOT_APPLICABLE" in EVERY TAG_FILTER

    Default beacon_type: "SESSION_START" | Default use_case for get_all_mobile_app_beacons: "FILTERING"

ANALYZE (resource_type="analyze"):
    operations:
        - get_all_mobile_app_beacons
            params: {time_frame, beacon_type, pagination, tag_filter_expression (optional), filter_fields (optional)}

        - get_mobile_app_beacon_groups
            params: {time_frame, beacon_type, fill_time_series, pagination, tag_filter_expression (optional), metrics (optional), group (optional), order (optional)}

    Aggregations: SUM, MEAN, MAX, MIN, P25, P50, P75, P90, P95, P98, P99, P99_9, P99_99, DISTINCT_COUNT, SUM_POSITIVE, PER_SECOND, INCREASE
    Operators: EQUALS, NOT_EQUAL, CONTAINS, NOT_CONTAIN, STARTS_WITH, ENDS_WITH, NOT_STARTS_WITH, NOT_ENDS_WITH, GREATER_THAN, GREATER_OR_EQUAL_THAN, LESS_THAN, LESS_OR_EQUAL_THAN, NOT_EMPTY, IS_EMPTY, NOT_BLANK, IS_BLANK, REGEX_MATCH

    time_frame: {"to": <timestamp_or_datetime>, "windowSize": <milliseconds>}
        - to: Unix timestamp in milliseconds OR datetime string (e.g., "19 March 2026, 2:47 PM|IST")
        - If timezone not specified in datetime string, defaults to UTC
        - windowSize: Duration in milliseconds (default: 3600000 = 1 hour)

    tag_filter_expression: CRITICAL - Entity field is REQUIRED for ALL tag filters
        - ALWAYS set "entity": "NOT_APPLICABLE" for ALL mobile app beacon tags
        - This applies to ALL tags: mobileBeacon.mobileApp.*, mobileBeacon.view.*, mobileBeacon.device.*, mobileBeacon.geo.*, etc.
        - The entity field is MANDATORY - never omit it or set it to null
        - Tag names MUST start with "mobileBeacon." - get valid names from get_mobile_app_tag_catalog first

        Examples:
          * {"type": "TAG_FILTER", "name": "mobileBeacon.mobileApp.name", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Robot Shop"}
          * {"type": "TAG_FILTER", "name": "mobileBeacon.view.name", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Products"}
          * {"type": "TAG_FILTER", "name": "mobileBeacon.device.model", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "iPhone 12"}

    filter_fields (optional, default: True):
        - Controls which fields are included in each returned beacon.
        - True / None / omitted — essential fields only
        -  False — all fields returned by the REST endpoint (unfiltered, larger payload)

    get_all_mobile_app_beacons - Use for individual beacon data (e.g., "list all session start beacons")
    get_mobile_app_beacon_groups - Use for grouped/aggregated beacon metrics (e.g., "beacon count per mobile app")

CATALOG (resource_type="catalog"):
    operations: get_mobile_app_metric_catalog, get_mobile_app_tag_catalog
    params: {beacon_type, use_case}

    get_mobile_app_metric_catalog - Get mobile app metrics catalog with necessary metadata for query planning (metricId, label, description, formatter, aggregations, beaconTypes). Use params.view="full" to retrieve raw SDK metadata (rarely needed).

    get_mobile_app_tag_catalog - MUST CALL THIS FIRST before using any tag names
        Returns: List of valid tag names that start with "mobileBeacon."
        Valid beacon_type: "SESSION_START", "VIEW_CHANGE", "HTTP_REQUEST", "CUSTOM", "CRASH", "PERF", "DROP_BEACON"
        Valid use_case: "GROUPING", "FILTERING", "SERVICE_MAPPING", "SMART_ALERTS", etc.

        Example call:
        resource_type="catalog", operation="get_mobile_app_tag_catalog",
        params={"beacon_type": "SESSION_START", "use_case": "FILTERING"}

CONFIGURATION (resource_type="configuration"):
    operations: get_all, get
    params: {mobile_app_id, mobile_app_name}

    get_all - List all mobile apps
    get - Get mobile app by ID or name (supports name resolution)

    NOTE: Create, Update, Delete operations are not available.
            Use the Instana UI for mobile app configuration modifications.

ADVANCED_CONFIG (resource_type="advanced_config"):
    operations: get_geo_config, get_ip_masking, get_geo_rules, get_source_map_upload_config, get_mobile_app_source_map_upload_config_by_id
    params: {mobile_app_id, mobile_app_name, config_id (for get_mobile_app_source_map_upload_configuration_by_id)}

    NOTE: These are READ-ONLY operations for retrieving advanced configurations.
            Use the Instana UI for modifications.
            Source map operations are not currently available due to authentication limitations.

    get_geo_config - Get geo-location configuration
        Returns: geoDetailRemoval setting and geoMappingRules array
    get_ip_masking - Get IP masking configuration
        Returns: ipMasking setting (DEFAULT ,STRICT ,REMOVE_ALL_DETAILS)
    get_geo_rules - Get custom geo mapping rules
        Returns: Array of geo mapping rules with CIDR ranges and location data
    get_source_map_upload_config - Get source map upload configuration details
        Returns: Source map upload configuration settings
    get_mobile_app_source_map_upload_config_by_id - Get specific source map upload configuration by ID
        Returns: Source map upload configuration settings for the specified ID

ALERT (resource_type="alert"):
    operations: find_active_mobile_app_alert_configs, find_mobile_app_alert_config
    params: {mobile_app_id, alert_ids, id, valid_on}

    find_active_mobile_app_alert_configs - Get all alert configurations for a mobile app
        - mobile_app_id: Mobile app ID to get alert configs for (required)
        - alert_ids: Optional list of specific alert IDs to filter (optional)

    find_mobile_app_alert_config - Get a specific alert configuration by ID
        - id: Specific alert config ID to retrieve (required)
        - valid_on: Unix timestamp to retrieve config valid at that time (optional, defaults to latest active version)

SESSION_REPLAY (resource_type="session_replay"):
    operations: get_session_replay_action_beacons
    params: {mobile_app_id (required), session_id (required), cursor (optional), page_size (optional)}

    get_session_replay_action_beacons - Get paginated session replay action beacons by mobile app id and session id
        Required parameters:
            - mobile_app_id: Mobile app ID that owns the session
            - session_id: Session ID to retrieve action beacons for

        Optional pagination parameters:
            - cursor: Zero-based offset of the first beacon to return
                * Use cursor=0 for the first page
                * Do NOT treat cursor as a timestamp
                * Use cursor=0 for the first page. If the response has hasMore=true, call again with cursor=nextCursor until hasMore=false.
            - page_size: Maximum number of beacons to return in one request
                * Use a small value like 1 for debugging
                * Use a larger value like 100 for normal retrieval
                * Maximum value of 1000

        Response fields:
            - beacons: List of action beacons returned for this page
            - nextCursor: Offset to use in the next request
            - hasMore: Whether more beacons remain after this page

        PAGINATION RULES - FOLLOW EXACTLY:
            1. Start with cursor=0.
            2. Read the returned beacons.
            3. If hasMore=true, call again with cursor=nextCursor.
            4. Repeat until hasMore=false.
            5. Combine all returned beacons in order.

        PAGINATION EXAMPLE:
            First request:
                params={"mobile_app_id": "app-123", "session_id": "session-456", "cursor": 0, "page_size": 100}

            Example response:
                {"beacons": [...], "nextCursor": 100, "hasMore": true}

            Second request:
                params={"mobile_app_id": "app-123", "session_id": "session-456", "cursor": 100, "page_size": 100}

            Final response example:
                {"beacons": [...], "nextCursor": null, "hasMore": false}

Args:
    resource_type: "analyze", "catalog", "configuration", or "advanced_config", "alert", "session_replay"
    operation: Specific operation for the resource type
    params: Operation-specific parameters (optional)

Returns:
    Dictionary with results from the appropriate tool

        Examples:
            resource_type="catalog", operation="get_mobile_app_tag_catalog", params={"beacon_type": "SESSION_START", "use_case": "GROUPING"}
            resource_type="analyze", operation="get_mobile_app_beacon_groups", params={"metrics": [{"metric": "beaconCount", "aggregation": "SUM"}], "group": {"groupByTag": "mobileBeacon.view.name"}, "time_frame": {"to": "19 March 2026, 2:47 PM|IST", "windowSize": 3600000}, "beacon_type": "SESSION_START"}
            resource_type="analyze", operation="get_all_mobile_app_beacons", params={"time_frame": {"to": 1234567890000, "windowSize": 3600000}, "beacon_type": "SESSION_START", "pagination": {"retrievalSize": 50}, "filter_fields": True}
            resource_type="catalog", operation="get_mobile_app_metric_catalog"
            resource_type="configuration", operation="get_all"
            resource_type="configuration", operation="get", params={"mobile_app_name": "robot-shop"}
            resource_type="advanced_config", operation="get_geo_config", params={"mobile_app_name": "robot-shop"}
            resource_type="session_replay", operation="get_session_replay_action_beacons", params={"mobile_app_id": "i1IsNS7FQAegEljBTkNBMQ", "session_id": "1d616527-2635-407f-89fc-de7136b66fb4", "cursor": 10, "page_size": 100}
            """
    )
    async def manage_mobile_apps(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Unified Instana mobile app resource manager for beacon monitoring, catalog, configuration, alert, and session replay operations."""

        try:
            logger.debug(f"Mobile App Router: resource_type={resource_type}, operation={operation}")

            # Handle params being passed as a JSON string (MCP framework may serialize it)
            if params is None:
                params = {}

            # Validate resource_type
            if resource_type not in ["analyze", "catalog", "configuration", "advanced_config", "alert", "session_replay"]:
                return {
                    "error": f"Invalid resource_type '{resource_type}'. Valid types: 'analyze', 'catalog', 'configuration', 'advanced_config', 'alert', 'session_replay'",
                    "valid_types": ["analyze", "catalog", "configuration", "advanced_config", "alert", "session_replay"]
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
            elif resource_type == "session_replay":
                return await self._handle_session_replay(operation, params, ctx)
            else:
                return {
                    "error": f"Unsupported resource_type: {resource_type}",
                    "supported_types": ["analyze", "catalog", "configuration", "advanced_config", "alert", "session_replay"]
                }

        except Exception as e:
            logger.error(
                f"Error in mobile app smart router: {e} | "
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
        """Handle mobile app analyze operations."""

        # Validate operation
        if operation not in ANALYZE_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for analyze",
                "valid_operations": ANALYZE_VALID_OPERATIONS
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
        filter_fields = params.get(PARAM_FILTER_FIELDS)

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
        if operation == "get_mobile_app_beacon_groups":
            logger.debug(
                f"Routing to Mobile App Beacon Groups | "
                f"metrics={metrics}, group={group}, beacon_type={beacon_type}, "
                f"time_frame={time_frame}, fill_time_series={fill_time_series},"
                f"tag_filter_expression={tag_filter_expression},"
                f"order={order}, pagination: {pagination}"
            )

            # Pass individual parameters to the client
            result = await self.mobile_app_analyze_client.get_mobile_app_beacon_groups(
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

        elif operation == "get_all_mobile_app_beacons":
            logger.debug(
                f"Routing to Mobile App Beacons | "
                f"metrics={metrics}, group={group}, beacon_type={beacon_type}, "
                f"time_frame={time_frame}, fill_time_series={fill_time_series},"
                f"tag_filter_expression={tag_filter_expression},"
                f"order={order}, pagination: {pagination}, filter_fields: {filter_fields}"
            )

            # Pass individual parameters to the client
            result = await self.mobile_app_analyze_client.get_all_mobile_app_beacons(
                tag_filter_expression=tag_filter_expression,
                time_frame=time_frame,
                beacon_type=beacon_type,
                pagination=pagination,
                filter_fields=filter_fields,
                ctx=ctx
            )

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
        """Handle Mobile App catalog operations"""

        # Validate operation
        if operation not in CATALOG_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for catalog",
                "valid_operations": CATALOG_VALID_OPERATIONS
            }

        # Initialize result to avoid unbound variable error
        result = None

        #Route to specific operation
        if operation == "get_mobile_app_metric_catalog":
            view = (params or {}).get("view", "planner")
            logger.debug(f"Routing to Mobile App Catalog Metrics | view={view}")
            result = await self.mobile_app_catalog_client.get_mobile_app_metric_catalog(ctx=ctx, view=view)

        elif operation == "get_mobile_app_tag_catalog":
            # Extract required parameters
            beacon_type = params.get(PARAM_BEACON_TYPE)
            use_case = params.get(PARAM_USE_CASE)

            logger.debug(
                f"Routing to Mobile App Tag Catalog | "
                f"beacon_type={beacon_type}, use_case={use_case}"
            )

            # Normalize beacon_type to camelCase format (API expects camelCase)
            normalized_beacon_type = normalize_beacon_type(beacon_type, MOBILE_BEACON_TYPE_MAP)
            if beacon_type != normalized_beacon_type:
                logger.debug(f"Normalized beacon_type from '{beacon_type}' to '{normalized_beacon_type}'")
                beacon_type = normalized_beacon_type

            # Pass parameters to the client
            result = await self.mobile_app_catalog_client.get_mobile_app_tag_catalog(
                beacon_type=beacon_type,
                use_case=use_case,
                ctx=ctx
            )
        else:
            # This should never happen due to validation above, but handle it gracefully
            return {
                "error": f"Unhandled operation '{operation}' for catalog",
                "valid_operations": CATALOG_VALID_OPERATIONS
            }

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
        ctx
    ) -> Dict[str, Any]:
        """Handle Mobile App configuration operations"""

        # Validate operation
        if operation not in CONFIGURATION_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for configuration",
                "valid_operations": CONFIGURATION_VALID_OPERATIONS
            }

        mobile_app_id = params.get(PARAM_MOBILE_APP_ID)
        mobile_app_name = params.get(PARAM_MOBILE_APP_NAME)

        # Route to specific operation
        result = await self.mobile_app_configuration_client.execute_mobile_app_operation(
            operation=operation,
            mobile_app_id=mobile_app_id,
            mobile_app_name=mobile_app_name,
            ctx=ctx
        )

        return {
            "resource_type": "configuration",
            "operation": operation,
            "mobile_app_name": mobile_app_name if mobile_app_name else None,
            "mobile_app_id": mobile_app_id if mobile_app_id else None,
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
        mobile_app_id = params.get(PARAM_MOBILE_APP_ID)
        mobile_app_name = params.get(PARAM_MOBILE_APP_NAME)
        config_id = params.get(PARAM_CONFIG_ID)

        # Route to the configuration client's advanced config executor
        result = await self.mobile_app_configuration_client.execute_mobile_app_advanced_config_operation(
            operation=operation,
            mobile_app_id=mobile_app_id,
            mobile_app_name=mobile_app_name,
            config_id=config_id,
            ctx=ctx
        )

        return {
            "resource_type": "advanced_config",
            "operation": operation,
            "mobile_app_name": mobile_app_name if mobile_app_name else None,
            "mobile_app_id": mobile_app_id if mobile_app_id else None,
            "config_id": config_id if config_id else None,
            "results": result
        }

    async def _handle_alert(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
        ) -> Dict[str, Any]:
        """Handle Mobile App alert operations"""

        # Validate operation
        if operation not in ALERT_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for alert",
                "valid_operations": ALERT_VALID_OPERATIONS
            }

        # Initialize result to avoid unbound variable error
        result = None

        #Route to specific operation
        if operation == "find_active_mobile_app_alert_configs":
            mobile_app_id = params.get(PARAM_MOBILE_APP_ID)
            alert_ids = params.get(PARAM_ALERT_IDS)

            logger.debug(f"Routing to find_active_mobile_app_alert_configs with mobile_app_id={mobile_app_id}")
            result = await self.mobile_app_alert_client.find_active_mobile_app_alert_configs(
                mobile_app_id=mobile_app_id,
                alert_ids=alert_ids,
                ctx=ctx
            )
        elif operation == "find_mobile_app_alert_config":
            alert_id = params.get(PARAM_ALERT_ID)
            valid_on = params.get(PARAM_VALID_ON)

            logger.debug(f"Routing to find_mobile_app_alert_config with id={alert_id}")
            result = await self.mobile_app_alert_client.find_mobile_app_alert_config(
                id=alert_id,
                valid_on=valid_on,
                ctx=ctx
            )
        else:
            # This should never happen due to validation above, but handle it gracefully
            return {
                "error": f"Unhandled operation '{operation}' for alert",
                "valid_operations": ALERT_VALID_OPERATIONS
            }

        # Return structured response
        return {
            "resource_type": "alert",
            "operation": operation,
            "results": result
        }

    async def _handle_session_replay(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx: Optional[Context] = None
        ) -> Dict[str, Any]:
        """Handle Session Replay operations"""

        # Validate operation
        if operation not in SESSION_REPLAY_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for session replay",
                "valid_operations": SESSION_REPLAY_VALID_OPERATIONS
            }

        # Initialize result to avoid unbound variable error
        result = None

        #Route to specific operation
        if operation == "get_session_replay_action_beacons":
            mobile_app_id = params.get(PARAM_MOBILE_APP_ID)
            session_id = params.get(PARAM_SESSION_ID)
            cursor = params.get(PARAM_CURSOR)
            page_size = params.get(PARAM_PAGE_SIZE)

            logger.debug(f"Routing to get_session_replay_action_beacons with mobile_app_id={mobile_app_id} and session_id={session_id}")
            result = await self.mobile_app_session_replay_client.get_session_replay_action_beacons(
                mobile_app_id=mobile_app_id,
                session_id=session_id,
                cursor=cursor,
                page_size=page_size,
                ctx=ctx
            )
        else:
            # This should never happen due to validation above, but handle it gracefully
            return {
                "error": f"Unhandled operation '{operation}' for session replay",
                "valid_operations": SESSION_REPLAY_VALID_OPERATIONS
            }

        # Return structured response
        return {
            "resource_type": "session_replay",
            "operation": operation,
            "results": result
        }
