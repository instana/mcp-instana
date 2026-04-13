"""
Website Analyze MCP Tools Module

This module provides website analyze-specific MCP tools for Instana monitoring.
"""

import json
import logging
from datetime import datetime
from email.message import Message
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context

# Constants
DEFAULT_CHARSET = 'utf-8'
DEFAULT_GROUP_BY_TAG = 'beacon.location.path'  # Default grouping by URL path
DEFAULT_GROUP_BY_TAG_ENTITY = 'NOT_APPLICABLE'


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

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)


def _decode_response(response) -> str:
    """
    Safely decode response data using the response's charset or UTF-8 as fallback.

    Args:
        response: The HTTP response object

    Returns:
        Decoded response text
    """
    # Try to get charset from response headers using standard library parsing
    charset = DEFAULT_CHARSET  # Default fallback

    # Check if response has charset information
    if hasattr(response, 'headers') and response.headers:
        content_type = response.headers.get('Content-Type', '')
        if content_type:
            # Use email.message.Message for proper RFC-compliant Content-Type parsing
            # This handles quoted values, whitespace, case-insensitivity, etc.
            msg = Message()
            msg['content-type'] = content_type
            parsed_charset = msg.get_content_charset()
            if parsed_charset:
                charset = parsed_charset

    try:
        return response.data.decode(charset)
    except (UnicodeDecodeError, LookupError):
        # Fallback to DEFAULT_CHARSET if specified charset fails
        return response.data.decode(DEFAULT_CHARSET, errors='replace')


