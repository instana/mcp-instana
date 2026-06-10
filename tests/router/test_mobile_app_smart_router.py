"""
Unit tests for Mobile App Smart Router Tool.

Tests the MobileAppSmartRouterMCPTool which routes mobile app monitoring operations.
"""

import asyncio
import logging
import unittest
from unittest.mock import MagicMock, patch


# Mock decorator
def mock_with_header_auth(func):
    return func

# Suppress logging
logging.getLogger().addHandler(logging.NullHandler())

# Patch decorator before import
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.router.mobile_app_smart_router import MobileAppSmartRouterMCPTool


class TestMobileAppSmartRouterTool(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.mock_analyze_client = MagicMock()
        self.mock_catalog_client = MagicMock()
        self.mock_alert_client = MagicMock()

        self.router = MobileAppSmartRouterMCPTool.__new__(MobileAppSmartRouterMCPTool)
        self.router.read_token = "test_token"
        self.router.base_url = "https://test.instana.com"

        self.router.mobile_app_analyze_client = self.mock_analyze_client
        self.router.mobile_app_catalog_client = self.mock_catalog_client
        self.router.mobile_app_alert_client = self.mock_alert_client


    def test_initialization(self):
        self.assertIsNotNone(self.router)
        self.assertIsNotNone(self.router.mobile_app_analyze_client)
        self.assertIsNotNone(self.router.mobile_app_catalog_client)
        self.assertIsNotNone(self.router.mobile_app_alert_client)

    def test_invalid_resource_type(self):
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="invalid",
            operation="test"
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid resource_type", result["error"])

    def test_params_none(self):
        async def mock_metrics(*args, **kwargs):
            return {"metrics": []}

        self.mock_catalog_client.get_mobile_app_metric_catalog = mock_metrics

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_metric_catalog",
            params=None
        ))

        self.assertIn("results", result)

    def test_analyze_beacon_groups(self):
        async def mock_groups(*args, **kwargs):
            return {"groups": [{"name": "App1", "count": 10}]}

        self.mock_analyze_client.get_mobile_app_beacon_groups = mock_groups

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "group": {"groupByTag": "mobileBeacon.mobileApp.name"},
                "time_frame": {"to": 1609459200000, "windowSize": 3600000},
                "beacon_type": "SESSION_START"
            }
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_mobile_app_beacon_groups")

    def test_analyze_all_beacons(self):
        async def mock_beacons(*args, **kwargs):
            return {"beacons": [{"id": "b1"}]}

        self.mock_analyze_client.get_all_mobile_app_beacons = mock_beacons

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_all_mobile_app_beacons",
            params={
                "time_frame": {"to": 1609459200000, "windowSize": 3600000},
                "beacon_type": "SESSION_START"
            }
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_all_mobile_app_beacons")

    def test_analyze_invalid_operation(self):
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="invalid_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_analyze_with_tag_filter(self):
        async def mock_groups(*args, **kwargs):
            return {"groups": []}

        self.mock_analyze_client.get_mobile_app_beacon_groups = mock_groups

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "tag_filter_expression": {
                    "type": "TAG_FILTER",
                    "name": "mobileBeacon.mobileApp.name",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "Robot Shop"
                }
            }
        ))

        self.assertIn("results", result)

    def test_analyze_fill_time_series(self):
        async def mock_groups(*args, **kwargs):
            self.assertEqual(kwargs.get("fill_time_series"), False)
            return {"groups": []}

        self.mock_analyze_client.get_mobile_app_beacon_groups = mock_groups

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "fill_time_series": False
            }
        ))

        self.assertIn("results", result)

    def test_analyze_with_order_and_pagination(self):
        async def mock_groups(*args, **kwargs):
            return {"groups": []}

        self.mock_analyze_client.get_mobile_app_beacon_groups = mock_groups

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "order": {"by": "beaconCount", "direction": "DESC"},
                "pagination": {"retrievalSize": 10}
            }
        ))

        self.assertIn("results", result)

    def test_analyze_datetime_conversion_error(self):
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={
                "time_frame": {"to": "INVALID_DATE"}
            }
        ))

        self.assertIn("error", result)

    def test_catalog_metrics(self):
        async def mock_metrics(*args, **kwargs):
            return {"metrics": ["beaconCount"]}

        self.mock_catalog_client.get_mobile_app_metric_catalog = mock_metrics

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_metric_catalog"
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_mobile_app_metric_catalog")

    def test_catalog_metrics_default_passes_planner_view(self):
        captured = {}

        async def mock_metrics(*args, **kwargs):
            captured.update(kwargs)
            return {"metrics": []}

        self.mock_catalog_client.get_mobile_app_metric_catalog = mock_metrics

        asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_metric_catalog"
        ))

        self.assertEqual(captured.get("view"), "planner")

    def test_catalog_metrics_passes_view_full(self):
        captured = {}

        async def mock_metrics(*args, **kwargs):
            captured.update(kwargs)
            return {"metrics": []}

        self.mock_catalog_client.get_mobile_app_metric_catalog = mock_metrics

        asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_metric_catalog",
            params={"view": "full"}
        ))

        self.assertEqual(captured.get("view"), "full")

    def test_catalog_tag_catalog(self):
        async def mock_tags(*args, **kwargs):
            return {"tags": ["mobileBeacon.mobileApp.name"]}

        self.mock_catalog_client.get_mobile_app_tag_catalog = mock_tags

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_tag_catalog",
            params={"beacon_type": "SESSION_START", "use_case": "GROUPING"}
        ))

        self.assertIn("results", result)

    def test_catalog_beacon_type_normalization(self):
        async def mock_tags(*args, **kwargs):
            self.assertEqual(kwargs.get("beacon_type"), "sessionStart")
            return {"tags": []}

        self.mock_catalog_client.get_mobile_app_tag_catalog = mock_tags

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_tag_catalog",
            params={"beacon_type": "SESSION_START"}
        ))

        self.assertIn("results", result)

    def test_catalog_invalid_operation(self):
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="invalid_op",
            params={}
        ))

        self.assertIn("error", result)


    def test_exception_handling(self):
        async def mock_error(*args, **kwargs):
            raise Exception("test error")

        self.mock_analyze_client.get_mobile_app_beacon_groups = mock_error

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Smart router error", result["error"])

    def test_alert_find_config(self):
        async def mock_alert(*args, **kwargs):
            return {"id": "alert-1", "name": "Test Alert"}

        self.mock_alert_client.find_mobile_app_alert_config = mock_alert

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_mobile_app_alert_config",
            params={"id": "alert-1"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "find_mobile_app_alert_config")
        self.assertEqual(result["results"]["id"], "alert-1")

    def test_alert_param_mapping(self):
        async def mock_alert(*args, **kwargs):
            self.assertEqual(kwargs.get("id"), "alert-123")
            self.assertEqual(kwargs.get("valid_on"), 1234567890)
            return {"id": "alert-123"}

        self.mock_alert_client.find_mobile_app_alert_config = mock_alert

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_mobile_app_alert_config",
            params={
                "id": "alert-123",
                "valid_on": 1234567890
            }
        ))

        self.assertIn("results", result)

    def test_alert_find_active_configs(self):
        """Test find_active_mobile_app_alert_configs operation"""
        async def mock_alert(*args, **kwargs):
            return {
                "configs": [
                    {"id": "alert-1", "name": "Alert 1"},
                    {"id": "alert-2", "name": "Alert 2"}
                ],
                "count": 2,
                "total": 2
            }

        self.mock_alert_client.find_active_mobile_app_alert_configs = mock_alert

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_active_mobile_app_alert_configs",
            params={"mobile_app_id": "app-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "find_active_mobile_app_alert_configs")
        self.assertEqual(result["results"]["count"], 2)

    def test_alert_find_active_configs_with_alert_ids(self):
        """Test find_active_mobile_app_alert_configs with alert_ids filter"""
        async def mock_alert(*args, **kwargs):
            self.assertEqual(kwargs.get("mobile_app_id"), "app-123")
            self.assertEqual(kwargs.get("alert_ids"), ["alert-1", "alert-2"])
            return {"configs": [{"id": "alert-1"}], "count": 1, "total": 1}

        self.mock_alert_client.find_active_mobile_app_alert_configs = mock_alert

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_active_mobile_app_alert_configs",
            params={
                "mobile_app_id": "app-123",
                "alert_ids": ["alert-1", "alert-2"]
            }
        ))

        self.assertIn("results", result)

    def test_alert_find_active_configs_empty_results(self):
        """Test find_active_mobile_app_alert_configs with no results"""
        async def mock_alert(*args, **kwargs):
            return {"configs": [], "count": 0, "total": 0}

        self.mock_alert_client.find_active_mobile_app_alert_configs = mock_alert

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_active_mobile_app_alert_configs",
            params={"mobile_app_id": "app-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["results"]["count"], 0)

    def test_alert_resource_invalid_operation(self):
        """Test alert resource with invalid operation"""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="invalid_alert_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_alert_no_params(self):
        async def mock_alert(*args, **kwargs):
            self.assertIsNone(kwargs.get("id"))
            self.assertIsNone(kwargs.get("valid_on"))
            return {"configs": []}

        self.mock_alert_client.find_mobile_app_alert_config = mock_alert

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_mobile_app_alert_config",
            params={}
        ))

        self.assertIn("results", result)

    def test_alert_invalid_operation(self):
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="invalid_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_alert_exception_handling(self):
        async def mock_error(*args, **kwargs):
            raise Exception("alert error")

        self.mock_alert_client.find_mobile_app_alert_config = mock_error

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_mobile_app_alert_config",
            params={"id": "alert-1"}
        ))

        self.assertIn("error", result)
        self.assertIn("Smart router error", result["error"])


if __name__ == "__main__":
    unittest.main()
