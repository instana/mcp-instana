"""
E2E tests for SLO Report MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_slo_report_client(instana_credentials):
    """Dynamically import and create SLO Report client"""
    module = importlib.import_module("src.slo.slo_report")
    module = importlib.reload(module)
    return module.SLOReportMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload).encode("utf-8")
        self.data = payload
        self.status = status
        self.headers = {"Content-Type": "application/json"}


def _api_returning(payload, status=200):
    mock_api = MagicMock()
    mock_api.get_slo_without_preload_content.return_value = _MockResponse(payload, status)
    return mock_api


SAMPLE_REPORT = {
    "sli": 0.98,
    "slo": 0.95,
    "fromTimestamp": 1700000000000,
    "toTimestamp": 1700003600000,
    "errorBudgetRemaining": 0.02,
    "errorBudgetSpent": 0.01,
    "totalErrorBudget": 0.05,
    "errorBurnRate": 1.5,
    "extra": "dropped",
}


class TestSLOReportE2E:
    """End-to-end tests for SLO Report MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_slo_report_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_dict_response(self, instana_credentials):
        mock_api = _api_returning(SAMPLE_REPORT)
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(
            slo_id="slo-1", var_from="1700000000000", to="1700003600000",
            exclude_correction_id=["c1"], include_correction_id=["c2"],
            api_client=mock_api,
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["status_code"] == 200
        assert result["reports"][0]["sli"] == 0.98
        assert "extra" not in result["reports"][0]
        mock_api.get_slo_without_preload_content.assert_called_once_with(
            slo_id="slo-1", var_from="1700000000000", to="1700003600000",
            exclude_correction_id=["c1"], include_correction_id=["c2"],
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_list_response_with_charts(self, instana_credentials):
        report = dict(SAMPLE_REPORT)
        report.update({
            "errorChart": [1],
            "errorBudgetRemainChart": [2],
            "errorBurnRateChart": [3],
            "violationDistribution": [4],
            "errorAccumulationChart": [5],
        })
        mock_api = _api_returning([report, SAMPLE_REPORT])
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(slo_id="slo-1", api_client=mock_api)

        assert result["success"] is True
        assert result["count"] == 2
        first = result["reports"][0]
        assert first["errorChart"] == [1]
        assert first["errorBudgetRemainChart"] == [2]
        assert first["errorBurnRateChart"] == [3]
        assert first["violationDistribution"] == [4]
        assert first["errorAccumulationChart"] == [5]
        assert "errorChart" not in result["reports"][1]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_empty_list(self, instana_credentials):
        mock_api = _api_returning([])
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(slo_id="slo-1", api_client=mock_api)

        assert result["success"] is True
        assert result["reports"] == []
        assert result["count"] == 0
        assert "No reports found" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_unexpected_format(self, instana_credentials):
        mock_api = _api_returning({"foo": "bar"})
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(slo_id="slo-1", api_client=mock_api)

        assert result["success"] is True
        assert result["count"] == 0
        assert "Unexpected response format" in result["message"]
        assert result["raw_data"] == {"foo": "bar"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_missing_slo_id(self, instana_credentials):
        mock_api = MagicMock()
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(slo_id="", api_client=mock_api)

        assert result == {"error": "slo_id is required"}
        mock_api.get_slo_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_api_error_status(self, instana_credentials):
        mock_api = _api_returning(b"not found", status=404)
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(slo_id="slo-1", api_client=mock_api)

        assert result["status_code"] == 404
        assert "API error (status 404)" in result["error"]
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_api_error_status_without_body(self, instana_credentials):
        mock_api = _api_returning(b"", status=500)
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(slo_id="slo-1", api_client=mock_api)

        assert result["status_code"] == 500
        assert "No error details provided" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_empty_body(self, instana_credentials):
        mock_api = _api_returning(b"   ")
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(slo_id="slo-1", api_client=mock_api)

        assert result["error"] == "Empty response from API"
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_invalid_json(self, instana_credentials):
        mock_api = _api_returning(b"{not json")
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(slo_id="slo-1", api_client=mock_api)

        assert "Failed to parse JSON response" in result["error"]
        assert result["raw_response"] == "{not json"
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_sdk_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_slo_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_report_client(instana_credentials)

        result = await client.get_slo_report(slo_id="slo-1", api_client=mock_api)

        assert "Failed to get SLO report" in result["error"]
        assert "Boom" in result["error"]
