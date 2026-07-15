"""Tests for the ApplicationAnalyzePrompts class."""
import unittest

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_analyze import ApplicationAnalyzePrompts


class TestApplicationAnalyzePrompts(unittest.TestCase):
    """Test cases for the ApplicationAnalyzePrompts class."""

    def test_get_all_traces_registered(self):
        func = ApplicationAnalyzePrompts.get_all_traces
        self.assertTrue(any(getattr(item, "__func__", item) == func for item in PROMPT_REGISTRY))

    def test_get_trace_details_registered(self):
        func = ApplicationAnalyzePrompts.get_trace_details
        self.assertTrue(any(getattr(item, "__func__", item) == func for item in PROMPT_REGISTRY))

    def test_get_trace_groups_registered(self):
        func = ApplicationAnalyzePrompts.get_trace_groups
        self.assertTrue(any(getattr(item, "__func__", item) == func for item in PROMPT_REGISTRY))

    def test_get_prompts_returns_all_prompts(self):
        prompts = ApplicationAnalyzePrompts.get_prompts()
        self.assertEqual(len(prompts), 3)
        self.assertEqual(prompts[0][0], "get_all_traces")
        self.assertEqual(prompts[1][0], "get_trace_details")
        self.assertEqual(prompts[2][0], "get_trace_groups")


if __name__ == "__main__":
    unittest.main()
