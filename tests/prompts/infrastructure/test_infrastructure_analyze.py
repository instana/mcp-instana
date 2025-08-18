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
        self.assertIn(InfrastructureAnalyzePrompts.infra_available_metrics, PROMPT_REGISTRY)

    def test_infra_get_entities_registered(self):
        """Test that infra_get_entities is registered in the prompt registry."""
        self.assertIn(InfrastructureAnalyzePrompts.infra_get_entities, PROMPT_REGISTRY)

    def test_infra_available_plugins_registered(self):
        """Test that infra_available_plugins is registered in the prompt registry."""
        self.assertIn(InfrastructureAnalyzePrompts.infra_available_plugins, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = InfrastructureAnalyzePrompts.get_prompts()
        self.assertEqual(len(prompts), 3)
        self.assertEqual(prompts[0][0], 'infra_available_metrics')
        self.assertEqual(prompts[1][0], 'infra_get_entities')
        self.assertEqual(prompts[2][0], 'infra_available_plugins')


if __name__ == '__main__':
    unittest.main()


