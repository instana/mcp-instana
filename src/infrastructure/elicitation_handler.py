"""
Elicitation Handler Module

Handles ambiguity resolution when multiple options exist.
Asks user to choose when intent is unclear.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mcp.types import EmbeddedResource, TextContent, TextResourceContents

logger = logging.getLogger(__name__)


@dataclass
class ElicitationRequest:
    """
    Structured elicitation request to present to user.
    """
    type: str  # "choice", "clarification", "missing_parameter"
    message: str
    options: List[Dict[str, str]]
    context: Dict[str, Any]


class ElicitationHandler:
    """
    Handles ambiguity resolution via elicitation.

    Responsibilities:
    1. Detect when intent is ambiguous
    2. Create user-friendly choice requests
    3. Preserve context for follow-up
    """

    def check_ambiguity(self,normalized_intent,registry,resolved_metrics: Optional[List[str]] = None) -> Optional[ElicitationRequest]:
        """
        Check if intent is ambiguous and needs elicitation.

        Args:
            normalized_intent: NormalizedIntent object
            registry: EntityCapabilityRegistry instance
            resolved_metrics: List of resolved metric names (if any)

        Returns:
            ElicitationRequest if ambiguous, None otherwise
        """

        #Check 1: Unknown entity
        if normalized_intent.entity_class == "unknown":
            return self._create_unknown_entity_elicitation(normalized_intent)

        #Check 2: Unknown metric
        if normalized_intent.metric_category == "unknown":
            return self._create_unknown_metric_elicitation(normalized_intent, registry)

        #Check 3: Multiple possible metric matches
        if resolved_metrics and len(resolved_metrics) > 1:
            return self._create_multiple_metrics_elicitation(normalized_intent, resolved_metrics)

        #Check 4: No metric found
        if resolved_metrics is not None and len(resolved_metrics) == 0:
            return self._create_no_metric_elicitation(normalized_intent, registry)

        #No ambiguity detected
        return None

    def _create_unknown_entity_elicitation(self,normalized_intent) -> ElicitationRequest:
        """
        Create ElicitationRequest for unknown entity type.
        """
        return ElicitationRequest(
            type="clarification",
            message=f"I don't recognize the entity '{normalized_intent.entity_class}'. "
             f"Please specify one of the supported entity types:",
             options=[
                {"label": "Kubernetes Pod", "value": "kubernetes pod"},
                {"label": "Kubernetes Deployment", "value": "kubernetes deployment"},
                {"label": "Docker Containers", "value": "docker container"},
                {"label": "JVM Applications", "value": "jvm application"},
                {"label": "DB2 Database", "value": "db2 database"},
                {"label": "IBM MQ Queues", "value": "ibm mq queues"},
                {"label": "GenAI/LLM", "value": "genai llm"},
             ],
             context={"normalized_intent": normalized_intent}
        )

    def _create_unknown_metric_elicitation(
        self,
        normalized_intent,
        registry
    ) -> ElicitationRequest:
        """
        Create elicitation for unknown metric.
        """
        # Try to get entity capability to show available metrics
        capability = registry.resolve(normalized_intent.entity_class, normalized_intent.entity_kind)

        if capability:
            #Show some common metrics for this entity
            common_metrics = capability.metrics[:10] #Show first 10 metrics
            options = [{"label": metric, "value": metric} for metric in common_metrics]

            return ElicitationRequest(
                type="choice",
                message=f"I don't recognize the metric '{normalized_intent.metric_category}'. "
                 f"Here are some available metrics for {capability.entity_type}:",
                 options=options,
                 context={
                    "normalized_intent": normalized_intent,
                    "entity_type": capability.entity_type
                 }
            )
        else:
            return ElicitationRequest(
                type="clarification",
                message=f"I don't recognize the metric '{normalized_intent.metric_category}'. "
                f"Please provide a valid metric name.",
                options=[],
                context={"normalized_intent": normalized_intent}
            )

    def _create_multiple_metrics_elicitation(self, normalized_intent, resolved_metrics: List[str]) -> ElicitationRequest:
        """
        Create elicitation for multiple metrics match.
        """
        options = [{"label": metric, "value": metric} for metric in resolved_metrics]

        return ElicitationRequest(
            type="choice",
            message=f"Multiple metrics match '{normalized_intent.metric_category}'. "
            f"Please select the correct one:",
            options=options,
            context={
                "normalized_intent": normalized_intent,
                "resolved_metrics": resolved_metrics
            }
        )

    def _create_no_metric_elicitation(
        self,
        normalized_intent,
        registry
    ) -> ElicitationRequest:
        """
        Create elicitation when no metrics found.
        """
        capability = registry.resolve(
            normalized_intent.entity_class,
            normalized_intent.entity_kind
        )

        if capability:
            # Show all available metrics
            options = [
                {"label": metric, "value": metric}
                for metric in capability.metrics[:20]  # First 20
            ]

            return ElicitationRequest(
                type="choice",
                message=f"No metrics found matching '{normalized_intent.metric_category}' "
                       f"for {capability.entity_type}. Available metrics:",
                options=options,
                context={
                    "normalized_intent": normalized_intent,
                    "entity_type": capability.entity_type
                }
            )

        return ElicitationRequest(
            type="clarification",
            message=f"Could not find metrics for '{normalized_intent.metric_category}'.",
            options=[],
            context={"normalized_intent": normalized_intent}
        )

    def create_schema_elicitation(self, entity_type: str, schema: dict, intent: str) -> list:
        """
        Create machine-facing elicitation with full schema.

        Returns MCP-compliant list of content blocks for LLM.

        Args:
            entity_type: Entity type (e.g., "jvmRuntimePlatform")
            schema: Complete schema dict from entity_registry
            intent: User's original query

        Returns:
            List of MCP content blocks: [TextContent, EmbeddedResource]
        """
        # Extract schema info for instruction text
        metrics = schema.get("parameters", {}).get("metrics", {}).get("metric", [])
        tag_filters_params = schema.get("parameters", {}).get("tagFilterElements", {})
        tag_filters = tag_filters_params.get("enum", []) if isinstance(tag_filters_params, dict) else []
        aggregations = schema.get("parameters", {}).get("metrics", {}).get("aggregation", {}).get("enum", [])

        # Create instruction text
        instruction_text = f"""Based on your query: "{intent}"
