from typing import Optional

from src.prompts import auto_register_prompt


class SyntheticTestPlaybackResultsPrompts:
    """
    Multi-step synthetic monitoring prompts that require two or more sequential
    tool calls, covering:
      - Cross-referencing test playback data with location metadata
      - Temporal / release correlation across multiple time windows
    """

    @auto_register_prompt
    @staticmethod
    def get_failing_tests_by_location_label(
        location_label: Optional[str] = None,
        location_id: Optional[str] = None,
        time_window_ms: Optional[int] = None,
    ) -> str:
        return f"""
        Failing synthetic tests for a location:
        - location_label: {location_label or '(not specified)'}
        - location_id: {location_id or '(not specified — resolve from location_label)'}
        - time_window_ms: {time_window_ms or '3600000 (1 hour)'}

        Steps:
        1. If location_id not provided: call settings/get_locations, match location_label case-insensitively against label/displayLabel, extract id
        2. Call test_playback/get_test_summary_list for the time window (pageSize=20)
        3. For each test result inspect locationStatusList — keep entries where locationId matches AND successRate < 1.0; report test label, locationDisplayLabel, successRate, totalTestRuns, successRuns
        """

    @auto_register_prompt
    @staticmethod
    def get_tests_linked_to_location_with_success_rates(
        location_id: str,
        time_window_ms: Optional[int] = None,
    ) -> str:
        return f"""
        Synthetic tests running in a location with their success rates:
        - location_id: {location_id}
        - time_window_ms: {time_window_ms or '3600000 (1 hour)'}

        Steps:
        1. Call settings/get_synthetic_tests with location_id="{location_id}" — collect test ids and labels
        2. Call test_playback/get_test_summary_list for the time window (pageSize=20)
        3. For each test from Step 1, find its summary entry and extract successRate and totalTestRuns from the locationStatusList entry where locationId="{location_id}"; report test label, successRate, totalTestRuns, successRuns
        """

    @auto_register_prompt
    @staticmethod
    def get_online_datacenters_with_failures() -> str:
        return """
        Online Managed datacenters that have failing synthetic tests:

        Steps:
        1. Call settings/get_all_datacenters with status="Online" — collect all location ids and displayLabels
        2. Call test_playback/get_test_summary_list for the last hour (pageSize=20)
        3. For each datacenter cross-reference its locationStatusList entries (locationType="Managed"): FAILING if any successRate < 1.0, PASSING if all = 1.0, NO DATA if no entries; report failing datacenters (displayLabel, lowest successRate, failing test names), passing datacenters, and no-data datacenters
        """

    @auto_register_prompt
    @staticmethod
    def get_managed_fleet_health_score(time_window_ms: Optional[int] = None) -> str:
        return f"""
        Managed fleet health score:
        - time_window_ms: {time_window_ms or '3600000 (1 hour)'}

        Steps:
        1. Call settings/get_all_datacenters with status="Online" — store total_online as denominator N
        2. Call test_playback/get_test_summary_list for the time window (pageSize=20) — each item has locationStatusList
        3. For each datacenter: collect locationStatusList entries where locationType="Managed"; PASS if ALL have successRate=1.0, FAIL if ANY < 1.0, UNKNOWN if no entries
        4. fleet_health_score = count(PASS) / N x 100 - report headline score, failing datacenters (with lowest successRate), passing datacenters, and unknowns

        Note: Each datacenter is binary PASS or FAIL — do NOT average successRates or use sum(successRuns)/sum(totalTestRuns).
        """

    @auto_register_prompt
    @staticmethod
    def get_location_health_overview(time_window_ms: Optional[int] = None) -> str:
        return f"""
        Health status for every synthetic monitoring location:
        - time_window_ms: {time_window_ms or '3600000 (1 hour)'}

        Steps:
        1. Call settings/get_locations — collect id, displayLabel, locationType, status for every location
        2. Call test_playback/get_test_summary_list for the time window (pageSize=20) — build a map of locationId → average successRate across all tests at that location
        3. Classify each location: HEALTHY (=1.0), DEGRADED (0 < rate < 1.0), FAILING (=0.0), NO DATA; report grouped by classification with displayLabel, locationType, infrastructure status, and successRate
        """

    @auto_register_prompt
    @staticmethod
    def check_location_full_outage(time_window_ms: Optional[int] = None) -> str:
        return f"""
        Detect full location outages across synthetic monitoring datacenters:
        - time_window_ms: {time_window_ms or '3600000 (1 hour)'}

        Steps:
        1. Call settings/get_all_datacenters with status="Online" — collect all location ids and displayLabels
        2. Call test_playback/get_test_summary_list for the time window (pageSize=20)
        3. For each datacenter collect locationStatusList entries (locationType="Managed"): full outage = ≥1 entry AND all successRate=0.0; partial outage = some 0.0, some not; report full-outage datacenters (displayLabel, failing test names, totalTestRuns), partial-outage datacenters, and no answer if none found

        Note: Full outage means every test at the datacenter has successRate = 0.0.
        """

    @auto_register_prompt
    @staticmethod
    def check_failure_concentration(time_window_ms: Optional[int] = None) -> str:
        return f"""
        Whether synthetic test failures are concentrated on specific locations or widespread:
        - time_window_ms: {time_window_ms or '3600000 (1 hour)'}

        Steps:
        1. Call settings/get_locations — build a map of locationId → (locationType, displayLabel)
        2. Call test_playback/get_test_summary_list for the time window (pageSize=20) — accumulate total runs and failed runs (totalTestRuns - successRuns) per locationId across all tests
        3. Tally failures by Managed vs Private; identify if failures share a common locationId (concentrated) or span many (widespread); report top 5 locations by failure count (displayLabel, locationType), verdict, and which location type accounts for more failures
        """

    @auto_register_prompt
    @staticmethod
    def analyze_synthetic_failure_rate_after_release(
        release_name: Optional[str] = None,
        release_id: Optional[str] = None,
        comparison_window_ms: Optional[int] = None,
    ) -> str:
        if release_name and not release_id:
            lookup_instruction = f"Find the release by name using get_all_releases with name_filter='{release_name}'"
        elif release_id:
            lookup_instruction = f"Fetch release details directly using release_id='{release_id}'"
        else:
            lookup_instruction = "ERROR: supply either release_name or release_id"

        return f"""
        Synthetic test failure rates before and after a release:
        - release_name: {release_name or '(not specified)'}
        - release_id: {release_id or '(not specified)'}
        - comparison_window_ms: {comparison_window_ms or '3600000 (1 hour each side)'}

        Steps:
        1. {lookup_instruction} — extract release_start (Unix ms)
        2. Call test_playback/get_test_summary_list with timeFrame.to=release_start and the comparison window — record per-test successRate as pre_rate
        3. Call test_playback/get_test_summary_list with timeFrame.to=release_start + comparison_window — record per-test successRate as post_rate
        4. For each test compute delta = post_rate - pre_rate; report tests where rate went DOWN (delta < 0, failure rate increased), UP (delta > 0, failure rate decreased), or unchanged, and overall verdict

        Note: If both release_name and release_id are provided, release_id takes precedence.
        """

    @auto_register_prompt
    @staticmethod
    def find_first_failure_timestamp(
        test_name: Optional[str] = None,
        test_id: Optional[str] = None,
        location_name: Optional[str] = None,
        location_id: Optional[str] = None,
        search_window_ms: Optional[int] = None,
    ) -> str:
        return f"""
        First failure timestamp for a synthetic test at a specific location:
        - test_name: {test_name or '(not specified)'}
        - test_id: {test_id or '(not specified — resolve from test_name)'}
        - location_name: {location_name or '(not specified)'}
        - location_id: {location_id or '(not specified — resolve from location_name)'}
        - search_window_ms: {search_window_ms or '86400000 (24 hours)'}

        Steps:
        1. If test_id not provided: call settings/get_synthetic_tests, match test_name case-insensitively against label, extract id
        2. If location_id not provided: call settings/get_locations, match location_name against label/displayLabel, extract id
        3. Call test_playback/get_synthetic_result_list ordered ASC by start_time, filtered by testId and locationId, metrics: metricsStatus, startTime, errors
        4. Scan runs oldest-first; find earliest run where metricsStatus != 0 - report test label, location displayLabel, first failure timestamp (ISO), duration broken (now - first_failure_time), and error message
        """

    @auto_register_prompt
    @staticmethod
    def compare_test_pass_rate_across_locations(
        test_name: Optional[str] = None,
        test_id: Optional[str] = None,
        location_names: Optional[list] = None,
        time_window_ms: Optional[int] = None,
    ) -> str:
        return f"""
        A synthetic test's pass rate compared across locations:
        - test_name: {test_name or '(not specified)'}
        - test_id: {test_id or '(not specified — resolve from test_name)'}
        - location_names: {location_names or '(not specified — compare all locations)'}
        - time_window_ms: {time_window_ms or '604800000 (7 days)'}

        Steps:
        1. If test_id not provided: call settings/get_synthetic_tests, match test_name against label (case-insensitive), extract id
        2. If location_names provided: call settings/get_locations, match each name against label/displayLabel, build a map of name → locationId
        3. Call test_playback/get_test_summary_list for the time window (pageSize=20) — find the matching test entry and extract its locationStatusList
        4. For each target location (or all if none specified) extract successRate, totalTestRuns, successRuns; report per-location breakdown and identify most/least reliable location
        """

    @auto_register_prompt
    @staticmethod
    def check_consecutive_failures(
        test_name: Optional[str] = None,
        test_id: Optional[str] = None,
        time_window_ms: Optional[int] = None,
    ) -> str:
        return f"""
        Consecutive failure count for a synthetic test:
        - test_name: {test_name or '(not specified)'}
        - test_id: {test_id or '(not specified — resolve from test_name)'}
        - time_window_ms: {time_window_ms or '86400000 (24 hours)'}

        Steps:
        1. If test_id not provided: call settings/get_synthetic_tests, match test_name against label (case-insensitive), extract id
        2. Call test_playback/get_synthetic_result_list ordered DESC by start_time, filtered by testId, metrics: metricsStatus, startTime, errors
        3. Iterate runs newest-to-oldest; count leading failures (stop at first metricsStatus=0)
        4. Report total consecutive failures, streak duration, whether it is a prolonged outage (>5), last successful run timestamp, and sample error messages
        """

    @auto_register_prompt
    @staticmethod
    def analyze_test_failure_trend(
        test_name: Optional[str] = None,
        test_id: Optional[str] = None,
        location_name: Optional[str] = None,
        location_id: Optional[str] = None,
        time_window_ms: Optional[int] = None,
    ) -> str:
        return f"""
        Failure trend for a synthetic test over a time window:
        - test_name: {test_name or '(not specified)'}
        - test_id: {test_id or '(not specified — resolve from test_name)'}
        - location_name: {location_name or '(not specified — analyse across all locations)'}
        - location_id: {location_id or '(not specified)'}
        - time_window_ms: {time_window_ms or '2592000000 (30 days)'}

        Steps:
        1. If test_id not provided: call settings/get_synthetic_tests, match test_name against label, extract id; if location_id not provided: call settings/get_locations, match location_name, extract id
        2. Call test_playback/get_synthetic_result_list ordered ASC by start_time, filtered by testId (and locationId if provided), metrics: metricsStatus, startTime (pageSize=20)
        3. Group runs by calendar day (UTC); compute daily_failure_rate = failed_runs / total_runs (metricsStatus != 0 = failure)
        4. Compare first-half vs second-half average to classify: CONSISTENT FAILURE (>0.9 throughout), REGRESSION (low→high), IMPROVING (high→low), INTERMITTENT (mixed); report daily failure rate table, trend classification, and notable spikes
        """

    @auto_register_prompt
    @staticmethod
    def find_most_reliable_tests(
        time_window_ms: Optional[int] = None,
        min_runs: Optional[int] = None,
    ) -> str:
        return f"""
        Synthetic tests with zero failures across all locations:
        - time_window_ms: {time_window_ms or '604800000 (7 days)'}
        - min_runs: {min_runs or '1 (exclude tests with no runs)'}

        Steps:
        1. Call test_playback/get_test_summary_list for the time window (pageSize=20)
        2. For each test check all locationStatusList entries: perfectly reliable = every entry successRate=1.0 AND sum(totalTestRuns) >= {min_runs or 1}
        3. List all perfectly reliable tests (label, total runs, locations); also list top 5 most reliable non-perfect tests by successRate descending
        """

    @auto_register_prompt
    @staticmethod
    def rank_tests_by_failure_rate(
        time_window_ms: Optional[int] = None,
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> str:
        return f"""
        Synthetic tests ranked by failure rate:
        - time_window_ms: {time_window_ms or '86400000 (24 hours)'}
        - limit: {limit or '20'}
        - order: {order or 'ASC (worst first)'}

        Steps:
        1. Call test_playback/get_test_summary_list for the time window (pageSize=20)
        2. For each test compute weighted_rate = sum(successRuns) / sum(totalTestRuns) across all locationStatusList entries
        3. Sort by weighted_rate in {order or 'ASC'} order and return top {limit or 20}; report rank, test label, weighted successRate, total runs, and failing locations
        """

    @auto_register_prompt
    @staticmethod
    def check_test_per_location_failure(
        test_name: Optional[str] = None,
        test_id: Optional[str] = None,
        time_window_ms: Optional[int] = None,
    ) -> str:
        return f"""
        Whether a synthetic test is failing on all locations or only specific ones:
        - test_name: {test_name or '(not specified)'}
        - test_id: {test_id or '(not specified — resolve from test_name)'}
        - time_window_ms: {time_window_ms or '3600000 (1 hour)'}

        Steps:
        1. If test_id not provided: call settings/get_synthetic_tests, match test_name against label (case-insensitive), extract id
        2. Call test_playback/get_test_summary_list for the time window (pageSize=20) — find the matching test entry and extract its locationStatusList
        3. Classify: "Failing on ALL locations" if all successRate < 1.0, "Failing on SPECIFIC locations" if only some fail (list them), "Passing everywhere" if all = 1.0; report per-location breakdown with locationDisplayLabel, successRate, totalTestRuns, successRuns
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            # Cross-reference prompts
            ('get_failing_tests_by_location_label', cls.get_failing_tests_by_location_label),
            ('get_tests_linked_to_location_with_success_rates', cls.get_tests_linked_to_location_with_success_rates),
            ('get_online_datacenters_with_failures', cls.get_online_datacenters_with_failures),
            ('get_managed_fleet_health_score', cls.get_managed_fleet_health_score),
            ('get_location_health_overview', cls.get_location_health_overview),
            ('check_location_full_outage', cls.check_location_full_outage),
            ('check_failure_concentration', cls.check_failure_concentration),
            # Temporal / release correlation prompts
            ('analyze_synthetic_failure_rate_after_release', cls.analyze_synthetic_failure_rate_after_release),
            ('find_first_failure_timestamp', cls.find_first_failure_timestamp),
            ('compare_test_pass_rate_across_locations', cls.compare_test_pass_rate_across_locations),
            ('check_consecutive_failures', cls.check_consecutive_failures),
            ('analyze_test_failure_trend', cls.analyze_test_failure_trend),
            ('find_most_reliable_tests', cls.find_most_reliable_tests),
            ('rank_tests_by_failure_rate', cls.rank_tests_by_failure_rate),
            ('check_test_per_location_failure', cls.check_test_per_location_failure),
        ]
