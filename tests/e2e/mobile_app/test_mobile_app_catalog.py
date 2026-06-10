"""
E2E tests for Mobile App Catalog MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def create_mobile_app_catalog_client(instana_credentials):
    """Dynamically import and create Mobile App Catalog client"""
    module = importlib.import_module("src.mobile_app.mobile_app_catalog")
    module = importlib.reload(module)
    mobile_app_catalog_mcp_tools = module.MobileAppCatalogMCPTools
    return mobile_app_catalog_mcp_tools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"]
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


class TestMobileAppCatalogE2E:
    """End-to-end tests for Mobile App Catalog MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_tag_catalog_mocked_success(self, instana_credentials):
        payload = {
            "tagTree": {
                "tagName": "mobileBeacon.root",
                "children": [{"tagName": "mobileBeacon.mobileApp.name"}],
            },
            "tags": [{"name": "mobileBeacon.view.name"}],
        }
        mock_api = MagicMock()
        mock_api.get_mobile_app_tag_catalog_without_preload_content.return_value = _MockResponse(
            json.dumps(payload).encode("utf-8")
        )

        client = create_mobile_app_catalog_client(instana_credentials)

        result = await client.get_mobile_app_tag_catalog(
            beacon_type="SESSION_START",
            use_case="GROUPING",
            api_client=mock_api,
        )

        assert isinstance(result, dict)
        assert "tag_names" in result
        assert result["count"] == len(result["tag_names"])
        assert "mobileBeacon.view.name" in result["tag_names"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_metric_catalog_mocked_success(self, instana_credentials):
        payload = [{"metricId": "metric.a"}, {"metricId": "metric.b"}, {"name": "ignore"}]
        mock_api = MagicMock()
        mock_api.get_mobile_app_metric_catalog_without_preload_content.return_value = _MockResponse(
            json.dumps(payload).encode("utf-8")
        )

        client = create_mobile_app_catalog_client(instana_credentials)

        result = await client.get_mobile_app_metric_catalog(api_client=mock_api)

        assert isinstance(result, dict)
        assert "metrics" in result
        assert len(result["metrics"]) == 3
        assert result["metrics"][0]["metricId"] == "metric.a"
        assert result["metrics"][1]["metricId"] == "metric.b"
        assert result["count"] == 2
        assert "description" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_tag_catalog_error_handling(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_tag_catalog_without_preload_content.side_effect = Exception("API Error")

        client = create_mobile_app_catalog_client(instana_credentials)

        result = await client.get_mobile_app_tag_catalog(
            beacon_type="SESSION_START",
            use_case="GROUPING",
            api_client=mock_api,
        )

        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to get mobile app tag catalog" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_catalog_initialization_error(self, instana_credentials):
        with patch(
            "src.mobile_app.mobile_app_catalog.MobileAppCatalogApi",
            side_effect=Exception("Initialization Error"),
        ):
            client = create_mobile_app_catalog_client(instana_credentials)
            assert client is not None
