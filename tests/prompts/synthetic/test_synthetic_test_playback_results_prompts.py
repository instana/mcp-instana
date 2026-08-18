"""Tests for the SyntheticTestPlaybackResultsPrompts class."""
import unittest

from src.prompts import PROMPT_REGISTRY
from src.prompts.synthetic.synthetic_test_playback_results import (
    SyntheticTestPlaybackResultsPrompts,
)

# Canonical ordered list — mirrors get_prompts() return order
EXPECTED_PROMPT_NAMES = [
    # Cross-reference prompts
    "get_failing_tests_by_location_label",
    "get_tests_linked_to_location_with_success_rates",
    "get_online_datacenters_with_failures",
    "get_managed_fleet_health_score",
    "get_location_health_overview",
    "check_location_full_outage",
    "check_failure_concentration",
    # Temporal / release correlation prompts
    "analyze_synthetic_failure_rate_after_release",
    "find_first_failure_timestamp",
    "compare_test_pass_rate_across_locations",
    "check_consecutive_failures",
    "analyze_test_failure_trend",
    "find_most_reliable_tests",
    "rank_tests_by_failure_rate",
    "check_test_per_location_failure",
]


def _in_registry(func) -> bool:
    """Return True if func is registered as a staticmethod in PROMPT_REGISTRY."""
    return any(
        isinstance(item, staticmethod) and item.__func__ == func
        for item in PROMPT_REGISTRY
    )


class TestSyntheticTestPlaybackResultsPromptsRegistration(unittest.TestCase):
    """Each prompt is individually registered in PROMPT_REGISTRY via @auto_register_prompt."""

    def test_get_failing_tests_by_location_label_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.get_failing_tests_by_location_label))

    def test_get_tests_linked_to_location_with_success_rates_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.get_tests_linked_to_location_with_success_rates))

    def test_get_online_datacenters_with_failures_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.get_online_datacenters_with_failures))

    def test_get_fleet_health_cross_reference_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.get_managed_fleet_health_score))

    def test_get_location_health_overview_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.get_location_health_overview))

    def test_check_location_full_outage_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.check_location_full_outage))

    def test_check_failure_concentration_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.check_failure_concentration))

    def test_analyze_synthetic_failure_rate_after_release_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release))

    def test_find_first_failure_timestamp_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.find_first_failure_timestamp))

    def test_compare_test_pass_rate_across_locations_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.compare_test_pass_rate_across_locations))

    def test_check_consecutive_failures_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.check_consecutive_failures))

    def test_analyze_test_failure_trend_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.analyze_test_failure_trend))

    def test_find_most_reliable_tests_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.find_most_reliable_tests))

    def test_rank_tests_by_failure_rate_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.rank_tests_by_failure_rate))

    def test_check_test_per_location_failure_registered(self):
        self.assertTrue(_in_registry(SyntheticTestPlaybackResultsPrompts.check_test_per_location_failure))

    def test_all_prompts_registered(self):
        """Bulk check: every function returned by get_prompts is in the registry."""
        for name, func in SyntheticTestPlaybackResultsPrompts.get_prompts():
            self.assertTrue(_in_registry(func), f"Prompt '{name}' not found in PROMPT_REGISTRY")


