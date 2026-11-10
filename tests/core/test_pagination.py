"""
Tests for the shared, stateless pagination helpers (src/core/pagination.py).
Router-level navigation tests live in tests/router/test_pagination_navigation.py.
"""

import unittest

from src.core.pagination import (
    NavigationError,
    add_navigation,
    apply_navigation,
    build_pagination,
    coerce_int,
    normalize_page_args,
    operation_for_page,
    page_kwargs,
    paginate,
    resolve_nav_page,
    stable_sort_key,
)


class TestResolveNavPage(unittest.TestCase):
    def test_page_n_embeds_the_number(self):
        self.assertEqual(resolve_nav_page("page_10", {}), 10)
        self.assertEqual(resolve_nav_page("PAGE_3", {}), 3)
        self.assertEqual(resolve_nav_page("  Page_2 ", {}), 2)

    def test_next_and_previous_use_current_page(self):
        self.assertEqual(resolve_nav_page("next", {"page_number": 4}), 5)
        self.assertEqual(resolve_nav_page("next", {"page_number": "4"}), 5)
        self.assertEqual(resolve_nav_page("previous", {"page_number": 4}), 3)

    def test_operations_are_case_insensitive(self):
        self.assertEqual(resolve_nav_page("Next", {"page": 1}), 2)
        self.assertEqual(resolve_nav_page(" PREVIOUS ", {"page": 3}), 2)
        self.assertEqual(resolve_nav_page("Go_To_Page", {"target_page": 6}), 6)

    def test_page_param_is_accepted_as_current_page(self):
        self.assertEqual(resolve_nav_page("next", {"page": 4}), 5)

    def test_flat_page_number_is_accepted(self):
        self.assertEqual(resolve_nav_page("next", {}, page_number="7"), 8)

    def test_next_and_previous_without_current_page_are_errors(self):
        for op in ("next", "previous"):
            with self.assertRaises(NavigationError):
                resolve_nav_page(op, {})

    def test_previous_on_first_page_is_an_error(self):
        with self.assertRaises(NavigationError):
            resolve_nav_page("previous", {"page_number": 1})

    def test_invalid_current_page_is_an_error(self):
        with self.assertRaises(NavigationError):
            resolve_nav_page("next", {"page": "abc"})
        with self.assertRaises(NavigationError):
            resolve_nav_page("next", {"page": 0})

    def test_go_to_page_requires_a_valid_target(self):
        self.assertEqual(resolve_nav_page("go_to_page", {"target_page": "9"}), 9)
        for params in ({}, {"target_page": "abc"}, {"target_page": 0}, {"target_page": ""}):
            with self.assertRaises(NavigationError):
                resolve_nav_page("go_to_page", params)

    def test_go_to_page_does_not_fall_back_to_the_current_page(self):
        with self.assertRaises(NavigationError):
            resolve_nav_page("go_to_page", {"page_number": 6})

    def test_absurd_page_numbers_are_rejected(self):
        with self.assertRaises(NavigationError):
            resolve_nav_page("page_99999999999999999999", {})
        with self.assertRaises(NavigationError):
            resolve_nav_page("page_0", {})

    def test_non_navigation_operation_returns_none(self):
        self.assertIsNone(resolve_nav_page("get_all", {}))
        self.assertIsNone(resolve_nav_page("find_active", {}))
        self.assertIsNone(resolve_nav_page(None, {}))
        self.assertIsNone(resolve_nav_page("page_x", {}))


class TestAddNavigation(unittest.TestCase):
    def test_first_page(self):
        meta = add_navigation({"page": 1, "has_more": True})
        self.assertEqual(meta["next_operation"], "page_2")
        self.assertIsNone(meta["previous_operation"])

    def test_middle_page(self):
        meta = add_navigation({"page": 5, "has_more": True})
        self.assertEqual(meta["next_operation"], "page_6")
        self.assertEqual(meta["previous_operation"], "page_4")

    def test_last_page(self):
        meta = add_navigation({"page": 10, "has_more": False})
        self.assertIsNone(meta["next_operation"])
        self.assertEqual(meta["previous_operation"], "page_9")

    def test_operation_for_page_round_trips_through_resolver(self):
        self.assertEqual(resolve_nav_page(operation_for_page(7), {}), 7)

    def test_non_dict_is_returned_untouched(self):
        self.assertIsNone(add_navigation(None))


