"""
Application Catalog MCP Tools Module

This module provides application catalog-specific MCP tools for Instana monitoring.
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

from src.core.utils import (
    BaseInstanaClient,
    register_as_tool,
    with_header_auth,
)
from src.prompts import mcp

try:
    from instana_client.api.application_catalog_api import (
        ApplicationCatalogApi,
    )

except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationCatalogMCPTools(BaseInstanaClient):
    """Tools for application catalog in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Catalog MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Application Tag Catalog",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationCatalogApi)
    async def get_application_tag_catalog(self,
                                          use_case: Optional[str] = None,
                                          data_source: Optional[str] = None,
                                          var_from: Optional[int] = None,
                                          ctx = None, api_client=None) -> Dict[str, Any]:
        """
        Get application tag catalog data from Instana Server.
        This tool retrieves application tag catalog data for a specific use case and data source.
        It allows you to specify the use case (e.g., 'GROUPING'), data source (e.g., 'CALLS'),
        and a timestamp from which to get data.

        Args:
            use_case: The use case for the tag catalog (e.g., 'GROUPING')
            data_source: The data source for the tag catalog (e.g., 'CALLS')
            var_from: The timestamp from which to get data
            ctx: Context information

        Returns:
            A dictionary containing the application tag catalog data
        """
        try:
            logger.debug(f"get_application_tag_catalog called with use_case={use_case}, data_source={data_source}, var_from={var_from}")

            if not var_from:
                var_from = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)

            raw_response = api_client.get_application_tag_catalog_without_preload_content(
                use_case=use_case,
                data_source=data_source,
                var_from=var_from,
            )

            raw_data = raw_response.data
            parsed = json.loads(raw_data)

            def trim_tag_tree(obj):
                if "tagTree" in obj and isinstance(obj["tagTree"], list):
                    obj["tagTree"] = obj["tagTree"][:3]  # Limit to top 3 levels
                    for level in obj["tagTree"]:
                        if "children" in level and isinstance(level["children"], list):
                            level["children"] = level["children"][:3]  # Limit to 3 tags per level
                return obj

            # Normalize the parsed structure and apply trim
            if isinstance(parsed, str):
                parsed = json.loads(parsed)

            if isinstance(parsed, list):
                # Return the list as-is for list responses
                parsed = [trim_tag_tree(item) for item in parsed if isinstance(item, dict)]
                # Wrap list in a dictionary to match return type
                result_dict = {"tags": parsed}
            elif isinstance(parsed, dict):
                result_dict = trim_tag_tree(parsed)
            else:
                logger.debug(f"Unexpected response format: {type(parsed)}")
                return {"error": "Unexpected response format from API"}

            logger.debug(f"Result from get_application_tag_catalog: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_application_tag_catalog: {e}", exc_info=True)
            return {"error": f"Failed to get application catalog: {e!s}"}


    @register_as_tool(
        title="Get Application Metric Catalog",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationCatalogApi)
    async def get_application_metric_catalog(self, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        This API endpoint retrieves  all available metric definitions for application monitoring.
        This tool allows you to discover what metrics are available for monitoring different components in your application environment.

        Args:
            ctx: Context information

        Returns:
            A dictionary containing the application metric catalog data
        """
        try:
            logger.debug("get_application_metric_catalog called")

            # Call the API to get application metric catalog data
            result = api_client.get_application_catalog_metrics()

            # Handle different result types
            if hasattr(result, "to_dict"):
                result_data = result.to_dict()
            else:
                result_data = result

            # Ensure we always return a dict
            if isinstance(result_data, list):
                result_dict = {"metrics": result_data}
            elif isinstance(result_data, dict):
                result_dict = result_data
            else:
                # Handle case where result_data is a MetricDescription object or other type
                try:
                    # Try to convert to dict if it has attributes
                    if hasattr(result_data, "__dict__"):
                        result_dict = {"metrics": [result_data.__dict__]}
                    else:
                        result_dict = {"metrics": [str(result_data)]}
                except Exception:
                    result_dict = {"metrics": [str(result_data)]}

            logger.debug(f"Result from get_application_metric_catalog: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_application_metric_catalog: {e}", exc_info=True)
            return {"error": f"Failed to get application metric catalog: {e!s}"}
