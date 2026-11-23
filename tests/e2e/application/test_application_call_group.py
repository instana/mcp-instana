"""
E2E tests for Application Call Group MCP Tools
"""

import importlib
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def real_call_groups_model():
    """Skip when another test module has replaced the SDK model with a mock (mixed test runs)."""
    module = importlib.import_module("instana_client.models.get_call_groups")
    if not isinstance(getattr(module, "GetCallGroups", None), type):
        pytest.skip("instana_client.models.get_call_groups.GetCallGroups is mocked in this session")


def create_application_call_group_client(instana_credentials):
    """Dynamically import and create Application Call Group client"""
    module = importlib.import_module("src.application.application_call_group")
    module = importlib.reload(module)
    return module.ApplicationCallGroupMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


def _valid_args(**overrides):
    args = {
        "metrics": [{"metric": "calls", "aggregation": "SUM"}],
        "time_frame": {"to": 1700000000000, "windowSize": 3600000},
        "group": {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"},
    }
    args.update(overrides)
    return args


def _mock_api(return_value=None, side_effect=None):
    mock_api = MagicMock()
    mock_api.get_call_group = MagicMock(return_value=return_value, side_effect=side_effect)
    return mock_api


class TestApplicationCallGroupE2E:
    """End-to-end tests for Application Call Group MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ------------------------------------------------------------------
    # Elicitation / validation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_elicitation_when_everything_missing(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        mock_api = _mock_api()

        result = await client.get_grouped_calls_metrics(api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert result["missing_parameters"] == ["metrics", "time_frame", "group"]
        assert "metrics:" in result["message"]
        assert "time_frame:" in result["message"]
        assert "group:" in result["message"]
        mock_api.get_call_group.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_elicitation_when_only_group_missing(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        mock_api = _mock_api()
        args = _valid_args()
        args.pop("group")

        result = await client.get_grouped_calls_metrics(api_client=mock_api, **args)

        assert result["elicitation_needed"] is True
        assert result["missing_parameters"] == ["group"]
        mock_api.get_call_group.assert_not_called()

    @pytest.mark.mocked
    def test_create_elicitation_request_unknown_param_uses_examples(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)

        result = client._create_elicitation_request(
            [{"name": "custom", "description": "x", "examples": ["a", "b", "c", "d"], "type": "str"}]
        )

        assert result["missing_parameters"] == ["custom"]
        assert "custom: a, b, c" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_structure_validation_failure(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        mock_api = _mock_api()

        result = await client.get_grouped_calls_metrics(
            api_client=mock_api,
            **_valid_args(metrics=[{"metric": "calls", "aggregation": "BAD"}]),
        )

        assert result["elicitation_needed"] is True
        assert result["api_error"]
        assert "validation problem" in result["reason"]
        mock_api.get_call_group.assert_not_called()

    @pytest.mark.mocked
    def test_validate_call_group_structure_valid_returns_none(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        args = _valid_args()
        assert client._validate_call_group_structure(
            args["metrics"], args["time_frame"], args["group"], None, None, None
        ) is None

    # ------------------------------------------------------------------
    # Success paths
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_success_dict(self, instana_credentials, real_call_groups_model):
        client = create_application_call_group_client(instana_credentials)
        api_response = {
            "items": [
                {
                    "name": "svc-a",
                    "metrics": {
                        "calls.sum": [[1700000000000, 120.0]],
                        "errors.mean": [[1700000000000, 0.05]],
                        "latency.mean": [[1700000000000, 12.345]],
                        "erroneousCalls.sum": [[1700000000000, 6.0]],
                        "other.sum": [[1700000000000, 1.0]],
                        "empty.sum": [],
                        "short.sum": [[1]],
                    },
                },
                {"name": "svc-b", "metrics": "not-a-dict"},
                "not-a-dict-item",
            ]
        }
        mock_api = _mock_api(api_response)

        result = await client.get_grouped_calls_metrics(
            api_client=mock_api,
            fill_time_series=True,
            include_internal="true",
            include_synthetic="false",
            order={"by": "calls", "direction": "DESC"},
            pagination={"retrievalSize": 10},
            tag_filter_expression={
                "type": "TAG_FILTER",
                "name": "call.type",
                "operator": "EQUALS",
                "entity": "NOT_APPLICABLE",
                "value": "HTTP",
            },
            **_valid_args(),
        )

        assert result["summary"]["total_groups"] == 3
        first = result["items"][0]
        assert first["metrics_summary"]["total_calls"] == 120
        assert first["metrics_summary"]["error_rate"] == "5.00%"
        assert first["metrics_summary"]["latency_ms"] == "12.35ms"
        assert first["metrics_summary"]["erroneous_calls"] == 6
        assert "Error Rate: 5.00%" in first["interpretation"]
        assert "Total Calls: 120" in first["interpretation"]
        assert "Erroneous Calls: 6" in first["interpretation"]
        assert "Latency: 12.35ms" in first["interpretation"]
        assert "other.sum" in first["metrics_extracted"]
        assert "empty.sum" not in first["metrics_extracted"]
        # item whose metrics is not a dict is returned as-is
        assert "metrics_extracted" not in result["items"][1]
        assert result["items"][2] == "not-a-dict-item"

        mock_api.get_call_group.assert_called_once()
        kwargs = mock_api.get_call_group.call_args.kwargs
        assert kwargs["fill_time_series"] is True
        body = kwargs["get_call_groups"]
        assert body.include_internal is True
        assert body.include_synthetic is False
        assert body.pagination.retrieval_size == 10

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_success_to_dict_object(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        response = MagicMock()
        response.to_dict.return_value = {
            "items": [{"name": "svc", "metrics": {"calls.sum": [[1, 3.0]]}}]
        }
        mock_api = _mock_api(response)

        result = await client.get_grouped_calls_metrics(api_client=mock_api, **_valid_args())

        assert result["items"][0]["metrics_summary"] == {"total_calls": 3}
        assert result["summary"]["total_groups"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_empty_items_has_no_summary(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        mock_api = _mock_api({"items": []})

        result = await client.get_grouped_calls_metrics(api_client=mock_api, **_valid_args())

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_non_dict_response(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        mock_api = _mock_api(["raw"])

        result = await client.get_grouped_calls_metrics(api_client=mock_api, **_valid_args())

        assert result == ["raw"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_aggregates_latency_by_endpoint(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        mock_api = _mock_api(
            {
                "items": [
                    {"name": "e1", "metrics": {"latency.mean": [[1, 10.0]]}},
                    {"name": "e2", "metrics": {"latency.mean": [[1, 30.0]]}},
                    "skip-me",
                ]
            }
        )

        result = await client.get_grouped_calls_metrics(
            api_client=mock_api,
            metrics=[{"metric": "latency", "aggregation": "MEAN"}],
            time_frame={"to": 1700000000000, "windowSize": 3600000},
            group={"groupbyTag": "endpoint.name", "groupbyTagEntity": "DESTINATION"},
        )

        assert result["aggregated"] is True
        assert result["total_groups_analyzed"] == 3
        overall = result["overall_metrics"]["latency.mean"]
        assert overall["value"] == pytest.approx(20.0)
        assert overall["unit"] == "ms"
        assert "Average across 2 endpoints" in overall["note"]
        assert result["summary"] == "Overall mean latency: 20.00ms across 3 endpoints"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_aggregates_empty_items(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        mock_api = _mock_api({"items": []})

        result = await client.get_grouped_calls_metrics(
            api_client=mock_api,
            metrics=[{"metric": "latency", "aggregation": "MEAN"}],
            time_frame={"to": 1700000000000, "windowSize": 3600000},
            group={"groupbyTag": "endpoint.name", "groupbyTagEntity": "DESTINATION"},
        )

        assert result["aggregated"] is True
        assert result["overall_metrics"] == {}
        assert "No data available" in result["message"]

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_api_error(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        mock_api = _mock_api(side_effect=Exception("API Error"))

        result = await client.get_grouped_calls_metrics(api_client=mock_api, **_valid_args())

        assert "error" in result
        assert "Failed to get grouped calls metrics" in result["error"]
        assert "API Error" in result["error"]

    # ------------------------------------------------------------------
    # Helper branches
    # ------------------------------------------------------------------

    @pytest.mark.mocked
    def test_apply_call_group_defaults(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)

        metrics, time_frame, group = client._apply_call_group_defaults(None, None, None)

        assert metrics == [
            {"metric": "calls", "aggregation": "SUM"},
            {"metric": "latency", "aggregation": "MEAN"},
        ]
        assert time_frame["windowSize"] == 3600000
        assert isinstance(time_frame["to"], int)
        assert group == {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}

        given = ([{"metric": "x"}], {"windowSize": 1}, {"groupbyTag": "t"})
        assert client._apply_call_group_defaults(*given) == given

    @pytest.mark.mocked
    def test_build_call_group_request_optional_fields(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        base = ([{"metric": "calls"}], {"windowSize": 1}, {"groupbyTag": "t"})

        minimal = client._build_call_group_request(*base, None, None, None, None, None)
        assert set(minimal) == {"group", "metrics", "timeFrame"}

        full = client._build_call_group_request(
            *base, {"type": "EXPRESSION"}, {"by": "calls"}, {"retrievalSize": 5}, True, False
        )
        assert full["tagFilterExpression"] == {"type": "EXPRESSION"}
        assert full["order"] == {"by": "calls"}
        assert full["pagination"] == {"retrievalSize": 5}
        assert full["includeInternal"] is True
        assert full["includeSynthetic"] is False

    @pytest.mark.mocked
    def test_log_call_group_response_variants(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        client._log_call_group_response(
            {
                "items": [
                    {"metrics": {"calls.sum": []}},
                    {"metrics": ["list-metrics"]},
                    "not-a-dict",
                ]
            }
        )
        client._log_call_group_response(["not", "a", "dict"])

    @pytest.mark.mocked
    def test_process_metrics_response_passthrough_and_error(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)

        assert client._process_metrics_response("text") == "text"
        assert client._process_metrics_response({"a": 1}) == {"a": 1}

        # items that is not iterable of dicts triggers the exception path
        bad = {"items": 5}
        assert client._process_metrics_response(bad) is bad

    @pytest.mark.mocked
    def test_should_aggregate_results(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        endpoint_group = {"groupbyTag": "endpoint.name"}
        latency_mean = [{"metric": "latency", "aggregation": "MEAN"}]

        assert client._should_aggregate_results(latency_mean, endpoint_group) is True
        assert client._should_aggregate_results(None, endpoint_group) is False
        assert client._should_aggregate_results(latency_mean, None) is False
        assert client._should_aggregate_results(latency_mean, {"groupbyTag": "service.name"}) is False
        assert client._should_aggregate_results(
            [{"metric": "latency", "aggregation": "P95"}], endpoint_group
        ) is False
        assert client._should_aggregate_results(
            [*latency_mean, {"metric": "calls", "aggregation": "SUM"}], endpoint_group
        ) is False

    @pytest.mark.mocked
    def test_accumulate_metric_value_variants(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        totals: dict = {}
        counts: dict = {}

        client._accumulate_metric_value("a", {"value": 2}, totals, counts)
        client._accumulate_metric_value("a", 4, totals, counts)
        client._accumulate_metric_value("a", 1.5, totals, counts)
        client._accumulate_metric_value("b", {"no_value": True}, totals, counts)
        client._accumulate_metric_value("c", "ignored", totals, counts)

        assert totals == {"a": 7.5, "b": 0}
        assert counts == {"a": 3, "b": 1}

    @pytest.mark.mocked
    def test_compute_overall_metrics_variants(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)

        overall = client._compute_overall_metrics(
            {"latency.mean": 10.0, "calls.sum": 8.0, "zero": 1.0}, {"latency.mean": 2, "calls.sum": 4, "zero": 0}
        )

        assert overall["latency.mean"]["unit"] == "ms"
        assert overall["calls.sum"] == {
            "value": 2.0,
            "aggregation": "MEAN",
            "note": "Average across 4 groups",
        }
        assert "zero" not in overall

    @pytest.mark.mocked
    def test_aggregate_grouped_results_edge_cases(self, instana_credentials):
        client = create_application_call_group_client(instana_credentials)
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]

        assert client._aggregate_grouped_results("text", metrics) == "text"
        assert client._aggregate_grouped_results({"no": "items"}, metrics) == {"no": "items"}

        # items without metrics_extracted fall back to raw metrics; no latency.mean => no summary
        result = client._aggregate_grouped_results(
            {"items": [{"metrics": {"calls.sum": 4}}, {"metrics": {"calls.sum": 6}}]}, metrics
        )
        assert result["overall_metrics"]["calls.sum"]["value"] == 5
        assert "summary" not in result

        # a non-dict metrics value makes .items() fail -> original dict is returned
        broken = {"items": [{"metrics": 5}]}
        assert client._aggregate_grouped_results(broken, metrics) is broken
