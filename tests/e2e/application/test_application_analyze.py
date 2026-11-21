"""
E2E tests for Application Analyze MCP Tools
"""

import importlib
import inspect
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def real_analyze_sdk_models():
    """Skip when another test module has replaced the SDK models with mocks (mixed test runs)."""
    for module_path, attr in (
        ("instana_client.models.get_traces", "GetTraces"),
        ("instana_client.models.get_trace_groups", "GetTraceGroups"),
    ):
        module = importlib.import_module(module_path)
        if not isinstance(getattr(module, attr, None), type):
            pytest.skip(f"{module_path}.{attr} is mocked in this session")


def create_application_analyze_client(instana_credentials):
    """Dynamically import and create Application Analyze client"""
    module = importlib.import_module("src.application.application_analyze")
    module = importlib.reload(module)
    application_analyze_mcp_tools = module.ApplicationAnalyzeMCPTools
    return application_analyze_mcp_tools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"]
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


def _json_response(body):
    return _MockResponse(json.dumps(body).encode("utf-8"))


def _valid_trace_filter():
    return {
        "type": "TAG_FILTER",
        "name": "service.name",
        "operator": "EQUALS",
        "entity": "DESTINATION",
        "value": "groundskeeper",
    }


def _valid_group_payload(**overrides):
    payload = {
        "group": {"groupbyTag": "trace.service.name", "groupbyTagEntity": "DESTINATION"},
        "metrics": [{"metric": "traces", "aggregation": "SUM"}],
    }
    payload.update(overrides)
    return payload


class TestApplicationAnalyzeInitE2E:
    """Initialization and module error handling tests"""

    @pytest.mark.mocked
    def test_initialization_success(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]
        assert hasattr(client, "analyze_api")
        assert client.analyze_api is not None

    @pytest.mark.mocked
    def test_initialization_error(self, instana_credentials):
        from src.application.application_analyze import ApplicationAnalyzeMCPTools

        with patch(
            "src.application.application_analyze.ApplicationAnalyzeApi",
            side_effect=Exception("SDK Init Error"),
        ):
            with pytest.raises(Exception) as excinfo:
                ApplicationAnalyzeMCPTools(
                    read_token=instana_credentials["api_token"],
                    base_url=instana_credentials["base_url"],
                )
            assert "SDK Init Error" in str(excinfo.value)

    @pytest.mark.mocked
    def test_import_error_handling(self):
        """Verify module has top-level try/except ImportError handling."""
        import src.application.application_analyze as module

        source_code = inspect.getsource(module)
        assert "try:" in source_code
        assert "from instana_client.api.application_analyze_api import ApplicationAnalyzeApi" in source_code
        assert "except ImportError:" in source_code
        assert "logger.error(\"Failed to import application analyze API\"" in source_code
        assert "raise" in source_code


