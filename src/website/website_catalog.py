"""
Website Catalog MCP Tools Module

This module provides website catalog-specific MCP tools for Instana monitoring.
"""

import logging
from email.message import Message
from typing import Any, Dict, List, Optional

from fastmcp import Context

# Import the necessary classes from the SDK
try:
    from instana_client.api.website_catalog_api import WebsiteCatalogApi
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
    charset = 'utf-8'  # Default fallback

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
        # Fallback to utf-8 if specified charset fails
        return response.data.decode('utf-8', errors='replace')


class WebsiteCatalogMCPTools(BaseInstanaClient):
    """Tools for website catalog in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Website Catalog MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)


    @with_header_auth(WebsiteCatalogApi)
    async def get_website_catalog_metrics(self, ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Get website monitoring metrics catalog.

        This API endpoint retrieves all available metric IDs for website monitoring.
        Returns a simple list of valid metric IDs that can be used in queries.
        This serves as schema information for LLM to know what metrics are available.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing list of valid metric IDs
        """
        try:
            logger.debug("[get_website_catalog_metrics] Called")

            # Use without_preload_content to bypass Pydantic validation
            response = api_client.get_website_catalog_metrics_without_preload_content()

            # Check if the response was successful
            if response.status != 200:
                error_message = f"Failed to get website catalog metrics: HTTP {response.status}"
                logger.error(f"[get_website_catalog_metrics] {error_message}")

                # Try to get error details from response
                try:
                    error_body = _decode_response(response)
                    logger.error(f"[get_website_catalog_metrics] API Error Response: {error_body}")
                    return {
                        "error": error_message,
                        "details": error_body,
                        "status_code": response.status
                    }
                except Exception:
                    return {"error": error_message, "status_code": response.status}

            # Read and parse the response content
            response_text = _decode_response(response)
            import json
            full_metrics = json.loads(response_text)

            # Extract only metric IDs - this is schema information for LLM
            metric_ids = [metric.get("metricId") for metric in full_metrics if metric.get("metricId")]

            result_dict = {
                "metric_ids": metric_ids,
                "count": len(metric_ids)
            }

            logger.debug(f"[get_website_catalog_metrics] Returning {len(metric_ids)} metric IDs from catalog")
            return result_dict
        except Exception as e:
            logger.error(f"[get_website_catalog_metrics] Error: {e}", exc_info=True)
            return {"error": f"Failed to get website catalog metrics: {e!s}"}

    @with_header_auth(WebsiteCatalogApi)
    async def get_website_catalog_tags(self, ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
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
            result = api_client.get_website_catalog_tags()

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
                                    ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
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
            response = api_client.get_website_tag_catalog_without_preload_content(
                beacon_type=beacon_type,
                use_case=use_case
            )

            # Check if the response was successful
            if response.status != 200:
                error_message = f"Failed to get website tag catalog: HTTP {response.status}"
                logger.error(f"[get_website_tag_catalog] {error_message}")

                # Try to get error details from response
                try:
                    error_body = _decode_response(response)
                    logger.error(f"[get_website_tag_catalog] API Error Response: {error_body}")
                    return {
                        "error": error_message,
                        "details": error_body,
                        "status_code": response.status
                    }
                except Exception:
                    return {"error": error_message, "status_code": response.status}

            # Read and parse the response content
            response_text = _decode_response(response)
            import json
            full_response = json.loads(response_text)

            # Extract tag names from both tagTree and tags
            tag_names = []

            # Helper function to recursively extract tagName from tree structure
            def extract_tag_names_from_tree(node):
                """Recursively extract tagName values from nested tree structure"""
                if isinstance(node, dict):
                    # If this node has a tagName, add it
                    if node.get("tagName"):
                        tag_names.append(node["tagName"])

                    # Recursively process children
                    if "children" in node and isinstance(node["children"], list):
                        for child in node["children"]:
                            extract_tag_names_from_tree(child)
                elif isinstance(node, list):
                    # If it's a list, process each item
                    for item in node:
                        extract_tag_names_from_tree(item)

            # Extract from tagTree
            if "tagTree" in full_response:
                extract_tag_names_from_tree(full_response["tagTree"])

            # Extract from flat tags list (using 'name' field)
            if "tags" in full_response and isinstance(full_response["tags"], list):
                for tag in full_response["tags"]:
                    if isinstance(tag, dict) and "name" in tag and tag["name"]:
                        tag_names.append(tag["name"])

            # Remove duplicates and sort
            tag_names = sorted(set(tag_names))

            result_dict = {
                "tag_names": tag_names,
                "count": len(tag_names),
                "beacon_type": beacon_type,
                "use_case": use_case
            }

            logger.debug(f"[get_website_tag_catalog] Returning {len(tag_names)} tag names for {beacon_type}/{use_case}")
            return result_dict
        except Exception as e:
            logger.error(f"[get_website_tag_catalog] Error: {e}", exc_info=True)
            return {"error": f"Failed to get website tag catalog: {e!s}"}
