"""Unit tests for the application-health MCP skill."""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

_SDK_STUBS = {
    "instana_client": MagicMock(),
    "instana_client.api": MagicMock(),
    "instana_client.api.events_api": MagicMock(),
    "instana_client.api.releases_api": MagicMock(),
    "instana_client.models": MagicMock(),
    "instana_client.models.release": MagicMock(),
    "instana_client.api_client": MagicMock(),
    "instana_client.configuration": MagicMock(),
}
for mod_name, stub in _SDK_STUBS.items():
    sys.modules.setdefault(mod_name, stub)

SKILLS_DIR = Path(__file__).parent.parent.parent / "src" / "skills"
SKILL_NAME = "application-health"
SKILL_MD = SKILLS_DIR / SKILL_NAME / "SKILL.md"

# Token-budget guard: the skill is loaded into context on every health query.
MAX_SKILL_CHARS = 6000


def _content() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


class TestSkillFile(unittest.TestCase):
    def test_exists(self):
        self.assertTrue(SKILL_MD.exists())

    def test_lightweight(self):
        self.assertLessEqual(len(_content()), MAX_SKILL_CHARS)

    def test_no_references_dir(self):
        self.assertFalse((SKILL_MD.parent / "references").exists())

    def test_frontmatter_name(self):
        self.assertIn(f"name: {SKILL_NAME}", _content().split("---", 2)[1])


class TestSkillProtocol(unittest.TestCase):
    def test_pins_metric_ids_and_group_tag(self):
        c = _content()
        for token in ("erroneousCalls", '"calls"', '"P95"', "application.name"):
            self.assertIn(token, c)

    def test_uses_required_operations(self):
        c = _content()
        self.assertIn('operation="get_grouped_calls_metrics"', c)
        self.assertIn('operation="get_events"', c)

    def test_queries_open_application_events_only(self):
        c = _content()
        self.assertIn('"entity_type":"APPLICATION"', c)
        self.assertNotIn('"entity_type":"SERVICE"', c)
        self.assertEqual(c.count('operation="get_events"'), 1)
        self.assertIn('"state":"open"', c)
        self.assertNotIn("max_events", c)

    def test_forbids_catalog_and_alert_config_calls(self):
        c = _content()
        for token in ("get_metric_catalog", "get_tag_catalog", "alert_config", "find_active"):
            self.assertIn(token, c)
        self.assertIn("Do NOT call", c)

    def test_unrated_apps_not_healthy(self):
        self.assertIn("never \"healthy\"", _content())

    def test_report_sections(self):
        c = _content()
        for section in ("Verdict", "Needs attention", "Elevated", "Healthy", "Coverage", "SLOs"):
            self.assertIn(section, c)

    def test_low_volume_never_healthy(self):
        c = _content()
        self.assertIn("Low volume", c)
        self.assertIn('never "healthy"', c)


class TestSkillVerdict(unittest.TestCase):
    def test_never_a_bare_no(self):
        c = _content()
        self.assertIn('never a bare "No"', c)
        # Old binary verdict must be gone.
        self.assertNotIn("Otherwise `No`", c)

    def test_graded_verdicts(self):
        c = _content()
        self.assertIn("Yes, all N rated applications are healthy", c)
        self.assertIn("Mostly healthy", c)
        self.assertIn("rated applications need attention", c)


class TestSkillSlo(unittest.TestCase):
    def test_queries_breaching_application_slos(self):
        c = _content()
        self.assertIn('manage_slo(resource_type="configuration", operation="get_all"', c)
        # The SLO API takes entity_type as a list and slo_status as an uppercase string.
        self.assertIn('"entity_type":["application"]', c)
        self.assertIn('"slo_status":"BREACHING"', c)

    def test_slo_affects_verdict(self):
        c = _content()
        self.assertIn("no breaching SLOs", c)
        self.assertIn("breaching SLO", c)

    def test_slo_report_section_and_empty_case(self):
        c = _content()
        self.assertIn("No application SLOs breaching", c)
        self.assertIn("entity.applicationId", c)


class TestSkillSynthetics(unittest.TestCase):
    def test_queries_synthetic_test_summary(self):
        c = _content()
        self.assertIn('manage_synthetics(resource_type="test_playback", operation="get_test_summary_list"', c)
        self.assertIn('"metric":"success_rate"', c)

    def test_synthetics_is_best_effort(self):
        c = _content()
        self.assertIn("Synthetic monitoring unavailable", c)
        self.assertIn("No synthetic tests failing", c)

    def test_failing_tests_affect_verdict(self):
        self.assertIn("failing test", _content())

    def test_links_call_is_after_synthetics_call(self):
        c = _content()
        self.assertIn("5. Links, after 1-4", c)
        self.assertIn("`_links.self` in a call 5 result", c)


class TestSkillLinks(unittest.TestCase):
    def test_single_lookup_call(self):
        c = _content()
        self.assertIn("5. Links, after 1-4, one call", c)
        self.assertNotIn("at most 3", c)
        self.assertEqual(c.count('operation="get_applications"'), 1)

    def test_resolves_id_with_filtered_lookup(self):
        c = _content()
        self.assertIn('operation="get_applications", params={"name_filter"', c)
        self.assertIn("without `name_filter`", c)

    def test_link_format(self):
        c = _content()
        self.assertIn(
            "<base>/#/application;appId=<id>/summary"
            "?timeline.to&timeline.fm&timeline.ar=true&timeline.ws=<ms>",
            c,
        )

    def test_reuses_ids_from_earlier_calls(self):
        c = _content()
        self.assertIn("entity.applicationId", c)
        self.assertIn("entity.label", c)
        self.assertIn("applicationIds", c)
        self.assertIn("applicationLabels", c)
        self.assertIn("Unknown id: plain text", c)

    def test_base_url_derived_not_hardcoded(self):
        c = _content()
        self.assertIn("_links.self", c)
        self.assertNotIn("instana.rocks", c)
        self.assertIn("Never guess a base or id", c)


class TestSkillsToolIntegration(unittest.TestCase):
    def test_discovered_and_loadable(self):
        from src.skills import skills_tool

        ids = [s["id"] for s in skills_tool._discover_skills()]
        self.assertIn(SKILL_NAME, ids)

        tool = skills_tool.SkillsMCPTool(read_token="t", base_url="https://x.instana.io")
        result = asyncio.run(tool.load_instana_skills(operation="get", name=SKILL_NAME))
        self.assertEqual(result["skill"], SKILL_NAME)
        self.assertEqual(result["references"], [])
        self.assertIn("Application Health", result["content"])


if __name__ == "__main__":
    unittest.main()
