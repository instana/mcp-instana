"""
Website Catalog MCP Tools Module

This module provides website catalog-specific MCP tools for Instana monitoring.
"""

import logging
from typing import Any, Dict, List, Optional

# Import the necessary classes from the SDK
try:
    from instana_client.api.website_catalog_api import WebsiteCatalogApi
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from mcp.types import ToolAnnotations

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    decode_response,
    process_tag_catalog_response,
    project_metric_card,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


class WebsiteCatalogMCPTools(BaseInstanaClient):
    """Tools for website catalog in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Website Catalog MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)


    @with_header_auth(WebsiteCatalogApi)
    async def get_website_catalog_metrics(
        self,
        ctx=None,
        api_client=None,
        view: str = "planner",
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get website monitoring metrics catalog.

        Returns metric definitions including metricId, label, description, formatter,
        aggregations, and beaconTypes to help agents construct valid queries.

        Args:
            ctx: The MCP context (optional)
            view: "planner" (default) returns compact cards for query planning.
                  "full" returns the raw SDK response including internal fields.

        Returns:
            Dictionary containing list of metrics, count, and description.
        """
        try:
            logger.debug(f"[get_website_catalog_metrics] Called with view={view}")

            if view not in ("planner", "full"):
                return {
                    "error": f"Invalid view '{view}'. Valid views: 'planner', 'full'",
                    "valid_views": ["planner", "full"],
                }

            # Use without_preload_content to bypass Pydantic validation
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_website_catalog_metrics_without_preload_content),
                ctx=ctx,
                operation_name="get_website_catalog_metrics",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Check if the response was successful
            if response.status != 200:
                error_message = f"Failed to get website catalog metrics: HTTP {response.status}"
                logger.error(f"[get_website_catalog_metrics] {error_message}")

                # Try to get error details from response
                try:
                    error_body = decode_response(response)
                    logger.error(f"[get_website_catalog_metrics] API Error Response: {error_body}")
                    return {
                        "error": error_message,
                        "details": error_body,
                        "status_code": response.status
                    }
                except Exception:
                    return {"error": error_message, "status_code": response.status}

            # Read and parse the response content
            response_text = decode_response(response)
            import json
            full_metrics = json.loads(response_text)

            # Extract only metric IDs - this is schema information for LLM
            metric_ids = [metric.get("metricId") for metric in full_metrics if metric.get("metricId")]

            if view == "full":
                result_dict = {
                    "metrics": full_metrics,
                    "count": len(metric_ids),
                    "description": "Website monitoring metrics catalog with full metadata"
                }
            else:
                compact_metrics = [project_metric_card(metric) for metric in full_metrics]
                result_dict = {
                    "metrics": compact_metrics,
                    "count": len(metric_ids),
                    "description": "Website monitoring metrics catalog with necessary metadata for query planning"
                }

            logger.debug(f"[get_website_catalog_metrics] Returning {len(metric_ids)} metric IDs from catalog")
            return result_dict
        except Exception as e:
            logger.error(f"[get_website_catalog_metrics] Error: {e}", exc_info=True)
            return {"error": f"Failed to get website catalog metrics: {e!s}"}

    @with_header_auth(WebsiteCatalogApi)
    async def get_website_catalog_tags(self, ctx=None, api_client=None,
                                        resource_type: Optional[str] = None,
                                        tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get website monitoring tags catalog.

        This API endpoint retrieves all available tags for website monitoring.
        Use this to discover what tags are available for filtering website beacons.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing available website tags or error information
        """
        try:
            logger.debug("[get_website_catalog_tags] Called")

            # Call the get_website_catalog_tags method from the SDK
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_website_catalog_tags),
                ctx=ctx,
                operation_name="get_website_catalog_tags",
                resource_type=resource_type, tool_name=tool_name,
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

            # Ensure we always return a dictionary, not a list
            if isinstance(result_list, list):
                result_dict = {"tags": result_list, "count": len(result_list)}
            else:
                result_dict = {"data": result_list}

            logger.debug(f"[get_website_catalog_tags] Result: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"[get_website_catalog_tags] Error: {e}", exc_info=True)
            return {"error": f"Failed to get website catalog tags: {e!s}"}

    @with_header_auth(WebsiteCatalogApi)
    async def get_website_tag_catalog(self,
                                    beacon_type: str,
                                    use_case: str,
                                    ctx=None, api_client=None,
    resource_type: Optional[str] = None,
    tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get website monitoring tag catalog.

        This API endpoint retrieves all available tag names for website monitoring.
        Returns a simple list of valid tag names that can be used in queries.
        This serves as schema information for LLM to know what tags are available.

        Args:
            beacon_type: The beacon type (e.g., 'PAGELOAD', 'ERROR')
            use_case: The use case (e.g., 'GROUPING', 'FILTERING')
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing list of valid tag names for the specified beacon type and use case
        """
        try:
            logger.debug(f"[get_website_tag_catalog] Called with beacon_type={beacon_type}, use_case={use_case}")
            if not beacon_type:
                return {"error": "beacon_type parameter is required"}
            if not use_case:
                return {"error": "use_case parameter is required"}

            # Use without_preload_content to bypass Pydantic validation
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_website_tag_catalog_without_preload_content,
                    beacon_type=beacon_type,
                    use_case=use_case),
                ctx=ctx,
                operation_name="get_website_tag_catalog",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Check if the response was successful
            if response.status != 200:
                error_message = f"Failed to get website tag catalog: HTTP {response.status}"
                logger.error(f"[get_website_tag_catalog] {error_message}")

                # Try to get error details from response
                try:
                    error_body = decode_response(response)
                    logger.error(f"[get_website_tag_catalog] API Error Response: {error_body}")
                    return {
                        "error": error_message,
                        "details": error_body,
                        "status_code": response.status
                    }
                except Exception:
                    return {"error": error_message, "status_code": response.status}

            # Read and parse the response content
            response_text = decode_response(response)
            import json
            full_response = json.loads(response_text)

            # Use shared function to process tag catalog response
            result_dict = process_tag_catalog_response(full_response, beacon_type, use_case)

            logger.debug(f"[get_website_tag_catalog] Returning {result_dict['count']} tag names for {beacon_type}/{use_case}")
            return result_dict
        except Exception as e:
            logger.error(f"[get_website_tag_catalog] Error: {e}", exc_info=True)
            return {"error": f"Failed to get website tag catalog: {e!s}"}
