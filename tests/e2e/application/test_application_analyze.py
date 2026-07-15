"""
E2E tests for Application Analyze MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


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
