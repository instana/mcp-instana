"""Mocked e2e tests for the alert channels smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.alert_channels_smart_router_tool import (
    AlertChannelsSmartRouterMCPTool,
)


@pytest.fixture
def router(instana_credentials):
    tool = AlertChannelsSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.alert_channels_client = AsyncMock()
    tool.alert_channels_client.get_overview.return_value = {"items": []}
    tool.alert_channels_client.get.return_value = {"id": "chan-1"}
    return tool


class TestAlertChannelsSmartRouterE2E:
    """Dispatch and validation tests for AlertChannelsSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_operation_returns_elicitation(self, router):
        result = await router.manage_alert_channels(operation="delete")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"
        router.alert_channels_client.get_overview.assert_not_called()
        router.alert_channels_client.get.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_defaults_pagination(self, router):
        result = await router.manage_alert_channels(operation="get_overview")
        assert result == {"items": []}
        kwargs = router.alert_channels_client.get_overview.call_args.kwargs
        assert kwargs["page"] == 1
        assert kwargs["page_size"] == 20
        assert kwargs["ids"] is None
        assert kwargs["kind"] is None
        assert kwargs["name_filter"] is None
        assert kwargs["resource_type"] == "alert_channels"
        assert kwargs["tool_name"] == "manage_alert_channels"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_maps_alias_params(self, router):
        await router.manage_alert_channels(
            operation="get_overview",
            params={
                "channelIds": ["a", "b"],
                "kind": "WEB_HOOK",
                "nameFilter": "Slack",
                "pageNumber": 2,
                "pageSize": 5,
            },
        )
        kwargs = router.alert_channels_client.get_overview.call_args.kwargs
        assert kwargs["ids"] == ["a", "b"]
        assert kwargs["kind"] == "WEB_HOOK"
        assert kwargs["name_filter"] == "Slack"
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 5

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_query_alias_for_name_filter(self, router):
        await router.manage_alert_channels(
            operation="get_overview", params={"query": "pager"}
        )
        kwargs = router.alert_channels_client.get_overview.call_args.kwargs
        assert kwargs["name_filter"] == "pager"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_requires_id_or_name(self, router):
        result = await router.manage_alert_channels(operation="get", params={})
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        router.alert_channels_client.get.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_id_alias_forwarded(self, router):
        result = await router.manage_alert_channels(
            operation="get", params={"channelId": "chan-1"}
        )
        assert result == {"id": "chan-1"}
        kwargs = router.alert_channels_client.get.call_args.kwargs
        assert kwargs["channel_id"] == "chan-1"
        assert kwargs["name"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_name_forwarded(self, router):
        await router.manage_alert_channels(
            operation="get", params={"channel_name": "SRE Team Webhook"}
        )
        kwargs = router.alert_channels_client.get.call_args.kwargs
        assert kwargs["name"] == "SRE Team Webhook"
        assert kwargs["channel_id"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_error(self, router):
        router.alert_channels_client.get_overview.side_effect = RuntimeError("down")
        result = await router.manage_alert_channels(operation="get_overview")
        assert "down" in result["error"]
        assert result["operation"] == "get_overview"
