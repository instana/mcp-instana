"""Mocked e2e tests for the SLO smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.slo_smart_router_tool import SLOSmartRouterMCPTool


@pytest.fixture
def router(instana_credentials):
    tool = SLOSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.slo_config_client = AsyncMock()
    tool.slo_config_client.get_all_slo_configs.return_value = {"items": []}
    tool.slo_config_client.get_slo_config_by_id.return_value = {"id": "slo-1"}
    tool.slo_config_client.create_slo_config.return_value = {"id": "slo-new"}
    tool.slo_config_client.update_slo_config.return_value = {"id": "slo-1"}
    tool.slo_config_client.delete_slo_config.return_value = {"deleted": True}
    tool.slo_config_client.get_all_slo_config_tags.return_value = {"tags": []}
    tool.slo_report_client = AsyncMock()
    tool.slo_report_client.get_slo_report.return_value = {"sli": 0.99}
    tool.slo_alert_client = AsyncMock()
    tool.slo_alert_client.find_active_alert_configs.return_value = {"alerts": []}
    tool.slo_alert_client.find_alert_config.return_value = {"id": "al-1"}
    tool.slo_alert_client.find_alert_config_versions.return_value = {"versions": []}
    tool.slo_alert_client.create_alert_config.return_value = {"id": "al-new"}
    tool.slo_alert_client.update_alert_config.return_value = {"id": "al-1"}
    tool.slo_alert_client.delete_alert_config.return_value = {"deleted": True}
    tool.slo_alert_client.disable_alert_config.return_value = {"enabled": False}
    tool.slo_alert_client.enable_alert_config.return_value = {"enabled": True}
    tool.slo_alert_client.restore_alert_config.return_value = {"id": "al-1"}
    tool.slo_correction_client = AsyncMock()
    tool.slo_correction_client.get_all_corrections.return_value = {"items": []}
    tool.slo_correction_client.get_correction_by_id.return_value = {"id": "cor-1"}
    tool.slo_correction_client.create_correction.return_value = {"id": "cor-new"}
    tool.slo_correction_client.update_correction.return_value = {"id": "cor-1"}
    tool.slo_correction_client.delete_correction.return_value = {"deleted": True}
    return tool


class TestSLOSmartRouterE2E:
    """Dispatch and validation tests for SLOSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_resource_type_returns_elicitation(self, router):
        result = await router.manage_slo(resource_type="bogus", operation="get_all")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_resource_type"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_invalid_operation(self, router):
        result = await router.manage_slo(resource_type="configuration", operation="patch")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_get_all_maps_filters(self, router):
        result = await router.manage_slo(
            resource_type="configuration",
            operation="get_all",
            params={"page_size": 5, "query": "api", "slo_status": "BREACHED"},
        )
        assert result == {
            "resource_type": "configuration",
            "operation": "get_all",
            "results": {"items": []},
        }
        filters = router.slo_config_client.get_all_slo_configs.call_args.kwargs["filters"]
        assert filters["page_size"] == 5
        assert filters["query"] == "api"
        assert filters["slo_status"] == "BREACHED"
        assert filters["page"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_get_by_id_requires_id(self, router):
        result = await router.manage_slo(
            resource_type="configuration", operation="get_by_id", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "id"
        router.slo_config_client.get_slo_config_by_id.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_get_by_id_forwards_id_and_refresh(self, router):
        result = await router.manage_slo(
            resource_type="configuration",
            operation="get_by_id",
            params={"id": "slo-1", "refresh": True},
        )
        assert result["results"] == {"id": "slo-1"}
        kwargs = router.slo_config_client.get_slo_config_by_id.call_args.kwargs
        assert kwargs["id"] == "slo-1"
        assert kwargs["refresh"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_create_requires_payload(self, router):
        result = await router.manage_slo(
            resource_type="configuration", operation="create", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "payload"
        router.slo_config_client.create_slo_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_create_forwards_payload(self, router):
        payload = {"name": "API SLO", "target": 0.99}
        result = await router.manage_slo(
            resource_type="configuration",
            operation="create",
            params={"payload": payload},
        )
        assert result["results"] == {"id": "slo-new"}
        assert router.slo_config_client.create_slo_config.call_args.kwargs["payload"] == payload

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_update_reports_missing_id_and_payload(self, router):
        result = await router.manage_slo(
            resource_type="configuration", operation="update", params={}
        )
        assert result["elicitation_needed"] is True
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["id", "payload"]
        router.slo_config_client.update_slo_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_update_includes_id_in_response(self, router):
        result = await router.manage_slo(
            resource_type="configuration",
            operation="update",
            params={"id": "slo-1", "payload": {"name": "x"}},
        )
        assert result["id"] == "slo-1"
        kwargs = router.slo_config_client.update_slo_config.call_args.kwargs
        assert kwargs["id"] == "slo-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_delete_requires_id(self, router):
        result = await router.manage_slo(
            resource_type="configuration", operation="delete", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "id"
        router.slo_config_client.delete_slo_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_delete_forwards_id(self, router):
        result = await router.manage_slo(
            resource_type="configuration", operation="delete", params={"id": "slo-1"}
        )
        assert result["id"] == "slo-1"
        assert router.slo_config_client.delete_slo_config.call_args.kwargs["id"] == "slo-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configuration_get_tags_forwards_filters(self, router):
        await router.manage_slo(
            resource_type="configuration",
            operation="get_tags",
            params={"query": "prod", "tag": "team-a", "entity_type": "application"},
        )
        kwargs = router.slo_config_client.get_all_slo_config_tags.call_args.kwargs
        assert kwargs["query"] == "prod"
        assert kwargs["tag"] == "team-a"
        assert kwargs["entity_type"] == "application"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_report_invalid_operation(self, router):
        result = await router.manage_slo(resource_type="report", operation="export")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_report_requires_slo_id(self, router):
        result = await router.manage_slo(resource_type="report", operation="get", params={})
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "slo_id"
        router.slo_report_client.get_slo_report.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_report_requires_timezone_on_var_from(self, router):
        result = await router.manage_slo(
            resource_type="report",
            operation="get",
            params={"slo_id": "slo-1", "var_from": "10 March 2026, 2:00 PM"},
        )
        assert result["missing_parameters"] == ["timezone"]
        router.slo_report_client.get_slo_report.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_report_converts_timezone_aware_datetimes(self, router):
        result = await router.manage_slo(
            resource_type="report",
            operation="get",
            params={
                "slo_id": "slo-1",
                "var_from": "10 March 2026, 2:00 PM|UTC",
                "to": "17 March 2026, 2:00 PM|UTC",
                "exclude_correction_id": "cor-9",
            },
        )
        assert result["results"] == {"sli": 0.99}
        kwargs = router.slo_report_client.get_slo_report.call_args.kwargs
        assert kwargs["slo_id"] == "slo-1"
        assert kwargs["var_from"].isdigit()
        assert kwargs["to"].isdigit()
        assert kwargs["exclude_correction_id"] == "cor-9"
        assert kwargs["include_correction_id"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_report_passes_numeric_timestamps_through(self, router):
        await router.manage_slo(
            resource_type="report",
            operation="get",
            params={"slo_id": "slo-1", "var_from": 1742369820000, "to": 1742373420000},
        )
        kwargs = router.slo_report_client.get_slo_report.call_args.kwargs
        assert kwargs["var_from"] == 1742369820000
        assert kwargs["to"] == 1742373420000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_invalid_operation(self, router):
        result = await router.manage_slo(resource_type="alert", operation="pause")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_active_forwards_slo_id(self, router):
        result = await router.manage_slo(
            resource_type="alert",
            operation="find_active",
            params={"slo_id": "slo-1", "alert_ids": ["al-1"]},
        )
        assert result["results"] == {"alerts": []}
        kwargs = router.slo_alert_client.find_active_alert_configs.call_args.kwargs
        assert kwargs["slo_id"] == "slo-1"
        assert kwargs["alert_ids"] == ["al-1"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_find_forwards_valid_on(self, router):
        await router.manage_slo(
            resource_type="alert",
            operation="find",
            params={"id": "al-1", "valid_on": 1742369820000},
        )
        kwargs = router.slo_alert_client.find_alert_config.call_args.kwargs
        assert kwargs["id"] == "al-1"
        assert kwargs["valid_on"] == 1742369820000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation", ["find", "find_versions", "delete", "enable", "disable"])
    async def test_alert_id_required_operations(self, router, operation):
        result = await router.manage_slo(resource_type="alert", operation=operation, params={})
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "id"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_create_requires_payload(self, router):
        result = await router.manage_slo(resource_type="alert", operation="create", params={})
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "payload"
        router.slo_alert_client.create_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_create_forwards_payload(self, router):
        payload = {"name": "Burn"}
        result = await router.manage_slo(
            resource_type="alert", operation="create", params={"payload": payload}
        )
        assert result["results"] == {"id": "al-new"}
        assert router.slo_alert_client.create_alert_config.call_args.kwargs["payload"] == payload

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_update_requires_id_and_payload(self, router):
        result = await router.manage_slo(resource_type="alert", operation="update", params={})
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["id", "payload"]
        router.slo_alert_client.update_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_update_forwards_id_and_payload(self, router):
        await router.manage_slo(
            resource_type="alert",
            operation="update",
            params={"id": "al-1", "payload": {"name": "x"}},
        )
        kwargs = router.slo_alert_client.update_alert_config.call_args.kwargs
        assert kwargs["id"] == "al-1"
        assert kwargs["payload"] == {"name": "x"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_restore_requires_created(self, router):
        result = await router.manage_slo(
            resource_type="alert", operation="restore", params={"id": "al-1"}
        )
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "created"
        router.slo_alert_client.restore_alert_config.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_restore_forwards_created(self, router):
        await router.manage_slo(
            resource_type="alert",
            operation="restore",
            params={"id": "al-1", "created": 1742369820000},
        )
        kwargs = router.slo_alert_client.restore_alert_config.call_args.kwargs
        assert kwargs["created"] == 1742369820000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_enable_and_disable_route_to_client(self, router):
        enabled = await router.manage_slo(
            resource_type="alert", operation="enable", params={"id": "al-1"}
        )
        disabled = await router.manage_slo(
            resource_type="alert", operation="disable", params={"id": "al-1"}
        )
        assert enabled["results"] == {"enabled": True}
        assert disabled["results"] == {"enabled": False}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_invalid_operation(self, router):
        result = await router.manage_slo(resource_type="correction", operation="pause")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_get_all_forwards_filters(self, router):
        result = await router.manage_slo(
            resource_type="correction",
            operation="get_all",
            params={"slo_id": "slo-1", "page_size": 3},
        )
        assert result["results"] == {"items": []}
        kwargs = router.slo_correction_client.get_all_corrections.call_args.kwargs
        assert kwargs["slo_id"] == "slo-1"
        assert kwargs["page_size"] == 3

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_get_by_id_requires_id(self, router):
        result = await router.manage_slo(
            resource_type="correction", operation="get_by_id", params={}
        )
        assert result["elicitation_needed"] is True
        router.slo_correction_client.get_correction_by_id.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_create_requires_payload(self, router):
        result = await router.manage_slo(resource_type="correction", operation="create", params={})
        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "payload"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_create_asks_for_scheduling(self, router):
        result = await router.manage_slo(
            resource_type="correction",
            operation="create",
            params={"payload": {"name": "Maintenance"}},
        )
        assert result["missing_parameters"] == ["scheduling"]
        router.slo_correction_client.create_correction.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_create_asks_for_start_time(self, router):
        result = await router.manage_slo(
            resource_type="correction",
            operation="create",
            params={"payload": {"name": "M", "scheduling": {"duration": 2}}},
        )
        assert result["missing_parameters"] == ["startTime"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_create_requires_timezone_on_string_start(self, router):
        result = await router.manage_slo(
            resource_type="correction",
            operation="create",
            params={
                "payload": {
                    "name": "M",
                    "scheduling": {"duration": 2, "startTime": "10 March 2026, 2:00 PM"},
                }
            },
        )
        assert result["missing_parameters"] == ["timezone"]
        router.slo_correction_client.create_correction.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_create_converts_start_time_and_forwards(self, router):
        payload = {
            "name": "Maintenance",
            "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "10 March 2026, 2:00 PM|UTC"},
        }
        result = await router.manage_slo(
            resource_type="correction", operation="create", params={"payload": payload}
        )
        assert result["results"] == {"id": "cor-new"}
        sent = router.slo_correction_client.create_correction.call_args.kwargs["payload"]
        assert isinstance(sent["scheduling"]["startTime"], int)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_create_passes_numeric_start_time(self, router):
        payload = {"name": "M", "scheduling": {"duration": 1, "startTime": 1742369820000}}
        await router.manage_slo(
            resource_type="correction", operation="create", params={"payload": payload}
        )
        sent = router.slo_correction_client.create_correction.call_args.kwargs["payload"]
        assert sent["scheduling"]["startTime"] == 1742369820000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_update_requires_id_and_payload(self, router):
        result = await router.manage_slo(resource_type="correction", operation="update", params={})
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["id", "payload"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_update_forwards_id_and_payload(self, router):
        result = await router.manage_slo(
            resource_type="correction",
            operation="update",
            params={"id": "cor-1", "payload": {"name": "renamed"}},
        )
        assert result["results"] == {"id": "cor-1"}
        kwargs = router.slo_correction_client.update_correction.call_args.kwargs
        assert kwargs["id"] == "cor-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_delete_requires_id(self, router):
        result = await router.manage_slo(resource_type="correction", operation="delete", params={})
        assert result["elicitation_needed"] is True
        router.slo_correction_client.delete_correction.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correction_delete_forwards_id(self, router):
        result = await router.manage_slo(
            resource_type="correction", operation="delete", params={"id": "cor-1"}
        )
        assert result["results"] == {"deleted": True}
        assert router.slo_correction_client.delete_correction.call_args.kwargs["id"] == "cor-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_error(self, router):
        router.slo_report_client.get_slo_report.side_effect = RuntimeError("down")
        result = await router.manage_slo(
            resource_type="report",
            operation="get",
            params={"slo_id": "slo-1", "var_from": 1742369820000},
        )
        assert "down" in result["error"]
        assert result["resource_type"] == "report"
