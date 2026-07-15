"""Tests for the ApplicationAnalyzePrompts class."""
import unittest

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_analyze import ApplicationAnalyzePrompts


class TestApplicationAnalyzePrompts(unittest.TestCase):
    """Test cases for the ApplicationAnalyzePrompts class."""

    def test_get_all_traces_prompt_output(self):
        prompt = ApplicationAnalyzePrompts.get_all_traces(payload={"timeFrame": {"windowSize": 3600000}})

        self.assertIn("Get all application traces with", prompt)
        self.assertIn("Payload: {'timeFrame': {'windowSize': 3600000}}", prompt)

    def test_get_all_traces_prompt_output_none_payload(self):
        prompt = ApplicationAnalyzePrompts.get_all_traces(payload=None)

        self.assertIn("Payload: None (will use default payload)", prompt)

    def test_get_trace_details_prompt_output(self):
        prompt = ApplicationAnalyzePrompts.get_trace_details(
            trace_id="trace-123",
            retrieval_size=100,
            offset=10,
            ingestion_time=1234567890
        )

        self.assertIn("Get trace details with", prompt)
        self.assertIn("Trace ID: trace-123", prompt)
        self.assertIn("Retrieval size: 100", prompt)
        self.assertIn("Offset: 10", prompt)
        self.assertIn("Ingestion time: 1234567890", prompt)

    def test_get_trace_groups_prompt_output(self):
        prompt = ApplicationAnalyzePrompts.get_trace_groups(payload={"group": {"groupbyTag": "trace.service.name"}})

        self.assertIn("Get grouped application traces with", prompt)
        self.assertIn("Payload: {'group': {'groupbyTag': 'trace.service.name'}}", prompt)

    def test_get_trace_groups_prompt_output_none_payload(self):
        prompt = ApplicationAnalyzePrompts.get_trace_groups(payload=None)

        self.assertIn("Payload: None", prompt)

    def test_get_prompts_returns_all_prompts(self):
        prompts = ApplicationAnalyzePrompts.get_prompts()

        self.assertEqual(len(prompts), 3)
        self.assertEqual([item[0] for item in prompts], [
            "get_all_traces",
            "get_trace_details",
            "get_trace_groups"
        ])

    def test_prompt_registry_contains_prompt_functions(self):
        names = [getattr(getattr(item, '__func__', item), '__name__', None) for item in PROMPT_REGISTRY]

        self.assertIn("get_all_traces", names)
        self.assertIn("get_trace_details", names)
        self.assertIn("get_trace_groups", names)


if __name__ == '__main__':
    unittest.main()
