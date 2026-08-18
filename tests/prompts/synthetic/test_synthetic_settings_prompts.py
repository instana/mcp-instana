"""Tests for the SyntheticSettingsPrompts class."""
import unittest

from src.prompts import PROMPT_REGISTRY
from src.prompts.synthetic.synthetic_settings import SyntheticSettingsPrompts

EXPECTED_PROMPT_NAMES = [
    "get_synthetic_test",
    "get_synthetic_tests",
    "get_locations",
    "get_location_by_id",
    "get_all_datacenters",
    "get_fleet_health_score",
]


def _in_registry(func) -> bool:
    return any(
        isinstance(item, staticmethod) and item.__func__ == func
        for item in PROMPT_REGISTRY
    )


class TestSyntheticSettingsPromptsRegistration(unittest.TestCase):

    def test_get_synthetic_test_registered(self):
        self.assertTrue(_in_registry(SyntheticSettingsPrompts.get_synthetic_test))

    def test_get_synthetic_tests_registered(self):
        self.assertTrue(_in_registry(SyntheticSettingsPrompts.get_synthetic_tests))

    def test_get_locations_registered(self):
        self.assertTrue(_in_registry(SyntheticSettingsPrompts.get_locations))

    def test_get_location_by_id_registered(self):
        self.assertTrue(_in_registry(SyntheticSettingsPrompts.get_location_by_id))

    def test_get_all_datacenters_registered(self):
        self.assertTrue(_in_registry(SyntheticSettingsPrompts.get_all_datacenters))

    def test_get_fleet_health_score_registered(self):
        self.assertTrue(_in_registry(SyntheticSettingsPrompts.get_fleet_health_score))

    def test_all_prompts_registered(self):
        for name, func in SyntheticSettingsPrompts.get_prompts():
            self.assertTrue(_in_registry(func), f"Prompt '{name}' not in PROMPT_REGISTRY")


class TestSyntheticSettingsPromptsGetPrompts(unittest.TestCase):

    def setUp(self):
        self.prompts = SyntheticSettingsPrompts.get_prompts()

    def test_returns_list(self):
        self.assertIsInstance(self.prompts, list)

    def test_returns_correct_count(self):
        self.assertEqual(len(self.prompts), len(EXPECTED_PROMPT_NAMES))

    def test_every_item_is_two_tuple(self):
        for item in self.prompts:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_every_name_is_nonempty_string(self):
        for name, _ in self.prompts:
            self.assertIsInstance(name, str)
            self.assertTrue(name)

    def test_names_match_expected_order(self):
        self.assertEqual([p[0] for p in self.prompts], EXPECTED_PROMPT_NAMES)

    def test_names_are_unique(self):
        names = [p[0] for p in self.prompts]
        self.assertEqual(len(names), len(set(names)))

    def test_functions_are_unique(self):
        ids = [id(p[1]) for p in self.prompts]
        self.assertEqual(len(ids), len(set(ids)))

    def test_order_is_stable_across_calls(self):
        names1 = [p[0] for p in SyntheticSettingsPrompts.get_prompts()]
        names2 = [p[0] for p in SyntheticSettingsPrompts.get_prompts()]
        self.assertEqual(names1, names2)

    def test_all_expected_names_present(self):
        actual = {p[0] for p in self.prompts}
        for expected in EXPECTED_PROMPT_NAMES:
            self.assertIn(expected, actual)


# ---------------------------------------------------------------------------
# Content tests
# ---------------------------------------------------------------------------

class TestGetSyntheticTestContent(unittest.TestCase):

    def test_defaults_show_none_placeholders(self):
        result = SyntheticSettingsPrompts.get_synthetic_test()
        self.assertIn("None (supply test_name instead for name resolution)", result)
        self.assertIn("None (supply test_id instead for direct lookup)", result)

    def test_test_id_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_test(test_id="abc-123")
        self.assertIn("abc-123", result)

    def test_test_name_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_test(test_name="e2e-api-ScriptTest")
        self.assertIn("e2e-api-ScriptTest", result)

    def test_both_params_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_test(test_id="id-1", test_name="my-test")
        self.assertIn("id-1", result)
        self.assertIn("my-test", result)

    def test_name_resolution_described(self):
        result = SyntheticSettingsPrompts.get_synthetic_test()
        self.assertIn("case-insensitive", result)

    def test_returns_string(self):
        result = SyntheticSettingsPrompts.get_synthetic_test()
        self.assertIsInstance(result, str)
        self.assertTrue(result.strip())


