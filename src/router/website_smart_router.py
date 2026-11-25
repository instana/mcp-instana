"""
Smart Router Tool for Website Monitoring

This module provides a unified MCP tool that routes website monitoring queries
to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, List, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.elicitation import missing_param
from src.core.timestamp_utils import convert_nested_datetime_param
from src.core.utils import (
    BaseInstanaClient,
    WEBSITE_BEACON_TYPE_MAP,
    normalize_beacon_type,
    parse_payload,
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
ALERT_VALID_OPERATIONS = [
    "find_active_website_alert_configs",
    "find_website_alert_config",
    "find_versions",
    "create",
    "update",
    "delete",
    "enable",
    "disable",
    "restore",
]
# Operations that only need an alert config `id`
ALERT_ID_ONLY_OPERATIONS = ["delete", "enable", "disable", "find_versions"]
ALERT_ID_HINT = "Use resource_type='alert', operation='find_active_website_alert_configs' to list alert config IDs"
# Legacy single-rule fields; the server only accepts them if they agree with `rules`
ALERT_LEGACY_RULE_FIELDS = ["rule", "threshold", "severity"]

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
PARAM_CREATED = "created"


def _coerce_int(value: Any, name: str) -> int:
    """Return ``value`` as a positive int.

    Accepts an int, an integral float (JSON clients may send ``1.7e12``) or a digit string
    (MCP clients often send timestamps as strings). Raises ``ValueError`` naming ``name`` for
    anything else, including bools, fractional floats, zero and negative numbers.
    """
    number: Optional[int] = None
    if isinstance(value, bool):
        number = None
    elif isinstance(value, int):
        number = value
    elif isinstance(value, float) and value.is_integer():
        number = int(value)
    elif isinstance(value, str):
        try:
            number = int(value.strip())
        except ValueError:
            number = None
    if number is None:
        raise ValueError(f"'{name}' must be an integer, got {value!r}")
    if number <= 0:
        raise ValueError(f"'{name}' must be a positive Unix timestamp in milliseconds, got {value!r}")
    return number


def _coerce_id(value: Any) -> Any:
    """The SDK requires a str id; MCP clients sometimes send a number. Leave falsy values for the missing-param check."""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return value


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
        from src.website.website_alert import WebsiteAlertMCPTools

        # Initialize the website clients
        self.website_analyze_client = WebsiteAnalyzeMCPTools(read_token, base_url)
        self.website_catalog_client = WebsiteCatalogMCPTools(read_token, base_url)
        self.website_configuration_client = WebsiteConfigurationMCPTools(read_token, base_url)
        self.website_alert_client = WebsiteAlertMCPTools(read_token, base_url)

        logger.info("Smart Router Website initialized with Analyze, Catalog, Configuration and Alert tools")

    @register_as_tool(
        title="Manage Instana Website Resources",
        # destructiveHint stays False on purpose: `delete` is a soft delete that `restore` can undo.
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
        description="""Unified Instana website resource manager for beacon monitoring, catalog, configuration and alert operations.

