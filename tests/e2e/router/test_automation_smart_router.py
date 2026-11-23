"""Mocked e2e tests for the automation smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.automation_smart_router_tool import AutomationSmartRouterMCPTool


@pytest.fixture
def router(instana_credentials):
    tool = AutomationSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.action_catalog_client = AsyncMock()
    tool.action_catalog_client.get_actions.return_value = {"actions": []}
    tool.action_catalog_client.get_action_details.return_value = {"id": "a-1"}
    tool.action_catalog_client.get_action_matches.return_value = {"matches": []}
    tool.action_catalog_client.get_action_matches_by_id_and_time_window.return_value = {
        "matches": []
    }
    tool.action_catalog_client.get_action_types.return_value = {"types": []}
    tool.action_catalog_client.get_action_tags.return_value = {"tags": []}
    tool.action_history_client = AsyncMock()
    tool.action_history_client.list_action_instances.return_value = {"items": []}
    tool.action_history_client.get_action_instance_details.return_value = {"id": "i-1"}
    return tool


class TestAutomationSmartRouterE2E:
    """Dispatch and validation tests for AutomationSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_resource_type_returns_elicitation(self, router):
        result = await router.manage_automation(resource_type="bogus", operation="list")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_resource_type"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_catalog_operation_returns_elicitation(self, router):
        result = await router.manage_automation(
            resource_type="catalog", operation="delete_action"
        )
        assert result["elicitation_needed"] is True
        assert "delete_action" in result["reason"]
        router.action_catalog_client.get_actions.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_actions(self, router):
        result = await router.manage_automation(
            resource_type="catalog", operation="get_actions"
        )
        assert result == {
            "resource_type": "catalog",
            "operation": "get_actions",
            "results": {"actions": []},
        }
        kwargs = router.action_catalog_client.get_actions.call_args.kwargs
        assert kwargs["resource_type"] == "catalog"
        assert kwargs["tool_name"] == "manage_automation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_action_details_requires_action_id(self, router):
        result = await router.manage_automation(
            resource_type="catalog", operation="get_action_details", params={}
        )
        assert result["elicitation_needed"] is True
        assert "action_id" in result["reason"]
        router.action_catalog_client.get_action_details.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_action_details_forwards_id(self, router):
        result = await router.manage_automation(
            resource_type="catalog",
            operation="get_action_details",
            params={"action_id": "a-1"},
        )
        assert result["action_id"] == "a-1"
        assert result["results"] == {"id": "a-1"}
        kwargs = router.action_catalog_client.get_action_details.call_args.kwargs
        assert kwargs["action_id"] == "a-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_action_matches_requires_payload(self, router):
        result = await router.manage_automation(
            resource_type="catalog", operation="get_action_matches", params={}
        )
        assert result["elicitation_needed"] is True
        assert "payload" in result["reason"]
        router.action_catalog_client.get_action_matches.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_action_matches_forwards_payload(self, router):
        payload = {"name": "CPU high", "description": "monitoring"}
        result = await router.manage_automation(
            resource_type="catalog",
            operation="get_action_matches",
            params={"payload": payload, "target_snapshot_id": "snap-1"},
        )
        assert result["target_snapshot_id"] == "snap-1"
        kwargs = router.action_catalog_client.get_action_matches.call_args.kwargs
        assert kwargs["payload"] == payload
        assert kwargs["target_snapshot_id"] == "snap-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_matches_by_id_requires_application_or_snapshot(self, router):
        result = await router.manage_automation(
            resource_type="catalog",
            operation="get_action_matches_by_id_and_time_window",
            params={"to": 1742373420000},
        )
        assert result["elicitation_needed"] is True
        assert "application_id" in result["reason"]
        router.action_catalog_client.get_action_matches_by_id_and_time_window.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_matches_by_id_invalid_time_returns_elicitation(self, router):
        result = await router.manage_automation(
            resource_type="catalog",
            operation="get_action_matches_by_id_and_time_window",
            params={"application_id": "app-1", "to": "not a real date"},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_time_params"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_matches_by_id_forwards_params(self, router):
        result = await router.manage_automation(
            resource_type="catalog",
            operation="get_action_matches_by_id_and_time_window",
            params={"application_id": "app-1", "to": 1742373420000, "window_size": 3600000},
        )
        assert result["filters"] == {
            "application_id": "app-1",
            "snapshot_id": None,
            "to": 1742373420000,
            "window_size": 3600000,
        }
        kwargs = (
            router.action_catalog_client.get_action_matches_by_id_and_time_window.call_args.kwargs
        )
        assert kwargs["application_id"] == "app-1"
        assert kwargs["to"] == 1742373420000
        assert kwargs["window_size"] == 3600000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_action_types_and_tags(self, router):
        types_result = await router.manage_automation(
            resource_type="catalog", operation="get_action_types"
        )
        tags_result = await router.manage_automation(
            resource_type="catalog", operation="get_action_tags"
        )
        assert types_result["results"] == {"types": []}
        assert tags_result["results"] == {"tags": []}
        router.action_catalog_client.get_action_types.assert_awaited_once()
        router.action_catalog_client.get_action_tags.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_history_operation_returns_elicitation(self, router):
        result = await router.manage_automation(
            resource_type="history", operation="delete"
        )
        assert result["elicitation_needed"] is True
        assert "delete" in result["reason"]
        router.action_history_client.list_action_instances.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_history_list_converts_to_and_forwards_filters(self, router):
        result = await router.manage_automation(
            resource_type="history",
            operation="list",
            params={
                "to": 1742373420000,
                "window_size": 3600000,
                "page": 1,
                "page_size": 50,
                "action_statuses": ["SUCCESS", "FAILED"],
            },
        )
        assert result["filters"] == {
            "window_size": 3600000,
            "page": 1,
            "page_size": 50,
        }
        kwargs = router.action_history_client.list_action_instances.call_args.kwargs
        assert kwargs["filters"]["to"] == 1742373420000
        assert kwargs["filters"]["action_statuses"] == ["SUCCESS", "FAILED"]
        assert kwargs["filters"]["event_id"] is None
        assert kwargs["resource_type"] == "history"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_history_list_invalid_time_returns_elicitation(self, router):
        result = await router.manage_automation(
            resource_type="history",
            operation="list",
            params={"to": "not a real date"},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_time_params"
        router.action_history_client.list_action_instances.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_history_get_details_requires_instance_id(self, router):
        result = await router.manage_automation(
            resource_type="history", operation="get_details", params={}
        )
        assert result["elicitation_needed"] is True
        assert "action_instance_id" in result["reason"]
        router.action_history_client.get_action_instance_details.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_history_get_details_forwards_params(self, router):
        result = await router.manage_automation(
            resource_type="history",
            operation="get_details",
            params={"action_instance_id": "i-1", "window_size": 600000, "to": 1742373420000},
        )
        assert result["action_instance_id"] == "i-1"
        assert result["results"] == {"id": "i-1"}
        kwargs = router.action_history_client.get_action_instance_details.call_args.kwargs
        assert kwargs["action_instance_id"] == "i-1"
        assert kwargs["window_size"] == 600000
        assert kwargs["to"] == 1742373420000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_catalog_error(self, router):
        router.action_catalog_client.get_actions.side_effect = RuntimeError("down")
        result = await router.manage_automation(
            resource_type="catalog", operation="get_actions"
        )
        assert "down" in result["error"]
        assert result["resource_type"] == "catalog"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_history_error(self, router):
        router.action_history_client.list_action_instances.side_effect = RuntimeError("down")
        result = await router.manage_automation(resource_type="history", operation="list")
        assert "down" in result["error"]
        assert result["resource_type"] == "history"
