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

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid resource_type", result["message"])

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
                "group": {"groupbyTag": "beacon.page.name", "groupbyTagEntity": "NOT_APPLICABLE"},
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
                "group": {"groupbyTag": "beacon.page.name", "groupbyTagEntity": "NOT_APPLICABLE"},
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
                "group": {"groupbyTag": "beacon.page.name", "groupbyTagEntity": "NOT_APPLICABLE"},
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
                "group": {"groupbyTag": "beacon.page.name", "groupbyTagEntity": "NOT_APPLICABLE"},
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

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid operation", result["message"])

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
        captured = {}

        async def mock_get_tag_catalog(*args, **kwargs):
            captured["beacon_type"] = kwargs.get("beacon_type")
            return {"tags": ["beacon.website.name"]}

        self.mock_catalog_client.get_website_tag_catalog = mock_get_tag_catalog

        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"beacon_type": "PAGELOAD", "use_case": "GROUPING"}
        ))

        self.assertIn("results", result)
        # Router normalises PAGELOAD → pageLoad for the API
        self.assertEqual(captured.get("beacon_type"), "pageLoad")

    def test_catalog_invalid_operation(self):
        """Test catalog with invalid operation."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="invalid_op",
            params={}
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid operation", result["message"])

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

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid operation", result["message"])

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

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid operation", result["message"])

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
        """Omitting 'id' triggers a pre-flight elicitation at the router level."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_website_alert_config",
            params={}
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))

    def test_alert_invalid_operation(self):
        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="invalid_op",
            params={}
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid operation", result["message"])

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



    # ------------------------------------------------------------------
    # Pre-flight StructureValidator tests (added with INSTA-77605)
    # ------------------------------------------------------------------

    def test_preflight_invalid_beacon_type(self):
        """Router rejects an invalid beacon_type before calling the service layer."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={
                "beacon_type": "NOT_A_REAL_TYPE",
                "time_frame": {"windowSize": 3600000},
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("NOT_A_REAL_TYPE" in e for e in result["api_error"]))

    def test_preflight_invalid_window_size(self):
        """Router rejects a windowSize that exceeds the SDK upper bound."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={
                "beacon_type": "PAGELOAD",
                "time_frame": {"windowSize": 9_999_999_999},
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("windowSize" in e for e in result["api_error"]))

    def test_preflight_invalid_retrieval_size(self):
        """Router rejects a retrievalSize outside [1, 200]."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={
                "beacon_type": "PAGELOAD",
                "pagination": {"retrievalSize": 500},
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("retrievalSize" in e for e in result["api_error"]))

    def test_preflight_invalid_aggregation_in_metrics(self):
        """Router rejects a metrics entry with an unrecognised aggregation."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "INVALID_AGG"}],
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("INVALID_AGG" in e for e in result["api_error"]))

    def test_preflight_tag_filter_missing_entity(self):
        """Router rejects a TAG_FILTER that omits the required entity field."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "tag_filter_expression": {
                    "type": "TAG_FILTER",
                    "name": "beacon.page.name",
                    "operator": "EQUALS",
                    "value": "home",
                    # entity intentionally omitted
                }
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("entity" in e for e in result["api_error"]))

    def test_preflight_invalid_order_direction(self):
        """Router rejects an order with an invalid direction."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "order": {"by": "beaconCount", "direction": "DESCENDING"},
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("direction" in e for e in result["api_error"]))

    def test_preflight_group_missing_entity(self):
        """Router rejects a group dict that omits groupbyTagEntity."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={
                "group": {"groupbyTag": "beacon.page.name"},
                # groupbyTagEntity intentionally omitted
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("groupbyTagEntity" in e for e in result["api_error"]))

    def test_preflight_multiple_errors_consolidated(self):
        """Router collects ALL validation errors in a single response."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={
                "beacon_type": "BAD_TYPE",
                "time_frame": {"windowSize": 9_999_999_999},
                "pagination": {"retrievalSize": 0},
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        # All three problems must appear in one response — not split across calls
        self.assertGreaterEqual(len(result["api_error"]), 3)

    def test_preflight_valid_payload_reaches_service(self):
        """A fully valid payload passes pre-flight and is forwarded to the service."""
        captured = {}

        async def mock_beacons(*args, **kwargs):
            captured["called"] = True
            return {"beacons": []}

        self.mock_analyze_client.get_website_beacons = mock_beacons

        result = asyncio.run(self.router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={
                "beacon_type": "PAGELOAD",
                "time_frame": {"windowSize": 3600000},
                "pagination": {"retrievalSize": 50},
            }
        ))

        self.assertTrue(captured.get("called"), "Service layer was not called for a valid payload")
        self.assertIn("results", result)


    # ------------------------------------------------------------------
    # Pre-flight tests added for website gap fixes
    # ------------------------------------------------------------------

    # --- _handle_alert required-field guards ---

    def test_alert_find_active_missing_website_id(self):
        """find_active_website_alert_configs rejects a missing website_id at the router level."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_active_website_alert_configs",
            params={},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(result["reason"], "missing_required_params")
        self.assertTrue(any(e["field"] == "website_id" for e in result["api_error"]))
        self.mock_alert_client.find_active_website_alert_configs.assert_not_called()

    def test_alert_find_config_missing_id(self):
        """find_website_alert_config rejects a missing id at the router level."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_website_alert_config",
            params={},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(result["reason"], "missing_required_params")
        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))
        self.mock_alert_client.find_website_alert_config.assert_not_called()

    def test_alert_find_active_with_website_id_reaches_service(self):
        """find_active_website_alert_configs with a valid website_id reaches the service."""
        async def mock_find_active(*args, **kwargs):
            return {"items": []}

        self.mock_alert_client.find_active_website_alert_configs = mock_find_active

        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_active_website_alert_configs",
            params={"website_id": "site-abc"},
        ))

        self.assertIn("results", result)
        self.assertFalse(result.get("elicitation_needed"))

    def test_alert_find_config_with_id_reaches_service(self):
        """find_website_alert_config with a valid id reaches the service."""
        async def mock_find(*args, **kwargs):
            return {"id": "alert-1"}

        self.mock_alert_client.find_website_alert_config = mock_find

        result = asyncio.run(self.router.manage_websites(
            resource_type="alert",
            operation="find_website_alert_config",
            params={"id": "alert-1"},
        ))

        self.assertIn("results", result)
        self.assertFalse(result.get("elicitation_needed"))


    # --- Alert create / update / lifecycle operations ---

    VALID_ALERT_PAYLOAD = {
        "name": "Slow page loads",
        "description": "P90 load time high",
        "websiteId": "site-1",
        "rules": [{
            "rule": {"alertType": "slowness", "metricName": "onLoadTime", "aggregation": "P90"},
            "thresholdOperator": ">",
            "thresholds": {"CRITICAL": {"type": "staticThreshold", "value": 5000}},
        }],
    }

    def _run_alert(self, operation, params):
        return asyncio.run(self.router.manage_websites(
            resource_type="alert", operation=operation, params=params,
        ))

    def test_alert_new_operations_are_advertised(self):
        description = WebsiteSmartRouterMCPTool.manage_websites._mcp_description
        for op in ("create", "update", "delete", "enable", "disable", "restore", "find_versions"):
            self.assertIn(op, description)

    def test_alert_create_success_forwards_payload(self):
        captured = {}

        async def mock_create(*args, **kwargs):
            captured.update(kwargs)
            return {"id": "alert-new"}

        self.mock_alert_client.create_website_alert_config = mock_create

        result = self._run_alert("create", {"payload": self.VALID_ALERT_PAYLOAD})

        self.assertEqual(result["results"], {"id": "alert-new"})
        self.assertEqual(captured["payload"], self.VALID_ALERT_PAYLOAD)
        self.assertEqual(captured["tool_name"], "manage_websites")

    def test_alert_create_accepts_json_string_payload(self):
        import json

        async def mock_create(*args, **kwargs):
            self.assertEqual(kwargs["payload"], self.VALID_ALERT_PAYLOAD)
            return {"id": "alert-new"}

        self.mock_alert_client.create_website_alert_config = mock_create

        result = self._run_alert("create", {"payload": json.dumps(self.VALID_ALERT_PAYLOAD)})

        self.assertIn("results", result)

    def test_alert_create_missing_payload(self):
        result = self._run_alert("create", {})

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "payload" for e in result["api_error"]))
        self.mock_alert_client.create_website_alert_config.assert_not_called()

    def test_alert_create_missing_required_fields(self):
        result = self._run_alert("create", {"payload": {"name": "only a name"}})

        self.assertEqual(result["reason"], "invalid_payload")
        fields = {e["field"] for e in result["api_error"]}
        self.assertTrue({"description", "websiteId", "rules"} <= fields)
        self.mock_alert_client.create_website_alert_config.assert_not_called()

    def test_alert_create_rejects_legacy_top_level_fields(self):
        payload = {**self.VALID_ALERT_PAYLOAD, "rule": {}, "threshold": {}, "severity": 10}

        result = self._run_alert("create", {"payload": payload})

        self.assertEqual(result["reason"], "invalid_payload")
        fields = {e["field"] for e in result["api_error"]}
        self.assertTrue({"rule", "threshold", "severity"} <= fields)
        self.mock_alert_client.create_website_alert_config.assert_not_called()

    def test_alert_create_rejects_both_channel_fields(self):
        payload = {**self.VALID_ALERT_PAYLOAD, "alertChannelIds": ["c1"], "alertChannels": {"CRITICAL": ["c1"]}}

        result = self._run_alert("create", {"payload": payload})

        self.assertEqual(result["reason"], "invalid_payload")
        self.assertTrue(any(e["field"] == "alertChannels" for e in result["api_error"]))
        self.mock_alert_client.create_website_alert_config.assert_not_called()

    def test_alert_rejects_unknown_severity_channel_key(self):
        payload = {**self.VALID_ALERT_PAYLOAD, "alertChannels": {"MAJOR": ["c1"]}}

        for operation, extra in (("create", {}), ("update", {"id": "alert-1"})):
            with self.subTest(operation=operation):
                result = self._run_alert(operation, {"payload": payload, **extra})

                self.assertEqual(result["reason"], "invalid_payload")

    def test_alert_update_allows_both_channel_fields(self):
        async def mock_update(*args, **kwargs):
            return {"id": "alert-1"}

        self.mock_alert_client.update_website_alert_config = mock_update
        payload = {**self.VALID_ALERT_PAYLOAD, "alertChannelIds": ["c1"], "alertChannels": {"CRITICAL": ["c1"]}}

        result = self._run_alert("update", {"id": "alert-1", "payload": payload})

        self.assertEqual(result["results"], {"id": "alert-1"})

    def test_alert_client_error_is_returned_at_top_level(self):
        async def mock_delete(*args, **kwargs):
            return {"error": "API error (status 403): denied", "status_code": 403}

        self.mock_alert_client.delete_website_alert_config = mock_delete

        result = self._run_alert("delete", {"id": "alert-1"})

        self.assertEqual(result["error"], "API error (status 403): denied")
        self.assertEqual(result["operation"], "delete")
        self.assertNotIn("results", result)

    def test_alert_timeout_warning_is_returned_at_top_level(self):
        async def mock_disable(*args, **kwargs):
            return {"error": "timed out", "timeout_seconds": 1, "warning": "outcome unknown"}

        self.mock_alert_client.disable_website_alert_config = mock_disable

        result = self._run_alert("disable", {"id": "alert-1"})

        self.assertEqual(result["warning"], "outcome unknown")

    def test_alert_rejects_non_positive_and_malformed_created(self):
        for bad in ("-5", "--5", "0", -1):
            with self.subTest(created=bad):
                result = self._run_alert("restore", {"id": "alert-1", "created": bad})

                self.assertTrue(any(e["field"] == "created" for e in result["api_error"]))

    def test_alert_restore_accepts_integral_float_created(self):
        captured = {}

        async def mock_restore(*args, **kwargs):
            captured.update(kwargs)
            return {"success": True}

        self.mock_alert_client.restore_website_alert_config = mock_restore

        self._run_alert("restore", {"id": "alert-1", "created": 1.7e12})

        self.assertEqual(captured["created"], 1700000000000)

    def test_alert_invalid_numeric_params_use_invalid_param_reason(self):
        restore = self._run_alert("restore", {"id": "alert-1", "created": "-5"})
        find = self._run_alert("find_website_alert_config", {"id": "alert-1", "valid_on": "yesterday"})
        missing = self._run_alert("restore", {"id": "alert-1"})

        self.assertEqual(restore["reason"], "invalid_param")
        self.assertEqual(find["reason"], "invalid_param")
        self.assertEqual(missing["reason"], "missing_required_params")

    def test_router_error_log_omits_payload(self):
        self.mock_alert_client.create_website_alert_config = MagicMock(side_effect=RuntimeError("boom"))

        # Patch the module logger: assertLogs breaks when another test module mocks `logging`.
        with patch("src.router.website_smart_router.logger") as mock_logger:
            result = self._run_alert("create", {"payload": {**self.VALID_ALERT_PAYLOAD, "description": "SECRET-TEXT"}})

        self.assertIn("error", result)
        mock_logger.error.assert_called_once()
        self.assertNotIn("SECRET-TEXT", str(mock_logger.error.call_args))

    def test_alert_create_rejects_bad_rules_shape(self):
        for bad_rules in (
            [self.VALID_ALERT_PAYLOAD["rules"][0], self.VALID_ALERT_PAYLOAD["rules"][0]],
            [{"rule": {}, "thresholds": {"INFO": {"type": "staticThreshold", "value": 1}}}],
            [{"rule": {}, "thresholds": {}}],
            [{"rule": {}}],
        ):
            with self.subTest(rules=bad_rules):
                result = self._run_alert("create", {"payload": {**self.VALID_ALERT_PAYLOAD, "rules": bad_rules}})
                self.assertEqual(result["reason"], "invalid_payload")
        self.mock_alert_client.create_website_alert_config.assert_not_called()

    def test_alert_update_success_forwards_id_and_payload(self):
        captured = {}
        payload = {**self.VALID_ALERT_PAYLOAD, "name": "Renamed"}

        async def mock_update(*args, **kwargs):
            captured.update(kwargs)
            return {"id": "alert-1", "name": "Renamed"}

        self.mock_alert_client.update_website_alert_config = mock_update

        result = self._run_alert("update", {"id": "alert-1", "payload": payload})

        self.assertEqual(result["results"]["name"], "Renamed")
        self.assertEqual(captured["id"], "alert-1")
        self.assertEqual(captured["payload"], payload)

    def test_alert_update_partial_payload_is_rejected(self):
        result = self._run_alert("update", {"id": "alert-1", "payload": {"granularity": 300000}})

        self.assertEqual(result["reason"], "invalid_payload")
        fields = {e["field"] for e in result["api_error"]}
        self.assertTrue({"name", "description", "websiteId", "rules"} <= fields)
        self.mock_alert_client.update_website_alert_config.assert_not_called()

    def test_alert_update_missing_id(self):
        result = self._run_alert("update", {"payload": {"name": "x"}})

        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))
        self.mock_alert_client.update_website_alert_config.assert_not_called()

    def test_alert_update_missing_payload(self):
        result = self._run_alert("update", {"id": "alert-1"})

        self.assertTrue(any(e["field"] == "payload" for e in result["api_error"]))
        self.mock_alert_client.update_website_alert_config.assert_not_called()

    def test_alert_update_accepts_legacy_top_level_fields_for_client_to_drop(self):
        captured = {}

        async def mock_update(*args, **kwargs):
            captured.update(kwargs)
            return {"id": "alert-1"}

        self.mock_alert_client.update_website_alert_config = mock_update
        payload = {**self.VALID_ALERT_PAYLOAD, "rule": {}, "threshold": {}, "severity": 5}

        result = self._run_alert("update", {"id": "alert-1", "payload": payload})

        self.assertNotIn("elicitation_needed", result)
        self.assertEqual(captured["payload"], payload)

    def test_alert_id_only_operations_forward_id(self):
        methods = {
            "delete": "delete_website_alert_config",
            "enable": "enable_website_alert_config",
            "disable": "disable_website_alert_config",
            "find_versions": "find_website_alert_config_versions",
        }
        for operation, method in methods.items():
            with self.subTest(operation=operation):
                captured = {}

                async def mock_call(*args, _captured=captured, **kwargs):
                    _captured.update(kwargs)
                    return {"success": True}

                setattr(self.mock_alert_client, method, mock_call)

                result = self._run_alert(operation, {"id": "alert-1"})

                self.assertEqual(result["operation"], operation)
                self.assertEqual(result["results"], {"success": True})
                self.assertEqual(captured["id"], "alert-1")

    def test_alert_id_only_operations_missing_id(self):
        for operation in ("delete", "enable", "disable", "find_versions"):
            with self.subTest(operation=operation):
                result = self._run_alert(operation, {})

                self.assertTrue(result.get("elicitation_needed"))
                self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))

    def test_alert_restore_success(self):
        captured = {}

        async def mock_restore(*args, **kwargs):
            captured.update(kwargs)
            return {"success": True}

        self.mock_alert_client.restore_website_alert_config = mock_restore

        result = self._run_alert("restore", {"id": "alert-1", "created": 1700000000000})

        self.assertEqual(result["results"], {"success": True})
        self.assertEqual(captured["id"], "alert-1")
        self.assertEqual(captured["created"], 1700000000000)

    def test_alert_restore_missing_id_and_created(self):
        no_id = self._run_alert("restore", {"created": 1})
        no_created = self._run_alert("restore", {"id": "alert-1"})

        self.assertTrue(any(e["field"] == "id" for e in no_id["api_error"]))
        self.assertTrue(any(e["field"] == "created" for e in no_created["api_error"]))
        self.mock_alert_client.restore_website_alert_config.assert_not_called()

    def test_alert_client_exception_is_caught_by_router(self):
        async def mock_error(*args, **kwargs):
            raise Exception("boom")

        self.mock_alert_client.delete_website_alert_config = mock_error

        result = self._run_alert("delete", {"id": "alert-1"})

        self.assertIn("Smart router error", result["error"])

    def test_alert_create_and_update_reject_non_dict_payload(self):
        for operation in ("create", "update"):
            for bad in ("[1]", "5", [1, 2]):
                with self.subTest(operation=operation, payload=bad):
                    result = self._run_alert(operation, {"id": "alert-1", "payload": bad})

                    self.assertTrue(result.get("elicitation_needed"), result)
                    self.assertTrue(any(e["field"] == "payload" for e in result["api_error"]))
        self.mock_alert_client.create_website_alert_config.assert_not_called()
        self.mock_alert_client.update_website_alert_config.assert_not_called()

    def test_alert_rules_item_not_an_object_is_reported_as_such(self):
        payload = {**self.VALID_ALERT_PAYLOAD, "rules": ["x"]}

        result = self._run_alert("create", {"payload": payload})

        self.assertEqual([e["field"] for e in result["api_error"]], ["rules[0]"])

    def test_alert_restore_coerces_numeric_string_created(self):
        captured = {}

        async def mock_restore(*args, **kwargs):
            captured.update(kwargs)
            return {"success": True}

        self.mock_alert_client.restore_website_alert_config = mock_restore

        self._run_alert("restore", {"id": "alert-1", "created": "1700000000000"})

        self.assertEqual(captured["created"], 1700000000000)
        self.assertIsInstance(captured["created"], int)

    def test_alert_restore_rejects_non_numeric_created(self):
        for bad in ("abc", True, 1.5, []):
            with self.subTest(created=bad):
                result = self._run_alert("restore", {"id": "alert-1", "created": bad})

                self.assertTrue(any(e["field"] == "created" for e in result["api_error"]))
        self.mock_alert_client.restore_website_alert_config.assert_not_called()

    def test_alert_numeric_id_is_coerced_to_str(self):
        captured = {}

        async def mock_delete(*args, **kwargs):
            captured.update(kwargs)
            return {"success": True}

        self.mock_alert_client.delete_website_alert_config = mock_delete

        self._run_alert("delete", {"id": 123})

        self.assertEqual(captured["id"], "123")

    def test_alert_find_coerces_valid_on_and_rejects_garbage(self):
        captured = {}

        async def mock_find(*args, **kwargs):
            captured.update(kwargs)
            return {"id": "alert-1"}

        self.mock_alert_client.find_website_alert_config = mock_find

        self._run_alert("find_website_alert_config", {"id": "alert-1", "valid_on": "1742349976000"})
        bad = self._run_alert("find_website_alert_config", {"id": "alert-1", "valid_on": "yesterday"})

        self.assertEqual(captured["valid_on"], 1742349976000)
        self.assertTrue(any(e["field"] == "valid_on" for e in bad["api_error"]))

    def test_alert_description_warns_about_writes(self):
        description = WebsiteSmartRouterMCPTool.manage_websites._mcp_description

        self.assertIn("Confirm with the user", description)
        self.assertIn("outcome is unknown", description)


    # --- _handle_catalog get_tag_catalog guards ---

    def test_catalog_tag_catalog_missing_use_case_rejected(self):
        """get_tag_catalog rejects a missing use_case before hitting the API."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"beacon_type": "PAGELOAD"},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "use_case" for e in result["api_error"]))
        self.mock_catalog_client.get_website_tag_catalog.assert_not_called()

    def test_catalog_tag_catalog_invalid_beacon_type_rejected(self):
        """get_tag_catalog rejects a beacon_type not in VALID_WEBSITE_BEACON_TYPES."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"beacon_type": "SESSION_START", "use_case": "FILTERING"},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "beacon_type" for e in result["api_error"]))
        self.assertTrue(any("SESSION_START" in e["issue"] for e in result["api_error"]))
        self.mock_catalog_client.get_website_tag_catalog.assert_not_called()

    def test_catalog_tag_catalog_both_errors_consolidated(self):
        """Missing use_case AND invalid beacon_type are reported together in one response."""
        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"beacon_type": "SESSION_START"},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        fields = [e["field"] for e in result["api_error"]]
        self.assertIn("use_case", fields)
        self.assertIn("beacon_type", fields)

    def test_catalog_tag_catalog_valid_params_reach_service(self):
        """get_tag_catalog with valid beacon_type and use_case reaches the service."""
        async def mock_tags(*args, **kwargs):
            return {"tags": []}

        self.mock_catalog_client.get_website_tag_catalog = mock_tags

        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"beacon_type": "PAGELOAD", "use_case": "FILTERING"},
        ))

        self.assertIn("results", result)
        self.assertFalse(result.get("elicitation_needed"))

    def test_catalog_tag_catalog_none_beacon_type_passes_through(self):
        """get_tag_catalog with no beacon_type (optional) is still forwarded."""
        async def mock_tags(*args, **kwargs):
            return {"tags": []}

        self.mock_catalog_client.get_website_tag_catalog = mock_tags

        result = asyncio.run(self.router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"use_case": "FILTERING"},
        ))

        self.assertIn("results", result)
        self.assertFalse(result.get("elicitation_needed"))


if __name__ == "__main__":
    unittest.main()
