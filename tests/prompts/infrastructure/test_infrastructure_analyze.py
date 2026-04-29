"""Tests for the InfrastructureAnalyzePrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.infrastructure.infrastructure_analyze import (
    InfrastructureAnalyzePrompts,
)


class TestInfrastructureAnalyzePrompts(unittest.TestCase):
    """Test cases for the InfrastructureAnalyzePrompts class."""

    def test_infra_available_metrics_registered(self):
        """Test that infra_available_metrics is registered in the prompt registry."""
        # The registry contains staticmethod objects, so we need to unwrap them
        func = InfrastructureAnalyzePrompts.infra_available_metrics
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_infra_get_entities_registered(self):
        """Test that infra_get_entities is registered in the prompt registry."""
        # The registry contains staticmethod objects, so we need to unwrap them
        func = InfrastructureAnalyzePrompts.infra_get_entities
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_infra_available_plugins_registered(self):
        """Test that infra_available_plugins is registered in the prompt registry."""
        # The registry contains staticmethod objects, so we need to unwrap them
        func = InfrastructureAnalyzePrompts.infra_available_plugins
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = InfrastructureAnalyzePrompts.get_prompts()
        # Updated to 12 prompts: 3 original + 9 IBM MQ debugging workflows
        self.assertEqual(len(prompts), 12)
        self.assertEqual(prompts[0][0], 'infra_available_metrics')
        self.assertEqual(prompts[1][0], 'infra_get_entities')
        self.assertEqual(prompts[2][0], 'infra_available_plugins')
        # Verify IBM MQ debugging prompts are included
        prompt_names = [p[0] for p in prompts]
        self.assertIn('debug_ibmmq_queue_full', prompt_names)
        self.assertIn('debug_ibmmq_invalid_queue', prompt_names)
        self.assertIn('debug_ibmmq_channel_issues', prompt_names)
        self.assertIn('monitor_ibmmq_health', prompt_names)


if __name__ == '__main__':
    unittest.main()
