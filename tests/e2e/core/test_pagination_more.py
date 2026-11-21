"""Mocked e2e tests for remaining branches in src/core/pagination.py."""

import pytest

from src.core.pagination import (
    MAX_PAGE_NUMBER,
    NavigationError,
    add_navigation,
    apply_navigation,
    coerce_int,
    navigation_error,
    normalize_page_args,
    operation_for_page,
    page_kwargs,
    paginate,
    resolve_nav_page,
    stable_sort_key,
)


class _Obj:
    """Plain object exposing arbitrary attributes."""

    def __init__(self, **attrs):
        for key, value in attrs.items():
            setattr(self, key, value)


class TestPaginationArgumentHelpersE2E:
    """coerce_int / normalize_page_args / page_kwargs / operation_for_page."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_operation_for_page_clamps_to_first(self):
        assert operation_for_page(3) == "page_3"
        assert operation_for_page(0) == "page_1"
        assert operation_for_page(-4) == "page_1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_coerce_int_handles_none_blank_and_strings(self):
        assert coerce_int(None, 7) == 7
        assert coerce_int("   ", 7) == 7
        assert coerce_int("12", 7) == 12
        assert coerce_int(5, 7) == 5

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_coerce_int_handles_float_like_values(self):
        assert coerce_int("2.0", 7) == 2
        assert coerce_int(3.0, 7) == 3
        assert coerce_int("2.5", 7) == 7
        assert coerce_int("abc", 7) == 7
        assert coerce_int("nan", 7) == 7
        assert coerce_int([1], 7) == 7

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_normalize_page_args_clamps_page_and_size(self):
        assert normalize_page_args(0, 500) == (1, 100)
        assert normalize_page_args("3", "25") == (3, 25)
        assert normalize_page_args(None, None) == (1, 10)
        assert normalize_page_args("x", "y", default_size=20, max_size=50) == (1, 20)
        assert normalize_page_args(2, -3) == (2, 1)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_kwargs_only_returns_supplied_entries(self):
        assert page_kwargs({"page": 2, "page_size": None, "other": 1}) == {"page": 2}
        assert page_kwargs({"page_size": 5}) == {"page_size": 5}
        assert page_kwargs({}) == {}


class TestResolveNavPageE2E:
    """Navigation operation resolution and its error branches."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_n_is_case_insensitive(self):
        assert resolve_nav_page("page_3", {}) == 3
        assert resolve_nav_page("PAGE_12", {}) == 12
        assert resolve_nav_page("  Page_2 ", {}) == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_non_navigation_operation_returns_none(self):
        assert resolve_nav_page("find_active", {}) is None
        assert resolve_nav_page(None, {}) is None
        assert resolve_nav_page("", {}) is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_zero_and_too_large_are_rejected(self):
        with pytest.raises(NavigationError, match=">= 1"):
            resolve_nav_page("page_0", {})
        with pytest.raises(NavigationError, match="<="):
            resolve_nav_page(f"page_{MAX_PAGE_NUMBER + 1}", {})

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_go_to_page_uses_params_or_argument(self):
        assert resolve_nav_page("go_to_page", {"target_page": 4}) == 4
        assert resolve_nav_page("go_to_page", {}, target_page="5") == 5
        assert resolve_nav_page("go_to_page", {"target_page": "6.0"}) == 6

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_go_to_page_requires_target(self):
        with pytest.raises(NavigationError, match="requires target_page"):
            resolve_nav_page("go_to_page", {})
        with pytest.raises(NavigationError, match="requires target_page"):
            resolve_nav_page("go_to_page", {"target_page": "  "})

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_go_to_page_rejects_non_whole_numbers(self):
        with pytest.raises(NavigationError, match="whole number"):
            resolve_nav_page("go_to_page", {"target_page": "abc"})
        with pytest.raises(NavigationError, match="whole number"):
            resolve_nav_page("go_to_page", {"target_page": "2.5"})
        with pytest.raises(NavigationError, match="whole number"):
            resolve_nav_page("go_to_page", {"target_page": True})

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_next_and_previous_use_current_page(self):
        assert resolve_nav_page("next", {"page": 2}) == 3
        assert resolve_nav_page("previous", {"page": 5}) == 4
        assert resolve_nav_page("next", {"page_number": "7"}) == 8
        assert resolve_nav_page("next", {}, page_number=9) == 10

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_current_page_skips_blank_values(self):
        assert resolve_nav_page("next", {"page_number": "  ", "page": 3}) == 4

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_next_without_current_page_is_error(self):
        with pytest.raises(NavigationError, match="needs the current page"):
            resolve_nav_page("next", {})

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_previous_on_first_page_is_error(self):
        with pytest.raises(NavigationError, match="first page"):
            resolve_nav_page("previous", {"page": 1})

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_current_page_below_one_is_error(self):
        with pytest.raises(NavigationError, match="current page must be >= 1"):
            resolve_nav_page("next", {"page": 0})

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_current_page_is_error(self):
        with pytest.raises(NavigationError, match="whole number"):
            resolve_nav_page("next", {"page": "abc"})

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_previous_below_first_destination_rejected(self):
        # current=1 is caught earlier, so a negative current page hits the < 1 guard
        with pytest.raises(NavigationError, match="current page must be >= 1"):
            resolve_nav_page("previous", {"page": -2})


