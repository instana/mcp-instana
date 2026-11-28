"""
Additional E2E tests (mocked) for Mobile App Analyze MCP Tools.

Complements ``test_mobile_app_analyze.py`` with ``get_mobile_app_beacon_groups``
and the validation / conversion / summarisation helpers.
"""

import importlib
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _require_real_sdk():
    """Skip when another test module replaced the SDK with MagicMocks (mixed test runs)."""
    mocked = [
        name for name, mod in sys.modules.items()
        if name.startswith("instana_client") and isinstance(mod, MagicMock)
    ]
    if mocked:
        pytest.skip(f"instana_client is mocked in this session: {mocked[0]}")


def create_mobile_app_analyze_client(instana_credentials):
    """Dynamically import and create Mobile App Analyze client"""
    module = importlib.import_module("src.mobile_app.mobile_app_analyze")
    module = importlib.reload(module)
    return module.MobileAppAnalyzeMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


def _json_response(body, status=200):
    return _MockResponse(json.dumps(body).encode("utf-8"), status=status)


def _tag_filter(name="mobileBeacon.mobileApp.name", **overrides):
    base = {
        "type": "TAG_FILTER",
        "name": name,
        "operator": "EQUALS",
        "entity": "NOT_APPLICABLE",
        "value": "robot-shop",
    }
    base.update(overrides)
    return base


def _group(tag="mobileBeacon.view.name"):
    return {"groupbyTag": tag, "groupbyTagEntity": "NOT_APPLICABLE"}


def _metrics():
    return [{"metric": "beaconCount", "aggregation": "SUM"}]


def _groups_kwargs(**overrides):
    kwargs = {
        "metrics": _metrics(),
        "group": _group(),
        "beacon_type": "SESSION_START",
        "time_frame": {"windowSize": 3600000},
    }
    kwargs.update(overrides)
    return kwargs


def _compat_ok():
    """Patch metric/beacon-type compatibility pre-flight so it needs no catalog call."""
    return patch(
        "src.mobile_app.mobile_app_analyze.MobileAppAnalyzeMCPTools._validate_metric_compatibility_for_beacon_groups",
        new=AsyncMock(return_value=None),
    )


