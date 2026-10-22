"""
Smart Router Tool for Synthetic Monitoring

This module provides a unified MCP tool that routes synthetic monitoring queries
to the appropriate specialized tools.
"""

import logging
import re
from typing import Any, Dict, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)

CATALOG_VALID_OPERATIONS = ["get_synthetic_catalog_metrics", "get_synthetic_tag_catalog"]
METRICS_VALID_OPERATIONS = ["get_metrics_result"]
SETTINGS_VALID_OPERATIONS = ["get_synthetic_test", "get_synthetic_tests", "get_locations", "get_location_by_id", "get_all_datacenters"]
TEST_PLAYBACK_VALID_OPERATIONS = ["get_synthetic_result", "get_synthetic_result_analytic", "get_synthetic_result_list", "get_location_summary_list", "get_synthetic_result_metadata", "get_test_summary_list", "get_synthetic_result_detail_data"]
ALERT_VALID_OPERATIONS = ["find_active", "find", "find_versions", "create", "update", "delete", "enable", "disable", "restore"]

ALERT_REQUIRED_PARAMS = {
    "find": ["id"],
    "find_versions": ["id"],
    "create": ["payload"],
    "update": ["id", "payload"],
    "delete": ["id"],
    "enable": ["id"],
    "disable": ["id"],
    "restore": ["id", "created"],
}
ALERT_MISSING_PARAM_MESSAGES = {
    ("create", "payload"): "Missing required parameter 'payload'. See SyntheticAlertConfig fields in the tool description.",
    ("update", "payload"): "Missing required parameter 'payload'. Fetch the current config via find first, then submit the full merged payload.",
    ("restore", "created"): "Missing required parameter 'created'. Use find_versions to get the creation timestamp of the desired version.",
}


_INT_STRING = re.compile(r"[+-]?[0-9]+")


