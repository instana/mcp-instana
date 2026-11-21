"""Mocked e2e tests for the mobile app smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.mobile_app_smart_router import MobileAppSmartRouterMCPTool


@pytest.fixture
def router(instana_credentials):
    tool = MobileAppSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.mobile_app_analyze_client = AsyncMock()
    tool.mobile_app_analyze_client.get_mobile_app_beacon_groups.return_value = {"groups": []}
    tool.mobile_app_analyze_client.get_all_mobile_app_beacons.return_value = {"beacons": []}
    tool.mobile_app_catalog_client = AsyncMock()
    tool.mobile_app_catalog_client.get_mobile_app_metric_catalog.return_value = {"metrics": []}
    tool.mobile_app_catalog_client.get_mobile_app_tag_catalog.return_value = {"tags": []}
    tool.mobile_app_configuration_client = AsyncMock()
    tool.mobile_app_configuration_client.execute_mobile_app_operation.return_value = {
        "apps": []
    }
    tool.mobile_app_configuration_client.execute_mobile_app_advanced_config_operation.return_value = {
        "geo": {}
    }
    tool.mobile_app_alert_client = AsyncMock()
    tool.mobile_app_alert_client.find_active_mobile_app_alert_configs.return_value = {
        "configs": []
    }
    tool.mobile_app_alert_client.find_mobile_app_alert_config.return_value = {"id": "a-1"}
    tool.mobile_app_session_client = AsyncMock()
    tool.mobile_app_session_client.get_session_beacons.return_value = {"beacons": []}
    tool.mobile_app_session_replay_client = AsyncMock()
    tool.mobile_app_session_replay_client.get_session_replay_action_beacons.return_value = {
        "beacons": [],
        "hasMore": False,
    }
    return tool


class TestMobileAppSmartRouterE2E:
    """Dispatch and validation tests for MobileAppSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_resource_type_returns_elicitation(self, router):
        result = await router.manage_mobile_apps(resource_type="bogus", operation="get_all")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_resource_type"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_invalid_operation(self, router):
        result = await router.manage_mobile_apps(resource_type="analyze", operation="drop")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_beacon_groups_forwards_parameters(self, router):
        params = {
            "beacon_type": "SESSION_START",
            "time_frame": {"to": 1742373420000, "windowSize": 3600000},
            "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
            "group": {"groupByTag": "mobileBeacon.view.name", "groupbyTagEntity": "NOT_APPLICABLE"},
        }
        result = await router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params=params,
        )
        assert result["operation"] == "get_mobile_app_beacon_groups"
        assert result["results"] == {"groups": []}
        kwargs = router.mobile_app_analyze_client.get_mobile_app_beacon_groups.call_args.kwargs
        assert kwargs["beacon_type"] == "SESSION_START"
        assert kwargs["fill_time_series"] is True
        assert kwargs["resource_type"] == "analyze"
        assert kwargs["tool_name"] == "manage_mobile_apps"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_preflight_collects_validation_errors(self, router):
        result = await router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_mobile_app_beacon_groups",
            params={"beacon_type": "NOT_A_BEACON", "time_frame": {"windowSize": 1000}},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"].startswith("analyze 'get_mobile_app_beacon_groups' payload has")
        router.mobile_app_analyze_client.get_mobile_app_beacon_groups.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_get_all_beacons_routes_correctly(self, router):
        result = await router.manage_mobile_apps(
            resource_type="analyze",
            operation="get_all_mobile_app_beacons",
            params={
                "beacon_type": "SESSION_START",
                "time_frame": {"to": 1742373420000, "windowSize": 3600000},
                "pagination": {"retrievalSize": 50},
                "filter_fields": False,
            },
        )
        assert result["results"] == {"beacons": []}
        kwargs = router.mobile_app_analyze_client.get_all_mobile_app_beacons.call_args.kwargs
        assert kwargs["filter_fields"] is False
        assert kwargs["pagination"] == {"retrievalSize": 50}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_invalid_operation(self, router):
        result = await router.manage_mobile_apps(resource_type="catalog", operation="nope")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_metric_catalog_defaults_view(self, router):
        result = await router.manage_mobile_apps(
            resource_type="catalog", operation="get_mobile_app_metric_catalog"
        )
        assert result["results"] == {"metrics": []}
        kwargs = router.mobile_app_catalog_client.get_mobile_app_metric_catalog.call_args.kwargs
        assert kwargs["view"] == "planner"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tag_catalog_rejects_invalid_beacon_type(self, router):
        result = await router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_tag_catalog",
            params={"beacon_type": "BOGUS", "use_case": "FILTERING"},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_beacon_type"
        router.mobile_app_catalog_client.get_mobile_app_tag_catalog.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tag_catalog_forwards_valid_beacon_type(self, router):
        result = await router.manage_mobile_apps(
            resource_type="catalog",
            operation="get_mobile_app_tag_catalog",
            params={"beacon_type": "SESSION_START", "use_case": "FILTERING"},
        )
        assert result["results"] == {"tags": []}
        kwargs = router.mobile_app_catalog_client.get_mobile_app_tag_catalog.call_args.kwargs
        assert kwargs["use_case"] == "FILTERING"
        assert kwargs["beacon_type"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_invalid_operation(self, router):
        result = await router.manage_mobile_apps(
            resource_type="configuration", operation="create"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_get_forwards_name(self, router):
        result = await router.manage_mobile_apps(
            resource_type="configuration",
            operation="get",
            params={"mobile_app_name": "robot-shop"},
        )
        assert result["mobile_app_name"] == "robot-shop"
        assert result["mobile_app_id"] is None
        kwargs = router.mobile_app_configuration_client.execute_mobile_app_operation.call_args.kwargs
        assert kwargs["operation"] == "get"
        assert kwargs["mobile_app_name"] == "robot-shop"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_advanced_config_invalid_operation(self, router):
        result = await router.manage_mobile_apps(
            resource_type="advanced_config", operation="set_geo_config"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_advanced_config_forwards_config_id(self, router):
        result = await router.manage_mobile_apps(
            resource_type="advanced_config",
            operation="get_geo_config",
            params={"mobile_app_id": "app-1", "config_id": "cfg-9"},
        )
        assert result["mobile_app_id"] == "app-1"
        assert result["config_id"] == "cfg-9"
        kwargs = (
            router.mobile_app_configuration_client.execute_mobile_app_advanced_config_operation.call_args.kwargs
        )
        assert kwargs["config_id"] == "cfg-9"
        assert kwargs["mobile_app_id"] == "app-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_invalid_operation(self, router):
        result = await router.manage_mobile_apps(resource_type="alert", operation="delete")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_active_requires_mobile_app_id(self, router):
        result = await router.manage_mobile_apps(
            resource_type="alert",
            operation="find_active_mobile_app_alert_configs",
            params={},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        router.mobile_app_alert_client.find_active_mobile_app_alert_configs.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_active_forwards_ids(self, router):
        result = await router.manage_mobile_apps(
            resource_type="alert",
            operation="find_active_mobile_app_alert_configs",
            params={"mobile_app_id": "app-1", "alert_ids": ["a1"]},
        )
        assert result["results"] == {"configs": []}
        kwargs = router.mobile_app_alert_client.find_active_mobile_app_alert_configs.call_args.kwargs
        assert kwargs["mobile_app_id"] == "app-1"
        assert kwargs["alert_ids"] == ["a1"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_requires_id(self, router):
        result = await router.manage_mobile_apps(
            resource_type="alert", operation="find_mobile_app_alert_config", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        router.mobile_app_alert_client.find_mobile_app_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_forwards_id_and_valid_on(self, router):
        result = await router.manage_mobile_apps(
            resource_type="alert",
            operation="find_mobile_app_alert_config",
            params={"id": "a-1", "valid_on": 1742373420000},
        )
        assert result["results"] == {"id": "a-1"}
        kwargs = router.mobile_app_alert_client.find_mobile_app_alert_config.call_args.kwargs
        assert kwargs["id"] == "a-1"
        assert kwargs["valid_on"] == 1742373420000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_session_invalid_operation(self, router):
        result = await router.manage_mobile_apps(resource_type="session", operation="close")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_session_get_session_beacons_forwards_ids(self, router):
        result = await router.manage_mobile_apps(
            resource_type="session",
            operation="get_session_beacons",
            params={"session_id": "s-1", "timestamp": 1785786779333},
        )
        assert result["results"] == {"beacons": []}
        kwargs = router.mobile_app_session_client.get_session_beacons.call_args.kwargs
        assert kwargs["session_id"] == "s-1"
        assert kwargs["timestamp"] == 1785786779333

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_session_replay_reports_all_missing_fields(self, router):
        result = await router.manage_mobile_apps(
            resource_type="session",
            operation="get_session_replay_action_beacons",
            params={},
        )
        assert result["elicitation_needed"] is True
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["mobile_app_id", "session_id"]
        router.mobile_app_session_replay_client.get_session_replay_action_beacons.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("page_size", [0, 1001])
    async def test_session_replay_rejects_out_of_range_page_size(self, router, page_size):
        result = await router.manage_mobile_apps(
            resource_type="session",
            operation="get_session_replay_action_beacons",
            params={"mobile_app_id": "app-1", "session_id": "s-1", "page_size": page_size},
        )
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "page_size"
        assert "out of range" in result["api_error"][0]["issue"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_session_replay_rejects_non_integer_page_size(self, router):
        result = await router.manage_mobile_apps(
            resource_type="session",
            operation="get_session_replay_action_beacons",
            params={"mobile_app_id": "app-1", "session_id": "s-1", "page_size": "10"},
        )
        assert result["elicitation_needed"] is True
        assert "must be an integer" in result["api_error"][0]["issue"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_session_replay_forwards_cursor_and_page_size(self, router):
        result = await router.manage_mobile_apps(
            resource_type="session",
            operation="get_session_replay_action_beacons",
            params={
                "mobile_app_id": "app-1",
                "session_id": "s-1",
                "cursor": 100,
                "page_size": 100,
            },
        )
        assert result["results"]["hasMore"] is False
        kwargs = router.mobile_app_session_replay_client.get_session_replay_action_beacons.call_args.kwargs
        assert kwargs["cursor"] == 100
        assert kwargs["page_size"] == 100
        assert kwargs["mobile_app_id"] == "app-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_error(self, router):
        router.mobile_app_session_client.get_session_beacons.side_effect = RuntimeError(
            "down"
        )
        result = await router.manage_mobile_apps(
            resource_type="session",
            operation="get_session_beacons",
            params={"session_id": "s-1", "timestamp": 1},
        )
        assert "down" in result["error"]
        assert result["resource_type"] == "session"
