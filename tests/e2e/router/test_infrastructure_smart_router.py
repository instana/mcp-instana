"""Mocked e2e tests for the infrastructure smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.infrastructure_smart_router_tool import (
    InfrastructureSmartRouterMCPTool,
)


@pytest.fixture
def router(instana_credentials):
    tool = InfrastructureSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.infrastructure_analyze_client = AsyncMock()
    tool.infrastructure_analyze_client.get_entities.return_value = {
        "items": [{"metrics": {"cpu.used": [[1, 0.5]]}}]
    }
    tool.infrastructure_analyze_client.get_aggregated_entity_groups.return_value = {
        "groups": []
    }
    tool.infrastructure_catalog_client = AsyncMock()
    tool.infrastructure_catalog_client.get_infrastructure_catalog_plugins.return_value = [
        {"id": "host"}
    ]
    tool.infrastructure_catalog_client.get_infrastructure_catalog_metrics.return_value = [
        "cpu.used"
    ]
    tool.infrastructure_catalog_client.get_tag_catalog.return_value = ["host.name"]
    tool.infrastructure_catalog_client.get_plugin_schema.return_value = {"metrics": []}
    tool.infrastructure_resources_client = AsyncMock()
    tool.infrastructure_resources_client.get_snapshot.return_value = {"id": "snap-1"}
    tool.infrastructure_resources_client.get_snapshots.return_value = {"items": []}
    tool.infrastructure_alert_config_client = AsyncMock()
    tool.infrastructure_alert_config_client.execute_alert_config_operation.return_value = {
        "configs": []
    }
    return tool


class TestInfrastructureSmartRouterE2E:
    """Dispatch and validation tests for InfrastructureSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_resource_type_returns_elicitation(self, router):
        result = await router.manage_infrastructure(
            resource_type="bogus", operation="get_plugins"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_resource_type"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_invalid_operation(self, router):
        result = await router.manage_infrastructure(
            resource_type="analyze", operation="get_snapshots", params={"payload": {}}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_requires_payload(self, router):
        result = await router.manage_infrastructure(
            resource_type="analyze", operation="get_entities", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        router.infrastructure_analyze_client.get_entities.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_routes_to_get_entities_without_group_by(self, router):
        payload = {"type": "host", "metrics": [{"metric": "cpu.used"}]}
        result = await router.manage_infrastructure(
            resource_type="analyze",
            operation="get_entity_groups",
            params={"payload": payload},
        )
        assert result["operation"] == "get_entities"
        router.infrastructure_analyze_client.get_entities.assert_awaited_once()
        assert (
            router.infrastructure_analyze_client.get_entities.call_args.kwargs["payload"]
            == payload
        )
        router.infrastructure_analyze_client.get_aggregated_entity_groups.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_routes_to_groups_when_group_by_present(self, router):
        payload = {"type": "host", "groupBy": ["host.name"], "metrics": []}
        result = await router.manage_infrastructure(
            resource_type="analyze",
            operation="get_entities",
            params={"payload": payload},
        )
        assert result["operation"] == "get_entity_groups"
        assert result["results"] == {"groups": []}
        router.infrastructure_analyze_client.get_aggregated_entity_groups.assert_awaited_once()
        router.infrastructure_analyze_client.get_entities.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_warns_when_entities_have_no_metric_values(self, router):
        router.infrastructure_analyze_client.get_entities.return_value = {
            "items": [{"metrics": {"cpu.used": []}}]
        }
        payload = {
            "type": "host",
            "metrics": [{"metric": "cpu.used"}],
            "tagFilterExpression": {
                "type": "TAG_FILTER",
                "name": "label",
                "entity": "NOT_APPLICABLE",
                "operator": "EQUALS",
                "value": "web-1",
            },
        }
        result = await router.manage_infrastructure(
            resource_type="analyze", operation="get_entities", params={"payload": payload}
        )
        assert "warning" in result
        assert "1 entity matched but no metric values" in result["warning"]
        assert "label" in result["warning"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_invalid_operation(self, router):
        result = await router.manage_infrastructure(
            resource_type="catalog", operation="delete"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_plugins(self, router):
        result = await router.manage_infrastructure(
            resource_type="catalog", operation="get_plugins"
        )
        assert result == {
            "resource_type": "catalog",
            "operation": "get_plugins",
            "results": [{"id": "host"}],
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_metrics_requires_plugin(self, router):
        result = await router.manage_infrastructure(
            resource_type="catalog", operation="get_metrics", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        router.infrastructure_catalog_client.get_infrastructure_catalog_metrics.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_metrics_forwards_plugin_and_filter(self, router):
        result = await router.manage_infrastructure(
            resource_type="catalog",
            operation="get_metrics",
            params={"plugin": "host", "filter": "builtin"},
        )
        assert result["results"] == ["cpu.used"]
        kwargs = (
            router.infrastructure_catalog_client.get_infrastructure_catalog_metrics.call_args.kwargs
        )
        assert kwargs["plugin"] == "host"
        assert kwargs["filter"] == "builtin"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_tag_catalog_requires_plugin(self, router):
        result = await router.manage_infrastructure(
            resource_type="catalog", operation="get_tag_catalog", params={}
        )
        assert result["elicitation_needed"] is True
        router.infrastructure_catalog_client.get_tag_catalog.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_tag_catalog_forwards_plugin(self, router):
        result = await router.manage_infrastructure(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"plugin": "host"},
        )
        assert result["results"] == ["host.name"]
        assert router.infrastructure_catalog_client.get_tag_catalog.call_args.kwargs["plugin"] == "host"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_plugin_schema_requires_plugin(self, router):
        result = await router.manage_infrastructure(
            resource_type="catalog", operation="get_plugin_schema", params={}
        )
        assert result["elicitation_needed"] is True
        router.infrastructure_catalog_client.get_plugin_schema.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_get_plugin_schema_forwards_plugin(self, router):
        result = await router.manage_infrastructure(
            resource_type="catalog",
            operation="get_plugin_schema",
            params={"plugin": "host", "filter": "custom"},
        )
        assert result["results"] == {"metrics": []}
        kwargs = router.infrastructure_catalog_client.get_plugin_schema.call_args.kwargs
        assert kwargs["filter"] == "custom"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_resources_invalid_operation(self, router):
        result = await router.manage_infrastructure(
            resource_type="resources", operation="get_entities"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_resources_get_snapshot_requires_id(self, router):
        result = await router.manage_infrastructure(
            resource_type="resources", operation="get_snapshot", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        router.infrastructure_resources_client.get_snapshot.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_resources_get_snapshot_forwards_params(self, router):
        result = await router.manage_infrastructure(
            resource_type="resources",
            operation="get_snapshot",
            params={"snapshot_id": "snap-1", "window_size": 600000},
        )
        assert result["results"] == {"id": "snap-1"}
        kwargs = router.infrastructure_resources_client.get_snapshot.call_args.kwargs
        assert kwargs["snapshot_id"] == "snap-1"
        assert kwargs["window_size"] == 600000
        assert kwargs["to_time"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_resources_get_snapshots_applies_defaults(self, router):
        await router.manage_infrastructure(
            resource_type="resources",
            operation="get_snapshots",
            params={"plugin": "host", "query": "web"},
        )
        kwargs = router.infrastructure_resources_client.get_snapshots.call_args.kwargs
        assert kwargs["size"] == 100
        assert kwargs["offline"] is False
        assert kwargs["detailed"] is False
        assert kwargs["plugin"] == "host"
        assert kwargs["query"] == "web"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_config_invalid_operation(self, router):
        result = await router.manage_infrastructure(
            resource_type="alert_config", operation="publish"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_config_forwards_all_params(self, router):
        result = await router.manage_infrastructure(
            resource_type="alert_config",
            operation="find_active",
            params={"page": 2, "page_size": 25, "alert_ids": ["a1"]},
        )
        assert result == {
            "resource_type": "alert_config",
            "operation": "find_active",
            "results": {"configs": []},
        }
        kwargs = (
            router.infrastructure_alert_config_client.execute_alert_config_operation.call_args.kwargs
        )
        assert kwargs["operation"] == "find_active"
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 25
        assert kwargs["alert_ids"] == ["a1"]
        assert kwargs["tool_name"] == "manage_infrastructure"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_error(self, router):
        router.infrastructure_catalog_client.get_plugin_schema.side_effect = RuntimeError(
            "boom"
        )
        result = await router.manage_infrastructure(
            resource_type="catalog",
            operation="get_plugin_schema",
            params={"plugin": "host"},
        )
        assert "boom" in result["error"]
        assert result["resource_type"] == "catalog"
