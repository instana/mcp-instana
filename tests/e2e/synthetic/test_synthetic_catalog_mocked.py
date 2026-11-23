"""
Mocked E2E tests for Synthetic Catalog MCP Tools (no real Instana API required)
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_synthetic_catalog_client(instana_credentials):
    """Dynamically import and create Synthetic Catalog client"""
    module = importlib.import_module("src.synthetic.synthetic_catalog")
    module = importlib.reload(module)
    return module.SyntheticCatalogMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


METRICS_PAYLOAD = [
    {
        "metricId": "synthetic.metricsResponseTime",
        "label": "Response Time",
        "description": "desc",
        "aggregations": ["MEAN", "SUM"],
        "beaconTypes": ["synthetic"],
        "formatter": "MILLIS",
        "pathToValueInBeacon": "internal",
        "tagName": "internal",
    },
    {"metricId": "synthetic.errors", "label": "Errors"},
    {"label": "no id"},
]


class TestSyntheticCatalogE2E:
    """End-to-end (mocked) tests for Synthetic Catalog MCP Tools"""

    def setup_method(self):
        from src.core.catalog_cache import clear_cache
        clear_cache()

    # ------------------------------------------------------------------
    # get_synthetic_catalog_metrics
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_catalog_metrics_planner_view(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_catalog_metrics_without_preload_content.return_value = _MockResponse(
            json.dumps(METRICS_PAYLOAD).encode("utf-8")
        )
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_catalog_metrics(api_client=mock_api)

        assert result["count"] == 2
        assert len(result["metrics"]) == 3
        first = result["metrics"][0]
        assert first["metricId"] == "synthetic.metricsResponseTime"
        assert first["aggregations"] == ["MEAN", "SUM"]
        assert "pathToValueInBeacon" not in first
        assert "tagName" not in first
        assert result["metrics"][1]["aggregations"] == []
        assert "query planning" in result["description"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_catalog_metrics_full_view(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_catalog_metrics_without_preload_content.return_value = _MockResponse(
            json.dumps(METRICS_PAYLOAD).encode("utf-8")
        )
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_catalog_metrics(view="full", api_client=mock_api)

        assert result["metrics"] == METRICS_PAYLOAD
        assert result["count"] == 2
        assert "full metadata" in result["description"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_catalog_metrics_invalid_view(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_catalog_metrics(view="bogus", api_client=mock_api)

        assert "Invalid view 'bogus'" in result["error"]
        assert result["valid_views"] == ["planner", "full"]
        mock_api.get_synthetic_catalog_metrics_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_catalog_metrics_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_catalog_metrics_without_preload_content.return_value = _MockResponse(
            b"server down", status=503
        )
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_catalog_metrics(api_client=mock_api)

        assert "HTTP 503" in result["error"]
        assert result["status_code"] == 503
        assert result["details"] == "server down"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_catalog_metrics_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_catalog_metrics_without_preload_content.side_effect = Exception("API Error")
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_catalog_metrics(api_client=mock_api)

        assert "Failed to get synthetic catalog metrics" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_catalog_metrics_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_catalog_metrics_without_preload_content.return_value = _MockResponse(b"not-json")
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_catalog_metrics(api_client=mock_api)

        assert "Failed to get synthetic catalog metrics" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_catalog_metrics_result_cached(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_catalog_metrics_without_preload_content.return_value = _MockResponse(
            json.dumps(METRICS_PAYLOAD).encode("utf-8")
        )
        client = create_synthetic_catalog_client(instana_credentials)

        first = await client.get_synthetic_catalog_metrics(api_client=mock_api)
        second = await client.get_synthetic_catalog_metrics(api_client=mock_api)

        assert first == second
        assert mock_api.get_synthetic_catalog_metrics_without_preload_content.call_count == 1

    # ------------------------------------------------------------------
    # get_synthetic_tag_catalog
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_tag_catalog_success(self, instana_credentials):
        payload = {
            "tagTree": {
                "tagName": "synthetic.root",
                "children": [{"tagName": "synthetic.locationId"}],
            },
            "tags": [{"name": "synthetic.testName"}, {"name": "synthetic.locationId"}],
        }
        mock_api = MagicMock()
        mock_api.get_synthetic_tag_catalog_without_preload_content.return_value = _MockResponse(
            json.dumps(payload).encode("utf-8")
        )
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_tag_catalog(use_case="FILTERING", api_client=mock_api)

        assert result["use_case"] == "FILTERING"
        assert result["beacon_type"] is None
        assert result["count"] == len(result["tag_names"])
        assert "synthetic.testName" in result["tag_names"]
        assert "synthetic.locationId" in result["tag_names"]
        assert result["tag_names"] == sorted(set(result["tag_names"]))
        mock_api.get_synthetic_tag_catalog_without_preload_content.assert_called_once_with(use_case="FILTERING")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_tag_catalog_missing_use_case(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_tag_catalog(use_case="", api_client=mock_api)

        assert result == {"error": "use_case parameter is required"}
        mock_api.get_synthetic_tag_catalog_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_tag_catalog_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tag_catalog_without_preload_content.return_value = _MockResponse(
            b"bad request", status=400
        )
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_tag_catalog(use_case="GROUPING", api_client=mock_api)

        assert "HTTP 400" in result["error"]
        assert result["status_code"] == 400

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_tag_catalog_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tag_catalog_without_preload_content.side_effect = Exception("API Error")
        client = create_synthetic_catalog_client(instana_credentials)

        result = await client.get_synthetic_tag_catalog(use_case="SMART_ALERTS", api_client=mock_api)

        assert "Failed to get synthetic tag catalog" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_tag_catalog_cached_per_use_case(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tag_catalog_without_preload_content.return_value = _MockResponse(
            json.dumps({"tags": [{"name": "synthetic.a"}]}).encode("utf-8")
        )
        client = create_synthetic_catalog_client(instana_credentials)

        await client.get_synthetic_tag_catalog(use_case="GROUPING", api_client=mock_api)
        await client.get_synthetic_tag_catalog(use_case="GROUPING", api_client=mock_api)
        await client.get_synthetic_tag_catalog(use_case="FILTERING", api_client=mock_api)

        assert mock_api.get_synthetic_tag_catalog_without_preload_content.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_synthetic_catalog_client(instana_credentials)

        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]
