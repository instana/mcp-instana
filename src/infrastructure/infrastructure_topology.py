"""
Infrastructure Topology MCP Tools Module

This module provides infrastructure topology-specific MCP tools for Instana monitoring.
"""

import logging
from typing import Any, Dict, Optional

# Import the necessary classes from the SDK
try:
    from instana_client.api.infrastructure_topology_api import (
        InfrastructureTopologyApi,  #type: ignore
    )

except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import infrastructure topology API", exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)

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

    # @register_as_tool(...)  # Disabled for future reference
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
            result = await sdk_call_with_keepalive(call_sdk_fn(api_client.get_related_hosts, snapshot_id=snapshot_id, to=to_time, window_size=window_size), ctx=ctx, operation_name="get_related_hosts")

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

    # @register_as_tool(...)  # Disabled for future reference
    def _parse_topology_response(self, response):
        """Parse topology response and return result dict."""
        import json
        try:
            response_text = response.data.decode('utf-8')
            result = json.loads(response_text)
            logger.debug("Successfully parsed topology data as JSON")
            return result, None
        except (json.JSONDecodeError, AttributeError) as json_err:
            error_message = f"Failed to parse JSON response: {json_err}"
            logger.error(error_message)
            return None, {"error": error_message}

    def _convert_result_to_dict(self, result):
        """Convert result to dictionary using various methods."""
        if hasattr(result, 'to_dict'):
            try:
                return result.to_dict()
            except Exception as e:
                logger.error(f"to_dict() failed: {e}")

        if isinstance(result, dict):
            return result

        # Try manual extraction
        if hasattr(result, '__dict__'):
            return result.__dict__

        return {"data": str(result)}

    def _analyze_node(self, node, plugin_counts, host_info, kubernetes_resources):
        """Analyze a single node and update counters."""
        if not isinstance(node, dict):
            return None

        plugin = node.get('plugin', 'unknown')
        plugin_counts[plugin] = plugin_counts.get(plugin, 0) + 1

        # Prepare node details
        node_label = str(node.get('label', 'unknown'))
        if len(node_label) > 80:
            node_label = node_label[:77] + "..."

        node_details = {
            'plugin': plugin,
            'label': node_label,
            'id': str(node.get('id', ''))
        }

        # Extract host information
        if plugin == 'host':
            label = str(node.get('label', 'unknown'))
            host_info[label] = str(node.get('id', ''))

        # Group Kubernetes resources
        if plugin.startswith('kubernetes'):
            k8s_type = plugin.replace('kubernetes', '').lower()
            kubernetes_resources[k8s_type] = kubernetes_resources.get(k8s_type, 0) + 1

        return node_details

    def _create_topology_summary(self, nodes, edges, sample_nodes, plugin_counts, host_info, kubernetes_resources):
        """Create comprehensive topology summary."""
        sample_size = len(sample_nodes)
        total_size = len(nodes)
        scaling_factor = total_size / sample_size if sample_size > 0 else 1

        estimated_plugin_counts = {
            plugin: int(count * scaling_factor)
            for plugin, count in plugin_counts.items()
        }

        return {
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
                'sampleHosts': list(host_info.keys())[:3],
                'kubernetesTypes': kubernetes_resources,
                'estimatedContainers': int((plugin_counts.get('crio', 0) + plugin_counts.get('containerd', 0) + plugin_counts.get('docker', 0)) * scaling_factor),
                'estimatedProcesses': int(plugin_counts.get('process', 0) * scaling_factor)
            }
        }

    def _analyze_edges(self, sample_edges):
        """Analyze edge types from sample."""
        edge_types = {}
        for edge in sample_edges:
            if isinstance(edge, dict):
                edge_type = edge.get('type', 'unknown')
                edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        return edge_types if edge_types else None

    def _handle_unexpected_data_format(self, result_dict, nodes):
        """Handle case where data is in unexpected format."""
        if not nodes and 'data' in result_dict:
            logger.debug("No nodes found, checking data field")
            data_str = str(result_dict.get('data'))
            data_preview = data_str[:200] + "..." if len(data_str) > 200 else data_str
            return {
                "summary": {
                    "status": "Data retrieved but in unexpected format",
                    "dataType": type(result_dict.get('data')).__name__,
                    "dataPreview": data_preview
                },
                "rawDataAvailable": True,
                "note": "Topology data was retrieved but not in the expected nodes/edges format"
            }
        return None

    def _process_topology_nodes_and_edges(self, nodes, edges):
        """Process topology nodes and edges to create summary."""
        sample_nodes = nodes[:30] if len(nodes) > 30 else nodes
        sample_edges = edges[:30] if len(edges) > 30 else edges

        plugin_counts = {}
        host_info = {}
        kubernetes_resources = {}
        sample_nodes_details = []

        for node in sample_nodes:
            node_details = self._analyze_node(node, plugin_counts, host_info, kubernetes_resources)
            if node_details:
                sample_nodes_details.append(node_details)

        # Create summary
        summary = self._create_topology_summary(nodes, edges, sample_nodes, plugin_counts, host_info, kubernetes_resources)

        # Add edge analysis if available
        if sample_edges:
            edge_types = self._analyze_edges(sample_edges)
            if edge_types:
                summary['connectionAnalysis'] = {
                    'sampleEdgeTypes': edge_types,
                    'sampleEdgesAnalyzed': len(sample_edges)
                }

        return {
            'summary': summary,
            'sampleNodes': sample_nodes_details[:8],
            'status': 'success',
            'note': 'Topology data processed successfully with sampling to manage size'
        }

    def _handle_invalid_result_format(self, result_dict):
        """Handle case where result is not in expected format."""
        return {
            "error": "Unexpected data format",
            "dataType": type(result_dict).__name__,
            "availableKeys": list(result_dict.keys()) if isinstance(result_dict, dict) else "Not a dictionary",
            "suggestion": "The topology data may be in a different format than expected"
        }

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

        This implementation uses the `get_topology_without_preload_content` method from the SDK to bypass validation
        issues that can occur with complex Kubernetes infrastructure data.

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

            # Get and parse topology data
            try:
                response = await sdk_call_with_keepalive(call_sdk_fn(api_client.get_topology_without_preload_content, include_data=include_data), ctx=ctx, operation_name="get_topology_without_preload_content")
                logger.debug("SDK call successful using get_topology_without_preload_content")

                result, error = self._parse_topology_response(response)
                if error:
                    return error
            except Exception as sdk_error:
                logger.error(f"SDK error: {sdk_error}")
                return {
                    "error": "Failed to get topology data",
                    "details": str(sdk_error),
                    "suggestion": "The API may be unavailable or the request format is incorrect.",
                    "workaround": "Try again later or check if the include_data parameter affects the response."
                }

            # Convert result to dictionary
            result_dict = self._convert_result_to_dict(result)

            # Process the result if we have valid data
            if isinstance(result_dict, dict) and ('nodes' in result_dict or 'data' in result_dict):
                nodes = result_dict.get('nodes', [])
                edges = result_dict.get('edges', [])

                logger.debug(f"Processing {len(nodes)} nodes and {len(edges)} edges")

                # If we have no nodes but have data, try to extract from data field
                unexpected_format = self._handle_unexpected_data_format(result_dict, nodes)
                if unexpected_format:
                    return unexpected_format

                # Process nodes and edges
                return self._process_topology_nodes_and_edges(nodes, edges)
            else:
                return self._handle_invalid_result_format(result_dict)

        except Exception as e:
            logger.error(f"Error in get_topology: {e}", exc_info=True)
            return {
                "error": f"Failed to get topology: {e!s}",
                "errorType": type(e).__name__,
                "suggestion": "This may be due to API response format changes or network issues"
            }

