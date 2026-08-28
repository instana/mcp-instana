"""
Infrastructure Analyze MCP Prompts Module

This module provides infrastructure analyze-specific MCP prompts for Instana monitoring.
"""

from typing import Optional

from src.prompts import auto_register_prompt


class InfrastructureAnalyzePrompts:
    """Class containing prompts for infrastructure analysis in Instana."""

    @auto_register_prompt
    @staticmethod
    def infra_available_metrics(
        type: str,
        query: Optional[str] = None,
        var_from: Optional[int] = None,
        to: Optional[int] = None,
        windowSize: Optional[int] = None) -> str:
        """Get available infrastructure metrics for a given entity type"""
        return f"""
        Use the manage_infrastructure tool to get available metrics for an infrastructure entity type.
        - resource_type: "catalog"
        - operation: "get_plugin_schema"
        - Type: {type}
        - Query: {query if query is not None else 'None'}
        - From: {var_from if var_from is not None else 'None'}
        - To: {to if to is not None else 'None'}
        - Window size: {windowSize if windowSize is not None else 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def infra_get_entities(
        type: str,
        metrics: Optional[str] = None,
        windowSize: Optional[int] = None,
        to: Optional[int] = None) -> str:
        """Fetch infrastructure entities and their metrics"""
        return f"""
        Use the manage_infrastructure tool to fetch infrastructure entities and their metrics.
        - resource_type: "analyze"
        - operation: "get_entities"
        - Type: {type}
        - Metrics: {metrics if metrics is not None else 'None'}
        - Window size: {windowSize if windowSize is not None else 'None'}
        - To: {to if to is not None else 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def infra_available_plugins(
        offline: bool,
        query: Optional[str] = None,
        windowSize: Optional[int] = None,
        to: Optional[int] = None) -> str:
        """List available infrastructure monitoring plugins"""
        return f"""
        Use the manage_infrastructure tool to list available infrastructure monitoring plugins.
        - resource_type: "catalog"
        - operation: "get_plugins"
        - Query: {query if query is not None else 'None'}
        - Offline: {offline}
        - Window size: {windowSize if windowSize is not None else 'None'}
        - To: {to if to is not None else 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def llm_performance_and_token_queries() -> str:
        """Route LLM performance and token correlation queries to infrastructure only."""
        return """
        Use the manage_infrastructure tool for all LLM and GenAI performance and token usage queries.
         Do NOT use manage_applications tool.
        - resource_type: "analyze"
        - operation: "get_entities" or "get_entity_groups" depending on whether grouping is needed
        - type: "oTelLLM" (for LLM/GenAI entities)
        Covers service, .run.workflow, and GenAI App forms.
        Covers highest latency P95, latency > P95, duration thresholds, and token usage over a time range.
        Always call manage_infrastructure first with resource_type="catalog", operation="get_plugin_schema", plugin="oTelLLM"
        to discover valid metrics and tags before querying.
        """

    @auto_register_prompt
    @staticmethod
    def list_llm_genai_apps() -> str:
        """Route GenAI app listing queries to infrastructure only."""
        return """
        Use the manage_infrastructure tool to list or show GenAI apps.
        Do NOT use manage_applications tool.
        - resource_type: "resources"
        - operation: "get_snapshots"
        - plugin: "oTelLLM"
        """

    @auto_register_prompt
    @staticmethod
    def failed_llm_prompt_or_output() -> str:
        """Route failed LLM prompt or output queries to infrastructure only."""
        return """
        Use the manage_infrastructure tool to show the most recent failed prompt or output for an LLM or GenAI service.
        Do NOT use manage_applications tool.
        - resource_type: "analyze"
        - operation: "get_entities"
        - type: "oTelLLM"
        Filter by a relevant error or status metric/tag to identify failed calls.
        """

    @auto_register_prompt
    @staticmethod
    def total_llm_token_usage() -> str:
        """Route total LLM token usage queries to infrastructure only."""
        return """
        Use the manage_infrastructure tool to get total token usage for an LLM or GenAI service over a time range.
         Do NOT use manage_applications tool.
        - resource_type: "analyze"
        - operation: "get_entity_groups"
        - type: "oTelLLM"
        Use a token-related metric (e.g. "metrics.gauges.llm.usage.total_tokens") with aggregation "SUM".
        Always call manage_infrastructure first with resource_type="catalog", operation="get_plugin_schema", plugin="oTelLLM"
        to confirm valid metric names before querying.
        """

    @auto_register_prompt
    @staticmethod
    def llm_individual_trace_latency_and_tokens() -> str:
        """Route queries for individual LLM workflow run latency (above P95) and tokens per run to infrastructure only.

        Do NOT use manage_applications tool — this data is not available via call traces.

        1. resource_type="catalog", operation="get_plugin_schema", plugin="oTelLLM"
           to confirm valid metric names and tag names.

        2. resource_type="analyze", operation="get_entities":
           - type: "oTelLLM"
           - Filter by the agent label (e.g. "payment-agent") using tagFilterExpression on the "label" tag.
           - Use granularity 60000 ms for per-invocation resolution.
           - Include latency.per_token, response.duration, total/input/output tokens, and request.count metrics.
           - timeFrame: windowSize 3600000 (last 1 hour) unless specified otherwise.

        3. Treat each non-zero 2-minute bucket as one workflow invocation.
           Compute P95 across all non-zero latency values.
           Present only invocations exceeding P95 in a table:
               Time (UTC) | Latency/Token (ms) | Response Duration (ms) | Total Tokens | Input Tokens | Output Tokens
        """
        return """
        Do NOT use manage_applications tool — this data is not available via call traces.
        Use manage_infrastructure with type "oTelLLM", filtered by the agent label, at fine granularity (60s)
        to get per-invocation time-series. Compute P95 across non-zero latency buckets and present only
        invocations exceeding it in a table.
        """

    @classmethod
    def get_prompts(cls):
        """Get all prompts defined in this class"""
        return [
            ('infra_available_metrics', cls.infra_available_metrics),
            ('infra_get_entities', cls.infra_get_entities),
            ('infra_available_plugins', cls.infra_available_plugins),
            ('llm_performance_and_token_queries', cls.llm_performance_and_token_queries),
            ('list_llm_genai_apps', cls.list_llm_genai_apps),
            ('failed_llm_prompt_or_output', cls.failed_llm_prompt_or_output),
            ('total_llm_token_usage', cls.total_llm_token_usage),
            ('llm_individual_trace_latency_and_tokens', cls.llm_individual_trace_latency_and_tokens),
        ]
