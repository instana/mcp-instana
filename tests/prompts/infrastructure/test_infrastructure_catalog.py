"""Tests for the InfrastructureCatalogPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.infrastructure.infrastructure_catalog import (
    InfrastructureCatalogPrompts,
)


class TestInfrastructureCatalogPrompts(unittest.TestCase):
    """Test cases for the InfrastructureCatalogPrompts class."""

    def test_get_available_payload_keys_by_plugin_id_registered(self):
        """Test that get_available_payload_keys_by_plugin_id is registered in the prompt registry."""
        self.assertIn(InfrastructureCatalogPrompts.get_available_payload_keys_by_plugin_id, PROMPT_REGISTRY)

    def test_get_infrastructure_catalog_metrics_registered(self):
        """Test that get_infrastructure_catalog_metrics is registered in the prompt registry."""
        self.assertIn(InfrastructureCatalogPrompts.get_infrastructure_catalog_metrics, PROMPT_REGISTRY)

    def test_get_tag_catalog_registered(self):
        """Test that get_tag_catalog is registered in the prompt registry."""
        self.assertIn(InfrastructureCatalogPrompts.get_tag_catalog, PROMPT_REGISTRY)

    def test_get_tag_catalog_all_registered(self):
        """Test that get_tag_catalog_all is registered in the prompt registry."""
        self.assertIn(InfrastructureCatalogPrompts.get_tag_catalog_all, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = InfrastructureCatalogPrompts.get_prompts()
        self.assertEqual(len(prompts), 4)
        self.assertEqual(prompts[0][0], 'get_available_payload_keys_by_plugin_id')
        self.assertEqual(prompts[1][0], 'get_infrastructure_catalog_metrics')
        self.assertEqual(prompts[2][0], 'get_tag_catalog')
        self.assertEqual(prompts[3][0], 'get_tag_catalog_all')


if __name__ == '__main__':
    unittest.main()


