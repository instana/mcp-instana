"""
Unit tests for metric compatibility validation (pure functions, no I/O).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.metric_validation import (
    validate_beacon_type_known,
    validate_metric_compatibility,
)
from src.core.utils import MOBILE_BEACON_TYPE_MAP, WEBSITE_BEACON_TYPE_MAP

SAMPLE_CATALOG = [
    {
        "metricId": "onLoadTime",
        "label": "On Load Time",
        "description": "Page load time",
        "aggregations": ["MEAN", "SUM", "P50", "P75", "P90", "P95", "P98", "P99", "MAX", "MIN"],
        "beaconTypes": ["pageLoad"],
        "formatter": "millis",
    },
    {
        "metricId": "beaconCount",
        "label": "Beacon Count",
        "description": "Number of beacons",
        "aggregations": ["SUM"],
        "beaconTypes": ["pageLoad", "pageChange", "resourceLoad", "custom", "httpRequest", "error"],
        "formatter": "number",
    },
    {
        "metricId": "crashFreeSessionRate",
        "label": "Crash Free Session Rate",
        "description": "Crash free session rate",
        "aggregations": ["MEAN"],
        "beaconTypes": ["crash"],
        "formatter": "percent",
    },
]

MOBILE_CATALOG = [
    {
        "metricId": "beaconCount",
        "label": "Beacon Count",
        "description": "Number of beacons",
        "aggregations": ["SUM"],
        "beaconTypes": ["sessionStart", "viewChange", "httpRequest", "custom", "crash", "perf", "dropBeacon"],
        "formatter": "number",
    },
    {
        "metricId": "sessionDuration",
        "label": "Session Duration",
        "description": "Session duration",
        "aggregations": ["MEAN", "P50", "P90", "MAX"],
        "beaconTypes": ["sessionStart"],
        "formatter": "millis",
    },
]


class TestValidateBeaconTypeKnown(unittest.TestCase):

    def test_known_website_beacon_type(self):
        result = validate_beacon_type_known("PAGELOAD", WEBSITE_BEACON_TYPE_MAP)
        self.assertIsNone(result)

    def test_page_change_uses_canonical_request_value(self):
        result = validate_beacon_type_known("PAGE_CHANGE", WEBSITE_BEACON_TYPE_MAP)
        self.assertIsNone(result)

    def test_legacy_pagechange_is_rejected(self):
        result = validate_beacon_type_known("PAGECHANGE", WEBSITE_BEACON_TYPE_MAP)
        self.assertIsNotNone(result)
        self.assertIn("PAGE_CHANGE", str(result["api_error"]))

    def test_known_mobile_beacon_type(self):
        result = validate_beacon_type_known("SESSION_START", MOBILE_BEACON_TYPE_MAP)
        self.assertIsNone(result)

    def test_unknown_beacon_type_returns_elicitation(self):
        result = validate_beacon_type_known("FOOBAR", WEBSITE_BEACON_TYPE_MAP)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("FOOBAR", result["reason"])
        self.assertIn("PAGELOAD", str(result["api_error"]))

    def test_unknown_mobile_beacon_type_lists_mobile_values(self):
        result = validate_beacon_type_known("INVALID", MOBILE_BEACON_TYPE_MAP)
        self.assertIsNotNone(result)
        self.assertIn("SESSION_START", str(result["api_error"]))
        self.assertIn("CRASH", str(result["api_error"]))

    def test_case_insensitive(self):
        result = validate_beacon_type_known("pageload", WEBSITE_BEACON_TYPE_MAP)
        self.assertIsNone(result)


class TestValidateMetricCompatibility(unittest.TestCase):

    def test_valid_metric_returns_none(self):
        metrics = [{"metric": "onLoadTime", "aggregation": "MEAN"}]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNone(result)

    def test_metric_not_found(self):
        metrics = [{"metric": "fakeMetric", "aggregation": "SUM"}]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("fakeMetric", result["api_error"][0])
        self.assertIn("not found", result["api_error"][0])

    def test_beacon_type_incompatible(self):
        metrics = [{"metric": "onLoadTime", "aggregation": "MEAN"}]
        result = validate_metric_compatibility(
            metrics, "ERROR", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("incompatible", result["api_error"][0])
        # Valid beacon types should be in UPPER_SNAKE display format
        self.assertIn("PAGELOAD", str(result["api_error"][0]))

    def test_aggregation_incompatible(self):
        metrics = [{"metric": "onLoadTime", "aggregation": "INVALID_AGG"}]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("INVALID_AGG", result["api_error"][0])
        self.assertIn("valid aggregations", result["api_error"][0])

    def test_multiple_errors_collected(self):
        metrics = [
            {"metric": "fakeMetric", "aggregation": "SUM"},
            {"metric": "crashFreeSessionRate", "aggregation": "MEAN"},
        ]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result["api_error"]), 2)
        self.assertIn("2 invalid", result["reason"])

    def test_missing_aggregation_skips_check(self):
        metrics = [{"metric": "onLoadTime"}]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNone(result)

    def test_empty_metrics_list(self):
        result = validate_metric_compatibility(
            [], "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNone(result)

    def test_beacon_type_normalization(self):
        metrics = [{"metric": "beaconCount", "aggregation": "SUM"}]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNone(result)

    def test_malformed_entry_non_dict(self):
        metrics = ["not_a_dict"]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("invalid metric entry", result["api_error"][0])

    def test_malformed_entry_missing_metric_key(self):
        metrics = [{"aggregation": "SUM"}]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNotNone(result)
        self.assertIn("missing required 'metric' field", result["api_error"][0])

    def test_malformed_entry_non_string_metric(self):
        metrics = [{"metric": 12345, "aggregation": "SUM"}]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNotNone(result)
        self.assertIn("missing required 'metric' field", result["api_error"][0])

    def test_response_has_required_action(self):
        metrics = [{"metric": "fakeMetric"}]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertEqual(result["required_action"]["operation"], "get_metrics")

    def test_mobile_domain(self):
        metrics = [{"metric": "sessionDuration", "aggregation": "MEAN"}]
        result = validate_metric_compatibility(
            metrics, "SESSION_START", MOBILE_CATALOG, MOBILE_BEACON_TYPE_MAP,
            "get_mobile_app_metric_catalog",
        )
        self.assertIsNone(result)

    def test_mobile_beacon_type_mismatch(self):
        metrics = [{"metric": "sessionDuration", "aggregation": "MEAN"}]
        result = validate_metric_compatibility(
            metrics, "CRASH", MOBILE_CATALOG, MOBILE_BEACON_TYPE_MAP,
            "get_mobile_app_metric_catalog",
        )
        self.assertIsNotNone(result)
        self.assertIn("incompatible", result["api_error"][0])
        self.assertIn("SESSION_START", str(result["api_error"][0]))

    def test_valid_beacon_types_displayed_in_upper_snake(self):
        metrics = [{"metric": "onLoadTime", "aggregation": "MEAN"}]
        result = validate_metric_compatibility(
            metrics, "ERROR", SAMPLE_CATALOG, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNotNone(result)
        error_msg = result["api_error"][0]
        # Should show PAGELOAD (UPPER_SNAKE), not pageLoad (camelCase)
        self.assertIn("PAGELOAD", error_msg)
        self.assertNotIn("pageLoad", error_msg)


    def test_empty_catalog_aggregations_skips_check(self):
        """Policy: empty catalog aggregations = unavailable metadata, not 'no valid aggregations'.
        Aggregation validation is best-effort; metric existence and beacon-type checks are mandatory."""
        catalog = [
            {
                "metricId": "noAggMetric",
                "label": "No Agg",
                "description": "Metric with empty aggregations",
                "aggregations": [],
                "beaconTypes": ["pageLoad"],
                "formatter": "number",
            },
        ]
        metrics = [{"metric": "noAggMetric", "aggregation": "TOTALLY_BAD"}]
        result = validate_metric_compatibility(
            metrics, "PAGELOAD", catalog, WEBSITE_BEACON_TYPE_MAP,
            "get_metrics",
        )
        self.assertIsNone(result)


class TestValidateBeaconTypeKnownCamelCase(unittest.TestCase):

    def test_camelcase_beacon_type_rejected(self):
        """Catalog-format camelCase values are not valid request-format beacon types."""
        result = validate_beacon_type_known("sessionStart", MOBILE_BEACON_TYPE_MAP)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_camelcase_website_beacon_type_rejected_even_when_uppercase_matches(self):
        """'pageLoad'.upper() = 'PAGELOAD' which IS in the map, but mixed-case
        (camelCase) inputs are rejected to stay consistent with sessionStart/viewChange."""
        result = validate_beacon_type_known("pageLoad", WEBSITE_BEACON_TYPE_MAP)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_camelcase_with_underscore_mismatch_rejected(self):
        """'httpRequest'.upper() = 'HTTPREQUEST' which IS in the map, but
        'viewChange'.upper() = 'VIEWCHANGE' which is NOT 'VIEW_CHANGE'."""
        result = validate_beacon_type_known("viewChange", MOBILE_BEACON_TYPE_MAP)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])


if __name__ == "__main__":
    unittest.main()
