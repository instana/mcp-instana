"""
Website Metrics MCP Tools Module

This module provides website metrics-specific MCP tools for Instana monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Import the necessary classes from the SDK
try:
    from instana_client.api.website_metrics_api import WebsiteMetricsApi
    from instana_client.models.get_website_metrics_v2 import GetWebsiteMetricsV2
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class WebsiteMetricsMCPTools(BaseInstanaClient):
    """Tools for website metrics in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Website Metrics MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Website Page Load",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteMetricsApi)
    async def get_website_page_load(self,
                                   page_id: str,
                                   timestamp: int,
                                   ctx=None, api_client=None) -> List[Dict[str, Any]]:
        """
        Get website monitoring beacons for a specific page load.

        This API endpoint retrieves detailed beacon information for a specific page load event.

        Args:
            page_id: Identifier of the page load to be retrieved
            timestamp: Timestamp of the page load to be retrieved
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing page load beacon data or error information
        """
        try:
            if not page_id:
                return [{"error": "page_id parameter is required"}]
            if not timestamp:
                return [{"error": "timestamp parameter is required"}]

            logger.debug(f"get_website_page_load called with page_id={page_id}, timestamp={timestamp}")

            # Call the get_page_load method from the SDK
            result = api_client.get_page_load(
                id=page_id,
                timestamp=timestamp
            )
                        # Convert the result to a list of dictionaries
            if isinstance(result, list):
                # If it's a list, convert each item to dict if possible
                result_list = []
                for item in result:
                    if hasattr(item, 'to_dict'):
                        result_list.append(item.to_dict())
                    else:
                        result_list.append(item)
            elif hasattr(result, 'to_dict'):
                result_list = [result.to_dict()]
            else:
                # If it's already a list or another format, use it as is
                result_list = result

            logger.debug(f"Result from get_website_page_load: {result_list}")
            return result_list

        except Exception as e:
            logger.error(f"Error in get_website_page_load: {e}", exc_info=True)
            return [{"error": f"Failed to get website page load: {e!s}"}]

    @register_as_tool(
        title="Get Website Beacon Metrics V2",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteMetricsApi)
    async def get_website_beacon_metrics_v2(self,
                                           payload: Optional[Union[Dict[str, Any], str]] = None,
                                           ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get website beacon metrics using the v2 API.

        This API endpoint retrieves one or more supported aggregations of metrics for website monitoring beacons.
        For example, retrieve MEAN aggregation of page load time metric for specific pages or websites.

        Args:
            payload: Complete request payload as a dictionary or JSON string
                {
                    "metrics": [
                        {
                        "metric": "beaconCount",
                        "aggregation": "SUM"
                        }
                    ],
                    "tagFilterExpression": {
                        "type": "EXPRESSION",
                        "logicalOperator": "AND",
                        "elements": [
                        {
                            "type": "TAG_FILTER",
                            "name": "beacon.website.name",
                            "operator": "EQUALS",
                            "entity": "NOT_APPLICABLE",
                            "value": "robot-shop"
                        },
                        {
                            "type": "TAG_FILTER",
                            "name": "beacon.location.path",
                            "operator": "EQUALS",
                            "entity": "NOT_APPLICABLE",
                            "value": "/"
                        }
                        ]
                    },
                    "timeFrame": {
                        "to": null,
                        "windowSize": 3600000
                    },
                    "type": "PAGELOAD"
                    }
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing website metrics data or error information
        """
        try:
            logger.debug("get_website_beacon_metrics_v2 called")

            # Parse the payload
            if isinstance(payload, str):
                logger.debug("Payload is a string, attempting to parse")
                try:
                    import json
                    try:
                        parsed_payload = json.loads(payload)
                        logger.debug("Successfully parsed payload as JSON")
                        request_body = parsed_payload
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON parsing failed: {e}, trying with quotes replaced")

                        # Try replacing single quotes with double quotes
                        fixed_payload = payload.replace("'", "\"")
                        try:
                            parsed_payload = json.loads(fixed_payload)
                            logger.debug("Successfully parsed fixed JSON")
                            request_body = parsed_payload
                        except json.JSONDecodeError:
                            # Try as Python literal
                            import ast
                            try:
                                parsed_payload = ast.literal_eval(payload)
                                logger.debug("Successfully parsed payload as Python literal")
                                request_body = parsed_payload
                            except (SyntaxError, ValueError) as e2:
                                logger.debug(f"Failed to parse payload string: {e2}")
                                return {"error": f"Invalid payload format: {e2}", "payload": payload}
                except Exception as e:
                    logger.debug(f"Error parsing payload string: {e}")
                    return {"error": f"Failed to parse payload: {e}", "payload": payload}
            else:
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            try:
                from instana_client.models.get_website_metrics_v2 import (
                    GetWebsiteMetricsV2,
                )
                logger.debug("Successfully imported GetWebsiteMetricsV2")
            except ImportError as e:
                logger.debug(f"Error importing GetWebsiteMetricsV2: {e}")
                return {"error": f"Failed to import GetWebsiteMetricsV2: {e!s}"}

            # Create an GetWebsiteMetricsV2 object from the request body
            try:
                query_params = {}

                # Extract required fields from request body
                if request_body:
                    # Required field: metrics
                    if "metrics" in request_body:
                        query_params["metrics"] = request_body["metrics"]
                    else:
                        return {"error": "Required field 'metrics' is missing from payload"}

                    # Required field: type
                    if "type" in request_body:
                        query_params["type"] = request_body["type"]
                    else:
                        return {"error": "Required field 'type' is missing from payload"}

                    # Optional fields
                    if "tagFilterExpression" in request_body:
                        query_params["tag_filter_expression"] = request_body["tagFilterExpression"]
                    elif "tag_filter_expression" in request_body:
                        query_params["tag_filter_expression"] = request_body["tag_filter_expression"]

                    if "timeFrame" in request_body:
                        query_params["time_frame"] = request_body["timeFrame"]
                    elif "time_frame" in request_body:
                        query_params["time_frame"] = request_body["time_frame"]

                logger.debug(f"Creating get_website_beacon_metrics_v2 with params: {query_params}")
                config_object = GetWebsiteMetricsV2(**query_params)
                logger.debug("Successfully created GetWebsiteMetricsV2 object")
            except Exception as e:
                logger.debug(f"Error creating get_website_beacon_metrics_v2: {e}")
                return {"error": f"Failed to get website beacon metrics: {e!s}"}

            # Call the get_beacon_metrics_v2 method from the SDK
            logger.debug("Calling get_beacon_metrics_v2 with config object")
            result = api_client.get_beacon_metrics_v2(
                get_website_metrics_v2=config_object
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Get website beacon metrics"
                }

            logger.debug(f"Result from get_website_beacon_metrics_v2: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_website_beacon_metrics_v2: {e}")
            return {"error": f"Failed to get website beacon metrics: {e!s}"}
