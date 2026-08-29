"""
Website Analyze MCP Tools Module

This module provides website analyze-specific MCP tools for Instana monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Constants
DEFAULT_GROUP_BY_TAG = 'beacon.location.path'  # Default grouping by URL path
DEFAULT_GROUP_BY_TAG_ENTITY = 'NOT_APPLICABLE'
DEFAULT_BEACON_TYPE = 'PAGELOAD'
DEFAULT_TIME_FRAME = {'windowSize': 3600000}
DEFAULT_GROUP_METRICS = [{'metric': 'beaconCount', 'aggregation': 'SUM'}]
DEFAULT_GROUP = {'groupByTag': 'beacon.page.name'}
DEFAULT_EMPTY_EXPRESSION = {'type': 'EXPRESSION', 'logicalOperator': 'AND', 'elements': []}
DEFAULT_BEACON_PAGINATION = {'retrievalSize': 20, 'offset': 0}


def clean_nan_values(data: Any) -> Any:
    """
    Recursively clean 'NaN' string values from data structures.
    This is needed because the Instana API sometimes returns 'NaN' as strings
    instead of proper null values, which causes Pydantic validation errors.
    """
    if isinstance(data, dict):
        return {key: clean_nan_values(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif isinstance(data, str) and data == 'NaN':
        return None
    else:
        return data

# Import the necessary classes from the SDK
try:
    from instana_client.api.website_analyze_api import WebsiteAnalyzeApi
    from instana_client.models.get_website_beacon_groups import GetWebsiteBeaconGroups
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from mcp.types import ToolAnnotations

from src.core.utils import (
    BaseInstanaClient,
    decode_response,
    register_as_tool,
    with_header_auth,
)
from src.core.validation import VALID_WEBSITE_BEACON_TYPES, StructureValidator

# Configure logger for this module
logger = logging.getLogger(__name__)


class WebsiteAnalyzeMCPTools(BaseInstanaClient):
    def _collect_structure_validation_errors(self, validators: List[tuple[Any, Any, Dict[str, Any]]]) -> List[str]:
        errors: List[str] = []
        for validator, value, kwargs in validators:
            result = validator(value, **kwargs)
            if result:
                errors.extend(result["api_error"])
        return errors

    def _build_validation_error_response(self, operation: str, errors: List[str]) -> Dict[str, Any]:
        return {
            "elicitation_needed": True,
            "reason": f"{operation} payload has {len(errors)} validation problem(s)",
            "api_error": errors,
            "message": (
                f"The {operation} payload has {len(errors)} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    def _apply_beacon_group_defaults(
        self,
        beacon_type: Optional[str],
        time_frame: Optional[Dict[str, int]],
        metrics: Optional[List[Dict[str, Any]]],
        group: Optional[Dict[str, str]],
        tag_filter_expression: Optional[Dict[str, Any]],
    ) -> tuple[str, Dict[str, int], List[Dict[str, Any]], Dict[str, str], Dict[str, Any]]:
        beacon_type = beacon_type or DEFAULT_BEACON_TYPE
        time_frame = time_frame or DEFAULT_TIME_FRAME.copy()
        metrics = metrics or [metric.copy() for metric in DEFAULT_GROUP_METRICS]
        group = group or DEFAULT_GROUP.copy()
        tag_filter_expression = tag_filter_expression or {
            "type": DEFAULT_EMPTY_EXPRESSION["type"],
            "logicalOperator": DEFAULT_EMPTY_EXPRESSION["logicalOperator"],
            "elements": list(DEFAULT_EMPTY_EXPRESSION["elements"]),
        }
        return beacon_type, time_frame, metrics, group, tag_filter_expression

    def _validate_group_metrics_if_needed(
        self,
        user_provided_metrics: bool,
        metrics: List[Dict[str, Any]],
        beacon_type: str,
        api_client,
    ) -> Optional[Dict[str, Any]]:
        if not user_provided_metrics:
            return None

        from instana_client.api.website_catalog_api import WebsiteCatalogApi

        from src.core.metric_validation import (
            fetch_metric_catalog_internal,
            validate_beacon_type_known,
            validate_metric_compatibility,
        )
        from src.core.utils import WEBSITE_BEACON_TYPE_MAP

        beacon_type_error = validate_beacon_type_known(
            beacon_type=beacon_type,
            beacon_type_map=WEBSITE_BEACON_TYPE_MAP,
        )
        if beacon_type_error:
            return beacon_type_error

        catalog_result = fetch_metric_catalog_internal(
            api_client=api_client,
            catalog_api_class=WebsiteCatalogApi,
            fetch_method_name="get_website_catalog_metrics_without_preload_content",
        )
        if isinstance(catalog_result, dict) and "error" in catalog_result:
            return catalog_result

        return validate_metric_compatibility(
            metrics=metrics,
            beacon_type=beacon_type,
            catalog=catalog_result,
            beacon_type_map=WEBSITE_BEACON_TYPE_MAP,
            catalog_operation="get_metrics",
        )

    def _map_group_fields(self, group: Dict[str, str]) -> Dict[str, str]:
        mapped_group: Dict[str, str] = {}
        if "groupByTag" in group:
            mapped_group["groupbyTag"] = group["groupByTag"]
        elif "groupbyTag" in group:
            mapped_group["groupbyTag"] = group["groupbyTag"]

        if "groupByTagEntity" in group:
            mapped_group["groupbyTagEntity"] = group["groupByTagEntity"]
        elif "groupbyTagEntity" in group:
            mapped_group["groupbyTagEntity"] = group["groupbyTagEntity"]

        # Optional 2nd-level key for key/value tags (e.g. the sub-key of
        # beacon.meta) — supported by the API's WebsiteBeaconTagGroup model
        second_level_key = (
            group.get("groupByTagSecondLevelKey")
            or group.get("groupbyTagSecondLevelKey")
        )
        if second_level_key:
            mapped_group["groupbyTagSecondLevelKey"] = second_level_key

        mapped_group.setdefault("groupbyTag", DEFAULT_GROUP_BY_TAG)
        mapped_group.setdefault("groupbyTagEntity", DEFAULT_GROUP_BY_TAG_ENTITY)
        return mapped_group

    def _convert_group_tag_filter(self, tag_filter_expression: Dict[str, Any]) -> tuple[Optional[Any], Optional[Dict[str, Any]]]:
        try:
            from instana_client.models.tag_filter_expression_element import (
                TagFilterExpressionElement,
            )
            tag_filter_obj = TagFilterExpressionElement.from_dict(tag_filter_expression)
            return tag_filter_obj, None
        except Exception as e:
            logger.error(f"[get_website_beacon_groups] Error converting tag filter expression: {e}")
            return None, {"error": f"Invalid tag filter expression: {e!s}"}

    def _build_beacon_groups_query_params(
        self,
        beacon_type: str,
        group: Dict[str, str],
        metrics: List[Dict[str, Any]],
        time_frame: Dict[str, int],
        tag_filter_expression: Dict[str, Any],
        order: Optional[Dict[str, str]],
        pagination: Optional[Dict[str, int]],
    ) -> Dict[str, Any] | Dict[str, str]:
        query_params: Dict[str, Any] = {
            "type": beacon_type,
            "group": self._map_group_fields(group),
            "metrics": metrics,
            "timeFrame": time_frame,
        }

        tag_filter_obj, error = self._convert_group_tag_filter(tag_filter_expression)
        if error:
            return error
        if tag_filter_obj:
            query_params["tagFilterExpression"] = tag_filter_obj
        if order:
            query_params["order"] = order
        if pagination:
            query_params["pagination"] = pagination
        return query_params

    def _normalize_beacon_pagination(self, pagination: Optional[Dict[str, int]]) -> Dict[str, int]:
        normalized = dict(pagination) if pagination else DEFAULT_BEACON_PAGINATION.copy()
        retrieval_size = normalized.get("retrievalSize", DEFAULT_BEACON_PAGINATION["retrievalSize"])
        if retrieval_size < 1:
            normalized["retrievalSize"] = 1
        elif retrieval_size > 200:
            normalized["retrievalSize"] = 200
        else:
            normalized["retrievalSize"] = retrieval_size
        normalized.setdefault("offset", DEFAULT_BEACON_PAGINATION["offset"])
        return normalized

    def _convert_beacon_tag_filters(self, tag_filter_expression: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not tag_filter_expression:
            return {}
        try:
            from instana_client.models.deprecated_tag_filter import DeprecatedTagFilter
            if tag_filter_expression.get("type") == "TAG_FILTER":
                name = tag_filter_expression.get("name")
                operator = tag_filter_expression.get("operator")
                value = tag_filter_expression.get("value")
                if not name or not operator or not value:
                    return {"error": "TAG_FILTER requires 'name', 'operator', and 'value' fields"}
                tag_filter_dict = {"name": name, "operator": operator, "value": value}
                if "entity" in tag_filter_expression:
                    tag_filter_dict["entity"] = tag_filter_expression.get("entity")
                return {"tagFilters": [DeprecatedTagFilter(**tag_filter_dict)]}
            if tag_filter_expression.get("type") == "EXPRESSION":
                elements = tag_filter_expression.get("elements", [])
                tag_filters = []
                for elem in elements:
                    if elem.get("type") == "TAG_FILTER":
                        tag_filter_dict = {
                            "name": elem.get("name"),
                            "operator": elem.get("operator"),
                            "value": elem.get("value"),
                        }
                        if "entity" in elem:
                            tag_filter_dict["entity"] = elem.get("entity")
                        tag_filters.append(DeprecatedTagFilter(**tag_filter_dict))
                return {"tagFilters": tag_filters} if tag_filters else {}
            return {}
        except Exception as e:
            logger.error(f"[get_website_beacons] Error converting tag filter expression: {e}")
            return {"error": f"Invalid tag filter expression: {e!s}"}

    def _build_beacons_query_params(
        self,
        beacon_type: str,
        time_frame: Dict[str, int],
        tag_filter_expression: Optional[Dict[str, Any]],
        pagination: Dict[str, int],
    ) -> Dict[str, Any]:
        query_params: Dict[str, Any] = {
            "type": beacon_type,
            "timeFrame": time_frame,
        }
        tag_filters = self._convert_beacon_tag_filters(tag_filter_expression)
        if "error" in tag_filters:
            return tag_filters
        query_params.update(tag_filters)
        return query_params
    """Tools for website analyze in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Website Analyze MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(WebsiteAnalyzeApi)
    async def get_website_beacon_groups(self,
    metrics: Optional[List[Dict[str, Any]]] = None,
    group: Optional[Dict[str, str]] = None,
    tag_filter_expression: Optional[Dict[str, Any]] = None,
    time_frame: Optional[Dict[str, int]] = None,
    beacon_type: Optional[str] = None,
    fill_time_series: Optional[bool] = True,
    order: Optional[Dict[str, str]] = None,
    pagination: Optional[Dict[str, int]] = None,
    ctx=None,
    api_client=None) -> Dict[str, Any]:
        """
        Get grouped website beacon metrics.

        This API endpoint retrieves grouped website monitoring beacon metrics, allowing you to analyze
        performance across different dimensions like page URLs, browsers, or geographic locations.

        Args:
            metrics: List of metrics to retrieve with their aggregations
                Example: [
                    {"metric": "beaconCount", "aggregation": "SUM", "granularity": 60}
                ]
            group: Grouping configuration
                Example: {"groupByTag": "beacon.page.name"}
                For key/value tags (e.g. `beacon.meta`), an optional
                `groupbyTagSecondLevelKey` selects the sub-key to group by:
                {"groupbyTag": "beacon.meta", "groupbyTagEntity": "NOT_APPLICABLE",
                 "groupbyTagSecondLevelKey": "myKey"}
            tag_filter_expression: Filter expression for tags
                Example: {
                    "type": "TAG_FILTER",
                    "name": "beacon.website.name",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "robot-shop"
                }
            time_frame: Time range for metrics
                Example: {"to": null, "windowSize": 3600000}
            beacon_type: Type of beacon (PAGELOAD, ERROR, RESOURCE, etc.)
            fill_time_series: Whether to fill missing data points with timestamp and value 0
            order: Ordering configuration
                Example: {"by": "beaconCount", "direction": "DESC"}
            pagination: Pagination configuration
                Example: {"retrievalSize": 20}
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing grouped website metrics data or error information
        """
        try:
            logger.debug(
                f"[get_website_beacon_groups] Called with metrics={metrics}, group={group}, "
                f"beacon_type={beacon_type}, time_frame={time_frame}"
            )

            user_provided_metrics = metrics is not None
            beacon_type = beacon_type or DEFAULT_BEACON_TYPE

            elicitation_request = self._check_elicitation_for_beacon_groups(metrics, group, beacon_type)
            if elicitation_request:
                return elicitation_request

            validation_errors = self._collect_structure_validation_errors([
                (StructureValidator.validate_metrics_array, metrics, {"required": False}),
                (StructureValidator.validate_group, group, {"required": False}),
                (StructureValidator.validate_tag_filter_expression, tag_filter_expression, {}),
                (StructureValidator.validate_time_frame, time_frame, {}),
                (StructureValidator.validate_order, order, {}),
                (StructureValidator.validate_pagination, pagination, {}),
            ])
            # Cross-field: granularity/windowSize ratio (granularity in seconds for website)
            _gr = StructureValidator.validate_granularity_ratio(metrics, time_frame, granularity_in_ms=False)
            if _gr:
                validation_errors = (validation_errors or []) + _gr["api_error"]
            if validation_errors:
                return self._build_validation_error_response("get_website_beacon_groups", validation_errors)

            tag_validation = self._validate_tag_names(tag_filter_expression, group, beacon_type, use_case="GROUPING")
            if tag_validation:
                return tag_validation

            beacon_type, time_frame, metrics, group, tag_filter_expression = self._apply_beacon_group_defaults(
                beacon_type,
                time_frame,
                metrics,
                group,
                tag_filter_expression,
            )

            compatibility_error = self._validate_group_metrics_if_needed(
                user_provided_metrics,
                metrics,
                beacon_type,
                api_client,
            )
            if compatibility_error:
                return compatibility_error

            query_params = self._build_beacon_groups_query_params(
                beacon_type,
                group,
                metrics,
                time_frame,
                tag_filter_expression,
                order,
                pagination,
            )
            if "error" in query_params:
                return query_params

            try:
                from instana_client.models.get_website_beacon_groups import (
                    GetWebsiteBeaconGroups,
                )
                config_object = GetWebsiteBeaconGroups(**query_params)
            except Exception as e:
                logger.error(f"[get_website_beacon_groups] Error creating GetWebsiteBeaconGroups object: {e!s}")
                return {"error": f"Failed to create beacon groups request: {e!s}"}

            # Call the get_beacon_groups method from the SDK
            logger.debug(f"[get_website_beacon_groups] Calling get_beacon_groups with fill_time_series={fill_time_series}")
            try:
                # Log the final payload being sent to API
                final_payload = {
                    "get_website_beacon_groups": config_object.to_dict(),
                    "fill_time_series": fill_time_series
                }
                logger.debug(f"[get_website_beacon_groups] Final API payload: {json.dumps(final_payload, indent=2)}")

                # Use without_preload_content to bypass Pydantic validation and handle NaN values manually
                response = api_client.get_beacon_groups_without_preload_content(
                    get_website_beacon_groups=config_object,
                    fill_time_series=fill_time_series
                )
                logger.debug("[get_website_beacon_groups] Successfully received response from get_beacon_groups")

                # Check if the response was successful
                if response.status != 200:
                    error_message = f"Failed to get website beacon groups: HTTP {response.status}"
                    logger.error(f"[get_website_beacon_groups] {error_message}")

                    # Try to get error details from response
                    try:
                        error_body = decode_response(response)
                        logger.error(f"[get_website_beacon_groups] API Error Response: {error_body}")

                        # Check if error is related to invalid metrics
                        try:
                            error_data = json.loads(error_body)
                            if "errors" in error_data and isinstance(error_data["errors"], list):
                                for error in error_data["errors"]:
                                    if isinstance(error, str) and "Metric type unknown" in error:
                                        logger.warning(f"[get_website_beacon_groups] Invalid metric detected: {error}")
                                        return {
                                            "elicitation_needed": True,
                                            "reason": f"Invalid metric detected: {error}",
                                            "api_error": error_data["errors"],
                                            "required_action": {
                                                "resource_type": "catalog",
                                                "operation": "get_metrics",
                                                "params": {}
                                            },
                                            "message": "Please call get_catalog_metrics first to get the list of valid metric names, then use those exact metric names in your request."
                                        }
                        except json.JSONDecodeError:
                            pass

                        return {
                            "error": error_message,
                            "details": error_body,
                            "status_code": response.status
                        }
                    except Exception:
                        return {"error": error_message, "status_code": response.status}

                #Read the response
                response_text = decode_response(response)

                # Parse the response as JSON
                result_dict = json.loads(response_text)

                logger.debug("[get_website_beacon_groups] Successfully parsed raw response")
                logger.debug(f"[get_website_beacon_groups] Result keys: {list(result_dict.keys())}")

                return result_dict

            except Exception as api_error:
                # Handle validation errors from the SDK
                error_msg = str(api_error)
                if "customMetric" in error_msg and "NaN" in error_msg:
                    logger.warning(f"[get_website_beacon_groups] API returned 'NaN' values for customMetric field: {error_msg}")
                    return {"error": "API returned invalid data (NaN values for customMetric field). This is a known issue with the Instana API response format.",
                    "details": error_msg,
                    "suggestion": "Try using a different time range or filtering criteria to avoid beacons with NaN customMetric values."
                    }
                else:
                    raise api_error
        except Exception as e:
            logger.error(f"[get_website_beacon_groups] Error: {e}", exc_info=True)
            return {"error": f"Failed to get website beacon groups: {e!s}"}

    def _summarize_beacons_response(self, response_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a structured summary of beacons response with clean, relevant fields.

        Returns:
        {
            "summary": {
                "totalHits": ...,
                "canLoadMore": ...,
                "timeframe": {...}
            },
            "beacons": [
                {
                    "websiteLabel": "...",
                    "timestamp": ...,
                    "duration": ...,
                    "page": "...",
                    // ... only relevant fields
                }
            ]
        }

        This reduces response size by ~70-80% while keeping all essential data.
        """
        if not isinstance(response_data, dict):
            return response_data

        # Essential fields to extract from each beacon
        essential_fields = [
            # Identity
            "websiteLabel", "websiteId", "beaconId", "pageLoadId", "label",
            # Timing
            "timestamp", "duration", "clockSkew",
            # Performance metrics
            "backendTime", "frontendTime", "requestTime", "responseTime",
            "processingTime", "domTime", "childrenTime",
            "firstPaintTime", "firstContentfulPaintTime", "largestContentfulPaintTime",
            "firstInputDelayTime", "cumulativeLayoutShift", "interactionNextPaint",
            # Page context
            "page", "phase", "type", "locationUrl", "locationPath", "locationOrigin",
            # User context
            "browserName", "browserVersion", "osName", "osVersion",
            "city", "country", "continent",
            "userIp", "connectionType",
            # Error info
            "errorCount", "errorMessage", "errorType",
            # Error diagnostic fields (for ERROR beacons)
            "stackTrace", "parsedStackTrace", "errorId", "stackTraceReadability",
            # Session and user tracking (all beacon types)
            "sessionId",
            # Backend correlation (for PAGELOAD beacons)
            "backendTraceId",
            # HTTP metrics (if applicable)
            "httpCallStatus", "httpCallMethod", "httpCallUrl",
            # Resource info
            "initiator", "resourceType",
            # Other
            "batchSize", "bytesIngested"
        ]

        result = {
            "summary": {
                "totalHits": response_data.get("totalHits", 0),
                "totalRepresentedItemCount": response_data.get("totalRepresentedItemCount", 0),
                "totalRetainedItemCount": response_data.get("totalRetainedItemCount", 0),
                "canLoadMore": response_data.get("canLoadMore", False),
            },
            "beacons": []
        }

        # Add timeframe if present
        if "adjustedTimeframe" in response_data:
            result["summary"]["timeframe"] = response_data["adjustedTimeframe"]

        # Process items (beacons)
        if "items" in response_data and isinstance(response_data["items"], list):
            for item in response_data["items"]:
                if not isinstance(item, dict) or "beacon" not in item:
                    continue

                beacon = item["beacon"]
                if not isinstance(beacon, dict):
                    continue

                # Extract only essential fields
                clean_beacon = {}
                for field in essential_fields:
                    if field in beacon:
                        value = beacon[field]
                        # Skip empty/default values
                        if value == "" or value == -1 or value is None:
                            continue
                        if isinstance(value, list) and len(value) == 0:
                            continue
                        if isinstance(value, dict) and len(value) == 0:
                            continue
                        # Skip 0 for timing fields that indicate "not measured"
                        if value == 0 and field in {"errorCount", "firstInputDelayTime", "interactionNextPaint"}:
                            continue

                        clean_beacon[field] = value

                result["beacons"].append(clean_beacon)

        return result

    @with_header_auth(WebsiteAnalyzeApi)
    async def get_website_beacons(
        self,
        tag_filter_expression: Optional[Dict[str, Any]] = None,
        time_frame: Optional[Dict[str, int]] = None,
        beacon_type: Optional[str] = None,
        pagination: Optional[Dict[str, int]] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get website beacon metrics with pagination support.

        This API endpoint retrieves website monitoring beacon metrics with matching type.
        By default, returns 20 beacons per page (matching UI behavior).

        Args:
            tag_filter_expression: Filter expression for tags
            time_frame: Time range for metrics
            beacon_type: Type of beacon (PAGELOAD, ERROR, etc.)
            pagination: Pagination configuration with:
                - retrievalSize: Number of items per page (default: 20, min: 1, max: 200)
                - offset: Number of items to skip from ingestionTime (default: 0)
                - ingestionTime: Starting timestamp in Unix epoch (optional)
                Example: {"retrievalSize": 20, "offset": 0}
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing website beacon data with matching type or error information
        """
        try:
            logger.debug(
                f"[get_website_beacons] Called with beacon_type={beacon_type}, "
                f"pagination={pagination}, time_frame={time_frame}"
            )

            validation_errors = self._collect_structure_validation_errors([
                (StructureValidator.validate_beacon_type, beacon_type, {"valid_types": VALID_WEBSITE_BEACON_TYPES}),
                (StructureValidator.validate_tag_filter_expression, tag_filter_expression, {}),
                (StructureValidator.validate_time_frame, time_frame, {}),
                (StructureValidator.validate_pagination, pagination, {}),
            ])
            if validation_errors:
                return self._build_validation_error_response("get_website_beacons", validation_errors)

            if not beacon_type:
                return {
                    "elicitation_needed": True,
                    "missing_parameters": [{
                        "name": "beacon_type",
                        "description": "Type of beacon to retrieve (REQUIRED)",
                        "examples": sorted(VALID_WEBSITE_BEACON_TYPES)
                    }],
                    "message": (
                        "Please provide the beacon type you want to retrieve. "
                        f"Valid values: {sorted(VALID_WEBSITE_BEACON_TYPES)}"
                    )
                }

            tag_validation = self._validate_tag_names(tag_filter_expression, None, beacon_type, use_case="FILTERING")
            if tag_validation:
                return tag_validation

            time_frame = time_frame or DEFAULT_TIME_FRAME.copy()
            pagination = self._normalize_beacon_pagination(pagination)
            query_params = self._build_beacons_query_params(
                beacon_type,
                time_frame,
                tag_filter_expression,
                pagination,
            )
            if "error" in query_params:
                return query_params

            from instana_client.models.cursor_pagination import CursorPagination
            try:
                query_params["pagination"] = CursorPagination(**pagination)
            except Exception as e:
                logger.error(f"[get_website_beacons] Error creating CursorPagination object: {e}")
                return {"error": f"Invalid pagination configuration: {e!s}"}

            try:
                from instana_client.models.get_website_beacons import GetWebsiteBeacons
                config_object = GetWebsiteBeacons(**query_params)
            except Exception as e:
                logger.error(f"[get_website_beacons] Error creating GetWebsiteBeacons object: {e!s}")
                return {"error": f"Failed to create GetWebsiteBeacons object: {e!s}"}

            # Make API call
            logger.debug("[get_website_beacons] Making API call to get website beacons")
            result = api_client.get_beacons_without_preload_content(get_website_beacons=config_object)

            # Process results
            response_text = decode_response(result)
            result_dict = json.loads(response_text)

            # Clean NaN values
            result_dict = clean_nan_values(result_dict)

            # Ensure we always return a dictionary
            if isinstance(result_dict, list):
                result_dict = {"beacons": result_dict,
                "count": len(result_dict)}

            elif not isinstance(result_dict, dict):
                result_dict = {"data": result_dict}

            logger.debug(f"[get_website_beacons] Result before summarization: {len(str(result_dict))} chars")

            # Summarize the response to remove redundant data
            summarized_result = self._summarize_beacons_response(result_dict)
            logger.debug(
                f"[get_website_beacons] Result after summarization: {len(str(summarized_result))} chars "
                f"(reduced by {len(str(result_dict)) - len(str(summarized_result))} chars)"
            )

            return summarized_result

        except Exception as e:
            logger.error(f"[get_website_beacons] Error: {e}", exc_info=True)
            return {"error": f"Failed to get website beacons: {e!s}"}


    def _check_elicitation_for_beacon_groups(
        self,
        metrics: Optional[List[Dict[str, Any]]],
        group: Optional[Dict[str, str]],
        beacon_type: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Check for required and recommended parameters (Two-Pass Elicitation).

        Args:
            metrics: Metrics list if provided
            group: Group configuration if provided
            beacon_type: Beacon type if provided

        Returns:
           Elicitation request dict if parameters are missing, None otherwise
        """
        missing_params = []

        #Check for REQUIRED parameters
        if not metrics:
            missing_params.append({
                "name": "metrics",
                "description": "List of metric names with aggregations (REQUIRED)",
                "examples": [
                    {"metric": "beaconCount", "aggregation": "SUM"},
                    {"metric": "onLoadTime", "aggregation": "MEAN"}
                ]
            })

        if not group:
            missing_params.append({
                "name": "group",
                "description": "Grouping configuration (REQUIRED)",
                "examples": [
                    {"groupByTag": "beacon.page.name"},
                    {"groupByTag": "beacon.user.country"}
                ]
            })

        if not beacon_type:
            missing_params.append({
                "name": "beacon_type",
                "description": "Type of beacon to analyze (REQUIRED)",
                "examples": ["PAGELOAD", "ERROR", "RESOURCE", "JAVASCRIPT_ERROR"]
            })

        if missing_params:
            return {
                "elicitation_required": True,
                "missing_parameters": missing_params,
                "message": "Please provide the required parameters to get website beacon groups",
                "elicitation_prompt": "To retrieve website beacon groups, I need:\n" +
                 "\n".join([f"- {p['name']}: {p['description']}" for p in missing_params])
            }

        return None

    def _validate_tag_names(
        self,
        tag_filter_expression: Optional[Dict[str, Any]],
        group: Optional[Dict[str, str]],
        beacon_type: str,
        use_case: str = "GROUPING"
    ) -> Optional[Dict[str, Any]]:
        """
        Validate that tag names follow the beacon.* pattern AND that entity field is present in TAG_FILTER.
        Returns elicitation if tags are invalid, missing, or entity field is missing.

        Args:
            tag_filter_expression: Tag filter expression to validate
            group: Group configuration to validate
            beacon_type: Beacon type for catalog call
            use_case: Use case for catalog call (GROUPING or FILTERING)

        Returns:
            Elicitation dict if validation fails, None if valid
        """
        invalid_tags = []
        missing_entity_tags = []

        # Helper function to extract tag names and check entity field
        def extract_and_validate_tags(expr):
            tags = []
            if not expr:
                return tags

            if isinstance(expr, dict):
                # Single TAG_FILTER
                if expr.get("type") == "TAG_FILTER":
                    tag_name = expr.get("name")
                    if tag_name:
                        tags.append(tag_name)
                        # CRITICAL: Check if entity field is present
                        if "entity" not in expr or expr.get("entity") is None:
                            missing_entity_tags.append(tag_name)

                # EXPRESSION with elements
                elif expr.get("type") == "EXPRESSION":
                    elements = expr.get("elements", [])
                    for element in elements:
                        tags.extend(extract_and_validate_tags(element))

            return tags

        # Extract tag names from tag_filter_expression and validate entity field
        filter_tags = extract_and_validate_tags(tag_filter_expression)

        # Extract tag name from group
        group_tag = None
        if group:
            # Handle both groupByTag and groupbyTag
            group_tag = group.get("groupByTag") or group.get("groupbyTag")

        # Combine all tags
        all_tags = filter_tags + ([group_tag] if group_tag else [])

        # Validate each tag name format
        for tag in all_tags:
            if tag:
                # Check if tag follows beacon.* pattern
                if not tag.startswith("beacon."):
                    invalid_tags.append(tag)

        # PRIORITY 1: Check for missing entity field (most common error)
        if missing_entity_tags:
            logger.warning(f"TAG_FILTER missing required 'entity' field for tags: {missing_entity_tags}")
            return {
                "elicitation_needed": True,
                "reason": f"TAG_FILTER is missing required 'entity' field for tags: {', '.join(missing_entity_tags)}",
                "missing_entity_tags": missing_entity_tags,
                "message": (
                    f"CRITICAL ERROR: Your TAG_FILTER for tags {missing_entity_tags} is missing the required 'entity' field.\n\n"
                    f"EVERY TAG_FILTER MUST include an 'entity' field with one of these values:\n"
                    f"- 'NOT_APPLICABLE' (for website/browser/OS/user/geo tags)\n"
                    f"- 'DESTINATION' (for page/endpoint tags)\n"
                    f"- 'SOURCE' (for backend/service tags)\n\n"
                    f"Example CORRECT format:\n"
                    f'{{"type": "TAG_FILTER", "name": "beacon.website.name", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Robot Shop"}}\n\n'
                    f"NEVER omit the 'entity' field or set it to null. It is REQUIRED for all TAG_FILTER expressions."
                )
            }

        # PRIORITY 2: Check for invalid tag names
        if invalid_tags:
            logger.warning(f"Invalid tag names detected: {invalid_tags}")
            return {
                "elicitation_needed": True,
                "reason": f"Invalid tag names detected: {', '.join(invalid_tags)}",
                "invalid_tags": invalid_tags,
                "required_action": {
                    "resource_type": "catalog",
                    "operation": "get_tag_catalog",
                    "params": {
                        "beacon_type": beacon_type,
                        "use_case": use_case
                    }
                },
                "message": f"Please call get_tag_catalog first to get valid tag names for beacon_type='{beacon_type}' and use_case='{use_case}'. Tag names must start with 'beacon.'"
            }

        # PRIORITY 3: Check if no tags provided at all
        if (tag_filter_expression or group) and not all_tags:
            logger.debug("Tag filter or group provided but no tag names extracted")
            return {
                "elicitation_needed": True,
                "reason": "No valid tag names found in tag_filter_expression or group",
                "required_action": {
                    "resource_type": "catalog",
                    "operation": "get_tag_catalog",
                    "params": {
                        "beacon_type": beacon_type,
                        "use_case": use_case
                    }
                },
                "message": f"Please call get_tag_catalog first to get valid tag names for beacon_type='{beacon_type}' and use_case='{use_case}'"
            }

        return None