class TestMobileAppAnalyzeHelpersE2E:
    def setup_method(self):
        from src.core.catalog_cache import clear_cache
        clear_cache()

    @pytest.mark.mocked
    def test_clean_nan_values(self):
        module = importlib.reload(importlib.import_module("src.mobile_app.mobile_app_analyze"))
        assert module.clean_nan_values({"a": "NaN", "b": ["NaN", {"c": "NaN"}], "d": 1}) == {
            "a": None,
            "b": [None, {"c": None}],
            "d": 1,
        }

    # -- _apply_beacon_groups_defaults ------------------------------------------------

    @pytest.mark.mocked
    def test_apply_beacon_groups_defaults_fills_everything(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        beacon_type, metrics, group, time_frame, tag_filter = client._apply_beacon_groups_defaults(
            None, None, None, None, None
        )

        assert beacon_type == "SESSION_START"
        assert metrics == [{"metric": "beaconCount", "aggregation": "SUM"}]
        assert group == {"groupbyTag": "mobileBeacon.mobileApp.name"}
        assert time_frame == {"windowSize": 3600000}
        assert tag_filter == {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}

    @pytest.mark.mocked
    def test_apply_beacon_groups_defaults_keeps_user_values(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        tf = _tag_filter()

        result = client._apply_beacon_groups_defaults("CRASH", _metrics(), _group(), {"windowSize": 5}, tf)

        assert result == ("CRASH", _metrics(), _group(), {"windowSize": 5}, tf)

    # -- _build_beacon_groups_query_params --------------------------------------------

    @pytest.mark.mocked
    def test_build_beacon_groups_query_params_group_defaults(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        params = client._build_beacon_groups_query_params(
            "SESSION_START", _metrics(), {}, {"windowSize": 1}, {}, None, None
        )

        assert params["group"] == {
            "groupbyTag": "mobileBeacon.view.name",
            "groupbyTagEntity": "NOT_APPLICABLE",
        }
        assert "tagFilterExpression" not in params
        assert "order" not in params
        assert "pagination" not in params

    @pytest.mark.mocked
    def test_build_beacon_groups_query_params_invalid_tag_filter(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        params = client._build_beacon_groups_query_params(
            "SESSION_START", _metrics(), _group(), {"windowSize": 1}, {"type": "NOT_A_TYPE"}, None, None
        )

        assert params["error"]["type"] == "TAG_FILTER_PARSE_ERROR"
        assert "Invalid tag filter expression" in params["error"]["message"]

    # -- _check_metric_error / _handle_beacon_groups_error_response -------------------

    @pytest.mark.mocked
    def test_check_metric_error_detects_unknown_metric(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        body = json.dumps({"errors": ["Metric type unknown: foo", "other"]})

        result = client._check_metric_error(body)

        assert result["elicitation_needed"] is True
        assert "Metric type unknown: foo" in result["reason"]
        assert result["required_action"]["operation"] == "get_mobile_app_metric_catalog"

    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "body",
        [
            "not json",
            json.dumps({"errors": "not-a-list"}),
            json.dumps({"errors": ["something else", 5]}),
            json.dumps({"no_errors": True}),
        ],
    )
    def test_check_metric_error_returns_none_for_other_errors(self, instana_credentials, body):
        client = create_mobile_app_analyze_client(instana_credentials)
        assert client._check_metric_error(body) is None

    @pytest.mark.mocked
    def test_handle_beacon_groups_error_response_falls_back_to_generic(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        response = _MockResponse(b"oops", status=500)

        result = client._handle_beacon_groups_error_response(response, "oops")

        assert result["status_code"] == 500
        assert "get mobile app beacon groups" in result["error"]

    # -- _handle_nan_error ------------------------------------------------------------

    @pytest.mark.mocked
    def test_handle_nan_error_custom_metric(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = client._handle_nan_error(ValueError("bad customMetric: NaN"))

        assert "NaN values for customMetric" in result["error"]
        assert "suggestion" in result

    @pytest.mark.mocked
    def test_handle_nan_error_reraises_other_errors(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with pytest.raises(ValueError, match="API error: kaboom"):
            client._handle_nan_error(RuntimeError("kaboom"))

    # -- pagination / defaults for beacons --------------------------------------------

    @pytest.mark.mocked
    def test_apply_beacons_defaults(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        time_frame, pagination, filter_fields = client._apply_beacons_defaults(None, None, None)

        assert time_frame == {"windowSize": 3600000}
        assert pagination == {"retrievalSize": 20, "offset": 0}
        assert filter_fields is True

    @pytest.mark.mocked
    def test_apply_beacons_defaults_validates_given_pagination(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        _, pagination, filter_fields = client._apply_beacons_defaults(
            {"windowSize": 1}, {"retrievalSize": 500}, False
        )

        assert pagination == {"retrievalSize": 200, "offset": 0}
        assert filter_fields is False

    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "given,expected",
        [
            ({"retrievalSize": 0}, {"retrievalSize": 1, "offset": 0}),
            ({"retrievalSize": 201, "offset": 4}, {"retrievalSize": 200, "offset": 4}),
            ({"retrievalSize": 50}, {"retrievalSize": 50, "offset": 0}),
            ({"offset": 7}, {"retrievalSize": 20, "offset": 7}),
        ],
    )
    def test_validate_pagination_clamps(self, instana_credentials, given, expected):
        client = create_mobile_app_analyze_client(instana_credentials)
        assert client._validate_pagination(dict(given)) == expected

    # -- tag filter conversion --------------------------------------------------------

    @pytest.mark.mocked
    def test_convert_single_tag_filter_requires_fields(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = client._convert_single_tag_filter({"name": "mobileBeacon.x", "operator": "EQUALS"})

        assert result == {"error": "TAG_FILTER requires 'name', 'operator', and 'value' fields"}

    @pytest.mark.mocked
    def test_convert_single_tag_filter_with_and_without_entity(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with_entity = client._convert_single_tag_filter(_tag_filter())
        without_entity = client._convert_single_tag_filter(
            {"name": "mobileBeacon.x", "operator": "EQUALS", "value": "v"}
        )

        assert with_entity.name == "mobileBeacon.mobileApp.name"
        assert with_entity.entity == "NOT_APPLICABLE"
        assert without_entity.name == "mobileBeacon.x"

    @pytest.mark.mocked
    def test_convert_expression_filters_skips_non_tag_filters(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = client._convert_expression_filters(
            [
                _tag_filter(),
                {"type": "TAG_FILTER", "name": "mobileBeacon.y", "operator": "EQUALS", "value": "v"},
                {"type": "EXPRESSION", "elements": []},
            ]
        )

        assert [f.name for f in result] == ["mobileBeacon.mobileApp.name", "mobileBeacon.y"]

    @pytest.mark.mocked
    def test_convert_tag_filter_to_deprecated_variants(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        single = client._convert_tag_filter_to_deprecated(_tag_filter())
        assert len(single) == 1

        error = client._convert_tag_filter_to_deprecated({"type": "TAG_FILTER", "name": "n"})
        assert "error" in error

        expression = client._convert_tag_filter_to_deprecated(
            {"type": "EXPRESSION", "logicalOperator": "AND", "elements": [_tag_filter(), _tag_filter("mobileBeacon.b")]}
        )
        assert len(expression) == 2

        empty_expression = client._convert_tag_filter_to_deprecated(
            {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}
        )
        assert empty_expression == []

        expression_without_tag_filters = client._convert_tag_filter_to_deprecated(
            {"type": "EXPRESSION", "logicalOperator": "AND", "elements": [{"type": "EXPRESSION"}]}
        )
        assert expression_without_tag_filters == []

        assert client._convert_tag_filter_to_deprecated({"type": "OTHER"}) == []

    @pytest.mark.mocked
    def test_build_beacons_query_params_variants(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        pagination = {"retrievalSize": 5, "offset": 0}

        with_filter = client._build_beacons_query_params(
            "SESSION_START", {"windowSize": 1}, _tag_filter(), pagination
        )
        assert len(with_filter["tagFilters"]) == 1
        assert with_filter["pagination"].retrieval_size == 5

        empty_expression = client._build_beacons_query_params(
            "SESSION_START",
            {"windowSize": 1},
            {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
            pagination,
        )
        assert "tagFilters" not in empty_expression

        conversion_error = client._build_beacons_query_params(
            "SESSION_START", {"windowSize": 1}, {"type": "TAG_FILTER", "name": "n"}, pagination
        )
        assert "TAG_FILTER requires" in conversion_error["error"]

        bad_pagination = client._build_beacons_query_params(
            "SESSION_START", {"windowSize": 1}, None, {"retrievalSize": "many"}
        )
        assert "Invalid pagination configuration" in bad_pagination["error"]

    @pytest.mark.mocked
    def test_build_beacons_query_params_conversion_exception(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with patch.object(client, "_convert_tag_filter_to_deprecated", side_effect=RuntimeError("kaboom")):
            result = client._build_beacons_query_params(
                "SESSION_START", {"windowSize": 1}, _tag_filter(), {"retrievalSize": 1, "offset": 0}
            )

        assert result == {"error": "Invalid tag filter expression: kaboom"}

    # -- _process_beacons_response -----------------------------------------------------

    @pytest.mark.mocked
    def test_process_beacons_response_scalar_json(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = client._process_beacons_response(_MockResponse(b"42"))

        # scalar -> {"data": 42} -> summarised
        assert result["beacons"] == []
        assert result["summary"]["totalHits"] == 0

    @pytest.mark.mocked
    def test_process_beacons_response_list_with_nan(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        payload = [{"beacon": {"mobileAppLabel": "A", "duration": "NaN", "type": "x"}}]

        result = client._process_beacons_response(_json_response(payload))

        # a plain list is wrapped as {"beacons": [...]} and has no "items" -> nothing extracted
        assert result["beacons"] == []

    # -- _extract_tags_and_check_entity / _validate_tag_names ---------------------------

    @pytest.mark.mocked
    def test_extract_tags_and_check_entity(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        missing = []
        expr = {
            "type": "EXPRESSION",
            "elements": [
                _tag_filter("mobileBeacon.a"),
                {"type": "TAG_FILTER", "name": "mobileBeacon.b", "operator": "EQUALS", "value": "x"},
                {"type": "TAG_FILTER", "name": "mobileBeacon.c", "entity": None, "value": "x"},
                {"type": "TAG_FILTER", "operator": "EQUALS"},
            ],
        }

        tags = client._extract_tags_and_check_entity(expr, missing)

        assert tags == ["mobileBeacon.a", "mobileBeacon.b", "mobileBeacon.c"]
        assert missing == ["mobileBeacon.b", "mobileBeacon.c"]
        assert client._extract_tags_and_check_entity(None, []) == []
        assert client._extract_tags_and_check_entity("nope", []) == []
        assert client._extract_tags_and_check_entity({"type": "OTHER"}, []) == []

    @pytest.mark.mocked
    def test_validate_tag_names_missing_entity(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = client._validate_tag_names(
            {"type": "TAG_FILTER", "name": "mobileBeacon.a", "operator": "EQUALS", "value": "x"},
            None,
            "SESSION_START",
            use_case="FILTERING",
        )

        assert result["elicitation_needed"] is True
        assert result["missing_entity_tags"] == ["mobileBeacon.a"]
        assert "entity" in result["message"]

    @pytest.mark.mocked
    def test_validate_tag_names_no_tags_extracted(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = client._validate_tag_names({"type": "TAG_FILTER"}, {}, "CRASH")

        assert result["reason"] == "No valid tag names found in tag_filter_expression or group"
        assert result["required_action"]["operation"] == "get_mobile_app_tag_catalog"

    # -- _validate_metrics ------------------------------------------------------------

    @pytest.mark.mocked
    def test_validate_metrics_branches(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        assert client._validate_metrics(None, user_provided=True) is None
        assert client._validate_metrics([], user_provided=True) is None
        assert client._validate_metrics([{"metric": ""}], user_provided=False) is None
        assert client._validate_metrics(_metrics(), user_provided=True) is None

        no_names = client._validate_metrics([{"aggregation": "SUM"}, "bad"], user_provided=True)
        assert no_names["reason"] == "Metrics list provided but no valid metric names found"

        blank = client._validate_metrics([{"metric": "  "}, {"metric": 5}], user_provided=True)
        assert blank["invalid_metrics"] == ["  ", 5]
        assert blank["required_action"]["operation"] == "get_mobile_app_metric_catalog"

    # -- beacon summarisation ---------------------------------------------------------

    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "field,value,expected",
        [
            ("label", "", True),
            ("label", -1, True),
            ("label", None, True),
            ("label", [], True),
            ("label", {}, True),
            ("errorCount", 0, True),
            ("coldStartTimeMs", 0, True),
            ("duration", 0, False),
            ("label", "x", False),
            ("errorCount", 3, False),
        ],
    )
    def test_should_skip_field_value(self, instana_credentials, field, value, expected):
        client = create_mobile_app_analyze_client(instana_credentials)
        assert client._should_skip_field_value(field, value) is expected

    @pytest.mark.mocked
    def test_extract_clean_beacon_filters_non_essential(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        fields = client._get_essential_beacon_fields()

        cleaned = client._extract_clean_beacon(
            {"mobileAppLabel": "A", "label": "", "errorCount": 0, "secret": "drop-me", "duration": 0}, fields
        )

        assert cleaned == {"mobileAppLabel": "A", "duration": 0}

    @pytest.mark.mocked
    def test_process_beacon_items_variants(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        fields = client._get_essential_beacon_fields()
        items = [
            {"beacon": {"mobileAppLabel": "A", "extra": 1}},
            {"beacon": "not-a-dict"},
            {"no_beacon": True},
            "not-a-dict-item",
        ]

        filtered = client._process_beacon_items(items, fields, True)
        raw = client._process_beacon_items(items, fields, False)
        appended = client._process_beacon_items(items[:1], fields, True, [{"pre": 1}])

        assert filtered == [{"mobileAppLabel": "A"}]
        assert raw == [{"mobileAppLabel": "A", "extra": 1}]
        assert appended == [{"pre": 1}, {"mobileAppLabel": "A"}]

    @pytest.mark.mocked
    def test_summarize_beacons_response(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        assert client._summarize_beacons_response(["not", "a", "dict"]) == ["not", "a", "dict"]

        summary = client._summarize_beacons_response(
            {
                "totalHits": 2,
                "totalRepresentedItemCount": 3,
                "totalRetainedItemCount": 4,
                "canLoadMore": True,
                "adjustedTimeframe": {"from": 1, "to": 2},
                "items": [{"beacon": {"mobileAppLabel": "A"}}],
            }
        )
        assert summary["summary"] == {
            "totalHits": 2,
            "totalRepresentedItemCount": 3,
            "totalRetainedItemCount": 4,
            "canLoadMore": True,
            "timeframe": {"from": 1, "to": 2},
        }
        assert summary["beacons"] == [{"mobileAppLabel": "A"}]

        no_items = client._summarize_beacons_response({"items": "not-a-list"})
        assert no_items["beacons"] == []
        assert "timeframe" not in no_items["summary"]

    # -- _check_elicitation_for_beacon_groups -------------------------------------------

    @pytest.mark.mocked
    def test_check_elicitation_for_beacon_groups(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        all_missing = client._check_elicitation_for_beacon_groups(None, None, None)
        assert all_missing["elicitation_required"] is True
        assert [p["name"] for p in all_missing["missing_parameters"]] == ["metrics", "group", "beacon_type"]
        assert "- beacon_type:" in all_missing["elicitation_prompt"]

        only_type = client._check_elicitation_for_beacon_groups(_metrics(), _group(), None)
        assert [p["name"] for p in only_type["missing_parameters"]] == ["beacon_type"]

        assert client._check_elicitation_for_beacon_groups(_metrics(), _group(), "CRASH") is None

    # -- _validate_beacon_group_structure -----------------------------------------------

    @pytest.mark.mocked
    def test_validate_beacon_group_structure_collects_errors(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = client._validate_beacon_group_structure(
            [{"metric": "", "aggregation": "BAD"}],
            {"groupbyTag": "mobileBeacon.x"},
            {"type": "WRONG"},
            {"windowSize": -1},
            {"by": "", "direction": "UP"},
            {"retrievalSize": 0},
        )

        assert result["elicitation_needed"] is True
        assert len(result["api_error"]) >= 6
        assert "get_mobile_app_beacon_groups payload has" in result["reason"]

    @pytest.mark.mocked
    def test_validate_beacon_group_structure_granularity_ratio(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = client._validate_beacon_group_structure(
            [{"metric": "beaconCount", "aggregation": "SUM", "granularity": 1}],
            _group(),
            None,
            {"windowSize": 2_592_000_000},
            None,
            None,
        )

        assert any("data points" in e for e in result["api_error"])

    @pytest.mark.mocked
    def test_validate_beacon_group_structure_ok(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        assert client._validate_beacon_group_structure(_metrics(), _group(), None, None, None, None) is None


class TestMobileAppBeaconGroupsE2E:
    """get_mobile_app_beacon_groups"""

    def setup_method(self):
        from src.core.catalog_cache import clear_cache
        clear_cache()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_success(self, instana_credentials):
        body = {"items": [{"name": "Home", "metrics": {"beaconCount.SUM": [[1, 5]]}}]}
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = _json_response(body)
        client = create_mobile_app_analyze_client(instana_credentials)

        with _compat_ok():
            result = await client.get_mobile_app_beacon_groups(
                **_groups_kwargs(
                    tag_filter_expression=_tag_filter(),
                    order={"by": "beaconCount", "direction": "DESC"},
                    pagination={"retrievalSize": 5},
                ),
                api_client=mock_api,
            )

        assert result == body
        kwargs = mock_api.get_mobile_app_beacon_groups_without_preload_content.call_args.kwargs
        assert kwargs["fill_time_series"] is True
        assert kwargs["get_mobile_app_beacon_groups"] is not None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_success_with_ctx_and_fill_time_series_false(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = _json_response({"items": []})
        ctx = MagicMock()
        ctx.log = AsyncMock()
        client = create_mobile_app_analyze_client(instana_credentials)

        with _compat_ok():
            result = await client.get_mobile_app_beacon_groups(
                **_groups_kwargs(fill_time_series=False),
                ctx=ctx,
                api_client=mock_api,
                resource_type="mobile_app",
                tool_name="manage_mobile_apps",
            )

        assert result == {"items": []}
        assert mock_api.get_mobile_app_beacon_groups_without_preload_content.call_args.kwargs["fill_time_series"] is False

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_expression_filter_skips_tag_validation(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = _json_response({"items": []})
        client = create_mobile_app_analyze_client(instana_credentials)

        with _compat_ok():
            result = await client.get_mobile_app_beacon_groups(
                **_groups_kwargs(
                    tag_filter_expression={"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}
                ),
                api_client=mock_api,
            )

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_missing_required_params_uses_elicitation_required_key(self, instana_credentials):
        mock_api = MagicMock()
        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_mobile_app_beacon_groups(api_client=mock_api)

        assert result["elicitation_required"] is True
        assert len(result["missing_parameters"]) == 3
        mock_api.get_mobile_app_beacon_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_structure_validation_error(self, instana_credentials):
        mock_api = MagicMock()
        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_mobile_app_beacon_groups(
            **_groups_kwargs(time_frame={"windowSize": -1}), api_client=mock_api
        )

        assert result["elicitation_needed"] is True
        assert "validation problem" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_metric_names_after_structure_validation(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with patch.object(
            client, "_validate_beacon_group_structure", return_value=None
        ):
            result = await client.get_mobile_app_beacon_groups(
                **_groups_kwargs(metrics=[{"aggregation": "SUM"}]), api_client=MagicMock()
            )

        assert result["reason"] == "Metrics list provided but no valid metric names found"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_group_tag_name(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_mobile_app_beacon_groups(
            **_groups_kwargs(group={"groupbyTag": "beacon.page.name", "groupbyTagEntity": "NOT_APPLICABLE"}),
            api_client=MagicMock(),
        )

        assert result["invalid_tags"] == ["beacon.page.name"]
        assert result["required_action"]["params"]["use_case"] == "GROUPING"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_filter_missing_entity(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        # validate_tag_filter_expression requires entity too, so bypass the structural check
        tag_filter = {"type": "TAG_FILTER", "name": "mobileBeacon.a", "operator": "EQUALS", "value": "x"}

        with patch.object(client, "_validate_beacon_group_structure", return_value=None):
            result = await client.get_mobile_app_beacon_groups(
                **_groups_kwargs(tag_filter_expression=tag_filter), api_client=MagicMock()
            )

        assert result["missing_entity_tags"] == ["mobileBeacon.a"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_compatibility_error_is_returned(self, instana_credentials):
        mock_api = MagicMock()
        client = create_mobile_app_analyze_client(instana_credentials)
        compat_error = {"elicitation_needed": True, "reason": "incompatible"}

        with patch.object(
            client, "_validate_metric_compatibility_for_beacon_groups", AsyncMock(return_value=compat_error)
        ):
            result = await client.get_mobile_app_beacon_groups(**_groups_kwargs(), api_client=mock_api)

        assert result == compat_error
        mock_api.get_mobile_app_beacon_groups_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_query_param_build_error_is_returned(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with _compat_ok():
            result = await client.get_mobile_app_beacon_groups(
                **_groups_kwargs(tag_filter_expression={"type": "TAG_FILTER", "name": "mobileBeacon.a",
                                                        "operator": "EQUALS", "entity": "BAD_ENTITY",
                                                        "value": "x"}),
                api_client=MagicMock(),
            )

        # either surfaced by the structure validator or by the SDK model conversion
        assert result.get("elicitation_needed") or "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_request_object_creation_error(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client._execute_beacon_groups_api_call(
            {"type": "SESSION_START"}, True, MagicMock()
        )

        assert result["error"].startswith("Failed to create beacon groups request")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metric_error_response_triggers_catalog_elicitation(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = _json_response(
            {"errors": ["Metric type unknown: nope"]}, status=400
        )
        client = create_mobile_app_analyze_client(instana_credentials)

        with _compat_ok():
            result = await client.get_mobile_app_beacon_groups(**_groups_kwargs(), api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "Metric type unknown" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_generic_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = _MockResponse(
            b"server exploded", status=500
        )
        client = create_mobile_app_analyze_client(instana_credentials)

        with _compat_ok():
            result = await client.get_mobile_app_beacon_groups(**_groups_kwargs(), api_client=mock_api)

        assert result["status_code"] == 500
        assert result["details"] == "server exploded"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_api_exception_with_nan_custom_metric(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacon_groups_without_preload_content.side_effect = ValueError(
            "customMetric got NaN"
        )
        client = create_mobile_app_analyze_client(instana_credentials)

        with _compat_ok():
            result = await client.get_mobile_app_beacon_groups(**_groups_kwargs(), api_client=mock_api)

        assert "NaN values for customMetric" in result["error"]
        assert "suggestion" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_api_exception_other_error_reaches_outer_handler(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacon_groups_without_preload_content.side_effect = RuntimeError("down")
        client = create_mobile_app_analyze_client(instana_credentials)

        with _compat_ok():
            result = await client.get_mobile_app_beacon_groups(**_groups_kwargs(), api_client=mock_api)

        assert result == {"error": "Failed to get mobile app beacon groups: API error: down"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_json_body_reaches_outer_handler(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacon_groups_without_preload_content.return_value = _MockResponse(b"<html>")
        client = create_mobile_app_analyze_client(instana_credentials)

        with _compat_ok():
            result = await client.get_mobile_app_beacon_groups(**_groups_kwargs(), api_client=mock_api)

        assert result["error"].startswith("Failed to get mobile app beacon groups: API error")


class TestMobileAppMetricCompatibilityE2E:
    """_validate_metric_compatibility_for_beacon_groups with a mocked metric catalog"""

    def setup_method(self):
        from src.core.catalog_cache import clear_cache
        clear_cache()

    @staticmethod
    def _catalog_patch(response=None, side_effect=None):
        catalog_instance = MagicMock()
        fetch = catalog_instance.get_mobile_app_metric_catalog_without_preload_content
        if side_effect is not None:
            fetch.side_effect = side_effect
        else:
            fetch.return_value = response
        return patch(
            "instana_client.api.mobile_app_catalog_api.MobileAppCatalogApi",
            return_value=catalog_instance,
        )

    @staticmethod
    def _catalog_body():
        return [
            {
                "metricId": "beaconCount",
                "label": "Beacon count",
                "aggregations": ["SUM", "MEAN"],
                "beaconTypes": ["sessionStart", "viewChange"],
            }
        ]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unknown_beacon_type(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client._validate_metric_compatibility_for_beacon_groups(
            _metrics(), "NOT_A_TYPE", MagicMock()
        )

        assert result["elicitation_needed"] is True
        assert "unrecognized beacon_type" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_compatible_metric_passes(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with self._catalog_patch(_json_response(self._catalog_body())):
            result = await client._validate_metric_compatibility_for_beacon_groups(
                _metrics(), "SESSION_START", MagicMock()
            )

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_is_cached_between_calls(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        api = MagicMock()

        with self._catalog_patch(_json_response(self._catalog_body())) as patched:
            await client._validate_metric_compatibility_for_beacon_groups(_metrics(), "SESSION_START", api)
            await client._validate_metric_compatibility_for_beacon_groups(_metrics(), "SESSION_START", api)

        assert patched.call_count == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_incompatible_beacon_type_and_unknown_metric(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with self._catalog_patch(_json_response(self._catalog_body())):
            incompatible = await client._validate_metric_compatibility_for_beacon_groups(
                _metrics(), "CRASH", MagicMock()
            )
        assert "incompatible with beacon_type 'CRASH'" in incompatible["api_error"][0]
        assert incompatible["required_action"]["operation"] == "get_mobile_app_metric_catalog"

        from src.core.catalog_cache import clear_cache
        clear_cache()

        with self._catalog_patch(_json_response(self._catalog_body())):
            unknown = await client._validate_metric_compatibility_for_beacon_groups(
                [{"metric": "ghost", "aggregation": "SUM"}, {"metric": "beaconCount", "aggregation": "P99"}],
                "SESSION_START",
                MagicMock(),
            )
        assert len(unknown["api_error"]) == 2
        assert "not found in catalog" in unknown["api_error"][0]
        assert "does not support aggregation 'P99'" in unknown["api_error"][1]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_http_error(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with self._catalog_patch(_MockResponse(b"nope", status=503)):
            result = await client._validate_metric_compatibility_for_beacon_groups(
                _metrics(), "SESSION_START", MagicMock()
            )

        assert "HTTP 503" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_fetch_exception_and_bad_payloads(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with self._catalog_patch(side_effect=RuntimeError("down")):
            fetch_error = await client._validate_metric_compatibility_for_beacon_groups(
                _metrics(), "SESSION_START", MagicMock()
            )
        assert "Failed to fetch metric catalog" in fetch_error["error"]

        with self._catalog_patch(_MockResponse(b"not-json")):
            parse_error = await client._validate_metric_compatibility_for_beacon_groups(
                _metrics(), "SESSION_START", MagicMock()
            )
        assert "Failed to parse metric catalog response" in parse_error["error"]

        with self._catalog_patch(_json_response({"not": "a list"})):
            not_list = await client._validate_metric_compatibility_for_beacon_groups(
                _metrics(), "SESSION_START", MagicMock()
            )
        assert "not a list" in not_list["error"]

        with self._catalog_patch(_json_response(["x"])):
            non_dict = await client._validate_metric_compatibility_for_beacon_groups(
                _metrics(), "SESSION_START", MagicMock()
            )
        assert "non-dict entries" in non_dict["error"]

        with self._catalog_patch(_json_response([{"label": "no id"}])):
            malformed = await client._validate_metric_compatibility_for_beacon_groups(
                _metrics(), "SESSION_START", MagicMock()
            )
        assert "malformed entries" in malformed["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_no_underlying_api_client(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        api = MagicMock(spec=[])  # no ``api_client`` attribute

        result = await client._validate_metric_compatibility_for_beacon_groups(
            _metrics(), "SESSION_START", api
        )

        assert result == {"error": "Cannot access underlying ApiClient for catalog fetch"}


class TestMobileAppBeaconsMoreE2E:
    """extra branches of get_all_mobile_app_beacons"""

    @staticmethod
    def _api(body=None):
        api = MagicMock()
        api.get_mobile_app_beacons_without_preload_content.return_value = _json_response(
            body if body is not None else {"totalHits": 0, "items": []}
        )
        return api

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_tag_filter_and_unfiltered_fields(self, instana_credentials):
        api = self._api(
            {"totalHits": 1, "items": [{"beacon": {"mobileAppLabel": "A", "secret": "kept", "label": ""}}]}
        )
        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            tag_filter_expression=_tag_filter(),
            filter_fields=False,
            api_client=api,
        )

        assert result["beacons"] == [{"mobileAppLabel": "A", "secret": "kept", "label": ""}]
        assert len(api.get_mobile_app_beacons_without_preload_content.call_args.kwargs
                   ["get_mobile_app_beacons"].tag_filters) == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_with_expression_filter(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="VIEW_CHANGE",
            tag_filter_expression={
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": [_tag_filter(), _tag_filter("mobileBeacon.view.name", value="Home")],
            },
            api_client=self._api(),
        )

        assert result["summary"]["totalHits"] == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_tag_filter_with_invalid_tag_name(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        api = self._api()

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START", tag_filter_expression=_tag_filter("beacon.page.name"), api_client=api
        )

        assert result["invalid_tags"] == ["beacon.page.name"]
        assert result["required_action"]["params"]["use_case"] == "FILTERING"
        api.get_mobile_app_beacons_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_query_param_error_is_returned(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)
        # TAG_FILTER without a ``value`` passes structural validation but cannot be converted
        tag_filter = {"type": "TAG_FILTER", "name": "mobileBeacon.a", "operator": "IS_EMPTY", "entity": "NOT_APPLICABLE"}

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START", tag_filter_expression=tag_filter, api_client=self._api()
        )

        assert "TAG_FILTER requires" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_beacons_request_object_creation_error(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        with patch.object(
            client, "_build_beacons_query_params", return_value={"type": ["not", "a", "string"]}
        ):
            result = await client.get_all_mobile_app_beacons(
                beacon_type="SESSION_START", api_client=self._api()
            )

        assert result["error"].startswith("Failed to create GetMobileAppBeacons object")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_structure_validation_error(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="WRONG", time_frame={"windowSize": -1}, pagination={"retrievalSize": 0}, api_client=MagicMock()
        )

        assert result["elicitation_needed"] is True
        assert len(result["api_error"]) >= 3
