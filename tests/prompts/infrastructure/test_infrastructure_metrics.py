"""Tests for the InfrastructureMetricsPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.infrastructure.infrastructure_metrics import (
    InfrastructureMetricsPrompts,
)


class TestInfrastructureMetricsPrompts(unittest.TestCase):
    """Test cases for the InfrastructureMetricsPrompts class."""

    def test_get_infrastructure_metrics_registered(self):
        """Test that get_infrastructure_metrics is registered in the prompt registry."""
        self.assertIn(InfrastructureMetricsPrompts.get_infrastructure_metrics, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = InfrastructureMetricsPrompts.get_prompts()
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0][0], 'get_infrastructure_metrics')


if __name__ == '__main__':
    unittest.main()


