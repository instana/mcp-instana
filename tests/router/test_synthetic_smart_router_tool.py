"""
Unit tests for Synthetic Smart Router Tool.

Tests the SyntheticSmartRouterMCPTool which routes synthetic monitoring
operations to the appropriate specialised sub-clients.
"""

import asyncio
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Suppress noisy log output during test runs
logging.getLogger().addHandler(logging.NullHandler())

# Patch the decorator at import time so the sub-clients can be imported
# without a live instana_client package.
def mock_with_header_auth(func):
    return func

with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.router.synthetic_smart_router_tool import SyntheticSmartRouterMCPTool


class TestSyntheticSmartRouterMCPTool(unittest.TestCase):
    """Test cases for SyntheticSmartRouterMCPTool."""

    def setUp(self):
        """Create a router with all sub-clients replaced by mocks."""
        self.router = SyntheticSmartRouterMCPTool.__new__(SyntheticSmartRouterMCPTool)
        self.router.read_token = "test_token"
        self.router.base_url = "https://test.instana.io"

        self.mock_catalog = MagicMock()
        self.mock_metrics = MagicMock()
        self.mock_settings = MagicMock()
        self.mock_playback = MagicMock()

        self.router.synthetic_catalog_client = self.mock_catalog
        self.router.synthetic_metrics_client = self.mock_metrics
        self.router.synthetic_settings_client = self.mock_settings
        self.router.synthetic_test_playback_client = self.mock_playback

    def test_invalid_resource_type_returns_error(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="unsupported",
            operation="get_synthetic_catalog_metrics"
        ))
        self.assertIn("elicitation_needed", result)
        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(result["reason"], "invalid_resource_type")
        self.assertIn("unsupported", result["api_error"][0]["issue"])

    def test_params_none_defaults_to_empty_dict(self):
        """Passing params=None should not raise; catalog route should work."""
        async def mock_metrics(*args, **kwargs):
            return {"metrics": [], "count": 0}
        self.mock_catalog.get_synthetic_catalog_metrics = mock_metrics

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="catalog",
            operation="get_synthetic_catalog_metrics",
            params=None,
        ))
        self.assertEqual(result["resource_type"], "catalog")

    def test_catalog_get_synthetic_catalog_metrics(self):
        async def mock_fn(*args, **kwargs):
            return {"metrics": [{"metricId": "synthetic.metricsResponseTime"}], "count": 1}
        self.mock_catalog.get_synthetic_catalog_metrics = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="catalog",
            operation="get_synthetic_catalog_metrics",
        ))
        self.assertEqual(result["resource_type"], "catalog")
        self.assertEqual(result["operation"], "get_synthetic_catalog_metrics")
        self.assertIn("results", result)

    def test_catalog_get_synthetic_catalog_metrics_full_view(self):
        """view param should be forwarded to the catalog client."""
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"metrics": [], "count": 0}
        self.mock_catalog.get_synthetic_catalog_metrics = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="catalog",
            operation="get_synthetic_catalog_metrics",
            params={"view": "full"},
        ))
        self.assertEqual(captured.get("view"), "full")

    def test_catalog_get_synthetic_tag_catalog(self):
        async def mock_fn(*args, **kwargs):
            return {"tag_names": ["synthetic.testName", "synthetic.locationId"], "count": 2}
        self.mock_catalog.get_synthetic_tag_catalog = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="catalog",
            operation="get_synthetic_tag_catalog",
            params={"use_case": "FILTERING"},
        ))
        self.assertEqual(result["resource_type"], "catalog")
        self.assertIn("results", result)

    def test_catalog_get_synthetic_tag_catalog_passes_use_case(self):
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"tag_names": [], "count": 0}
        self.mock_catalog.get_synthetic_tag_catalog = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="catalog",
            operation="get_synthetic_tag_catalog",
            params={"use_case": "GROUPING"},
        ))
        self.assertEqual(captured.get("use_case"), "GROUPING")

    def test_catalog_invalid_operation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="catalog",
            operation="nonexistent_operation",
        ))
        self.assertIn("elicitation_needed", result)
        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(result["reason"], "invalid_operation")
        self.assertIn("nonexistent_operation", result["api_error"][0]["issue"])

    def test_metrics_get_metrics_result(self):
        async def mock_fn(*args, **kwargs):
            return {"items": [{"testId": "t1", "metricsResponseTime": 200.0}]}
        self.mock_metrics.get_metrics_result = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="metrics",
            operation="get_metrics_result",
            params={"payload": {
                "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "MEAN"}],
                "timeFrame": {"to": 0, "windowSize": 3600000},
            }},
        ))
        self.assertEqual(result["resource_type"], "metrics")
        self.assertEqual(result["operation"], "get_metrics_result")
        self.assertIn("results", result)

    def test_metrics_payload_forwarded(self):
        """Payload from params should be forwarded to get_metrics_result."""
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {}
        self.mock_metrics.get_metrics_result = mock_fn

        expected_payload = {
            "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}],
            "groups": [{"groupbyTag": "synthetic.locationId", "groupbyTagEntity": "NOT_APPLICABLE", "direction": "DESC"}],
        }
        asyncio.run(self.router.manage_synthetics(
            resource_type="metrics",
            operation="get_metrics_result",
            params={"payload": expected_payload},
        ))
        self.assertEqual(captured.get("payload"), expected_payload)

    def test_settings_get_synthetic_test_by_id(self):
        async def mock_fn(*args, **kwargs):
            return {"id": "test-001", "label": "Login Flow"}
        self.mock_settings.get_synthetic_test = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_synthetic_test",
            params={"test_id": "test-001"},
        ))
        self.assertEqual(result["resource_type"], "settings")
        self.assertIn("results", result)

    def test_settings_get_synthetic_test_by_name(self):
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"id": "test-002", "label": "API Health"}
        self.mock_settings.get_synthetic_test = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_synthetic_test",
            params={"test_name": "API Health"},
        ))
        self.assertEqual(captured.get("test_name"), "API Health")

    def test_settings_get_synthetic_tests(self):
        async def mock_fn(*args, **kwargs):
            return {"items": [{"id": "t1"}, {"id": "t2"}], "count": 2}
        self.mock_settings.get_synthetic_tests = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_synthetic_tests",
            params={"limit": 2, "sort": "+label"},
        ))
        self.assertEqual(result["resource_type"], "settings")
        self.assertEqual(result["operation"], "get_synthetic_tests")

    def test_settings_get_synthetic_tests_forwards_params(self):
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"items": [], "count": 0}
        self.mock_settings.get_synthetic_tests = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_synthetic_tests",
            params={"application_id": "app-1", "location_id": "loc-1", "limit": 5, "sort": "-label"},
        ))
        self.assertEqual(captured.get("application_id"), "app-1")
        self.assertEqual(captured.get("location_id"), "loc-1")
        self.assertEqual(captured.get("limit"), 5)

    def test_settings_get_locations(self):
        async def mock_fn(*args, **kwargs):
            return {"items": [], "count": 0, "filters_applied": {}}
        self.mock_settings.get_locations = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_locations",
        ))
        self.assertEqual(result["resource_type"], "settings")
        self.assertEqual(result["operation"], "get_locations")

    def test_settings_get_locations_forwards_filters(self):
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"items": [], "count": 0}
        self.mock_settings.get_locations = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_locations",
            params={"location_type": "Managed", "status": "Online"},
        ))
        self.assertEqual(captured.get("location_type"), "Managed")
        self.assertEqual(captured.get("status"), "Online")

    def test_settings_get_location_by_id(self):
        async def mock_fn(*args, **kwargs):
            return {"id": "loc-1", "label": "instana-aws-us-east-1"}
        self.mock_settings.get_location_by_id = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_location_by_id",
            params={"location_id": "loc-1"},
        ))
        self.assertEqual(result["resource_type"], "settings")

    def test_settings_get_location_by_name(self):
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"id": "loc-2"}
        self.mock_settings.get_location_by_id = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_location_by_id",
            params={"location_name": "ap-south-1(Mumbai)"},
        ))
        self.assertEqual(captured.get("location_name"), "ap-south-1(Mumbai)")

    def test_settings_get_all_datacenters(self):
        async def mock_fn(*args, **kwargs):
            return {"items": [], "count": 0, "total_online": 0}
        self.mock_settings.get_all_datacenters = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_all_datacenters",
        ))
        self.assertEqual(result["resource_type"], "settings")
        self.assertEqual(result["operation"], "get_all_datacenters")

    def test_settings_get_all_datacenters_status_param(self):
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"items": [], "count": 0, "total_online": 0}
        self.mock_settings.get_all_datacenters = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_all_datacenters",
            params={"status": "Online"},
        ))
        self.assertEqual(captured.get("status"), "Online")

    def test_settings_invalid_operation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="unknown_setting_op",
        ))
        self.assertIn("elicitation_needed", result)
        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(result["reason"], "invalid_operation")
        self.assertIn("unknown_setting_op", result["api_error"][0]["issue"])

    def test_test_playback_get_synthetic_result(self):
        async def mock_execute(*args, **kwargs):
            return {"items": [{"testId": "t1"}]}
        self.mock_playback.execute_playback_operation = mock_execute

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_synthetic_result",
            params={"payload": {"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}},
        ))
        self.assertEqual(result["resource_type"], "test_playback")
        self.assertEqual(result["operation"], "get_synthetic_result")
        self.assertIn("results", result)

    def test_test_playback_get_synthetic_result_analytic(self):
        async def mock_execute(*args, **kwargs):
            return {"items": []}
        self.mock_playback.execute_playback_operation = mock_execute

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_synthetic_result_analytic",
            params={"payload": {"syntheticMetrics": ["synthetic.metricsStatus"], "analyticFunction": "LAST_VALUE"}},
        ))
        self.assertEqual(result["operation"], "get_synthetic_result_analytic")

    def test_test_playback_get_synthetic_result_list(self):
        async def mock_execute(*args, **kwargs):
            return {"items": []}
        self.mock_playback.execute_playback_operation = mock_execute

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_synthetic_result_list",
            params={"payload": {"syntheticMetrics": ["synthetic.metricsStatus"]}},
        ))
        self.assertEqual(result["operation"], "get_synthetic_result_list")

    def test_test_playback_get_location_summary_list(self):
        async def mock_execute(*args, **kwargs):
            return {"items": []}
        self.mock_playback.execute_playback_operation = mock_execute

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_location_summary_list",
            params={"payload": {"timeFrame": {"to": None, "windowSize": 300000}}},
        ))
        self.assertEqual(result["operation"], "get_location_summary_list")

    def test_test_playback_get_test_summary_list(self):
        async def mock_execute(*args, **kwargs):
            return {"items": []}
        self.mock_playback.execute_playback_operation = mock_execute

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_test_summary_list",
            params={"payload": {"metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}]}},
        ))
        self.assertEqual(result["operation"], "get_test_summary_list")

    def test_test_playback_get_synthetic_result_metadata(self):
        async def mock_execute(*args, **kwargs):
            return {"types": [{"type": "HAR"}]}
        self.mock_playback.execute_playback_operation = mock_execute

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_synthetic_result_metadata",
            params={"testid": "t1", "testresultid": "r1"},
        ))
        self.assertEqual(result["operation"], "get_synthetic_result_metadata")

    def test_test_playback_get_synthetic_result_detail_data(self):
        async def mock_execute(*args, **kwargs):
            return {"data": "..."}
        self.mock_playback.execute_playback_operation = mock_execute

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_synthetic_result_detail_data",
            params={"testid": "t1", "testresultid": "r1", "type": "HAR"},
        ))
        self.assertEqual(result["operation"], "get_synthetic_result_detail_data")

    def test_test_playback_invalid_operation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="bad_op",
        ))
        self.assertIn("elicitation_needed", result)
        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(result["reason"], "invalid_operation")
        self.assertIn("bad_op", result["api_error"][0]["issue"])

    def test_test_playback_forwards_params_to_execute(self):
        """All params from the call should be forwarded to execute_playback_operation."""
        captured = {}

        async def mock_execute(operation, params, ctx=None, **kwargs):
            captured["operation"] = operation
            captured["params"] = params
            return {}
        self.mock_playback.execute_playback_operation = mock_execute

        asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_synthetic_result_list",
            params={"payload": {"syntheticMetrics": ["synthetic.metricsStatus"]}, "extra": "value"},
        ))
        self.assertEqual(captured["operation"], "get_synthetic_result_list")
        self.assertIn("payload", captured["params"])

    def test_exception_in_sub_client_is_caught(self):
        async def blow_up(*args, **kwargs):
            raise RuntimeError("Sub-client exploded")
        self.mock_catalog.get_synthetic_catalog_metrics = blow_up

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="catalog",
            operation="get_synthetic_catalog_metrics",
        ))
        self.assertIn("error", result)
        self.assertIn("resource_type", result)
        self.assertIn("operation", result)

    def test_metrics_invalid_operation(self):
        """Invalid operation for metrics should return elicitation_needed."""
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="metrics",
            operation="nonexistent_metrics_op",
        ))
        self.assertIn("elicitation_needed", result)
        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(result["reason"], "invalid_operation")
        self.assertIn("nonexistent_metrics_op", result["api_error"][0]["issue"])

    def test_top_level_exception_is_caught(self):
        """An exception raised before any handler is called is caught at the top level."""
        # Patch _handle_catalog itself to raise — this fires inside the top-level try
        # but outside any handler's own try/except, so it hits lines 262-268.
        async def blow_up(*args, **kwargs):
            raise ValueError("Top-level routing error")
        self.router._handle_catalog = blow_up

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="catalog",
            operation="get_synthetic_catalog_metrics",
        ))
        self.assertIn("error", result)
        self.assertIn("resource_type", result)
        self.assertIn("operation", result)

    def test_settings_exception_is_caught(self):
        """An exception raised inside _handle_settings should be caught and returned."""
        async def blow_up(*args, **kwargs):
            raise RuntimeError("Settings exploded")
        self.mock_settings.get_synthetic_tests = blow_up

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="settings",
            operation="get_synthetic_tests",
        ))
        self.assertIn("error", result)
        self.assertEqual(result["resource_type"], "settings")
        self.assertEqual(result["operation"], "get_synthetic_tests")

    def test_test_playback_exception_is_caught(self):
        """An exception raised inside _handle_test_playback should be caught and returned."""
        async def blow_up(*args, **kwargs):
            raise RuntimeError("Playback exploded")
        self.mock_playback.execute_playback_operation = blow_up

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_synthetic_result",
        ))
        self.assertIn("error", result)
        self.assertEqual(result["resource_type"], "test_playback")
        self.assertEqual(result["operation"], "get_synthetic_result")


if __name__ == '__main__':
    unittest.main()