class TestGetSyntheticTestsContent(unittest.TestCase):

    def test_defaults_show_none_placeholders(self):
        result = SyntheticSettingsPrompts.get_synthetic_tests()
        self.assertIn("None (no application filter)", result)
        self.assertIn("None (no location filter)", result)
        self.assertIn("None (no credential filter)", result)
        self.assertIn("None (return all)", result)

    def test_application_id_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_tests(application_id="app-xyz")
        self.assertIn("app-xyz", result)

    def test_location_id_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_tests(location_id="loc-abc")
        self.assertIn("loc-abc", result)

    def test_credential_name_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_tests(credential_name="my-cred")
        self.assertIn("my-cred", result)

    def test_sort_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_tests(sort="+label")
        self.assertIn("+label", result)

    def test_offset_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_tests(offset=5)
        self.assertIn("5", result)

    def test_limit_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_tests(limit=50)
        self.assertIn("50", result)

    def test_filter_interpolated(self):
        result = SyntheticSettingsPrompts.get_synthetic_tests(filter="active=true")
        self.assertIn("active=true", result)

    def test_all_optional_note_present(self):
        result = SyntheticSettingsPrompts.get_synthetic_tests()
        self.assertIn("All parameters are optional", result)

    def test_returns_string(self):
        self.assertIsInstance(SyntheticSettingsPrompts.get_synthetic_tests(), str)


class TestGetLocationsContent(unittest.TestCase):

    def test_defaults_show_none_placeholders(self):
        result = SyntheticSettingsPrompts.get_locations()
        self.assertIn("None (return all", result)

    def test_location_type_interpolated(self):
        result = SyntheticSettingsPrompts.get_locations(location_type="Managed")
        self.assertIn("Managed", result)

    def test_status_interpolated(self):
        result = SyntheticSettingsPrompts.get_locations(status="Online")
        self.assertIn("Online", result)

    def test_datacenter_identification_section_present(self):
        result = SyntheticSettingsPrompts.get_locations()
        self.assertIn("DATACENTER IDENTIFICATION", result)
        self.assertIn("Managed", result)
        self.assertIn("Private", result)

    def test_key_fields_documented(self):
        result = SyntheticSettingsPrompts.get_locations()
        for field in ("id", "label", "displayLabel", "geoPoint", "status", "totalTests"):
            self.assertIn(field, result)

    def test_workflow_section_present(self):
        result = SyntheticSettingsPrompts.get_locations()
        self.assertIn("WORKFLOW", result)
        self.assertIn("TAG_FILTER", result)

    def test_forbidden_api_mentioned(self):
        result = SyntheticSettingsPrompts.get_locations()
        self.assertIn("get_location_summary_list", result)
        self.assertIn("NEVER", result)

    def test_sort_interpolated(self):
        result = SyntheticSettingsPrompts.get_locations(sort="-label")
        self.assertIn("-label", result)

    def test_returns_string(self):
        self.assertIsInstance(SyntheticSettingsPrompts.get_locations(), str)


class TestGetLocationByIdContent(unittest.TestCase):

    def test_defaults_show_none_placeholders(self):
        result = SyntheticSettingsPrompts.get_location_by_id()
        self.assertIn("None (supply location_name instead for name resolution)", result)
        self.assertIn("None (supply location_id instead for direct lookup)", result)

    def test_location_id_interpolated(self):
        result = SyntheticSettingsPrompts.get_location_by_id(location_id="loc-99")
        self.assertIn("loc-99", result)

    def test_location_name_interpolated(self):
        result = SyntheticSettingsPrompts.get_location_by_id(location_name="ap-south-1(Mumbai)")
        self.assertIn("ap-south-1(Mumbai)", result)

    def test_name_resolution_steps_present(self):
        result = SyntheticSettingsPrompts.get_location_by_id()
        self.assertIn("1.", result)
        self.assertIn("2.", result)
        self.assertIn("3.", result)
        self.assertIn("4.", result)

    def test_label_and_display_label_match_documented(self):
        result = SyntheticSettingsPrompts.get_location_by_id()
        self.assertIn("label", result)
        self.assertIn("displayLabel", result)

    def test_case_insensitive_matching_noted(self):
        result = SyntheticSettingsPrompts.get_location_by_id()
        self.assertIn("case-insensitive", result)

    def test_returns_string(self):
        self.assertIsInstance(SyntheticSettingsPrompts.get_location_by_id(), str)


