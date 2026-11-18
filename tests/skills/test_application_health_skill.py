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
FLEET_MD = SKILLS_DIR / SKILL_NAME / "references" / "all-applications-query.md"
SINGLE_MD = SKILLS_DIR / SKILL_NAME / "references" / "application-query.md"

# Token-budget guard: the skill is loaded into context on every health query.
MAX_SKILL_CHARS = 6000
# Each reference is loaded on demand, one per query.
MAX_REFERENCE_CHARS = 6000


def _content() -> str:
    """SKILL.md (the router)."""
    return SKILL_MD.read_text(encoding="utf-8")


def _fleet() -> str:
    """references/all-applications-query.md (all applications)."""
    return FLEET_MD.read_text(encoding="utf-8")


def _single() -> str:
    """references/application-query.md (one application)."""
    return SINGLE_MD.read_text(encoding="utf-8")


class TestSkillFile(unittest.TestCase):
    def test_exists(self):
        self.assertTrue(SKILL_MD.exists())

    def test_lightweight(self):
        self.assertLessEqual(len(_content()), MAX_SKILL_CHARS)

    def test_references_exist(self):
        self.assertTrue((SKILL_MD.parent / "references").is_dir())
        self.assertTrue(FLEET_MD.is_file())
        self.assertTrue(SINGLE_MD.is_file())

    def test_references_lightweight(self):
        self.assertLessEqual(len(_fleet()), MAX_REFERENCE_CHARS)
        self.assertLessEqual(len(_single()), MAX_REFERENCE_CHARS)

    def test_frontmatter_name(self):
        self.assertIn(f"name: {SKILL_NAME}", _content().split("---", 2)[1])


class TestSkillRouter(unittest.TestCase):
    def test_mentions_both_references(self):
        c = _content()
        self.assertIn("application-query.md", c)
        self.assertIn("all-applications-query.md", c)

    def test_has_get_reference_gate(self):
        c = _content()
        self.assertIn('operation="get_reference"', c)
        self.assertIn('name="application-health"', c)

    def test_asks_user_when_unclear(self):
        c = _content()
        self.assertIn("unclear", c.lower())
        self.assertIn("ask the user", c)

    def test_description_covers_single_application(self):
        frontmatter = _content().split("---", 2)[1]
        self.assertNotIn("NOT for one named application", frontmatter)

    def test_frontmatter_version(self):
        self.assertIn("version: 2.0.0", _content().split("---", 2)[1])

    def test_frontmatter_lists_references(self):
        frontmatter = _content().split("---", 2)[1]
        self.assertIn("references:", frontmatter)
        self.assertIn("  - application-query.md", frontmatter)
        self.assertIn("\n  - all-applications-query.md\n", frontmatter)


class TestSingleApplicationReference(unittest.TestCase):
    def test_resolves_with_name_filter_only(self):
        c = _single()
        calls = [line for line in c.splitlines() if 'operation="get_applications"' in line]
        self.assertGreaterEqual(len(calls), 1)
        for line in calls:
            self.assertIn('"name_filter"', line)
        self.assertIn("never call `get_applications` without `name_filter`", c)

    def test_id_path_uses_settings_get(self):
        c = _single()
        self.assertIn('resource_type="settings", operation="get"', c)
        self.assertIn('"resource_subtype":"application"', c)

    def test_events_call_scoped_and_post_filtered(self):
        c = _single()
        self.assertEqual(c.count('operation="get_events"'), 1)
        self.assertIn('"entity_type":"APPLICATION"', c)
        self.assertIn('"state":"open"', c)
        self.assertIn("entity.applicationId", c)
        self.assertNotIn("max_events", c)

    def test_application_and_service_groupings(self):
        c = _single()
        self.assertIn('"groupbyTag":"application.name"', c)
        self.assertIn('"groupbyTag":"service.name"', c)

    def test_slo_call_scoped_to_application(self):
        c = _single()
        self.assertIn('"entity_ids":["<id>"]', c)
        self.assertIn('"entity_type":["application"]', c)
        self.assertIn('"slo_status":"BREACHING"', c)

    def test_synthetic_call_scoped_to_application(self):
        c = _single()
        self.assertIn("synthetic.applicationId", c)
        self.assertIn("TagFilterExpression", c)
        self.assertIn("Synthetic monitoring unavailable", c)
        self.assertIn("No synthetic tests failing", c)

    def test_resolve_rules(self):
        c = _single()
        self.assertIn("Exact case-insensitive `label` match wins", c)
        self.assertIn("ask user to pick", c)
        self.assertIn("No match or error: stop. Run NO data calls.", c)

    def test_report_table_and_link_template(self):
        c = _single()
        self.assertIn("Service | Calls | Error rate | P95", c)
        self.assertIn(
            "<base>/#/application;appId=<id>/summary"
            "?timeline.to&timeline.fm&timeline.ar=true&timeline.ws=<ms>",
            c,
        )

    def test_forbids_catalog_and_alert_config_calls(self):
        c = _single()
        for token in ("get_metric_catalog", "get_tag_catalog", "alert_config", "find_active"):
            self.assertIn(token, c)
        self.assertIn("Do NOT call", c)

    def test_unrated_never_healthy(self):
        c = _single()
        self.assertIn('never "healthy"', c)
        self.assertIn("No calls in window", c)


