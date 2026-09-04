"""
Unit tests for SLO Report MCP Tools.

Tests the SLOReportMCPTools which manages SLO reports.
"""

import asyncio
import json
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level
logging.basicConfig(level=logging.ERROR)

# Get the SLO logger and replace its handlers
slo_logger = logging.getLogger('src.slo.slo_report')
slo_logger.handlers = []
slo_logger.addHandler(NullHandler())
slo_logger.propagate = False

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            for attr_name in ("report_api", "slo_config_api", "alert_config_api", "correction_api"):
                api_client = getattr(self, attr_name, None)
                if api_client is not None:
                    kwargs["api_client"] = api_client
                    break
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.service_levels_objective_slo_report_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client_class = MagicMock()
mock_report_api = MagicMock()

mock_report_api.__name__ = "ServiceLevelsObjectiveSLOReportApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client_class
sys.modules['instana_client.api.service_levels_objective_slo_report_api'].ServiceLevelsObjectiveSLOReportApi = mock_report_api

# Import with patched decorator
import src.core.utils

original_with_header_auth = src.core.utils.with_header_auth
src.core.utils.with_header_auth = mock_with_header_auth

from src.slo.slo_report import SLOReportMCPTools

# Restore original decorator
src.core.utils.with_header_auth = original_with_header_auth


