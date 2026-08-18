"""
Synthetic Catalog MCP Tools Module

This module provides synthetic catalog-specific MCP tools for Instana monitoring.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Import the necessary classes from the SDK
try:
    from instana_client.api.synthetic_catalog_api import SyntheticCatalogApi
except ImportError as e:
    logger.error("Error importing Instana SDK: %s", e, exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    decode_response,
    process_tag_catalog_response,
    project_metric_card,
    with_header_auth,
)


class SyntheticCatalogMCPTools(BaseInstanaClient):
    """Tools for synthetic catalog in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Synthetic Catalog MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)


    @with_header_auth(SyntheticCatalogApi)
    async def get_synthetic_catalog_metrics(
        self,
        ctx=None,
        api_client=None,
        view: str = "planner",
    ) -> Dict[str, Any]:
        """
        Get synthetic monitoring metrics catalog.

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
            logger.debug("[get_synthetic_catalog_metrics] Called with view=%s", view)

            if view not in ("planner", "full"):
                return {
                    "error": f"Invalid view '{view}'. Valid views: 'planner', 'full'",
                    "valid_views": ["planner", "full"],
                }

            # Use without_preload_content to bypass Pydantic validation
            response = api_client.get_synthetic_catalog_metrics_without_preload_content()

            # Check if the response was successful
            if response.status != 200:
                return self.handle_api_error_response(response, "get synthetic catalog metrics", logger)

            # Read and parse the response content
            response_text = decode_response(response)
            full_metrics = json.loads(response_text)

            # Extract only metric IDs - this is schema information for LLM
            metric_ids = [metric.get("metricId") for metric in full_metrics if metric.get("metricId")]

            if view == "full":
                result_dict = {
                    "metrics": full_metrics,
                    "count": len(metric_ids),
                    "description": "Synthetic monitoring metrics catalog with full metadata"
                }
            else:
                compact_metrics = [project_metric_card(metric) for metric in full_metrics]
                result_dict = {
                    "metrics": compact_metrics,
                    "count": len(metric_ids),
                    "description": "Synthetic monitoring metrics catalog with necessary metadata for query planning"
                }

            logger.debug("[get_synthetic_catalog_metrics] Returning %d metric IDs from catalog", len(metric_ids))
            return result_dict
        except Exception as e:
            logger.error("[get_synthetic_catalog_metrics] Error: %s", e, exc_info=True)
            return {"error": f"Failed to get synthetic catalog metrics: {e!s}"}

    @with_header_auth(SyntheticCatalogApi)
    async def get_synthetic_tag_catalog(
        self,
        use_case: str,
        ctx=None,
        api_client=None,
    ) -> Dict[str, Any]:
        """
        Get synthetic monitoring tag catalog.

        Returns a list of valid tag names that can be used for filtering synthetic
        monitoring data. Synthetics has no beacon type concept — only use_case is
        required.

        Args:
            use_case: The use case (e.g., "GROUPING", "FILTERING", "SMART_ALERTS")
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing tag_names, count, and use_case.
        """
        try:
            logger.debug("[get_synthetic_tag_catalog] Called with use_case=%s", use_case)

            if not use_case:
                logger.warning("[get_synthetic_tag_catalog] Missing required param: use_case")
                return {"error": "use_case parameter is required"}

            # Use without_preload_content to bypass Pydantic validation
            response = api_client.get_synthetic_tag_catalog_without_preload_content(
                use_case=use_case
            )

            # Check if the response was successful
            if response.status != 200:
                return self.handle_api_error_response(response, "get synthetic tag catalog", logger)

            # Read and parse the response content
            response_text = decode_response(response)
            full_response = json.loads(response_text)

            # Use shared function to extract tag names from tagTree / tags list
            result_dict = process_tag_catalog_response(full_response, beacon_type=None, use_case=use_case)

            logger.debug("[get_synthetic_tag_catalog] Returning %d tag names for use_case=%s", result_dict["count"], use_case)
            return result_dict
        except Exception as e:
            logger.error("[get_synthetic_tag_catalog] Error: %s", e, exc_info=True)
            return {"error": f"Failed to get synthetic tag catalog: {e!s}"}
