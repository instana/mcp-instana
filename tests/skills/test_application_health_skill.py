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
MAX_SKILL_CHARS = 4500


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

    def test_queries_open_application_and_service_events(self):
        c = _content()
        self.assertIn('"entity_type":"APPLICATION"', c)
        self.assertIn('"entity_type":"SERVICE"', c)
        self.assertIn('"state":"open"', c)

    def test_forbids_catalog_and_alert_config_calls(self):
        c = _content()
        for token in ("get_metric_catalog", "get_tag_catalog", "alert_config", "find_active"):
            self.assertIn(token, c)
        self.assertIn("Do NOT call", c)

    def test_unrated_apps_not_healthy(self):
        self.assertIn("never \"healthy\"", _content())

    def test_report_sections(self):
        c = _content()
        for section in ("Verdict", "Needs attention", "Elevated", "Healthy", "Coverage"):
            self.assertIn(section, c)


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
