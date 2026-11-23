"""Mocked e2e tests for the custom dashboard smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.custom_dashboard_smart_router_tool import (
    CustomDashboardSmartRouterMCPTool,
)


@pytest.fixture
def router(instana_credentials):
    tool = CustomDashboardSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.dashboard_client = AsyncMock()
    tool.dashboard_client.execute_dashboard_operation.return_value = {"ok": True}
    return tool


class TestCustomDashboardSmartRouterE2E:
    """Dispatch and validation tests for CustomDashboardSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_operation_returns_elicitation(self, router):
        result = await router.manage_custom_dashboards(operation="publish")
        assert result["elicitation_needed"] is True
        assert "publish" in result["reason"]
        router.dashboard_client.execute_dashboard_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_routes_with_dashboard_id(self, router):
        result = await router.manage_custom_dashboards(
            operation="get", params={"dashboard_id": "abc123"}
        )
        assert result == {
            "resource_type": "custom_dashboard",
            "operation": "get",
            "dashboard_id": "abc123",
            "results": {"ok": True},
        }
        kwargs = router.dashboard_client.execute_dashboard_operation.call_args.kwargs
        assert kwargs["operation"] == "get"
        assert kwargs["params"] == {"dashboard_id": "abc123"}
        assert kwargs["resource_type"] == "custom_dashboard"
        assert kwargs["tool_name"] == "manage_custom_dashboards"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dashboard_id_none_when_absent(self, router):
        result = await router.manage_custom_dashboards(operation="get_all")
        assert result["dashboard_id"] is None
        assert result["operation"] == "get_all"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_forwards_custom_dashboard_payload(self, router):
        payload = {"title": "My Dashboard", "widgets": []}
        await router.manage_custom_dashboards(
            operation="create", params={"custom_dashboard": payload}
        )
        kwargs = router.dashboard_client.execute_dashboard_operation.call_args.kwargs
        assert kwargs["operation"] == "create"
        assert kwargs["params"]["custom_dashboard"] == payload

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_navigation_sets_total_hits_and_default_size(self, router):
        await router.manage_custom_dashboards(operation="page_2", params={})
        kwargs = router.dashboard_client.execute_dashboard_operation.call_args.kwargs
        assert kwargs["operation"] == "get_all"
        assert kwargs["params"]["with_total_hits"] is True
        assert kwargs["params"]["page_size"] == 10

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_error(self, router):
        router.dashboard_client.execute_dashboard_operation.side_effect = (
            RuntimeError("api down")
        )
        result = await router.manage_custom_dashboards(operation="delete")
        assert "api down" in result["error"]
        assert result["resource_type"] == "custom_dashboard"
        assert result["operation"] == "delete"
