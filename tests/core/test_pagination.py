"""
Tests for the shared, stateless pagination helpers (src/core/pagination.py) and a
cross-tool check that the list tools using them accept page_N / next / previous /
go_to_page and resolve them to the same destination page.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import src.core.pagination as pagination_module
from src.core.pagination import (
    add_navigation,
    build_pagination,
    operation_for_page,
    paginate,
    resolve_nav_page,
)
from src.router.application_smart_router_tool import ApplicationSmartRouterMCPTool
from src.router.custom_dashboard_smart_router_tool import (
    CustomDashboardSmartRouterMCPTool,
)
from src.router.releases_smart_router_tool import ReleasesSmartRouterMCPTool
from src.router.synthetic_smart_router_tool import SyntheticSmartRouterMCPTool


class TestResolveNavPage(unittest.TestCase):
    def test_page_n_embeds_the_number(self):
        self.assertEqual(resolve_nav_page("page_10", {}), 10)
        self.assertEqual(resolve_nav_page("PAGE_3", {}), 3)

    def test_next_and_previous_use_current_page(self):
        self.assertEqual(resolve_nav_page("next", {"page_number": 4}), 5)
        self.assertEqual(resolve_nav_page("next", {"page_number": "4"}), 5)
        self.assertEqual(resolve_nav_page("previous", {"page_number": 4}), 3)

    def test_page_param_is_accepted_as_current_page(self):
        self.assertEqual(resolve_nav_page("next", {"page": 4}), 5)

    def test_previous_never_goes_below_one(self):
        self.assertEqual(resolve_nav_page("previous", {"page_number": 1}), 1)

    def test_flat_page_number_is_accepted(self):
        self.assertEqual(resolve_nav_page("next", {}, page_number="7"), 8)

    def test_go_to_page_prefers_target_page(self):
        self.assertEqual(resolve_nav_page("go_to_page", {"target_page": 9, "page_number": 2}), 9)
        self.assertEqual(resolve_nav_page("go_to_page", {"page_number": 6}), 6)

    def test_missing_current_page_defaults_to_one(self):
        with patch.object(pagination_module.logger, "warning") as warn:
            self.assertEqual(resolve_nav_page("next", {}), 2)
        warn.assert_called_once()

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


def _run(coro):
    return asyncio.run(coro)


class TestPageNWorksOnEveryRouter(unittest.TestCase):
    """page_N / next / previous / go_to_page reach the data layer as the right page."""

    def _tool(self, cls):
        return cls("tok", "https://x.instana.io")

    def test_releases(self):
        router = self._tool(ReleasesSmartRouterMCPTool)
        asked = []

        async def fake(page_number=None, page_size=None, **kw):
            asked.append((page_number, page_size))
            return {"success": True}

        with patch.object(router.releases_client, "get_all_releases", new=AsyncMock(side_effect=fake)):
            _run(router.manage_releases("page_7"))
            _run(router.manage_releases("PAGE_3", {"page_size": 20}))
            _run(router.manage_releases("next", {"page_number": 4}))
            _run(router.manage_releases("previous", {"page_number": 4}))
            _run(router.manage_releases("go_to_page", {"page_number": 9}))
        self.assertEqual(asked, [(7, 50), (3, 20), (5, 50), (3, 50), (9, 50)])

    def test_custom_dashboards(self):
        router = self._tool(CustomDashboardSmartRouterMCPTool)
        asked = []

        async def fake(operation, params=None, **kw):
            asked.append((operation, params["page"], params["page_size"], params["with_total_hits"]))
            return {}

        with patch.object(router.dashboard_client, "execute_dashboard_operation", new=AsyncMock(side_effect=fake)):
            _run(router.manage_custom_dashboards("page_7"))
            _run(router.manage_custom_dashboards("next", {"page": 4, "page_size": 25}))
            _run(router.manage_custom_dashboards("previous", {"page": 4}))
            _run(router.manage_custom_dashboards("go_to_page", {"page": 9}))
        self.assertEqual(asked, [
            ("get_all", 7, 10, True),
            ("get_all", 5, 25, True),
            ("get_all", 3, 10, True),
            ("get_all", 9, 10, True),
        ])

    def test_synthetic_settings_and_alert(self):
        router = self._tool(SyntheticSmartRouterMCPTool)
        tests, alerts = [], []

        async def fake_tests(page=None, page_size=None, **kw):
            tests.append((page, page_size))
            return {"items": []}

        async def fake_alerts(page=None, page_size=None, **kw):
            alerts.append((page, page_size))
            return {"configs": []}

        with patch.object(router.synthetic_settings_client, "get_synthetic_tests", new=AsyncMock(side_effect=fake_tests)), \
             patch.object(router.synthetic_alert_client, "find_active_synthetic_alert_configs", new=AsyncMock(side_effect=fake_alerts)):
            _run(router.manage_synthetics("settings", "page_7"))
            _run(router.manage_synthetics("settings", "next", {"page": 4, "page_size": 20}))
            _run(router.manage_synthetics("alert", "page_3"))
            _run(router.manage_synthetics("alert", "previous", {"page": 4, "page_size": 20}))
        self.assertEqual(tests, [(7, 10), (5, 20)])
        self.assertEqual(alerts, [(3, None), (3, 20)])

    def test_application_alert_configs(self):
        router = self._tool(ApplicationSmartRouterMCPTool)
        seen = {"alert_config": [], "global_alert_config": []}

        def fake_for(kind):
            async def fake(operation, **kw):
                seen[kind].append((operation, kw.get("page"), kw.get("page_size")))
                return {}
            return AsyncMock(side_effect=fake)

        with patch.object(router.app_alert_config_client, "execute_alert_config_operation", new=fake_for("alert_config")), \
             patch.object(router.app_global_alert_config_client, "execute_alert_config_operation", new=fake_for("global_alert_config")):
            for rt in ("alert_config", "global_alert_config"):
                _run(router.manage_applications(rt, "page_7", {"application_id": "a1"}))
                _run(router.manage_applications(rt, "next", {"application_id": "a1", "page": 2, "page_size": 5}))
        for rt in seen:
            self.assertEqual(seen[rt], [("find_active", 7, None), ("find_active", 3, 5)])

    def test_application_settings_get_all_paginates_only_when_asked(self):
        router = self._tool(ApplicationSmartRouterMCPTool)
        items = [{"id": str(i)} for i in range(25)]
        with patch.object(router.app_settings_client, "execute_settings_operation", new=AsyncMock(return_value=items)):
            plain = _run(router.manage_applications(
                "settings", "get_all", {"resource_subtype": "application"}))
            self.assertEqual(len(plain["results"]), 25)
            self.assertNotIn("pagination", plain)

            page1 = _run(router.manage_applications(
                "settings", "get_all", {"resource_subtype": "application", "page_size": 10}))
            self.assertEqual(len(page1["results"]), 10)
            self.assertEqual(page1["pagination"]["next_operation"], "page_2")
            self.assertEqual(page1["pagination"]["list_id"], "application_settings")

            # Follow next_operation; the agent need not repeat resource_subtype / page_size.
            page3 = _run(router.manage_applications("settings", "page_3", {}))
            self.assertEqual([r["id"] for r in page3["results"]], [str(i) for i in range(20, 25)])
            self.assertIsNone(page3["pagination"]["next_operation"])
            self.assertEqual(page3["pagination"]["previous_operation"], "page_2")


if __name__ == "__main__":
    unittest.main()
