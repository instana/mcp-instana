"""Mocked e2e tests for the maintenance window smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.maintenance_window_smart_router import (
    MaintenanceWindowSmartRouterMCPTool,
)


@pytest.fixture
def router(instana_credentials):
    tool = MaintenanceWindowSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.maintenance_window_client = AsyncMock()
    tool.maintenance_window_client.execute_maintenance_operation.return_value = {
        "windows": []
    }
    return tool


class TestMaintenanceWindowSmartRouterE2E:
    """Dispatch and validation tests for MaintenanceWindowSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_resource_type_returns_elicitation(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="bogus", operation="list_all"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_resource_type"
        router.maintenance_window_client.execute_maintenance_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_defaults_apply_when_arguments_omitted(self, router):
        result = await router.manage_maintenance_windows(
            resource_type=None, operation=None
        )
        assert result["resource_type"] == "window"
        assert result["operation"] == "list_scheduled"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "alias", ["maintenance", "maintenance_window", "windows"]
    )
    async def test_window_aliases_normalise_to_window(self, router, alias):
        result = await router.manage_maintenance_windows(
            resource_type=alias, operation="list_all"
        )
        assert result["resource_type"] == "window"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_window_operation(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="window", operation="delete"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_requires_identifier_and_start_time(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="window", operation="create", params={}
        )
        assert result["elicitation_needed"] is True
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["imap_code / application_id", "start_time"]
        router.maintenance_window_client.execute_maintenance_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_rejects_unknown_template(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="window",
            operation="create",
            params={
                "imap_code": "EAL-012471",
                "start_time": "1748786400000",
                "template": "bogus",
            },
        )
        assert result["elicitation_needed"] is True
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["template"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_forwards_parsed_params(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="window",
            operation="create",
            params={
                "imap_code": "EAL-012471",
                "start_time": "1748786400000",
                "duration_minutes": "120",
                "template": "deployment",
                "affected_services": '["svc-a", "svc-b"]',
                "notification_channels": "email, slack",
                "use_tag_filter_expression": "TRUE",
            },
        )
        assert result["resource_type"] == "window"
        assert result["operation"] == "create"
        kwargs = router.maintenance_window_client.execute_maintenance_operation.call_args.kwargs
        assert kwargs["operation"] == "create"
        assert kwargs["resource_type"] == "window"
        sent = kwargs["params"]
        assert sent["imap_code"] == "EAL-012471"
        assert sent["duration_minutes"] == "120"
        assert sent["affected_services"] == ["svc-a", "svc-b"]
        assert sent["notification_channels"] == ["email", "slack"]
        assert sent["use_tag_filter_expression"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_bulk_create_requires_ids_and_start_time(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="window", operation="bulk_create", params={}
        )
        assert result["elicitation_needed"] is True
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["imap_codes / application_ids", "start_time"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_bulk_create_accepts_comma_separated_codes(self, router):
        await router.manage_maintenance_windows(
            resource_type="window",
            operation="bulk_create",
            params={
                "imap_codes": "EAL-012471,ORZ-000012",
                "start_time": "1748786400000",
            },
        )
        sent = router.maintenance_window_client.execute_maintenance_operation.call_args.kwargs["params"]
        assert sent["imap_codes"] == ["EAL-012471", "ORZ-000012"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation", ["modify", "close"])
    async def test_modify_and_close_require_window_id(self, router, operation):
        result = await router.manage_maintenance_windows(
            resource_type="window", operation=operation, params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        assert result["api_error"][0]["field"] == "window_id"
        router.maintenance_window_client.execute_maintenance_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_close_forwards_window_id_and_notes(self, router):
        await router.manage_maintenance_windows(
            resource_type="window",
            operation="close",
            params={"window_id": "mw-789", "completion_notes": "done"},
        )
        sent = router.maintenance_window_client.execute_maintenance_operation.call_args.kwargs["params"]
        assert sent["window_id"] == "mw-789"
        assert sent["completion_notes"] == "done"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "operation", ["list_active", "list_scheduled", "list_all", "list_expired"]
    )
    async def test_list_operations_dispatch_without_validation(self, router, operation):
        result = await router.manage_maintenance_windows(
            resource_type="window", operation=operation, params={"imap_code": "EAL-1"}
        )
        assert result["operation"] == operation
        kwargs = router.maintenance_window_client.execute_maintenance_operation.call_args.kwargs
        assert kwargs["operation"] == operation
        assert kwargs["params"]["imap_code"] == "EAL-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_validate_operation_checks_create_rules(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="window", operation="validate", params={"imap_code": "EAL-1"}
        )
        assert result["operation"] == "validate"
        kwargs = router.maintenance_window_client.execute_maintenance_operation.call_args.kwargs
        assert kwargs["operation"] == "validate"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_templates_get_routes_to_get_templates(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="templates", operation="get"
        )
        assert result == {
            "resource_type": "templates",
            "operation": "get",
            "results": {"windows": []},
        }
        kwargs = router.maintenance_window_client.execute_maintenance_operation.call_args.kwargs
        assert kwargs["operation"] == "get_templates"
        assert kwargs["resource_type"] == "templates"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_templates_alias_template_is_accepted(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="template", operation="get"
        )
        assert result["resource_type"] == "templates"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_templates_invalid_operation(self, router):
        result = await router.manage_maintenance_windows(
            resource_type="templates", operation="create"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"
        router.maintenance_window_client.execute_maintenance_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_returns_structured_error(self, router):
        router.maintenance_window_client.execute_maintenance_operation.side_effect = (
            RuntimeError("api down")
        )
        result = await router.manage_maintenance_windows(
            resource_type="window",
            operation="list_all",
            params={"imap_code": "EAL-1", "start_time": "1"},
        )
        assert result["error"] == "Maintenance window router error: api down"
        assert result["error_type"] == "RuntimeError"
        assert result["parameters"]["imap_code"] == "EAL-1"
