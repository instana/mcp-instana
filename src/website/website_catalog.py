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

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class WebsiteCatalogMCPTools(BaseInstanaClient):
    """Tools for website catalog in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Website Catalog MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Website Catalog Metrics",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteCatalogApi)
    async def get_website_catalog_metrics(self, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get website monitoring metrics catalog.

        This API endpoint retrieves all available metric definitions for website monitoring.
        Use this to discover what metrics are available for website monitoring.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing available website metrics or error information
        """
        try:
            logger.debug("get_website_catalog_metrics called")

            # Call the get_website_catalog_metrics method from the SDK
            result = api_client.get_website_catalog_metrics()

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
                result_dict = {"metrics": result_list, "count": len(result_list)}
            else:
                result_dict = {"data": result_list}

            logger.debug(f"Result from get_website_catalog_metrics: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_website_catalog_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get website catalog metrics: {e!s}"}

    @register_as_tool(
        title="Get Website Catalog Tags",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteCatalogApi)
    async def get_website_catalog_tags(self, ctx=None, api_client=None) -> Dict[str, Any]:
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
            logger.debug("get_website_catalog_tags called")

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

            logger.debug(f"Result from get_website_catalog_tags: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_website_catalog_tags: {e}", exc_info=True)
            return {"error": f"Failed to get website catalog tags: {e!s}"}

    @register_as_tool(
        title="Get Website Tag Catalog",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteCatalogApi)
    async def get_website_tag_catalog(self,
                                    beacon_type: str,
                                    use_case: str,
                                    ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get website monitoring tag catalog.

        This API endpoint retrieves all available tags for website monitoring.
        Use this to discover what tags are available for filtering website beacons.

        Args:
            beacon_type: The beacon type (e.g., 'PAGELOAD')
            use_case: The use case (e.g., 'GROUPING')
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing available website tags or error information
        """
        try:
            logger.debug("get_website_tag_catalog called")
            if not beacon_type:
                return {"error": "beacon_type parameter is required"}
            if not use_case:
                return {"error": "use_case parameter is required"}

            # Call the get_website_tag_catalog method from the SDK
            result = api_client.get_website_tag_catalog(
                beacon_type=beacon_type,
                use_case=use_case
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_website_tag_catalog: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_website_tag_catalog: {e}", exc_info=True)
            return {"error": f"Failed to get website tag catalog: {e!s}"}
