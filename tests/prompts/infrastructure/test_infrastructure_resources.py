"""Tests for the InfrastructureResourcesPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.infrastructure.infrastructure_resources import (
    InfrastructureResourcesPrompts,
)


class TestInfrastructureResourcesPrompts(unittest.TestCase):
    """Test cases for the InfrastructureResourcesPrompts class."""

    def test_get_infrastructure_monitoring_state_registered(self):
        """Test that get_infrastructure_monitoring_state is registered in the prompt registry."""
        self.assertIn(InfrastructureResourcesPrompts.get_infrastructure_monitoring_state, PROMPT_REGISTRY)

    def test_get_infrastructure_plugin_payload_registered(self):
        """Test that get_infrastructure_plugin_payload is registered in the prompt registry."""
        self.assertIn(InfrastructureResourcesPrompts.get_infrastructure_plugin_payload, PROMPT_REGISTRY)

    def test_get_infrastructure_metrics_snapshot_registered(self):
        """Test that get_infrastructure_metrics_snapshot is registered in the prompt registry."""
        self.assertIn(InfrastructureResourcesPrompts.get_infrastructure_metrics_snapshot, PROMPT_REGISTRY)

    def test_post_infrastructure_metrics_snapshot_registered(self):
        """Test that post_infrastructure_metrics_snapshot is registered in the prompt registry."""
        self.assertIn(InfrastructureResourcesPrompts.post_infrastructure_metrics_snapshot, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = InfrastructureResourcesPrompts.get_prompts()
        self.assertEqual(len(prompts), 4)
        self.assertEqual(prompts[0][0], 'get_infrastructure_monitoring_state')
        self.assertEqual(prompts[1][0], 'get_infrastructure_plugin_payload')
        self.assertEqual(prompts[2][0], 'get_infrastructure_metrics_snapshot')
        self.assertEqual(prompts[3][0], 'post_infrastructure_metrics_snapshot')


if __name__ == '__main__':
    unittest.main()


