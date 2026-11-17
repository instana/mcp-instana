"""
Router-level tests for stateless pagination navigation (src/core/pagination.py).

Every list tool behind a smart router must resolve ``page_N`` / ``next`` / ``previous`` /
``go_to_page`` to the right page, forward the other params, rewrite the operation to the
tool's list operation, and answer an unresolvable request with an elicitation error
instead of guessing.
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.pagination import apply_navigation, paginate, resolve_nav_page
from src.router.application_smart_router_tool import ApplicationSmartRouterMCPTool
from src.router.custom_dashboard_smart_router_tool import (
    CustomDashboardSmartRouterMCPTool,
)
from src.router.releases_smart_router_tool import ReleasesSmartRouterMCPTool
from src.router.synthetic_smart_router_tool import SyntheticSmartRouterMCPTool


def _run(coro):
    return asyncio.run(coro)


def _tool(cls):
    return cls("tok", "https://x.instana.io")


class NavigationCases:
    """Shared assertions; subclasses provide ``call(operation, params)`` and ``pages_asked``."""

    def reset(self):
        self.asked = []

    def assert_pages(self, expected):
        self.assertEqual([entry[0] for entry in self.asked], expected)

    def test_page_n(self):
        self.call("page_2", {})
        self.call("PAGE_7", {})
        self.assert_pages([2, 7])

    def test_next_with_page_1(self):
        self.call("next", {"page": 1, "page_number": 1})
        self.assert_pages([2])

    def test_next_is_case_insensitive(self):
        self.call("Next", {"page": 1, "page_number": 1})
        self.assert_pages([2])

    def test_previous_with_page_3(self):
        self.call("previous", {"page": 3, "page_number": 3})
        self.assert_pages([2])

    def test_go_to_page(self):
        self.call("go_to_page", {"target_page": 9})
        self.assert_pages([9])

    def test_other_params_are_forwarded(self):
        self.call("page_3", self.extra_params())
        self.assertEqual(self.asked[0][1], self.expected_extra())

    def test_next_without_current_page_is_an_elicitation_error(self):
        result = self.call("next", {})
        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(result["reason"], "invalid_pagination")
        self.assertEqual(self.asked, [])

    def test_previous_on_first_page_is_an_elicitation_error(self):
        result = self.call("previous", {"page": 1, "page_number": 1})
        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(self.asked, [])

    def test_go_to_page_without_a_valid_target_is_an_elicitation_error(self):
        for params in ({}, {"target_page": "abc"}):
            result = self.call("go_to_page", params)
            self.assertTrue(result["elicitation_needed"])
        self.assertEqual(self.asked, [])

    def test_absurd_page_is_an_elicitation_error(self):
        result = self.call("page_99999999999999999999", {})
        self.assertTrue(result["elicitation_needed"])
        self.assertEqual(self.asked, [])


class TestReleasesNavigation(NavigationCases, unittest.TestCase):
    def setUp(self):
        self.reset()
        self.router = _tool(ReleasesSmartRouterMCPTool)

        async def fake(page_number=None, page_size=None, name_filter=None, **kw):
            self.asked.append((page_number, {"page_size": page_size, "name_filter": name_filter}))
            return {"success": True}

        patcher = patch.object(
            self.router.releases_client, "get_all_releases", new=AsyncMock(side_effect=fake)
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, operation, params):
        return _run(self.router.manage_releases(operation, dict(params)))

    def extra_params(self):
        return {"page_size": 20, "name_filter": "rel"}

    def expected_extra(self):
        return {"page_size": 20, "name_filter": "rel"}

    def test_page_and_page_number_are_interchangeable(self):
        self.call("get_all_releases", {"page": 3, "page_size": 5})
        self.call("get_all_releases", {"page_number": 4, "page_size": 5})
        self.assert_pages([3, 4])

    def test_get_all_without_paging_passes_nothing(self):
        self.call("get_all_releases", {})
        self.assertEqual(self.asked, [(None, {"page_size": None, "name_filter": None})])


class TestCustomDashboardNavigation(NavigationCases, unittest.TestCase):
    def setUp(self):
        self.reset()
        self.router = _tool(CustomDashboardSmartRouterMCPTool)

        async def fake(operation, params=None, **kw):
            self.asked.append((params.get("page"), {"operation": operation, "query": params.get("query"),
                                                    "with_total_hits": params.get("with_total_hits")}))
            return {}

        patcher = patch.object(
            self.router.dashboard_client, "execute_dashboard_operation", new=AsyncMock(side_effect=fake)
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, operation, params):
        return _run(self.router.manage_custom_dashboards(operation, dict(params)))

    def extra_params(self):
        return {"query": "prod"}

    def expected_extra(self):
        return {"operation": "get_all", "query": "prod", "with_total_hits": True}

    def test_get_all_without_paging_leaves_api_defaults(self):
        self.call("get_all", {})
        self.assertEqual(self.asked, [(None, {"operation": "get_all", "query": None, "with_total_hits": None})])


class TestSyntheticSettingsNavigation(NavigationCases, unittest.TestCase):
    def setUp(self):
        self.reset()
        self.router = _tool(SyntheticSmartRouterMCPTool)

        async def fake(page=None, page_size=None, application_id=None, **kw):
            self.asked.append((page, {"application_id": application_id}))
            return {"items": []}

        patcher = patch.object(
            self.router.synthetic_settings_client, "get_synthetic_tests", new=AsyncMock(side_effect=fake)
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, operation, params):
        return _run(self.router.manage_synthetics("settings", operation, dict(params)))

    def extra_params(self):
        return {"application_id": "app-1"}

    def expected_extra(self):
        return {"application_id": "app-1"}

    def test_get_synthetic_tests_without_paging_is_not_paged(self):
        self.call("get_synthetic_tests", {})
        self.assertEqual(self.asked, [(None, {"application_id": None})])


class TestSyntheticAlertNavigation(NavigationCases, unittest.TestCase):
    def setUp(self):
        self.reset()
        self.router = _tool(SyntheticSmartRouterMCPTool)

        async def fake(page=None, page_size=None, synthetic_test_id=None, **kw):
            self.asked.append((page, {"synthetic_test_id": synthetic_test_id}))
            return {"configs": []}

        patcher = patch.object(
            self.router.synthetic_alert_client, "find_active_synthetic_alert_configs",
            new=AsyncMock(side_effect=fake),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, operation, params):
        return _run(self.router.manage_synthetics("alert", operation, dict(params)))

    def extra_params(self):
        return {"synthetic_test_id": "t-1"}

    def expected_extra(self):
        return {"synthetic_test_id": "t-1"}


class _ApplicationAlertNavigation(NavigationCases):
    resource_type = ""
    client_attr = ""

    def setUp(self):
        self.reset()
        self.router = _tool(ApplicationSmartRouterMCPTool)

        async def fake(operation, application_id=None, page=None, page_size=None, **kw):
            self.asked.append((page, {"operation": operation, "application_id": application_id}))
            return {}

        patcher = patch.object(
            getattr(self.router, self.client_attr), "execute_alert_config_operation",
            new=AsyncMock(side_effect=fake),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, operation, params):
        return _run(self.router.manage_applications(
            self.resource_type, operation, {"application_id": "a1", **params}))

    def extra_params(self):
        return {}

    def expected_extra(self):
        return {"operation": "find_active", "application_id": "a1"}


class TestApplicationAlertConfigNavigation(_ApplicationAlertNavigation, unittest.TestCase):
    resource_type = "alert_config"
    client_attr = "app_alert_config_client"


class TestApplicationGlobalAlertConfigNavigation(_ApplicationAlertNavigation, unittest.TestCase):
    resource_type = "global_alert_config"
    client_attr = "app_global_alert_config_client"


class TestApplicationSettingsNavigation(NavigationCases, unittest.TestCase):
    def setUp(self):
        self.reset()
        self.router = _tool(ApplicationSmartRouterMCPTool)
        self.items = [{"id": f"{i:02d}"} for i in range(25)]
        patcher = patch.object(
            self.router.app_settings_client, "execute_settings_operation",
            new=AsyncMock(return_value=self.items),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def call(self, operation, params):
        result = _run(self.router.manage_applications(
            "settings", operation, {"resource_subtype": "application", **params}))
        if "pagination" in result:
            self.asked.append((result["pagination"]["page"], params))
        return result

    def extra_params(self):
        return {"page_size": 5}

    def expected_extra(self):
        return {"page_size": 5}

    def test_get_all_without_paging_returns_everything(self):
        result = _run(self.router.manage_applications(
            "settings", "get_all", {"resource_subtype": "application"}))
        self.assertEqual(len(result["results"]), 25)
        self.assertNotIn("pagination", result)

    def test_page_n_slices_and_links_onward(self):
        page3 = _run(self.router.manage_applications("settings", "page_3", {"page_size": 10}))
        self.assertEqual([r["id"] for r in page3["results"]], [f"{i:02d}" for i in range(20, 25)])
        self.assertIsNone(page3["pagination"]["next_operation"])
        self.assertEqual(page3["pagination"]["previous_operation"], "page_2")
        self.assertEqual(page3["pagination"]["list_id"], "application_settings")


if __name__ == "__main__":
    unittest.main()


class TestEndToEndNavigationFlow(unittest.TestCase):
    """
    Follow ``pagination.next_operation`` from each real tool response back through the
    router's navigation rewriting until it is ``None``: the pages must tile the data exactly
    (no gaps, no repeats), and ``previous_operation`` must walk back the same way.
    """

    TOTAL = 23
    PAGE_SIZE = 5

    def _api_client(self, payload):
        response = MagicMock()
        response.status = 200
        response.data = json.dumps(payload).encode("utf-8")
        response.headers = {"Content-Type": "application/json"}
        client = MagicMock()
        client.get_all_releases_without_preload_content = MagicMock(return_value=response)
        return client

    def test_releases_pages_tile_the_data(self):
        client = _tool(ReleasesSmartRouterMCPTool).releases_client
        releases = [{"id": f"r{i:03d}", "name": f"rel-{i}"} for i in range(self.TOTAL)]
        api = self._api_client(releases)

        # Other test modules swap with_header_auth for a mock at import time, so pin the
        # API client on the instance and call through whichever wrapper is in place.
        client.releases_api = api

        def fetch(page):
            return _run(client.get_all_releases(
                page_number=page, page_size=self.PAGE_SIZE, api_client=api))

        seen, result = [], fetch(1)
        for _ in range(50):  # hard stop: a broken envelope must not loop forever
            self.assertTrue(result["success"])
            seen.extend(result["releases"])
            op = result["pagination"]["next_operation"]
            if op is None:
                break
            operation, params, error = apply_navigation(
                op, {"page_size": self.PAGE_SIZE}, "get_all_releases", page_key="page_number")
            self.assertIsNone(error)
            self.assertEqual(operation, "get_all_releases")
            result = fetch(params["page_number"])
        else:
            self.fail("next_operation never became None")

        self.assertEqual([r["id"] for r in seen], [r["id"] for r in releases])
        self.assertEqual(result["pagination"]["page"], 5)
        self.assertEqual(result["pagination"]["total_pages"], 5)

    def test_previous_operation_walks_back_to_page_one(self):
        records = [{"id": f"{i:03d}"} for i in range(self.TOTAL)]
        _, envelope = paginate(records, page=5, page_size=self.PAGE_SIZE)
        visited = [envelope["page"]]
        while envelope["previous_operation"] is not None:
            page = resolve_nav_page(envelope["previous_operation"], {})
            _, envelope = paginate(records, page=page, page_size=self.PAGE_SIZE)
            visited.append(envelope["page"])
        self.assertEqual(visited, [5, 4, 3, 2, 1])