class TestPaginate(unittest.TestCase):
    def setUp(self):
        self.records = [{"id": f"{i:03d}"} for i in range(25)]

    def test_slices_and_builds_envelope(self):
        page, meta = paginate(self.records, page=2, page_size=10, list_id="things")
        self.assertEqual([r["id"] for r in page], [f"{i:03d}" for i in range(10, 20)])
        self.assertEqual(meta["page"], 2)
        self.assertEqual(meta["page_size"], 10)
        self.assertEqual(meta["total_items"], 25)
        self.assertEqual(meta["total_pages"], 3)
        self.assertTrue(meta["has_more"])
        self.assertTrue(meta["has_previous"])
        self.assertEqual(meta["next_operation"], "page_3")
        self.assertEqual(meta["previous_operation"], "page_1")
        self.assertEqual(meta["list_id"], "things")

    def test_last_partial_page(self):
        page, meta = paginate(self.records, page=3, page_size=10)
        self.assertEqual(len(page), 5)
        self.assertFalse(meta["has_more"])
        self.assertIsNone(meta["next_operation"])
        self.assertNotIn("list_id", meta)

    def test_accepts_strings_and_falls_back_on_garbage(self):
        page, meta = paginate(self.records, page="2", page_size="10")
        self.assertEqual((meta["page"], len(page)), (2, 10))
        page, meta = paginate(self.records, page="nope", page_size="nope")
        self.assertEqual((meta["page"], meta["page_size"], len(page)), (1, 10, 10))

    def test_page_size_is_clamped(self):
        _, meta = paginate(self.records, page_size=5000, max_page_size=20)
        self.assertEqual(meta["page_size"], 20)
        _, meta = paginate(self.records, page_size=0)
        self.assertEqual(meta["page_size"], 1)

    def test_page_past_the_end_is_empty_not_a_different_page(self):
        page, meta = paginate(self.records, page=99, page_size=10)
        self.assertEqual(page, [])
        self.assertEqual(meta["page"], 99)
        self.assertFalse(meta["has_more"])

    def test_empty_list(self):
        page, meta = paginate([], page=1)
        self.assertEqual(page, [])
        self.assertEqual((meta["total_items"], meta["total_pages"]), (0, 1))
        self.assertFalse(meta["has_more"])
        self.assertFalse(meta["has_previous"])

    def test_sort_key_makes_pages_independent_of_fetch_order(self):
        shuffled = list(reversed(self.records))
        page, _ = paginate(shuffled, page=1, page_size=3, sort_key=lambda r: r["id"])
        self.assertEqual([r["id"] for r in page], ["000", "001", "002"])
        self.assertEqual(shuffled[0]["id"], "024")  # input not mutated

    def test_no_item_is_skipped_or_repeated_across_pages(self):
        seen = []
        meta = {"next_operation": "page_1"}
        while meta["next_operation"]:
            page_no = resolve_nav_page(meta["next_operation"], {})
            page, meta = paginate(self.records, page=page_no, page_size=7)
            seen += [r["id"] for r in page]
        self.assertEqual(seen, [r["id"] for r in self.records])


class TestBuildPagination(unittest.TestCase):
    def test_for_sources_that_already_returned_one_page(self):
        meta = build_pagination(page=4, page_size=10, total_items=95, list_id="x")
        self.assertEqual(meta["total_pages"], 10)
        self.assertEqual(meta["next_operation"], "page_5")
        self.assertEqual(meta["previous_operation"], "page_3")

    def test_bad_values_are_sanitised(self):
        meta = build_pagination(page=None, page_size="x", total_items="x")
        self.assertEqual((meta["page"], meta["page_size"], meta["total_items"]), (1, 10, 0))


class TestPaginateStableSorting(unittest.TestCase):
    def test_paginate_stable_sorting(self):
        """paginate with stable_sort_key sorts records to prevent skipping/duplicating items."""
        unsorted_items = [{"id": "b"}, {"id": "c"}, {"id": "a"}]
        page, _ = paginate(unsorted_items, page=1, page_size=2, sort_key=stable_sort_key)
        self.assertEqual([item["id"] for item in page], ["a", "b"])


class TestArgumentHelpers(unittest.TestCase):
    def test_coerce_int(self):
        self.assertEqual(coerce_int("7", 1), 7)
        self.assertEqual(coerce_int(7, 1), 7)
        self.assertEqual(coerce_int(None, 3), 3)
        self.assertEqual(coerce_int("", 3), 3)
        self.assertEqual(coerce_int("abc", 3), 3)

    def test_normalize_page_args(self):
        self.assertEqual(normalize_page_args(None, None), (1, 10))
        self.assertEqual(normalize_page_args("2", "25"), (2, 25))
        self.assertEqual(normalize_page_args(0, 0), (1, 1))
        self.assertEqual(normalize_page_args("abc", "abc", default_size=20), (1, 20))
        self.assertEqual(normalize_page_args(1, 5000, max_size=100), (1, 100))

    def test_page_kwargs_keeps_only_supplied_values(self):
        self.assertEqual(page_kwargs({}), {})
        self.assertEqual(page_kwargs({"page": 0, "page_size": None, "x": 1}), {"page": 0})
        self.assertEqual(page_kwargs({"page": 2, "page_size": 5}), {"page": 2, "page_size": 5})


class TestApplyNavigation(unittest.TestCase):
    def test_non_navigation_is_untouched(self):
        params = {"a": 1}
        self.assertEqual(apply_navigation("find_active", params, "find_active"),
                         ("find_active", params, None))

    def test_navigation_is_rewritten(self):
        op, params, err = apply_navigation("page_4", {"a": 1}, "get_all", page_key="page_number")
        self.assertEqual((op, params, err), ("get_all", {"a": 1, "page_number": 4}, None))

    def test_unresolvable_navigation_returns_elicitation_error(self):
        op, params, err = apply_navigation("next", {}, "get_all")
        self.assertEqual(op, "next")
        self.assertTrue(err["elicitation_needed"])
        self.assertEqual(err["reason"], "invalid_pagination")


if __name__ == "__main__":
    unittest.main()