I'm providing the complete schema for {entity_type}.

**Schema Summary:**
    - {len(metrics)} available metrics
    - {len(tag_filters)} available tag filters
    - Aggregations: {', '.join(aggregations) if aggregations else 'N/A'}

**CRITICAL RULES - YOU MUST FOLLOW THESE:**
    1. ⚠️ ONLY use names that EXACTLY match the schema below - NO assumptions, NO variations, NO constructions
    2. ⚠️ If user says "label.node name", search the schema for filters containing BOTH "label" AND "node"
    3. ⚠️ NEVER infer or construct filter/metric names - copy them EXACTLY from the schema
    4. ⚠️ If you cannot find an exact match in the schema, ask the user for clarification
    5. ⚠️ The schema is your ONLY source of truth - do not use external knowledge
    6. ⚠️ **NEVER add "groupBy" unless user EXPLICITLY uses grouping keywords** (see examples below)

**EXAMPLE - CORRECT BEHAVIOR:**
User query: "pods with label.node name = worker3"
Your process:
  Step 1: Search schema filters for "label" AND "node"
  Step 2: Find exact match: "kubernetes.pod.label.node_name"
  Step 3: Use EXACTLY: {{"name": "kubernetes.pod.label.node_name", "value": "worker3"}}

**EXAMPLE - INCORRECT BEHAVIOR (DO NOT DO THIS):**
User query: "pods with label.node name = worker3"
❌ WRONG: Assume it means "kubernetes.node.name" (this is a node property, not a pod label)
❌ WRONG: Construct "kubernetes.pod.label.node" (incomplete name)
❌ WRONG: Use "node.name" (too short, not in schema)
✅ CORRECT: Use "kubernetes.pod.label.node_name" (exact match from schema)

**GROUPBY RULES - WHEN TO USE AND WHEN NOT TO USE:**

⚠️ **DO NOT use "groupBy" unless user EXPLICITLY asks for it with these keywords:**
   - "group by", "grouped by", "per", "for each", "by host", "by namespace", "break down by"

**CORRECT Examples (NO groupBy):**
   ✅ "Show me CPU usage for hosts" → NO groupBy (aggregated result across all hosts)
   ✅ "What is memory usage of pods in production?" → NO groupBy (aggregated result)
   ✅ "Get free memory of host with CPU model Intel Xeon" → NO groupBy (aggregated result)
   ✅ "List hosts with high disk usage" → NO groupBy (aggregated result)

**CORRECT Examples (WITH groupBy):**
   ✅ "Show me CPU usage grouped by host" → groupBy: ["host.name"]
   ✅ "What is memory usage per namespace?" → groupBy: ["kubernetes.namespace.name"]
   ✅ "Get CPU for each pod" → groupBy: ["kubernetes.pod.name"]
   ✅ "Break down memory by host and cluster" → groupBy: ["host.name", "kubernetes.cluster.name"]

**INCORRECT Examples (DO NOT DO THIS):**
   ❌ "Show me CPU usage for hosts" → groupBy: ["host.name"] ← WRONG! No grouping keyword used
   ❌ "Get memory of pods" → groupBy: ["kubernetes.pod.name"] ← WRONG! No "per" or "each" keyword
   ❌ "List hosts with high CPU" → groupBy: ["host.name"] ← WRONG! User wants aggregated list, not breakdown

