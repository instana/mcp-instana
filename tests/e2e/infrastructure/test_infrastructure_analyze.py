"""
E2E tests (mocked) for Infrastructure Analyze MCP Tools
"""

import importlib
import json
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _require_real_sdk():
    """Skip when another test module replaced the SDK with MagicMocks (mixed test runs)."""
    mocked = [
        name for name, mod in sys.modules.items()
        if name.startswith("instana_client") and isinstance(mod, MagicMock)
    ]
    if mocked:
        pytest.skip(f"instana_client is mocked in this session: {mocked[0]}")


def create_infrastructure_analyze_client(instana_credentials):
    """Dynamically import and create Infrastructure Analyze client"""
    module = importlib.import_module("src.infrastructure.infrastructure_analyze")
    module = importlib.reload(module)
    return module.InfrastructureAnalyzeMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


def _json_response(body, status=200):
    return _MockResponse(json.dumps(body).encode("utf-8"), status=status)


def _tag_filter(**overrides):
    base = {
        "type": "TAG_FILTER",
        "entity": "NOT_APPLICABLE",
        "name": "label",
        "operator": "EQUALS",
        "stringValue": "custom-metrics.jar",
    }
    base.update(overrides)
    return base


def _entities_payload(**overrides):
    payload = {
        "type": "jvmRuntimePlatform",
        "tagFilterExpression": _tag_filter(),
        "timeFrame": {"to": 1743923995000, "windowSize": 3600000},
        "pagination": {"retrievalSize": 20},
        "metrics": [{"metric": "memory.used", "granularity": 600000, "aggregation": "MAX"}],
    }
    payload.update(overrides)
    return payload


def _discovery_payload(**overrides):
    """Payload accepted by GetAvailableMetricsQuery / GetAvailablePluginsQuery."""
    payload = {
        "timeFrame": {"to": 1743923995000, "windowSize": 3600000},
        "tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
    }
    payload.update(overrides)
    return payload


def _groups_payload(**overrides):
    payload = _entities_payload(groupBy=["host.name"], order={"by": "label", "direction": "ASC"})
    payload.update(overrides)
    return payload


