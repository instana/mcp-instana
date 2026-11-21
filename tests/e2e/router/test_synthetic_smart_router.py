"""Mocked e2e tests for the synthetic smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.synthetic_smart_router_tool import SyntheticSmartRouterMCPTool


@pytest.fixture
def router(instana_credentials):
    tool = SyntheticSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.synthetic_catalog_client = AsyncMock()
    tool.synthetic_catalog_client.get_synthetic_catalog_metrics.return_value = {"metrics": []}
    tool.synthetic_catalog_client.get_synthetic_tag_catalog.return_value = {"tags": []}
    tool.synthetic_metrics_client = AsyncMock()
    tool.synthetic_metrics_client.get_metrics_result.return_value = {"values": []}
    tool.synthetic_settings_client = AsyncMock()
    tool.synthetic_settings_client.get_synthetic_test.return_value = {"id": "t-1"}
    tool.synthetic_settings_client.get_synthetic_tests.return_value = {"items": []}
    tool.synthetic_settings_client.get_locations.return_value = {"items": []}
    tool.synthetic_settings_client.get_location_by_id.return_value = {"id": "loc-1"}
    tool.synthetic_settings_client.get_all_datacenters.return_value = {"items": []}
    tool.synthetic_test_playback_client = AsyncMock()
    tool.synthetic_test_playback_client.execute_playback_operation.return_value = {
        "rows": []
    }
    tool.synthetic_alert_client = AsyncMock()
    tool.synthetic_alert_client.find_active_synthetic_alert_configs.return_value = {
        "configs": []
    }
    tool.synthetic_alert_client.find_synthetic_alert_config.return_value = {"id": "al-1"}
    tool.synthetic_alert_client.find_synthetic_alert_config_versions.return_value = {
        "versions": []
    }
    tool.synthetic_alert_client.create_synthetic_alert_config.return_value = {"id": "al-new"}
    tool.synthetic_alert_client.update_synthetic_alert_config.return_value = {"id": "al-1"}
    tool.synthetic_alert_client.delete_synthetic_alert_config.return_value = {"deleted": True}
    tool.synthetic_alert_client.enable_synthetic_alert_config.return_value = {"enabled": True}
    tool.synthetic_alert_client.disable_synthetic_alert_config.return_value = {"enabled": False}
    tool.synthetic_alert_client.restore_synthetic_alert_config.return_value = {"id": "al-1"}
    return tool


class TestSyntheticSmartRouterE2E:
    """Dispatch and validation tests for SyntheticSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_resource_type_returns_elicitation(self, router):
        result = await router.manage_synthetics(resource_type="bogus", operation="find")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_resource_type"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_metrics_defaults_view(self, router):
        result = await router.manage_synthetics(
            resource_type="catalog", operation="get_synthetic_catalog_metrics"
        )
        assert result["results"] == {"metrics": []}
        kwargs = router.synthetic_catalog_client.get_synthetic_catalog_metrics.call_args.kwargs
        assert kwargs["view"] == "planner"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_invalid_operation(self, router):
        result = await router.manage_synthetics(resource_type="catalog", operation="nope")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tag_catalog_requires_use_case(self, router):
        result = await router.manage_synthetics(
            resource_type="catalog", operation="get_synthetic_tag_catalog", params={}
        )
        assert result["elicitation_needed"] is True
        assert "use_case" in result["reason"]
        router.synthetic_catalog_client.get_synthetic_tag_catalog.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tag_catalog_forwards_use_case(self, router):
        result = await router.manage_synthetics(
            resource_type="catalog",
            operation="get_synthetic_tag_catalog",
            params={"use_case": "FILTERING"},
        )
        assert result["results"] == {"tags": []}
        kwargs = router.synthetic_catalog_client.get_synthetic_tag_catalog.call_args.kwargs
        assert kwargs["use_case"] == "FILTERING"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metrics_invalid_operation(self, router):
        result = await router.manage_synthetics(resource_type="metrics", operation="series")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metrics_forwards_payload(self, router):
        payload = {"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        result = await router.manage_synthetics(
            resource_type="metrics",
            operation="get_metrics_result",
            params={"payload": payload},
        )
        assert result["resource_type"] == "metrics"
        assert result["results"] == {"values": []}
        kwargs = router.synthetic_metrics_client.get_metrics_result.call_args.kwargs
        assert kwargs["payload"] == payload

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_invalid_operation(self, router):
        result = await router.manage_synthetics(resource_type="settings", operation="delete")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_get_synthetic_test_forwards_name(self, router):
        result = await router.manage_synthetics(
            resource_type="settings",
            operation="get_synthetic_test",
            params={"test_name": "Login Flow"},
        )
        assert result["results"] == {"id": "t-1"}
        kwargs = router.synthetic_settings_client.get_synthetic_test.call_args.kwargs
        assert kwargs["test_name"] == "Login Flow"
        assert kwargs["test_id"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_get_synthetic_tests_maps_filter(self, router):
        await router.manage_synthetics(
            resource_type="settings",
            operation="get_synthetic_tests",
            params={"limit": 20, "sort": "+label", "filter": "prod"},
        )
        kwargs = router.synthetic_settings_client.get_synthetic_tests.call_args.kwargs
        assert kwargs["limit"] == 20
        assert kwargs["sort"] == "+label"
        assert kwargs["filter_param"] == "prod"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_page_navigation_reruns_get_synthetic_tests(self, router):
        await router.manage_synthetics(
            resource_type="settings", operation="page_3", params={"page_size": 10}
        )
        kwargs = router.synthetic_settings_client.get_synthetic_tests.call_args.kwargs
        assert kwargs["page"] == 3
        assert kwargs["page_size"] == 10

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_get_locations_forwards_filters(self, router):
        await router.manage_synthetics(
            resource_type="settings",
            operation="get_locations",
            params={"location_type": "Managed", "status": "Online"},
        )
        kwargs = router.synthetic_settings_client.get_locations.call_args.kwargs
        assert kwargs["location_type"] == "Managed"
        assert kwargs["status"] == "Online"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_get_location_by_id_forwards_name(self, router):
        await router.manage_synthetics(
            resource_type="settings",
            operation="get_location_by_id",
            params={"location_name": "ap-south-1(Mumbai)"},
        )
        kwargs = router.synthetic_settings_client.get_location_by_id.call_args.kwargs
        assert kwargs["location_name"] == "ap-south-1(Mumbai)"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_get_all_datacenters_forwards_status(self, router):
        result = await router.manage_synthetics(
            resource_type="settings",
            operation="get_all_datacenters",
            params={"status": "Online"},
        )
        assert result["operation"] == "get_all_datacenters"
        kwargs = router.synthetic_settings_client.get_all_datacenters.call_args.kwargs
        assert kwargs["status"] == "Online"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_test_playback_invalid_operation(self, router):
        result = await router.manage_synthetics(
            resource_type="test_playback", operation="purge"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_test_playback_delegates_params_unchanged(self, router):
        params = {"payload": {"metrics": [], "timeFrame": {"windowSize": 3600000}}}
        result = await router.manage_synthetics(
            resource_type="test_playback",
            operation="get_test_summary_list",
            params=params,
        )
        assert result == {
            "resource_type": "test_playback",
            "operation": "get_test_summary_list",
            "results": {"rows": []},
        }
        kwargs = router.synthetic_test_playback_client.execute_playback_operation.call_args.kwargs
        assert kwargs["operation"] == "get_test_summary_list"
        assert kwargs["params"] == params

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_invalid_operation(self, router):
        result = await router.manage_synthetics(resource_type="alert", operation="mute")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_active_coerces_pagination_and_alias(self, router):
        result = await router.manage_synthetics(
            resource_type="alert",
            operation="find_active",
            params={"page": "2", "pageSize": 25, "alert_ids": "a1, a2"},
        )
        assert result["operation"] == "find_active"
        kwargs = router.synthetic_alert_client.find_active_synthetic_alert_configs.call_args.kwargs
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 25
        assert kwargs["alert_ids"] == ["a1", "a2"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_active_rejects_non_integer_page(self, router):
        result = await router.manage_synthetics(
            resource_type="alert",
            operation="find_active",
            params={"page": "two"},
        )
        assert result["error"] == "'page' must be an integer, got 'two'"
        router.synthetic_alert_client.find_active_synthetic_alert_configs.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_requires_id(self, router):
        result = await router.manage_synthetics(resource_type="alert", operation="find", params={})
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "id"
        router.synthetic_alert_client.find_synthetic_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_coerces_valid_on(self, router):
        await router.manage_synthetics(
            resource_type="alert",
            operation="find",
            params={"id": "al-1", "valid_on": "1742369820000"},
        )
        kwargs = router.synthetic_alert_client.find_synthetic_alert_config.call_args.kwargs
        assert kwargs["valid_on"] == 1742369820000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_create_requires_payload(self, router):
        result = await router.manage_synthetics(resource_type="alert", operation="create", params={})
        assert result["elicitation_needed"] is True
        assert "payload" in result["message"]
        router.synthetic_alert_client.create_synthetic_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_create_forwards_payload(self, router):
        payload = {"name": "Login failing", "syntheticTestIds": ["t-1"]}
        result = await router.manage_synthetics(
            resource_type="alert", operation="create", params={"payload": payload}
        )
        assert result["results"] == {"id": "al-new"}
        kwargs = router.synthetic_alert_client.create_synthetic_alert_config.call_args.kwargs
        assert kwargs["payload"] == payload

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_update_requires_id_and_payload(self, router):
        result = await router.manage_synthetics(resource_type="alert", operation="update", params={"id": "al-1"})
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "payload"
        router.synthetic_alert_client.update_synthetic_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_update_forwards_id_and_payload(self, router):
        await router.manage_synthetics(
            resource_type="alert",
            operation="update",
            params={"id": "al-1", "payload": {"name": "x"}},
        )
        kwargs = router.synthetic_alert_client.update_synthetic_alert_config.call_args.kwargs
        assert kwargs["id"] == "al-1"
        assert kwargs["payload"] == {"name": "x"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation", ["find_versions", "delete", "enable", "disable"])
    async def test_alert_id_only_operations_require_id(self, router, operation):
        result = await router.manage_synthetics(resource_type="alert", operation=operation, params={})
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "id"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_enable_and_disable_route_to_client(self, router):
        enabled = await router.manage_synthetics(
            resource_type="alert", operation="enable", params={"id": "al-1"}
        )
        disabled = await router.manage_synthetics(
            resource_type="alert", operation="disable", params={"id": "al-1"}
        )
        assert enabled["results"] == {"enabled": True}
        assert disabled["results"] == {"enabled": False}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_restore_requires_created(self, router):
        result = await router.manage_synthetics(
            resource_type="alert", operation="restore", params={"id": "al-1"}
        )
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "created"
        router.synthetic_alert_client.restore_synthetic_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_restore_coerces_created(self, router):
        await router.manage_synthetics(
            resource_type="alert",
            operation="restore",
            params={"id": "al-1", "created": "1742369820000"},
        )
        kwargs = router.synthetic_alert_client.restore_synthetic_alert_config.call_args.kwargs
        assert kwargs["created"] == 1742369820000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_delete_forwards_id(self, router):
        result = await router.manage_synthetics(
            resource_type="alert", operation="delete", params={"id": "al-1"}
        )
        assert result["operation"] == "delete"
        assert router.synthetic_alert_client.delete_synthetic_alert_config.call_args.kwargs["id"] == "al-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_error(self, router):
        router.synthetic_metrics_client.get_metrics_result.side_effect = RuntimeError("down")
        result = await router.manage_synthetics(
            resource_type="metrics",
            operation="get_metrics_result",
            params={"payload": {"metrics": []}},
        )
        assert "down" in result["error"]
        assert result["resource_type"] == "metrics"