**Instructions:**
    1. Review the embedded schema resource below carefully
    2. Select one or more exact metric names from the schema (up to 10 metrics)
    3. Select the aggregation type based on the user's intent:
       - "mean" for average/typical/normal values
       - "sum" for total/combined/count/cumulative values
       - "max" for highest/maximum/peak/largest values
       - "min" for lowest/minimum/smallest values
    4. For filters: Search the schema for exact matches to user's terms
       - If user says "label.X", look for filters containing "label" and "X"
       - If user says "node name", look for filters containing "node" and "name"
       - Copy the COMPLETE filter name from schema (e.g., "kubernetes.pod.label.node_name")
    5. **ONLY include "groupBy" if user EXPLICITLY uses grouping keywords:**
       - Keywords: "group by", "grouped by", "per", "for each", "by host", "by namespace", "break down by"
       - If NO grouping keyword → DO NOT include "groupBy" in your response
       - If grouping keyword present → select groupBy tags from schema (max 5)
    6. If user specifies time range, include timeRange in one of two formats:
       - Relative: "1h", "30m", "2h", "1d" (last N hours/minutes/days from now)
       - Absolute: {{"from": "YYYY-MM-DD HH:MM:SS", "to": "YYYY-MM-DD HH:MM:SS"}} (specific time window)
       - IMPORTANT: For absolute times, use date STRING format, NOT Unix timestamps
       - The server will handle date parsing - you just provide readable dates
    7. If user asks to sort/order results (e.g., "highest first", "sorted by CPU"), include order
       - CRITICAL: "order.by" must be in format "metricName.AGGREGATION" (e.g., "queueDepth.MEAN", "cpu.used.MAX")
       - NOT just the metric name alone

**Return your selections in this exact JSON format:**
    {{
        "selectedMetrics": ["exact.metric.name.1", "exact.metric.name.2"],
        "aggregation": "mean|max|min|sum",
        "filters": [
        {{"name": "exact.tag.filter.name.from.schema", "value": "your_value"}}
        ],
        "groupBy": ["exact.tag.name.1", "exact.tag.name.2"],
        "timeRange": "1h|30m|2h|1d" OR {{"from": "2026-01-24 12:25:00", "to": "2026-01-24 14:40:00"}},
        "order": {{"by": "metric.name.AGGREGATION", "direction": "ASC|DESC"}},
        "pagination": {{"page": 1, "pageSize": 20}} OR {{"offset": 0, "limit": 20}}
    }}

**IMPORTANT REMINDERS:**
- Use EXACT names from the schema - copy/paste them, do not type from memory
- "selectedMetrics" must be an array, even for a single metric: ["metric.name"]
- You can select multiple metrics if the user asks for them (e.g., "runnable and waiting threads")
- **"groupBy" - CRITICAL RULE:**
  - ⚠️ DO NOT include "groupBy" unless user uses explicit grouping keywords
  - ⚠️ Grouping keywords: "group by", "grouped by", "per", "for each", "by host", "by namespace", "break down by"
  - ⚠️ If user just asks "show me X" or "get X" or "list X" → NO groupBy (return aggregated result)
  - ⚠️ If user asks "show me X per Y" or "X grouped by Y" → YES groupBy: ["Y"]
  - "groupBy" uses tag filter names from the schema (max 5 tags)
- "timeRange" is optional - supports two formats:
  - Relative (default): "1h", "30m", "2h", "1d" for last N hours/minutes/days from now
  - Absolute: {{"from": "YYYY-MM-DD HH:MM:SS", "to": "YYYY-MM-DD HH:MM:SS"}} for specific time window
  - ⚠️ CRITICAL: For absolute times, use DATE STRINGS, NOT Unix timestamps
  - ⚠️ DO NOT calculate timestamps yourself - the server will parse the date strings
  - Example relative: "2h" means last 2 hours from now
  - Example absolute: {{"from": "2026-01-24 12:25:00", "to": "2026-01-24 14:40:00"}}
  - Supported date formats: "YYYY-MM-DD HH:MM:SS", "DD-Month-YYYY HH:MM" (e.g., "24-January-2026 12:25")
- "order" is optional - only include if user asks to sort results
  - "by" MUST be in format "metricName.AGGREGATION" (e.g., "queueDepth.MEAN", "cpu.requests.MAX")
  - "direction" is ASC or DESC
  - Example: {{"by": "queueDepth.MEAN", "direction": "DESC"}} for "order by average queue depth descending"
- "pagination" is optional - controls how many results to return
  - Format 1 (page-based): {{"page": 1, "pageSize": 20}} - page 1 with 20 items per page
  - Format 2 (offset-based): {{"offset": 0, "limit": 20}} - skip 0 items, return 20 items
  - Format 3 (size only): {{"pageSize": 20}} - return first 20 items
  - Default: 50 items if not specified
  - Example: {{"page": 2, "pageSize": 10}} for "show me page 2 with 10 items per page"
- When in doubt about a filter name, search the schema carefully or ask for clarification
"""

        # Create TextContent(Pydantic Model)
        text_content = TextContent(type="text", text=instruction_text)

        # Create EmbeddedResource (Pydantic Model)
        schema_resource = EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri=f"schema://{entity_type}",
                mimeType="application/json",
                text=json.dumps(schema, indent=2)
            )
        )

        logger.info(f"Created schema elicitation for {entity_type}: {len(metrics)} metrics, {len(tag_filters)} tags")

        #Return list of the MCP content blocks
        return [text_content, schema_resource]
