"""Tests for the ApplicationTopologyPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_topology import ApplicationTopologyPrompts


class TestApplicationTopologyPrompts(unittest.TestCase):
    """Test cases for the ApplicationTopologyPrompts class."""

    def test_get_application_topology_registered(self):
        """Test that get_application_topology is registered in the prompt registry."""
        self.assertIn(ApplicationTopologyPrompts.get_application_topology, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = ApplicationTopologyPrompts.get_prompts()
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0][0], 'get_application_topology')


if __name__ == '__main__':
    unittest.main()