class TestSyntheticTestPlaybackResultsPromptsGetPrompts(unittest.TestCase):
    """Tests for the get_prompts() classmethod structure and ordering."""

    def setUp(self):
        self.prompts = SyntheticTestPlaybackResultsPrompts.get_prompts()

    def test_returns_list(self):
        self.assertIsInstance(self.prompts, list)

    def test_returns_correct_count(self):
        self.assertEqual(len(self.prompts), len(EXPECTED_PROMPT_NAMES))

    def test_every_item_is_two_tuple(self):
        for item in self.prompts:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_every_name_is_string(self):
        for name, _ in self.prompts:
            self.assertIsInstance(name, str)
            self.assertTrue(name, "Prompt name must be non-empty")

    def test_every_function_is_not_none(self):
        for name, func in self.prompts:
            self.assertIsNotNone(func, f"Function for '{name}' is None")

    def test_names_match_expected_order(self):
        actual_names = [p[0] for p in self.prompts]
        self.assertEqual(actual_names, EXPECTED_PROMPT_NAMES)

    def test_names_are_unique(self):
        names = [p[0] for p in self.prompts]
        self.assertEqual(len(names), len(set(names)), "Duplicate prompt names found")

    def test_functions_are_unique(self):
        func_ids = [id(p[1]) for p in self.prompts]
        self.assertEqual(len(func_ids), len(set(func_ids)), "Duplicate prompt functions found")

    def test_order_is_stable_across_calls(self):
        names1 = [p[0] for p in SyntheticTestPlaybackResultsPrompts.get_prompts()]
        names2 = [p[0] for p in SyntheticTestPlaybackResultsPrompts.get_prompts()]
        self.assertEqual(names1, names2)

    def test_all_expected_names_present(self):
        actual_names = {p[0] for p in self.prompts}
        for expected in EXPECTED_PROMPT_NAMES:
            self.assertIn(expected, actual_names)


# ---------------------------------------------------------------------------
# Content tests — verify each prompt renders key workflow text correctly
# ---------------------------------------------------------------------------

class TestGetFailingTestsByLocationLabel(unittest.TestCase):

    def test_defaults_show_none_placeholders(self):
        result = SyntheticTestPlaybackResultsPrompts.get_failing_tests_by_location_label()
        self.assertIn("(not specified)", result)
        self.assertIn("3600000 (1 hour)", result)

    def test_location_label_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.get_failing_tests_by_location_label(
            location_label="instana-release-aws-ap-south-1-Mumbai"
        )
        self.assertIn("instana-release-aws-ap-south-1-Mumbai", result)

    def test_location_id_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.get_failing_tests_by_location_label(
            location_id="LOC123"
        )
        self.assertIn("LOC123", result)

    def test_custom_time_window_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.get_failing_tests_by_location_label(
            time_window_ms=7200000
        )
        self.assertIn("7200000", result)

    def test_required_steps_present(self):
        result = SyntheticTestPlaybackResultsPrompts.get_failing_tests_by_location_label()
        self.assertIn("1.", result)
        self.assertIn("2.", result)
        self.assertIn("3.", result)
        self.assertIn("get_locations", result)
        self.assertIn("get_test_summary_list", result)
        self.assertIn("successRate", result)


class TestGetTestsLinkedToLocationWithSuccessRates(unittest.TestCase):

    def test_location_id_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.get_tests_linked_to_location_with_success_rates(
            location_id="BSMZeeYgd72vn2sYYMDk"
        )
        self.assertIn("BSMZeeYgd72vn2sYYMDk", result)

    def test_default_time_window(self):
        result = SyntheticTestPlaybackResultsPrompts.get_tests_linked_to_location_with_success_rates(
            location_id="loc-1"
        )
        self.assertIn("3600000 (1 hour)", result)

    def test_custom_time_window(self):
        result = SyntheticTestPlaybackResultsPrompts.get_tests_linked_to_location_with_success_rates(
            location_id="loc-1", time_window_ms=14400000
        )
        self.assertIn("14400000", result)

    def test_workflow_references_both_operations(self):
        result = SyntheticTestPlaybackResultsPrompts.get_tests_linked_to_location_with_success_rates(
            location_id="loc-1"
        )
        self.assertIn("get_synthetic_tests", result)
        self.assertIn("get_test_summary_list", result)


class TestGetOnlineDatacentersWithFailures(unittest.TestCase):

    def test_contains_required_steps(self):
        result = SyntheticTestPlaybackResultsPrompts.get_online_datacenters_with_failures()
        self.assertIn("1.", result)
        self.assertIn("2.", result)
        self.assertIn("3.", result)

    def test_references_get_all_datacenters(self):
        result = SyntheticTestPlaybackResultsPrompts.get_online_datacenters_with_failures()
        self.assertIn("get_all_datacenters", result)
        self.assertIn('"Online"', result)

    def test_references_get_test_summary_list(self):
        result = SyntheticTestPlaybackResultsPrompts.get_online_datacenters_with_failures()
        self.assertIn("get_test_summary_list", result)

    def test_describes_failing_and_passing_cases(self):
        result = SyntheticTestPlaybackResultsPrompts.get_online_datacenters_with_failures()
        self.assertIn("FAILING", result)
        self.assertIn("PASSING", result)


