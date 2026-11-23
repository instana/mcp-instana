"""
Mocked E2E tests for Website Catalog MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_website_catalog_client(instana_credentials):
    """Dynamically import and create Website Catalog client"""
    module = importlib.import_module("src.website.website_catalog")
    module = importlib.reload(module)
    return module.WebsiteCatalogMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


class _ToDictItem:
    def __init__(self, value):
        self._value = value

    def to_dict(self):
        return {"name": self._value}


class TestWebsiteCatalogE2E:
    """Mocked end-to-end tests for Website Catalog MCP Tools"""

    def setup_method(self):
        from src.core.catalog_cache import clear_cache
        clear_cache()

    # ---------------- get_website_catalog_metrics ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_metrics_planner_view(self, instana_credentials):
        payload = [
            {"metricId": "beaconCount", "label": "Count", "description": "d",
             "aggregations": ["SUM"], "beaconTypes": ["PAGELOAD"], "formatter": "NUMBER",
             "pathToValueInBeacon": "internal"},
            {"label": "no id"},
        ]
        mock_api = MagicMock()
        mock_api.get_website_catalog_metrics_without_preload_content.return_value = _MockResponse(
            json.dumps(payload).encode("utf-8")
        )
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_metrics(api_client=mock_api)

        assert result["count"] == 1
        assert len(result["metrics"]) == 2
        card = result["metrics"][0]
        assert card["metricId"] == "beaconCount"
        assert "pathToValueInBeacon" not in card
        assert "query planning" in result["description"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_metrics_full_view(self, instana_credentials):
        payload = [{"metricId": "m1", "pathToValueInBeacon": "x"}]
        mock_api = MagicMock()
        mock_api.get_website_catalog_metrics_without_preload_content.return_value = _MockResponse(
            json.dumps(payload).encode("utf-8")
        )
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_metrics(api_client=mock_api, view="full")

        assert result["metrics"] == payload
        assert result["count"] == 1
        assert "full metadata" in result["description"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_metrics_invalid_view(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_metrics(api_client=mock_api, view="bogus")

        assert "Invalid view" in result["error"]
        assert result["valid_views"] == ["planner", "full"]
        mock_api.get_website_catalog_metrics_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_metrics_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_catalog_metrics_without_preload_content.return_value = _MockResponse(
            b"forbidden", status=403, headers={"Content-Type": "text/plain"}
        )
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_metrics(api_client=mock_api)

        assert "HTTP 403" in result["error"]
        assert result["status_code"] == 403
        assert result["details"] == "forbidden"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_metrics_http_error_decode_failure(self, instana_credentials, monkeypatch):
        mock_api = MagicMock()
        mock_api.get_website_catalog_metrics_without_preload_content.return_value = _MockResponse(
            b"boom", status=500
        )
        client = create_website_catalog_client(instana_credentials)
        module = importlib.import_module("src.website.website_catalog")

        def _raise(_response):
            raise ValueError("cannot decode")

        monkeypatch.setattr(module, "decode_response", _raise)

        result = await client.get_website_catalog_metrics(api_client=mock_api)

        assert result == {"error": "Failed to get website catalog metrics: HTTP 500", "status_code": 500}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_metrics_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_catalog_metrics_without_preload_content.side_effect = Exception("API Error")
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_metrics(api_client=mock_api)

        assert "Failed to get website catalog metrics" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_metrics_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_catalog_metrics_without_preload_content.return_value = _MockResponse(
            b"not json"
        )
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_metrics(api_client=mock_api)

        assert "Failed to get website catalog metrics" in result["error"]

    # ---------------- get_website_catalog_tags ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tags_list_with_to_dict_and_plain(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_catalog_tags.return_value = [_ToDictItem("a"), {"name": "b"}]
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_tags(api_client=mock_api)

        assert result == {"tags": [{"name": "a"}, {"name": "b"}], "count": 2}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tags_single_to_dict_object(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_catalog_tags.return_value = _ToDictItem("solo")
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_tags(api_client=mock_api)

        assert result == {"tags": [{"name": "solo"}], "count": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tags_non_list_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_catalog_tags.return_value = {"raw": "value"}
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_tags(api_client=mock_api)

        assert result == {"data": {"raw": "value"}}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tags_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_catalog_tags.side_effect = Exception("tags down")
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_catalog_tags(api_client=mock_api)

        assert "Failed to get website catalog tags" in result["error"]
        assert "tags down" in result["error"]

    # ---------------- get_website_tag_catalog ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_success(self, instana_credentials):
        payload = {
            "tagTree": {
                "tagName": "beacon.root",
                "children": [{"tagName": "beacon.page.name"}],
            },
            "tags": [{"name": "beacon.website.name"}, {"name": ""}, "junk"],
        }
        mock_api = MagicMock()
        mock_api.get_website_tag_catalog_without_preload_content.return_value = _MockResponse(
            json.dumps(payload).encode("utf-8")
        )
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_tag_catalog(
            beacon_type="PAGELOAD", use_case="GROUPING", api_client=mock_api
        )

        assert result["beacon_type"] == "PAGELOAD"
        assert result["use_case"] == "GROUPING"
        assert "beacon.website.name" in result["tag_names"]
        assert result["count"] == len(result["tag_names"])
        mock_api.get_website_tag_catalog_without_preload_content.assert_called_once_with(
            beacon_type="PAGELOAD", use_case="GROUPING"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_missing_beacon_type(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_tag_catalog(
            beacon_type="", use_case="GROUPING", api_client=mock_api
        )

        assert result == {"error": "beacon_type parameter is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_missing_use_case(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_tag_catalog(
            beacon_type="PAGELOAD", use_case="", api_client=mock_api
        )

        assert result == {"error": "use_case parameter is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_tag_catalog_without_preload_content.return_value = _MockResponse(
            b"bad request", status=400, headers={"Content-Type": "text/plain"}
        )
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_tag_catalog(
            beacon_type="PAGELOAD", use_case="FILTERING", api_client=mock_api
        )

        assert "HTTP 400" in result["error"]
        assert result["status_code"] == 400
        assert result["details"] == "bad request"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_http_error_decode_failure(self, instana_credentials, monkeypatch):
        mock_api = MagicMock()
        mock_api.get_website_tag_catalog_without_preload_content.return_value = _MockResponse(
            b"x", status=502
        )
        client = create_website_catalog_client(instana_credentials)
        module = importlib.import_module("src.website.website_catalog")

        def _raise(_response):
            raise ValueError("cannot decode")

        monkeypatch.setattr(module, "decode_response", _raise)

        result = await client.get_website_tag_catalog(
            beacon_type="ERROR", use_case="GROUPING", api_client=mock_api
        )

        assert result == {"error": "Failed to get website tag catalog: HTTP 502", "status_code": 502}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_tag_catalog_without_preload_content.side_effect = Exception("API Error")
        client = create_website_catalog_client(instana_credentials)

        result = await client.get_website_tag_catalog(
            beacon_type="PAGELOAD", use_case="GROUPING", api_client=mock_api
        )

        assert "Failed to get website tag catalog" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_initialization(self, instana_credentials):
        client = create_website_catalog_client(instana_credentials)
        assert client is not None