def _coerce_int(value: Any, name: str) -> int:
    """Accept an int, a whole-number float, or an ASCII integer string; reject everything else.

    Booleans, NaN/inf, fractional floats, and non-ASCII digits (e.g. '²') are rejected so
    callers always get a field-aware error instead of a raw ``int()`` failure.
    """
    if isinstance(value, bool):
        raise ValueError(f"'{name}' must be an integer, got {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and _INT_STRING.fullmatch(value.strip()):
        return int(value)
    raise ValueError(f"'{name}' must be an integer, got {value!r}")


class SyntheticSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for synthetic monitoring operations.
    Routes queries to Synthetic Catalog, Metrics, Settings, and Test Playback tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Smart Router Synthetic MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
        from src.synthetic.synthetic_alert import SyntheticAlertMCPTools
        from src.synthetic.synthetic_catalog import SyntheticCatalogMCPTools
        from src.synthetic.synthetic_metrics import SyntheticMetricsMCPTools
        from src.synthetic.synthetic_settings import SyntheticSettingsMCPTools
        from src.synthetic.synthetic_test_playback_results import (
            SyntheticTestPlaybackResultsMCPTools,
        )

        # Initialize the synthetic clients
        self.synthetic_catalog_client = SyntheticCatalogMCPTools(read_token, base_url)
        self.synthetic_metrics_client = SyntheticMetricsMCPTools(read_token, base_url)
        self.synthetic_settings_client = SyntheticSettingsMCPTools(read_token, base_url)
        self.synthetic_test_playback_client = SyntheticTestPlaybackResultsMCPTools(read_token, base_url)
        self.synthetic_alert_client = SyntheticAlertMCPTools(read_token, base_url)

        logger.info("Smart Router Synthetic initialized with Catalog, Metrics, Settings, Test Playback, and Alert tools")

    @register_as_tool(
        title="Manage Instana Synthetic Resources",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
        description="""Unified Instana synthetic resource manager for catalog, metrics, settings, test playback operations, and smart alert configurations.

Resource Types:
    - "catalog": Get available metrics and tags for synthetic monitoring
    - "metrics": Retrieve aggregated synthetic monitoring metrics
    - "settings": Look up synthetic test configuration (id, label, description)
    - "test_playback": Retrieve synthetic test playback results
    - "alert": Manage Synthetic Smart Alert Configurations (CRUD + enable/disable/restore)

CRITICAL WORKFLOW:
    BEFORE any data query, call catalog first to get valid metric and tag names. Never guess.
    Pagination: for payload "pagination" objects (metrics, test_playback) always set {"page": 1, "pageSize": 20}
    unless user asks for more. For alert find_active use flat params page / page_size instead.

    METRIC FIELD FORMAT — within test_playback, two different formats are used:
    - "metrics" key with {metric, aggregation} objects — used by: get_synthetic_result, get_test_summary_list
    - "syntheticMetrics" key with plain name strings — used by: get_synthetic_result_list, get_synthetic_result_analytic
    Using the wrong key will cause a validation error.

CATALOG (resource_type="catalog"):
    operations: get_synthetic_catalog_metrics, get_synthetic_tag_catalog
    params: {use_case, view}

    get_synthetic_catalog_metrics - Get synthetic metrics catalog with necessary metadata for query
        planning (metricId, label, description, formatter, aggregations, beaconTypes).
        Use params.view="full" to retrieve raw SDK metadata (rarely needed).
    get_synthetic_tag_catalog - Get valid tag names for the given use_case.
        Valid use_case: "GROUPING", "FILTERING", "SMART_ALERTS"

METRICS (resource_type="metrics"):
    operations: get_metrics_result
    params: {payload}

    get_metrics_result - Retrieve one or more aggregated metrics for synthetic monitoring beacons.
        NOTE: always returns ONE scalar per group — NOT a time-series array. For day-by-day trend
        data use get_test_summary_list with granularity=86400 instead.
        payload: Complete request body as a dict or JSON string with the following fields:
            - metrics (required): List of metric/aggregation objects
                  e.g. [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]
            - timeFrame (optional): {"to": <unix_ms>, "windowSize": <milliseconds>}
            - pagination (optional): {"page": 1, "pageSize": 3}
            - groups (optional): List of grouping objects. Each object MUST include all three fields:
                  - groupbyTag (required): tag name from get_synthetic_tag_catalog (use_case="GROUPING")
                  - groupbyTagEntity (required): "NOT_APPLICABLE"
                  - direction (required): "ASC" or "DESC"
                  NOTE: get_metrics_result grouping responses do NOT return location/tag labels — only
                  metric values. To get failures broken down by named location, use get_test_summary_list
                  instead — each result item includes locationStatusList with per-location totalTestRuns,
                  successRuns, and successRate.
            - tagFilterExpression (optional): Tag filter expression object.
                  CRITICAL: ALL tag filters MUST include "entity": "NOT_APPLICABLE" for synthetic tags.
            - disableDefaultGroups (optional): boolean
            - includeAggregatedTestIds (optional): boolean

SETTINGS (resource_type="settings"):
    operations: get_synthetic_test, get_synthetic_tests, get_locations, get_location_by_id, get_all_datacenters
    params: {test_id, test_name, application_id, location_id, location_type, status, credential_name, sort, offset, limit, filter}

    get_synthetic_test - Retrieve a single synthetic test's full record.
        Supply either test_id (direct lookup) or test_name (name resolution).
        - test_id: The synthetic test ID (e.g. "CVkDqtbdHMR4pqms7K5N")
        - test_name: The synthetic test label (case-insensitive match)

    get_synthetic_tests - List synthetic tests, optionally filtered and paginated.
        params: {application_id, location_id, credential_name, sort, offset, limit, filter_param} — all optional.

    get_locations - List all locations with full metadata (id, label, displayLabel, locationType,
        status, geoPoint, customProperties.datacenterFlag, totalTests).
        locationType="Managed" = datacenter (IBM/AWS/Azure hosted). locationType="Private" = self-hosted PoP.
        To resolve a datacenter name to a locationId: call get_all_datacenters, match user input
        against displayLabel, label, or customProperties.datacenterFlag, use the id in TAG_FILTERs.
        params: {location_type, status, sort, offset, limit, filter} — all optional.

    get_location_by_id - Single location by location_id (direct) or location_name (resolves label/displayLabel,
        case-insensitive). Returns available_location_names on miss.

    get_all_datacenters - Convenience operation that returns ONLY Managed (datacenter) locations.
        Equivalent to get_locations with location_type="Managed" but also returns total_online count.
        Use this for fleet health scoring (total_online = denominator for health %).
        - status: Optional — "Online" to restrict to active datacenters only
        Returns: items, count, total_online, filters_applied

TEST_PLAYBACK (resource_type="test_playback"):
    operations: get_synthetic_result, get_synthetic_result_analytic, get_synthetic_result_list,
                get_location_summary_list, get_test_summary_list, get_synthetic_result_metadata,
                get_synthetic_result_detail_data
    All operations use payload param except metadata/detail which use flat params.
    ALL TagFilterExpression filters require "entity": "NOT_APPLICABLE".

    get_synthetic_result - Aggregated metrics. Uses "metrics" key.
        payload: {metrics, timeFrame, pagination, order}

    get_synthetic_result_analytic - Per-test reduction. Uses "syntheticMetrics" key.
        analyticFunction="LAST_VALUE" returns the most recent run per test.
        payload: {syntheticMetrics, analyticFunction, timeFrame, pagination, order, TagFilterExpression}

    get_synthetic_result_list - One row per run, no aggregation. Uses "syntheticMetrics" key.
        For metricsStatus filter use "numberValue": 1 (pass) / 0 (fail) — NOT plain "value".
        payload: {syntheticMetrics, timeFrame, pagination, order, TagFilterExpression}

    get_location_summary_list - PoP metadata only (id, label, status, linkedTests). No success rates.
        Use get_test_summary_list for health data. payload: {timeFrame, pagination}

    get_test_summary_list - Health, errors, and per-location pass rates in one call. Use for all health/failure/error questions.
        Each item has locationStatusList: [{locationId, successRate, totalTestRuns, successRuns, locationDisplayLabel, locationType}].
        Uses "metrics" key. payload: {metrics: [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}], timeFrame, pagination, TagFilterExpression}

    get_synthetic_result_metadata - Discover available detail file types. params (flat): {testid, testresultid, start_time}

    get_synthetic_result_detail_data - Download a detail file. Call metadata first to discover types.
        params (flat): {testid, testresultid, detail_type ("HAR"|"IMAGES"|"LOGS"|"SUBTRANSACTIONS"|"VIDEOS"), name, start_time}

ALERT (resource_type="alert"):
    operations: find_active, find, find_versions, create, update, delete, enable, disable, restore
    params: {id, synthetic_test_id, alert_ids, valid_on, created, payload}

    NOTE: create/update/delete/enable/disable/restore change live alerting.
    Confirm with the user before calling them.

    find_active - List all active Smart Alert Configurations
        params: {synthetic_test_id (optional), alert_ids (optional; list of IDs or a comma-separated string), page (optional, default 1), page_size (optional, default 50; "pageSize" is accepted as an alias)}
        Returns: Paginated configurations with count, total, page, page_size, total_pages, has_next, has_previous fields.
        Filter by synthetic_test_id to scope to a specific test.

    find - Get a specific Smart Alert Configuration by ID (may return deleted configs)
        params: {id (required), valid_on (optional Unix timestamp ms)}

    find_versions - Get all versions of a Smart Alert Configuration
        params: {id (required)}

    create - Create a new Smart Alert Configuration
        params: {payload (required)} — see SyntheticAlertConfig payload fields below

    update - Update an existing Smart Alert Configuration (requires ALL fields)
        CRITICAL: Fetch the current config via find first, merge your changes, then submit the full payload (find response can be passed directly).
        params: {id (required), payload (required, same as create)}

    delete - Delete a Smart Alert Configuration
        params: {id (required)}

    enable - Enable a Smart Alert Configuration
        params: {id (required)}

    disable - Disable a Smart Alert Configuration
        params: {id (required)}

    restore - Restore a deleted Smart Alert Configuration to a prior version
        params: {id (required), created (required — Unix timestamp from find_versions)}

    SyntheticAlertConfig payload fields:
        - name (required): str, alert title template (max 256 chars)
        - description (required): str, alert message template (max 65536 chars)
        - syntheticTestIds (required): List[str], IDs of synthetic tests to monitor
        - alertChannelIds (required): List[str], can be []
        - customPayloadFields (required): List[CustomPayloadField], can be [].
              Each entry: {"key": str (non-empty), "type": "staticString"|"dynamic"|"metricField",
              ...type-specific fields}
        - rule (required): {"alertType": "failure", "metricName": <metricId from
              get_synthetic_catalog_metrics>, "aggregation": optional, one of
              "SUM", "MEAN", "MAX", "MIN", "P25", "P50", "P75", "P90", "P95",
              "P98", "P99", "P99_9", "P99_99", "DISTINCT_COUNT", "SUM_POSITIVE",
              "PER_SECOND", "INCREASE"}
        - timeThreshold (required): {"type": "violationsInSequence",
              "violationsCount": optional int 1-12}
        - tagFilterExpression (required key): TagFilterExpressionElement object. null is
              rejected by the API (HTTP 422 "must not be null"); for no filter send
              {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}.
              Two subtypes (discriminated by "type"):
              - TAG_FILTER: {"type": "TAG_FILTER", "name": str, "entity": "NOT_APPLICABLE"|
                "SOURCE"|"DESTINATION" (use "NOT_APPLICABLE" for synthetic tags), "operator":
                one of "EQUALS","CONTAINS","NOT_EQUAL","NOT_CONTAIN","IS_EMPTY","NOT_EMPTY",
                "LESS_THAN","LESS_OR_EQUAL_THAN","GREATER_THAN","GREATER_OR_EQUAL_THAN",
                "NOT_BLANK","IS_BLANK","STARTS_WITH","ENDS_WITH","NOT_STARTS_WITH",
                "NOT_ENDS_WITH","REGEX_MATCH", "stringValue"/"numberValue"/"booleanValue"/
                "floatValue": value to match, "key": optional tag key}
                For alert configs, ALSO set "value" to the same value as the typed field
                (e.g. "stringValue": "us", "value": "us"). The API rejects a TAG_FILTER
                without it (HTTP 422 "Key value fields should be used in Tag Filters").
                This applies to alert payloads only; test_playback filters use just the typed field.
              - EXPRESSION: {"type": "EXPRESSION", "logicalOperator": "AND"|"OR",
                "elements": [list of nested TAG_FILTER or EXPRESSION objects]}
        - severity (optional): 5 (Warning) or 10 (Critical)
        - affectedLocationsCount (optional): int >= 1
        - evaluationType (optional): "PER_LOCATION" or "PER_SYNTHETIC_TEST"
        - gracePeriod (optional): int, ms the alert stays open after conditions clear
        - includeOnDemand (optional): bool

Args:
    resource_type: "catalog", "metrics", "settings", "test_playback", or "alert"
    operation: Specific operation for the resource type
    params: Operation-specific parameters (optional)

Returns:
    Dictionary with results from the appropriate tool

Examples:
    # catalog
    resource_type="catalog", operation="get_synthetic_catalog_metrics"
    resource_type="catalog", operation="get_synthetic_tag_catalog", params={"use_case": "FILTERING"}
    # metrics
    resource_type="metrics", operation="get_metrics_result", params={"payload": {"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}], "timeFrame": {"to": 0, "windowSize": 3600000}}}
    # settings
    resource_type="settings", operation="get_synthetic_test", params={"test_name": "Login Flow"}
    resource_type="settings", operation="get_synthetic_tests", params={"limit": 20, "sort": "+label"}
    resource_type="settings", operation="get_all_datacenters", params={"status": "Online"}
    resource_type="settings", operation="get_location_by_id", params={"location_name": "ap-south-1(Mumbai)"}
    # test_playback
    resource_type="test_playback", operation="get_synthetic_result_analytic", params={"payload": {"syntheticMetrics": ["synthetic.metricsResponseTime", "synthetic.metricsStatus"], "analyticFunction": "LAST_VALUE", "timeFrame": {"to": 0, "windowSize": 144000000}}}
    resource_type="test_playback", operation="get_synthetic_result_list", params={"payload": {"syntheticMetrics": ["synthetic.metricsStatus", "synthetic.errors"], "timeFrame": {"to": 0, "windowSize": 3600000}, "TagFilterExpression": {"type": "TAG_FILTER", "name": "synthetic.locationId", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "stringValue": "<location_id>"}}}
    resource_type="test_playback", operation="get_test_summary_list", params={"payload": {"metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}], "timeFrame": {"to": 0, "windowSize": 1800000}}}
    resource_type="test_playback", operation="get_synthetic_result_metadata", params={"testid": "abc123", "testresultid": "res456"}
    resource_type="test_playback", operation="get_synthetic_result_detail_data", params={"testid": "abc123", "testresultid": "res456", "detail_type": "HAR"}
    # alert
    resource_type="alert", operation="find_active"
    resource_type="alert", operation="find_active", params={"synthetic_test_id": "CVkDqtbdHMR4pqms7K5N"}
    resource_type="alert", operation="find_active", params={"page": 1, "page_size": 20}
    resource_type="alert", operation="find", params={"id": "alert-123"}
    resource_type="alert", operation="find_versions", params={"id": "alert-123"}
    resource_type="alert", operation="create", params={"payload": {"name": "Login test failing", "description": "Fails in 2+ locations", "syntheticTestIds": ["CVkDqtbdHMR4pqms7K5N"], "alertChannelIds": [], "customPayloadFields": [], "rule": {"alertType": "failure", "metricName": "synthetic.metricsStatus", "aggregation": "SUM"}, "timeThreshold": {"type": "violationsInSequence", "violationsCount": 2}, "tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}, "severity": 10, "affectedLocationsCount": 2, "evaluationType": "PER_LOCATION"}}
    resource_type="alert", operation="update", params={"id": "alert-123", "payload": <full config returned by find, with changes merged>}
    resource_type="alert", operation="delete", params={"id": "alert-123"}
    resource_type="alert", operation="enable", params={"id": "alert-123"}
    resource_type="alert", operation="disable", params={"id": "alert-123"}
    resource_type="alert", operation="restore", params={"id": "alert-123", "created": 1710658800000}"""
    )
    async def manage_synthetics(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Unified Instana synthetic resource manager for catalog, metrics, settings, test playback, and alert operations."""

        try:
            logger.debug("[manage_synthetics] resource_type=%s, operation=%s", resource_type, operation)

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate resource_type
            valid_resource_types = ["catalog", "metrics", "settings", "test_playback", "alert"]
            if resource_type not in valid_resource_types:
                logger.warning("[manage_synthetics] Invalid resource_type: %s", resource_type)
                return {
                    "elicitation_needed": True,
                    "reason": "invalid_resource_type",
                    "api_error": [
                        {
                            "field": "resource_type",
                            "issue": f"'{resource_type}' is not a valid resource type",
                            "expected": valid_resource_types
                        }
                    ],
                    "message": f"Invalid resource_type '{resource_type}'. Must be one of: {valid_resource_types}"
                }

            if resource_type == "catalog":
                return await self._handle_catalog(operation, params, ctx)
            elif resource_type == "metrics":
                if operation not in METRICS_VALID_OPERATIONS:
                    return {
                        "elicitation_needed": True,
                        "reason": "invalid_operation",
                        "api_error": [
                            {
                                "field": "operation",
                                "issue": f"'{operation}' is not a valid metrics operation",
                                "expected": METRICS_VALID_OPERATIONS
                            }
                        ],
                        "message": f"Invalid operation '{operation}' for resource_type 'metrics'. Valid operations: {METRICS_VALID_OPERATIONS}"
                    }
                payload = params.get("payload")
                logger.debug("[manage_synthetics] Routing to Synthetic Metrics get_metrics_result | payload=%s", payload)
                result = await self.synthetic_metrics_client.get_metrics_result(
                    payload=payload,
                    ctx=ctx,
                    resource_type="metrics", tool_name="manage_synthetics",
                )
                return {
                    "resource_type": "metrics",
                    "operation": operation,
                    "results": result,
                }
            elif resource_type == "settings":
                return await self._handle_settings(operation, params, ctx)

            elif resource_type == "test_playback":
                return await self._handle_test_playback(operation, params, ctx)

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
                            "expected": valid_resource_types
                        }
                    ],
                    "message": f"Unsupported resource_type '{resource_type}'. Must be one of: {valid_resource_types}"
                }

        except Exception as e:
            # Redact payload: alert payloads can contain user-supplied custom payload values.
            loggable_params = (
                {k: ("<redacted>" if k == "payload" else v) for k, v in params.items()}
                if isinstance(params, dict)
                else params
            )
            logger.error(
                "[manage_synthetics] Error in smart router: %s | resource_type=%s, operation=%s, params=%s",
                e, resource_type, operation, loggable_params,
                exc_info=True,
            )
            return {
                "error": f"Smart router error: {e!s}",
                "resource_type": resource_type,
                "operation": operation
            }

    async def _handle_catalog(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle Synthetic catalog operations."""

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

        try:
            if operation == "get_synthetic_catalog_metrics":
                view = params.get("view", "planner")
                logger.debug("[_handle_catalog] Routing to get_synthetic_catalog_metrics | view=%s", view)
                result = await self.synthetic_catalog_client.get_synthetic_catalog_metrics(
                    ctx=ctx, view=view,
                    resource_type="catalog", tool_name="manage_synthetics",
                )

            elif operation == "get_synthetic_tag_catalog":
                use_case = params.get("use_case")
                if not use_case:
                    logger.warning("[_handle_catalog] Missing required param for get_synthetic_tag_catalog: use_case")
                    return {
                        "elicitation_needed": True,
                        "reason": "Missing required parameter 'use_case'.",
                        "message": "Valid use_case values are: 'GROUPING', 'FILTERING', 'SMART_ALERTS'."
                    }
                logger.debug("[_handle_catalog] Routing to get_synthetic_tag_catalog | use_case=%s", use_case)
                result = await self.synthetic_catalog_client.get_synthetic_tag_catalog(
                    use_case=use_case,
                    ctx=ctx,
                    resource_type="catalog", tool_name="manage_synthetics",
                )


            # Return structured response
            return {
                "resource_type": "catalog",
                "operation": operation,
                "results": result
            }

        except Exception as e:
            logger.error("[_handle_catalog] Error: %s", e, exc_info=True)
            return {
                "error": f"[_handle_catalog] Error: {e!s}",
                "resource_type": "catalog",
                "operation": operation
            }

    async def _handle_settings(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle Synthetic settings operations."""

        if operation not in SETTINGS_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid settings operation",
                        "expected": SETTINGS_VALID_OPERATIONS
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'settings'. Valid operations: {SETTINGS_VALID_OPERATIONS}"
            }

        try:
            if operation == "get_synthetic_test":
                test_id = params.get("test_id")
                test_name = params.get("test_name")
                logger.debug("[_handle_settings] Routing to get_synthetic_test | test_id=%s, test_name=%s", test_id, test_name)
                result = await self.synthetic_settings_client.get_synthetic_test(
                    test_id=test_id,
                    test_name=test_name,
                    ctx=ctx,
                    resource_type="settings", tool_name="manage_synthetics",
                )

            elif operation == "get_synthetic_tests":
                logger.debug("[_handle_settings] Routing to get_synthetic_tests | params=%s", params)
                result = await self.synthetic_settings_client.get_synthetic_tests(
                    application_id=params.get("application_id"),
                    location_id=params.get("location_id"),
                    credential_name=params.get("credential_name"),
                    sort=params.get("sort"),
                    offset=params.get("offset"),
                    limit=params.get("limit"),
                    filter_param=params.get("filter"),
                    ctx=ctx,
                    resource_type="settings", tool_name="manage_synthetics",
                )

            elif operation == "get_locations":
                logger.debug("[_handle_settings] Routing to get_locations | params=%s", params)
                result = await self.synthetic_settings_client.get_locations(
                    location_type=params.get("location_type"),
                    status=params.get("status"),
                    sort=params.get("sort"),
                    offset=params.get("offset"),
                    limit=params.get("limit"),
                    filter=params.get("filter"),
                    ctx=ctx,
                    resource_type="settings", tool_name="manage_synthetics",
                )

            elif operation == "get_location_by_id":
                location_id = params.get("location_id")
                location_name = params.get("location_name")
                logger.debug("[_handle_settings] Routing to get_location_by_id | location_id=%s, location_name=%s", location_id, location_name)
                result = await self.synthetic_settings_client.get_location_by_id(
                    location_id=location_id,
                    location_name=location_name,
                    ctx=ctx,
                    resource_type="settings", tool_name="manage_synthetics",
                )

            elif operation == "get_all_datacenters":
                logger.debug("[_handle_settings] Routing to get_all_datacenters | params=%s", params)
                result = await self.synthetic_settings_client.get_all_datacenters(
                    status=params.get("status"),
                    ctx=ctx,
                    resource_type="settings", tool_name="manage_synthetics",
                )


            return {
                "resource_type": "settings",
                "operation": operation,
                "results": result
            }

        except Exception as e:
            logger.error("[_handle_settings] Error: %s", e, exc_info=True)
            return {
                "error": f"[_handle_settings] Error: {e!s}",
                "resource_type": "settings",
                "operation": operation
            }

    async def _handle_test_playback(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle Synthetic test playback results operations."""

        if operation not in TEST_PLAYBACK_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid test_playback operation",
                        "expected": TEST_PLAYBACK_VALID_OPERATIONS
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'test_playback'. Valid operations: {TEST_PLAYBACK_VALID_OPERATIONS}"
            }

        try:
            logger.debug("[_handle_test_playback] Routing to execute_playback_operation | operation=%s, params=%s", operation, params)
            result = await self.synthetic_test_playback_client.execute_playback_operation(
                operation=operation,
                params=params,
                ctx=ctx,
                resource_type="test_playback", tool_name="manage_synthetics",
            )

            return {
                "resource_type": "test_playback",
                "operation": operation,
                "results": result,
            }

        except Exception as e:
            logger.error("[_handle_test_playback] Error: %s", e, exc_info=True)
            return {
                "error": f"[_handle_test_playback] Error: {e!s}",
                "resource_type": "test_playback",
                "operation": operation
            }


    def _missing_alert_param_error(self, operation: str, field: str) -> Dict[str, Any]:
        """Build an elicitation error for a missing required alert parameter."""
        error: Dict[str, Any] = {"field": field, "issue": f"{field} is required for {operation}"}
        if field == "id" and operation in ("find", "find_versions"):
            error["hint"] = "Use operation='find_active' to list available alert config IDs"
        elif field == "created":
            error["issue"] = "created (Unix timestamp) is required for restore"
            error["hint"] = "Use operation='find_versions' to get the creation timestamp of a prior version"

        message = ALERT_MISSING_PARAM_MESSAGES.get((operation, field), f"Missing required parameter '{field}'.")
        return {
            "elicitation_needed": True,
            "reason": "missing_required_params",
            "api_error": [error],
            "message": message,
        }

    def _validate_alert_operation(self, operation: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return an error dict if *params* fail validation for *operation*, else None."""
        for field in ALERT_REQUIRED_PARAMS.get(operation, []):
            value = params.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                return self._missing_alert_param_error(operation, field)
        return None

    async def _call_alert_client(self, operation: str, params: Dict[str, Any], ctx):
        """Dispatch a pre-validated alert operation to the appropriate client method."""
        # Coerce only the numeric params the given operation actually uses, so a stray
        # value on an unrelated operation does not fail the call.
        valid_on = created = page = page_size = None
        # The shared pagination guidance uses camelCase "pageSize"; accept it as an alias.
        raw_page_size = params.get("page_size")
        if raw_page_size is None:
            raw_page_size = params.get("pageSize")
        try:
            if operation == "find" and params.get("valid_on") is not None:
                valid_on = _coerce_int(params["valid_on"], "valid_on")
            elif operation == "restore":
                created = _coerce_int(params["created"], "created")
            elif operation == "find_active":
                if params.get("page") is not None:
                    page = _coerce_int(params["page"], "page")
                if raw_page_size is not None:
                    page_size = _coerce_int(raw_page_size, "page_size")
        except ValueError as e:
            return {"error": str(e)}

        alert_ids = params.get("alert_ids")
        if isinstance(alert_ids, str):
            alert_ids = [a.strip() for a in alert_ids.split(",") if a.strip()]

        c = self.synthetic_alert_client
        kw = {"ctx": ctx, "resource_type": "alert", "tool_name": "manage_synthetics"}
        handlers = {
            "find_active": lambda: c.find_active_synthetic_alert_configs(
                synthetic_test_id=params.get("synthetic_test_id"),
                alert_ids=alert_ids,
                page=page,
                page_size=page_size,
                **kw,
            ),
            "find": lambda: c.find_synthetic_alert_config(id=params["id"], valid_on=valid_on, **kw),
            "find_versions": lambda: c.find_synthetic_alert_config_versions(id=params["id"], **kw),
            "create": lambda: c.create_synthetic_alert_config(payload=params["payload"], **kw),
            "update": lambda: c.update_synthetic_alert_config(id=params["id"], payload=params["payload"], **kw),
            "delete": lambda: c.delete_synthetic_alert_config(id=params["id"], **kw),
            "enable": lambda: c.enable_synthetic_alert_config(id=params["id"], **kw),
            "disable": lambda: c.disable_synthetic_alert_config(id=params["id"], **kw),
            "restore": lambda: c.restore_synthetic_alert_config(id=params["id"], created=created, **kw),
        }
        return await handlers[operation]()

    async def _handle_alert(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx,
    ) -> Dict[str, Any]:
        """Handle Synthetic smart alert configuration operations."""

        if operation not in ALERT_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid alert operation",
                        "expected": ALERT_VALID_OPERATIONS,
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'alert'. Valid operations: {ALERT_VALID_OPERATIONS}",
            }

        error = self._validate_alert_operation(operation, params)
        if error:
            return error

        try:
            logger.debug("[_handle_alert] Routing operation=%s", operation)
            result = await self._call_alert_client(operation, params, ctx)
        except Exception as e:
            logger.error("[_handle_alert] Error: %s", e, exc_info=True)
            return {
                "error": f"[_handle_alert] Error: {e!s}",
                "resource_type": "alert",
                "operation": operation,
            }

        # Surface validation/API failures at the top level (like the missing-param and
        # invalid-operation elicitations above) instead of burying them under "results".
        if result.get("elicitation_needed") or result.get("error"):
            return result

        return {
            "resource_type": "alert",
            "operation": operation,
            "results": result,
        }