class TestGetFleetHealthCrossReference(unittest.TestCase):

    def test_default_time_window(self):
        result = SyntheticTestPlaybackResultsPrompts.get_managed_fleet_health_score()
        self.assertIn("3600000 (1 hour)", result)

    def test_custom_time_window(self):
        result = SyntheticTestPlaybackResultsPrompts.get_managed_fleet_health_score(
            time_window_ms=1800000
        )
        self.assertIn("1800000", result)

    def test_four_step_workflow(self):
        result = SyntheticTestPlaybackResultsPrompts.get_managed_fleet_health_score()
        for step in ("1.", "2.", "3.", "4."):
            self.assertIn(step, result)

    def test_forbidden_clause_present(self):
        result = SyntheticTestPlaybackResultsPrompts.get_managed_fleet_health_score()
        self.assertIn("do NOT average", result)

    def test_passing_count_formula_present(self):
        result = SyntheticTestPlaybackResultsPrompts.get_managed_fleet_health_score()
        self.assertIn("fleet_health_score", result)
        self.assertIn("total_online", result)


class TestGetLocationHealthOverview(unittest.TestCase):

    def test_four_classifications_present(self):
        result = SyntheticTestPlaybackResultsPrompts.get_location_health_overview()
        for cls_name in ("HEALTHY", "DEGRADED", "FAILING", "NO DATA"):
            self.assertIn(cls_name, result)

    def test_default_time_window(self):
        result = SyntheticTestPlaybackResultsPrompts.get_location_health_overview()
        self.assertIn("3600000 (1 hour)", result)

    def test_custom_time_window(self):
        result = SyntheticTestPlaybackResultsPrompts.get_location_health_overview(
            time_window_ms=3600000 * 6
        )
        self.assertIn(str(3600000 * 6), result)

    def test_references_get_locations(self):
        result = SyntheticTestPlaybackResultsPrompts.get_location_health_overview()
        self.assertIn("get_locations", result)


class TestCheckLocationFullOutage(unittest.TestCase):

    def test_full_outage_definition_present(self):
        result = SyntheticTestPlaybackResultsPrompts.check_location_full_outage()
        self.assertIn("successRate = 0.0", result)

    def test_distinguishes_full_and_partial_outage(self):
        result = SyntheticTestPlaybackResultsPrompts.check_location_full_outage()
        self.assertIn("full outage", result)
        self.assertIn("partial outage", result)

    def test_default_time_window(self):
        result = SyntheticTestPlaybackResultsPrompts.check_location_full_outage()
        self.assertIn("3600000 (1 hour)", result)


class TestCheckFailureConcentration(unittest.TestCase):

    def test_verdict_text_present(self):
        result = SyntheticTestPlaybackResultsPrompts.check_failure_concentration()
        self.assertIn("concentrated", result)
        self.assertIn("widespread", result)

    def test_managed_vs_private_comparison(self):
        result = SyntheticTestPlaybackResultsPrompts.check_failure_concentration()
        self.assertIn("Managed", result)
        self.assertIn("Private", result)

    def test_default_time_window(self):
        result = SyntheticTestPlaybackResultsPrompts.check_failure_concentration()
        self.assertIn("3600000 (1 hour)", result)


