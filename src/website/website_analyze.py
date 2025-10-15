"""
Website Analyze MCP Tools Module

This module provides website analyze-specific MCP tools for Instana monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


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


class WebsiteAnalyzeMCPTools(BaseInstanaClient):
    """Tools for website analyze in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Website Analyze MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Website Beacon Groups",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteAnalyzeApi)
    async def get_website_beacon_groups(self,
                                       payload: Optional[Union[Dict[str, Any], str]] = None,
                                       fill_time_series: Optional[bool] = True,
                                       ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get grouped website beacon metrics.

        This API endpoint retrieves grouped website monitoring beacon metrics, allowing you to analyze
        performance across different dimensions like page URLs, browsers, or geographic locations.

        Args:
            payload: Complete request payload as a dictionary or JSON string
            {
                "metrics": [
                    {
                    "metric": "beaconCount",
                    "aggregation": "SUM",
                    "granularity": 60
                    }
                ],
                "group": {
                    "groupByTag": "beacon.page.name"
                },
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
                        "value": "/checkout"
                    }
                    ]
                },
                "timeFrame": {
                    "to": null,
                    "windowSize": 3600000
                },
                "type": "PAGELOAD"
            }
            fill_time_series: Whether to fill missing data points with timestamp and value 0
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing grouped website metrics data or error information
        """
        try:
            logger.debug("get_website_beacon_groups called")

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

            # Handle nested payload structure - if the payload contains a 'payload' key, extract it
            if isinstance(request_body, dict) and "payload" in request_body and len(request_body) == 1:
                logger.debug("Found nested payload structure, extracting inner payload")
                request_body = request_body["payload"]

            logger.debug(f"Final request_body structure: {request_body}")
            logger.debug(f"Request body keys: {list(request_body.keys()) if isinstance(request_body, dict) else 'Not a dict'}")

            try:
                from instana_client.models.get_website_beacon_groups import (
                    GetWebsiteBeaconGroups,
                )
                logger.debug("Successfully imported GetWebsiteBeaconGroups")
            except ImportError as e:
                logger.debug(f"Error importing GetWebsiteBeaconGroups: {e}")
                return {"error": f"Failed to import GetWebsiteBeaconGroups: {e!s}"}

            # Create an GetWebsiteBeaconGroups object from the request body
            try:
                query_params = {}

                # Extract required fields from request_body
                if request_body and "type" in request_body:
                    query_params["type"] = request_body["type"]

                # Handle required 'group' field
                if request_body and "group" in request_body:
                    group_data = request_body["group"]
                    # Map the group field names to match Pydantic model expectations
                    mapped_group = {}
                    if "groupByTag" in group_data:
                        mapped_group["groupbyTag"] = group_data["groupByTag"]
                    if "groupByTagEntity" in group_data:
                        mapped_group["groupbyTagEntity"] = group_data["groupByTagEntity"]
                    # Also handle the correct case if already present
                    if "groupbyTag" in group_data:
                        mapped_group["groupbyTag"] = group_data["groupbyTag"]
                    if "groupbyTagEntity" in group_data:
                        mapped_group["groupbyTagEntity"] = group_data["groupbyTagEntity"]

                    # Ensure both required fields are present - provide default for groupbyTagEntity if missing
                    if "groupbyTag" not in mapped_group:
                        return {"error": "Required field 'groupByTag' is missing from group payload"}
                    if "groupbyTagEntity" not in mapped_group:
                        # Provide default value for groupbyTagEntity when not specified
                        mapped_group["groupbyTagEntity"] = "NOT_APPLICABLE"

                    query_params["group"] = mapped_group
                else:
                    return {"error": "Required field 'group' is missing from payload"}

                # Handle required 'metrics' field
                if request_body and "metrics" in request_body:
                    query_params["metrics"] = request_body["metrics"]
                else:
                    return {"error": "Required field 'metrics' is missing from payload"}

                # Handle optional fields
                if request_body and "timeFrame" in request_body:
                    query_params["timeFrame"] = request_body["timeFrame"]
                if request_body and "tagFilterExpression" in request_body:
                    query_params["tagFilterExpression"] = request_body["tagFilterExpression"]
                if request_body and "tagFilters" in request_body:
                    query_params["tagFilters"] = request_body["tagFilters"]
                if request_body and "order" in request_body:
                    query_params["order"] = request_body["order"]
                if request_body and "pagination" in request_body:
                    query_params["pagination"] = request_body["pagination"]

                logger.debug(f"Creating GetWebsiteBeaconGroups with params: {query_params}")
                config_object = GetWebsiteBeaconGroups(**query_params)
                logger.debug("Successfully created GetWebsiteBeaconGroups object")
            except Exception as e:
                logger.debug(f"Error creating GetWebsiteBeaconGroups: {e}")
                return {"error": f"Failed to get website beacon groups: {e!s}"}

            # Call the get_beacon_groups method from the SDK using without_preload_content to avoid NaN validation errors
            logger.debug("Calling get_beacon_groups with config object")
            try:
                # Use without_preload_content to bypass Pydantic validation and handle NaN values manually
                response = api_client.get_beacon_groups_without_preload_content(
                    get_website_beacon_groups=config_object,
                    fill_time_series=fill_time_series
                )

                # Check if the response was successful
                if response.status != 200:
                    error_message = f"Failed to get website beacon groups: HTTP {response.status}"
                    logger.debug(error_message)
                    return {"error": error_message}

                # Read the response content
                response_text = response.data.decode('utf-8')

                # Parse the response as JSON
                import json
                result_dict = json.loads(response_text)

                logger.debug("Successfully parsed raw response")

                logger.debug(f"Result from get_website_beacon_groups: {result_dict}")
                return result_dict
            except Exception as api_error:
                # Handle validation errors from the SDK, particularly for customMetric 'NaN' values
                error_msg = str(api_error)
                if "customMetric" in error_msg and "NaN" in error_msg:
                    logger.warning(f"API returned 'NaN' values for customMetric field: {error_msg}")
                    return {
                        "error": "API returned invalid data (NaN values for customMetric field). This is a known issue with the Instana API response format.",
                        "details": error_msg,
                        "suggestion": "Try using a different time range or filtering criteria to avoid beacons with NaN customMetric values."
                    }
                else:
                    # Re-raise other errors
                    raise api_error
        except Exception as e:
            logger.error(f"Error in get_website_beacon_groups: {e}")
            return {"error": f"Failed to get website beacon groups: {e!s}"}


    @register_as_tool(
        title="Get Website Beacons",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteAnalyzeApi)
    async def get_website_beacons(self,
                                 payload: Optional[Union[Dict[str, Any], str]] = None,
                                 ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get all website beacon metrics.

        This API endpoint retrieves all website monitoring beacon metrics with matching type.

        Args:
            payload: Complete request payload as a dictionary or JSON string
            {
                "tagFilterExpression": {
                    "type": "TAG_FILTER",
                    "name": "beacon.website.name",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "Ecommerce_Bob_Squad"
                },
                "timeFrame": {
                    "to": 1757333439394,
                    "windowSize": 3600000
                },
                "type": "ERROR"
            }
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing all website beacon data with matching type or error information
        """
        try:
            logger.debug("get_website_beacons called")

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

            # Handle nested payload structure - if the payload contains a 'payload' key, extract it
            if isinstance(request_body, dict) and "payload" in request_body and len(request_body) == 1:
                logger.debug("Found nested payload structure, extracting inner payload")
                request_body = request_body["payload"]

            logger.debug(f"Final request_body structure: {request_body}")
            logger.debug(f"Request body keys: {list(request_body.keys()) if isinstance(request_body, dict) else 'Not a dict'}")

            try:
                from instana_client.models.get_website_beacons import (
                    GetWebsiteBeacons,
                )
                logger.debug("Successfully imported GetWebsiteBeacons")
            except ImportError as e:
                logger.debug(f"Error importing GetWebsiteBeacons: {e}")
                return {"error": f"Failed to import GetWebsiteBeacons: {e!s}"}

            # Create an GetWebsiteBeacons object from the request body
            try:
                query_params = {}

                # Handle required 'type' field
                if request_body and "type" in request_body:
                    query_params["type"] = request_body["type"]
                else:
                    return {"error": "Required field 'type' is missing from payload"}

                # Handle optional fields
                if request_body and "timeFrame" in request_body:
                    time_frame = {}
                    if "to" in request_body["timeFrame"]:
                        time_frame["to"] = request_body["timeFrame"]["to"]
                    if "windowSize" in request_body["timeFrame"]:
                        time_frame["windowSize"] = request_body["timeFrame"]["windowSize"]
                    query_params["timeFrame"] = time_frame

                if request_body and "tagFilters" in request_body:
                    query_params["tagFilters"] = request_body["tagFilters"]

                if request_body and "pagination" in request_body:
                    query_params["pagination"] = request_body["pagination"]

                logger.debug(f"Creating GetWebsiteBeacons with params: {query_params}")
                config_object = GetWebsiteBeacons(**query_params)
                logger.debug("Successfully created GetWebsiteBeacons object")
            except Exception as e:
                logger.debug(f"Error creating GetWebsiteBeacons: {e}")
                return {"error": f"Failed to get website beacons: {e!s}"}

            # Call the get_beacons method from the SDK using without_preload_content to avoid NaN validation errors
            logger.debug("Calling get_beacons with config object")
            try:
                # Use without_preload_content to bypass Pydantic validation and handle NaN values manually
                result = api_client.get_beacons_without_preload_content(
                    get_website_beacons=config_object
                )

                # Read the response content
                response_text = result.data.decode('utf-8')

                # Parse the response as JSON
                import json
                result_dict = json.loads(response_text)

                logger.debug("Successfully parsed raw response")

                # Clean any NaN values from the response
                result_dict = clean_nan_values(result_dict)

                # Handle nested JSON response format
                if isinstance(result_dict, dict) and "data" in result_dict and isinstance(result_dict["data"], list):
                    # Check if data contains JSON strings that need to be parsed
                    if len(result_dict["data"]) > 0 and isinstance(result_dict["data"][0], str):
                        try:
                            # Parse the JSON string from the data array
                            parsed_data = json.loads(result_dict["data"][0])
                            result_dict = parsed_data
                            logger.debug("Successfully parsed nested JSON response")
                        except (json.JSONDecodeError, IndexError) as e:
                            logger.debug(f"Failed to parse nested JSON: {e}")
                            # Fall back to original structure
                            pass

                # Ensure we always return a dictionary, not a list
                if isinstance(result_dict, list):
                    result_dict = {"beacons": result_dict, "count": len(result_dict)}
                elif not isinstance(result_dict, dict):
                    result_dict = {"data": result_dict}
                logger.debug(f"Result from get_website_beacons: {result_dict}")
                return result_dict
            except Exception as api_error:
                # Handle validation errors from the SDK, particularly for customMetric 'NaN' values
                error_msg = str(api_error)
                logger.debug(f"API error details: {error_msg}")
                return {"error": error_msg}
        except Exception as e:
            logger.error(f"Error in get_website_beacons: {e}")
            return {"error": f"Failed to get website beacons: {e!s}"}
