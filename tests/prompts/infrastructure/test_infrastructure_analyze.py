"""Tests for the InfrastructureAnalyzePrompts class."""
import unittest

from src.prompts import PROMPT_REGISTRY
from src.prompts.infrastructure.infrastructure_analyze import (
    InfrastructureAnalyzePrompts,
)


class TestInfrastructureAnalyzePrompts(unittest.TestCase):
    """Test cases for the InfrastructureAnalyzePrompts class."""

    # ------------------------------------------------------------------
    # Registry registration tests
    # ------------------------------------------------------------------

    def test_infra_available_metrics_registered(self):
        """Test that infra_available_metrics is registered in the prompt registry."""
        func = InfrastructureAnalyzePrompts.infra_available_metrics
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_infra_get_entities_registered(self):
        """Test that infra_get_entities is registered in the prompt registry."""
        func = InfrastructureAnalyzePrompts.infra_get_entities
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_infra_available_plugins_registered(self):
        """Test that infra_available_plugins is registered in the prompt registry."""
        func = InfrastructureAnalyzePrompts.infra_available_plugins
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_llm_performance_and_token_queries_registered(self):
        """Test that llm_performance_and_token_queries is registered in the prompt registry."""
        func = InfrastructureAnalyzePrompts.llm_performance_and_token_queries
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_list_llm_genai_apps_registered(self):
        """Test that list_llm_genai_apps is registered in the prompt registry."""
        func = InfrastructureAnalyzePrompts.list_llm_genai_apps
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_failed_llm_prompt_or_output_registered(self):
        """Test that failed_llm_prompt_or_output is registered in the prompt registry."""
        func = InfrastructureAnalyzePrompts.failed_llm_prompt_or_output
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_total_llm_token_usage_registered(self):
        """Test that total_llm_token_usage is registered in the prompt registry."""
        func = InfrastructureAnalyzePrompts.total_llm_token_usage
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_llm_individual_trace_latency_and_tokens_registered(self):
        """Test that llm_individual_trace_latency_and_tokens is registered in the prompt registry."""
        func = InfrastructureAnalyzePrompts.llm_individual_trace_latency_and_tokens
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    # ------------------------------------------------------------------
    # get_prompts() shape tests
    # ------------------------------------------------------------------

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all 8 prompts in the correct order."""
        prompts = InfrastructureAnalyzePrompts.get_prompts()
        self.assertEqual(len(prompts), 8)
        names = [p[0] for p in prompts]
        self.assertEqual(names, [
            'infra_available_metrics',
            'infra_get_entities',
            'infra_available_plugins',
            'llm_performance_and_token_queries',
            'list_llm_genai_apps',
            'failed_llm_prompt_or_output',
            'total_llm_token_usage',
            'llm_individual_trace_latency_and_tokens',
        ])

    # ------------------------------------------------------------------
    # infra_available_metrics content tests
    # ------------------------------------------------------------------

    def test_infra_available_metrics_contains_tool_instruction(self):
        """Test that infra_available_metrics output directs to manage_infrastructure."""
        result = InfrastructureAnalyzePrompts.infra_available_metrics(type='host')
        self.assertIn('manage_infrastructure', result)
        self.assertIn('resource_type: "catalog"', result)
        self.assertIn('operation: "get_plugin_schema"', result)

    def test_infra_available_metrics_with_all_params(self):
        """Test that infra_available_metrics interpolates all provided parameters."""
        result = InfrastructureAnalyzePrompts.infra_available_metrics(
            type='host', query='cpu', var_from=1000, to=2000, windowSize=3600000
        )
        self.assertIn('host', result)
        self.assertIn('cpu', result)
        self.assertIn('1000', result)
        self.assertIn('2000', result)
        self.assertIn('3600000', result)

    def test_infra_available_metrics_none_defaults(self):
        """Test that optional params default to 'None' string when not provided."""
        result = InfrastructureAnalyzePrompts.infra_available_metrics(type='jvmRuntimePlatform')
        self.assertIn('jvmRuntimePlatform', result)
        self.assertIn('None', result)

    # ------------------------------------------------------------------
    # infra_get_entities content tests
    # ------------------------------------------------------------------

    def test_infra_get_entities_contains_tool_instruction(self):
        """Test that infra_get_entities output directs to manage_infrastructure."""
        result = InfrastructureAnalyzePrompts.infra_get_entities(type='host')
        self.assertIn('manage_infrastructure', result)
        self.assertIn('resource_type: "analyze"', result)
        self.assertIn('operation: "get_entities"', result)

    def test_infra_get_entities_with_all_params(self):
        """Test that infra_get_entities interpolates all provided parameters."""
        result = InfrastructureAnalyzePrompts.infra_get_entities(
            type='host', metrics='cpu.used', windowSize=3600000, to=9999999
        )
        self.assertIn('host', result)
        self.assertIn('cpu.used', result)
        self.assertIn('3600000', result)
        self.assertIn('9999999', result)

    def test_infra_get_entities_none_defaults(self):
        """Test that optional params default to 'None' string when not provided."""
        result = InfrastructureAnalyzePrompts.infra_get_entities(type='host')
        self.assertIn('None', result)

    # ------------------------------------------------------------------
    # infra_available_plugins content tests
    # ------------------------------------------------------------------

    def test_infra_available_plugins_contains_tool_instruction(self):
        """Test that infra_available_plugins output directs to manage_infrastructure."""
        result = InfrastructureAnalyzePrompts.infra_available_plugins(offline=False)
        self.assertIn('manage_infrastructure', result)
        self.assertIn('resource_type: "catalog"', result)
        self.assertIn('operation: "get_plugins"', result)

    def test_infra_available_plugins_with_all_params(self):
        """Test that infra_available_plugins interpolates all provided parameters."""
        result = InfrastructureAnalyzePrompts.infra_available_plugins(
            offline=True, query='k8s', windowSize=1800000, to=12345
        )
        self.assertIn('True', result)
        self.assertIn('k8s', result)
        self.assertIn('1800000', result)
        self.assertIn('12345', result)

    def test_infra_available_plugins_none_defaults(self):
        """Test that optional params default to 'None' string when not provided."""
        result = InfrastructureAnalyzePrompts.infra_available_plugins(offline=False)
        self.assertIn('None', result)

    # ------------------------------------------------------------------
    # llm_performance_and_token_queries content tests
    # ------------------------------------------------------------------

    def test_llm_performance_and_token_queries_uses_infrastructure(self):
        """Test that the prompt routes to manage_infrastructure and not manage_applications."""
        result = InfrastructureAnalyzePrompts.llm_performance_and_token_queries()
        self.assertIn('manage_infrastructure', result)
        self.assertIn('Do NOT use manage_applications', result)

    def test_llm_performance_and_token_queries_specifies_otelllm(self):
        """Test that the prompt specifies the oTelLLM entity type."""
        result = InfrastructureAnalyzePrompts.llm_performance_and_token_queries()
        self.assertIn('oTelLLM', result)

    def test_llm_performance_and_token_queries_mentions_get_plugin_schema(self):
        """Test that the prompt instructs to call get_plugin_schema first."""
        result = InfrastructureAnalyzePrompts.llm_performance_and_token_queries()
        self.assertIn('get_plugin_schema', result)

    # ------------------------------------------------------------------
    # list_llm_genai_apps content tests
    # ------------------------------------------------------------------

    def test_list_llm_genai_apps_uses_infrastructure(self):
        """Test that the prompt routes to manage_infrastructure and not manage_applications."""
        result = InfrastructureAnalyzePrompts.list_llm_genai_apps()
        self.assertIn('manage_infrastructure', result)
        self.assertIn('Do NOT use manage_applications', result)

    def test_list_llm_genai_apps_specifies_resources_and_snapshots(self):
        """Test that the prompt specifies the resources/get_snapshots operation."""
        result = InfrastructureAnalyzePrompts.list_llm_genai_apps()
        self.assertIn('resource_type: "resources"', result)
        self.assertIn('operation: "get_snapshots"', result)
        self.assertIn('oTelLLM', result)

    # ------------------------------------------------------------------
    # failed_llm_prompt_or_output content tests
    # ------------------------------------------------------------------

    def test_failed_llm_prompt_or_output_uses_infrastructure(self):
        """Test that the prompt routes to manage_infrastructure and not manage_applications."""
        result = InfrastructureAnalyzePrompts.failed_llm_prompt_or_output()
        self.assertIn('manage_infrastructure', result)
        self.assertIn('Do NOT use manage_applications', result)

    def test_failed_llm_prompt_or_output_specifies_analyze_get_entities(self):
        """Test that the prompt specifies the analyze/get_entities operation."""
        result = InfrastructureAnalyzePrompts.failed_llm_prompt_or_output()
        self.assertIn('resource_type: "analyze"', result)
        self.assertIn('operation: "get_entities"', result)
        self.assertIn('oTelLLM', result)

    # ------------------------------------------------------------------
    # total_llm_token_usage content tests
    # ------------------------------------------------------------------

    def test_total_llm_token_usage_uses_infrastructure(self):
        """Test that the prompt routes to manage_infrastructure and not manage_applications."""
        result = InfrastructureAnalyzePrompts.total_llm_token_usage()
        self.assertIn('manage_infrastructure', result)
        self.assertIn('Do NOT use manage_applications', result)

    def test_total_llm_token_usage_specifies_entity_groups(self):
        """Test that the prompt specifies the analyze/get_entity_groups operation."""
        result = InfrastructureAnalyzePrompts.total_llm_token_usage()
        self.assertIn('resource_type: "analyze"', result)
        self.assertIn('operation: "get_entity_groups"', result)
        self.assertIn('oTelLLM', result)

    def test_total_llm_token_usage_mentions_token_metric(self):
        """Test that the prompt references a token usage metric."""
        result = InfrastructureAnalyzePrompts.total_llm_token_usage()
        self.assertIn('metrics.gauges.llm.usage.total_tokens', result)
        self.assertIn('get_plugin_schema', result)

    # ------------------------------------------------------------------
    # llm_individual_trace_latency_and_tokens content tests
    # ------------------------------------------------------------------

    def test_llm_individual_trace_latency_and_tokens_uses_infrastructure(self):
        """Test that the prompt routes to manage_infrastructure and not manage_applications."""
        result = InfrastructureAnalyzePrompts.llm_individual_trace_latency_and_tokens()
        self.assertIn('manage_infrastructure', result)
        self.assertIn('Do NOT use manage_applications', result)

    def test_llm_individual_trace_latency_and_tokens_specifies_otelllm(self):
        """Test that the prompt specifies the oTelLLM type."""
        result = InfrastructureAnalyzePrompts.llm_individual_trace_latency_and_tokens()
        self.assertIn('oTelLLM', result)

    def test_llm_individual_trace_latency_and_tokens_mentions_p95(self):
        """Test that the prompt refers to P95 computation."""
        result = InfrastructureAnalyzePrompts.llm_individual_trace_latency_and_tokens()
        self.assertIn('P95', result)


if __name__ == '__main__':
    unittest.main()
