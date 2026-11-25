"""
Mocked E2E tests for Website Analyze MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def create_website_analyze_client(instana_credentials):
    """Dynamically import and create Website Analyze client"""
    module = importlib.import_module("src.website.website_analyze")
    module = importlib.reload(module)
    return module.WebsiteAnalyzeMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


def _json_response(obj, status=200):
    return _MockResponse(json.dumps(obj).encode("utf-8"), status=status)


def _tag_filter(name="beacon.website.name", value="robot-shop", entity="NOT_APPLICABLE"):
    tag = {"type": "TAG_FILTER", "name": name, "operator": "EQUALS", "value": value}
    if entity is not None:
        tag["entity"] = entity
    return tag


def _group(tag="beacon.page.name"):
    return {"groupbyTag": tag, "groupbyTagEntity": "NOT_APPLICABLE"}


def _metrics():
    return [{"metric": "beaconCount", "aggregation": "SUM"}]


def _group_args(**overrides):
    args = {
        "metrics": _metrics(),
        "group": _group(),
        "beacon_type": "PAGELOAD",
        "time_frame": {"windowSize": 3600000},
    }
    args.update(overrides)
    return args


def _catalog_mock_api(catalog_payload=None, status=200, host="https://test.instana.io"):
    """Mock website analyze api whose underlying ApiClient is usable for catalog prefetch."""
    mock_api = MagicMock()
    mock_api.api_client = MagicMock()
    mock_api.api_client.configuration.host = host
    catalog = catalog_payload
    if catalog is None:
        catalog = [
            {
                "metricId": "beaconCount",
                "label": "Count",
                "aggregations": ["SUM", "MEAN"],
                "beaconTypes": ["pageLoad", "error"],
            }
        ]
    catalog_instance = MagicMock()
    catalog_instance.get_website_catalog_metrics_without_preload_content.return_value = (
        _json_response(catalog, status=status)
    )
    return mock_api, catalog_instance


class TestWebsiteAnalyzeE2E:
    """Mocked end-to-end tests for Website Analyze MCP Tools"""

    def setup_method(self):
        from src.core.catalog_cache import clear_cache
        clear_cache()

    # ---------------- helper functions ----------------

    @pytest.mark.mocked
    def test_clean_nan_values(self):
        module = importlib.import_module("src.website.website_analyze")
        data = {"a": "NaN", "b": ["NaN", 1, {"c": "NaN", "d": "ok"}], "e": 5}

        assert module.clean_nan_values(data) == {"a": None, "b": [None, 1, {"c": None, "d": "ok"}], "e": 5}

    @pytest.mark.mocked
    def test_convert_beacon_tag_filters(self, instana_credentials):
        client = create_website_analyze_client(instana_credentials)

        assert client._convert_beacon_tag_filters(None) == {}
        assert client._convert_beacon_tag_filters({"type": "OTHER"}) == {}
        assert "error" in client._convert_beacon_tag_filters({"type": "TAG_FILTER", "name": "n"})

        single = client._convert_beacon_tag_filters(_tag_filter())
        assert len(single["tagFilters"]) == 1

        no_entity = client._convert_beacon_tag_filters(_tag_filter(entity=None))
        assert len(no_entity["tagFilters"]) == 1

        expression = client._convert_beacon_tag_filters(
            {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": [_tag_filter(), {"type": "EXPRESSION", "elements": []}, _tag_filter(entity=None)],
            }
        )
        assert len(expression["tagFilters"]) == 2

        assert client._convert_beacon_tag_filters(
            {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}
        ) == {}

    @pytest.mark.mocked
    def test_convert_beacon_tag_filters_conversion_error(self, instana_credentials):
        client = create_website_analyze_client(instana_credentials)
        bad = {
            "type": "EXPRESSION",
            "elements": [{"type": "TAG_FILTER", "name": None, "operator": None, "value": None}],
        }

        result = client._convert_beacon_tag_filters(bad)

        assert "Invalid tag filter expression" in result["error"]

    @pytest.mark.mocked
    def test_convert_group_tag_filter_error(self, instana_credentials):
        client = create_website_analyze_client(instana_credentials)

        obj, error = client._convert_group_tag_filter({"type": "TAG_FILTER", "name": 1})

        assert obj is None
        assert "Invalid tag filter expression" in error["error"]

    @pytest.mark.mocked
    def test_build_beacon_groups_query_params_order_pagination_and_error(self, instana_credentials):
        client = create_website_analyze_client(instana_credentials)
        empty_expr = {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}

        params = client._build_beacon_groups_query_params(
            "PAGELOAD", _group(), _metrics(), {"windowSize": 1}, empty_expr,
            {"by": "beaconCount", "direction": "DESC"}, {"retrievalSize": 5},
        )
        assert params["order"] == {"by": "beaconCount", "direction": "DESC"}
        assert params["pagination"] == {"retrievalSize": 5}

        error = client._build_beacon_groups_query_params(
            "PAGELOAD", _group(), _metrics(), {"windowSize": 1}, {"type": "TAG_FILTER", "name": 1},
            None, None,
        )
        assert "error" in error

    # ---------------- _validate_tag_names ----------------

    # ---------------- get_website_beacon_groups ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_success(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        expected = {"items": [{"name": "home", "metrics": {"beaconCount.SUM": [[1, 5]]}}]}
        mock_api.get_beacon_groups_without_preload_content.return_value = _json_response(expected)
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            result = await client.get_website_beacon_groups(
                **_group_args(
                    tag_filter_expression=_tag_filter(),
                    order={"by": "beaconCount.SUM", "direction": "DESC"},
                    pagination={"retrievalSize": 10},
                ),
                api_client=mock_api,
            )

        assert result == expected
        kwargs = mock_api.get_beacon_groups_without_preload_content.call_args.kwargs
        assert kwargs["fill_time_series"] is True
        assert kwargs["get_website_beacon_groups"].type == "PAGELOAD"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_elicitation_when_missing_required(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacon_groups(api_client=mock_api)

        assert result["elicitation_required"] is True
        names = [p["name"] for p in result["missing_parameters"]]
        assert names == ["metrics", "group"]
        mock_api.get_beacon_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_structure_validation_error(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacon_groups(
            **_group_args(time_frame={"windowSize": "not-an-int"}),
            api_client=mock_api,
        )

        assert result["elicitation_needed"] is True
        assert result["api_error"]
        assert "get_website_beacon_groups payload has" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_invalid_tag_names(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacon_groups(
            **_group_args(group=_group("not.beacon.tag")), api_client=mock_api
        )

        assert result["invalid_tags"] == ["not.beacon.tag"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_unknown_beacon_type(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacon_groups(
            **_group_args(beacon_type="NOPE"), api_client=mock_api
        )

        assert result["elicitation_needed"] is True
        assert "Unrecognized beacon_type" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_catalog_unavailable(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.api_client = None
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)

        assert result == {"error": "Cannot access underlying ApiClient for catalog fetch"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_incompatible_metric(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            result = await client.get_website_beacon_groups(
                **_group_args(metrics=[{"metric": "unknownMetric", "aggregation": "SUM"}]),
                api_client=mock_api,
            )

        assert result["elicitation_needed"] is True
        assert "not found in catalog" in result["api_error"][0]
        mock_api.get_beacon_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_invalid_tag_filter_expression(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        client = create_website_analyze_client(instana_credentials)
        # Passes the structure/tag validators but cannot be converted into a TagFilterExpressionElement.
        bad_filter = {
            "type": "TAG_FILTER",
            "name": "beacon.website.name",
            "entity": "NOT_APPLICABLE",
            "operator": "NOT_A_REAL_OPERATOR",
            "value": "x",
        }

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            result = await client.get_website_beacon_groups(
                **_group_args(tag_filter_expression=bad_filter), api_client=mock_api
            )

        assert "error" in result or result.get("elicitation_needed")
        mock_api.get_beacon_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_request_object_creation_error(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ), patch(
            "instana_client.models.get_website_beacon_groups.GetWebsiteBeaconGroups",
            side_effect=ValueError("bad model"),
        ):
            result = await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)

        assert "Failed to create beacon groups request" in result["error"]
        assert "bad model" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_http_error_with_details(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        mock_api.get_beacon_groups_without_preload_content.return_value = _MockResponse(
            b"server exploded", status=500, headers={"Content-Type": "text/plain"}
        )
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            result = await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)

        assert "HTTP 500" in result["error"]
        assert result["status_code"] == 500
        assert result["details"] == "server exploded"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_http_error_metric_type_unknown(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        body = {"errors": ["Metric type unknown: foo"]}
        mock_api.get_beacon_groups_without_preload_content.return_value = _json_response(body, status=400)
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            result = await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "Invalid metric detected" in result["reason"]
        assert result["api_error"] == body["errors"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_http_error_other_json_errors(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        body = {"errors": ["something else", 42]}
        mock_api.get_beacon_groups_without_preload_content.return_value = _json_response(body, status=400)
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            result = await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)

        assert result["status_code"] == 400
        assert json.loads(result["details"]) == body

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_http_error_undecodable(self, instana_credentials, monkeypatch):
        mock_api, catalog_instance = _catalog_mock_api()
        mock_api.get_beacon_groups_without_preload_content.return_value = _MockResponse(b"x", status=502)
        client = create_website_analyze_client(instana_credentials)
        module = importlib.import_module("src.website.website_analyze")

        original = module.decode_response
        calls = {"n": 0}

        def _decode(response):
            # First call is for the catalog prefetch (status 200), later ones belong to the failing response.
            calls["n"] += 1
            if response.status != 200:
                raise ValueError("cannot decode")
            return original(response)

        monkeypatch.setattr(module, "decode_response", _decode)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            result = await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)

        assert result == {"error": "Failed to get website beacon groups: HTTP 502", "status_code": 502}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_nan_custom_metric_error(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        mock_api.get_beacon_groups_without_preload_content.side_effect = Exception(
            "validation error: customMetric got NaN"
        )
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            result = await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)

        assert "NaN values for customMetric" in result["error"]
        assert "customMetric" in result["details"]
        assert "suggestion" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_generic_api_exception(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        mock_api.get_beacon_groups_without_preload_content.side_effect = Exception("API Error")
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            result = await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)

        assert "Failed to get website beacon groups" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacon_groups_catalog_is_cached(self, instana_credentials):
        mock_api, catalog_instance = _catalog_mock_api()
        mock_api.get_beacon_groups_without_preload_content.return_value = _json_response({"items": []})
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.api.website_catalog_api.WebsiteCatalogApi", return_value=catalog_instance
        ):
            await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)
            await client.get_website_beacon_groups(**_group_args(), api_client=mock_api)

        assert catalog_instance.get_website_catalog_metrics_without_preload_content.call_count == 1

    # ---------------- get_website_beacons ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_success_summarized(self, instana_credentials):
        payload = {
            "items": [
                {
                    "beacon": {
                        "websiteLabel": "shop",
                        "timestamp": 1700000000000,
                        "duration": 120,
                        "errorCount": 0,
                        "firstInputDelayTime": 0,
                        "city": "",
                        "country": "NaN",
                        "clockSkew": -1,
                        "stackTrace": [],
                        "locationUrl": "https://shop/",
                        "page": "home",
                        "unknownField": "dropped",
                        "parsedStackTrace": {},
                    }
                },
                {"beacon": "not-a-dict"},
                {"nothing": True},
                "not-a-dict",
            ],
            "totalHits": 4,
            "canLoadMore": True,
            "adjustedTimeframe": {"windowSize": 1},
        }
        mock_api = MagicMock()
        mock_api.get_beacons_without_preload_content.return_value = _json_response(payload)
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacons(
            beacon_type="PAGELOAD",
            tag_filter_expression=_tag_filter(),
            time_frame={"windowSize": 3600000},
            pagination={"retrievalSize": 200},
            api_client=mock_api,
        )

        assert result["summary"]["totalHits"] == 4
        assert result["summary"]["canLoadMore"] is True
        assert result["summary"]["timeframe"] == {"windowSize": 1}
        assert result["beacons"] == [
            {
                "websiteLabel": "shop",
                "timestamp": 1700000000000,
                "duration": 120,
                "locationUrl": "https://shop/",
                "page": "home",
            }
        ]
        config = mock_api.get_beacons_without_preload_content.call_args.kwargs["get_website_beacons"]
        assert config.pagination.retrieval_size == 200
        assert config.pagination.offset == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_expression_filter_and_defaults(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacons_without_preload_content.return_value = _json_response({"items": []})
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacons(
            beacon_type="ERROR",
            tag_filter_expression={
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": [_tag_filter(), _tag_filter(name="beacon.page.name", value="home")],
            },
            api_client=mock_api,
        )

        assert result["beacons"] == []
        assert result["summary"]["totalHits"] == 0
        config = mock_api.get_beacons_without_preload_content.call_args.kwargs["get_website_beacons"]
        assert len(config.tag_filters) == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_list_and_scalar_responses(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        mock_api.get_beacons_without_preload_content.return_value = _json_response([{"a": 1}])
        result = await client.get_website_beacons(beacon_type="PAGELOAD", api_client=mock_api)
        # a list is wrapped as {"beacons": [...], "count": n} and then summarized (no "items" key)
        assert result["beacons"] == []
        assert result["summary"]["totalHits"] == 0

        mock_api.get_beacons_without_preload_content.return_value = _json_response("scalar")
        result = await client.get_website_beacons(beacon_type="PAGELOAD", api_client=mock_api)
        assert result["beacons"] == []

    @pytest.mark.mocked
    def test_summarize_non_dict(self, instana_credentials):
        client = create_website_analyze_client(instana_credentials)

        assert client._summarize_beacons_response([1, 2]) == [1, 2]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_missing_beacon_type(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacons(api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert result["missing_parameters"][0]["name"] == "beacon_type"
        mock_api.get_beacons_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_invalid_beacon_type(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacons(beacon_type="BOGUS", api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "get_website_beacons payload has" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_invalid_tag_name(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacons(
            beacon_type="PAGELOAD",
            tag_filter_expression=_tag_filter(name="wrong.name"),
            api_client=mock_api,
        )

        assert result["invalid_tags"] == ["wrong.name"]
        assert result["required_action"]["params"]["use_case"] == "FILTERING"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_tag_filter_missing_value(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)
        tag = {"type": "TAG_FILTER", "name": "beacon.website.name", "operator": "EQUALS",
               "entity": "NOT_APPLICABLE", "value": ""}

        result = await client.get_website_beacons(
            beacon_type="PAGELOAD", tag_filter_expression=tag, api_client=mock_api
        )

        # Either the structure validator or the converter rejects it; the API is never called.
        assert result.get("elicitation_needed") or "error" in result
        mock_api.get_beacons_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_invalid_pagination_object(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.models.cursor_pagination.CursorPagination",
            side_effect=ValueError("bad pagination"),
        ):
            result = await client.get_website_beacons(beacon_type="PAGELOAD", api_client=mock_api)

        assert "Invalid pagination configuration" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_request_object_creation_error(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_analyze_client(instana_credentials)

        with patch(
            "instana_client.models.get_website_beacons.GetWebsiteBeacons",
            side_effect=ValueError("bad request model"),
        ):
            result = await client.get_website_beacons(beacon_type="PAGELOAD", api_client=mock_api)

        assert "Failed to create GetWebsiteBeacons object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_api_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacons_without_preload_content.side_effect = Exception("API Error")
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacons(beacon_type="PAGELOAD", api_client=mock_api)

        assert "Failed to get website beacons" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_invalid_json_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_beacons_without_preload_content.return_value = _MockResponse(b"<html>")
        client = create_website_analyze_client(instana_credentials)

        result = await client.get_website_beacons(beacon_type="PAGELOAD", api_client=mock_api)

        assert "Failed to get website beacons" in result["error"]
