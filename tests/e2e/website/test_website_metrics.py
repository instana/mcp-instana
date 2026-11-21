"""
Mocked E2E tests for Website Metrics MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_website_metrics_client(instana_credentials):
    """Dynamically import and create Website Metrics client"""
    module = importlib.import_module("src.website.website_metrics")
    module = importlib.reload(module)
    return module.WebsiteMetricsMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _ToDict:
    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return self._data


def _valid_payload():
    return {
        "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
        "type": "PAGELOAD",
        "tagFilterExpression": {
            "type": "TAG_FILTER",
            "name": "beacon.website.name",
            "operator": "EQUALS",
            "entity": "NOT_APPLICABLE",
            "value": "robot-shop",
        },
        "timeFrame": {"windowSize": 3600000},
    }


class TestWebsiteMetricsE2E:
    """Mocked end-to-end tests for Website Metrics MCP Tools"""

    # ---------------- get_website_page_load ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_load_list_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_page_load.return_value = [_ToDict({"a": 1}), {"b": 2}]
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_page_load(
            page_id="p1", timestamp=1700000000000, api_client=mock_api
        )

        assert result == [{"a": 1}, {"b": 2}]
        mock_api.get_page_load.assert_called_once_with(id="p1", timestamp=1700000000000)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_load_single_to_dict_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_page_load.return_value = _ToDict({"x": "y"})
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_page_load(
            page_id="p1", timestamp=1, api_client=mock_api
        )

        assert result == [{"x": "y"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_load_other_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_page_load.return_value = {"raw": True}
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_page_load(
            page_id="p1", timestamp=1, api_client=mock_api
        )

        assert result == {"raw": True}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_load_missing_page_id(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_page_load(
            page_id="", timestamp=1, api_client=mock_api
        )

        assert result == [{"error": "page_id parameter is required"}]
        mock_api.get_page_load.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_load_missing_timestamp(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_page_load(
            page_id="p1", timestamp=0, api_client=mock_api
        )

        assert result == [{"error": "timestamp parameter is required"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_load_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_page_load.side_effect = Exception("boom")
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_page_load(
            page_id="p1", timestamp=1, api_client=mock_api
        )

        assert len(result) == 1
        assert "Failed to get website page load" in result[0]["error"]
        assert "boom" in result[0]["error"]

    # ---------------- get_website_beacon_metrics_v2 ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_dict_payload_to_dict_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacon_metrics_v2.return_value = _ToDict({"items": [1, 2]})
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_beacon_metrics_v2(
            payload=_valid_payload(), api_client=mock_api
        )

        assert result == {"items": [1, 2]}
        kwargs = mock_api.get_beacon_metrics_v2.call_args.kwargs
        config = kwargs["get_website_metrics_v2"]
        assert config.type == "PAGELOAD"
        assert config.metrics[0].metric == "beaconCount"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_json_string_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacon_metrics_v2.return_value = {"items": []}
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_beacon_metrics_v2(
            payload=json.dumps(_valid_payload()), api_client=mock_api
        )

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_single_quote_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacon_metrics_v2.return_value = {"ok": 1}
        client = create_website_metrics_client(instana_credentials)
        payload = "{'metrics': [{'metric': 'beaconCount', 'aggregation': 'SUM'}], 'type': 'PAGELOAD'}"

        result = await client.get_website_beacon_metrics_v2(payload=payload, api_client=mock_api)

        assert result == {"ok": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_python_literal_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacon_metrics_v2.return_value = {"ok": 2}
        client = create_website_metrics_client(instana_credentials)
        # Contains a single quote inside a value, so the quote-replacement JSON attempt fails
        # and the payload is parsed as a Python literal.
        payload = (
            "{'metrics': [{'metric': 'beaconCount', 'aggregation': 'SUM'}], "
            "'type': 'PAGELOAD', 'tagFilterExpression': None, 'note': \"it's\"}"
        )

        result = await client.get_website_beacon_metrics_v2(payload=payload, api_client=mock_api)

        assert result == {"ok": 2}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_invalid_string_payload(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_beacon_metrics_v2(
            payload="this is {not valid", api_client=mock_api
        )

        assert "Invalid payload format" in result["error"]
        assert result["payload"] == "this is {not valid"
        mock_api.get_beacon_metrics_v2.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_snake_case_optional_fields(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacon_metrics_v2.return_value = {"ok": 3}
        client = create_website_metrics_client(instana_credentials)
        payload = {
            "metrics": [{"metric": "beaconCount", "aggregation": "SUM"}],
            "type": "PAGELOAD",
            "tag_filter_expression": {
                "type": "TAG_FILTER",
                "name": "beacon.website.name",
                "operator": "EQUALS",
                "entity": "NOT_APPLICABLE",
                "value": "x",
            },
            "time_frame": {"windowSize": 1000},
        }

        result = await client.get_website_beacon_metrics_v2(payload=payload, api_client=mock_api)

        assert result == {"ok": 3}
        config = mock_api.get_beacon_metrics_v2.call_args.kwargs["get_website_metrics_v2"]
        assert config.time_frame.window_size == 1000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_missing_metrics(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_beacon_metrics_v2(
            payload={"type": "PAGELOAD"}, api_client=mock_api
        )

        assert result == {"error": "Required field 'metrics' is missing from payload"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_missing_type(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_beacon_metrics_v2(
            payload={"metrics": [{"metric": "beaconCount", "aggregation": "SUM"}]},
            api_client=mock_api,
        )

        assert result == {"error": "Required field 'type' is missing from payload"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_none_payload(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_beacon_metrics_v2(payload=None, api_client=mock_api)

        assert "Failed to get website beacon metrics" in result["error"]
        mock_api.get_beacon_metrics_v2.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_invalid_model(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_metrics_client(instana_credentials)
        payload = {"metrics": "not-a-list", "type": "PAGELOAD"}

        result = await client.get_website_beacon_metrics_v2(payload=payload, api_client=mock_api)

        assert "Failed to get website beacon metrics" in result["error"]
        mock_api.get_beacon_metrics_v2.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_empty_result_default(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacon_metrics_v2.return_value = None
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_beacon_metrics_v2(
            payload=_valid_payload(), api_client=mock_api
        )

        assert result == {"success": True, "message": "Get website beacon metrics"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_metrics_v2_api_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacon_metrics_v2.side_effect = Exception("API Error")
        client = create_website_metrics_client(instana_credentials)

        result = await client.get_website_beacon_metrics_v2(
            payload=_valid_payload(), api_client=mock_api
        )

        assert "Failed to get website beacon metrics" in result["error"]
        assert "API Error" in result["error"]
