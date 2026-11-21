"""
E2E tests for Application Catalog MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_application_catalog_client(instana_credentials):
    """Dynamically import and create Application Catalog client"""
    module = importlib.import_module("src.application.application_catalog")
    module = importlib.reload(module)
    return module.ApplicationCatalogMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


def _tag_api(payload):
    mock_api = MagicMock()
    mock_api.get_application_tag_catalog_without_preload_content.return_value = _MockResponse(
        json.dumps(payload).encode("utf-8")
    )
    return mock_api


class TestApplicationCatalogE2E:
    """End-to-end tests for Application Catalog MCP Tools"""

    def setup_method(self):
        from src.core.catalog_cache import clear_cache
        clear_cache()

    def teardown_method(self):
        from src.core.catalog_cache import clear_cache
        clear_cache()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_application_catalog_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ------------------------------------------------------------------
    # get_application_tag_catalog
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_dict_trims_tag_tree(self, instana_credentials):
        payload = {
            "tagTree": [
                {"label": f"level{i}", "children": [{"tagName": f"t{i}{j}"} for j in range(5)]}
                for i in range(5)
            ],
            "tags": [{"name": "service.name"}],
        }
        mock_api = _tag_api(payload)
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", var_from=1700000000000, api_client=mock_api
        )

        assert len(result["tagTree"]) == 3
        assert all(len(level["children"]) == 3 for level in result["tagTree"])
        assert result["tags"] == [{"name": "service.name"}]
        call_kwargs = mock_api.get_application_tag_catalog_without_preload_content.call_args.kwargs
        assert call_kwargs == {
            "use_case": "GROUPING",
            "data_source": "CALLS",
            "var_from": 1700000000000,
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_defaults_var_from(self, instana_credentials):
        mock_api = _tag_api({"tags": []})
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_tag_catalog(
            use_case="FILTERING", data_source="CALLS", api_client=mock_api
        )

        assert result == {"tags": []}
        call_kwargs = mock_api.get_application_tag_catalog_without_preload_content.call_args.kwargs
        assert isinstance(call_kwargs["var_from"], int)
        assert call_kwargs["var_from"] > 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_tag_tree_non_list_is_kept(self, instana_credentials):
        mock_api = _tag_api({"tagTree": {"tagName": "root"}})
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", api_client=mock_api
        )

        assert result == {"tagTree": {"tagName": "root"}}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_list_response_is_wrapped(self, instana_credentials):
        payload = [
            {"tagTree": [{"children": [1, 2, 3, 4]}, {"label": "no-children"}]},
            "skipped-non-dict",
        ]
        mock_api = _tag_api(payload)
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", api_client=mock_api
        )

        assert list(result) == ["tags"]
        assert len(result["tags"]) == 1
        assert result["tags"][0]["tagTree"][0]["children"] == [1, 2, 3]
        assert result["tags"][0]["tagTree"][1] == {"label": "no-children"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_double_encoded_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_tag_catalog_without_preload_content.return_value = _MockResponse(
            json.dumps(json.dumps({"tags": ["a"]})).encode("utf-8")
        )
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", api_client=mock_api
        )

        assert result == {"tags": ["a"]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_unexpected_format(self, instana_credentials):
        mock_api = _tag_api(42)
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", api_client=mock_api
        )

        assert result == {"error": "Unexpected response format from API"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_tag_catalog_without_preload_content.return_value = _MockResponse(
            b"not-json"
        )
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", api_client=mock_api
        )

        assert "Failed to get application catalog" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_tag_catalog_without_preload_content.side_effect = Exception("API Error")
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", api_client=mock_api
        )

        assert "Failed to get application catalog" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_catalog_success_is_cached_and_errors_are_not(self, instana_credentials):
        client = create_application_catalog_client(instana_credentials)

        failing_api = MagicMock()
        failing_api.get_application_tag_catalog_without_preload_content.side_effect = Exception("boom")
        first = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", api_client=failing_api
        )
        assert "error" in first

        ok_api = _tag_api({"tags": ["x"]})
        second = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", api_client=ok_api
        )
        assert second == {"tags": ["x"]}

        other_api = _tag_api({"tags": ["y"]})
        third = await client.get_application_tag_catalog(
            use_case="GROUPING", data_source="CALLS", api_client=other_api
        )
        assert third == {"tags": ["x"]}
        other_api.get_application_tag_catalog_without_preload_content.assert_not_called()

    # ------------------------------------------------------------------
    # get_application_metric_catalog
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metric_catalog_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_catalog_metrics.return_value = [{"metricId": "calls"}]
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_metric_catalog(api_client=mock_api)

        assert result == {"metrics": [{"metricId": "calls"}]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metric_catalog_dict_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_catalog_metrics.return_value = {"metrics": ["a"]}
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_metric_catalog(api_client=mock_api)

        assert result == {"metrics": ["a"]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metric_catalog_to_dict_response(self, instana_credentials):
        response = MagicMock()
        response.to_dict.return_value = {"metrics": ["from_to_dict"]}
        mock_api = MagicMock()
        mock_api.get_application_catalog_metrics.return_value = response
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_metric_catalog(api_client=mock_api)

        assert result == {"metrics": ["from_to_dict"]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metric_catalog_object_with_dict_attrs(self, instana_credentials):
        class Described:
            def __init__(self):
                self.metric_id = "calls"

        mock_api = MagicMock()
        mock_api.get_application_catalog_metrics.return_value = Described()
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_metric_catalog(api_client=mock_api)

        assert result == {"metrics": [{"metric_id": "calls"}]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metric_catalog_scalar_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_catalog_metrics.return_value = 7
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_metric_catalog(api_client=mock_api)

        assert result == {"metrics": ["7"]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metric_catalog_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_catalog_metrics.side_effect = Exception("API Error")
        client = create_application_catalog_client(instana_credentials)

        result = await client.get_application_metric_catalog(api_client=mock_api)

        assert "Failed to get application metric catalog" in result["error"]
        assert "API Error" in result["error"]
