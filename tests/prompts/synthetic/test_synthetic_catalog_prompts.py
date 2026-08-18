"""Tests for the SyntheticCatalogPrompts class."""
import unittest

from src.prompts import PROMPT_REGISTRY
from src.prompts.synthetic.synthetic_catalog import SyntheticCatalogPrompts

EXPECTED_PROMPT_NAMES = [
    "get_synthetic_catalog_metrics",
    "get_synthetic_tag_catalog",
]


def _in_registry(func) -> bool:
    return any(
        isinstance(item, staticmethod) and item.__func__ == func
        for item in PROMPT_REGISTRY
    )


class TestSyntheticCatalogPromptsRegistration(unittest.TestCase):

    def test_get_synthetic_catalog_metrics_registered(self):
        self.assertTrue(_in_registry(SyntheticCatalogPrompts.get_synthetic_catalog_metrics))

    def test_get_synthetic_tag_catalog_registered(self):
        self.assertTrue(_in_registry(SyntheticCatalogPrompts.get_synthetic_tag_catalog))

    def test_all_prompts_registered(self):
        for name, func in SyntheticCatalogPrompts.get_prompts():
            self.assertTrue(_in_registry(func), f"Prompt '{name}' not in PROMPT_REGISTRY")


class TestSyntheticCatalogPromptsGetPrompts(unittest.TestCase):

    def setUp(self):
        self.prompts = SyntheticCatalogPrompts.get_prompts()

    def test_returns_list(self):
        self.assertIsInstance(self.prompts, list)

    def test_returns_correct_count(self):
        self.assertEqual(len(self.prompts), len(EXPECTED_PROMPT_NAMES))

    def test_every_item_is_two_tuple(self):
        for item in self.prompts:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_names_match_expected_order(self):
        self.assertEqual([p[0] for p in self.prompts], EXPECTED_PROMPT_NAMES)

    def test_names_are_unique(self):
        names = [p[0] for p in self.prompts]
        self.assertEqual(len(names), len(set(names)))

    def test_functions_are_unique(self):
        ids = [id(p[1]) for p in self.prompts]
        self.assertEqual(len(ids), len(set(ids)))

    def test_order_is_stable_across_calls(self):
        names1 = [p[0] for p in SyntheticCatalogPrompts.get_prompts()]
        names2 = [p[0] for p in SyntheticCatalogPrompts.get_prompts()]
        self.assertEqual(names1, names2)


class TestSyntheticCatalogPromptsContent(unittest.TestCase):

    def test_get_synthetic_catalog_metrics_returns_string(self):
        result = SyntheticCatalogPrompts.get_synthetic_catalog_metrics()
        self.assertIsInstance(result, str)
        self.assertTrue(result.strip())

    def test_get_synthetic_catalog_metrics_mentions_metadata(self):
        result = SyntheticCatalogPrompts.get_synthetic_catalog_metrics()
        self.assertIn("metadata", result)

    def test_get_synthetic_catalog_metrics_mentions_aggregations(self):
        result = SyntheticCatalogPrompts.get_synthetic_catalog_metrics()
        self.assertIn("aggregations", result)

    def test_get_synthetic_tag_catalog_returns_string(self):
        result = SyntheticCatalogPrompts.get_synthetic_tag_catalog()
        self.assertIsInstance(result, str)
        self.assertTrue(result.strip())

    def test_get_synthetic_tag_catalog_mentions_tags(self):
        result = SyntheticCatalogPrompts.get_synthetic_tag_catalog()
        self.assertIn("synthetic monitoring tags", result)


class TestSyntheticCatalogPromptsIntegration(unittest.TestCase):

    def test_class_usable_without_instantiation(self):
        self.assertGreater(len(SyntheticCatalogPrompts.get_prompts()), 0)

    def test_every_prompt_output_is_nonempty_string(self):
        for name, func in SyntheticCatalogPrompts.get_prompts():
            result = func()
            self.assertIsInstance(result, str, f"{name} did not return str")
            self.assertTrue(result.strip(), f"{name} returned empty string")


if __name__ == "__main__":
    unittest.main()
