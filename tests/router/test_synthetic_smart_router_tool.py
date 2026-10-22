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
        self.mock_alert = MagicMock()

        self.router.synthetic_catalog_client = self.mock_catalog
        self.router.synthetic_metrics_client = self.mock_metrics
        self.router.synthetic_settings_client = self.mock_settings
        self.router.synthetic_test_playback_client = self.mock_playback
        self.router.synthetic_alert_client = self.mock_alert

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

    # ------------------------------------------------------------------
    # alert resource_type
    # ------------------------------------------------------------------

    def test_alert_invalid_operation_returns_elicitation(self):
        """Invalid operation for alert should return elicitation_needed."""
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="nonexistent_alert_op",
        ))
        self.assertIn("elicitation_needed", result)
        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(result["reason"], "invalid_operation")
        self.assertIn("nonexistent_alert_op", result["api_error"][0]["issue"])

    def test_alert_find_active(self):
        async def mock_fn(*args, **kwargs):
            return {"configs": [], "total": 0}
        self.mock_alert.find_active_synthetic_alert_configs = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find_active",
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "find_active")
        self.assertIn("results", result)

    def test_alert_find_active_forwards_params(self):
        """synthetic_test_id, alert_ids, page and page_size should be forwarded."""
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"configs": [], "total": 0}
        self.mock_alert.find_active_synthetic_alert_configs = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find_active",
            params={
                "synthetic_test_id": "test-xyz",
                "alert_ids": ["id1"],
                "page": 2,
                "page_size": 5,
            },
        ))
        self.assertEqual(captured.get("synthetic_test_id"), "test-xyz")
        self.assertEqual(captured.get("alert_ids"), ["id1"])
        self.assertEqual(captured.get("page"), 2)
        self.assertEqual(captured.get("page_size"), 5)

    def test_alert_find_active_accepts_camel_case_page_size(self):
        """camelCase pageSize is accepted as an alias for page_size."""
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"configs": [], "total": 0}
        self.mock_alert.find_active_synthetic_alert_configs = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find_active",
            params={"page": 1, "pageSize": 7},
        ))
        self.assertEqual(captured.get("page_size"), 7)

    def test_alert_find_active_page_size_wins_over_camel_case(self):
        """When both spellings are given, page_size takes precedence."""
        captured = {}

        async def mock_fn(*args, **kwargs):
            captured.update(kwargs)
            return {"configs": [], "total": 0}
        self.mock_alert.find_active_synthetic_alert_configs = mock_fn

        asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find_active",
            params={"page_size": 3, "pageSize": 9},
        ))
        self.assertEqual(captured.get("page_size"), 3)

    def test_alert_find_missing_id_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find",
            params={},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(result["reason"], "missing_required_params")
        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))

    def test_alert_empty_or_blank_id_returns_elicitation(self):
        """Empty and whitespace-only ids are treated as missing, not forwarded to the API."""
        for bad_id in ("", "   "):
            for operation in ("find", "find_versions", "delete", "enable", "disable"):
                with self.subTest(operation=operation, bad_id=bad_id):
                    result = asyncio.run(self.router.manage_synthetics(
                        resource_type="alert",
                        operation=operation,
                        params={"id": bad_id},
                    ))
                    self.assertTrue(result.get("elicitation_needed"))
                    self.assertEqual(result["reason"], "missing_required_params")
                    self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))

    def test_top_level_error_log_redacts_payload(self):
        """The error log must not contain the alert payload, but keeps other params."""
        async def blow_up(*args, **kwargs):
            raise RuntimeError("boom")
        self.router._handle_alert = blow_up

        import src.router.synthetic_smart_router_tool as router_module

        # Patch the module logger directly: other test files replace the logging module with
        # a mock, which breaks assertLogs when the whole suite runs in one process.
        with patch.object(router_module, "logger") as mock_logger:
            result = asyncio.run(self.router.manage_synthetics(
                resource_type="alert",
                operation="create",
                params={"payload": {"customPayloadFields": [{"key": "k", "value": "s3cret-value"}]}, "id": "alert-1"},
            ))

        self.assertIn("error", result)
        mock_logger.error.assert_called_once()
        logged_args = repr(mock_logger.error.call_args)
        self.assertNotIn("s3cret-value", logged_args)
        self.assertIn("<redacted>", logged_args)
        self.assertIn("alert-1", logged_args)

    def test_alert_find_success(self):
        async def mock_fn(*args, **kwargs):
            return {"id": "alert-123", "name": "My Alert"}
        self.mock_alert.find_synthetic_alert_config = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find",
            params={"id": "alert-123"},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "find")
        self.assertIn("results", result)

    def test_alert_find_versions_missing_id_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find_versions",
            params={},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(result["reason"], "missing_required_params")

    def test_alert_find_versions_success(self):
        async def mock_fn(*args, **kwargs):
            return {"versions": [], "count": 0}
        self.mock_alert.find_synthetic_alert_config_versions = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find_versions",
            params={"id": "alert-123"},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "find_versions")

    def test_alert_create_missing_payload_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="create",
            params={},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(result["reason"], "missing_required_params")
        self.assertTrue(any(e["field"] == "payload" for e in result["api_error"]))

    def test_alert_create_success(self):
        async def mock_fn(*args, **kwargs):
            return {"id": "new-alert", "name": "Created"}
        self.mock_alert.create_synthetic_alert_config = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="create",
            params={"payload": {"name": "My Alert", "syntheticTestIds": ["t1"]}},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "create")

    def test_alert_update_missing_id_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="update",
            params={"payload": {"name": "x"}},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))

    def test_alert_update_missing_payload_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="update",
            params={"id": "alert-123"},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "payload" for e in result["api_error"]))

    def test_alert_update_success(self):
        async def mock_fn(*args, **kwargs):
            return {"id": "alert-123", "name": "Updated"}
        self.mock_alert.update_synthetic_alert_config = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="update",
            params={"id": "alert-123", "payload": {"name": "Updated"}},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "update")

    def test_alert_delete_missing_id_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="delete",
            params={},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))

    def test_alert_delete_success(self):
        async def mock_fn(*args, **kwargs):
            return {"success": True, "message": "Deleted"}
        self.mock_alert.delete_synthetic_alert_config = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="delete",
            params={"id": "alert-123"},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "delete")

    def test_alert_enable_missing_id_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="enable",
            params={},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))

    def test_alert_enable_success(self):
        async def mock_fn(*args, **kwargs):
            return {"success": True}
        self.mock_alert.enable_synthetic_alert_config = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="enable",
            params={"id": "alert-123"},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "enable")

    def test_alert_disable_missing_id_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="disable",
            params={},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))

    def test_alert_disable_success(self):
        async def mock_fn(*args, **kwargs):
            return {"success": True}
        self.mock_alert.disable_synthetic_alert_config = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="disable",
            params={"id": "alert-123"},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "disable")

    def test_alert_restore_missing_id_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="restore",
            params={"created": 1710000000000},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))

    def test_alert_restore_missing_created_returns_elicitation(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="restore",
            params={"id": "alert-123"},
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "created" for e in result["api_error"]))

    def test_alert_restore_success(self):
        async def mock_fn(*args, **kwargs):
            return {"success": True}
        self.mock_alert.restore_synthetic_alert_config = mock_fn

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="restore",
            params={"id": "alert-123", "created": 1710000000000},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "restore")

    def test_alert_exception_is_caught(self):
        async def blow_up(*args, **kwargs):
            raise RuntimeError("Alert client exploded")
        self.mock_alert.find_active_synthetic_alert_configs = blow_up

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find_active",
        ))
        self.assertIn("error", result)
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(result["operation"], "find_active")

    def test_alert_handler_table_covers_all_valid_operations(self):
        from src.router.synthetic_smart_router_tool import ALERT_VALID_OPERATIONS
        # Verify that all operations in ALERT_VALID_OPERATIONS can be dispatched
        for op in ALERT_VALID_OPERATIONS:
            # Setting up mocks
            dummy_params = {
                "id": "alert-1",
                "created": 12345,
                "payload": {"name": "test"},
            }
            # Execute through router's _call_alert_client
            # Each mock should return a success dummy
            self.mock_alert.find_active_synthetic_alert_configs = AsyncMock(return_value={"success": True})
            self.mock_alert.find_synthetic_alert_config = AsyncMock(return_value={"success": True})
            self.mock_alert.find_synthetic_alert_config_versions = AsyncMock(return_value={"success": True})
            self.mock_alert.create_synthetic_alert_config = AsyncMock(return_value={"success": True})
            self.mock_alert.update_synthetic_alert_config = AsyncMock(return_value={"success": True})
            self.mock_alert.delete_synthetic_alert_config = AsyncMock(return_value={"success": True})
            self.mock_alert.enable_synthetic_alert_config = AsyncMock(return_value={"success": True})
            self.mock_alert.disable_synthetic_alert_config = AsyncMock(return_value={"success": True})
            self.mock_alert.restore_synthetic_alert_config = AsyncMock(return_value={"success": True})

            res = asyncio.run(self.router._call_alert_client(op, dummy_params, ctx=None))
            self.assertEqual(res, {"success": True})

    def test_alert_coercion_string_to_int_params(self):
        captured = {}
        async def mock_find(id, valid_on, **kwargs):
            captured["valid_on"] = valid_on
            return {"id": id}
        self.mock_alert.find_synthetic_alert_config = mock_find

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find",
            params={"id": "alert-123", "valid_on": "1710658800000"},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(captured.get("valid_on"), 1710658800000)

    def test_alert_coercion_invalid_string_returns_error(self):
        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find",
            params={"id": "alert-123", "valid_on": "not-a-number"},
        ))
        self.assertNotIn("results", result)
        self.assertIn("'valid_on' must be an integer", result["error"])

    def test_alert_payload_validation_elicitation_is_top_level(self):
        """An invalid_payload elicitation from the client must not be nested under 'results'."""
        elicitation = {
            "elicitation_needed": True,
            "reason": "invalid_payload",
            "api_error": [{"field": "name", "issue": "Field required"}],
            "message": "Payload failed SyntheticAlertConfig validation. Fix the listed fields and retry.",
        }

        async def mock_create(*args, **kwargs):
            return elicitation
        self.mock_alert.create_synthetic_alert_config = mock_create

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="create",
            params={"payload": {"description": "x"}},
        ))
        self.assertEqual(result, elicitation)

    def test_alert_api_and_timeout_errors_are_top_level(self):
        """API error and timeout dicts from the client are returned unwrapped."""
        errors = [
            {"error": "API error (status 404): not found"},
            {
                "error": "Instana API call timed out after 180s (find_synthetic_alert_config).",
                "operation": "find_synthetic_alert_config",
                "resource_type": "alert",
                "timeout_seconds": 180,
            },
        ]
        for error in errors:
            with self.subTest(error=error["error"]):
                async def mock_find(*args, _error=error, **kwargs):
                    return _error
                self.mock_alert.find_synthetic_alert_config = mock_find

                result = asyncio.run(self.router.manage_synthetics(
                    resource_type="alert",
                    operation="find",
                    params={"id": "alert-123"},
                ))
                self.assertEqual(result, error)

    def test_alert_coercion_single_string_alert_ids_to_list(self):
        captured = {}
        async def mock_find_active(synthetic_test_id, alert_ids, page, page_size, **kwargs):
            captured["alert_ids"] = alert_ids
            return {"configs": []}
        self.mock_alert.find_active_synthetic_alert_configs = mock_find_active

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find_active",
            params={"alert_ids": "single-id"},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(captured.get("alert_ids"), ["single-id"])

    def test_alert_coercion_comma_delimited_string_alert_ids_to_list(self):
        """A comma-delimited string like 'alert-1, alert-2' should split into ['alert-1', 'alert-2']."""
        captured = {}
        async def mock_find_active(synthetic_test_id, alert_ids, page, page_size, **kwargs):
            captured["alert_ids"] = alert_ids
            return {"configs": []}
        self.mock_alert.find_active_synthetic_alert_configs = mock_find_active

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find_active",
            params={"alert_ids": "alert-1, alert-2"},
        ))
        self.assertEqual(result["resource_type"], "alert")
        self.assertEqual(captured.get("alert_ids"), ["alert-1", "alert-2"])

    def test_alert_coercion_comma_delimited_alert_ids_drops_empty_entries(self):
        """Empty entries from stray commas are dropped; an all-empty string yields []."""
        captured = {}
        async def mock_find_active(synthetic_test_id, alert_ids, page, page_size, **kwargs):
            captured["alert_ids"] = alert_ids
            return {"configs": []}
        self.mock_alert.find_active_synthetic_alert_configs = mock_find_active

        asyncio.run(self.router.manage_synthetics(
            resource_type="alert", operation="find_active",
            params={"alert_ids": "a,, b ,"},
        ))
        self.assertEqual(captured["alert_ids"], ["a", "b"])

        asyncio.run(self.router.manage_synthetics(
            resource_type="alert", operation="find_active",
            params={"alert_ids": " , "},
        ))
        self.assertEqual(captured["alert_ids"], [])

    def test_alert_unused_invalid_numeric_params_ignored(self):
        """Invalid page/valid_on on an operation that doesn't use them must not fail the call."""
        called = {}
        async def mock_delete(id, **kwargs):
            called["id"] = id
            return {"success": True}
        self.mock_alert.delete_synthetic_alert_config = mock_delete

        result = asyncio.run(self.router.manage_synthetics(
            resource_type="alert", operation="delete",
            params={"id": "x", "valid_on": "bogus", "page": "bogus"},
        ))
        self.assertEqual(called.get("id"), "x")
        self.assertNotIn("error", result["results"])


    def test_alert_coercion_whole_float_timestamp_accepted(self):
        """A whole-number float (e.g. JSON 1710658800000.0) is accepted for valid_on."""
        captured = {}

        async def mock_find(id, valid_on, **kwargs):
            captured["valid_on"] = valid_on
            return {"id": id}
        self.mock_alert.find_synthetic_alert_config = mock_find

        asyncio.run(self.router.manage_synthetics(
            resource_type="alert",
            operation="find",
            params={"id": "alert-123", "valid_on": 1710658800000.0},
        ))
        self.assertEqual(captured.get("valid_on"), 1710658800000)
        self.assertIsInstance(captured.get("valid_on"), int)


class TestCoerceInt(unittest.TestCase):
    """Direct tests for the _coerce_int helper."""

    def setUp(self):
        from src.router.synthetic_smart_router_tool import _coerce_int
        self.coerce = _coerce_int

    def test_accepts_valid_values(self):
        cases = [
            (5, 5), (0, 0), (-5, -5),
            ("5", 5), (" 5 ", 5), ("-5", -5), ("+5", 5), ("007", 7),
            ("1710658800000", 1710658800000),
            (1710658800000.0, 1710658800000), (3.0, 3),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                result = self.coerce(value, "x")
                self.assertEqual(result, expected)
                self.assertIsInstance(result, int)

    def test_rejects_invalid_values_with_field_aware_message(self):
        cases = [
            True, False, None, [1], {"a": 1},
            "", "  ", "abc", "--5", "+-5", "5-", "1.0", "1e3", "5 5",
            "²", "٣",  # non-ASCII digits that str.isdigit() would let through
            1.5, float("nan"), float("inf"), float("-inf"),
        ]
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as ctx:
                    self.coerce(value, "page")
                self.assertIn("'page' must be an integer", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
