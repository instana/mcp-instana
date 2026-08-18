"""Tests for the SyntheticMetricsPrompts class."""
import unittest

from src.prompts import PROMPT_REGISTRY
from src.prompts.synthetic.synthetic_metrics import SyntheticMetricsPrompts

EXPECTED_PROMPT_NAMES = [
    "get_metrics_result",
]


def _in_registry(func) -> bool:
    return any(
        isinstance(item, staticmethod) and item.__func__ == func
        for item in PROMPT_REGISTRY
    )


class TestSyntheticMetricsPromptsRegistration(unittest.TestCase):

    def test_get_metrics_result_registered(self):
        self.assertTrue(_in_registry(SyntheticMetricsPrompts.get_metrics_result))

    def test_all_prompts_registered(self):
        for name, func in SyntheticMetricsPrompts.get_prompts():
            self.assertTrue(_in_registry(func), f"Prompt '{name}' not in PROMPT_REGISTRY")


class TestSyntheticMetricsPromptsGetPrompts(unittest.TestCase):

    def setUp(self):
        self.prompts = SyntheticMetricsPrompts.get_prompts()

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

    def test_order_is_stable_across_calls(self):
        names1 = [p[0] for p in SyntheticMetricsPrompts.get_prompts()]
        names2 = [p[0] for p in SyntheticMetricsPrompts.get_prompts()]
        self.assertEqual(names1, names2)


class TestGetMetricsResultContent(unittest.TestCase):

    def test_no_payload_shows_default_placeholder(self):
        result = SyntheticMetricsPrompts.get_metrics_result()
        self.assertIn("(not specified)", result)

    def test_payload_interpolated(self):
        payload = {"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        result = SyntheticMetricsPrompts.get_metrics_result(payload=payload)
        self.assertIn("synthetic.metricsResponseTime", result)
        self.assertIn("SUM", result)

    def test_required_metrics_field_documented(self):
        result = SyntheticMetricsPrompts.get_metrics_result()
        self.assertIn("metrics (required)", result)

    def test_optional_fields_documented(self):
        result = SyntheticMetricsPrompts.get_metrics_result()
        for field in ("timeFrame", "pagination", "groups", "tagFilterExpression",
                      "disableDefaultGroups", "includeAggregatedTestIds"):
            self.assertIn(field, result)

    def test_catalog_prerequisite_mentioned(self):
        result = SyntheticMetricsPrompts.get_metrics_result()
        self.assertIn("get_synthetic_catalog_metrics", result)
        self.assertIn("get_synthetic_tag_catalog", result)

    def test_returns_string(self):
        result = SyntheticMetricsPrompts.get_metrics_result()
        self.assertIsInstance(result, str)
        self.assertTrue(result.strip())


class TestSyntheticMetricsPromptsIntegration(unittest.TestCase):

    def test_class_usable_without_instantiation(self):
        self.assertGreater(len(SyntheticMetricsPrompts.get_prompts()), 0)

    def test_every_prompt_output_is_nonempty_string(self):
        for name, func in SyntheticMetricsPrompts.get_prompts():
            result = func()
            self.assertIsInstance(result, str, f"{name} did not return str")
            self.assertTrue(result.strip(), f"{name} returned empty string")

    def test_get_prompts_idempotent(self):
        p1 = SyntheticMetricsPrompts.get_prompts()
        p2 = SyntheticMetricsPrompts.get_prompts()
        self.assertEqual([n for n, _ in p1], [n for n, _ in p2])


if __name__ == "__main__":
    unittest.main()