class TestApplyNavigationE2E:
    """Router-facing navigation helpers."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_navigation_error_shape(self):
        result = navigation_error("next", "needs page")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_pagination"
        assert result["api_error"][0]["field"] == "operation"
        assert result["api_error"][0]["issue"] == "needs page"
        assert "'next'" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_apply_navigation_returns_error_for_unresolvable_request(self):
        params = {"application_id": "a"}
        operation, new_params, error = apply_navigation("next", params, "find_active")
        assert operation == "next"
        assert new_params is params
        assert error["elicitation_needed"] is True
        assert "needs the current page" in error["api_error"][0]["issue"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_apply_navigation_passes_through_regular_operations(self):
        params = {"id": "x"}
        operation, new_params, error = apply_navigation("find", params, "find_active")
        assert (operation, new_params, error) == ("find", params, None)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_apply_navigation_custom_page_key_keeps_other_params(self):
        operation, params, error = apply_navigation(
            "next", {"page_number": 2, "q": "x"}, "get_all", page_key="page_number"
        )
        assert error is None
        assert operation == "get_all"
        assert params == {"page_number": 3, "q": "x"}


class TestAddNavigationAndPaginateE2E:
    """Envelope navigation edge cases and paginate slicing."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_navigation_first_page_has_no_previous(self):
        result = add_navigation({"page": 1, "has_more": True, "total_pages": 4})
        assert result["has_previous"] is False
        assert result["previous_operation"] is None
        assert result["next_operation"] == "page_2"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_navigation_without_total_pages_steps_back_one(self):
        result = add_navigation({"page": 4, "has_more": False})
        assert result["previous_operation"] == "page_3"
        assert result["next_operation"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_paginate_with_sort_key_orders_before_slicing(self):
        records = [{"id": "c"}, {"id": "a"}, {"id": "b"}]
        page_items, pagination = paginate(
            records, page=1, page_size=2, sort_key=stable_sort_key, list_id="things"
        )
        assert [r["id"] for r in page_items] == ["a", "b"]
        assert pagination["has_more"] is True
        assert pagination["list_id"] == "things"
        assert pagination["next_operation"] == "page_2"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_paginate_page_past_end_returns_empty_list(self):
        page_items, pagination = paginate([1, 2, 3], page=9, page_size=2)
        assert page_items == []
        assert pagination["page"] == 9
        assert pagination["has_more"] is False
        assert pagination["previous_operation"] == "page_2"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_paginate_clamps_page_size_to_max(self):
        page_items, pagination = paginate(list(range(20)), page="1", page_size=999, max_page_size=5)
        assert len(page_items) == 5
        assert pagination["page_size"] == 5
        assert pagination["total_pages"] == 4

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_paginate_empty_records(self):
        page_items, pagination = paginate([])
        assert page_items == []
        assert pagination["total_items"] == 0
        assert pagination["total_pages"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_stable_sort_key_object_prefers_first_non_none_attribute(self):
        assert stable_sort_key(_Obj(id=None, label="L")) == "L"
        assert stable_sort_key(_Obj(key=7)) == "7"
        assert stable_sort_key(_Obj(name="n", id=1)) == "1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_stable_sort_key_dict_falls_through_none_values(self):
        assert stable_sort_key({"id": None, "title": "T"}) == "T"
