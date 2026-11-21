"""
Mocked E2E tests for Synthetic Metrics MCP Tools (no real Instana API required)
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def _load_module():
    module = importlib.import_module("src.synthetic.synthetic_metrics")
    return importlib.reload(module)


def create_synthetic_metrics_client(instana_credentials):
    """Dynamically import and create Synthetic Metrics client"""
    module = _load_module()
    return module.SyntheticMetricsMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


VALID_PAYLOAD = {
    "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}],
    "timeFrame": {"windowSize": 3600000},
    "pagination": {"page": 1, "pageSize": 3},
}


class TestSyntheticMetricsE2E:
    """End-to-end (mocked) tests for Synthetic Metrics MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_success_dict_payload(self, instana_credentials):
        expected = {"items": [{"metrics": {"synthetic.metricsResponseTime.sum": [[0, 10]]}}]}
        mock_api = MagicMock()
        mock_api.get_metrics_result_without_preload_content.return_value = _MockResponse(
            json.dumps(expected).encode("utf-8")
        )
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(payload=VALID_PAYLOAD, api_client=mock_api)

        assert result == expected
        kwargs = mock_api.get_metrics_result_without_preload_content.call_args.kwargs
        assert kwargs["get_metrics_result"].metrics[0].metric == "synthetic.metricsResponseTime"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_success_json_string_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_metrics_result_without_preload_content.return_value = _MockResponse(b'{"items": []}')
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(payload=json.dumps(VALID_PAYLOAD), api_client=mock_api)

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_with_groups_and_tag_filter(self, instana_credentials):
        payload = {
            **VALID_PAYLOAD,
            "groups": [{"groupbyTag": "synthetic.applicationId", "groupbyTagEntity": "NOT_APPLICABLE", "direction": "DESC"}],
            "tagFilterExpression": {
                "type": "TAG_FILTER",
                "name": "synthetic.locationId",
                "operator": "EQUALS",
                "entity": "NOT_APPLICABLE",
                "stringValue": "loc1",
            },
        }
        mock_api = MagicMock()
        mock_api.get_metrics_result_without_preload_content.return_value = _MockResponse(b'{"items": []}')
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(payload=payload, api_client=mock_api)

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_missing_payload(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(payload=None, api_client=mock_api)

        assert result == {"error": "payload is required"}
        mock_api.get_metrics_result_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_unparseable_payload(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(payload="{{not valid", api_client=mock_api)

        assert "error" in result
        mock_api.get_metrics_result_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_empty_object_payload(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(payload="{}", api_client=mock_api)

        assert result == {"error": "payload must not be an empty object"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_validation_missing_metrics(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(
            payload={"timeFrame": {"windowSize": 3600000}}, api_client=mock_api
        )

        assert result["elicitation_needed"] is True
        assert result["api_error"]
        mock_api.get_metrics_result_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_validation_granularity_ratio(self, instana_credentials):
        payload = {
            "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM", "granularity": 1}],
            "timeFrame": {"windowSize": 2592000000},
        }
        mock_api = MagicMock()
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(payload=payload, api_client=mock_api)

        assert result["elicitation_needed"] is True
        mock_api.get_metrics_result_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_build_object_failure(self, instana_credentials):
        module = _load_module()
        client = module.SyntheticMetricsMCPTools(
            read_token=instana_credentials["api_token"], base_url=instana_credentials["base_url"]
        )
        mock_api = MagicMock()

        with patch.object(module.GetMetricsResult, "from_dict", side_effect=ValueError("bad shape")):
            result = await client.get_metrics_result(payload=VALID_PAYLOAD, api_client=mock_api)

        assert "Failed to build GetMetricsResult" in result["error"]
        assert "bad shape" in result["error"]
        mock_api.get_metrics_result_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_metrics_result_without_preload_content.return_value = _MockResponse(b"oops", status=500)
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(payload=VALID_PAYLOAD, api_client=mock_api)

        assert "HTTP 500" in result["error"]
        assert result["status_code"] == 500
        assert result["details"] == "oops"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_metrics_result_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_metrics_result_without_preload_content.side_effect = Exception("API Error")
        client = create_synthetic_metrics_client(instana_credentials)

        result = await client.get_metrics_result(payload=VALID_PAYLOAD, api_client=mock_api)

        assert "Failed to get synthetic metrics" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_synthetic_metrics_client(instana_credentials)

        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]
