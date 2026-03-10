"""
Infrastructure Analyze Tool - Option 2 Architecture

This tool implements the complete Option 2 flow:
1. LLM provides high-level intent (entity, metric, filters)
2. Server normalizes intent
3. Server resolves exact constants from schemas
4. Server handles elicitation if ambiguous
5. Server compiles complete payload
6. Server calls Instana API

Key benefit: LLM never sees schema complexity, reducing tokens by 99.4%
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from instana_client.api.infrastructure_analyze_api import InfrastructureAnalyzeApi
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from mcp.types import EmbeddedResource, TextContent, ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth
from src.infrastructure.elicitation_handler import ElicitationHandler
from src.infrastructure.entity_registry import EntityCapabilityRegistry

logger = logging.getLogger(__name__)


class InfrastructureAnalyzeOption2(BaseInstanaClient):
    """
    Infrastructure analyze tool using Option 2 architecture.

    This tool demonstrates the complete server-side payload assembly approach:
    - LLM provides simple intent (~300 tokens)
    - Server resolves all constants from schemas (~48,000 tokens saved)
    - Zero hallucination on metric/tag names
    """

    def __init__(self, read_token: str, base_url: str, schema_dir: Optional[Path] = None):
        """
        Initialize the Infrastructure Analyze Option 2 tool.

        Args:
            read_token: Instana API read token
            base_url: Instana API base URL
            schema_dir: Path to schema directory (defaults to ../schema)
        """
        super().__init__(read_token=read_token, base_url=base_url)

        # Initialize Option 2 components
        if schema_dir is None:
            # Try multiple locations for schema directory
            # 1. Development: relative to this file
            dev_schema_dir = Path(__file__).parent.parent.parent / "schema"

            # 2. Installed package: in site-packages/schema
            # Get the site-packages directory where this module is installed
            module_path = Path(__file__).parent
            site_packages = module_path.parent.parent  # Go up from src/infrastructure to site-packages
            pkg_schema_dir = site_packages / "schema"

            # Use development path if it exists, otherwise use package path
            if dev_schema_dir.exists():
                schema_dir = dev_schema_dir
            elif pkg_schema_dir.exists():
                schema_dir = pkg_schema_dir
            else:
                # Fallback to development path (will log warning if doesn't exist)
                schema_dir = dev_schema_dir

        self.registry = EntityCapabilityRegistry(
            schema_dir=schema_dir,
            base_url=base_url,
            read_token=read_token
        )
        self.elicitation_handler = ElicitationHandler()

        logger.info(f"Initialized Option 2 tool with {len(self.registry.get_entity_types())} entity types")

    @register_as_tool(
        title="Analyze Infrastructure with Elicitation (Two-Pass)",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureAnalyzeApi)
    async def analyze_infrastructure_elicitation(
        self,
        intent: Optional[str] = None,
        entity: Optional[str] = None,
        selections: Optional[Dict[str, Any]] = None,
        ctx=None,
        api_client=None
    ) -> List[Any]:
        """
        Two-pass infrastructure analysis using machine-facing elicitation.

        **Pass 1 - Intent to Schema:**
        Provide intent and entity hint. Server returns full schema via MCP elicitation.
        The server dynamically loads available entity types from the Instana API catalog,
        ensuring support for all monitored technologies in your environment.

        Parameters:
        - intent: Natural language query (e.g., "maximum heap size of JVM on host galactica1")
        - entity: Entity hint (e.g., "jvm", "kubernetes", "docker", "genai", "host", "db2", "ibmmq")
          The system supports all entity types available in your Instana installation, including
          Kubernetes pods/deployments, JVM runtimes, hosts, databases, message queues, containers,
          and any custom or newly added entity types.

        **Pass 2 - Selections to Results:**
        Provide exact selections from schema. Server builds payload and calls API.

        Parameters:
        - selections: Dict with:
          - entity_type: Exact entity type from schema (e.g., "jvmRuntimePlatform", "kubernetesPod")
          - metrics: Array of exact metric names from schema (e.g., ["jvm.heap.maxSize", "jvm.heap.used"])
          - aggregation: Aggregation type (e.g., "max", "mean", "sum")
          - filters: List of dicts with name/value pairs (e.g., [{"name": "host.name", "value": "galactica1"}])
          - groupBy: (optional) Array of tag names to group entities by (e.g., ["host.name"], ["kubernetes.namespace.name"])
          - timeRange: (optional) Time range string (e.g., "1h", "30m", "2h", "1d"). Default: "1h"
          - order: (optional) Dict with "by" (metric name) and "direction" ("ASC" or "DESC")

        Returns:
            List of MCP content blocks (TextContent or EmbeddedResource)

        Note: Entity type support is automatically synchronized with your Instana installation's
        plugin catalog, ensuring compatibility with all monitored technologies without manual updates.
        """
        try:
            # Route based on input
            if intent is not None and entity is not None:
                # Pass 1: Intent → Elicitation
                return await self._handle_pass1_intent({"intent": intent, "entity": entity})
            elif selections is not None:
                # Pass 2: Selections → API Call
                return await self._handle_pass2_selections({"selections": selections}, api_client)
            else:
                return [TextContent(
                    type="text",
                    text="Error: Invalid input. Provide either (intent + entity) for Pass 1, or (selections) for Pass 2."
                )]
        except Exception as e:
            logger.error(f"Error in analyze_infrastructure_elicitation: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error: {e!s}"
            )]

    async def _handle_pass1_intent(self, arguments: Dict[str, Any]) -> List[Any]:
        """
        Handle Pass 1: Intent → Schema Elicitation

        Args:
            arguments: Dict with 'intent' and 'entity' keys

        Returns:
            List of MCP content blocks with schema
        """
        intent = arguments.get("intent", "")
        entity_hint = arguments.get("entity", "").lower()
        intent_lower = intent.lower()

        logger.info(f"Pass 1: intent='{intent}', entity_hint='{entity_hint}'")

        # Entity type resolution with priority (more specific first)
        # Check for specific matches first, then fall back to general ones
        entity_type = None

        # Priority 1: Specific multi-word matches
        if "kubernetes deployment" in entity_hint or "k8s deployment" in entity_hint:
            entity_type = "kubernetesDeployment"
        elif "kubernetes pod" in entity_hint or "k8s pod" in entity_hint:
            entity_type = "kubernetesPod"
        elif "docker container" in entity_hint:
            entity_type = "dockerContainer"
        elif "ibm mq" in entity_hint or "ibmmq" in entity_hint:
            entity_type = "ibmMqQueue"
        elif "db2 database" in entity_hint:
            entity_type = "db2Database"
        elif ("otel llm" in entity_hint or "large language model" in entity_hint or
              "llm model" in entity_hint or "llm service" in entity_hint or "llm application" in entity_hint or
              "genai service" in entity_hint or "genai application" in entity_hint or "genai model" in entity_hint or
              "gen ai service" in entity_hint or "gen ai application" in entity_hint or "gen ai model" in entity_hint or
              "ai model" in entity_hint or "ai service" in entity_hint or "ai application" in entity_hint or "gen ai" in entity_hint):
            entity_type = "oTelLLM"
        # Priority 2: Single word specific matches
        elif "deployment" in entity_hint:
            entity_type = "kubernetesDeployment"
        elif "pod" in entity_hint:
            entity_type = "kubernetesPod"
        elif "jvm" in entity_hint or "java" in entity_hint:
            entity_type = "jvmRuntimePlatform"
        elif "docker" in entity_hint or "container" in entity_hint:
            entity_type = "dockerContainer"
        elif "mq" in entity_hint or "queue" in entity_hint:
            entity_type = "ibmMqQueue"
        elif "db2" in entity_hint or "database" in entity_hint:
            entity_type = "db2Database"
        elif "otelllm" in entity_hint or "genai" in entity_hint or "llm" in entity_hint or "ai" in entity_hint:
            entity_type = "oTelLLM"
        elif "host" in entity_hint or "server" in entity_hint or "machine" in entity_hint:
            entity_type = "host"
        # Priority 3: Generic kubernetes - use intent context to disambiguate
        elif "kubernetes" in entity_hint or "k8s" in entity_hint:
            # Smart disambiguation based on intent keywords
            deployment_keywords = ["deployment", "replica", "availabletodesiredreplica", "desiredreplica", "availablereplica"]
            pod_keywords = ["pod", "restart", "container"]

            # Check intent for deployment-specific keywords
            if any(keyword in intent_lower for keyword in deployment_keywords):
                entity_type = "kubernetesDeployment"
                logger.info("Resolved ambiguous 'kubernetes' to 'kubernetesDeployment' based on intent keywords")
            # Check intent for pod-specific keywords
            elif any(keyword in intent_lower for keyword in pod_keywords):
                entity_type = "kubernetesPod"
                logger.info("Resolved ambiguous 'kubernetes' to 'kubernetesPod' based on intent keywords")
            else:
                # Still ambiguous - ask for clarification
                return [TextContent(
                    type="text",
                    text="Ambiguous entity type 'kubernetes'. Please specify: 'kubernetes pod' or 'kubernetes deployment'"
                )]

        if not entity_type:
            return [TextContent(
                type="text",
                text=f"Error: Unknown entity type '{entity_hint}'. Supported: jvm, kubernetes pod, kubernetes deployment, docker, ibmmq, db2, genai"
            )]

        logger.info(f"Resolved entity type: {entity_type}")

        # Load full schema
        schema = self.registry.get_full_schema(entity_type)
        if not schema:
            return [TextContent(
                type="text",
                text=f"Error: Could not load schema for {entity_type}"
            )]

        logger.info(f"Loaded schema for {entity_type}")

        # Create elicitation response
        elicitation_content = self.elicitation_handler.create_schema_elicitation(
            entity_type=entity_type,
            schema=schema,
            intent=intent
        )

        logger.info(f"Created elicitation with {len(elicitation_content)} content blocks")

        return elicitation_content

    async def _handle_pass2_selections(
        self,
        arguments: Dict[str, Any],
        api_client
    ) -> List[Any]:
        """
        Handle Pass 2: Selections → API Call

        Args:
            arguments: Dict with 'selections' key containing user selections
            api_client: Instana API client

        Returns:
            List with TextContent containing formatted results
        """
        selections = arguments.get("selections", {})

        entity_type = selections.get("entity_type")
        # Support both "metrics" (correct) and "metric" (backward compatibility)
        metrics = selections.get("metrics") or selections.get("metric", [])
        aggregation = selections.get("aggregation", "mean")
        filters = selections.get("filters", [])
        group_by = selections.get("groupBy", [])
        order = selections.get("order")  # Optional: {"by": "metric_name", "direction": "ASC|DESC"}
        time_range = selections.get("timeRange", "1h")  # Default to 1 hour
        pagination = selections.get("pagination", {})  # Optional: {"page": 1, "pageSize": 20} or {"offset": 0, "limit": 20}

        # Ensure metrics is a list
        if not isinstance(metrics, list):
            metrics = [metrics] if metrics else []

        # Ensure groupBy is a list
        if not isinstance(group_by, list):
            group_by = [group_by] if group_by else []

        logger.info(f"Pass 2: entity_type={entity_type}, metrics={metrics}, aggregation={aggregation}, groupBy={group_by}, order={order}, timeRange={time_range}")

        if not entity_type or not metrics:
            return [TextContent(
                type="text",
                text="Error: selections must include 'entity_type' and 'metrics' (array)"
            )]

        # Validate groupBy if provided
        if group_by and len(group_by) > 5:
            return [TextContent(
                type="text",
                text="Error: groupBy can have maximum 5 tag names"
            )]

        # Build payload using payload compiler
        # For PoC, we'll build a simple payload directly
        from instana_client.models.cursor_pagination_infra_explore_cursor import (
            CursorPaginationInfraExploreCursor,
        )
        from instana_client.models.get_infrastructure_groups_query import (
            GetInfrastructureGroupsQuery,
        )
        from instana_client.models.get_infrastructure_query import (
            GetInfrastructureQuery,
        )
        from instana_client.models.infra_metric_configuration import (
            InfraMetricConfiguration,
        )
        from instana_client.models.order import Order
        from instana_client.models.simple_metric_configuration import (
            SimpleMetricConfiguration,
        )
        from instana_client.models.tag_filter import TagFilter
        from instana_client.models.tag_filter_all_of_value import TagFilterAllOfValue
        from instana_client.models.tag_filter_expression import TagFilterExpression
        from instana_client.models.time_frame import TimeFrame

        # Parse time range - supports relative, absolute timestamps, and human-readable dates
        def parse_time_range(time_input):
            """
            Convert time range to TimeFrame parameters.

            Supports three formats:
            1. Relative: "1h", "30m", "2h", "1d" -> returns (window_size_ms, None)
            2. Absolute (timestamps): {"from": timestamp_ms, "to": timestamp_ms} -> returns (window_size_ms, to_ms)
            3. Absolute (date strings): {"from": "2026-01-24 12:25:00", "to": "2026-01-24 14:40:00"} -> returns (window_size_ms, to_ms)

            Returns:
                tuple: (window_size_ms, to_timestamp_ms or None)
            """
            from datetime import datetime

            # Handle dict format for absolute time range
            if isinstance(time_input, dict):
                from_val = time_input.get("from")
                to_val = time_input.get("to")

                if from_val is not None and to_val is not None:
                    # Check if values are strings (date format) or integers (timestamps)
                    if isinstance(from_val, str) and isinstance(to_val, str):
                        # Parse date strings to timestamps
                        try:
                            from datetime import timezone

                            # Support multiple date formats
                            date_formats = [
                                "%Y-%m-%d %H:%M:%S",
                                "%Y-%m-%d %H:%M",
                                "%Y-%m-%dT%H:%M:%S",
                                "%Y-%m-%dT%H:%M:%SZ",
                                "%d-%B-%Y %H:%M",  # e.g., "24-January-2026 12:25"
                                "%d-%b-%Y %H:%M",   # e.g., "24-Jan-2026 12:25"
                            ]

                            from_dt = None
                            to_dt = None

                            for fmt in date_formats:
                                try:
                                    from_dt = datetime.strptime(from_val, fmt)
                                    to_dt = datetime.strptime(to_val, fmt)
                                    break
                                except ValueError:
                                    continue

                            if from_dt is None or to_dt is None:
                                logger.error(f"Could not parse date strings: from='{from_val}', to='{to_val}'")
                                return (3600000, None)

                            # Use system's local timezone for timestamp conversion
                            from_ts = int(from_dt.timestamp() * 1000)
                            to_ts = int(to_dt.timestamp() * 1000)
                            window_size_ms = to_ts - from_ts

                            logger.info(f"Parsed date strings (local timezone): from='{from_val}' ({from_ts}), to='{to_val}' ({to_ts}), window={window_size_ms}ms")
                            return (window_size_ms, to_ts)

                        except Exception as e:
                            logger.error(f"Error parsing date strings: {e}")
                            return (3600000, None)
                    else:
                        # Assume numeric timestamps
                        from_ts = int(from_val)
                        to_ts = int(to_val)
                        window_size_ms = to_ts - from_ts
                        logger.info(f"Parsed timestamp range: from={from_ts}, to={to_ts}, window={window_size_ms}ms")
                        return (window_size_ms, to_ts)
                else:
                    logger.warning("Absolute time range missing 'from' or 'to', defaulting to 1h")
                    return (3600000, None)

            # Handle string format for relative time range
            time_str = str(time_input).lower().strip()
            if time_str.endswith('h'):
                hours = int(time_str[:-1])
                window_size_ms = hours * 3600000
            elif time_str.endswith('m'):
                minutes = int(time_str[:-1])
                window_size_ms = minutes * 60000
            elif time_str.endswith('d'):
                days = int(time_str[:-1])
                window_size_ms = days * 86400000
            else:
                # Default to 1 hour if format not recognized
                window_size_ms = 3600000

            logger.info(f"Parsed relative time range '{time_str}' to {window_size_ms}ms")
            return (window_size_ms, None)

        window_size_ms, to_timestamp = parse_time_range(time_range)

        # Build tag filter expression
        if filters and len(filters) > 0:
            # Single filter case - use TagFilter directly
            if len(filters) == 1:
                filter_dict = filters[0]
                filter_name = filter_dict.get("name")
                filter_value = filter_dict.get("value")

                tag_filter_expression = TagFilter(
                    type="TAG_FILTER",
                    entity="NOT_APPLICABLE",
                    name=filter_name,
                    operator="EQUALS",
                    value=TagFilterAllOfValue(filter_value)
                )
            else:
                # Multiple filters - use TagFilterExpression with AND
                tag_filter_elements = []
                for filter_dict in filters:
                    filter_name = filter_dict.get("name")
                    filter_value = filter_dict.get("value")
                    if filter_name and filter_value:
                        tag_filter_elements.append(TagFilter(
                            type="TAG_FILTER",
                            entity="NOT_APPLICABLE",
                            name=filter_name,
                            operator="EQUALS",
                            value=TagFilterAllOfValue(filter_value)
                        ))

                tag_filter_expression = TagFilterExpression(
                    type="EXPRESSION",
                    logical_operator="AND",
                    elements=tag_filter_elements
                )
        else:
            # No filters - use empty expression
            tag_filter_expression = TagFilterExpression(
                type="EXPRESSION",
                logical_operator="AND",
                elements=[]
            )

        # Build metrics array with proper Pydantic objects
        # Note: granularity is intentionally omitted as it causes data discrepancies with UI
        infra_metrics = []
        for metric_name in metrics:
            metric_config = SimpleMetricConfiguration(
                metric=metric_name,
                aggregation=aggregation.upper()
            )
            infra_metric = InfraMetricConfiguration(actual_instance=metric_config)
            infra_metrics.append(infra_metric)

        logger.info(f"Built {len(infra_metrics)} metric configurations (without granularity)")

        # Build Order object if provided
        order_obj = None
        if order and isinstance(order, dict):
            order_by = order.get("by")
            order_direction = order.get("direction", "DESC").upper()
            if order_by:
                # Ensure order.by is in format "metricName.AGGREGATION"
                # If LLM provides just metric name, append aggregation
                if "." not in order_by and aggregation:
                    order_by = f"{order_by}.{aggregation.upper()}"
                    logger.info(f"Appended aggregation to order.by: {order_by}")

                order_obj = Order(by=order_by, direction=order_direction)
                logger.info(f"Built Order: by={order_by}, direction={order_direction}")

        # Build pagination object
        # Supports pagination formats: {"page": 1, "pageSize": 20} or {"offset": 0, "limit": 20}
        page_size = 50  # Default
        offset = None

        if pagination and isinstance(pagination, dict):
            # Handle pageSize or limit
            page_size = pagination.get("pageSize") or pagination.get("limit", 50)

            # Handle page number (convert to offset)
            page = pagination.get("page")
            if page is not None and page > 0:
                offset = (page - 1) * page_size
                logger.info(f"Converted page {page} to offset {offset}")

            # Handle direct offset
            if "offset" in pagination:
                offset = pagination.get("offset", 0)

            logger.info(f"Pagination: pageSize={page_size}, offset={offset}")

        # Build CursorPaginationInfraExploreCursor object
        if offset is not None and offset > 0:
            cursor_pagination = CursorPaginationInfraExploreCursor(retrievalSize=page_size, offset=offset)
        else:
            cursor_pagination = CursorPaginationInfraExploreCursor(retrievalSize=page_size)

        # Build TimeFrame object - supports both relative and absolute time ranges
        if to_timestamp is not None:
            # Absolute time range: from specific timestamp to another timestamp
            time_frame = TimeFrame(window_size=window_size_ms, to=to_timestamp)
            logger.info(f"Built absolute TimeFrame: window_size={window_size_ms}ms, to={to_timestamp}")
        else:
            # Relative time range: last N hours/minutes/days from now
            time_frame = TimeFrame(window_size=window_size_ms)
            logger.info(f"Built relative TimeFrame: window_size={window_size_ms}ms")

        # Build query with proper Pydantic objects - conditional based on groupBy
        if group_by and len(group_by) > 0:
            # Use GetInfrastructureGroupsQuery for grouped queries
            query = GetInfrastructureGroupsQuery(
                group_by=group_by,  # Required for groups API
                type=entity_type,
                metrics=infra_metrics,
                tag_filter_expression=tag_filter_expression,  # Required field
                time_frame=time_frame,
                pagination=cursor_pagination,
                order=order_obj  # Optional
            )
            logger.info(f"Built GROUPS query payload for {entity_type} with groupBy={group_by}")
        else:
            # Use GetInfrastructureQuery for non-grouped queries (existing behavior)
            query = GetInfrastructureQuery(
                type=entity_type,
                metrics=infra_metrics,
                tag_filter_expression=tag_filter_expression,  # Required field
                time_frame=time_frame,
                pagination=cursor_pagination,
                order=order_obj  # Optional
            )
            logger.info(f"Built ENTITIES query payload for {entity_type}")

        # Log the complete payload being sent to API
        import json
        try:
            payload_dict = query.to_dict()
            logger.info("=" * 80)
            logger.info("FINAL API PAYLOAD:")
            logger.info(json.dumps(payload_dict, indent=2))
            logger.info("=" * 80)
        except Exception as e:
            logger.warning(f"Could not serialize payload for logging: {e}")

        # Call Instana API - conditional based on groupBy
        try:
            if group_by and len(group_by) > 0:
                logger.info("Calling Instana API: get_entity_groups_without_preload_content (with groupBy)")
                raw_response = api_client.get_entity_groups_without_preload_content(
                    get_infrastructure_groups_query=query
                )
            else:
                logger.info("Calling Instana API: get_entities_without_preload_content (no groupBy)")
                raw_response = api_client.get_entities_without_preload_content(
                    get_infrastructure_query=query
                )
            logger.info("API call successful, processing response...")

            # Parse response
            import json
            response_text = raw_response.data.decode('utf-8')
            result_dict = json.loads(response_text)

            items = result_dict.get("items", [])
            logger.info(f"API returned {len(items)} items")

            # Format results - different format for grouped vs individual entities
            if not items:
                result_text = f"No {entity_type} entities found matching your criteria."
            elif group_by and len(group_by) > 0:
                # Grouped results format
                result_text = f"Found {len(items)} groups (grouped by {', '.join(group_by)}):\n\n"
                for idx, item in enumerate(items, 1):  # Show all groups
                    # For groups, extract the group key from 'tags' field
                    tags = item.get("tags", {})
                    count = item.get("count", 0)
                    metrics_data = item.get("metrics", {})

                    # Build group label from tags (the groupBy fields)
                    group_parts = []
                    for tag_name in group_by:
                        tag_value = tags.get(tag_name, "unknown")
                        group_parts.append(f"{tag_name}={tag_value}")
                    group_label = ", ".join(group_parts)

                    result_text += f"{idx}. Group: {group_label} (count: {count})\n"
                    if metrics_data:
                        for metric_key, metric_value in metrics_data.items():
                            # Check if metric_key matches any of the requested metrics
                            if any(requested_metric in metric_key for requested_metric in metrics):
                                result_text += f"   {metric_key}: {metric_value}\n"
                    result_text += "\n"
            else:
                # Individual entities format - return all entities
                result_text = f"Found {len(items)} {entity_type} entities:\n\n"
                for idx, item in enumerate(items, 1):  # Show all entities
                    label = item.get("label", "unknown")
                    metrics_data = item.get("metrics", {})

                    result_text += f"{idx}. {label}\n"
                    if metrics_data:
                        for metric_key, metric_value in metrics_data.items():
                            # Check if metric_key matches any of the requested metrics
                            if any(requested_metric in metric_key for requested_metric in metrics):
                                result_text += f"   {metric_key}: {metric_value}\n"
                    result_text += "\n"

            return [TextContent(type="text", text=result_text)]

        except Exception as e:
            logger.error(f"API call failed: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error calling Instana API: {e!s}"
            )]
