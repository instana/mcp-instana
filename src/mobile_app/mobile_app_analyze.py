"""
Mobile App Analyze MCP Tools Module

This module provides mobile app analyze-specific MCP tools for Instana monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

DEFAULT_GROUP_BY_TAG = 'mobileBeacon.view.name'  # Default grouping by URL path
DEFAULT_GROUP_BY_TAG_ENTITY = 'NOT_APPLICABLE'
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 200

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


try:
    from instana_client.api.mobile_app_analyze_api import MobileAppAnalyzeApi
    from instana_client.models.get_mobile_app_beacon_groups import (
        GetMobileAppBeaconGroups,
    )
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from instana_client import DeprecatedTagFilter
from mcp.types import ToolAnnotations

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    decode_response,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)
from src.core.validation import (
    ENTITY_GUIDANCE_EUM,
    VALID_MOBILE_BEACON_TYPES,
    StructureValidator,
)

logger = logging.getLogger(__name__)


class MobileAppAnalyzeMCPTools(BaseInstanaClient):
    """Tools for mobile app analyze in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Mobile App Analyze MCP Tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    def _apply_beacon_groups_defaults(
        self,
        beacon_type: Optional[str],
        metrics: Optional[List[Dict[str, Any]]],
        group: Optional[Dict[str, str]],
        time_frame: Optional[Dict[str, int]],
        tag_filter_expression: Optional[Dict[str, Any]]
    ) -> tuple[str, List[Dict[str, Any]], Dict[str, str], Dict[str, int], Dict[str, Any]]:
        """Apply default values for beacon groups parameters."""
        if not beacon_type:
            beacon_type = "SESSION_START"
            logger.debug("[get_mobile_app_beacon_groups] Applied default beacon_type: SESSION_START")

        if not time_frame:
            time_frame = {"windowSize": 3600000}
            logger.debug("[get_mobile_app_beacon_groups] Applied default time_frame: 1 hour (3600000ms)")

        if not metrics:
            metrics = [{"metric": "beaconCount", "aggregation": "SUM"}]
            logger.debug("[get_mobile_app_beacon_groups] Applied default metrics: beaconCount SUM")

        if not group:
            group = {"groupbyTag": "mobileBeacon.mobileApp.name"}
            logger.debug("[get_mobile_app_beacon_groups] Applied default group: mobileBeacon.mobileApp.name")

        if not tag_filter_expression:
            tag_filter_expression = {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}
            logger.debug("[get_mobile_app_beacon_groups] Applied default tag filter expression: empty EXPRESSION with AND operator")

        return beacon_type, metrics, group, time_frame, tag_filter_expression

    def _build_beacon_groups_query_params(
        self,
        beacon_type: str,
        metrics: List[Dict[str, Any]],
        group: Dict[str, str],
        time_frame: Dict[str, int],
        tag_filter_expression: Dict[str, Any],
        order: Optional[Dict[str, str]],
        pagination: Optional[Dict[str, int]]
    ) -> Union[Dict[str, Any], Dict[str, str]]:
        """Build query parameters for beacon groups request."""
        query_params = {
            "type": beacon_type,
            "metrics": metrics,
            "timeFrame": time_frame
        }

        # Handle group field with field name mapping
        # Normalize to lowercase 'groupbyTag' (canonical format for API)
        mapped_group = {
            "groupbyTag": group.get("groupbyTag") or group.get("groupByTag", DEFAULT_GROUP_BY_TAG),
            "groupbyTagEntity": group.get("groupbyTagEntity") or group.get("groupByTagEntity", DEFAULT_GROUP_BY_TAG_ENTITY),
        }
        query_params["group"] = mapped_group

        # Convert tag filter expression to SDK model
        if tag_filter_expression:
            try:
                from instana_client.models.tag_filter_expression_element import (
                    TagFilterExpressionElement,
                )
                tag_filter_obj = TagFilterExpressionElement.from_dict(tag_filter_expression)
                query_params["tagFilterExpression"] = tag_filter_obj
                logger.debug(f"[get_mobile_app_beacon_groups] Converted tag filter to SDK object: {tag_filter_obj.to_dict()}")
            except Exception as e:
                logger.error(f"[get_mobile_app_beacon_groups] Error converting tag filter expression: {e}")
                return {
                    "error": {
                        "message": f"Invalid tag filter expression: {e!s}",
                        "type": "TAG_FILTER_PARSE_ERROR"
                    }
                }

        if order:
            query_params["order"] = order
        if pagination:
            query_params["pagination"] = pagination

        return query_params

    def _check_metric_error(self, error_body: str) -> Optional[Dict[str, Any]]:
        """Check if error is related to invalid metrics and return elicitation if needed."""
        try:
            error_data = json.loads(error_body)
            if "errors" in error_data and isinstance(error_data["errors"], list):
                for error in error_data["errors"]:
                    if isinstance(error, str) and "Metric type unknown" in error:
                        logger.warning(f"[get_mobile_app_beacon_groups] Invalid metric detected: {error}")
                        return {
                            "elicitation_needed": True,
                            "reason": f"Invalid metric detected: {error}",
                            "api_error": error_data["errors"],
                            "required_action": {
                                "resource_type": "catalog",
                                "operation": "get_mobile_app_metric_catalog",
                                "params": {}
                            },
                            "message": "Please call get_mobile_app_metric_catalog first to get the list of valid metric names, then use those exact metric names in your request."
                        }
        except json.JSONDecodeError:
            pass
        return None

    def _handle_beacon_groups_error_response(self, response, error_body: str) -> Dict[str, Any]:
        """Handle error response from beacon groups API with special handling for metric errors."""
        metric_error = self._check_metric_error(error_body)
        if metric_error:
            return metric_error
        return self.handle_api_error_response(response, "get mobile app beacon groups", logger)

    @staticmethod
    def _validate_beacon_group_structure(
        metrics: Optional[List[Dict[str, Any]]],
        group: Optional[Dict[str, str]],
        tag_filter_expression: Optional[Dict[str, Any]],
        time_frame: Optional[Dict[str, int]],
        order: Optional[Dict[str, str]],
        pagination: Optional[Dict[str, int]],
    ) -> Optional[Dict[str, Any]]:
        """Run structural validators; return an elicitation dict on failure, else None."""
        errors: List[str] = []
        for validator_fn, field_val, kwargs in [
            (StructureValidator.validate_metrics_array, metrics, {"required": False}),
            (StructureValidator.validate_group, group, {"required": False, "entity_guidance": ENTITY_GUIDANCE_EUM}),
            (StructureValidator.validate_tag_filter_expression, tag_filter_expression, {}),
            (StructureValidator.validate_time_frame, time_frame, {}),
            (StructureValidator.validate_order, order, {}),
            (StructureValidator.validate_pagination, pagination, {}),
        ]:
            result = validator_fn(field_val, **kwargs)
            if result:
                errors.extend(result["api_error"])
        # Cross-field: granularity/windowSize ratio (granularity in seconds for mobile)
        _gr = StructureValidator.validate_granularity_ratio(metrics, time_frame, granularity_in_ms=False)
        if _gr:
            errors.extend(_gr["api_error"])
        if not errors:
            return None
        return {
            "elicitation_needed": True,
            "reason": f"get_mobile_app_beacon_groups payload has {len(errors)} validation problem(s)",
            "api_error": errors,
            "message": (
                f"The get_mobile_app_beacon_groups payload has {len(errors)} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    async def _validate_metric_compatibility_for_beacon_groups(
        self,
        metrics: List[Dict[str, Any]],
        beacon_type: str,
        api_client: Any,
        ctx=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Validate metric/beacon-type compatibility; return an error dict or None."""
        from instana_client.api.mobile_app_catalog_api import MobileAppCatalogApi

        from src.core.metric_validation import (
            fetch_metric_catalog_internal,
            validate_beacon_type_known,
            validate_metric_compatibility,
        )
        from src.core.utils import MOBILE_BEACON_TYPE_MAP

        beacon_type_error = validate_beacon_type_known(
            beacon_type=beacon_type,
            beacon_type_map=MOBILE_BEACON_TYPE_MAP,
        )
        if beacon_type_error:
            return beacon_type_error

        catalog_result = await fetch_metric_catalog_internal(
            api_client=api_client,
            catalog_api_class=MobileAppCatalogApi,
            fetch_method_name="get_mobile_app_metric_catalog_without_preload_content",
            ctx=ctx,
            resource_type=resource_type,
            tool_name=tool_name,
        )
        if isinstance(catalog_result, dict) and "error" in catalog_result:
            return catalog_result

        return validate_metric_compatibility(
            metrics=metrics,
            beacon_type=beacon_type,
            catalog=catalog_result,
            beacon_type_map=MOBILE_BEACON_TYPE_MAP,
            catalog_operation="get_mobile_app_metric_catalog",
        )

    @with_header_auth(MobileAppAnalyzeApi)
    async def get_mobile_app_beacon_groups(self,
    metrics: Optional[List[Dict[str, Any]]] = None,
    group: Optional[Dict[str, str]] = None,
    tag_filter_expression: Optional[Dict[str, Any]] = None,
    time_frame: Optional[Dict[str, int]] = None,
    beacon_type: Optional[str] = None,
    fill_time_series: Optional[bool] = True,
    order: Optional[Dict[str, str]] = None,
    pagination: Optional[Dict[str, int]] = None,
    ctx=None,
    api_client=None,
    resource_type: Optional[str] = None,
    tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get grouped mobile app beacon metrics.

        This API endpoint retrieves grouped mobile app monitoring beacon metrics, allowing you to analyze
        performance across different dimensions like mobile apps, browsers, or geographic locations.

        Args:
            metrics: List of metrics to retrieve with their aggregations
                Example: [
                    {"metric": "beaconCount", "aggregation": "SUM", "granularity": 60}
                ]
            group: Grouping configuration. The `group` parameter MUST follow this schema:

                {
                    "groupbyTag": "<tag_name>",
                    "groupbyTagEntity": "<entity_type>"
                }

                Rules:
                - Only `groupbyTag` and `groupbyTagEntity` keys are supported.
                - camelCase variants such as `groupByTag` are NOT supported.
                - If `group` is not provided, default grouping will be applied.
                - If `group` is provided but fields are missing:
                    - groupbyTag defaults to: mobileBeacon.mobileApp.name
                    - groupbyTagEntity defaults to: NOT_APPLICABLE
            tag_filter_expression: Filter expression for tags
                Example: {
                    "type": "TAG_FILTER",
                    "name": "mobileBeacon.mobileApp.name",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "robot-shop"
                }
            time_frame: Time range for metrics
                Example: {"to": null, "windowSize": 3600000}
            beacon_type: Type of beacon (SESSION_START, VIEW_CHANGE, PERF, etc.)
            fill_time_series: Whether to fill missing data points with timestamp and value 0
            order: Ordering configuration
                Example: {"by": "beaconCount", "direction": "DESC"}
            pagination: Pagination configuration
                Example: {"retrievalSize": 20}
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing grouped mobile app metrics data or error information
        """
        try:
            logger.debug(
                f"[get_mobile_app_beacon_groups] Called with metrics={metrics}, group={group}, "
                f"beacon_type={beacon_type}, time_frame={time_frame}"
            )

            user_provided_metrics = metrics is not None
            user_provided_group = group is not None
            user_provided_tag_filter = tag_filter_expression is not None and (
                tag_filter_expression.get("type") == "TAG_FILTER" or
                (tag_filter_expression.get("type") == "EXPRESSION" and tag_filter_expression.get("elements"))
            )

            elicitation_request = self._check_elicitation_for_beacon_groups(metrics, group, beacon_type)
            if elicitation_request:
                return elicitation_request

            validation_error = self._validate_beacon_group_structure(
                metrics, group, tag_filter_expression, time_frame, order, pagination
            )
            if validation_error:
                return validation_error

            beacon_type, metrics, group, time_frame, tag_filter_expression = (
                self._apply_beacon_groups_defaults(
                    beacon_type, metrics, group, time_frame, tag_filter_expression
                )
            )

            if user_provided_metrics:
                metric_validation = self._validate_metrics(metrics, user_provided=True)
                if metric_validation:
                    return metric_validation

            if user_provided_group or user_provided_tag_filter:
                tag_validation = self._validate_tag_names(
                    tag_filter_expression, group, beacon_type, use_case="GROUPING"
                )
                if tag_validation:
                    return tag_validation

            if user_provided_metrics:
                compatibility_error = await self._validate_metric_compatibility_for_beacon_groups(
                    metrics, beacon_type, api_client, ctx=ctx,
                    resource_type=resource_type, tool_name=tool_name,
                )
                if compatibility_error:
                    return compatibility_error

            query_params = self._build_beacon_groups_query_params(
                beacon_type, metrics, group, time_frame, tag_filter_expression, order, pagination
            )
            if "error" in query_params:
                return query_params

            return await self._execute_beacon_groups_api_call(query_params, fill_time_series, api_client, ctx, resource_type=resource_type, tool_name=tool_name)

        except Exception as e:
            logger.error(f"[get_mobile_app_beacon_groups] Error: {e}", exc_info=True)
            return {"error": f"Failed to get mobile app beacon groups: {e!s}"}

    async def _execute_beacon_groups_api_call(
        self,
        query_params: Dict[str, Any],
        fill_time_series: bool,
        api_client,
        ctx=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the beacon groups API call and handle response."""
        try:
            from instana_client.models.get_mobile_app_beacon_groups import (
                GetMobileAppBeaconGroups,
            )
            logger.debug(f"[get_mobile_app_beacon_groups] Creating GetMobileAppBeaconGroups with params: {query_params}")
            config_object = GetMobileAppBeaconGroups(**query_params)
            logger.debug(f"[get_mobile_app_beacon_groups] Successfully created GetMobileAppBeaconGroups, Config object dict: {config_object.to_dict()}")
        except Exception as e:
            logger.error(f"[get_mobile_app_beacon_groups] Error creating GetMobileAppBeaconGroups object: {e!s}")
            return {"error": f"Failed to create beacon groups request: {e!s}"}

        logger.debug(f"[get_mobile_app_beacon_groups] Calling get_beacon_groups with fill_time_series={fill_time_series}")
        try:
            final_payload = {
                "get_mobile_app_beacon_groups": config_object.to_dict(),
                "fill_time_series": fill_time_series
            }
            logger.debug(f"[get_mobile_app_beacon_groups] Final API payload: {json.dumps(final_payload, indent=2)}")

            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_mobile_app_beacon_groups_without_preload_content,
                    get_mobile_app_beacon_groups=config_object,
                    fill_time_series=fill_time_series,
                ),
                ctx=ctx,
                operation_name="get_mobile_app_beacon_groups",
                resource_type=resource_type,
                tool_name=tool_name,
            )
            logger.debug("[get_mobile_app_beacon_groups] Successfully received response from get_beacon_groups")

            if response.status != 200:
                error_body = decode_response(response)
                logger.error(f"[get_mobile_app_beacon_groups] API Error Response: {error_body}")
                return self._handle_beacon_groups_error_response(response, error_body)

            response_text = decode_response(response)
            result_dict = json.loads(response_text)

            logger.debug("[get_mobile_app_beacon_groups] Successfully parsed raw response")
            logger.debug(f"[get_mobile_app_beacon_groups] Result keys: {list(result_dict.keys())}")

            return result_dict

        except Exception as api_error:
            return self._handle_nan_error(api_error)

    def _handle_nan_error(self, api_error: Exception) -> Dict[str, Any]:
        """Handle NaN-related API errors."""
        error_msg = str(api_error)
        if "customMetric" in error_msg and "NaN" in error_msg:
            logger.warning(f"[get_mobile_app_beacon_groups] API returned 'NaN' values for customMetric field: {error_msg}")
            return {
                "error": "API returned invalid data (NaN values for customMetric field). This is a known issue with the Instana API response format.",
                "details": error_msg,
                "suggestion": "Try using a different time range or filtering criteria to avoid beacons with NaN customMetric values."
            }
        # Re-raise the original exception if it's not a NaN error
        raise ValueError(f"API error: {error_msg}") from api_error

    def _apply_beacons_defaults(
        self,
        time_frame: Optional[Dict[str, int]],
        pagination: Optional[Dict[str, int]],
        filter_fields: Optional[bool]
    ) -> tuple[Dict[str, int], Dict[str, int], bool]:
        """Apply default values for beacons parameters."""
        if not time_frame:
            time_frame = {"windowSize": 3600000}
            logger.debug("[get_mobile_app_beacons] Applied default time_frame: 1 hour (3600000ms)")

        if not pagination:
            pagination = {"retrievalSize": 20, "offset": 0}
            logger.debug("[get_mobile_app_beacons] Applied default pagination: 20 items per page, offset 0")
        else:
            pagination = self._validate_pagination(pagination)

        if filter_fields is None:
            filter_fields = True
            logger.debug("[get_mobile_app_beacons] Applied default filter_fields: True")

        return time_frame, pagination, filter_fields

    def _validate_pagination(self, pagination: Dict[str, int]) -> Dict[str, int]:
        """Validate and adjust pagination parameters."""
        if "retrievalSize" in pagination:
            retrieval_size = pagination["retrievalSize"]
            if retrieval_size < MIN_PAGE_SIZE:
                pagination["retrievalSize"] = MIN_PAGE_SIZE
                logger.warning(f"[get_mobile_app_beacons] retrievalSize {retrieval_size} is below minimum ({MIN_PAGE_SIZE}), setting to {MIN_PAGE_SIZE}")
            elif retrieval_size > MAX_PAGE_SIZE:
                pagination["retrievalSize"] = MAX_PAGE_SIZE
                logger.warning(f"[get_mobile_app_beacons] retrievalSize {retrieval_size} is above maximum ({MAX_PAGE_SIZE}), setting to {MAX_PAGE_SIZE}")
        else:
            pagination["retrievalSize"] = 20

        if "offset" not in pagination:
            pagination["offset"] = 0

        return pagination

    def _convert_single_tag_filter(self, tag_filter: Dict[str, Any]) -> Union[Any, Dict[str, Any]]:
        """Convert a single TAG_FILTER to DeprecatedTagFilter."""
        from instana_client.models.deprecated_tag_filter import DeprecatedTagFilter

        name = tag_filter.get("name")
        operator = tag_filter.get("operator")
        value = tag_filter.get("value")

        if not name or not operator or not value:
            return {"error": "TAG_FILTER requires 'name', 'operator', and 'value' fields"}

        tag_filter_dict = {"name": name, "operator": operator, "value": value}
        if "entity" in tag_filter:
            tag_filter_dict["entity"] = tag_filter.get("entity")

        return DeprecatedTagFilter(**tag_filter_dict)

    def _convert_expression_filters(self, elements: List[Dict[str, Any]]) -> List[Any]:
        """Convert EXPRESSION elements to list of DeprecatedTagFilter."""
        from instana_client.models.deprecated_tag_filter import DeprecatedTagFilter

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
        return tag_filters

    def _convert_tag_filter_to_deprecated(
        self,
        tag_filter_expression: Dict[str, Any]
    ) -> Union[List[Any], Dict[str, Any]]:
        """
        Convert tag filter expression to deprecated tag filters.

        Returns:
            - List[DeprecatedTagFilter]: Successfully converted filters
            - Dict with 'error' key: Conversion error occurred
            - Empty list: No filters to convert
        """
        # Single TAG_FILTER
        if tag_filter_expression.get("type") == "TAG_FILTER":
            result = self._convert_single_tag_filter(tag_filter_expression)
            if isinstance(result, dict) and "error" in result:
                return result
            logger.debug(f"[get_mobile_app_beacons] Converted single TAG_FILTER to DeprecatedTagFilter: {result.to_dict()}")
            return [result]

        # EXPRESSION with elements
        elif tag_filter_expression.get("type") == "EXPRESSION":
            elements = tag_filter_expression.get("elements", [])
            if elements:
                tag_filters = self._convert_expression_filters(elements)
                if tag_filters:
                    logger.debug(f"[get_mobile_app_beacons] Converted {len(tag_filters)} TAG_FILTERs from EXPRESSION")
                    return tag_filters
            else:
                logger.debug("[get_mobile_app_beacons] Empty EXPRESSION - no tag filters applied")

        return []

    def _build_beacons_query_params(
        self,
        beacon_type: str,
        time_frame: Dict[str, int],
        tag_filter_expression: Optional[Dict[str, Any]],
        pagination: Dict[str, int]
    ) -> Union[Dict[str, Any], Dict[str, str]]:
        """Build query parameters for beacons request."""
        query_params = {"type": beacon_type, "timeFrame": time_frame}

        # Convert tag filters
        if tag_filter_expression:
            try:
                conversion_result = self._convert_tag_filter_to_deprecated(tag_filter_expression)
                if isinstance(conversion_result, dict):
                    return conversion_result  # Return error
                if conversion_result:  # Non-empty list
                    query_params["tagFilters"] = conversion_result
            except Exception as e:
                logger.error(f"[get_mobile_app_beacons] Error converting tag filter expression: {e}")
                return {"error": f"Invalid tag filter expression: {e!s}"}

        # Add pagination
        from instana_client.models.cursor_pagination import CursorPagination
        try:
            pagination_obj = CursorPagination(**pagination)
            query_params["pagination"] = pagination_obj
            logger.debug(f"[get_mobile_app_beacons] Applied pagination: {pagination_obj.to_dict()}")
        except Exception as e:
            logger.error(f"[get_mobile_app_beacons] Error creating CursorPagination object: {e}")
            return {"error": f"Invalid pagination configuration: {e!s}"}

        return query_params

    def _process_beacons_response(self, result, filter_fields: bool = True) -> Dict[str, Any]:
        """Process and summarize beacons API response."""
        response_text = decode_response(result)
        result_dict = json.loads(response_text)
        result_dict = clean_nan_values(result_dict)

        # Ensure dictionary format
        if isinstance(result_dict, list):
            result_dict = {"beacons": result_dict, "count": len(result_dict)}
        elif not isinstance(result_dict, dict):
            result_dict = {"data": result_dict}

        logger.debug(f"[get_mobile_app_beacons] Result before summarization: {len(str(result_dict))} chars")

        summarized_result = self._summarize_beacons_response(result_dict, filter_fields)
        logger.debug(
            f"[get_mobile_app_beacons] Result after summarization: {len(str(summarized_result))} chars "
            f"(reduced by {len(str(result_dict)) - len(str(summarized_result))} chars)"
        )

        return summarized_result

    @with_header_auth(MobileAppAnalyzeApi)
    async def get_all_mobile_app_beacons(
        self,
        tag_filter_expression: Optional[Dict[str, Any]] = None,
        time_frame: Optional[Dict[str, int]] = None,
        beacon_type: Optional[str] = None,
        pagination: Optional[Dict[str, int]] = None,
        filter_fields: bool = True,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get mobile app beacon metrics with pagination support.

        This API endpoint retrieves mobile app monitoring beacon metrics with matching type.
        By default, returns 20 beacons per page (matching UI behaviour).

        Args:
            tag_filter_expression: Filter expression for tags
            time_frame: Time range for metrics
            beacon_type: Type of beacon (SESSION_START ,HTTP_REQUEST, etc.)
            pagination: Pagination configuration with:
                - retrievalSize: Number of items per page (default: 20, min: 1, max: 200)
                - offset: Number of items to skip from ingestionTime (default: 0)
                - ingestionTime: Starting timestamp in Unix epoch (optional)
                Example: {"retrievalSize": 20, "offset": 0}
            filter_fields: Whether beacon data should have "non-essential" fields removed or be returned as is
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing mobile app beacon data with matching type or error information.
        """
        try:
            logger.debug(
                f"[get_mobile_app_beacons] Called with beacon_type={beacon_type}, "
                f"pagination={pagination}, time_frame={time_frame}"
            )

            # STEP 1: Pre-flight structural validation (collect ALL errors in one pass)
            _sv_errors: List[str] = []
            for _sv_fn, _sv_val, _sv_kw in [
                (StructureValidator.validate_beacon_type, beacon_type,
                    {"valid_types": VALID_MOBILE_BEACON_TYPES}),
                (StructureValidator.validate_tag_filter_expression, tag_filter_expression, {}),
                (StructureValidator.validate_time_frame, time_frame, {}),
                (StructureValidator.validate_pagination, pagination, {}),
            ]:
                _sv_res = _sv_fn(_sv_val, **_sv_kw)
                if _sv_res:
                    _sv_errors.extend(_sv_res["api_error"])
            if _sv_errors:
                return {
                    "elicitation_needed": True,
                    "reason": f"get_all_mobile_app_beacons payload has {len(_sv_errors)} validation problem(s)",
                    "api_error": _sv_errors,
                    "message": (
                        f"The get_all_mobile_app_beacons payload has {len(_sv_errors)} problem(s). "
                        "Correct all issues below and retry:\n"
                        + "\n".join(f"  - {e}" for e in _sv_errors)
                    ),
                }

            # STEP 2: Required parameter check (beacon_type was not invalid but is missing)
            if not beacon_type:
                return {
                    "elicitation_needed": True,
                    "missing_parameters": [{
                        "name": "beacon_type",
                        "description": "Type of beacon to retrieve (REQUIRED)",
                        "examples": sorted(VALID_MOBILE_BEACON_TYPES)
                    }],
                    "message": (
                        "Please provide the beacon type you want to retrieve. "
                        f"Valid values: {sorted(VALID_MOBILE_BEACON_TYPES)}"
                    )
                }

            # STEP 3: Apply defaults AFTER validation
            time_frame, pagination, filter_fields = self._apply_beacons_defaults(time_frame, pagination, filter_fields)

            # STEP 4: Validate user-provided filters
            has_user_filter = (
                tag_filter_expression is not None
                and tag_filter_expression.get("type") == "TAG_FILTER"
                or (tag_filter_expression and tag_filter_expression.get("elements"))
            )

            if has_user_filter:
                tag_validation = self._validate_tag_names(
                    tag_filter_expression, None, beacon_type, use_case="FILTERING"
                )
                if tag_validation:
                    return tag_validation

            # Build query parameters
            query_params = self._build_beacons_query_params(
                beacon_type, time_frame, tag_filter_expression, pagination
            )
            if "error" in query_params:
                return query_params

            logger.debug(f"[get_mobile_app_beacons] Creating GetMobileAppBeacons with params: {query_params}")

            # Create config object
            try:
                from instana_client.models.get_mobile_app_beacons import (
                    GetMobileAppBeacons,
                )
                config_object = GetMobileAppBeacons(**query_params)
                logger.debug(f"[get_mobile_app_beacons] Successfully created GetMobileAppBeacons object: {config_object.to_dict()}")
            except Exception as e:
                logger.error(f"[get_mobile_app_beacons] Error creating GetMobileAppBeacons object: {e!s}")
                return {"error": f"Failed to create GetMobileAppBeacons object: {e!s}"}

            # Make API call
            logger.debug("[get_mobile_app_beacons] Making API call to get mobile app beacons")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_mobile_app_beacons_without_preload_content,
                    get_mobile_app_beacons=config_object),
                ctx=ctx,
                operation_name="get_mobile_app_beacons",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            # Process and return results
            return self._process_beacons_response(result, filter_fields)

        except Exception as e:
            logger.error(f"[get_mobile_app_beacons] Error: {e}", exc_info=True)
            return {"error": f"Failed to get mobile app beacons: {e!s}"}

    def _extract_tags_and_check_entity(
        self,
        expr: Optional[Dict[str, Any]],
        missing_entity_tags: List[str]
    ) -> List[str]:
        """Extract tag names from expression and check for missing entity field."""
        tags = []
        if not expr or not isinstance(expr, dict):
            return tags

        if expr.get("type") == "TAG_FILTER":
            tag_name = expr.get("name")
            if tag_name:
                tags.append(tag_name)
                if "entity" not in expr or expr.get("entity") is None:
                    missing_entity_tags.append(tag_name)
        elif expr.get("type") == "EXPRESSION":
            elements = expr.get("elements", [])
            for element in elements:
                tags.extend(self._extract_tags_and_check_entity(element, missing_entity_tags))

        return tags

    def _create_missing_entity_error(self, missing_entity_tags: List[str]) -> Dict[str, Any]:
        """Create error response for missing entity field."""
        logger.warning(f"TAG_FILTER missing required 'entity' field for tags: {missing_entity_tags}")
        return {
            "elicitation_needed": True,
            "reason": f"TAG_FILTER is missing required 'entity' field for tags: {', '.join(missing_entity_tags)}",
            "missing_entity_tags": missing_entity_tags,
            "message": (
                f"CRITICAL ERROR: Your TAG_FILTER for tags {missing_entity_tags} is missing the required 'entity' field.\n\n"
                f"EVERY TAG_FILTER MUST include an 'entity' field with one of these values:\n"
                f"- 'NOT_APPLICABLE' (for mobile/browser/OS/user/geo tags)\n"
                f"- 'DESTINATION' (for page/endpoint tags)\n"
                f"- 'SOURCE' (for backend/service tags)\n\n"
                f"Example CORRECT format:\n"
                f'{{"type": "TAG_FILTER", "name": "mobileBeacon.view.name", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Robot Shop"}}\n\n'
                f"NEVER omit the 'entity' field or set it to null. It is REQUIRED for all TAG_FILTER expressions."
            )
        }

    def _create_invalid_tags_error(
        self,
        invalid_tags: List[str],
        beacon_type: str,
        use_case: str
    ) -> Dict[str, Any]:
        """Create error response for invalid tag names."""
        logger.warning(f"Invalid tag names detected: {invalid_tags}")
        return {
            "elicitation_needed": True,
            "reason": f"Invalid tag names detected: {', '.join(invalid_tags)}",
            "invalid_tags": invalid_tags,
            "required_action": {
                "resource_type": "catalog",
                "operation": "get_mobile_app_tag_catalog",
                "params": {"beacon_type": beacon_type, "use_case": use_case}
            },
            "message": f"Please call get_mobile_app_tag_catalog first to get valid tag names for beacon_type='{beacon_type}' and use_case='{use_case}'. Tag names must start with 'mobileBeacon.'"
        }

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
        missing_entity_tags: List[str] = []

        # Extract and validate tags from filter expression
        filter_tags = self._extract_tags_and_check_entity(tag_filter_expression, missing_entity_tags)

        # Extract tag from group (support both camelCase variants)
        group_tag = None
        if group:
            group_tag = group.get("groupbyTag") or group.get("groupByTag")

        # Combine all tags
        all_tags = filter_tags + ([group_tag] if group_tag else [])

        # Check for missing entity field (Priority 1)
        if missing_entity_tags:
            return self._create_missing_entity_error(missing_entity_tags)

        # Validate tag name format (Priority 2)
        invalid_tags = [tag for tag in all_tags if tag and not tag.startswith("mobileBeacon.")]
        if invalid_tags:
            return self._create_invalid_tags_error(invalid_tags, beacon_type, use_case)

        # Check if no tags provided (Priority 3)
        if (tag_filter_expression or group) and not all_tags:
            logger.debug("Tag filter or group provided but no tag names extracted")
            return {
                "elicitation_needed": True,
                "reason": "No valid tag names found in tag_filter_expression or group",
                "required_action": {
                    "resource_type": "catalog",
                    "operation": "get_mobile_app_tag_catalog",
                    "params": {"beacon_type": beacon_type, "use_case": use_case}
                },
                "message": f"Please call get_mobile_app_tag_catalog first to get valid tag names for beacon_type='{beacon_type}' and use_case='{use_case}'"
            }

        return None

    def _validate_metrics(
        self,
        metrics: Optional[List[Dict[str, Any]]],
        user_provided: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Validate metric names to catch invalid metrics before API call.

        Args:
            metrics: List of metric configurations to validate
            user_provided: Whether metrics were provided by user (vs defaulted)

        Returns:
            Elicitation dict if validation fails, None if valid
        """
        if not metrics:
            return None

        # Only validate user-provided metrics (skip defaults)
        if not user_provided:
            return None

        # Extract metric names
        metric_names = [m.get("metric") for m in metrics if isinstance(m, dict) and "metric" in m]

        if not metric_names:
            return {
                "elicitation_needed": True,
                "reason": "Metrics list provided but no valid metric names found",
                "message": "Each metric must have a 'metric' field with the metric name. Example: {'metric': 'beaconCount', 'aggregation': 'SUM'}"
            }

        # Check for common invalid patterns
        invalid_metrics = []
        for metric_name in metric_names:
            # Metrics should not contain spaces or special characters (basic validation)
            if not isinstance(metric_name, str) or not metric_name.strip():
                invalid_metrics.append(metric_name)

        if invalid_metrics:
            return {
                "elicitation_needed": True,
                "reason": f"Invalid metric names detected: {invalid_metrics}",
                "invalid_metrics": invalid_metrics,
                "required_action": {
                    "resource_type": "catalog",
                    "operation": "get_mobile_app_metric_catalog",
                    "params": {}
                },
                "message": "Please call get_mobile_app_metric_catalog first to get the list of valid metric names, then use those exact metric names in your request."
            }

        return None

    def _get_essential_beacon_fields(self) -> List[str]:
        """Get list of essential fields to extract from beacons."""
        return [
            # Identity
            "mobileAppLabel", "mobileAppId", "beaconId", "sessionId", "label",
            # Timing
            "timestamp", "duration", "clockSkew", "ingestionTime",
            # Performance metrics
            "coldStartTimeMs", "warmStartTimeMs", "hotStartTimeMs",
            # View/Screen context
            "view", "type", "currentAppState",
            # HTTP metrics (for httpRequest beacons)
            "httpCallStatus", "httpCallMethod", "httpCallUrl", "httpCallPath", "httpCallOrigin",
            # Platform/Device context
            "platform", "osName", "osVersion", "deviceManufacturer", "deviceModel", "deviceHardware", "appVersion", "appBuild", "bundleIdentifier",
            # User context
            "userName", "userId", "userIp", "userSessionId", "userLanguages",
            "city", "country", "continent", "connectionType", "carrier",
            # Error info
            "errorCount", "errorMessage", "errorId", "errorType",
            # Device state
            "rooted", "viewportWidth", "viewportHeight",
            # Trace correlation
            "backendTraceId", "parentBeaconId",
            # Other
            "batchSize", "bytesIngested", "agentVersion"
        ]

    def _should_skip_field_value(self, field: str, value: Any) -> bool:
        """Determine if a field value should be skipped."""
        # Skip empty/default values
        if value == "" or value == -1 or value is None:
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        if isinstance(value, dict) and len(value) == 0:
            return True

        # Skip 0 for timing fields that indicate "not measured"
        ZERO_MEASURE_FIELDS = {"errorCount", "coldStartTimeMs", "warmStartTimeMs", "hotStartTimeMs"}
        return bool(value == 0 and field in ZERO_MEASURE_FIELDS)

    def _extract_clean_beacon(self, beacon: Dict[str, Any], essential_fields: List[str]) -> Dict[str, Any]:
        """Extract only essential fields from a beacon."""
        clean_beacon = {}
        for field in essential_fields:
            if field in beacon:
                value = beacon[field]
                if not self._should_skip_field_value(field, value):
                    clean_beacon[field] = value
        return clean_beacon

    def _process_beacon_items(
        self, items: List[Any], essential_fields: List[str], filter_fields: bool = True,
        beacons: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Extract clean beacons from a list of raw item dicts, appending to beacons if provided."""
        if beacons is None:
            beacons = []
        for item in items:
            if not isinstance(item, dict) or "beacon" not in item:
                continue
            beacon = item["beacon"]
            if not isinstance(beacon, dict):
                continue
            if filter_fields:
                beacons.append(self._extract_clean_beacon(beacon, essential_fields))
            else:
                beacons.append(beacon)
        return beacons

    def _summarize_beacons_response(self, response_data: Dict[str, Any], filter_fields: bool = True) -> Dict[str, Any]:
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
                    "mobileLabel": "...",
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

        essential_fields = self._get_essential_beacon_fields()

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
        items = response_data.get("items")
        if isinstance(items, list):
            result["beacons"] = self._process_beacon_items(items, essential_fields, filter_fields, result["beacons"])

        return result


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
                    {"metric": "uniqueUsers", "aggregation": "DISTINCT_COUNT"}
                ]
            })

        if not group:
            missing_params.append({
                "name": "group",
                "description": "Grouping configuration (REQUIRED)",
                "examples": [
                    {"groupbyTag": "mobileBeacon.mobileApp.name"},
                    {"groupbyTag": "mobileBeacon.view.name"}
                ]
            })

        if not beacon_type:
            missing_params.append({
                "name": "beacon_type",
                "description": "Type of beacon to analyze (REQUIRED)",
                "examples": ["SESSION_START", "VIEW_CHANGE", "HTTP_REQUEST", "CUSTOM", "CRASH", "DROP_BEACON", "PERF"]
            })

        if missing_params:
            return {
                "elicitation_required": True,
                "missing_parameters": missing_params,
                "message": "Please provide the required parameters to get mobile app beacon groups",
                "elicitation_prompt": "To retrieve mobile app beacon groups, I need:\n" +
                 "\n".join([f"- {p['name']}: {p['description']}" for p in missing_params])
            }

        return None
