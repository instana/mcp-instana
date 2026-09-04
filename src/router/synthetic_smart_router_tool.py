"""
Smart Router Tool for Synthetic Monitoring

This module provides a unified MCP tool that routes synthetic monitoring queries
to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)

CATALOG_VALID_OPERATIONS = ["get_synthetic_catalog_metrics", "get_synthetic_tag_catalog"]
METRICS_VALID_OPERATIONS = ["get_metrics_result"]
SETTINGS_VALID_OPERATIONS = ["get_synthetic_test", "get_synthetic_tests", "get_locations", "get_location_by_id", "get_all_datacenters"]
TEST_PLAYBACK_VALID_OPERATIONS = ["get_synthetic_result", "get_synthetic_result_analytic", "get_synthetic_result_list", "get_location_summary_list", "get_synthetic_result_metadata", "get_test_summary_list", "get_synthetic_result_detail_data"]

class SyntheticSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for synthetic monitoring operations.
    Routes queries to Synthetic Catalog, Metrics, Settings, and Test Playback tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Smart Router Synthetic MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
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

        logger.info("Smart Router Synthetic initialized with Catalog, Metrics, Settings, and Test Playback tools")

    @register_as_tool(
        title="Manage Instana Synthetic Resources",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        description="""Unified Instana synthetic resource manager for catalog, metrics, settings, and test playback operations.

Resource Types:
    - "catalog": Get available metrics and tags for synthetic monitoring
    - "metrics": Retrieve aggregated synthetic monitoring metrics
    - "settings": Look up synthetic test configuration (id, label, description)
    - "test_playback": Retrieve synthetic test playback results

CRITICAL WORKFLOW:
    BEFORE any data query, call catalog first to get valid metric and tag names. Never guess.
    Pagination: always set {"page": 1, "pageSize": 20} unless user asks for more.

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

Args:
    resource_type: "catalog", "metrics", "settings" or "test_playback"
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
    resource_type="test_playback", operation="get_synthetic_result_detail_data", params={"testid": "abc123", "testresultid": "res456", "detail_type": "HAR"}"""
    )
    async def manage_synthetics(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Unified Instana synthetic resource manager for catalog, metrics, and settings operations."""

        try:
            logger.debug("[manage_synthetics] resource_type=%s, operation=%s", resource_type, operation)

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate resource_type
            valid_resource_types = ["catalog", "metrics", "settings", "test_playback"]
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
            logger.error(
                "[manage_synthetics] Error in smart router: %s | resource_type=%s, operation=%s, params=%s",
                e, resource_type, operation, params,
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
