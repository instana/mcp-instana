"""
Smart Router Tool for Infrastructure Monitoring

This module provides a unified MCP tool that routes infrastructure monitoring queries
to the appropriate specialized tools, following the same pattern as website/application/mobile apps.

RECOMMENDED WORKFLOW:
1. get_plugins - Discover available entity types (e.g., 'host')
2. get_plugin_schema - Get BOTH metrics AND tags for a specific plugin in ONE call
   (combines get_metrics + get_tag_catalog to reduce API calls)
3. analyze operations - Query entities using the discovered types, metrics, and tags

IMPORTANT: Always call get_plugins FIRST to get valid plugin IDs. Using invalid plugin names
in get_plugin_schema will result in HTTP 400 errors with no diagnostic information.
"""

import logging
from typing import Any, Dict, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)

# Define valid operations for each resource type
ANALYZE_VALID_OPERATIONS = ["get_entities", "get_entity_groups"]
CATALOG_VALID_OPERATIONS = ["get_plugins", "get_metrics", "get_tag_catalog", "get_plugin_schema"]
RESOURCES_VALID_OPERATIONS = ["get_snapshot", "get_snapshots"]

# Define parameter key constants
PARAM_PAYLOAD = "payload"
PARAM_PLUGIN = "plugin"
PARAM_FILTER = "filter"
PARAM_SNAPSHOT_ID = "snapshot_id"
PARAM_INCLUDE_DATA = "include_data"
PARAM_TO_TIME = "to_time"
PARAM_WINDOW_SIZE = "window_size"
PARAM_QUERY = "query"
PARAM_FROM_TIME = "from_time"
PARAM_SIZE = "size"
PARAM_OFFLINE = "offline"
PARAM_DETAILED = "detailed"

# Error message constants
HINT_GET_PLUGINS_FIRST = "First call get_plugins to discover available entity types, then use one as the plugin parameter"


class InfrastructureSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for infrastructure monitoring operations.
    Routes queries to Infrastructure Analyze and Catalog tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Smart Router Infrastructure MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
        from src.infrastructure.infrastructure_analyze import InfrastructureAnalyzeMCPTools
        from src.infrastructure.infrastructure_catalog import InfrastructureCatalogMCPTools
        from src.infrastructure.infrastructure_resources import InfrastructureResourcesMCPTools

        # Initialize the infrastructure clients
        self.infrastructure_analyze_client = InfrastructureAnalyzeMCPTools(read_token, base_url)
        self.infrastructure_catalog_client = InfrastructureCatalogMCPTools(read_token, base_url)
        self.infrastructure_resources_client = InfrastructureResourcesMCPTools(read_token, base_url)

        logger.info("Smart Router Infrastructure initialized with Analyze, Catalog, Topology, and Resources tools")

    @register_as_tool(
        title="Manage Instana Infrastructure Resources",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        description="""Unified Instana infrastructure resource manager for comprehensive infrastructure monitoring.

Resource Types:
    - "analyze": Query infrastructure entity data with grouping or filtering
    - "catalog": Get available plugins, metrics, and tags for infrastructure monitoring
    - "resources": Get snapshot details and monitoring state

RECOMMENDED WORKFLOW FOR ANALYZE:
    1. FIRST: Call get_plugins to discover available entity types
       - Returns list of plugins with their IDs - these IDs are required for subsequent calls
       - Example: [{"id": "plugin_name1", ...}, {"id": "plugin_name2", ...}]
    
    2. SECOND: Call get_plugin_schema with a VALID plugin ID from step 1
       - Combines get_metrics + get_tag_catalog into ONE efficient call
       - IMPORTANT: Plugin ID must be from get_plugins - invalid IDs return HTTP 400
       - Returns: {"metrics": ["memory.usage", ...], "tags": ["host.name", ...]}
    
    3. THIRD: Use the discovered entity types, metrics, and tags in analyze operations
       - Build queries with proper type, metrics, and tagFilterExpression
       - The router auto-normalizes tagFilterExpression format to prevent HTTP 422 errors
    
ANALYZE (resource_type="analyze"):
    operations: get_entities, get_entity_groups
    params: {payload}
    
    IMPORTANT AUTO-ROUTING: The router automatically detects the correct endpoint based on payload:
    - If payload contains "groupBy" → automatically routes to get_entity_groups endpoint
    - If payload does NOT contain "groupBy" → automatically routes to get_entities endpoint
    You can specify either operation, but the router will auto-correct based on payload content.

    Aggregations: MAX, MEAN, MIN, SUM
    Operators: EQUALS, NOT_EQUAL, CONTAINS, NOT_CONTAIN, STARTS_WITH, ENDS_WITH, GREATER_THAN, GREATER_OR_EQUAL_THAN, LESS_THAN, LESS_OR_EQUAL_THAN

    payload (required): Complete request payload as dictionary
        - type (required): Entity type from get_plugins
        - metrics (required): Array of metric objects
            - metric (required): Metric name from get_metrics
            - granularity (required): Time granularity in milliseconds (e.g., 3600000 for 1 hour)
            - aggregation (required): Aggregation type (MAX, MEAN, MIN, SUM)
        - timeFrame (required): Time range for query
            - windowSize (required): Duration in milliseconds (e.g., 3600000 for 1 hour)
            - to (optional): End timestamp in milliseconds (default: now)
        - tagFilterExpression (optional): Filter expression for entities
            - type: "TAG_FILTER" for single filter, "EXPRESSION" for multiple
            - entity: "NOT_APPLICABLE" (required for TAG_FILTER)
            - name: Tag name from get_tag_catalog
            - operator: Filter operator (EQUALS, CONTAINS, etc.)
            - value: Filter value
            - logicalOperator: "AND" or "OR" (for EXPRESSION type)
            - elements: Array of TAG_FILTER objects (for EXPRESSION type)
        - pagination: Pagination settings
            - retrievalSize: Number of items to retrieve (default: 200 for entities, 20 for groups)
        - groupBy (optional, for get_entity_groups only): Array of tag names from get_tag_catalog
        - order (optional, for get_entity_groups only): Ordering settings
            - by: Field to order by (e.g., "label")
            - direction: "ASC" or "DESC"

    get_entities - Get individual infrastructure entities with metrics
    get_entity_groups - Get grouped infrastructure entities with aggregated metrics (requires groupBy parameter)

CATALOG (resource_type="catalog"):
    operations: get_plugins, get_plugin_schema, get_metrics, get_tag_catalog
    params: {plugin, filter}

    get_plugins - Get all available entity types (plugins) in your Instana installation
        Returns: List of plugin IDs that can be used as entity types
        This is the FIRST step - discover what entity types are available in your environment
    
    get_plugin_schema - Get complete schema (metrics + tags) for a plugin in ONE call (RECOMMENDED)
        - plugin (required): Plugin ID from get_plugins (e.g., "host", "jvmRuntimePlatform")
        - filter (optional): "builtin" or "custom" to filter metric types
        Returns: Dictionary with both metrics and tags for the plugin
        {
            "plugin": "host",
            "metrics": ["cpu.used", "memory.used", ...],
            "tags": {"host.name": {...}, "host.type": {...}, ...},
            "summary": {"total_metrics": 50, "total_tags": 25}
        }
        This COMBINES get_metrics and get_tag_catalog into a single call
    
    get_metrics - Get infrastructure metrics catalog for a specific plugin
        - plugin (required): Plugin ID from get_plugins (e.g., "host", "jvmRuntimePlatform")
        - filter (optional): "builtin" or "custom" to filter metric types
        Returns: List of metric names available for the plugin
        Use returned metric names exactly in analyze operations
    
    get_tag_catalog - Get valid tag names for a specific plugin
        - plugin (required): Plugin ID from get_plugins (e.g., "host", "kubernetesPod")
        Returns: Available tag names for filtering and grouping
        Use returned tag names exactly in analyze operations

RESOURCES (resource_type="resources"):
    operations: get_snapshot, get_snapshots
    params: {snapshot_id, to_time, window_size, query, from_time, size, plugin, offline, detailed}
    
    get_snapshot - Get detailed information for a specific snapshot ID
        - snapshot_id (required): The snapshot ID to retrieve details for
        - to_time (optional): End timestamp in milliseconds
        - window_size (optional): Window size in milliseconds
        Returns: Complete snapshot details including configuration, metrics, and state
        Use this when you have a specific snapshot ID and need its full details
    
    get_snapshots - Search and discover multiple snapshots matching criteria
        - query (optional): Search query string to filter snapshots
        - from_time (optional): Start timestamp in milliseconds (default: 1 hour ago)
        - to_time (optional): End timestamp in milliseconds (default: now)
        - size (optional): Maximum number of results to return (default: 100)
        - plugin (optional): Entity type to filter by (e.g., "host", "jvmRuntimePlatform")
        - offline (optional): Include offline snapshots (default: false)
        - detailed (optional): Return full raw data vs summarized (default: false)
        Returns: List of snapshots matching the search criteria
        Use this to discover entities, search infrastructure, or find components

Args:
    resource_type: "analyze", "catalog", or "resources"
    operation: Specific operation for the resource type
    params: Operation-specific parameters (optional)

Returns:
    Dictionary with results from the appropriate tool

Examples:
    resource_type="catalog", operation="get_plugins"
    resource_type="catalog", operation="get_metrics", params={"plugin": "host"}
    resource_type="catalog", operation="get_plugin_schema", params={"plugin": "host"}
    resource_type="catalog", operation="get_metrics", params={"plugin": "jvmRuntimePlatform", "filter": "builtin"}
    resource_type="catalog", operation="get_tag_catalog", params={"plugin": "host"}
    resource_type="analyze", operation="get_entities", params={"payload": {"type": "host", "metrics": [{"metric": "cpu.used", "granularity": 3600000, "aggregation": "MEAN"}], "timeFrame": {"windowSize": 3600000}}}
    resource_type="analyze", operation="get_entities", params={"payload": {"type": "jvmRuntimePlatform", "metrics": [{"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"}, {"metric": "threads.blocked", "granularity": 3600000, "aggregation": "MEAN"}], "timeFrame": {"to": 1743923995000, "windowSize": 3600000}, "tagFilterExpression": {"type": "TAG_FILTER", "entity": "NOT_APPLICABLE", "name": "host.name", "operator": "EQUALS", "value": "server1"}, "pagination": {"retrievalSize": 200}}}
    resource_type="analyze", operation="get_entity_groups", params={"payload": {"type": "kubernetesPod", "groupBy": ["kubernetes.namespace.name"], "metrics": [{"metric": "cpu.requests", "granularity": 3600000, "aggregation": "SUM"}], "timeFrame": {"windowSize": 7200000}, "tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}, "pagination": {"retrievalSize": 20}, "order": {"by": "label", "direction": "ASC"}}}
    resource_type="resources", operation="get_snapshot", params={"snapshot_id": "abc123xyz"}
    resource_type="resources", operation="get_snapshots", params={"plugin": "host", "size": 50}
    resource_type="resources", operation="get_snapshots", params={"query": "high cpu", "from_time": 1617994800000, "to_time": 1618081200000, "detailed": true}"""
    )
    async def manage_infrastructure(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Unified Instana infrastructure resource manager for entity monitoring and catalog operations."""

        try:
            logger.debug(f"Infrastructure Router: resource_type={resource_type}, operation={operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate resource_type
            valid_types = ["analyze", "catalog", "resources"]
            if resource_type not in valid_types:
                return {
                    "error": f"Invalid resource_type '{resource_type}'. Valid types: {', '.join(valid_types)}",
                    "valid_types": valid_types
                }

            # Route to the appropriate resource handler
            if resource_type == "analyze":
                return await self._handle_analyze(operation, params, ctx)
            elif resource_type == "catalog":
                return await self._handle_catalog(operation, params, ctx)
            elif resource_type == "resources":
                return await self._handle_resources(operation, params, ctx)
            else:
                return {
                    "error": f"Unsupported resource_type: {resource_type}",
                    "supported_types": valid_types
                }

        except Exception as e:
            logger.error(
                f"Error in infrastructure smart router: {e} | "
                f"resource_type={resource_type}, operation={operation}, params={params}",
                exc_info=True
            )
            return {
                "error": f"Smart router error: {e!s}",
                "resource_type": resource_type,
                "operation": operation
            }

    async def _handle_analyze(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle infrastructure analyze operations."""

        # Validate operation
        if operation not in ANALYZE_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for analyze",
                "valid_operations": ANALYZE_VALID_OPERATIONS
            }

        # Extract payload
        payload = params.get(PARAM_PAYLOAD)

        if not payload:
            return {
                "error": "Missing required parameter 'payload' for analyze operations",
                "required_format": {
                    "payload": {
                        "type": "entity_type_from_get_plugins",
                        "metrics": [{"metric": "metric_name", "granularity": 3600000, "aggregation": "MEAN"}],
                        "timeFrame": {"windowSize": 3600000}
                    }
                }
            }

        # Auto-detect the correct operation based on payload content
        # If groupBy is present, use get_entity_groups, otherwise use get_entities
        has_group_by = bool(payload.get("groupBy"))
        actual_operation = "get_entity_groups" if has_group_by else "get_entities"
        
        # Warn if user specified wrong operation
        if operation != actual_operation:
            logger.warning(
                f"Operation mismatch: user specified '{operation}' but payload "
                f"{'contains' if has_group_by else 'does not contain'} groupBy. "
                f"Auto-routing to '{actual_operation}'"
            )

        logger.debug(
            f"Routing to Infrastructure Analyze | "
            f"operation={actual_operation}, payload_type={payload.get('type')}, "
            f"has_groupBy={has_group_by}"
        )

        # Route to the correct operation based on payload content
        if actual_operation == "get_entity_groups":
            result = await self.infrastructure_analyze_client.get_aggregated_entity_groups(
                payload=payload,
                ctx=ctx
            )
        else:
            result = await self.infrastructure_analyze_client.get_entities(
                payload=payload,
                ctx=ctx
            )

        # Return structured response
        return {
            "resource_type": "analyze",
            "operation": actual_operation,
            "results": result
        }

    async def _handle_catalog(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle infrastructure catalog operations."""

        # Validate operation
        if operation not in CATALOG_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for catalog",
                "valid_operations": CATALOG_VALID_OPERATIONS
            }

        # Route to specific operation
        if operation == "get_plugins":
            logger.debug("Routing to Infrastructure Catalog Plugins")
            result = await self.infrastructure_catalog_client.get_infrastructure_catalog_plugins(ctx=ctx)

        elif operation == "get_metrics":
            plugin = params.get(PARAM_PLUGIN)
            filter_type = params.get(PARAM_FILTER)
            
            if not plugin:
                return {
                    "error": "Missing required parameter 'plugin' for get_metrics operation",
                    "hint": HINT_GET_PLUGINS_FIRST
                }
            
            logger.debug(f"Routing to Infrastructure Catalog Metrics | plugin={plugin}, filter={filter_type}")
            result = await self.infrastructure_catalog_client.get_infrastructure_catalog_metrics(
                plugin=plugin,
                filter=filter_type,
                ctx=ctx
            )

        elif operation == "get_tag_catalog":
            plugin = params.get(PARAM_PLUGIN)
            
            if not plugin:
                return {
                    "error": "Missing required parameter 'plugin' for get_tag_catalog operation",
                    "hint": HINT_GET_PLUGINS_FIRST
                }
            
            logger.debug(f"Routing to Infrastructure Tag Catalog | plugin={plugin}")
            result = await self.infrastructure_catalog_client.get_tag_catalog(
                plugin=plugin,
                ctx=ctx
            )

        elif operation == "get_plugin_schema":
            plugin = params.get(PARAM_PLUGIN)
            filter_type = params.get(PARAM_FILTER)
            
            if not plugin:
                return {
                    "error": "Missing required parameter 'plugin' for get_plugin_schema operation",
                    "hint": HINT_GET_PLUGINS_FIRST
                }
            
            logger.debug(f"Routing to Infrastructure Plugin Schema | plugin={plugin}, filter={filter_type}")
            result = await self.infrastructure_catalog_client.get_plugin_schema(
                plugin=plugin,
                filter=filter_type,
                ctx=ctx
            )

        # Return structured response
        return {
            "resource_type": "catalog",
            "operation": operation,
            "results": result
        }

    async def _handle_resources(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle infrastructure resources operations."""

        # Validate operation
        if operation not in RESOURCES_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for resources",
                "valid_operations": RESOURCES_VALID_OPERATIONS
            }

        # Route to specific operation
        if operation == "get_snapshot":
            snapshot_id = params.get(PARAM_SNAPSHOT_ID)
            to_time = params.get(PARAM_TO_TIME)
            window_size = params.get(PARAM_WINDOW_SIZE)
            
            if not snapshot_id:
                return {
                    "error": "Missing required parameter 'snapshot_id' for get_snapshot operation",
                    "hint": "Provide the snapshot ID to retrieve its details"
                }
            
            logger.debug(f"Routing to Infrastructure Get Snapshot | snapshot_id={snapshot_id}")
            result = await self.infrastructure_resources_client.get_snapshot(
                snapshot_id=snapshot_id,
                to_time=to_time,
                window_size=window_size,
                ctx=ctx
            )

        elif operation == "get_snapshots":
            query = params.get(PARAM_QUERY)
            from_time = params.get(PARAM_FROM_TIME)
            to_time = params.get(PARAM_TO_TIME)
            size = params.get(PARAM_SIZE, 100)
            plugin = params.get(PARAM_PLUGIN)
            offline = params.get(PARAM_OFFLINE, False)
            detailed = params.get(PARAM_DETAILED, False)
            
            logger.debug(f"Routing to Infrastructure Get Snapshots | query={query}, plugin={plugin}, size={size}")
            result = await self.infrastructure_resources_client.get_snapshots(
                query=query,
                from_time=from_time,
                to_time=to_time,
                size=size,
                plugin=plugin,
                offline=offline,
                detailed=detailed,
                ctx=ctx
            )

        # Return structured response
        return {
            "resource_type": "resources",
            "operation": operation,
            "results": result
        }