class TestAnalyzeSyntheticFailureRateAfterRelease(unittest.TestCase):

    def test_release_name_produces_name_filter_lookup(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release(
            release_name="backend/release-323-21"
        )
        self.assertIn("name_filter='backend/release-323-21'", result)

    def test_release_id_produces_direct_fetch(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release(
            release_id="rel-abc"
        )
        self.assertIn("release_id='rel-abc'", result)

    def test_both_provided_prefers_release_id(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release(
            release_name="my-release", release_id="rel-xyz"
        )
        self.assertIn("release_id='rel-xyz'", result)
        self.assertNotIn("name_filter='my-release'", result)

    def test_neither_provided_shows_error(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release()
        self.assertIn("ERROR", result)
        self.assertIn("supply either release_name or release_id", result)

    def test_default_comparison_window(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release(
            release_name="r"
        )
        self.assertIn("3600000 (1 hour each side)", result)

    def test_custom_comparison_window(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release(
            release_name="r", comparison_window_ms=7200000
        )
        self.assertIn("7200000", result)

    def test_four_step_workflow(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release(
            release_name="r"
        )
        for step in ("1.", "2.", "3.", "4."):
            self.assertIn(step, result)

    def test_delta_comparison_described(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release(
            release_name="r"
        )
        self.assertIn("delta", result)
        self.assertIn("pre_rate", result)
        self.assertIn("post_rate", result)


class TestFindFirstFailureTimestamp(unittest.TestCase):

    def test_defaults_show_none_placeholders(self):
        result = SyntheticTestPlaybackResultsPrompts.find_first_failure_timestamp()
        self.assertIn("(not specified)", result)
        self.assertIn("86400000 (24 hours)", result)

    def test_test_name_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.find_first_failure_timestamp(
            test_name="test-march3-new"
        )
        self.assertIn("test-march3-new", result)

    def test_location_name_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.find_first_failure_timestamp(
            location_name="ap-south-1(Mumbai)"
        )
        self.assertIn("ap-south-1(Mumbai)", result)

    def test_four_step_workflow(self):
        result = SyntheticTestPlaybackResultsPrompts.find_first_failure_timestamp()
        for step in ("1.", "2.", "3.", "4."):
            self.assertIn(step, result)

    def test_ascending_order_specified(self):
        result = SyntheticTestPlaybackResultsPrompts.find_first_failure_timestamp()
        self.assertIn("ASC", result)

    def test_metrics_status_check_present(self):
        result = SyntheticTestPlaybackResultsPrompts.find_first_failure_timestamp()
        self.assertIn("metricsStatus", result)


class TestCompareTestPassRateAcrossLocations(unittest.TestCase):

    def test_defaults(self):
        result = SyntheticTestPlaybackResultsPrompts.compare_test_pass_rate_across_locations()
        self.assertIn("604800000 (7 days)", result)
        self.assertIn("(not specified — compare all locations)", result)

    def test_test_name_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.compare_test_pass_rate_across_locations(
            test_name="feb-27-ssl-test"
        )
        self.assertIn("feb-27-ssl-test", result)

    def test_location_names_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.compare_test_pass_rate_across_locations(
            location_names=["ap-south-1(Mumbai)", "us-east-1(NVirginia)"]
        )
        self.assertIn("ap-south-1(Mumbai)", result)
        self.assertIn("us-east-1(NVirginia)", result)

    def test_four_step_workflow(self):
        result = SyntheticTestPlaybackResultsPrompts.compare_test_pass_rate_across_locations()
        for step in ("1.", "2.", "3.", "4."):
            self.assertIn(step, result)

    def test_references_location_status_list(self):
        result = SyntheticTestPlaybackResultsPrompts.compare_test_pass_rate_across_locations()
        self.assertIn("locationStatusList", result)


class TestCheckConsecutiveFailures(unittest.TestCase):

    def test_defaults(self):
        result = SyntheticTestPlaybackResultsPrompts.check_consecutive_failures()
        self.assertIn("(not specified)", result)
        self.assertIn("86400000 (24 hours)", result)

    def test_test_name_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.check_consecutive_failures(
            test_name="assoTest3"
        )
        self.assertIn("assoTest3", result)

    def test_descending_order_specified(self):
        result = SyntheticTestPlaybackResultsPrompts.check_consecutive_failures()
        self.assertIn("DESC", result)

    def test_four_step_workflow(self):
        result = SyntheticTestPlaybackResultsPrompts.check_consecutive_failures()
        for step in ("1.", "2.", "3.", "4."):
            self.assertIn(step, result)

    def test_success_stop_condition_described(self):
        result = SyntheticTestPlaybackResultsPrompts.check_consecutive_failures()
        self.assertIn("metricsStatus=0", result)
        self.assertIn("consecutive failures", result)


class TestAnalyzeTestFailureTrend(unittest.TestCase):

    def test_defaults(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_test_failure_trend()
        self.assertIn("2592000000 (30 days)", result)

    def test_test_name_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_test_failure_trend(
            test_name="test-march3-new"
        )
        self.assertIn("test-march3-new", result)

    def test_location_name_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_test_failure_trend(
            location_name="ap-south-1(Mumbai)"
        )
        self.assertIn("ap-south-1(Mumbai)", result)

    def test_four_trend_classifications_present(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_test_failure_trend()
        for trend in ("CONSISTENT FAILURE", "REGRESSION", "IMPROVING", "INTERMITTENT"):
            self.assertIn(trend, result)

    def test_four_step_workflow(self):
        result = SyntheticTestPlaybackResultsPrompts.analyze_test_failure_trend()
        for step in ("1.", "2.", "3.", "4."):
            self.assertIn(step, result)


class TestFindMostReliableTests(unittest.TestCase):

    def test_defaults(self):
        result = SyntheticTestPlaybackResultsPrompts.find_most_reliable_tests()
        self.assertIn("604800000 (7 days)", result)
        self.assertIn("1 (exclude tests with no runs)", result)

    def test_custom_time_window(self):
        result = SyntheticTestPlaybackResultsPrompts.find_most_reliable_tests(
            time_window_ms=172800000
        )
        self.assertIn("172800000", result)

    def test_custom_min_runs(self):
        result = SyntheticTestPlaybackResultsPrompts.find_most_reliable_tests(min_runs=10)
        self.assertIn("10", result)

    def test_perfect_reliability_condition_described(self):
        result = SyntheticTestPlaybackResultsPrompts.find_most_reliable_tests()
        self.assertIn("successRate=1.0", result)

    def test_three_step_workflow(self):
        result = SyntheticTestPlaybackResultsPrompts.find_most_reliable_tests()
        for step in ("1.", "2.", "3."):
            self.assertIn(step, result)


class TestRankTestsByFailureRate(unittest.TestCase):

    def test_defaults(self):
        result = SyntheticTestPlaybackResultsPrompts.rank_tests_by_failure_rate()
        self.assertIn("86400000 (24 hours)", result)
        self.assertIn("20", result)
        self.assertIn("ASC (worst first)", result)

    def test_custom_limit(self):
        result = SyntheticTestPlaybackResultsPrompts.rank_tests_by_failure_rate(limit=5)
        self.assertIn("5", result)

    def test_custom_order(self):
        result = SyntheticTestPlaybackResultsPrompts.rank_tests_by_failure_rate(order="DESC")
        self.assertIn("DESC", result)

    def test_weighted_rate_formula_described(self):
        result = SyntheticTestPlaybackResultsPrompts.rank_tests_by_failure_rate()
        self.assertIn("weighted_rate", result)
        self.assertIn("successRuns", result)
        self.assertIn("totalTestRuns", result)

    def test_three_step_workflow(self):
        result = SyntheticTestPlaybackResultsPrompts.rank_tests_by_failure_rate()
        for step in ("1.", "2.", "3."):
            self.assertIn(step, result)


class TestCheckTestPerLocationFailure(unittest.TestCase):

    def test_defaults(self):
        result = SyntheticTestPlaybackResultsPrompts.check_test_per_location_failure()
        self.assertIn("(not specified)", result)
        self.assertIn("3600000 (1 hour)", result)

    def test_test_name_interpolated(self):
        result = SyntheticTestPlaybackResultsPrompts.check_test_per_location_failure(
            test_name="DNS-all-stans-demo-one-updated"
        )
        self.assertIn("DNS-all-stans-demo-one-updated", result)

    def test_three_verdict_cases_described(self):
        result = SyntheticTestPlaybackResultsPrompts.check_test_per_location_failure()
        self.assertIn("Failing on ALL locations", result)
        self.assertIn("Failing on SPECIFIC locations", result)
        self.assertIn("Passing everywhere", result)

    def test_three_step_workflow(self):
        result = SyntheticTestPlaybackResultsPrompts.check_test_per_location_failure()
        for step in ("1.", "2.", "3."):
            self.assertIn(step, result)


class TestSyntheticTestPlaybackResultsPromptsIntegration(unittest.TestCase):
    """Integration-level checks across the whole class."""

    def test_class_usable_without_instantiation(self):
        prompts = SyntheticTestPlaybackResultsPrompts.get_prompts()
        self.assertGreater(len(prompts), 0)

    def test_get_prompts_idempotent(self):
        p1 = SyntheticTestPlaybackResultsPrompts.get_prompts()
        p2 = SyntheticTestPlaybackResultsPrompts.get_prompts()
        self.assertEqual([n for n, _ in p1], [n for n, _ in p2])

    def test_cross_reference_group_completeness(self):
        names = {p[0] for p in SyntheticTestPlaybackResultsPrompts.get_prompts()}
        cross_ref = {
            "get_failing_tests_by_location_label",
            "get_tests_linked_to_location_with_success_rates",
            "get_online_datacenters_with_failures",
            "get_managed_fleet_health_score",
            "get_location_health_overview",
            "check_location_full_outage",
            "check_failure_concentration",
        }
        for name in cross_ref:
            self.assertIn(name, names)

    def test_temporal_release_group_completeness(self):
        names = {p[0] for p in SyntheticTestPlaybackResultsPrompts.get_prompts()}
        temporal = {
            "analyze_synthetic_failure_rate_after_release",
            "find_first_failure_timestamp",
            "compare_test_pass_rate_across_locations",
            "check_consecutive_failures",
            "analyze_test_failure_trend",
            "find_most_reliable_tests",
            "rank_tests_by_failure_rate",
            "check_test_per_location_failure",
        }
        for name in temporal:
            self.assertIn(name, names)

    def test_every_prompt_output_is_string(self):
        """All prompts with no required args must return a non-empty string."""
        no_arg_prompts = [
            SyntheticTestPlaybackResultsPrompts.get_failing_tests_by_location_label,
            SyntheticTestPlaybackResultsPrompts.get_online_datacenters_with_failures,
            SyntheticTestPlaybackResultsPrompts.get_managed_fleet_health_score,
            SyntheticTestPlaybackResultsPrompts.get_location_health_overview,
            SyntheticTestPlaybackResultsPrompts.check_location_full_outage,
            SyntheticTestPlaybackResultsPrompts.check_failure_concentration,
            SyntheticTestPlaybackResultsPrompts.analyze_synthetic_failure_rate_after_release,
            SyntheticTestPlaybackResultsPrompts.find_first_failure_timestamp,
            SyntheticTestPlaybackResultsPrompts.compare_test_pass_rate_across_locations,
            SyntheticTestPlaybackResultsPrompts.check_consecutive_failures,
            SyntheticTestPlaybackResultsPrompts.analyze_test_failure_trend,
            SyntheticTestPlaybackResultsPrompts.find_most_reliable_tests,
            SyntheticTestPlaybackResultsPrompts.rank_tests_by_failure_rate,
            SyntheticTestPlaybackResultsPrompts.check_test_per_location_failure,
        ]
        for func in no_arg_prompts:
            result = func()
            self.assertIsInstance(result, str, f"{func.__name__} did not return a string")
            self.assertTrue(result.strip(), f"{func.__name__} returned an empty string")

    def test_prompts_with_required_location_id_return_string(self):
        result = SyntheticTestPlaybackResultsPrompts.get_tests_linked_to_location_with_success_rates(
            location_id="test-loc-id"
        )
        self.assertIsInstance(result, str)
        self.assertTrue(result.strip())


if __name__ == "__main__":
    unittest.main()
