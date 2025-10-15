"""
Infrastructure Topology MCP Tools Module

This module provides infrastructure topology-specific MCP tools for Instana monitoring.
"""

import logging
import sys
from typing import Any, Dict, Optional

# Import the necessary classes from the SDK
try:
    from instana_client.api.infrastructure_topology_api import (
        InfrastructureTopologyApi,  #type: ignore
    )
    from instana_client.api_client import ApiClient  #type: ignore
    from instana_client.configuration import Configuration  #type: ignore

except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import infrastructure topology API", exc_info=True)
    raise

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

def debug_print(*args, **kwargs):
    """
    Print debug information to stderr.

    This function is used for debugging purposes and prints information to stderr.
    It accepts the same arguments as the built-in print function.

    Args:
        *args: Variable length argument list to print
        **kwargs: Arbitrary keyword arguments to pass to print function
    """
    # Use logger.debug instead of direct printing
    message = " ".join(str(arg) for arg in args)
    logger.debug(message)

class InfrastructureTopologyMCPTools(BaseInstanaClient):
    """Tools for infrastructure topology in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Infrastructure Topology MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Related Hosts",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureTopologyApi)
    async def get_related_hosts(self,
                                snapshot_id: str,
                                to_time: Optional[int] = None,
                                window_size: Optional[int] = None,
                                ctx=None,
                                api_client=None) -> Dict[str, Any]:
        """
        Get hosts related to a specific snapshot.

        This tool retrieves a list of host IDs that are related to the specified snapshot. Use this when you need to
        understand the relationships between infrastructure components, particularly which hosts are connected to
        a specific entity.

        For example, use this tool when:
        - You need to find all hosts connected to a specific container, process, or service
        - You want to understand the infrastructure dependencies of an application component
        - You're investigating an issue and need to see which hosts might be affected

        Args:
            snapshot_id: The ID of the snapshot to find related hosts for (required)
            to_time: End timestamp in milliseconds (optional)
            window_size: Window size in milliseconds (optional)
            ctx: The MCP context (optional)
            api_client: API client for testing (optional)

        Returns:
            Dictionary containing related hosts information or error information
        """
        try:
            logger.debug(f"get_related_hosts called with snapshot_id={snapshot_id}")

            if not snapshot_id:
                return {"error": "snapshot_id parameter is required"}

            # Call the get_related_hosts method from the SDK
            result = api_client.get_related_hosts(
                snapshot_id=snapshot_id,
                to=to_time,
                window_size=window_size
            )

            # Convert the result to a dictionary
            if isinstance(result, list):
                result_dict = {
                    "relatedHosts": result,
                    "count": len(result),
                    "snapshotId": snapshot_id
                }
            else:
                # For any other type, convert to string representation
                result_dict = {"data": str(result), "snapshotId": snapshot_id}

            logger.debug(f"Result from get_related_hosts: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_related_hosts: {e}", exc_info=True)
            return {"error": f"Failed to get related hosts: {e!s}"}

    @register_as_tool(
        title="Get Topology",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureTopologyApi)
    async def get_topology(self,
                           include_data: Optional[bool] = False,
                           ctx=None,
                           api_client=None) -> Dict[str, Any]:
        """
        Get the infrastructure topology information.

        This tool retrieves the complete infrastructure topology from Instana, showing how all monitored entities
        are connected. Use this when you need a comprehensive view of your infrastructure's relationships and dependencies.

        The topology includes nodes (representing entities like hosts, processes, containers) and edges (representing
        connections between entities). This is useful for understanding the overall structure of your environment.

        For example, use this tool when:
        - You need a complete map of your infrastructure
        - You want to understand how components are connected
        - You're analyzing dependencies between systems
        - You need to visualize your infrastructure's architecture

        Args:
            include_data: Whether to include detailed snapshot data in nodes (optional, default: False)
            ctx: The MCP context (optional)
            api_client: API client for testing (optional)

        Returns:
            Dictionary containing infrastructure topology information with detailed summary or error information
        """
        try:
            logger.debug(f"get_topology called - using include_data={include_data}")

            # Use the API client from the decorator
            try:
                result = api_client.get_topology(include_data=include_data)
                logger.debug("SDK call successful, processing result")
            except Exception as sdk_error:
                logger.error(f"SDK validation error: {sdk_error}")

                # If it's a validation error, try to extract useful information from the error
                if "validation error" in str(sdk_error).lower():
                    return {
                        "error": "SDK validation error occurred",
                        "details": str(sdk_error),
                        "suggestion": "The API response format may not match the expected SDK model structure. This often happens with complex Kubernetes or cloud infrastructure data.",
                        "workaround": "Consider using other topology tools like get_related_hosts with specific snapshot IDs, or check if the include_data parameter affects the response format."
                    }
                else:
                    # Re-raise if it's not a validation error
                    raise sdk_error

            # Convert the result to a dictionary
            result_dict = None

            # Try different ways to convert the result
            if hasattr(result, 'to_dict'):
                try:
                    result_dict = result.to_dict()
                    logger.debug("Successfully converted result using to_dict()")
                except Exception as e:
                    logger.error(f"to_dict() failed: {e}")

            if result_dict is None and isinstance(result, dict):
                result_dict = result
                logger.debug("Result is already a dictionary")

            if result_dict is None:
                # Try to extract data from the result object manually
                try:
                    if hasattr(result, '__dict__'):
                        result_dict = result.__dict__
                        logger.debug("Extracted data using __dict__")
                    else:
                        result_dict = {"data": str(result)}
                        logger.debug("Converted result to string representation")
                except Exception as e:
                    logger.error(f"Manual extraction failed: {e}")
                    result_dict = {"data": str(result)}

            # Process the result if we have valid data
            if isinstance(result_dict, dict) and ('nodes' in result_dict or 'data' in result_dict):
                nodes = result_dict.get('nodes', [])
                edges = result_dict.get('edges', [])

                logger.debug(f"Processing {len(nodes)} nodes and {len(edges)} edges")

                # If we have no nodes but have data, try to extract from data field
                if not nodes and 'data' in result_dict:
                    logger.debug("No nodes found, checking data field")
                    return {
                        "summary": {
                            "status": "Data retrieved but in unexpected format",
                            "dataType": type(result_dict.get('data')).__name__,
                            "dataPreview": str(result_dict.get('data'))[:200] + "..." if len(str(result_dict.get('data'))) > 200 else str(result_dict.get('data'))
                        },
                        "rawDataAvailable": True,
                        "note": "Topology data was retrieved but not in the expected nodes/edges format"
                    }

                # Take only first 30 nodes for analysis to avoid token limits
                sample_nodes = nodes[:30] if len(nodes) > 30 else nodes
                sample_edges = edges[:30] if len(edges) > 30 else edges

                # Count nodes by plugin type from sample
                plugin_counts = {}
                host_info = {}
                kubernetes_resources = {}
                sample_nodes_details = []

                for node in sample_nodes:
                    if not isinstance(node, dict):
                        continue

                    plugin = node.get('plugin', 'unknown')
                    plugin_counts[plugin] = plugin_counts.get(plugin, 0) + 1

                    # Keep minimal node info for sample
                    node_label = str(node.get('label', 'unknown'))
                    if len(node_label) > 40:
                        node_label = node_label[:37] + "..."

                    node_id = str(node.get('id', ''))
                    if len(node_id) > 15:
                        node_id = node_id[:12] + "..."

                    sample_nodes_details.append({
                        'plugin': plugin,
                        'label': node_label,
                        'id': node_id
                    })

                    # Extract host information
                    if plugin == 'host':
                        label = str(node.get('label', 'unknown'))
                        host_info[label] = str(node.get('id', ''))

                    # Group Kubernetes resources
                    if plugin.startswith('kubernetes'):
                        k8s_type = plugin.replace('kubernetes', '').lower()
                        if k8s_type not in kubernetes_resources:
                            kubernetes_resources[k8s_type] = 0
                        kubernetes_resources[k8s_type] += 1

                # Estimate total counts based on sample
                sample_size = len(sample_nodes)
                total_size = len(nodes)
                scaling_factor = total_size / sample_size if sample_size > 0 else 1

                estimated_plugin_counts = {}
                for plugin, count in plugin_counts.items():
                    estimated_plugin_counts[plugin] = int(count * scaling_factor)

                # Create comprehensive summary
                summary = {
                    'totalNodes': len(nodes),
                    'totalEdges': len(edges),
                    'sampleAnalysis': {
                        'sampleSize': sample_size,
                        'scalingFactor': round(scaling_factor, 2),
                        'note': f'Analysis based on first {sample_size} nodes out of {total_size} total'
                    },
                    'topPluginTypes': dict(sorted(estimated_plugin_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                    'infrastructureOverview': {
                        'estimatedHosts': int(len(host_info) * scaling_factor),
                        'sampleHosts': list(host_info.keys())[:3],  # Show first 3 hosts
                        'kubernetesTypes': kubernetes_resources,
                        'estimatedContainers': int((plugin_counts.get('crio', 0) + plugin_counts.get('containerd', 0) + plugin_counts.get('docker', 0)) * scaling_factor),
                        'estimatedProcesses': int(plugin_counts.get('process', 0) * scaling_factor)
                    }
                }

                # Add edge analysis from sample if available
                if sample_edges:
                    edge_types = {}
                    for edge in sample_edges:
                        if isinstance(edge, dict):
                            edge_type = edge.get('type', 'unknown')
                            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

                    if edge_types:
                        summary['connectionAnalysis'] = {
                            'sampleEdgeTypes': edge_types,
                            'sampleEdgesAnalyzed': len(sample_edges)
                        }

                # Return compact summary
                return {
                    'summary': summary,
                    'sampleNodes': sample_nodes_details[:8],  # Just 8 example nodes
                    'status': 'success',
                    'note': 'Topology data processed successfully with sampling to manage size'
                }
            else:
                return {
                    "error": "Unexpected data format",
                    "dataType": type(result_dict).__name__,
                    "availableKeys": list(result_dict.keys()) if isinstance(result_dict, dict) else "Not a dictionary",
                    "suggestion": "The topology data may be in a different format than expected"
                }

        except Exception as e:
            logger.error(f"Error in get_topology: {e}", exc_info=True)
            return {
                "error": f"Failed to get topology: {e!s}",
                "errorType": type(e).__name__,
                "suggestion": "This may be due to API response format changes or network issues"
            }