class TestApplicationAnalyzeE2E:
    """End-to-end tests for Application Analyze MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_groups_mocked_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_trace_groups_without_preload_content.return_value = _MockResponse(
            json.dumps(
                {
                    "items": [{"group": "service-a", "cursor": {"ingestionTime": 1710000000, "offset": 2}}],
                    "canLoadMore": True,
                    "totalHits": 3,
                }
            ).encode("utf-8")
        )

        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload={
                "group": {"groupbyTag": "trace.service.name", "groupbyTagEntity": "DESTINATION"},
                "metrics": [{"metric": "traces", "aggregation": "SUM"}],
                "timeFrame": {"windowSize": 3600000}
            },
            api_client=mock_api
        )

        assert isinstance(result, dict)
        assert "items" in result
        assert result["itemCount"] == 1
        assert result["canLoadMore"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_groups_invalid_payload(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload="invalid{json",
            api_client=MagicMock()
        )

        assert isinstance(result, dict)
        assert "error" in result
        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_groups_error_handling(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_trace_groups_without_preload_content.side_effect = Exception("API Error")

        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload={
                "group": {"groupbyTag": "trace.service.name", "groupbyTagEntity": "DESTINATION"},
                "metrics": [{"metric": "traces", "aggregation": "SUM"}]
            },
            api_client=mock_api
        )

        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to get trace groups" in result["error"]


class TestApplicationAnalyzeGetAllTracesE2E:
    """get_all_traces"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.usefixtures("real_analyze_sdk_models")
    async def test_success_builds_sdk_request_and_paginates(self, instana_credentials):
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _json_response({
            "items": [
                {"trace": {"id": "t1"}},
                {"trace": {"id": "t2"}, "cursor": {"ingestionTime": 1710000000, "offset": 2}},
            ],
            "canLoadMore": True,
            "totalHits": 9,
        })
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(
            payload={
                "includeInternal": "false",
                "tagFilterExpression": _valid_trace_filter(),
                "order": {"by": "traceLabel", "direction": "DESC"},
                "pagination": {"retrievalSize": 10},
                "timeFrame": {"windowSize": 3600000},
            },
            api_client=api,
        )

        assert result["itemCount"] == 2
        assert result["totalHits"] == 9
        assert result["canLoadMore"] is True
        assert result["ingestionTime"] == 1710000000
        assert result["offset"] == 2

        api.get_traces_without_preload_content.assert_called_once()
        config = api.get_traces_without_preload_content.call_args.kwargs["get_traces"]
        assert config.include_internal is False  # "false" string coerced to bool
        assert config.order.by == "traceLabel"
        assert config.pagination.retrieval_size == 10
        assert config.time_frame.window_size == 3600000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_no_cursor_when_last_page(self, instana_credentials):
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _json_response({
            "items": [{"trace": {"id": "t1"}, "cursor": {"ingestionTime": 1, "offset": 1}}],
            "canLoadMore": False,
            "totalHits": 1,
        })
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload={}, api_client=api)

        assert result["canLoadMore"] is False
        assert "ingestionTime" not in result
        assert "offset" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_none_payload_uses_empty_request(self, instana_credentials):
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _json_response({"items": []})
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload=None, api_client=api)

        assert result == {"items": [], "itemCount": 0, "canLoadMore": False}
        api.get_traces_without_preload_content.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_total_hits_omitted_when_absent(self, instana_credentials):
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _json_response({"items": [{"a": 1}]})
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload={}, api_client=api)

        assert "totalHits" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_sanitizes_none_technologies(self, instana_credentials):
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _json_response({
            "items": [{"trace": {"service": {"technologies": None}, "others": [{"technologies": None}]}}],
        })
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload={}, api_client=api)

        trace = result["items"][0]["trace"]
        assert trace["service"]["technologies"] == []
        assert trace["others"][0]["technologies"] == []

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.usefixtures("real_analyze_sdk_models")
    @pytest.mark.parametrize("payload", [
        '{"timeFrame": {"windowSize": 3600000}}',
        "{'timeFrame': {'windowSize': 3600000}}",
    ])
    async def test_string_payload_formats(self, instana_credentials, payload):
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _json_response({"items": []})
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload=payload, api_client=api)

        assert "error" not in result
        config = api.get_traces_without_preload_content.call_args.kwargs["get_traces"]
        assert config.time_frame.window_size == 3600000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.usefixtures("real_analyze_sdk_models")
    async def test_python_literal_payload(self, instana_credentials):
        """Python literals with True are not JSON, even after quote replacement."""
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _json_response({"items": []})
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload="{'includeInternal': True}", api_client=api)

        assert "error" not in result
        config = api.get_traces_without_preload_content.call_args.kwargs["get_traces"]
        assert config.include_internal is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_string_payload(self, instana_credentials):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload="not{valid", api_client=api)

        assert "Invalid payload format" in result["error"]
        api.get_traces_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("payload,expected", [
        ({"tagFilterExpression": "x"}, "tagFilterExpression: must be a dict"),
        ({"order": {"by": "traceLabel", "direction": "SIDEWAYS"}}, "order.direction: 'SIDEWAYS' is not valid"),
        ({"pagination": {"retrievalSize": 99999}}, "pagination.retrievalSize: 99999 is out of range"),
        ({"timeFrame": {"windowSize": "a"}}, "timeFrame.windowSize: must be an integer"),
    ])
    async def test_validation_failures_return_elicitation(self, instana_credentials, payload, expected):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload=payload, api_client=api)

        assert result["elicitation_needed"] is True
        assert any(expected in e for e in result["api_error"]), result["api_error"]
        assert "1 problem(s)" in result["message"]
        api.get_traces_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_multiple_validation_errors_collected(self, instana_credentials):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(
            payload={"tagFilterExpression": "x", "pagination": {"retrievalSize": 99999}},
            api_client=api,
        )

        assert len(result["api_error"]) == 2
        assert "2 validation problem(s)" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_api_error(self, instana_credentials):
        api = MagicMock()
        api.get_traces_without_preload_content.side_effect = Exception("boom")
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload={}, api_client=api)

        assert "Failed to get traces" in result["error"]
        assert "boom" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_non_json_response_body(self, instana_credentials):
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _MockResponse(b"<html>nope</html>")
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(payload={}, api_client=api)

        assert "Failed to get traces" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.usefixtures("real_analyze_sdk_models")
    @pytest.mark.parametrize("bool_val,expected", [
        ("true", True),
        ("TRUE", True),
        ("false", False),
        ("FALSE", False),
        (True, True),
        (False, False),
    ])
    async def test_bool_flags_coercion(self, instana_credentials, bool_val, expected):
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _json_response({"items": []})
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_all_traces(
            payload={"includeInternal": bool_val, "includeSynthetic": bool_val},
            api_client=api,
        )

        assert "error" not in result
        config = api.get_traces_without_preload_content.call_args.kwargs["get_traces"]
        assert config.include_internal is expected
        assert config.include_synthetic is expected

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_forwards_ctx_and_routing_metadata(self, instana_credentials):
        api = MagicMock()
        api.get_traces_without_preload_content.return_value = _json_response({"items": []})
        client = create_application_analyze_client(instana_credentials)

        mock_ctx = MagicMock()
        result = await client.get_all_traces(
            payload={},
            api_client=api,
            ctx=mock_ctx,
            resource_type="analyze",
            tool_name="test_tool",
        )

        assert result == {"items": [], "itemCount": 0, "canLoadMore": False}
        api.get_traces_without_preload_content.assert_called_once()