class TestInfrastructureAnalyzeE2E:
    """End-to-end (mocked) tests for Infrastructure Analyze MCP Tools"""

    def setup_method(self):
        from src.core.catalog_cache import clear_cache
        clear_cache()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @pytest.mark.mocked
    def test_normalize_tag_filter_expression_passthrough(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        expr = _tag_filter()
        assert client._normalize_tag_filter_expression(expr) is expr

    @pytest.mark.mocked
    def test_summarize_entity_groups_result_collects_sorted_unique_hosts(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        result = {
            "items": [
                {"tags": {"host.name": "b-host"}},
                {"tags": {"host.name": "a-host"}},
                {"tags": {"host.name": "a-host"}},
                {"tags": {"host.name": {"name": "c-host"}}},
                {"tags": {"host.name": 42}},
                {"tags": "not-a-dict"},
                {"no_tags": True},
            ]
        }
        summary = client._summarize_entity_groups_result(result, {"groupBy": ["host.name"]})

        assert summary["hosts"] == ["42", "a-host", "b-host", "c-host"]
        assert summary["count"] == 4
        assert summary["summary"].startswith("Found 4 hosts")

    @pytest.mark.mocked
    def test_summarize_entity_groups_result_passthrough_error(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        err = {"error": "boom"}
        assert client._summarize_entity_groups_result(err, {}) is err

    @pytest.mark.mocked
    def test_summarize_entity_groups_result_without_group_by(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        summary = client._summarize_entity_groups_result({"items": [{"tags": {"x": "y"}}]}, {})
        assert summary == {"hosts": [], "count": 0, "summary": "Found 0 hosts: "}

    @pytest.mark.mocked
    def test_summarize_entity_groups_result_handles_internal_exception(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        # query_body of None -> TypeError on `in` check, handled by except branch
        result = client._summarize_entity_groups_result({"items": []}, None)
        assert "Failed to summarize results" in result["error"]

    # ------------------------------------------------------------------
    # get_available_metrics
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_success_with_to_dict(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"metrics": [{"label": "memory.used"}]}
        mock_api.get_available_metrics.return_value = mock_result

        result = await client.get_available_metrics(
            payload=_discovery_payload(
                timeFrame={"from": 1743920395000, "to": 1743923995000, "windowSize": 3600000},
                query="mem",
                type="jvmRuntimePlatform",
            ),
            api_client=mock_api,
        )

        assert result == {"metrics": [{"label": "memory.used"}]}
        mock_api.get_available_metrics.assert_called_once()
        assert "get_available_metrics_query" in mock_api.get_available_metrics.call_args.kwargs

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_dict_result_without_to_dict(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_available_metrics.return_value = {"metrics": []}

        result = await client.get_available_metrics(
            payload=json.dumps(_discovery_payload(type="host", query="")), api_client=mock_api
        )

        assert result == {"metrics": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_async_sdk_function(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_available_metrics = AsyncMock(return_value={"metrics": ["a"]})

        result = await client.get_available_metrics(payload=_discovery_payload(type="host"), api_client=mock_api)

        assert result == {"metrics": ["a"]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_with_ctx_keepalive(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_available_metrics.return_value = {"metrics": []}
        ctx = MagicMock()
        ctx.log = AsyncMock()

        result = await client.get_available_metrics(
            payload=_discovery_payload(type="host"), ctx=ctx, api_client=mock_api
        )

        assert result == {"metrics": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_missing_payload(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)

        result = await client.get_available_metrics(payload=None, api_client=MagicMock())

        assert result == {"error": "payload is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_invalid_payload_string(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)

        result = await client.get_available_metrics(payload="{not valid", api_client=MagicMock())

        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_invalid_query_object(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()

        result = await client.get_available_metrics(
            payload={"timeFrame": {"windowSize": "not-an-int"}}, api_client=mock_api
        )

        assert "Failed to create query object" in result["error"]
        mock_api.get_available_metrics.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_sdk_exception(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_available_metrics.side_effect = RuntimeError("sdk down")

        result = await client.get_available_metrics(
            payload=_discovery_payload(type="host"), api_client=mock_api
        )

        assert "Failed to get available metrics" in result["error"]
        assert "sdk down" in result["error"]

    # ------------------------------------------------------------------
    # get_available_plugins
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_success(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"plugins": [{"plugin": "host"}]}
        mock_api.get_available_plugins.return_value = mock_result

        result = await client.get_available_plugins(
            payload=_discovery_payload(query="java", offline=False),
            api_client=mock_api,
        )

        assert result == {"plugins": [{"plugin": "host"}]}
        assert "get_available_plugins_query" in mock_api.get_available_plugins.call_args.kwargs

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_dict_result(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_available_plugins.return_value = {"plugins": []}

        result = await client.get_available_plugins(payload=_discovery_payload(query="x"), api_client=mock_api)

        assert result == {"plugins": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_missing_payload(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)

        result = await client.get_available_plugins(payload=None, api_client=MagicMock())

        assert result == {"error": "payload is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_invalid_query_object(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()

        result = await client.get_available_plugins(
            payload={"timeFrame": {"windowSize": "bad"}}, api_client=mock_api
        )

        assert "Failed to create query object" in result["error"]
        mock_api.get_available_plugins.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_sdk_exception(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_available_plugins.side_effect = RuntimeError("nope")

        result = await client.get_available_plugins(payload=_discovery_payload(query="x"), api_client=mock_api)

        assert "Failed to get available plugins" in result["error"]

    # ------------------------------------------------------------------
    # get_entities
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_success(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        body = {"items": [{"label": "custom-metrics.jar", "metrics": {"memory.used": [[1, 2]]}}]}
        mock_api.get_entities_without_preload_content.return_value = _json_response(body)

        result = await client.get_entities(payload=_entities_payload(), api_client=mock_api)

        assert result == body
        kwargs = mock_api.get_entities_without_preload_content.call_args.kwargs
        assert "get_infrastructure_query" in kwargs

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_success_with_json_string_payload_and_ctx(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_entities_without_preload_content.return_value = _json_response({"items": []})
        ctx = MagicMock()
        ctx.log = AsyncMock()

        result = await client.get_entities(
            payload=json.dumps(_entities_payload()),
            ctx=ctx,
            api_client=mock_api,
            resource_type="infrastructure",
            tool_name="analyze",
        )

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_without_tag_filter(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_entities_without_preload_content.return_value = _json_response({"items": []})
        payload = _entities_payload()
        del payload["tagFilterExpression"]

        result = await client.get_entities(payload=payload, api_client=mock_api)

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_missing_payload(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)

        result = await client.get_entities(payload=None, api_client=MagicMock())

        assert result == {"error": "payload is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_validation_collects_all_errors(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        payload = _entities_payload(
            timeFrame={"windowSize": -5},
            pagination={"retrievalSize": 9999},
            metrics=[{"metric": "", "aggregation": "BAD"}],
            tagFilterExpression={"type": "WRONG"},
        )

        result = await client.get_entities(payload=payload, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert len(result["api_error"]) >= 4
        assert "get_entities payload has" in result["reason"]
        mock_api.get_entities_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_validation_granularity_ratio(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        payload = _entities_payload(
            timeFrame={"windowSize": 2_592_000_000},
            metrics=[{"metric": "memory.used", "granularity": 1000, "aggregation": "MAX"}],
        )

        result = await client.get_entities(payload=payload, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert any("data points" in e for e in result["api_error"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_model_creation_error(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()

        # type must be a string -> model validation fails after pre-flight passes
        result = await client.get_entities(
            payload=_entities_payload(type=["not", "a", "string"]), api_client=mock_api
        )

        assert "Failed to create GetInfrastructureQuery" in result["error"]
        mock_api.get_entities_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_http_error_status(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_entities_without_preload_content.return_value = _MockResponse(
            b"forbidden", status=403
        )

        result = await client.get_entities(payload=_entities_payload(), api_client=mock_api)

        assert result["status_code"] == 403
        assert "HTTP 403" in result["error"]
        assert result["details"] == "forbidden"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_invalid_json_body(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_entities_without_preload_content.return_value = _MockResponse(b"<html>")

        result = await client.get_entities(payload=_entities_payload(), api_client=mock_api)

        assert result["error"].startswith("API call failed")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_sdk_exception(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_entities_without_preload_content.side_effect = ConnectionError("down")

        result = await client.get_entities(payload=_entities_payload(), api_client=mock_api)

        assert result == {"error": "API call failed: down"}

    # ------------------------------------------------------------------
    # get_aggregated_entity_groups
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_success(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        body = {"items": [{"tags": {"host.name": "h1"}, "metrics": {}}]}
        mock_api.get_entity_groups_without_preload_content.return_value = _json_response(body)

        result = await client.get_aggregated_entity_groups(
            payload=_groups_payload(), api_client=mock_api
        )

        assert result == body
        kwargs = mock_api.get_entity_groups_without_preload_content.call_args.kwargs
        assert "get_infrastructure_groups_query" in kwargs

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_with_ctx_and_string_payload(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_entity_groups_without_preload_content.return_value = _json_response({"items": []})
        ctx = MagicMock()
        ctx.log = AsyncMock()

        result = await client.get_aggregated_entity_groups(
            payload=json.dumps(_groups_payload()),
            ctx=ctx,
            api_client=mock_api,
            resource_type="infrastructure",
            tool_name="analyze",
        )

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_missing_payload(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)

        result = await client.get_aggregated_entity_groups(payload="", api_client=MagicMock())

        assert result == {"error": "payload is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_validation_errors(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        payload = _groups_payload(
            order={"by": "", "direction": "sideways"},
            pagination={"retrievalSize": 0},
            timeFrame={"windowSize": "x"},
        )

        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "get_aggregated_entity_groups payload has" in result["reason"]
        assert len(result["api_error"]) >= 3
        mock_api.get_entity_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_granularity_ratio(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        payload = _groups_payload(
            timeFrame={"windowSize": 2_592_000_000},
            metrics=[{"metric": "memory.used", "granularity": 1000, "aggregation": "MEAN"}],
        )

        result = await client.get_aggregated_entity_groups(
            payload=payload, api_client=MagicMock()
        )

        assert result["elicitation_needed"] is True
        assert any("data points" in e for e in result["api_error"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_model_creation_error(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()

        result = await client.get_aggregated_entity_groups(
            payload=_groups_payload(groupBy="not-a-list"), api_client=mock_api
        )

        assert "Failed to create GetInfrastructureGroupsQuery" in result["error"]
        mock_api.get_entity_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_http_error_status(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_entity_groups_without_preload_content.return_value = _MockResponse(
            b"server error", status=500
        )

        result = await client.get_aggregated_entity_groups(
            payload=_groups_payload(), api_client=mock_api
        )

        assert result["status_code"] == 500
        assert "HTTP 500" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_invalid_json_body(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_entity_groups_without_preload_content.return_value = _MockResponse(b"oops")

        result = await client.get_aggregated_entity_groups(
            payload=_groups_payload(), api_client=mock_api
        )

        assert result["error"].startswith("API call failed")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_sdk_exception(self, instana_credentials):
        client = create_infrastructure_analyze_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.get_entity_groups_without_preload_content.side_effect = TimeoutError("slow")

        result = await client.get_aggregated_entity_groups(
            payload=_groups_payload(), api_client=mock_api
        )

        assert result == {"error": "API call failed: slow"}