Resource Types:
    - "analyze": Query website beacon data with grouping or filtering
    - "catalog": Get available metrics and tags for website monitoring
    - "configuration": Get website configurations
    - "advanced_config": Retrieve advanced configurations (geo-location, IP masking, geo rules) - READ ONLY
    - "alert": Read and manage website alert configurations (create, update, delete, enable, disable, restore)

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
    operations: find_active_website_alert_configs, find_website_alert_config, find_versions, create, update, delete, enable, disable, restore
    params: {website_id, alert_ids, id, valid_on, payload, created}

    find_active_website_alert_configs - Get all alert configurations for a website
        - website_id: Website ID to get alert configs for (required)
        - alert_ids: Optional list of specific alert IDs to filter (optional)
    
    find_website_alert_config - Get a specific alert configuration by ID
        - id: Specific alert configuration ID to retrieve (required)
        - valid_on: Unix timestamp (ms) to retrieve the configuration active at that time (optional, default is latest active version)

    find_versions - List every version of an alert configuration (id required). Each version has `created` (ms), `enabled`, `deleted`, `changeSummary`.
    create - Create an alert configuration (payload required)
    update - Update an alert configuration (id and payload required). Send the COMPLETE configuration (a partial
        payload is rejected): call find_website_alert_config first, apply your changes to the result, and send it back
        in the create payload format below. Server-managed fields (id, created, ...), the legacy top-level
        rule/threshold/severity fields and the threshold `baseline` arrays are dropped before sending
        (the server recomputes baselines).
    delete - Delete an alert configuration (id required). This is a soft delete; use find_versions + restore to undo it.
    enable / disable - Enable or disable an alert configuration (id required)
    restore - Restore an alert configuration to an earlier version (id and `created` required; take `created` from find_versions)

    Requires the canConfigureWebsiteSmartAlerts permission for create/update/delete/enable/disable/restore.
    NOTE: create/update/delete/enable/disable/restore change live alerting. Confirm with the user before calling them.
    If a write call times out, the outcome is unknown: check before retrying. After a create timeout use
    find_active_website_alert_configs (at most 10 configs are returned; narrow with alert_ids), otherwise a retried
    create can produce a duplicate alert. After update/delete/enable/disable/restore use find_website_alert_config
    or find_versions with the alert id.
    Failures are returned at the top level of the response (`error`, or `elicitation_needed` for missing/invalid input).
    Send either alertChannelIds or alertChannels on create, not both.
    Alert channel IDs are checked against existing channels before create/update; use manage_alert_channels to list them.

    payload for create (required: name, description, websiteId, rules):
        - name, description, websiteId
        - rules: EXACTLY ONE item: {"rule": {...}, "thresholdOperator": ">", "thresholds": {"WARNING": {...}, "CRITICAL": {...}}}
            Use WARNING, CRITICAL, or both (no other keys). Do NOT send top-level rule/threshold/severity.
            thresholdOperator: >, >=, <, <=, OUTSIDE, BETWEEN (OUTSIDE and BETWEEN use lowerBound and upperBound, no value).
            With > or >=, CRITICAL must be greater than WARNING. Both severities must use the same threshold type.
            Threshold `type` is one of three values:
            staticThreshold:  {"type": "staticThreshold", "value": 5000} (OUTSIDE and BETWEEN use lowerBound/upperBound instead)
            historicBaseline: {"type": "historicBaseline", "seasonality": "DAILY"|"WEEKLY", "deviationFactor": 1.75}
                (the UI's "static with seasonality"; deviationFactor 0.5 to 16; the baseline is computed by the server, do not send it)
            adaptiveBaseline: {"type": "adaptiveBaseline", "deviationFactor": 1.75, "sensitivityValue": 1.75,
                "sensitivityMode": "STANDARD_DEVIATIONS", "adaptability": 0.2841, "seasonality": "AUTO", "minimumAbsoluteDelta": 0}
                (seasonality is always AUTO; not editable in the UI; needs metric history, otherwise the API answers 428)
            All three types are available for slowness, throughput, statusCode and customEvent rules. specificJsError rules
            support staticThreshold only (the API answers 422 "rule type does not support baselines").
        - rule by alertType:
            slowness:        metricName onLoadTime | httpLatency; aggregation required (SUM, MEAN, MAX, MIN, P25, P50, P75, P90, P95, P98, P99)
            throughput:      metricName pageLoads | pageTransitions; aggregation (e.g. SUM)
            statusCode:      metricName httpxxx | specificStatusCodeRate; operator EQUALS | STARTS_WITH only; value required; aggregation
            specificJsError: metricName errors | specificJsErrorRate; operator (e.g. CONTAINS, EQUALS, STARTS_WITH, ENDS_WITH,
                NOT_EMPTY with value "Any"); value required; aggregation.
                Example: {"alertType": "specificJsError", "metricName": "errors", "operator": "EQUALS", "value": "TypeError", "aggregation": "SUM"}
            customEvent:     metricName beaconCount | customMetric | customDuration; customEventName required; aggregation.
                Example: {"alertType": "customEvent", "customEventName": "Payment Declined", "metricName": "beaconCount", "aggregation": "SUM"}
                or with metricName customDuration and aggregation P98.
        - granularity (optional, default 600000): 60000, 300000, 600000, 900000, 1200000 or 1800000
        - timeThreshold (optional): {"type": "violationsInSequence", "timeWindow": 600000}. timeWindow must be a multiple of
            granularity (1 to 12 times). Also violationsInPeriod (needs violations) and userImpactOfViolationsInSequence.
        - tagFilterExpression (optional): TAG_FILTER needs "name", "operator", "entity": "NOT_APPLICABLE" and "value" (value is mandatory)
        - alertChannelIds (list) or alertChannels ({"WARNING": [ids], "CRITICAL": [ids]}); send one of them, not both
        - triggering (bool), enabled (bool), gracePeriod (ms, a multiple of granularity), customPayloadFields
        - rbacTags: do not send. It is read-only and assigned by the server (the value is ignored on create and update;
            a config's rbacTags cannot be set or changed through this tool).
    payload for update: all the create fields (name, description, websiteId, rules, ...). websiteId cannot be changed.
        Unlike create, update accepts (and drops) top-level rule/threshold/severity and rbacTags, so the result of find
        can be edited and sent back.


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
    resource_type="alert", operation="find_website_alert_config", params={"id": "alert-123", "valid_on": 1234567890000}
    resource_type="alert", operation="create", params={"payload": {"name": "Slow page loads", "description": "P90 load time high", "websiteId": "website-abc123", "rules": [{"rule": {"alertType": "slowness", "metricName": "onLoadTime", "aggregation": "P90"}, "thresholdOperator": ">", "thresholds": {"WARNING": {"type": "staticThreshold", "value": 3000}, "CRITICAL": {"type": "staticThreshold", "value": 5000}}}], "alertChannelIds": ["channel-1"]}}
    resource_type="alert", operation="update", params={"id": "alert-123", "payload": {"name": "Renamed alert", "description": "P90 load time high", "websiteId": "website-abc123", "rules": [{"rule": {"alertType": "slowness", "metricName": "onLoadTime", "aggregation": "P90"}, "thresholdOperator": ">", "thresholds": {"CRITICAL": {"type": "staticThreshold", "value": 5000}}}], "granularity": 300000}}
    resource_type="alert", operation="disable", params={"id": "alert-123"}
    resource_type="alert", operation="find_versions", params={"id": "alert-123"}
    resource_type="alert", operation="restore", params={"id": "alert-123", "created": 1700000000000}"""
    )
    async def manage_websites(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Unified Instana website resource manager for beacon monitoring, catalog, configuration, advanced configuration, and alert operations."""

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
            # Log only the parameter names and identifiers: alert payloads can hold sensitive text.
            safe_params = {
                "keys": sorted(params) if isinstance(params, dict) else None,
                "id": params.get(PARAM_ALERT_ID) if isinstance(params, dict) else None,
                "website_id": params.get(PARAM_WEBSITE_ID) if isinstance(params, dict) else None,
            }
            logger.error(
                f"Error in website smart router: {e} | "
                f"resource_type={resource_type}, operation={operation}, params={safe_params}",
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
    
    @staticmethod
    def _check_legacy_fields(operation: str, payload: Dict[str, Any]) -> List[Dict[str, str]]:
        """Reject legacy single-rule fields on create (on update the client drops them)."""
        if operation != "create":
            return []
        return [
            {
                "field": field,
                "issue": f"top-level '{field}' is not supported",
                "hint": "Use 'rules' instead: [{\"rule\": {...}, \"thresholdOperator\": \">\", \"thresholds\": {\"WARNING\": {...}, \"CRITICAL\": {...}}}]",
            }
            for field in ALERT_LEGACY_RULE_FIELDS
            if field in payload
        ]

    @staticmethod
    def _check_channels(operation: str, payload: Dict[str, Any]) -> List[Dict[str, str]]:
        """Check the shape of alertChannelIds / alertChannels."""
        issues: List[Dict[str, str]] = []
        channel_ids = payload.get("alertChannelIds")
        channels = payload.get("alertChannels")
        # On update the config copied from find carries both fields, so only create enforces "one of".
        if operation == "create" and channel_ids and channels:
            issues.append({
                "field": "alertChannels",
                "issue": "send either alertChannelIds or alertChannels, not both",
            })
        if isinstance(channels, dict) and not set(channels) <= {"WARNING", "CRITICAL"}:
            issues.append({
                "field": "alertChannels",
                "issue": "alertChannels keys must be WARNING and/or CRITICAL",
            })
        return issues

    @staticmethod
    def _check_rules(payload: Dict[str, Any]) -> List[Dict[str, str]]:
        """Check that ``rules`` holds exactly one rule with WARNING and/or CRITICAL thresholds."""
        rules = payload.get("rules")
        if not rules:
            return []
        if not isinstance(rules, list) or len(rules) != 1:
            return [{"field": "rules", "issue": "rules must be a list with exactly one item"}]
        if not isinstance(rules[0], dict):
            return [{"field": "rules[0]", "issue": "rules[0] must be an object"}]
        thresholds = rules[0].get("thresholds")
        keys = set(thresholds) if isinstance(thresholds, dict) else set()
        if not keys or not keys <= {"WARNING", "CRITICAL"}:
            return [{
                "field": "rules[0].thresholds",
                "issue": "thresholds must contain WARNING, CRITICAL, or both, and no other keys",
            }]
        return []

    @classmethod
    def _validate_alert_payload(cls, operation: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Cheap pre-flight checks for create/update payloads; everything else is left to the server."""
        issues = cls._check_legacy_fields(operation, payload)
        issues += [
            {"field": field, "issue": f"{field} is required for {operation}"}
            for field in ("name", "description", "websiteId", "rules")
            if not payload.get(field)
        ]
        issues += cls._check_channels(operation, payload)
        issues += cls._check_rules(payload)

        if not issues:
            return None
        return {
            "elicitation_needed": True,
            "reason": "invalid_payload",
            "api_error": issues,
            "message": f"Invalid alert payload for {operation}. Fix the listed fields and retry.",
        }

    @staticmethod
    def _invalid_alert_operation(operation: str) -> Dict[str, Any]:
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

    async def _alert_find_active_website_alert_configs(self, params: Dict[str, Any], ctx) -> Dict[str, Any]:
        website_id = params.get(PARAM_WEBSITE_ID)
        if not website_id:
            return missing_param(
                "website_id", "website_id is required for find_active_website_alert_configs",
                "Use resource_type='configuration', operation='get_all' to list available website IDs")
        logger.debug(f"Routing to find_active_website_alert_configs with website_id={website_id}")
        return await self.website_alert_client.find_active_website_alert_configs(
            website_id=website_id,
            alert_ids=params.get(PARAM_ALERT_IDS),
            ctx=ctx,
            resource_type="alert", tool_name="manage_websites",
        )

    async def _alert_find_website_alert_config(self, params: Dict[str, Any], ctx) -> Dict[str, Any]:
        alert_id = _coerce_id(params.get(PARAM_ALERT_ID))
        valid_on = params.get(PARAM_VALID_ON)
        if not alert_id:
            return missing_param("id", "id is required for find_website_alert_config", ALERT_ID_HINT)
        if valid_on is not None:
            try:
                valid_on = _coerce_int(valid_on, "valid_on")
            except ValueError as e:
                return missing_param("valid_on", str(e), "valid_on is a Unix timestamp in milliseconds",
                                     reason="invalid_param")
        logger.debug(f"Routing to find_website_alert_config with id={alert_id}")
        return await self.website_alert_client.find_website_alert_config(
            id=alert_id,
            valid_on=valid_on,
            ctx=ctx,
            resource_type="alert", tool_name="manage_websites",
        )

    async def _alert_write(self, operation: str, params: Dict[str, Any], ctx) -> Dict[str, Any]:
        """Handle create and update."""
        alert_id = _coerce_id(params.get(PARAM_ALERT_ID))
        if operation == "update" and not alert_id:
            return missing_param("id", "id is required for update", ALERT_ID_HINT)

        payload = parse_payload(params.get(PARAM_PAYLOAD))
        payload_hint = "Provide the alert configuration as a JSON object. See the payload fields in the tool description."
        if not isinstance(payload, dict):
            return missing_param("payload", f"payload for {operation} must be a JSON object", payload_hint)
        if "error" in payload and len(payload) == 1:
            return missing_param(
                "payload", f"payload is required for {operation}: {payload['error']}", payload_hint
            )

        # Pre-flight: payload shape (avoids server 500s and ambiguous legacy fields)
        invalid = self._validate_alert_payload(operation, payload)
        if invalid:
            return invalid

        if operation == "create":
            return await self.website_alert_client.create_website_alert_config(
                payload=payload,
                ctx=ctx,
                resource_type="alert", tool_name="manage_websites",
            )
        return await self.website_alert_client.update_website_alert_config(
            id=alert_id,
            payload=payload,
            ctx=ctx,
            resource_type="alert", tool_name="manage_websites",
        )

    async def _alert_id_only(self, operation: str, params: Dict[str, Any], ctx) -> Dict[str, Any]:
        """Handle delete, enable, disable and find_versions."""
        alert_id = _coerce_id(params.get(PARAM_ALERT_ID))
        if not alert_id:
            return missing_param("id", f"id is required for {operation}", ALERT_ID_HINT)
        client_method = {
            "delete": self.website_alert_client.delete_website_alert_config,
            "enable": self.website_alert_client.enable_website_alert_config,
            "disable": self.website_alert_client.disable_website_alert_config,
            "find_versions": self.website_alert_client.find_website_alert_config_versions,
        }[operation]
        return await client_method(
            id=alert_id,
            ctx=ctx,
            resource_type="alert", tool_name="manage_websites",
        )

    async def _alert_restore(self, params: Dict[str, Any], ctx) -> Dict[str, Any]:
        alert_id = _coerce_id(params.get(PARAM_ALERT_ID))
        created = params.get(PARAM_CREATED)
        if not alert_id:
            return missing_param("id", "id is required for restore", ALERT_ID_HINT)
        created_hint = "Use operation='find_versions' to list versions and take a 'created' timestamp"
        if created is None:
            return missing_param("created", "created is required for restore", created_hint)
        try:
            created = _coerce_int(created, "created")
        except ValueError as e:
            return missing_param("created", str(e), created_hint, reason="invalid_param")
        return await self.website_alert_client.restore_website_alert_config(
            id=alert_id,
            created=created,
            ctx=ctx,
            resource_type="alert", tool_name="manage_websites",
        )

    async def _handle_alert(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
        ) -> Dict[str, Any]:
        """Route a Website alert operation to the alert client after pre-flight validation.

        Args:
            operation: One of ``ALERT_VALID_OPERATIONS``.
            params: Router parameters (``website_id``, ``alert_ids``, ``id``, ``valid_on``,
                ``payload``, ``created``).
            ctx: The MCP context (optional).

        Returns:
            ``{"resource_type", "operation", "results"}`` on success. For an error or an
            elicitation request (missing/invalid input) the client's dict is returned flat
            alongside ``resource_type`` and ``operation`` so ``error`` / ``elicitation_needed``
            are visible at the top level.
        """
        if operation not in ALERT_VALID_OPERATIONS:
            return self._invalid_alert_operation(operation)

        if operation == "find_active_website_alert_configs":
            result = await self._alert_find_active_website_alert_configs(params, ctx)
        elif operation == "find_website_alert_config":
            result = await self._alert_find_website_alert_config(params, ctx)
        elif operation in ("create", "update"):
            result = await self._alert_write(operation, params, ctx)
        elif operation in ALERT_ID_ONLY_OPERATIONS:
            result = await self._alert_id_only(operation, params, ctx)
        else:
            result = await self._alert_restore(params, ctx)

        # Errors and elicitation requests stay at the top level so a caller that only checks the
        # top-level keys does not mistake a failed write for a success.
        if isinstance(result, dict) and ("error" in result or result.get("elicitation_needed")):
            return {"resource_type": "alert", "operation": operation, **result}

        return {
            "resource_type": "alert",
            "operation": operation,
            "results": result
        }
