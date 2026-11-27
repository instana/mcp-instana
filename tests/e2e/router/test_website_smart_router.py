"""Mocked e2e tests for the website smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.website_smart_router import WebsiteSmartRouterMCPTool


@pytest.fixture
def router(instana_credentials):
    tool = WebsiteSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.website_analyze_client = AsyncMock()
    tool.website_analyze_client.get_website_beacon_groups.return_value = {"groups": []}
    tool.website_analyze_client.get_website_beacons.return_value = {"beacons": []}
    tool.website_catalog_client = AsyncMock()
    tool.website_catalog_client.get_website_catalog_metrics.return_value = {"metrics": []}
    tool.website_catalog_client.get_website_tag_catalog.return_value = {"tags": []}
    tool.website_configuration_client = AsyncMock()
    tool.website_configuration_client.execute_website_operation.return_value = {"sites": []}
    tool.website_configuration_client.execute_advanced_config_operation.return_value = {
        "geo": {}
    }
    tool.website_alert_client = AsyncMock()
    tool.website_alert_client.find_active_website_alert_configs.return_value = {"configs": []}
    tool.website_alert_client.find_website_alert_config.return_value = {"id": "al-1"}
    return tool


class TestWebsiteSmartRouterE2E:
    """Dispatch and validation tests for WebsiteSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_resource_type_returns_elicitation(self, router):
        result = await router.manage_websites(resource_type="bogus", operation="get_all")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_resource_type"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_invalid_operation(self, router):
        result = await router.manage_websites(
            resource_type="analyze", operation="get_sessions", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_beacon_groups_forwards_parameters(self, router):
        params = {
            "beacon_type": "PAGELOAD",
            "time_frame": {"to": 1742373420000, "windowSize": 3600000},
            "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
            "group": {"groupByTag": "beacon.page.name", "groupbyTagEntity": "NOT_APPLICABLE"},
        }
        result = await router.manage_websites(
            resource_type="analyze", operation="get_beacon_groups", params=params
        )
        assert result["operation"] == "get_beacon_groups"
        assert result["results"] == {"groups": []}
        kwargs = router.website_analyze_client.get_website_beacon_groups.call_args.kwargs
        assert kwargs["beacon_type"] == "PAGELOAD"
        assert kwargs["time_frame"] == {"to": 1742373420000, "windowSize": 3600000}
        assert kwargs["fill_time_series"] is True
        assert kwargs["tool_name"] == "manage_websites"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_converts_datetime_time_frame(self, router):
        await router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={
                "beacon_type": "PAGELOAD",
                "time_frame": {"to": "10 March 2026, 2:00 PM|UTC", "windowSize": 3600000},
            },
        )
        kwargs = router.website_analyze_client.get_website_beacons.call_args.kwargs
        assert isinstance(kwargs["time_frame"]["to"], int)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_invalid_datetime_returns_elicitation(self, router):
        result = await router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={"time_frame": {"to": "not a real date", "windowSize": 3600000}},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_time_params"
        router.website_analyze_client.get_website_beacons.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_preflight_collects_validation_errors(self, router):
        result = await router.manage_websites(
            resource_type="analyze",
            operation="get_beacon_groups",
            params={"beacon_type": "NOT_A_BEACON", "time_frame": {"windowSize": 1000}},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"].startswith("analyze 'get_beacon_groups' payload has")
        router.website_analyze_client.get_website_beacon_groups.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_get_beacons_routes_without_group(self, router):
        result = await router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={
                "beacon_type": "PAGELOAD",
                "time_frame": {"to": 1742373420000, "windowSize": 3600000},
                "pagination": {"retrievalSize": 50},
            },
        )
        assert result["results"] == {"beacons": []}
        kwargs = router.website_analyze_client.get_website_beacons.call_args.kwargs
        assert kwargs["pagination"] == {"retrievalSize": 50}
        router.website_analyze_client.get_website_beacon_groups.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_invalid_operation(self, router):
        result = await router.manage_websites(resource_type="catalog", operation="drop")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_metrics_defaults_view(self, router):
        result = await router.manage_websites(resource_type="catalog", operation="get_metrics")
        assert result["results"] == {"metrics": []}
        kwargs = router.website_catalog_client.get_website_catalog_metrics.call_args.kwargs
        assert kwargs["view"] == "planner"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tag_catalog_requires_use_case_and_valid_beacon(self, router):
        result = await router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"beacon_type": "NOT_A_BEACON"},
        )
        assert result["elicitation_needed"] is True
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["use_case", "beacon_type"]
        router.website_catalog_client.get_website_tag_catalog.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tag_catalog_forwards_valid_request(self, router):
        result = await router.manage_websites(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"beacon_type": "PAGELOAD", "use_case": "GROUPING"},
        )
        assert result["results"] == {"tags": []}
        kwargs = router.website_catalog_client.get_website_tag_catalog.call_args.kwargs
        assert kwargs["use_case"] == "GROUPING"
        assert kwargs["beacon_type"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_invalid_operation(self, router):
        result = await router.manage_websites(resource_type="configuration", operation="create")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_get_forwards_name(self, router):
        result = await router.manage_websites(
            resource_type="configuration",
            operation="get",
            params={"website_name": "robot-shop"},
        )
        assert result["website_name"] == "robot-shop"
        assert result["website_id"] is None
        kwargs = router.website_configuration_client.execute_website_operation.call_args.kwargs
        assert kwargs["operation"] == "get"
        assert kwargs["website_name"] == "robot-shop"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_advanced_config_invalid_operation(self, router):
        result = await router.manage_websites(
            resource_type="advanced_config", operation="set_geo_config"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_advanced_config_forwards_website_id(self, router):
        result = await router.manage_websites(
            resource_type="advanced_config",
            operation="get_ip_masking",
            params={"website_id": "site-1"},
        )
        assert result["website_id"] == "site-1"
        assert result["results"] == {"geo": {}}
        kwargs = router.website_configuration_client.execute_advanced_config_operation.call_args.kwargs
        assert kwargs["operation"] == "get_ip_masking"
        assert kwargs["website_id"] == "site-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_invalid_operation(self, router):
        result = await router.manage_websites(resource_type="alert", operation="invalid_op")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_active_requires_website_id(self, router):
        result = await router.manage_websites(
            resource_type="alert",
            operation="find_active_website_alert_configs",
            params={},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        router.website_alert_client.find_active_website_alert_configs.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_active_forwards_ids(self, router):
        result = await router.manage_websites(
            resource_type="alert",
            operation="find_active_website_alert_configs",
            params={"website_id": "site-1", "alert_ids": ["al-1"]},
        )
        assert result["results"] == {"configs": []}
        kwargs = router.website_alert_client.find_active_website_alert_configs.call_args.kwargs
        assert kwargs["website_id"] == "site-1"
        assert kwargs["alert_ids"] == ["al-1"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_requires_id(self, router):
        result = await router.manage_websites(
            resource_type="alert", operation="find_website_alert_config", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        router.website_alert_client.find_website_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_forwards_id_and_valid_on(self, router):
        result = await router.manage_websites(
            resource_type="alert",
            operation="find_website_alert_config",
            params={"id": "al-1", "valid_on": 1742373420000},
        )
        assert result["results"] == {"id": "al-1"}
        kwargs = router.website_alert_client.find_website_alert_config.call_args.kwargs
        assert kwargs["id"] == "al-1"
        assert kwargs["valid_on"] == 1742373420000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_error(self, router):
        router.website_analyze_client.get_website_beacons.side_effect = RuntimeError("down")
        result = await router.manage_websites(
            resource_type="analyze",
            operation="get_beacons",
            params={"beacon_type": "PAGELOAD"},
        )
        assert result["error"] == "Smart router error: down"
        assert result["resource_type"] == "analyze"