class TestGetAllDatacentersContent(unittest.TestCase):

    def test_default_status_shows_placeholder(self):
        result = SyntheticSettingsPrompts.get_all_datacenters()
        self.assertIn("None (return all datacenters", result)

    def test_status_online_interpolated(self):
        result = SyntheticSettingsPrompts.get_all_datacenters(status="Online")
        self.assertIn("Online", result)

    def test_managed_type_documented(self):
        result = SyntheticSettingsPrompts.get_all_datacenters()
        self.assertIn("Managed", result)

    def test_total_online_field_documented(self):
        result = SyntheticSettingsPrompts.get_all_datacenters()
        self.assertIn("total_online", result)

    def test_forbidden_api_warning_present(self):
        result = SyntheticSettingsPrompts.get_all_datacenters()
        self.assertIn("get_location_summary_list", result)
        self.assertIn("MUST NOT", result)

    def test_returns_field_list_documented(self):
        result = SyntheticSettingsPrompts.get_all_datacenters()
        for field in ("id", "label", "displayLabel", "geoPoint", "totalTests"):
            self.assertIn(field, result)

    def test_returns_string(self):
        self.assertIsInstance(SyntheticSettingsPrompts.get_all_datacenters(), str)


class TestGetFleetHealthScoreContent(unittest.TestCase):

    def test_default_datacenter_count_placeholder(self):
        result = SyntheticSettingsPrompts.get_fleet_health_score()
        self.assertIn("None (discover dynamically from get_all_datacenters)", result)

    def test_custom_datacenter_count_interpolated(self):
        result = SyntheticSettingsPrompts.get_fleet_health_score(datacenter_count=30)
        self.assertIn("30", result)

    def test_definition_formula_present(self):
        result = SyntheticSettingsPrompts.get_fleet_health_score()
        self.assertIn("Fleet health score", result)
        self.assertIn("successRate = 1.0", result)

    def test_forbidden_calculations_documented(self):
        result = SyntheticSettingsPrompts.get_fleet_health_score()
        self.assertIn("FORBIDDEN", result)
        self.assertIn("get_location_summary_list", result)
        self.assertIn("Private PoP", result)

    def test_five_required_steps_present(self):
        result = SyntheticSettingsPrompts.get_fleet_health_score()
        for step in ("1.", "2.", "3.", "4.", "5."):
            self.assertIn(step, result)

    def test_references_get_all_datacenters(self):
        result = SyntheticSettingsPrompts.get_fleet_health_score()
        self.assertIn("get_all_datacenters", result)

    def test_references_get_test_summary_list(self):
        result = SyntheticSettingsPrompts.get_fleet_health_score()
        self.assertIn("get_test_summary_list", result)

    def test_binary_pass_fail_logic_described(self):
        result = SyntheticSettingsPrompts.get_fleet_health_score()
        self.assertIn("PASSES", result)
        self.assertIn("FAILS", result)
        self.assertIn("passing_datacenters", result)
        self.assertIn("fleet_health_score", result)

    def test_report_section_present(self):
        result = SyntheticSettingsPrompts.get_fleet_health_score()
        self.assertIn("Report", result)
        self.assertIn("73%", result)  # example from the docstring

    def test_returns_string(self):
        self.assertIsInstance(SyntheticSettingsPrompts.get_fleet_health_score(), str)


class TestSyntheticSettingsPromptsIntegration(unittest.TestCase):

    def test_class_usable_without_instantiation(self):
        self.assertGreater(len(SyntheticSettingsPrompts.get_prompts()), 0)

    def test_get_prompts_idempotent(self):
        p1 = SyntheticSettingsPrompts.get_prompts()
        p2 = SyntheticSettingsPrompts.get_prompts()
        self.assertEqual([n for n, _ in p1], [n for n, _ in p2])

    def test_every_no_arg_prompt_returns_nonempty_string(self):
        no_arg_funcs = [
            SyntheticSettingsPrompts.get_synthetic_test,
            SyntheticSettingsPrompts.get_synthetic_tests,
            SyntheticSettingsPrompts.get_locations,
            SyntheticSettingsPrompts.get_location_by_id,
            SyntheticSettingsPrompts.get_all_datacenters,
            SyntheticSettingsPrompts.get_fleet_health_score,
        ]
        for func in no_arg_funcs:
            result = func()
            self.assertIsInstance(result, str, f"{func.__name__} did not return str")
            self.assertTrue(result.strip(), f"{func.__name__} returned empty string")

    def test_no_duplicate_prompt_names(self):
        names = [p[0] for p in SyntheticSettingsPrompts.get_prompts()]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
