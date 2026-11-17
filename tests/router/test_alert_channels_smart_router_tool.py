"""
Unit tests for AlertChannelsSmartRouterMCPTool.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock the Instana SDK while importing the modules under test (same approach as the other
# router tests) so these tests never load the real instana_client package, and restore
# sys.modules afterwards so other test modules are unaffected.
_SDK_MODULES = [
    "instana_client",
    "instana_client.api",
    "instana_client.api.event_settings_api",
    "instana_client.configuration",
    "instana_client.api_client",
]
_original_sdk_modules = {name: sys.modules.get(name) for name in _SDK_MODULES}
for _name in _SDK_MODULES:
    sys.modules[_name] = MagicMock()
sys.modules["instana_client.api.event_settings_api"].EventSettingsApi = MagicMock(__name__="EventSettingsApi")

try:
    from src.alert_channel import (
        alert_channels_tools,  # (router imports it lazily)
    )
    from src.router.alert_channels_smart_router_tool import (
        AlertChannelsSmartRouterMCPTool,
    )
finally:
    for _name, _original in _original_sdk_modules.items():
        if _original is not None:
            sys.modules[_name] = _original
        else:
            sys.modules.pop(_name, None)


@pytest.fixture
def router():
    with patch("src.alert_channel.alert_channels_tools.AlertChannelsMCPTools.__init__", return_value=None):
        r = AlertChannelsSmartRouterMCPTool(read_token="test-token", base_url="https://unit-test.instana.io")
        r.alert_channels_client = AsyncMock()
        return r


@pytest.mark.asyncio
async def test_invalid_operation(router):
    result = await router.manage_alert_channels(operation="invalid_op")
    assert result.get("elicitation_needed") is True
    assert result.get("reason") == "invalid_operation"
    assert "invalid_op" in result.get("message", "")


@pytest.mark.asyncio
async def test_get_overview_dispatch(router):
    router.alert_channels_client.get_overview.return_value = {
        "items": [{"id": "c1", "name": "Hook"}],
        "count": 1,
        "total": 1,
    }

    result = await router.manage_alert_channels(
        operation="get_overview",
        params={"kind": "WEB_HOOK", "name_filter": "hook", "page": 1, "page_size": 10},
    )

    assert result["count"] == 1
    assert result["items"][0]["id"] == "c1"
    router.alert_channels_client.get_overview.assert_called_once_with(
        ids=None,
        kind="WEB_HOOK",
        name_filter="hook",
        page=1,
        page_size=10,
        ctx=None,
        resource_type="alert_channels",
        tool_name="manage_alert_channels",
    )


@pytest.mark.asyncio
async def test_get_missing_params(router):
    result = await router.manage_alert_channels(operation="get", params={})
    assert result.get("elicitation_needed") is True
    assert result.get("reason") == "missing_required_params"


@pytest.mark.asyncio
async def test_get_dispatch_by_id(router):
    router.alert_channels_client.get.return_value = {
        "id": "chan-123",
        "name": "My Channel",
        "kind": "SLACK",
    }

    result = await router.manage_alert_channels(
        operation="get",
        params={"id": "chan-123"},
    )

    assert result["id"] == "chan-123"
    assert result["name"] == "My Channel"
    router.alert_channels_client.get.assert_called_once_with(
        channel_id="chan-123",
        name=None,
        ctx=None,
        resource_type="alert_channels",
        tool_name="manage_alert_channels",
    )


@pytest.mark.asyncio
async def test_get_dispatch_by_name(router):
    router.alert_channels_client.get.return_value = {
        "id": "chan-123",
        "name": "Prod Webhook",
        "kind": "WEB_HOOK",
    }

    result = await router.manage_alert_channels(
        operation="get",
        params={"name": "Prod Webhook"},
    )

    assert result["id"] == "chan-123"
    assert result["name"] == "Prod Webhook"
    router.alert_channels_client.get.assert_called_once_with(
        channel_id=None,
        name="Prod Webhook",
        ctx=None,
        resource_type="alert_channels",
        tool_name="manage_alert_channels",
    )


@pytest.mark.asyncio
async def test_parameter_aliases_overview_and_get(router):
    router.alert_channels_client.get_overview.return_value = {"items": [], "count": 0}
    router.alert_channels_client.get.return_value = {"id": "chan-1", "name": "Test"}

    # Test camelCase and alternative aliases for get_overview
    await router.manage_alert_channels(
        operation="get_overview",
        params={
            "channelIds": ["chan-1", "chan-2"],
            "nameFilter": "alert",
            "pageNumber": 2,
            "pageSize": 10,
        },
    )
    router.alert_channels_client.get_overview.assert_called_once_with(
        ids=["chan-1", "chan-2"],
        kind=None,
        name_filter="alert",
        page=2,
        page_size=10,
        ctx=None,
        resource_type="alert_channels",
        tool_name="manage_alert_channels",
    )

    # Test channelId alias for get
    await router.manage_alert_channels(
        operation="get",
        params={"channelId": "chan-99"},
    )
    router.alert_channels_client.get.assert_called_with(
        channel_id="chan-99",
        name=None,
        ctx=None,
        resource_type="alert_channels",
        tool_name="manage_alert_channels",
    )

    # Test channelName / channel_name alias for get
    await router.manage_alert_channels(
        operation="get",
        params={"channelName": "My Webhook"},
    )
    router.alert_channels_client.get.assert_called_with(
        channel_id=None,
        name="My Webhook",
        ctx=None,
        resource_type="alert_channels",
        tool_name="manage_alert_channels",
    )


@pytest.mark.asyncio
async def test_router_exception_handling(router):
    router.alert_channels_client.get_overview.side_effect = RuntimeError("Fatal crash")

    result = await router.manage_alert_channels(operation="get_overview")
    assert "error" in result
    assert "Fatal crash" in result["error"]
