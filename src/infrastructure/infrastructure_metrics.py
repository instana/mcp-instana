"""
Infrastructure Metrics MCP Tools Module

This module provides infrastructure metrics-specific MCP tools for Instana monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context
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

    # @register_as_tool(...)  # Disabled for future reference
    # Note: Not exposed as direct MCP tool - accessed via application_smart_router_tool.py
    @with_header_auth(InfrastructureMetricsApi)
    async def get_infrastructure_metrics(self,
                                         offline: Optional[StrictBool] = False,
                                         snapshot_ids: Optional[Union[str, List[str]]] = None,
                                         metrics: Optional[List[str]] = None,
                                         time_frame: Optional[Dict[str, int]] = None,
                                         rollup: Optional[int] = None,
                                         query: Optional[str] = None,
                                         plugin: Optional[str]=None,
                                         ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
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

            # Two-Pass Elicitation: Check for required parameters
            elicitation_request = self._check_elicitation_for_infra_metrics(
                metrics, plugin, query
            )
            if elicitation_request:
                logger.info("Elicitation needed for infrastructure metrics")
                return elicitation_request


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
            return {"error": f"Failed to get infrastructure metrics: {e!s}"}

    def _check_elicitation_for_infra_metrics(
        self,
        metrics: Optional[List[str]],
        plugin: Optional[str],
        query: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if required parameters are missing and create elicitation request (Two-Pass).

        Infrastructure metrics require plugin and query parameters.

        Args:
            metrics: Metrics list if provided
            plugin: Plugin name if provided
            query: Query filter if provided

        Returns:
            Elicitation request dict if parameters are missing, None otherwise
        """
        missing_params = []

        # Check for required parameters
        if not metrics:
            missing_params.append({
                "name": "metrics",
                "description": "List of metric names to retrieve (REQUIRED)",
                "examples": ["cpu.used", "memory.used", "disk.used"],
                "type": "list"
            })

        if not plugin:
            missing_params.append({
                "name": "plugin",
                "description": "Plugin type for infrastructure entity (REQUIRED)",
                "examples": ["host", "docker", "kubernetes", "jvm"],
                "type": "string"
            })

        if not query:
            missing_params.append({
                "name": "query_filter",
                "description": "Query filter to select entities (REQUIRED)",
                "examples": ["entity.type:host", "entity.type:docker", "entity.tag:production"],
                "type": "string"
            })

        # If any required parameters are missing, return elicitation request
        if missing_params:
            return self._create_elicitation_request(missing_params)

        return None

    def _create_elicitation_request(self, missing_params: list) -> Dict[str, Any]:
        """
        Create an elicitation request following MCP pattern.

        Args:
            missing_params: List of missing parameter descriptions

        Returns:
            Elicitation request dict
        """
        # Build simple, user-friendly parameter descriptions
        param_lines = []
        for param in missing_params:
            # Use the examples from the parameter definition instead of hardcoding
            examples = ", ".join([str(ex) for ex in param["examples"][:3]])
            param_lines.append(f"{param['name']}: {examples}")

        message = (
            "I need:\n\n"
            + "\n".join(param_lines)
        )

        return {
            "elicitation_needed": True,
            "message": message,
            "missing_parameters": [p["name"] for p in missing_params],
            "parameter_details": missing_params,
            "instructions": "Call query_instana_metrics again with these parameters filled in."
        }
