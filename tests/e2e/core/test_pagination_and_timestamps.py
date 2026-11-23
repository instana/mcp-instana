"""Mocked e2e tests for uncovered branches in src/core/pagination.py and timestamp_utils.py."""

import pytest

from src.core.pagination import (
    add_navigation,
    apply_navigation,
    build_pagination,
    paginate,
    stable_sort_key,
)
from src.core.timestamp_utils import convert_datetime_param, get_current_timestamp


class _Item:
    """Plain object exposing sort attributes (exercises the attribute path)."""

    def __init__(self, **attrs):
        for key, value in attrs.items():
            setattr(self, key, value)


class TestPaginationE2E:
    """Navigation, envelope building and sort-key extraction."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_navigation_ignores_non_dict(self):
        assert add_navigation("not-a-dict") == "not-a-dict"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_navigation_middle_page_has_both_links(self):
        pagination = {"page": 2, "total_pages": 5, "has_more": True}
        result = add_navigation(pagination)
        assert result["has_previous"] is True
        assert result["next_operation"] == "page_3"
        assert result["previous_operation"] == "page_1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_navigation_past_end_steps_back_to_last_page(self):
        pagination = {"page": 9, "total_pages": 3, "has_more": False}
        result = add_navigation(pagination)
        assert result["next_operation"] is None
        assert result["previous_operation"] == "page_3"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_navigation_invalid_page_defaults_to_first(self):
        result = add_navigation({"page": "abc", "has_more": False})
        assert result["has_previous"] is False
        assert result["previous_operation"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_build_pagination_envelope_with_list_id(self):
        result = build_pagination(page=1, page_size=10, total_items=25, list_id="apps")
        assert result["total_pages"] == 3
        assert result["has_more"] is True
        assert result["next_operation"] == "page_2"
        assert result["list_id"] == "apps"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_build_pagination_clamps_bad_inputs(self):
        result = build_pagination(page=0, page_size=0, total_items=-5)
        assert result["page"] == 1
        assert result["page_size"] >= 1
        assert result["total_items"] == 0
        assert result["total_pages"] == 1
        assert "list_id" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_paginate_returns_requested_slice(self):
        items = [{"id": str(i)} for i in range(7)]
        page_items, pagination = paginate(items, page=2, page_size=3)
        assert [i["id"] for i in page_items] == ["3", "4", "5"]
        assert pagination["total_items"] == 7

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_stable_sort_key_dict_prefers_id_then_name(self):
        assert stable_sort_key({"name": "x", "id": 42}) == "42"
        assert stable_sort_key({"label": "Checkout"}) == "Checkout"
        assert stable_sort_key({"other": 1}) == str({"other": 1})

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_stable_sort_key_object_uses_attributes(self):
        assert stable_sort_key(_Item(id="abc")) == "abc"
        assert stable_sort_key(_Item(title="Dash")) == "Dash"
        assert stable_sort_key(_Item(id=None, name=None)).startswith("<")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_apply_navigation_rewrites_page_operation(self):
        operation, params, error = apply_navigation("page_4", {"application_id": "a"}, "find_active")
        assert error is None
        assert operation == "find_active"
        assert params["page"] == 4


class TestTimestampUtilsE2E:
    """Output-unit and error branches of timestamp helpers."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_current_timestamp_in_seconds(self):
        result = get_current_timestamp(timezone="UTC", output_unit="seconds")
        assert result["success"] is True
        assert result["unit"] == "seconds"
        assert result["timestamp"] > 1_600_000_000
        assert result["timestamp"] < 100_000_000_000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_current_timestamp_invalid_unit(self):
        result = get_current_timestamp(output_unit="hours")
        assert "Invalid output_unit" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_current_timestamp_invalid_timezone_falls_back_to_utc(self):
        result = get_current_timestamp(timezone="Mars/Olympus")
        assert result["success"] is True
        assert result["timezone"] == "Mars/Olympus"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_convert_datetime_param_to_seconds(self):
        result = convert_datetime_param(
            "19 March 2026, 2:47 PM|UTC", "ingestionTime",
            default_timezone="UTC", output_unit="seconds",
        )
        assert result["converted"] is True
        assert isinstance(result["value"], int)
        assert result["value"] < 100_000_000_000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_convert_datetime_param_invalid_string_returns_error(self):
        result = convert_datetime_param("not a date", "ingestionTime", default_timezone="UTC")
        assert "error" in result
