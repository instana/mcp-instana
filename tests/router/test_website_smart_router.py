"""
Unit tests for Website Smart Router Tool.

Tests the WebsiteSmartRouterMCPTool which routes website monitoring operations to appropriate clients.
"""

import asyncio
import logging
import unittest
from unittest.mock import MagicMock, patch


# Mock the with_header_auth decorator before importing the router
def mock_with_header_auth(func):
    """Mock decorator that returns the function unchanged."""
    return func

# Suppress logging during tests
logging.getLogger().addHandler(logging.NullHandler())

# Patch the decorator at import time
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.router.website_smart_router import WebsiteSmartRouterMCPTool


class TestWebsiteSmartRouterTool(unittest.TestCase):
    """Test cases for Website Smart Router Tool."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock clients
        self.mock_analyze_client = MagicMock()
        self.mock_catalog_client = MagicMock()
        self.mock_config_client = MagicMock()
        self.mock_alert_client = MagicMock()

        # Create router and directly assign mock clients
        self.router = WebsiteSmartRouterMCPTool.__new__(WebsiteSmartRouterMCPTool)
        self.router.read_token = "test_token"
        self.router.base_url = "https://test.instana.com"
        # Assign mock clients directly
        self.router.website_analyze_client = self.mock_analyze_client
        self.router.website_catalog_client = self.mock_catalog_client
        self.router.website_configuration_client = self.mock_config_client
        self.router.website_alert_client = self.mock_alert_client

    def test_initialization(self):
        """Test router initialization."""
        self.assertIsNotNone(self.router)
        self.assertIsNotNone(self.router.website_analyze_client)
        self.assertIsNotNone(self.router.website_catalog_client)
        self.assertIsNotNone(self.router.website_configuration_client)
        self.assertIsNotNone(self.router.website_alert_client)

    def test_manage_websites_description_uses_current_page_load_metric(self):
        """Tool guidance should advertise the catalog-backed page load metric."""
        description = WebsiteSmartRouterMCPTool.manage_websites._mcp_description
        stale_metric = "page" + "LoadTime"

        self.assertIn('"onLoadTime"', description)
        self.assertNotIn(stale_metric, description)

    def test_invalid_resource_type(self):
        """Test handling of invalid resource type."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="invalid_type",
            operation="get_all"
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid resource_type", result["error"])
        self.assertIn("valid_types", result)

    # Analyze Tests
    def test_analyze_get_beacon_groups(self):
        """Test analyze get_beacon_groups operation."""
        async def mock_get_beacon_groups(*args, **kwargs):
            return {"groups": [{"name": "home", "count": 100}]}

        self.mock_analyze_client.get_website_beacon_groups = mock_get_beacon_groups

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "group": {"groupByTag": "beacon.page.name"},
                "time_frame": {"to": 1609459200000, "windowSize": 3600000},
                "beacon_type": "PAGELOAD"
            }
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "analyze")
        self.assertEqual(result["operation"], "get_beacon_groups")

    def test_analyze_get_beacons(self):
        """Test analyze get_beacons operation."""
        async def mock_get_beacons(*args, **kwargs):
            return {"beacons": [{"id": "beacon-1", "page": "home"}]}

        self.mock_analyze_client.get_website_beacons = mock_get_beacons

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={
                "time_frame": {"to": 1609459200000, "windowSize": 3600000},
                "beacon_type": "PAGELOAD",
                "pagination": {"retrievalSize": 50}
            }
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_beacons")

    def test_analyze_with_tag_filter(self):
        """Test analyze operation with tag filter expression."""
        async def mock_get_beacon_groups(*args, **kwargs):
            return {"groups": [{"name": "Robot Shop", "count": 50}]}

        self.mock_analyze_client.get_website_beacon_groups = mock_get_beacon_groups

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "tag_filter_expression": {
                    "type": "TAG_FILTER",
                    "name": "beacon.website.name",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "Robot Shop"
                },
                "time_frame": {"to": 1609459200000, "windowSize": 3600000},
                "beacon_type": "PAGELOAD"
            }
        ))

        self.assertIn("results", result)

    def test_analyze_with_different_aggregations(self):
        """Test analyze operation with different aggregation types (P95, MEAN, MAX)."""
        async def mock_get_beacon_groups(*args, **kwargs):
            return {"groups": [{"name": "checkout", "p95": 1500, "mean": 1200, "max": 3000}]}

        self.mock_analyze_client.get_website_beacon_groups = mock_get_beacon_groups

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "metrics": [
                    {"metric": "onLoadTime", "aggregation": "P95"},
                    {"metric": "onLoadTime", "aggregation": "MEAN"},
                    {"metric": "onLoadTime", "aggregation": "MAX"}
                ],
                "group": {"groupByTag": "beacon.page.name"},
                "beacon_type": "PAGELOAD"
            }
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_beacon_groups")

    def test_analyze_with_contains_operator(self):
        """Test analyze operation with CONTAINS operator."""
        async def mock_get_beacon_groups(*args, **kwargs):
            return {"groups": [{"name": "checkout-step1", "count": 50}, {"name": "checkout-step2", "count": 45}]}

        self.mock_analyze_client.get_website_beacon_groups = mock_get_beacon_groups

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "tag_filter_expression": {
                    "type": "TAG_FILTER",
                    "name": "beacon.page.name",
                    "operator": "CONTAINS",
                    "entity": "NOT_APPLICABLE",
                    "value": "checkout"
                },
                "group": {"groupByTag": "beacon.page.name"},
                "beacon_type": "PAGELOAD"
            }
        ))

        self.assertIn("results", result)

    def test_analyze_with_greater_than_operator(self):
        """Test analyze operation with GREATER_THAN operator."""
        async def mock_get_beacon_groups(*args, **kwargs):
            return {"groups": [{"name": "slow-page", "count": 10}]}

        self.mock_analyze_client.get_website_beacon_groups = mock_get_beacon_groups

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "tag_filter_expression": {
                    "type": "TAG_FILTER",
                    "name": "beacon.duration",
                    "operator": "GREATER_THAN",
                    "entity": "NOT_APPLICABLE",
                    "value": "5000"
                },
                "group": {"groupByTag": "beacon.page.name"},
                "beacon_type": "PAGELOAD"
            }
        ))

        self.assertIn("results", result)

    def test_analyze_invalid_operation(self):
        """Test analyze with invalid operation."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="invalid_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])
        self.assertIn("valid_operations", result)

    # Catalog Tests
    def test_catalog_get_metrics(self):
        """Test catalog get_metrics operation."""
        async def mock_get_metrics(*args, **kwargs):
            return {"metrics": ["beaconCount", "onLoadTime", "errorRate"]}

        self.mock_catalog_client.get_website_catalog_metrics = mock_get_metrics

        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_metrics"
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "catalog")
        self.assertEqual(result["operation"], "get_metrics")

    def test_catalog_get_metrics_default_passes_planner_view(self):
        """Router should default get_metrics to view='planner'."""
        captured = {}

        async def mock_get_metrics(*args, **kwargs):
            captured.update(kwargs)
            return {"metrics": []}

        self.mock_catalog_client.get_website_catalog_metrics = mock_get_metrics

        asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_metrics"
        ))

        self.assertEqual(captured.get("view"), "planner")

    def test_catalog_get_metrics_passes_view_full(self):
        """Router should forward params.view='full' to the catalog client."""
        captured = {}

        async def mock_get_metrics(*args, **kwargs):
            captured.update(kwargs)
            return {"metrics": []}

        self.mock_catalog_client.get_website_catalog_metrics = mock_get_metrics

        asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_metrics",
            params={"view": "full"}
        ))

        self.assertEqual(captured.get("view"), "full")

    def test_catalog_get_tag_catalog(self):
        """Test catalog get_tag_catalog operation."""
        async def mock_get_tag_catalog(*args, **kwargs):
            return {"tags": ["beacon.website.name", "beacon.page.name", "beacon.browser.name"]}

        self.mock_catalog_client.get_website_tag_catalog = mock_get_tag_catalog

        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"beacon_type": "PAGELOAD", "use_case": "GROUPING"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_tag_catalog")

    def test_catalog_beacon_type_normalization(self):
        """Test beacon_type normalization from uppercase to camelCase."""
        async def mock_get_tag_catalog(*args, **kwargs):
            # Verify the normalized beacon_type is passed
            self.assertEqual(kwargs.get("beacon_type"), "pageLoad")
            return {"tags": ["beacon.website.name"]}

        self.mock_catalog_client.get_website_tag_catalog = mock_get_tag_catalog

        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"beacon_type": "PAGELOAD", "use_case": "GROUPING"}
        ))

        self.assertIn("results", result)

    def test_catalog_invalid_operation(self):
        """Test catalog with invalid operation."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="invalid_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    # Configuration Tests
    def test_configuration_get_all(self):
        """Test configuration get_all operation."""
        async def mock_execute(*args, **kwargs):
            return {"websites": [{"id": "web-1", "name": "Robot Shop"}]}

        self.mock_config_client.execute_website_operation = mock_execute

        result = asyncio.run(self.router.manage_websites(
            resource_type="configuration",
            operation="get_all"
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "configuration")
        self.assertEqual(result["operation"], "get_all")

    def test_configuration_get_by_id(self):
        """Test configuration get operation with website_id."""
        async def mock_execute(*args, **kwargs):
            return {"id": "web-123", "name": "Robot Shop"}

        self.mock_config_client.execute_website_operation = mock_execute

        result = asyncio.run(self.router.manage_websites(
            resource_type="configuration",
            operation="get",
            params={"website_id": "web-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["website_id"], "web-123")

    def test_configuration_get_by_name(self):
        """Test configuration get operation with website_name."""
        async def mock_execute(*args, **kwargs):
            return {"id": "web-123", "name": "robot-shop"}

        self.mock_config_client.execute_website_operation = mock_execute

        result = asyncio.run(self.router.manage_websites(
            resource_type="configuration",
            operation="get",
            params={"website_name": "robot-shop"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["website_name"], "robot-shop")

    def test_configuration_invalid_operation(self):
        """Test configuration with invalid operation."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="configuration",
            operation="invalid_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    # Alert Tests - New find_active_*_alert_configs operations
    def test_alert_find_active_configs_success(self):
        """Test alert find_active_website_alert_configs operation"""
        async def mock_alert(*args, **kwargs):
            return {
                "configs": [
                    {"id": "alert-1", "name": "Alert 1"},
                    {"id": "alert-2", "name": "Alert 2"}
                ],
                "count": 2,
                "total": 2
            }

        self.mock_alert_client.find_active_website_alert_configs = mock_alert

        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_active_website_alert_configs",
            params={"website_id": "web-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "find_active_website_alert_configs")
        self.assertEqual(result["results"]["count"], 2)

    def test_alert_find_active_configs_with_alert_ids(self):
        """Test find_active_website_alert_configs with alert_ids filter"""
        async def mock_alert(*args, **kwargs):
            self.assertEqual(kwargs.get("website_id"), "web-123")
            self.assertEqual(kwargs.get("alert_ids"), ["alert-1", "alert-2"])
            return {"configs": [{"id": "alert-1"}], "count": 1, "total": 1}

        self.mock_alert_client.find_active_website_alert_configs = mock_alert

        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_active_website_alert_configs",
            params={
                "website_id": "web-123",
                "alert_ids": ["alert-1", "alert-2"]
            }
        ))

        self.assertIn("results", result)

    def test_alert_find_active_configs_empty_results(self):
        """Test find_active_website_alert_configs with no results"""
        async def mock_alert(*args, **kwargs):
            return {"configs": [], "count": 0, "total": 0}

        self.mock_alert_client.find_active_website_alert_configs = mock_alert

        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_active_website_alert_configs",
            params={"website_id": "web-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["results"]["count"], 0)


    # Advanced Config Tests
    def test_advanced_config_get_geo_config(self):
        """Test advanced_config get_geo_config operation."""
        async def mock_execute(*args, **kwargs):
            return {"geoDetailRemoval": "NONE", "geoMappingRules": []}

        self.mock_config_client.execute_advanced_config_operation = mock_execute

        result = asyncio.run(self.router.manage_websites(
            resource_type="advanced_config",
            operation="get_geo_config",
            params={"website_name": "robot-shop"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "advanced_config")
        self.assertEqual(result["operation"], "get_geo_config")

    def test_advanced_config_get_ip_masking(self):
        """Test advanced_config get_ip_masking operation."""
        async def mock_execute(*args, **kwargs):
            return {"ipMasking": "DEFAULT"}

        self.mock_config_client.execute_advanced_config_operation = mock_execute

        result = asyncio.run(self.router.manage_websites(
            resource_type="advanced_config",
            operation="get_ip_masking",
            params={"website_id": "web-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_ip_masking")

    def test_advanced_config_get_geo_rules(self):
        """Test advanced_config get_geo_rules operation."""
        async def mock_execute(*args, **kwargs):
            return {"rules": [{"cidr": "192.168.1.0/24", "country": "US"}]}

        self.mock_config_client.execute_advanced_config_operation = mock_execute

        result = asyncio.run(self.router.manage_websites(
            resource_type="advanced_config",
            operation="get_geo_rules",
            params={"website_name": "robot-shop"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_geo_rules")

    def test_advanced_config_invalid_operation(self):
        """Test advanced_config with invalid operation."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="advanced_config",
            operation="invalid_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])
        self.assertIn("valid_operations", result)

    # Error Handling Tests
    def test_exception_handling(self):
        """Test exception handling in router."""
        async def mock_error(*args, **kwargs):
            raise Exception("Test error")

        self.mock_analyze_client.get_website_beacon_groups = mock_error

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={"time_frame": {"to": 1609459200000, "windowSize": 3600000}}
        ))

        self.assertIn("error", result)
        self.assertIn("Smart router error", result["error"])

    def test_params_none(self):
        """Test handling when params is None."""
        async def mock_get_metrics(*args, **kwargs):
            return {"metrics": []}

        self.mock_catalog_client.get_website_catalog_metrics = mock_get_metrics

        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_metrics",
            params=None
        ))

        self.assertIn("results", result)

    def test_analyze_with_fill_time_series(self):
        """Test analyze operation with fill_time_series parameter."""
        async def mock_get_beacon_groups(*args, **kwargs):
            # Verify fill_time_series is passed correctly
            self.assertEqual(kwargs.get("fill_time_series"), False)
            return {"groups": []}

        self.mock_analyze_client.get_website_beacon_groups = mock_get_beacon_groups

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "time_frame": {"to": 1609459200000, "windowSize": 3600000},
                "fill_time_series": False
            }
        ))

        self.assertIn("results", result)

    def test_analyze_with_order_and_pagination(self):
        """Test analyze operation with order and pagination parameters."""
        async def mock_get_beacon_groups(*args, **kwargs):
            return {"groups": []}

        self.mock_analyze_client.get_website_beacon_groups = mock_get_beacon_groups

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
                "time_frame": {"to": 1609459200000, "windowSize": 3600000},
                "order": {"by": "beaconCount", "direction": "DESC"},
                "pagination": {"page": 1, "pageSize": 20}
            }
        ))

        self.assertIn("results", result)

    def test_catalog_all_beacon_types(self):
        """Test catalog with different beacon types."""
        async def mock_get_tag_catalog(*args, **kwargs):
            return {"tags": []}

        self.mock_catalog_client.get_website_tag_catalog = mock_get_tag_catalog

        beacon_types = ["PAGELOAD", "PAGE_CHANGE", "RESOURCELOAD", "CUSTOM", "HTTPREQUEST", "ERROR"]

        for beacon_type in beacon_types:
            result = asyncio.run(self.router.manage_websites(
                resource_type="catalog",
                operation="get_tag_catalog",
                params={"beacon_type": beacon_type, "use_case": "FILTERING"}
            ))
            self.assertIn("results", result)

    def test_configuration_with_name_and_payload(self):
        """Test configuration operation with name and payload parameters."""
        async def mock_execute(*args, **kwargs):
            return {"success": True}

        self.mock_config_client.execute_website_operation = mock_execute

        result = asyncio.run(self.router.manage_websites(
            resource_type="configuration",
            operation="get",
            params={
                "name": "robot-shop",
                "payload": {"some": "data"}
            }
        ))

        self.assertIn("results", result)

    def test_alert_find_config(self):
        async def mock_alert(*args, **kwargs):
            return {"id": "alert-1", "name": "Test Alert"}

        self.mock_alert_client.find_website_alert_config = mock_alert

        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_website_alert_config",
            params={"id": "alert-1"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "find_website_alert_config")
        self.assertEqual(result["results"]["id"], "alert-1")

    def test_alert_param_mapping(self):
        async def mock_alert(*args, **kwargs):
            self.assertEqual(kwargs.get("id"), "alert-123")
            self.assertEqual(kwargs.get("valid_on"), 1234567890)
            return {"id": "alert-123"}

        self.mock_alert_client.find_website_alert_config = mock_alert

        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_website_alert_config",
            params={
                "id": "alert-123",
                "valid_on": 1234567890
            }
        ))

        self.assertIn("results", result)

    def test_alert_no_params(self):
        async def mock_alert(*args, **kwargs):
            self.assertIsNone(kwargs.get("id"))
            self.assertIsNone(kwargs.get("valid_on"))
            return {"configs": []}

        self.mock_alert_client.find_website_alert_config = mock_alert

        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_website_alert_config",
            params={}
        ))

        self.assertIn("results", result)

    def test_alert_invalid_operation(self):
        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="invalid_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_alert_exception_handling(self):
        async def mock_error(*args, **kwargs):
            raise Exception("alert error")

        self.mock_alert_client.find_website_alert_config = mock_error

        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_website_alert_config",
            params={"id": "alert-1"}
        ))

        self.assertIn("error", result)
        self.assertIn("Smart router error", result["error"])



if __name__ == "__main__":
    unittest.main()
