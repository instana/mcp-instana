"""Tests for the InfrastructureTopologyPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.infrastructure.infrastructure_topology import (
    InfrastructureTopologyPrompts,
)


class TestInfrastructureTopologyPrompts(unittest.TestCase):
    """Test cases for the InfrastructureTopologyPrompts class."""

    def test_get_related_hosts_registered(self):
        """Test that get_related_hosts is registered in the prompt registry."""
        self.assertIn(InfrastructureTopologyPrompts.get_related_hosts, PROMPT_REGISTRY)

    def test_get_topology_registered(self):
        """Test that get_topology is registered in the prompt registry."""
        self.assertIn(InfrastructureTopologyPrompts.get_topology, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = InfrastructureTopologyPrompts.get_prompts()
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[0][0], 'get_related_hosts')
        self.assertEqual(prompts[1][0], 'get_topology')


if __name__ == '__main__':
    unittest.main()


