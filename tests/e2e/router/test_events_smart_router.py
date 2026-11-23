"""Mocked e2e tests for the events smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.events_smart_router_tool import EventsSmartRouterMCPTool


@pytest.fixture
def router(instana_credentials):
    tool = EventsSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.events_client = AsyncMock()
    tool.events_client.get_event.return_value = {"id": "evt-1"}
    tool.events_client.get_kubernetes_info_events.return_value = {"events": []}
    tool.events_client.get_agent_monitoring_events.return_value = {"events": []}
    tool.events_client.get_events.return_value = {"events": []}
    tool.events_client.get_events_by_ids.return_value = {"events": []}
    return tool


class TestEventsSmartRouterE2E:
    """Dispatch and validation tests for EventsSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_operation_returns_elicitation(self, router):
        result = await router.manage_events(operation="delete_event")
        assert result["elicitation_needed"] is True
        assert "delete_event" in result["reason"]
        router.events_client.get_events.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_event_requires_event_id(self, router):
        result = await router.manage_events(operation="get_event", params={"event_id": "  "})
        assert result["elicitation_needed"] is True
        assert result["reason"] == "get_event: event_id is required"
        router.events_client.get_event.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_event_forwards_id(self, router):
        result = await router.manage_events(
            operation="get_event", params={"event_id": "evt-1"}
        )
        assert result == {"operation": "get_event", "results": {"id": "evt-1"}}
        kwargs = router.events_client.get_event.call_args.kwargs
        assert kwargs["event_id"] == "evt-1"
        assert kwargs["resource_type"] == "events"
        assert kwargs["tool_name"] == "manage_events"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_events_by_ids_requires_ids(self, router):
        result = await router.manage_events(operation="get_events_by_ids", params={})
        assert result["elicitation_needed"] is True
        assert result["reason"] == "get_events_by_ids: event_ids is required"
        router.events_client.get_events_by_ids.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_events_by_ids_forwards_ids(self, router):
        await router.manage_events(
            operation="get_events_by_ids", params={"event_ids": ["a", "b"]}
        )
        kwargs = router.events_client.get_events_by_ids.call_args.kwargs
        assert kwargs["event_ids"] == ["a", "b"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_kubernetes_info_events_forwards_time_and_limits(self, router):
        await router.manage_events(
            operation="get_kubernetes_info_events",
            params={
                "from_time": 1742369820000,
                "to_time": 1742373420000,
                "max_events": 25,
            },
        )
        kwargs = router.events_client.get_kubernetes_info_events.call_args.kwargs
        assert kwargs["from_time"] == 1742369820000
        assert kwargs["to_time"] == 1742373420000
        assert kwargs["max_events"] == 25

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_time_required_operation_rejects_bad_max_events(self, router):
        result = await router.manage_events(
            operation="get_kubernetes_info_events",
            params={"max_events": 5000},
        )
        assert result["validation_failed"] is True
        assert result["valid"] is False
        assert result["error_count"] == 1
        router.events_client.get_kubernetes_info_events.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_agent_monitoring_events_forwards_query(self, router):
        await router.manage_events(
            operation="get_agent_monitoring_events",
            params={"query": "agent down", "time_range": "last 2 hours"},
        )
        kwargs = router.events_client.get_agent_monitoring_events.call_args.kwargs
        assert kwargs["query"] == "agent down"
        assert kwargs["time_range"] == "last 2 hours"
        assert kwargs["max_events"] == 50

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_datetime_returns_elicitation(self, router):
        result = await router.manage_events(
            operation="get_agent_monitoring_events",
            params={"from_time": "not a real date", "to_time": 1742373420000},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "datetime conversion failed for from_time or to_time"
        router.events_client.get_agent_monitoring_events.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_events_validates_nested_filters_and_coerces_booleans(self, router):
        await router.manage_events(
            operation="get_events",
            params={
                "filters": {
                    "severity": 10,
                    "event_type_filters": ["INCIDENT"],
                    "filter_event_updates": "false",
                    "exclude_triggered_before": "true",
                    "entity_type": "SERVICE",
                    "state": "open",
                }
            },
        )
        kwargs = router.events_client.get_events.call_args.kwargs
        forwarded = kwargs["filters"]
        assert forwarded["severity"] == 10
        assert forwarded["event_type_filters"] == ["INCIDENT"]
        assert forwarded["filter_event_updates"] is False
        assert forwarded["exclude_triggered_before"] is True
        assert forwarded["entity_type"] == "SERVICE"
        assert forwarded["state"] == "open"
        assert forwarded["max_events"] == 50

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_events_reports_all_filter_problems(self, router):
        result = await router.manage_events(
            operation="get_events",
            params={
                "filters": {
                    "severity": 7,
                    "event_type_filters": "INCIDENT",
                    "max_events": 0,
                    "filter_event_updates": "maybe",
                }
            },
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "get_events filters have 4 validation problem(s)"
        assert len(result["api_error"]) == 4
        router.events_client.get_events.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_events_rejects_invalid_event_type_entries(self, router):
        result = await router.manage_events(
            operation="get_events",
            params={"filters": {"event_type_filters": ["BOGUS", 3]}},
        )
        assert result["elicitation_needed"] is True
        assert len(result["api_error"]) == 2
        assert "event_type_filters[0]" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_events_rejects_non_integer_max_events(self, router):
        result = await router.manage_events(
            operation="get_events",
            params={"filters": {"max_events": "ten"}},
        )
        assert result["elicitation_needed"] is True
        assert "must be an integer" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_error(self, router):
        router.events_client.get_event.side_effect = RuntimeError("down")
        result = await router.manage_events(
            operation="get_event", params={"event_id": "evt-1"}
        )
        assert "down" in result["error"]
        assert result["operation"] == "get_event"