class WebsiteAnalyzeMCPTools(BaseInstanaClient):
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
    ctx: Optional[Context] = None,
    api_client: Any = None) -> Dict[str, Any]:
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

            # Set default beacon_type if not provided (must be done before elicitation/validation)
            if not beacon_type:
                beacon_type = "PAGELOAD"
                logger.debug("[get_website_beacon_groups] Applied default beacon_type: PAGELOAD")

            # Two-Pass Elicitation: Check for required and recommended parameters
            elicitation_request = self._check_elicitation_for_beacon_groups(
                metrics, group, beacon_type
            )
            if elicitation_request:
                logger.debug("[get_website_beacon_groups] Elicitation needed for beacon groups")
                return elicitation_request

            # Validate tag names in tag_filter_expression and group
            tag_validation = self._validate_tag_names(
                tag_filter_expression,
                group,
                beacon_type,
                use_case="GROUPING")

            if tag_validation:
                logger.debug("[get_website_beacon_groups] Tag validation failed - elicitation needed")
                return tag_validation

            # Set default time range if not provided
            if not time_frame:
                time_frame = {
                    "windowSize": 3600000  # Default to 1 hour
                }
                logger.debug("[get_website_beacon_groups] Applied default time_frame: 1 hour (3600000ms)")

            # Set default metrics if not provided
            if not metrics:
                metrics = [
                    {
                        "metric": "beaconCount",
                        "aggregation": "SUM"
                    }
                ]
                logger.debug("[get_website_beacon_groups] Applied default metrics: beaconCount SUM")

            # Set default group if not provided
            if not group:
                group = {
                    "groupByTag": "beacon.page.name"
                }
                logger.debug("[get_website_beacon_groups] Applied default group: beacon.page.name")

            #If no tag_filter_expression provided, use empty EXPRESSION
            # The API expects this field even when empty
            if not tag_filter_expression:
                tag_filter_expression = {
                    "type": "EXPRESSION",
                    "logicalOperator": "AND",
                    "elements": []
                }
                logger.debug("[get_website_beacon_groups] Applied default tag filter expression: empty EXPRESSION with AND operator")

            # Build the query parameters for the SDK model
            query_params = {}

            # Handle required 'type' field (beacon_type is now guaranteed to have a value)
            query_params["type"] = beacon_type

            # Handle required 'group' field with field name mapping
            if group:
                mapped_group = {}

                # Handle groupByTag/groupbyTag (support both camelCase and lowercase)
                if "groupByTag" in group:
                    mapped_group["groupbyTag"] = group["groupByTag"]
                elif "groupbyTag" in group:
                    mapped_group["groupbyTag"] = group["groupbyTag"]

                # Handle groupByTagEntity/groupbyTagEntity (support both camelCase and lowercase)
                if "groupByTagEntity" in group:
                    mapped_group["groupbyTagEntity"] = group["groupByTagEntity"]
                elif "groupbyTagEntity" in group:
                    mapped_group["groupbyTagEntity"] = group["groupbyTagEntity"]

                # Provide defaults for missing fields
                if "groupbyTag" not in mapped_group:
                    # Default to grouping by page name
                    logger.debug(f"[get_website_beacon_groups] No groupByTag specified, using default: {DEFAULT_GROUP_BY_TAG}")
                    mapped_group["groupbyTag"] = DEFAULT_GROUP_BY_TAG
                if "groupbyTagEntity" not in mapped_group:
                    # Provide default value for groupbyTagEntity when not specified
                    logger.debug(f"[get_website_beacon_groups] No groupByTagEntity specified, using default: {DEFAULT_GROUP_BY_TAG_ENTITY}")
                    mapped_group["groupbyTagEntity"] = DEFAULT_GROUP_BY_TAG_ENTITY

                query_params["group"] = mapped_group

            # Handle required 'metrics' field
            if metrics:
                query_params["metrics"] = metrics


            # Handle optional fields
            if time_frame:
                query_params["timeFrame"] = time_frame
            if tag_filter_expression:
                # Convert tag filter expression dict to SDK model
                try:
                    from instana_client.models.tag_filter_expression_element import (
                        TagFilterExpressionElement,
                    )
                    tag_filter_obj = TagFilterExpressionElement.from_dict(tag_filter_expression)
                    query_params["tagFilterExpression"] = tag_filter_obj
                    logger.debug(f"[get_website_beacon_groups] Converted tag filter to SDK object: {tag_filter_obj.to_dict()}")
                except Exception as e:
                    logger.error(f"[get_website_beacon_groups] Error converting tag filter expression: {e}")
                    return {"error": f"Invalid tag filter expression: {e!s}"}
            if order:
                query_params["order"] = order
            if pagination:
                query_params["pagination"] = pagination

            try:
                from instana_client.models.get_website_beacon_groups import (
                    GetWebsiteBeaconGroups,
                )
                logger.debug(f"[get_website_beacon_groups] Creating GetWebsiteBeaconGroups with params: {query_params}")
                config_object = GetWebsiteBeaconGroups(**query_params)
                logger.debug(f"[get_website_beacon_groups] Successfully created GetWebsiteBeaconGroups, Config object dict: {config_object.to_dict()}")
            except Exception as e:
                logger.error(f"[get_website_beacon_groups] Error creating GetWebsiteBeaconGroups object: {e!s}")
                return {
                    "error": f"Failed to create beacon groups request: {e!s}"
                }

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
                        error_body = _decode_response(response)
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
                response_text = _decode_response(response)

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
        ctx: Optional[Context] = None,
        api_client: Any = None
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

            # Elicitation: Check for required parameters
            if not beacon_type:
                return {
                    "elicitation_needed": True,
                    "missing_parameters": [{
                        "name": "beacon_type",
                        "description": "Type of beacon to retrieve (REQUIRED)",
                        "examples": ["PAGELOAD", "ERROR", "RESOURCELOAD", "HTTPREQUEST"]
                    }],
                    "message": "Please provide the beacon type you want to retrieve."
                }

            # Validate tag names in tag_filter_expression
            tag_validation = self._validate_tag_names(
                tag_filter_expression,
                None,  # get_website_beacons doesn't use group parameter
                beacon_type,
                use_case="FILTERING")

            if tag_validation:
                logger.debug("[get_website_beacons] Tag validation failed - elicitation needed")
                return tag_validation

            # Set default time frame if not provided
            if not time_frame:
                time_frame = {"windowSize": 3600000}
                logger.debug("[get_website_beacons] Applied default time_frame: 1 hour (3600000ms)")

            # Set default pagination if not provided (20 items per page, matching UI)
            if not pagination:
                pagination = {"retrievalSize": 20, "offset": 0}
                logger.debug("[get_website_beacons] Applied default pagination: 20 items per page, offset 0")
            else:
                # Ensure retrievalSize is within valid range (1-200)
                if "retrievalSize" in pagination:
                    retrieval_size = pagination["retrievalSize"]
                    if retrieval_size < 1:
                        pagination["retrievalSize"] = 1
                        logger.warning(f"[get_website_beacons] retrievalSize {retrieval_size} is below minimum (1), setting to 1")
                    elif retrieval_size > 200:
                        pagination["retrievalSize"] = 200
                        logger.warning(f"[get_website_beacons] retrievalSize {retrieval_size} exceeds maximum (200), setting to 200")
                else:
                    pagination["retrievalSize"] = 20

                # Set default offset if not provided
                if "offset" not in pagination:
                    pagination["offset"] = 0

            # Build query parameters
            query_params = {}

            # Required field
            if beacon_type:
                query_params["type"] = beacon_type

            # Optional fields
            if time_frame:
                query_params["timeFrame"] = time_frame

            # Convert tag_filter_expression to tag_filters (LIST of DeprecatedTagFilter)
            if tag_filter_expression:
                try:
                    from instana_client.models.deprecated_tag_filter import (
                        DeprecatedTagFilter,
                    )

                    # If it's a single TAG_FILTER, convert to DeprecatedTagFilter
                    if tag_filter_expression.get("type") == "TAG_FILTER":
                        # Validate required fields
                        name = tag_filter_expression.get("name")
                        operator = tag_filter_expression.get("operator")
                        value = tag_filter_expression.get("value")

                        if not name or not operator or not value:
                            return {"error": "TAG_FILTER requires 'name', 'operator', and 'value' fields"}

                        # Extract fields (remove 'type' field as DeprecatedTagFilter doesn't have it)
                        tag_filter_dict = {
                            "name": name,
                            "operator": operator,
                            "value": value,
                        }
                        if "entity" in tag_filter_expression:
                            tag_filter_dict["entity"] = tag_filter_expression.get("entity")

                        tag_filter_obj = DeprecatedTagFilter(**tag_filter_dict)
                        query_params["tagFilters"] = [tag_filter_obj]
                        logger.debug(f"[get_website_beacons] Converted single TAG_FILTER to DeprecatedTagFilter: {tag_filter_obj.to_dict()}")

                    # If it's an EXPRESSION with elements, convert each element
                    elif tag_filter_expression.get("type") == "EXPRESSION":
                        elements = tag_filter_expression.get("elements", [])
                        if elements:
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

                            if tag_filters:
                                query_params["tagFilters"] = tag_filters
                                logger.debug(f"[get_website_beacons] Converted {len(tag_filters)} TAG_FILTERs from EXPRESSION")
                        else:
                            # Empty EXPRESSION - no filters
                            logger.debug("[get_website_beacons] Empty EXPRESSION - no tag filters applied")

                except Exception as e:
                    logger.error(f"[get_website_beacons] Error converting tag filter expression: {e}")
                    return {"error": f"Invalid tag filter expression: {e!s}"}

            # Add pagination (always present with defaults)
            if pagination:
                from instana_client.models.cursor_pagination import CursorPagination
                try:
                    pagination_obj = CursorPagination(**pagination)
                    query_params["pagination"] = pagination_obj
                    logger.debug(f"[get_website_beacons] Applied pagination: {pagination_obj.to_dict()}")
                except Exception as e:
                    logger.error(f"[get_website_beacons] Error creating CursorPagination object: {e}")
                    return {"error": f"Invalid pagination configuration: {e!s}"}

            logger.debug(f"[get_website_beacons] Creating GetWebsiteBeacons with params: {query_params}")

            try:
                from instana_client.models.get_website_beacons import GetWebsiteBeacons
                config_object = GetWebsiteBeacons(**query_params)
                logger.debug(f"[get_website_beacons] Successfully created GetWebsiteBeacons object: {config_object.to_dict()}")
            except Exception as e:
                logger.error(f"[get_website_beacons] Error creating GetWebsiteBeacons object: {e!s}")
                return {"error": f"Failed to create GetWebsiteBeacons object: {e!s}"}

            # Make API call
            logger.debug("[get_website_beacons] Making API call to get website beacons")
            result = api_client.get_beacons_without_preload_content(get_website_beacons=config_object)

            # Process results
            response_text = _decode_response(result)
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
                    {"metric": "pageLoadTime", "aggregation": "MEAN"}
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
        Validate that tag names follow the beacon.* pattern.
        Returns elicitation if tags are invalid or missing.

        Args:
            tag_filter_expression: Tag filter expression to validate
            group: Group configuration to validate
            beacon_type: Beacon type for catalog call
            use_case: Use case for catalog call (GROUPING or FILTERING)

        Returns:
            Elicitation dict if validation fails, None if valid
        """
        invalid_tags = []

        # Helper function to extract tag names from filter expression
        def extract_tag_names(expr):
            tags = []
            if not expr:
                return tags

            if isinstance(expr, dict):
                # Single TAG_FILTER
                if expr.get("type") == "TAG_FILTER":
                    tag_name = expr.get("name")
                    if tag_name:
                        tags.append(tag_name)

                # EXPRESSION with elements
                elif expr.get("type") == "EXPRESSION":
                    elements = expr.get("elements", [])
                    for element in elements:
                        tags.extend(extract_tag_names(element))

            return tags

        # Extract tag names from tag_filter_expression
        filter_tags = extract_tag_names(tag_filter_expression)

        # Extract tag name from group
        group_tag = None
        if group:
            # Handle both groupByTag and groupbyTag
            group_tag = group.get("groupByTag") or group.get("groupbyTag")

        # Combine all tags
        all_tags = filter_tags + ([group_tag] if group_tag else [])

        # Validate each tag
        for tag in all_tags:
            if tag:
                # Check if tag follows beacon.* pattern
                if not tag.startswith("beacon."):
                    invalid_tags.append(tag)

        # If invalid tags found, return elicitation
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

        # If no tags provided at all (and group/filter are being used), suggest catalog
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
