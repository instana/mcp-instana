"""
Infrastructure Metrics MCP Tools Module

This module provides infrastructure metrics-specific MCP tools for Instana monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations
from pydantic import StrictBool

from src.core.utils import (
    BaseInstanaClient,
    register_as_tool,
    with_header_auth,
)

try:
    from instana_client.api.infrastructure_metrics_api import (
        InfrastructureMetricsApi,
    )
    from instana_client.models.get_combined_metrics import (
        GetCombinedMetrics,
    )
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

class InfrastructureMetricsMCPTools(BaseInstanaClient):
    """Tools for infrastructure metrics in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Infrastructure Analyze MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Infrastructure Metrics",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureMetricsApi)
    async def get_infrastructure_metrics(self,
                                         offline: Optional[StrictBool] = False,
                                         snapshot_ids: Optional[Union[str, List[str]]] = None,
                                         metrics: Optional[List[str]] = None,
                                         time_frame: Optional[Dict[str, int]] = None,
                                         rollup: Optional[int] = None,
                                         query: Optional[str] = None,
                                         plugin: Optional[str]=None,
                                         ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get infrastructure metrics from Instana server.
        This tool retrieves infrastructure metrics for specific components in your environment.
        It supports filtering by snapshot IDs, time ranges, metric types, and plugin source.
        Use this tool to analyze system health, performance trends, and resource utilization
        for infrastructure entities (e.g., hosts, containers, JVMs).

        Args:
            metrics: List of metrics to retrieve with their aggregations
            snapshot_ids: Snapshot ID to retrieve metrics for
            time_frame: Dictionary with 'from' and 'to' timestamps in milliseconds
                Example: {"from": 1617994800000, "to": 1618081200000}
            offline: Whether to include offline snapshots.
            plugin: Plugin to use for retrieving metrics
            limit: Maximum number of items to return (default: 3)
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing application metrics data or error information
        """

        try:

            # If no metrics is provided, return an error
            if not metrics:
                return {"error": "Metrics is required for this operation"}


            # If no plugin is provided, return an error
            if not plugin:
                return {"error": "Plugin is required for this operation"}

            if not query:
                return {"error": "Query is required for this operation"}


            if not time_frame:
                to_time = int(datetime.now().timestamp() * 1000)
                from_time = to_time - (60 * 60 * 1000)  # Default to 1 hour
                time_frame = {
                    "from": from_time,
                    "to": to_time
                }

            if not rollup:
                rollup = 60  # Default rollup to 60 seconds

            # Create the request body
            request_body = {
                "metrics": metrics,
                "plugin": plugin,
                "rollup": rollup,
                "query": query,
                "timeFrame": time_frame,
            }

            # Add snapshot IDs if provided
            if snapshot_ids:
                if isinstance(snapshot_ids, str):
                    snapshot_ids = [snapshot_ids]
                elif not isinstance(snapshot_ids, list):
                    logger.debug(f"Invalid snapshot_ids type: {type(snapshot_ids)}")
                    return {"error": "snapshot_ids must be a string or list of strings"}
                request_body["snapshotIds"] = snapshot_ids

            logger.debug("Sending request to Instana SDK with payload:")
            logger.debug(json.dumps(request_body, indent=2))

            # Create the InfrastructureMetricsApi object
            get_combined_metrics = GetCombinedMetrics(**request_body)

            # Call the get_infrastructure_metrics method from the SDK
            result = api_client.get_infrastructure_metrics(
                offline=offline,
                get_combined_metrics=get_combined_metrics
            )

            # Convert the result to a dictionary
            result_dict: Dict[str, Any] = {}

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            elif isinstance(result, list):
                # If it's a list, wrap it in a dictionary
                result_dict = {"items": result}
            else:
                # For any other type, convert to string and wrap
                result_dict = {"result": str(result)}

            # Limit the response size
            if "items" in result_dict and isinstance(result_dict["items"], list):
                # Limit items to top 3
                items_list = result_dict["items"]
                original_count = len(items_list)
                if original_count > 3:
                    result_dict["items"] = items_list[:3]
                    logger.debug(f"Limited response items from {original_count} to 3")

            # Remove any large nested structures to further reduce size
            if isinstance(result_dict, dict):
                for key, value in dict(result_dict).items():
                    if isinstance(value, list) and len(value) > 3 and key != "items":
                        original_count = len(value)
                        result_dict[key] = value[:3]
                        logger.debug(f"Limited {key} from {original_count} to 3")

            try:
                logger.debug(f"Result from get_infrastructure_metrics: {json.dumps(result_dict, indent=2)}")
            except TypeError:
                logger.debug(f"Result from get_infrastructure_metrics: {result_dict} (not JSON serializable)")

            return result_dict

        except Exception as e:
            logger.error(f"Error in get_infrastructure_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get Infra metrics: {e!s}"}
