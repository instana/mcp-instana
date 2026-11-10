"""
Unit tests for the Instana UI link helpers.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.core.ui_links import (
    add_application_link,
    add_service_link,
    add_synthetic_test_link,
    build_application_url,
    build_markdown_link,
    build_service_url,
    build_synthetic_test_url,
)

BASE = "https://test.instana.io"


class TestMarkdownLink(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(build_markdown_link("App", "https://x/y"), "[App](https://x/y)")

    def test_escapes_label_brackets_and_encodes_url_parens(self):
        link = build_markdown_link("a [b]", "https://x/y(1)")
        self.assertEqual(link, "[a \\[b\\]](https://x/y%281%29)")

    def test_empty_or_none_label_falls_back_to_url(self):
        self.assertEqual(build_markdown_link(None, "https://x/y"), "[https://x/y](https://x/y)")
        self.assertEqual(build_markdown_link("", "https://x/y"), "[https://x/y](https://x/y)")
        self.assertEqual(build_markdown_link("   ", "https://x/y"), "[https://x/y](https://x/y)")

    def test_escapes_backslashes_in_label(self):
        self.assertEqual(
            build_markdown_link("Domain\\User", "https://x/y"),
            "[Domain\\\\User](https://x/y)",
        )

    def test_encodes_spaces_in_url(self):
        self.assertEqual(
            build_markdown_link("My App", "https://x/y?a=b c"),
            "[My App](https://x/y?a=b%20c)",
        )


class TestApplicationLinks(unittest.TestCase):
    def test_application_url(self):
        self.assertEqual(
            build_application_url(BASE + "/", "app1"),
            f"{BASE}/#/application;appId=app1/summary;latencyTab=overTime",
        )

    def test_application_url_without_id(self):
        self.assertEqual(build_application_url(BASE, None), f"{BASE}/#/applications")

    def test_application_url_quotes_app_id(self):
        self.assertEqual(
            build_application_url(BASE, "app/1;test"),
            f"{BASE}/#/application;appId=app%2F1%3Btest/summary;latencyTab=overTime",
        )

    def test_base_url_none(self):
        self.assertEqual(
            build_application_url(None, "app1"),
            "/#/application;appId=app1/summary;latencyTab=overTime",
        )

    def test_add_application_link(self):
        app = {"id": "app1", "label": "My App"}
        add_application_link(BASE, app)
        self.assertEqual(app["url"], f"{BASE}/#/application;appId=app1/summary;latencyTab=overTime")
        self.assertEqual(app["link"], f"[My App]({app['url']})")

    def test_add_application_link_falls_back_to_id(self):
        app = {"id": "app1"}
        add_application_link(BASE, app)
        self.assertTrue(app["link"].startswith("[app1]("))


class TestServiceLinks(unittest.TestCase):
    def test_service_url(self):
        self.assertEqual(
            build_service_url(BASE, "app1", "svc1"),
            f"{BASE}/#/service;appId=app1;serviceId=svc1;boundaryScope=ALL/summary;latencyTab=overTime;callsTab=call",
        )

    def test_service_url_without_id(self):
        self.assertEqual(build_service_url(BASE, "app1", None), f"{BASE}/#/services")

    def test_global_service_url_without_app_id(self):
        self.assertEqual(
            build_service_url(BASE, None, "svc1"),
            f"{BASE}/#/service;serviceId=svc1;boundaryScope=ALL/summary;latencyTab=overTime;callsTab=call",
        )

    def test_service_url_quotes_ids(self):
        self.assertEqual(
            build_service_url(BASE, "app/1", "svc/1"),
            f"{BASE}/#/service;appId=app%2F1;serviceId=svc%2F1;boundaryScope=ALL/summary;latencyTab=overTime;callsTab=call",
        )

    def test_add_service_link(self):
        svc = {"id": "svc1", "label": "checkout"}
        add_service_link(BASE, "app1", svc)
        self.assertEqual(svc["link"], f"[checkout]({svc['url']})")

    def test_add_service_link_without_app_id(self):
        svc = {"id": "svc1", "label": "checkout"}
        add_service_link(BASE, None, svc)
        self.assertEqual(
            svc["url"],
            f"{BASE}/#/service;serviceId=svc1;boundaryScope=ALL/summary;latencyTab=overTime;callsTab=call",
        )
        self.assertEqual(svc["link"], f"[checkout]({svc['url']})")


class TestSyntheticTestLinks(unittest.TestCase):
    def test_url_contains_encoded_fields(self):
        test = {
            "id": "t1",
            "label": "/test path",
            "configuration": {"syntheticType": "APIScript"},
            "locations": ["loc a", "loc2"],
            "locationDisplayLabels": ["Loc A", "Loc 2"],
        }
        url = build_synthetic_test_url(BASE, test)
        self.assertTrue(url.startswith(f"{BASE}/#/synthetic;testId=t1;"))
        self.assertIn("testLabel=%2Ftest%20path;", url)
        self.assertIn("type=APIScript;", url)
        self.assertIn("locationDisplayLabels=Loc%20A%2CLoc%202;", url)
        self.assertIn("locationIds=loc%20a%2Cloc2;", url)
        self.assertTrue(url.endswith("runType=Scheduled;executionType=Scheduled/summary"))

    def test_defaults_when_fields_missing(self):
        url = build_synthetic_test_url(BASE, {"id": "t1", "label": "x", "configuration": None, "locations": None})
        self.assertIn("type=HTTPAction;", url)
        self.assertIn("locationIds=;", url)

    def test_handles_none_elements_in_locations_and_labels(self):
        test = {
            "id": "t1",
            "label": "test",
            "configuration": {"syntheticType": None},
            "locations": [None, "loc1", None],
            "locationDisplayLabels": [None, "Loc 1", None],
        }
        url = build_synthetic_test_url(BASE, test)
        self.assertIn("type=HTTPAction;", url)
        self.assertIn("locationIds=loc1;", url)
        self.assertIn("locationDisplayLabels=Loc%201;", url)

    def test_handles_missing_and_none_ids(self):
        url = build_synthetic_test_url(BASE, {"id": None, "label": None, "configuration": {}})
        self.assertIn("testId=;", url)
        self.assertIn("testLabel=;", url)
        self.assertIn("type=HTTPAction;", url)

    def test_add_synthetic_test_link_encodes_parens_in_link(self):
        test = {"id": "t1", "label": "Login (prod)"}
        add_synthetic_test_link(BASE, test)
        self.assertIn("(prod)", test["url"])
        self.assertIn("%28prod%29", test["link"])
        self.assertTrue(test["link"].startswith("[Login (prod)]("))


if __name__ == '__main__':
    unittest.main()