class TestSLOReportMCPTools(unittest.TestCase):
    """Test cases for SLO Report MCP Tools."""

    def setUp(self):
        """Set up test fixtures."""
        mock_configuration.reset_mock()
        mock_api_client_class.reset_mock()
        mock_report_api.reset_mock()

        self.client = SLOReportMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com"
        )

        self.mock_api = MagicMock()
        self.client.report_api = self.mock_api

    def test_initialization(self):
        """Test client initialization."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.com")

    def test_clean_slo_report_data(self):
        """Test cleaning SLO report data."""
        report = {
            "sli": 0.98,
            "slo": 0.95,
            "fromTimestamp": 1609459200000,
            "toTimestamp": 1612137600000,
            "errorBudgetRemaining": 0.02,
            "errorBudgetSpent": 0.01,
            "totalErrorBudget": 0.05,
            "errorBurnRate": 1.5,
            "errorChart": [{"timestamp": 1609459200000, "value": 0.01}],
            "extraField": "should be removed"
        }
        cleaned = self.client._clean_slo_report_data(report)
        self.assertIn("sli", cleaned)
        self.assertIn("slo", cleaned)
        self.assertIn("errorBudgetRemaining", cleaned)
        self.assertIn("errorChart", cleaned)
        self.assertNotIn("extraField", cleaned)

    def test_clean_slo_report_data_with_all_charts(self):
        """Test cleaning SLO report data with all chart types."""
        report = {
            "sli": 0.98,
            "slo": 0.95,
            "fromTimestamp": 1609459200000,
            "toTimestamp": 1612137600000,
            "errorBudgetRemaining": 0.02,
            "errorBudgetSpent": 0.01,
            "totalErrorBudget": 0.05,
            "errorBurnRate": 1.5,
            "errorChart": [{"timestamp": 1609459200000, "value": 0.01}],
            "errorBudgetRemainChart": [{"timestamp": 1609459200000, "value": 0.02}],
            "errorBurnRateChart": [{"timestamp": 1609459200000, "value": 1.5}],
            "violationDistribution": [{"type": "latency", "count": 5}],
            "errorAccumulationChart": [{"timestamp": 1609459200000, "value": 0.01}]
        }
        cleaned = self.client._clean_slo_report_data(report)
        self.assertIn("errorChart", cleaned)
        self.assertIn("errorBudgetRemainChart", cleaned)
        self.assertIn("errorBurnRateChart", cleaned)
        self.assertIn("violationDistribution", cleaned)
        self.assertIn("errorAccumulationChart", cleaned)

    def test_clean_slo_report_data_without_charts(self):
        """Test cleaning SLO report data without optional charts."""
        report = {
            "sli": 0.98,
            "slo": 0.95,
            "fromTimestamp": 1609459200000,
            "toTimestamp": 1612137600000,
            "errorBudgetRemaining": 0.02,
            "errorBudgetSpent": 0.01,
            "totalErrorBudget": 0.05,
            "errorBurnRate": 1.5
        }
        cleaned = self.client._clean_slo_report_data(report)
        self.assertIn("sli", cleaned)
        self.assertIn("slo", cleaned)
        self.assertNotIn("errorChart", cleaned)
        self.assertNotIn("errorBudgetRemainChart", cleaned)

    # get_slo_report Tests
    def test_get_slo_report_missing_slo_id(self):
        """Test getting SLO report with missing slo_id."""
        async def run_test():
            result = await self.client.get_slo_report(slo_id=None)
            self.assertIn("error", result)
            self.assertIn("required", result["error"])

        asyncio.run(run_test())

    def test_get_slo_report_success(self):
        """Test getting SLO report successfully."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([
                {
                    "sli": 0.98,
                    "slo": 0.95,
                    "fromTimestamp": 1609459200000,
                    "toTimestamp": 1612137600000,
                    "errorBudgetRemaining": 0.02,
                    "errorBudgetSpent": 0.01,
                    "totalErrorBudget": 0.05,
                    "errorBurnRate": 1.5
                }
            ]).encode('utf-8')

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertIn("reports", result)
            self.assertEqual(len(result["reports"]), 1)
            self.assertEqual(result["count"], 1)

        asyncio.run(run_test())

    def test_get_slo_report_with_time_range(self):
        """Test getting SLO report with time range."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([
                {
                    "sli": 0.98,
                    "slo": 0.95,
                    "fromTimestamp": 1609459200000,
                    "toTimestamp": 1612137600000,
                    "errorBudgetRemaining": 0.02
                }
            ]).encode('utf-8')

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(
                slo_id="slo-123",
                var_from="1609459200000",
                to="1612137600000"
            )

            self.assertIn("success", result)
            self.assertEqual(len(result["reports"]), 1)

        asyncio.run(run_test())

    def test_get_slo_report_with_correction_filters(self):
        """Test getting SLO report with correction filters."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([
                {
                    "sli": 0.98,
                    "slo": 0.95,
                    "errorBudgetRemaining": 0.02
                }
            ]).encode('utf-8')

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(
                slo_id="slo-123",
                exclude_correction_id=["corr-1"],
                include_correction_id=["corr-2"]
            )

            self.assertIn("success", result)

        asyncio.run(run_test())

    def test_get_slo_report_empty_list(self):
        """Test getting SLO report with empty result."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([]).encode('utf-8')

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertEqual(result["count"], 0)
            self.assertIn("No reports found", result["message"])

        asyncio.run(run_test())

    def test_get_slo_report_api_error(self):
        """Test getting SLO report with API error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 404
            mock_response.data = b"Not found"

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertIn("error", result)
            self.assertIn("status", result["error"])

        asyncio.run(run_test())

    def test_get_slo_report_empty_response(self):
        """Test getting SLO report with empty response."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = b""

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertIn("error", result)
            self.assertIn("Empty response", result["error"])

        asyncio.run(run_test())

    def test_get_slo_report_json_parse_error(self):
        """Test getting SLO report with JSON parse error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = b"invalid json"

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertIn("error", result)
            self.assertIn("parse", result["error"])

        asyncio.run(run_test())

    def test_get_slo_report_non_list_response(self):
        """Test getting SLO report with non-list response."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"error": "Invalid format"}).encode('utf-8')

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertIn("success", result)
            self.assertEqual(result["count"], 0)
            self.assertIn("Unexpected response format", result["message"])

        asyncio.run(run_test())

    def test_get_slo_report_single_dict_response(self):
        """Test getting SLO report when API returns a single dict (not a list)."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({
                "sli": 0.916,
                "slo": 0.99,
                "totalErrorBudget": 101,
                "errorBudgetRemaining": -741,
                "errorBudgetSpent": 842,
                "errorBurnRate": 8,
                "fromTimestamp": 1787316720000,
                "toTimestamp": 1787921520000,
            }).encode('utf-8')

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertTrue(result["success"])
            self.assertEqual(result["count"], 1)
            self.assertEqual(len(result["reports"]), 1)
            report = result["reports"][0]
            self.assertAlmostEqual(report["sli"], 0.916)
            self.assertAlmostEqual(report["slo"], 0.99)
            self.assertEqual(report["errorBurnRate"], 8)
            self.assertNotIn("message", result)

        asyncio.run(run_test())

    def test_get_slo_report_multiple_reports(self):
        """Test getting SLO report with multiple reports."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([
                {
                    "sli": 0.98,
                    "slo": 0.95,
                    "errorBudgetRemaining": 0.02
                },
                {
                    "sli": 0.97,
                    "slo": 0.95,
                    "errorBudgetRemaining": 0.03
                },
                {
                    "sli": 0.96,
                    "slo": 0.95,
                    "errorBudgetRemaining": 0.04
                }
            ]).encode('utf-8')

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertIn("success", result)
            self.assertEqual(result["count"], 3)
            self.assertEqual(len(result["reports"]), 3)

        asyncio.run(run_test())

    def test_get_slo_report_exception(self):
        """Test getting SLO report with exception."""
        async def run_test():
            self.mock_api.get_slo_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertIn("error", result)
            self.assertIn("Failed to get SLO report", result["error"])

        asyncio.run(run_test())

    def test_get_slo_report_with_all_parameters(self):
        """Test getting SLO report with all parameters."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([
                {
                    "sli": 0.98,
                    "slo": 0.95,
                    "fromTimestamp": 1609459200000,
                    "toTimestamp": 1612137600000,
                    "errorBudgetRemaining": 0.02,
                    "errorBudgetSpent": 0.01,
                    "totalErrorBudget": 0.05,
                    "errorBurnRate": 1.5,
                    "errorChart": [{"timestamp": 1609459200000, "value": 0.01}],
                    "errorBudgetRemainChart": [{"timestamp": 1609459200000, "value": 0.02}],
                    "errorBurnRateChart": [{"timestamp": 1609459200000, "value": 1.5}],
                    "violationDistribution": [{"type": "latency", "count": 5}],
                    "errorAccumulationChart": [{"timestamp": 1609459200000, "value": 0.01}]
                }
            ]).encode('utf-8')

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(
                slo_id="slo-123",
                var_from="1609459200000",
                to="1612137600000",
                exclude_correction_id=["corr-1"],
                include_correction_id=["corr-2"]
            )

            self.assertIn("success", result)
            self.assertEqual(len(result["reports"]), 1)
            # Verify all chart data is included
            report = result["reports"][0]
            self.assertIn("errorChart", report)
            self.assertIn("errorBudgetRemainChart", report)
            self.assertIn("errorBurnRateChart", report)
            self.assertIn("violationDistribution", report)
            self.assertIn("errorAccumulationChart", report)

        asyncio.run(run_test())

    def test_get_slo_report_status_code_in_response(self):
        """Test that status code is included in response."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([
                {"sli": 0.98, "slo": 0.95}
            ]).encode('utf-8')

            self.mock_api.get_slo_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_report(slo_id="slo-123")

            self.assertIn("status_code", result)
            self.assertEqual(result["status_code"], 200)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()

