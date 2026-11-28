"""
Mocked E2E tests for Synthetic Test Playback Results MCP Tools (no real Instana API required)
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def _load_module():
    module = importlib.import_module("src.synthetic.synthetic_test_playback_results")
    return importlib.reload(module)


def create_synthetic_playback_client(instana_credentials):
    """Dynamically import and create Synthetic Test Playback Results client"""
    module = _load_module()
    return module.SyntheticTestPlaybackResultsMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload).encode("utf-8")
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


TIME_FRAME = {"windowSize": 3600000}
RESULT_PAYLOAD = {
    "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}],
    "timeFrame": TIME_FRAME,
    "pagination": {"page": 1, "pageSize": 3},
}
SYNTH_METRICS_PAYLOAD = {
    "syntheticMetrics": ["synthetic.metricsResponseTime", "synthetic.metricsStatus"],
    "timeFrame": TIME_FRAME,
}
SUMMARY_PAYLOAD = {
    "metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}],
    "timeFrame": {"windowSize": 1800000},
}
LOCATION_SUMMARY_PAYLOAD = {"timeFrame": {"windowSize": 300000}, "pagination": {"page": 1, "pageSize": 3}}

TAG_FILTER = {
    "type": "TAG_FILTER",
    "name": "synthetic.locationId",
    "operator": "EQUALS",
    "entity": "NOT_APPLICABLE",
    "stringValue": "loc1",
}

# (method name, SDK method name, SDK kwarg, valid payload)
PAYLOAD_OPERATIONS = [
    ("get_synthetic_result", "get_synthetic_result_without_preload_content", "get_test_result", RESULT_PAYLOAD),
    (
        "get_synthetic_result_analytic",
        "get_synthetic_result_analytic_without_preload_content",
        "get_test_result_analytic",
        {**SYNTH_METRICS_PAYLOAD, "analyticFunction": "LAST_VALUE"},
    ),
    (
        "get_synthetic_result_list",
        "get_synthetic_result_list_without_preload_content",
        "get_test_result_list",
        SYNTH_METRICS_PAYLOAD,
    ),
    (
        "get_location_summary_list",
        "get_location_summary_list_without_preload_content",
        "get_test_result_base",
        LOCATION_SUMMARY_PAYLOAD,
    ),
    (
        "get_test_summary_list",
        "get_test_summary_list_without_preload_content",
        "get_test_summary_result",
        SUMMARY_PAYLOAD,
    ),
]

_PAYLOAD_PARAMS = [pytest.param(*op, id=op[0]) for op in PAYLOAD_OPERATIONS]


class TestSyntheticTestPlaybackE2E:
    """End-to-end (mocked) tests for Synthetic Test Playback Results MCP Tools"""

    # ------------------------------------------------------------------
    # Payload-based operations: shared behaviour
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_fn,sdk_kwarg,payload", _PAYLOAD_PARAMS)
    async def test_success_dict_payload(self, instana_credentials, method, sdk_fn, sdk_kwarg, payload):
        expected = {"items": [{"id": "r1"}]}
        mock_api = MagicMock()
        getattr(mock_api, sdk_fn).return_value = _MockResponse(expected)
        client = create_synthetic_playback_client(instana_credentials)

        result = await getattr(client, method)(payload=payload, api_client=mock_api)

        assert result == expected
        assert sdk_kwarg in getattr(mock_api, sdk_fn).call_args.kwargs

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_fn,sdk_kwarg,payload", _PAYLOAD_PARAMS)
    async def test_success_json_string_payload(self, instana_credentials, method, sdk_fn, sdk_kwarg, payload):
        mock_api = MagicMock()
        getattr(mock_api, sdk_fn).return_value = _MockResponse({"items": []})
        client = create_synthetic_playback_client(instana_credentials)

        result = await getattr(client, method)(payload=json.dumps(payload), api_client=mock_api)

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_fn,sdk_kwarg,payload", _PAYLOAD_PARAMS)
    async def test_missing_payload(self, instana_credentials, method, sdk_fn, sdk_kwarg, payload):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        result = await getattr(client, method)(payload=None, api_client=mock_api)

        assert result == {"error": "payload is required"}
        getattr(mock_api, sdk_fn).assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_fn,sdk_kwarg,payload", _PAYLOAD_PARAMS)
    async def test_empty_object_payload(self, instana_credentials, method, sdk_fn, sdk_kwarg, payload):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        result = await getattr(client, method)(payload="{}", api_client=mock_api)

        assert result == {"error": "payload must not be an empty object"}
        getattr(mock_api, sdk_fn).assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_fn,sdk_kwarg,payload", _PAYLOAD_PARAMS)
    async def test_unparseable_payload(self, instana_credentials, method, sdk_fn, sdk_kwarg, payload):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        result = await getattr(client, method)(payload="{{not valid", api_client=mock_api)

        assert "error" in result
        getattr(mock_api, sdk_fn).assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_fn,sdk_kwarg,payload", _PAYLOAD_PARAMS)
    async def test_http_error(self, instana_credentials, method, sdk_fn, sdk_kwarg, payload):
        mock_api = MagicMock()
        getattr(mock_api, sdk_fn).return_value = _MockResponse(b"server error", status=500)
        client = create_synthetic_playback_client(instana_credentials)

        result = await getattr(client, method)(payload=payload, api_client=mock_api)

        assert "HTTP 500" in result["error"]
        assert result["status_code"] == 500
        assert result["details"] == "server error"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_fn,sdk_kwarg,payload", _PAYLOAD_PARAMS)
    async def test_sdk_exception(self, instana_credentials, method, sdk_fn, sdk_kwarg, payload):
        mock_api = MagicMock()
        getattr(mock_api, sdk_fn).side_effect = Exception("API Error")
        client = create_synthetic_playback_client(instana_credentials)

        result = await getattr(client, method)(payload=payload, api_client=mock_api)

        assert result["error"].startswith("Failed to get")
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "method,sdk_fn,model_name",
        [
            ("get_synthetic_result", "get_synthetic_result_without_preload_content", "GetTestResult"),
            ("get_synthetic_result_analytic", "get_synthetic_result_analytic_without_preload_content",
             "GetTestResultAnalytic"),
            ("get_synthetic_result_list", "get_synthetic_result_list_without_preload_content", "GetTestResultList"),
            ("get_location_summary_list", "get_location_summary_list_without_preload_content", "GetTestResultBase"),
            ("get_test_summary_list", "get_test_summary_list_without_preload_content", "GetTestSummaryResult"),
        ],
    )
    async def test_model_build_failure(self, instana_credentials, method, sdk_fn, model_name):
        module = _load_module()
        client = module.SyntheticTestPlaybackResultsMCPTools(
            read_token=instana_credentials["api_token"], base_url=instana_credentials["base_url"]
        )
        payload = next(op[3] for op in PAYLOAD_OPERATIONS if op[0] == method)
        mock_api = MagicMock()

        with patch.object(getattr(module, model_name), "from_dict", side_effect=ValueError("bad shape")):
            result = await getattr(client, method)(payload=payload, api_client=mock_api)

        assert f"Failed to build {model_name}" in result["error"]
        assert "bad shape" in result["error"]
        getattr(mock_api, sdk_fn).assert_not_called()

    # ------------------------------------------------------------------
    # Per-operation validation branches
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_result_requires_metrics(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        result = await client.get_synthetic_result(payload={"timeFrame": TIME_FRAME}, api_client=mock_api)

        assert result["elicitation_needed"] is True
        mock_api.get_synthetic_result_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_result_granularity_ratio_rejected(self, instana_credentials):
        payload = {
            "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM", "granularity": 1}],
            "timeFrame": {"windowSize": 2592000000},
        }
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        result = await client.get_synthetic_result(payload=payload, api_client=mock_api)

        assert result["elicitation_needed"] is True
        mock_api.get_synthetic_result_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method", ["get_synthetic_result_analytic", "get_synthetic_result_list"])
    async def test_synthetic_metrics_required(self, instana_credentials, method):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        result = await getattr(client, method)(payload={"timeFrame": TIME_FRAME}, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert any("syntheticMetrics" in e for e in result["api_error"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_synthetic_metrics_must_be_list_of_non_empty_strings(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        not_list = await client.get_synthetic_result_list(
            payload={"syntheticMetrics": "synthetic.metricsStatus"}, api_client=mock_api
        )
        assert any("must be a list of strings" in e for e in not_list["api_error"])

        bad_item = await client.get_synthetic_result_list(
            payload={"syntheticMetrics": ["ok", " "]}, api_client=mock_api
        )
        assert any("syntheticMetrics[1]" in e for e in bad_item["api_error"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_result_list_with_tag_filter_key_variants(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_result_list_without_preload_content.return_value = _MockResponse({"items": []})
        client = create_synthetic_playback_client(instana_credentials)
        payload = {**SYNTH_METRICS_PAYLOAD, "tagFilterExpression": TAG_FILTER}

        result = await client.get_synthetic_result_list(payload=payload, api_client=mock_api)

        assert result == {"items": []}
        cfg = mock_api.get_synthetic_result_list_without_preload_content.call_args.kwargs["get_test_result_list"]
        assert cfg.tag_filter_expression is not None

    # ------------------------------------------------------------------
    # get_synthetic_result_metadata
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metadata_success(self, instana_credentials):
        expected = {"detailTypes": [{"type": "HAR", "count": 1}]}
        mock_api = MagicMock()
        mock_api.get_synthetic_result_metadata_without_preload_content.return_value = _MockResponse(expected)
        client = create_synthetic_playback_client(instana_credentials)

        result = await client.get_synthetic_result_metadata(
            testid="t1", testresultid="r1", start_time=123, api_client=mock_api
        )

        assert result == expected
        mock_api.get_synthetic_result_metadata_without_preload_content.assert_called_once_with(
            testid="t1", testresultid="r1", start_time=123
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("testid,testresultid", [("", "r1"), ("t1", ""), (None, None)])
    async def test_get_metadata_missing_params(self, instana_credentials, testid, testresultid):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        result = await client.get_synthetic_result_metadata(
            testid=testid, testresultid=testresultid, api_client=mock_api
        )

        assert "required" in result["error"]
        mock_api.get_synthetic_result_metadata_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metadata_http_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        mock_api.get_synthetic_result_metadata_without_preload_content.return_value = _MockResponse(
            b"nf", status=404
        )
        err = await client.get_synthetic_result_metadata(testid="t1", testresultid="r1", api_client=mock_api)
        assert "HTTP 404" in err["error"]

        mock_api.get_synthetic_result_metadata_without_preload_content.side_effect = Exception("API Error")
        exc = await client.get_synthetic_result_metadata(testid="t1", testresultid="r1", api_client=mock_api)
        assert "Failed to get synthetic result metadata" in exc["error"]

    # ------------------------------------------------------------------
    # get_synthetic_result_detail_data
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_detail_data_success(self, instana_credentials):
        expected = {"log": {"entries": []}}
        mock_api = MagicMock()
        mock_api.get_synthetic_result_detail_data_without_preload_content.return_value = _MockResponse(expected)
        client = create_synthetic_playback_client(instana_credentials)

        result = await client.get_synthetic_result_detail_data(
            testid="t1", testresultid="r1", detail_type="HAR", name="n", start_time=5, api_client=mock_api
        )

        assert result == expected
        mock_api.get_synthetic_result_detail_data_without_preload_content.assert_called_once_with(
            testid="t1", testresultid="r1", type="HAR", name="n", start_time=5
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_detail_data_missing_ids(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        result = await client.get_synthetic_result_detail_data(
            testid="", testresultid="r1", detail_type="HAR", api_client=mock_api
        )

        assert "required" in result["error"]
        mock_api.get_synthetic_result_detail_data_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_detail_data_missing_detail_type(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        result = await client.get_synthetic_result_detail_data(
            testid="t1", testresultid="r1", detail_type="", api_client=mock_api
        )

        assert "'detail_type' parameter is required" in result["error"]
        mock_api.get_synthetic_result_detail_data_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_detail_data_http_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_playback_client(instana_credentials)

        mock_api.get_synthetic_result_detail_data_without_preload_content.return_value = _MockResponse(
            b"gone", status=410
        )
        err = await client.get_synthetic_result_detail_data(
            testid="t1", testresultid="r1", detail_type="LOGS", api_client=mock_api
        )
        assert "HTTP 410" in err["error"]

        mock_api.get_synthetic_result_detail_data_without_preload_content.side_effect = Exception("API Error")
        exc = await client.get_synthetic_result_detail_data(
            testid="t1", testresultid="r1", detail_type="LOGS", api_client=mock_api
        )
        assert "Failed to get synthetic result detail data" in exc["error"]

    # ------------------------------------------------------------------
    # _normalize_tag_filter_key
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # execute_playback_operation dispatcher
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_fn,sdk_kwarg,payload", _PAYLOAD_PARAMS)
    async def test_execute_playback_operation_payload_operations(
        self, instana_credentials, method, sdk_fn, sdk_kwarg, payload
    ):
        module = _load_module()
        client = module.SyntheticTestPlaybackResultsMCPTools(
            read_token=instana_credentials["api_token"], base_url=instana_credentials["base_url"]
        )
        mock_api = MagicMock()
        getattr(mock_api, sdk_fn).return_value = _MockResponse({"ok": True})

        # Inject the mock api_client by wrapping the bound method the dispatcher calls
        original = getattr(module.SyntheticTestPlaybackResultsMCPTools, method)

        async def _with_mock(self, *args, **kwargs):
            kwargs["api_client"] = mock_api
            return await original(self, *args, **kwargs)

        with patch.object(module.SyntheticTestPlaybackResultsMCPTools, method, _with_mock):
            result = await client.execute_playback_operation(
                method, {"payload": payload}, resource_type="test_playback", tool_name="manage_synthetics"
            )

        assert result == {"ok": True}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_playback_operation_metadata_and_detail(self, instana_credentials):
        module = _load_module()
        client = module.SyntheticTestPlaybackResultsMCPTools(
            read_token=instana_credentials["api_token"], base_url=instana_credentials["base_url"]
        )
        calls = []

        async def _fake_meta(**kwargs):
            calls.append(("meta", kwargs))
            return {"meta": True}

        async def _fake_detail(**kwargs):
            calls.append(("detail", kwargs))
            return {"detail": True}

        with patch.object(client, "get_synthetic_result_metadata", _fake_meta), \
                patch.object(client, "get_synthetic_result_detail_data", _fake_detail):
            meta = await client.execute_playback_operation(
                "get_synthetic_result_metadata", {"testid": "t1", "testresultid": "r1", "start_time": 9}
            )
            detail = await client.execute_playback_operation(
                "get_synthetic_result_detail_data",
                {"testid": "t1", "testresultid": "r1", "detail_type": "HAR", "name": "n"},
            )
            # "type" is accepted as an alias for detail_type
            detail_alias = await client.execute_playback_operation(
                "get_synthetic_result_detail_data", {"testid": "t1", "testresultid": "r1", "type": "LOGS"}
            )

        assert meta == {"meta": True}
        assert detail == {"detail": True}
        assert detail_alias == {"detail": True}
        assert calls[0][1]["start_time"] == 9
        assert calls[1][1]["detail_type"] == "HAR"
        assert calls[2][1]["detail_type"] == "LOGS"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_playback_operation_unsupported(self, instana_credentials):
        client = create_synthetic_playback_client(instana_credentials)

        result = await client.execute_playback_operation("does_not_exist")

        assert result == {"error": "Operation 'does_not_exist' not supported for test_playback"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_playback_operation_exception(self, instana_credentials):
        client = create_synthetic_playback_client(instana_credentials)

        async def _boom(**kwargs):
            raise RuntimeError("kaboom")

        with patch.object(client, "get_synthetic_result", _boom):
            result = await client.execute_playback_operation("get_synthetic_result", None)

        assert "Error executing 'get_synthetic_result'" in result["error"]
        assert "kaboom" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_synthetic_playback_client(instana_credentials)

        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]
