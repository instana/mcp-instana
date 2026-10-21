"""Tests for the SLOPrompts class."""
import sys
import unittest
from unittest.mock import MagicMock

# Mock fastmcp before importing src.prompts
mock_fastmcp = MagicMock()
mock_fastmcp.FastMCP.return_value.prompt.return_value = lambda func: func
sys.modules['fastmcp'] = mock_fastmcp

from src.prompts import PROMPT_REGISTRY
from src.prompts.slo.slo_prompts import SLOPrompts


class TestSLOPrompts(unittest.TestCase):
    """Test cases for the consolidated SLOPrompts class."""

    def test_all_11_prompts_registered(self):
        """Test that all 11 prompt methods are registered in PROMPT_REGISTRY."""
        prompts = SLOPrompts.get_prompts()
        self.assertEqual(len(prompts), 11)
        for name, func in prompts:
            self.assertTrue(
                any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
                f"('{name}', {func}) not found in PROMPT_REGISTRY"
            )

    def test_get_slo_report_full(self):
        res = SLOPrompts.get_slo_report_full(slo_id="slo-123", var_from="1741604400000")
        self.assertIn("slo-123", res)
        self.assertIn("1741604400000", res)

    def test_get_slo_configurations_full(self):
        res = SLOPrompts.get_slo_configurations_full(query="cart", slo_status="breaching")
        self.assertIn("cart", res)
        self.assertIn("BREACHING", res)

    def test_correlate_slo_breach_with_infrastructure(self):
        res = SLOPrompts.correlate_slo_breach_with_infrastructure(tag="prod", infra_type="host")
        self.assertIn("BREACHING", res)
        self.assertIn("prod", res)
        self.assertIn("host", res)

    def test_correlate_slo_breach_with_events(self):
        res = SLOPrompts.correlate_slo_breach_with_events(tag="prod", time_window_hours=2)
        self.assertIn("INCIDENT", res)
        self.assertIn("last 2 hours", res)

    def test_slo_post_release_impact_analysis(self):
        res = SLOPrompts.slo_post_release_impact_analysis(release_id="rel-123")
        self.assertIn("rel-123", res)

    def test_audit_slo_alert_configuration_history(self):
        res = SLOPrompts.audit_slo_alert_configuration_history(slo_id="slo-123")
        self.assertIn("slo-123", res)

    def test_align_correction_windows_with_maintenance(self):
        res = SLOPrompts.align_correction_windows_with_maintenance(slo_id="slo-123")
        self.assertIn("slo-123", res)

    def test_sre_health_overview(self):
        res = SLOPrompts.sre_health_overview(tag="prod", time_window_hours=1)
        self.assertIn("BREACHING", res)
        self.assertIn("prod", res)

    def test_correlate_slo_with_synthetic_tests(self):
        res = SLOPrompts.correlate_slo_with_synthetic_tests(slo_id="slo-123")
        self.assertIn("slo-123", res)

    def test_correlate_slo_with_rum_data(self):
        res = SLOPrompts.correlate_slo_with_rum_data(slo_id="slo-123")
        self.assertIn("slo-123", res)

    def test_slo_error_budget_burn_investigation(self):
        res = SLOPrompts.slo_error_budget_burn_investigation(days=7)
        self.assertIn("availability", res)