class TestSkillProtocol(unittest.TestCase):
    def test_pins_metric_ids_and_group_tag(self):
        c = _fleet()
        for token in ("erroneousCalls", '"calls"', '"P95"', "application.name"):
            self.assertIn(token, c)

    def test_uses_required_operations(self):
        c = _fleet()
        self.assertIn('operation="get_grouped_calls_metrics"', c)
        self.assertIn('operation="get_events"', c)

    def test_queries_open_application_events_only(self):
        c = _fleet()
        self.assertIn('"entity_type":"APPLICATION"', c)
        self.assertNotIn('"entity_type":"SERVICE"', c)
        self.assertEqual(c.count('operation="get_events"'), 1)
        self.assertIn('"state":"open"', c)
        self.assertNotIn("max_events", c)

    def test_forbids_catalog_and_alert_config_calls(self):
        c = _fleet()
        for token in ("get_metric_catalog", "get_tag_catalog", "alert_config", "find_active"):
            self.assertIn(token, c)
        self.assertIn("Do NOT call", c)

    def test_unrated_apps_not_healthy(self):
        self.assertIn("never \"healthy\"", _fleet())

    def test_report_sections(self):
        c = _fleet()
        for section in ("Verdict", "Needs attention", "Elevated", "Healthy", "Coverage", "SLOs"):
            self.assertIn(section, c)

    def test_low_volume_never_healthy(self):
        c = _fleet()
        self.assertIn("Low volume", c)
        self.assertIn('never "healthy"', c)


class TestSkillVerdict(unittest.TestCase):
    def test_never_a_bare_no(self):
        c = _fleet()
        self.assertIn('never a bare "No"', c)
        # Old binary verdict must be gone.
        self.assertNotIn("Otherwise `No`", c)

    def test_graded_verdicts(self):
        c = _fleet()
        self.assertIn("Yes, all N rated applications are healthy", c)
        self.assertIn("Mostly healthy", c)
        self.assertIn("rated applications need attention", c)


class TestSkillSlo(unittest.TestCase):
    def test_queries_breaching_application_slos(self):
        c = _fleet()
        self.assertIn('manage_slo(resource_type="configuration", operation="get_all"', c)
        # The SLO API takes entity_type as a list and slo_status as an uppercase string.
        self.assertIn('"entity_type":["application"]', c)
        self.assertIn('"slo_status":"BREACHING"', c)

    def test_slo_affects_verdict(self):
        c = _fleet()
        self.assertIn("no breaching SLOs", c)
        self.assertIn("breaching SLO", c)

    def test_slo_report_section_and_empty_case(self):
        c = _fleet()
        self.assertIn("No application SLOs breaching", c)
        self.assertIn("entity.applicationId", c)


class TestSkillSynthetics(unittest.TestCase):
    def test_queries_synthetic_test_summary(self):
        c = _fleet()
        self.assertIn('manage_synthetics(resource_type="test_playback", operation="get_test_summary_list"', c)
        self.assertIn('"metric":"success_rate"', c)

    def test_synthetics_is_best_effort(self):
        c = _fleet()
        self.assertIn("Synthetic monitoring unavailable", c)
        self.assertIn("No synthetic tests failing", c)

    def test_failing_tests_affect_verdict(self):
        self.assertIn("failing test", _fleet())

    def test_links_call_is_after_synthetics_call(self):
        c = _fleet()
        self.assertIn("5. Links, after 1-4", c)
        self.assertIn("`_links.self` in a call 5 result", c)


class TestSkillLinks(unittest.TestCase):
    def test_single_lookup_call(self):
        c = _fleet()
        self.assertIn("5. Links, after 1-4, one call", c)
        self.assertNotIn("at most 3", c)
        self.assertEqual(c.count('operation="get_applications"'), 1)

    def test_resolves_id_with_filtered_lookup(self):
        c = _fleet()
        self.assertIn('operation="get_applications", params={"name_filter"', c)
        self.assertIn("without `name_filter`", c)

    def test_link_format(self):
        c = _fleet()
        self.assertIn(
            "<base>/#/application;appId=<id>/summary"
            "?timeline.to&timeline.fm&timeline.ar=true&timeline.ws=<ms>",
            c,
        )

    def test_reuses_ids_from_earlier_calls(self):
        c = _fleet()
        self.assertIn("entity.applicationId", c)
        self.assertIn("entity.label", c)
        self.assertIn("applicationIds", c)
        self.assertIn("applicationLabels", c)
        self.assertIn("Unknown id: plain text", c)

    def test_base_url_derived_not_hardcoded(self):
        c = _fleet()
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
        self.assertEqual(result["references"], ["all-applications-query.md", "application-query.md"])
        self.assertIn("Application Health", result["content"])

    def test_get_reference_returns_each_file(self):
        from src.skills import skills_tool

        tool = skills_tool.SkillsMCPTool(read_token="t", base_url="https://x.instana.io")
        for path, expected in (
            ("application-query.md", _single()),
            ("all-applications-query.md", _fleet()),
        ):
            result = asyncio.run(
                tool.load_instana_skills(operation="get_reference", name=SKILL_NAME, path=path)
            )
            self.assertEqual(result["skill"], SKILL_NAME)
            self.assertEqual(result["reference"], path)
            self.assertEqual(result["content"], expected)


if __name__ == "__main__":
    unittest.main()
