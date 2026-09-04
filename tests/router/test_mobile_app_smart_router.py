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
        self.mock_session_replay_client = MagicMock()

        self.router = MobileAppSmartRouterMCPTool.__new__(MobileAppSmartRouterMCPTool)
        self.router.read_token = "test_token"
        self.router.base_url = "https://test.instana.com"

        self.router.mobile_app_analyze_client = self.mock_analyze_client
        self.router.mobile_app_catalog_client = self.mock_catalog_client
        self.router.mobile_app_alert_client = self.mock_alert_client
        self.router.mobile_app_session_replay_client = self.mock_session_replay_client


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

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid resource_type", result["message"])

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
                "group": {"groupbyTag": "mobileBeacon.mobileApp.name", "groupbyTagEntity": "NOT_APPLICABLE"},
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

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid operation", result["message"])

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

        self.assertTrue(result.get("elicitation_needed"))

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
        """Validates that a canonical SCREAMING_SNAKE beacon_type is passed through
        unchanged to the tag catalog — the API expects SCREAMING_SNAKE, not camelCase."""
        captured = {}

        async def mock_tags(*args, **kwargs):
            captured["beacon_type"] = kwargs.get("beacon_type")
            return {"tags": []}

        self.mock_catalog_client.get_mobile_app_tag_catalog = mock_tags

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_tag_catalog",
            params={"beacon_type": "SESSION_START"}
        ))

        self.assertIn("results", result)
        # The tag catalog API expects SCREAMING_SNAKE_CASE — no normalization applied
        self.assertEqual(captured.get("beacon_type"), "SESSION_START")

    def test_catalog_invalid_operation(self):
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="invalid_op",
            params={}
        ))

        self.assertTrue(result.get("elicitation_needed"))


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

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid operation", result["message"])

    def test_alert_no_params(self):
        """Omitting 'id' triggers a pre-flight elicitation at the router level."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_mobile_app_alert_config",
            params={}
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("id" in e["field"] for e in result["api_error"]))

    def test_alert_invalid_operation(self):
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="invalid_op",
            params={}
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("Invalid operation", result["message"])

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


    # ------------------------------------------------------------------
    # Pre-flight StructureValidator tests (added with INSTA-77605)
    # ------------------------------------------------------------------

    def test_preflight_invalid_beacon_type(self):
        """Router rejects an invalid beacon_type before calling the service layer."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_all_mobile_app_beacons",
            params={
                "beacon_type": "NOT_A_REAL_TYPE",
                "time_frame": {"windowSize": 3600000},
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("NOT_A_REAL_TYPE" in e for e in result["api_error"]))

    def test_preflight_invalid_window_size(self):
        """Router rejects a windowSize that exceeds the SDK upper bound."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_all_mobile_app_beacons",
            params={
                "beacon_type": "SESSION_START",
                "time_frame": {"windowSize": 9_999_999_999},
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("windowSize" in e for e in result["api_error"]))

    def test_preflight_invalid_retrieval_size(self):
        """Router rejects a retrievalSize outside [1, 200]."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_all_mobile_app_beacons",
            params={
                "beacon_type": "SESSION_START",
                "pagination": {"retrievalSize": 999},
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("retrievalSize" in e for e in result["api_error"]))

    def test_preflight_invalid_aggregation_in_metrics(self):
        """Router rejects a metrics entry with an unrecognised aggregation."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={
                "metrics": [{"metric": "beaconCount", "aggregation": "INVALID_AGG"}],
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("INVALID_AGG" in e for e in result["api_error"]))

    def test_preflight_tag_filter_missing_entity(self):
        """Router rejects a TAG_FILTER that omits the required entity field."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={
                "tag_filter_expression": {
                    "type": "TAG_FILTER",
                    "name": "mobileBeacon.mobileApp.name",
                    "operator": "EQUALS",
                    "value": "MyApp",
                    # entity intentionally omitted
                }
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("entity" in e for e in result["api_error"]))

    def test_preflight_invalid_order_direction(self):
        """Router rejects an order with an invalid direction."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={
                "order": {"by": "beaconCount", "direction": "DESCENDING"},
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("direction" in e for e in result["api_error"]))

    def test_preflight_group_missing_entity(self):
        """Router rejects a group dict that omits groupbyTagEntity."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={
                "group": {"groupbyTag": "mobileBeacon.mobileApp.name"},
                # groupbyTagEntity intentionally omitted
            }
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("groupbyTagEntity" in e for e in result["api_error"]))

    def test_preflight_multiple_errors_consolidated(self):
        """Router collects ALL validation errors in a single response."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_all_mobile_app_beacons",
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

        self.mock_analyze_client.get_all_mobile_app_beacons = mock_beacons

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_all_mobile_app_beacons",
            params={
                "beacon_type": "SESSION_START",
                "time_frame": {"windowSize": 3600000},
                "pagination": {"retrievalSize": 50},
            }
        ))

        self.assertTrue(captured.get("called"), "Service layer was not called for a valid payload")
        self.assertIn("results", result)


    # ------------------------------------------------------------------
    # Pre-flight tests added for INSTA-77605 gap fixes
    # ------------------------------------------------------------------

    # --- resource_type guard ---

    def test_session_replay_resource_type_is_accepted(self):
        """resource_type='session_replay' must now pass the guard and reach the handler."""
        async def mock_beacons(*args, **kwargs):
            return {"beacons": [], "hasMore": False}

        self.mock_session_replay_client.get_session_replay_action_beacons = mock_beacons

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="session_replay",
            operation="get_session_replay_action_beacons",
            params={"mobile_app_id": "app-1", "session_id": "sess-1"},
        ))

        # Should reach the service and return results — NOT an invalid_resource_type error
        self.assertNotEqual(result.get("reason"), "invalid_resource_type")
        self.assertIn("results", result)

    # --- _handle_alert required-field guards ---

    def test_alert_find_active_missing_mobile_app_id(self):
        """find_active_mobile_app_alert_configs rejects a missing mobile_app_id before the service layer."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_active_mobile_app_alert_configs",
            params={},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(result["reason"], "missing_required_params")
        self.assertTrue(any(e["field"] == "mobile_app_id" for e in result["api_error"]))
        # Service layer must NOT have been called
        self.mock_alert_client.find_active_mobile_app_alert_configs.assert_not_called()

    def test_alert_find_config_missing_id(self):
        """find_mobile_app_alert_config rejects a missing id before the service layer."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_mobile_app_alert_config",
            params={},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(result["reason"], "missing_required_params")
        self.assertTrue(any(e["field"] == "id" for e in result["api_error"]))
        self.mock_alert_client.find_mobile_app_alert_config.assert_not_called()

    def test_alert_find_active_with_mobile_app_id_reaches_service(self):
        """find_active_mobile_app_alert_configs with a valid mobile_app_id reaches the service."""
        async def mock_find_active(*args, **kwargs):
            return {"items": []}

        self.mock_alert_client.find_active_mobile_app_alert_configs = mock_find_active

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="alert",
            operation="find_active_mobile_app_alert_configs",
            params={"mobile_app_id": "app-abc"},
        ))

        self.assertIn("results", result)
        self.assertFalse(result.get("elicitation_needed"))

    # --- _handle_session_replay invalid-op format ---

    def test_session_replay_invalid_operation_uses_elicitation_format(self):
        """Invalid session_replay operation must return elicitation_needed, not a bare error key."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="session_replay",
            operation="not_a_real_op",
            params={},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertNotIn("error", result)
        self.assertIn("api_error", result)
        self.assertTrue(any("not_a_real_op" in e["issue"] for e in result["api_error"]))

    # --- _handle_session_replay required-field guards ---

    def test_session_replay_missing_both_required_params_consolidated(self):
        """Omitting both mobile_app_id and session_id returns both errors in one response."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="session_replay",
            operation="get_session_replay_action_beacons",
            params={},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        fields = [e["field"] for e in result["api_error"]]
        self.assertIn("mobile_app_id", fields)
        self.assertIn("session_id", fields)
        self.mock_session_replay_client.get_session_replay_action_beacons.assert_not_called()

    def test_session_replay_missing_mobile_app_id_only(self):
        """Omitting only mobile_app_id while session_id is present returns the right error."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="session_replay",
            operation="get_session_replay_action_beacons",
            params={"session_id": "sess-1"},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        fields = [e["field"] for e in result["api_error"]]
        self.assertIn("mobile_app_id", fields)
        self.assertNotIn("session_id", fields)

    def test_session_replay_missing_session_id_only(self):
        """Omitting only session_id while mobile_app_id is present returns the right error."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="session_replay",
            operation="get_session_replay_action_beacons",
            params={"mobile_app_id": "app-1"},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        fields = [e["field"] for e in result["api_error"]]
        self.assertIn("session_id", fields)
        self.assertNotIn("mobile_app_id", fields)

    def test_session_replay_page_size_too_large(self):
        """page_size > 1000 is rejected at the router level."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="session_replay",
            operation="get_session_replay_action_beacons",
            params={"mobile_app_id": "app-1", "session_id": "sess-1", "page_size": 1001},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "page_size" for e in result["api_error"]))
        self.mock_session_replay_client.get_session_replay_action_beacons.assert_not_called()

    def test_session_replay_page_size_zero_rejected(self):
        """page_size=0 (below minimum of 1) is rejected at the router level."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="session_replay",
            operation="get_session_replay_action_beacons",
            params={"mobile_app_id": "app-1", "session_id": "sess-1", "page_size": 0},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any(e["field"] == "page_size" for e in result["api_error"]))

    def test_session_replay_valid_params_reach_service(self):
        """All required params present and valid — service layer is called."""
        async def mock_beacons(*args, **kwargs):
            return {"beacons": [{"id": "b1"}], "hasMore": False, "nextCursor": None}

        self.mock_session_replay_client.get_session_replay_action_beacons = mock_beacons

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="session_replay",
            operation="get_session_replay_action_beacons",
            params={"mobile_app_id": "app-1", "session_id": "sess-1", "cursor": 0, "page_size": 100},
        ))

        self.assertIn("results", result)
        self.assertFalse(result.get("elicitation_needed"))

    # --- _handle_catalog beacon_type guard for get_mobile_app_tag_catalog ---

    def test_catalog_tag_catalog_invalid_beacon_type_rejected(self):
        """get_mobile_app_tag_catalog rejects a beacon_type not in VALID_MOBILE_BEACON_TYPES."""
        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_tag_catalog",
            params={"beacon_type": "PAGELOAD", "use_case": "FILTERING"},
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertEqual(result["reason"], "invalid_beacon_type")
        self.assertTrue(any("PAGELOAD" in e["issue"] for e in result["api_error"]))
        self.mock_catalog_client.get_mobile_app_tag_catalog.assert_not_called()

    def test_catalog_tag_catalog_valid_beacon_type_reaches_service(self):
        """get_mobile_app_tag_catalog with a valid beacon_type reaches the service."""
        async def mock_tags(*args, **kwargs):
            return {"tags": []}

        self.mock_catalog_client.get_mobile_app_tag_catalog = mock_tags

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_tag_catalog",
            params={"beacon_type": "SESSION_START", "use_case": "FILTERING"},
        ))

        self.assertIn("results", result)
        self.assertFalse(result.get("elicitation_needed"))

    def test_catalog_tag_catalog_none_beacon_type_passes_through(self):
        """get_mobile_app_tag_catalog with no beacon_type (None) is still forwarded — it is optional."""
        async def mock_tags(*args, **kwargs):
            return {"tags": []}

        self.mock_catalog_client.get_mobile_app_tag_catalog = mock_tags

        result = asyncio.run(self.router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_tag_catalog",
            params={"use_case": "FILTERING"},
        ))

        self.assertIn("results", result)
        self.assertFalse(result.get("elicitation_needed"))


if __name__ == "__main__":
    unittest.main()