class TestApplicationAnalyzeGetTraceGroupsE2E:
    """get_trace_groups (beyond the basic success/error tests)"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.usefixtures("real_analyze_sdk_models")
    async def test_builds_sdk_request(self, instana_credentials):
        api = MagicMock()
        api.get_trace_groups_without_preload_content.return_value = _json_response(
            {"items": [{"group": "a"}], "canLoadMore": False, "totalHits": 1}
        )
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload=_valid_group_payload(
                includeInternal="true",
                timeFrame={"windowSize": 60000},
                order={"by": "traces", "direction": "ASC"},
            ),
            api_client=api,
        )

        assert result == {"items": [{"group": "a"}], "itemCount": 1, "canLoadMore": False, "totalHits": 1}
        config = api.get_trace_groups_without_preload_content.call_args.kwargs["get_trace_groups"]
        assert config.group.groupby_tag == "trace.service.name"
        assert config.include_internal is True
        assert config.time_frame.window_size == 60000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_returns_cursor_when_more_data(self, instana_credentials):
        api = MagicMock()
        api.get_trace_groups_without_preload_content.return_value = _json_response({
            "items": [{"group": "a", "cursor": {"ingestionTime": 11, "offset": 4}}],
            "canLoadMore": True,
        })
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(payload=_valid_group_payload(), api_client=api)

        assert result["ingestionTime"] == 11
        assert result["offset"] == 4
        assert "totalHits" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_sanitizes_none_technologies(self, instana_credentials):
        api = MagicMock()
        api.get_trace_groups_without_preload_content.return_value = _json_response(
            {"items": [{"service": {"technologies": None}}]}
        )
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(payload=_valid_group_payload(), api_client=api)

        assert result["items"][0]["service"]["technologies"] == []

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("payload", [None, {}])
    async def test_missing_group_and_metrics(self, instana_credentials, payload):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(payload=payload, api_client=api)

        assert result["elicitation_needed"] is True
        assert "group: required field missing" in result["api_error"]
        assert "metrics: required field missing" in result["api_error"]
        api.get_trace_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unsupported_groupby_tag(self, instana_credentials):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload=_valid_group_payload(group={"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}),
            api_client=api,
        )

        assert any("'service.name' is not supported for trace groups" in e for e in result["api_error"])
        api.get_trace_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alternate_groupby_tag_spelling_is_checked(self, instana_credentials):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload=_valid_group_payload(group={"groupByTag": "bogus", "groupbyTagEntity": "DESTINATION"}),
            api_client=api,
        )

        assert result["elicitation_needed"] is True
        assert any("'bogus' is not supported" in e for e in result["api_error"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_calls_metric_rejected(self, instana_credentials):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload=_valid_group_payload(metrics=[
                {"metric": "traces", "aggregation": "SUM"},
                {"metric": "calls", "aggregation": "SUM"},
            ]),
            api_client=api,
        )

        assert any("metrics[1].metric: 'calls' is not supported" in e for e in result["api_error"])
        api.get_trace_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_multiple_errors_in_one_response(self, instana_credentials):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload=_valid_group_payload(
                group={"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"},
                metrics=[{"metric": "calls", "aggregation": "SUM"}],
            ),
            api_client=api,
        )

        assert len(result["api_error"]) == 2
        assert "2 problem(s)" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("override,expected", [
        ({"tagFilterExpression": "x"}, "tagFilterExpression"),
        ({"order": {"by": "traces", "direction": "UP"}}, "order.direction"),
        ({"pagination": {"retrievalSize": 99999}}, "pagination.retrievalSize"),
        ({"timeFrame": {"windowSize": "a"}}, "timeFrame.windowSize"),
    ])
    async def test_optional_section_validation(self, instana_credentials, override, expected):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(payload=_valid_group_payload(**override), api_client=api)

        assert any(e.startswith(expected) for e in result["api_error"]), result["api_error"]
        api.get_trace_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_string_payload_accepted(self, instana_credentials):
        api = MagicMock()
        api.get_trace_groups_without_preload_content.return_value = _json_response({"items": []})
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(payload=json.dumps(_valid_group_payload()), api_client=api)

        assert result == {"items": [], "itemCount": 0, "canLoadMore": False}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metrics_max_items_exceeded(self, instana_credentials):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload=_valid_group_payload(
                metrics=[
                    {"metric": "traces", "aggregation": "SUM"},
                    {"metric": "traces", "aggregation": "MEAN"},
                    {"metric": "traces", "aggregation": "MAX"},
                    {"metric": "traces", "aggregation": "MIN"},
                    {"metric": "traces", "aggregation": "P90"},
                    {"metric": "traces", "aggregation": "P95"},
                ]
            ),
            api_client=api,
        )

        assert result["elicitation_needed"] is True
        assert any("metrics: contains 6 items but maximum allowed is 5" in e for e in result["api_error"])
        api.get_trace_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_non_json_response_body(self, instana_credentials):
        api = MagicMock()
        api.get_trace_groups_without_preload_content.return_value = _MockResponse(b"<html>invalid</html>")
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(payload=_valid_group_payload(), api_client=api)

        assert "Failed to get trace groups" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.usefixtures("real_analyze_sdk_models")
    async def test_endpoint_name_groupby_tag(self, instana_credentials):
        api = MagicMock()
        api.get_trace_groups_without_preload_content.return_value = _json_response({"items": []})
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_groups(
            payload=_valid_group_payload(
                group={"groupbyTag": "trace.endpoint.name", "groupbyTagEntity": "DESTINATION"}
            ),
            api_client=api,
        )

        assert result == {"items": [], "itemCount": 0, "canLoadMore": False}
        config = api.get_trace_groups_without_preload_content.call_args.kwargs["get_trace_groups"]
        assert config.group.groupby_tag == "trace.endpoint.name"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_forwards_ctx_and_routing_metadata(self, instana_credentials):
        api = MagicMock()
        api.get_trace_groups_without_preload_content.return_value = _json_response({"items": []})
        client = create_application_analyze_client(instana_credentials)

        mock_ctx = MagicMock()
        result = await client.get_trace_groups(
            payload=_valid_group_payload(),
            api_client=api,
            ctx=mock_ctx,
            resource_type="analyze",
            tool_name="test_tool",
        )

        assert result == {"items": [], "itemCount": 0, "canLoadMore": False}
        api.get_trace_groups_without_preload_content.assert_called_once()


class TestApplicationAnalyzeGetTraceDetailsE2E:
    """get_trace_details"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_success_with_cursor(self, instana_credentials):
        api = MagicMock()
        api.get_trace_download.return_value = {
            "items": [{"span": 1}, {"span": 2, "cursor": {"ingestionTime": 5, "offset": 2}}],
            "canLoadMore": True,
        }
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_details(id="trace-1", retrieval_size=2, api_client=api)

        assert result["itemCount"] == 2
        assert result["canLoadMore"] is True
        assert result["ingestionTime"] == 5
        assert result["offset"] == 2
        api.get_trace_download.assert_called_once_with(
            id="trace-1", retrieval_size=2, offset=None, ingestion_time=None
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_to_dict_result_without_more_data(self, instana_credentials):
        response = MagicMock()
        response.to_dict.return_value = {"items": [{"span": 1, "cursor": {"ingestionTime": 5}}], "canLoadMore": False}
        api = MagicMock()
        api.get_trace_download.return_value = response
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_details(id="trace-1", api_client=api)

        assert result == {"items": [{"span": 1, "cursor": {"ingestionTime": 5}}], "itemCount": 1, "canLoadMore": False}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_partial_cursor_fields(self, instana_credentials):
        api = MagicMock()
        api.get_trace_download.return_value = {
            "items": [{"cursor": {"offset": 7}}],
            "canLoadMore": True,
        }
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_details(id="trace-1", api_client=api)

        assert result["offset"] == 7
        assert "ingestionTime" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_items(self, instana_credentials):
        api = MagicMock()
        api.get_trace_download.return_value = {"canLoadMore": True}
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_details(id="trace-1", api_client=api)

        assert result == {"items": [], "itemCount": 0, "canLoadMore": True}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_forwards_pagination_args(self, instana_credentials):
        api = MagicMock()
        api.get_trace_download.return_value = {"items": []}
        client = create_application_analyze_client(instana_credentials)

        await client.get_trace_details(
            id="trace-1", retrieval_size=10, offset=3, ingestion_time=99, api_client=api
        )

        api.get_trace_download.assert_called_once_with(
            id="trace-1", retrieval_size=10, offset=3, ingestion_time=99
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_all_validation_errors_collected(self, instana_credentials):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_details(id="", retrieval_size=0, offset=1, api_client=api)

        assert result["elicitation_needed"] is True
        assert len(result["api_error"]) == 3
        assert result["api_error"][0].startswith("id: required")
        assert result["api_error"][1].startswith("retrievalSize: 0")
        assert result["api_error"][2].startswith("ingestionTime: required")
        api.get_trace_download.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("size", [0, -1, 10001])
    async def test_retrieval_size_out_of_range(self, instana_credentials, size):
        api = MagicMock()
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_details(id="trace-1", retrieval_size=size, api_client=api)

        assert f"retrievalSize: {size} is out of range" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("size", [1, 10000])
    async def test_retrieval_size_boundaries_accepted(self, instana_credentials, size):
        api = MagicMock()
        api.get_trace_download.return_value = {"items": []}
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_details(id="trace-1", retrieval_size=size, api_client=api)

        assert "error" not in result
        assert "elicitation_needed" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_api_error(self, instana_credentials):
        api = MagicMock()
        api.get_trace_download.side_effect = Exception("boom")
        client = create_application_analyze_client(instana_credentials)

        result = await client.get_trace_details(id="trace-1", api_client=api)

        assert "Failed to get trace details" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_forwards_ctx_and_routing_metadata(self, instana_credentials):
        api = MagicMock()
        api.get_trace_download.return_value = {"items": []}
        client = create_application_analyze_client(instana_credentials)

        mock_ctx = MagicMock()
        result = await client.get_trace_details(
            id="trace-1",
            api_client=api,
            ctx=mock_ctx,
            resource_type="analyze",
            tool_name="test_tool",
        )

        assert result == {"items": [], "itemCount": 0, "canLoadMore": False}
        api.get_trace_download.assert_called_once_with(
            id="trace-1", retrieval_size=None, offset=None, ingestion_time=None
        )


class TestApplicationAnalyzeHelpersE2E:
    """Pure helper methods"""

    @pytest.mark.mocked
    def test_parse_traces_payload_variants(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        assert client._parse_traces_payload(None) == {}
        assert client._parse_traces_payload({"a": 1}) == {"a": 1}
        assert client._parse_traces_payload('{"a": 1}') == {"a": 1}
        assert client._parse_traces_payload("{'a': 1}") == {"a": 1}
        assert client._parse_traces_payload("{'a': True}") == {"a": True}
        assert "Invalid payload format" in client._parse_traces_payload("{oops")["error"]

    @pytest.mark.mocked
    def test_sanitize_service_data_nested(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        data = {
            "technologies": None,
            "list": [{"technologies": None}, "plain", 3],
            "nested": {"deeper": {"technologies": None, "keep": ["x"]}},
        }

        result = client._sanitize_service_data(data)

        assert result["technologies"] == []
        assert result["list"][0]["technologies"] == []
        assert result["list"][1:] == ["plain", 3]
        assert result["nested"]["deeper"] == {"technologies": [], "keep": ["x"]}

    @pytest.mark.mocked
    def test_sanitize_service_data_leaves_non_dict_untouched(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        assert client._sanitize_service_data("text") == "text"
        assert client._sanitize_service_data({"technologies": ["java"]}) == {"technologies": ["java"]}

    @pytest.mark.mocked
    def test_build_paginated_response_total_hits_toggle(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        body = {"items": [{"cursor": {"ingestionTime": 1, "offset": 2}}], "canLoadMore": True, "totalHits": 5}

        with_hits = client._build_paginated_response(body, include_total_hits=True)
        without_hits = client._build_paginated_response(body, include_total_hits=False)

        assert with_hits["totalHits"] == 5
        assert "totalHits" not in without_hits
        assert without_hits["ingestionTime"] == 1
        assert without_hits["offset"] == 2

    @pytest.mark.mocked
    def test_coerce_bool_flags(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        body = {"includeInternal": "true", "includeSynthetic": "false", "other": "true"}

        client._coerce_bool_flags(body)

        assert body == {"includeInternal": True, "includeSynthetic": False, "other": "true"}

    @pytest.mark.mocked
    def test_check_groupby_tag_ignores_non_dict_and_missing_tag(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        errors = []
        client._check_groupby_tag("not-a-dict", errors)
        client._check_groupby_tag({}, errors)
        client._check_groupby_tag({"groupbyTag": "trace.endpoint.name"}, errors)
        assert errors == []

    @pytest.mark.mocked
    def test_check_calls_metric_ignores_non_list_and_non_dict_entries(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        errors = []
        client._check_calls_metric("calls", errors)
        client._check_calls_metric(["calls", {"metric": "traces"}], errors)
        assert errors == []

    @pytest.mark.mocked
    def test_validate_trace_details_params_valid(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        assert client._validate_trace_details_params("t", 10, 1, 5) is None
        assert client._validate_trace_details_params("t", None, None, None) is None

    @pytest.mark.mocked
    def test_parse_traces_payload_non_str_and_empty(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        assert client._parse_traces_payload([]) == []
        assert client._parse_traces_payload(123) == 123
        assert client._parse_traces_payload({}) == {}

    @pytest.mark.mocked
    def test_build_paginated_response_edge_cases(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        # Empty result
        assert client._build_paginated_response({}) == {
            "items": [],
            "itemCount": 0,
            "canLoadMore": False,
        }
        # canLoadMore is True but last item has no cursor
        body_no_cursor = {"items": [{"id": "1"}], "canLoadMore": True}
        assert client._build_paginated_response(body_no_cursor) == {
            "items": [{"id": "1"}],
            "itemCount": 1,
            "canLoadMore": True,
        }
        # canLoadMore is False with cursor in last item (cursor ignored)
        body_false_more = {"items": [{"cursor": {"ingestionTime": 1, "offset": 2}}], "canLoadMore": False}
        resp = client._build_paginated_response(body_false_more)
        assert resp["canLoadMore"] is False
        assert "ingestionTime" not in resp
        assert "offset" not in resp

    @pytest.mark.mocked
    def test_check_groupby_tag_supported_tags(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        for tag in ["trace.endpoint.name", "trace.service.name"]:
            errors = []
            client._check_groupby_tag({"groupbyTag": tag}, errors)
            assert errors == []
            errors_camel = []
            client._check_groupby_tag({"groupByTag": tag}, errors_camel)
            assert errors_camel == []

    @pytest.mark.mocked
    def test_check_calls_metric_multiple_occurrences(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        errors = []
        metrics = [
            {"metric": "calls", "aggregation": "SUM"},
            {"metric": "traces", "aggregation": "SUM"},
            {"metric": "calls", "aggregation": "MEAN"},
        ]
        client._check_calls_metric(metrics, errors)
        assert len(errors) == 2
        assert "metrics[0].metric: 'calls' is not supported" in errors[0]
        assert "metrics[2].metric: 'calls' is not supported" in errors[1]


class TestApplicationAnalyzeExecuteOperationE2E:
    """execute_analyze_operation dispatcher"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_traces_routes_payload(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        mock = AsyncMock(return_value={"routed": True})
        with patch.object(client, "get_all_traces", mock):
            result = await client.execute_analyze_operation(
                "get_all_traces", {"payload": {"a": 1}}, resource_type="analyze", tool_name="tool"
            )

        assert result == {"routed": True}
        mock.assert_awaited_once_with(
            {"a": 1}, ctx=None, resource_type="analyze", tool_name="tool"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_details_maps_camel_case_params(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        mock = AsyncMock(return_value={"routed": True})
        with patch.object(client, "get_trace_details", mock):
            await client.execute_analyze_operation(
                "get_trace_details",
                {"id": "t1", "retrievalSize": 5, "offset": 2, "ingestionTime": 99},
            )

        kwargs = mock.call_args.kwargs
        assert kwargs["id"] == "t1"
        assert kwargs["retrieval_size"] == 5
        assert kwargs["offset"] == 2
        assert kwargs["ingestion_time"] == 99

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("params,expected_payload", [
        ({"payload": {"g": 1}}, {"g": 1}),
        (None, None),
        ({}, None),
    ])
    async def test_get_trace_groups_routes_payload(self, instana_credentials, params, expected_payload):
        client = create_application_analyze_client(instana_credentials)
        mock = AsyncMock(return_value={"routed": True})
        with patch.object(client, "get_trace_groups", mock):
            await client.execute_analyze_operation("get_trace_groups", params)

        assert mock.call_args.args[0] == expected_payload

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unsupported_operation(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)

        result = await client.execute_analyze_operation("bogus", {})

        assert result == {"error": "Operation 'bogus' not supported"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_exceptions_are_wrapped(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)

        # params=None makes the get_all_traces branch raise AttributeError
        result = await client.execute_analyze_operation("get_all_traces", None)

        assert "Error executing get_all_traces" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_details_dispatcher_exception_wrapped(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)

        # params=None causes params.get to raise AttributeError
        result = await client.execute_analyze_operation("get_trace_details", None)

        assert "Error executing get_trace_details" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_details_forwards_ctx_and_routing(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        mock = AsyncMock(return_value={"routed": True})
        mock_ctx = MagicMock()
        with patch.object(client, "get_trace_details", mock):
            result = await client.execute_analyze_operation(
                "get_trace_details",
                {"id": "t1"},
                ctx=mock_ctx,
                resource_type="analyze",
                tool_name="test_tool",
            )

        assert result == {"routed": True}
        mock.assert_awaited_once_with(
            id="t1",
            retrieval_size=None,
            offset=None,
            ingestion_time=None,
            ctx=mock_ctx,
            resource_type="analyze",
            tool_name="test_tool",
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_groups_forwards_ctx_and_routing(self, instana_credentials):
        client = create_application_analyze_client(instana_credentials)
        mock = AsyncMock(return_value={"routed": True})
        mock_ctx = MagicMock()
        with patch.object(client, "get_trace_groups", mock):
            result = await client.execute_analyze_operation(
                "get_trace_groups",
                {"payload": {"group": {}}},
                ctx=mock_ctx,
                resource_type="analyze",
                tool_name="test_tool",
            )

        assert result == {"routed": True}
        mock.assert_awaited_once_with(
            {"group": {}},
            ctx=mock_ctx,
            resource_type="analyze",
            tool_name="test_tool",
        )
