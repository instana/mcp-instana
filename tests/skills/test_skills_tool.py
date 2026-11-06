"""Unit tests for SkillsMCPTool (src/skills/skills_tool.py)."""

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# ---------------------------------------------------------------------------
# SDK stubs (needed when fastmcp / server.py loads indirectly)
# ---------------------------------------------------------------------------
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

# Paths
SKILLS_DIR = Path(__file__).parent.parent.parent / "src" / "skills"
SKILL_MD_PATH = SKILLS_DIR / "change-timeline" / "SKILL.md"


class TestSkillsToolLoadSuccess(unittest.TestCase):
    """Test that load_instana_skills returns correct content for known skills."""

    def setUp(self):
        from src.skills.skills_tool import SkillsMCPTool
        self.tool = SkillsMCPTool(read_token="test-token", base_url="https://example.com")

    def _run(self, coro):
        return asyncio.run(coro)

    def test_returns_dict_with_skill_and_content_keys(self):
        result = self._run(self.tool.load_instana_skills("get", "change-timeline"))
        self.assertIsInstance(result, dict)
        self.assertIn("skill", result)
        self.assertIn("content", result)

    def test_skill_key_equals_name(self):
        result = self._run(self.tool.load_instana_skills("get", "change-timeline"))
        self.assertEqual(result["skill"], "change-timeline")

    def test_content_is_non_empty(self):
        result = self._run(self.tool.load_instana_skills("get", "change-timeline"))
        self.assertIsInstance(result["content"], str)
        self.assertGreater(len(result["content"]), 0)

    def test_content_matches_skill_md_exactly(self):
        """Byte-identity invariant: content == open(SKILL.md).read()."""
        expected = SKILL_MD_PATH.read_text(encoding="utf-8")
        result = self._run(self.tool.load_instana_skills("get", "change-timeline"))
        self.assertEqual(result["content"], expected)


class TestSkillsToolLoadUnknown(unittest.TestCase):
    """Test that load_instana_skills returns a clear error for unknown skill names."""

    def setUp(self):
        from src.skills.skills_tool import SkillsMCPTool
        self.tool = SkillsMCPTool(read_token="test-token", base_url="https://example.com")

    def _run(self, coro):
        return asyncio.run(coro)

    def test_unknown_skill_returns_error_dict(self):
        result = self._run(self.tool.load_instana_skills("get", "nonexistent-skill"))
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        self.assertIn("available", result)

    def test_unknown_skill_error_message_contains_name(self):
        result = self._run(self.tool.load_instana_skills("get", "nonexistent-skill"))
        self.assertIn("nonexistent-skill", result["error"])

    def test_unknown_skill_available_list_contains_change_timeline(self):
        result = self._run(self.tool.load_instana_skills("get", "nonexistent-skill"))
        self.assertIsInstance(result["available"], list)
        self.assertIn("change-timeline", result["available"])

    def test_no_skill_key_in_error_response(self):
        result = self._run(self.tool.load_instana_skills("get", "nonexistent-skill"))
        self.assertNotIn("content", result)


class TestSkillsToolList(unittest.TestCase):
    """Test operation="list"."""

    def setUp(self):
        from src.skills.skills_tool import SkillsMCPTool
        self.tool = SkillsMCPTool(read_token="test-token", base_url="https://example.com")

    def _run(self, coro):
        return asyncio.run(coro)

    def test_list_returns_skills_list(self):
        result = self._run(self.tool.load_instana_skills("list"))
        self.assertIn("skills", result)
        self.assertIsInstance(result["skills"], list)

    def test_list_entries_have_id_name_description(self):
        result = self._run(self.tool.load_instana_skills("list"))
        for entry in result["skills"]:
            self.assertIn("id", entry)
            self.assertIn("name", entry)
            self.assertIn("description", entry)

    def test_list_contains_change_timeline_with_frontmatter_values(self):
        result = self._run(self.tool.load_instana_skills("list"))
        entry = next((s for s in result["skills"] if s["id"] == "change-timeline"), None)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["name"], "change-timeline")
        self.assertIn("what changed", entry["description"])
        self.assertNotIn("\n", entry["description"])

    def test_list_has_no_content(self):
        result = self._run(self.tool.load_instana_skills("list"))
        self.assertNotIn("content", result)
        for entry in result["skills"]:
            self.assertNotIn("content", entry)


class TestSkillsToolErrors(unittest.TestCase):
    """Test error handling for get and invalid operations."""

    def setUp(self):
        from src.skills.skills_tool import SkillsMCPTool
        self.tool = SkillsMCPTool(read_token="test-token", base_url="https://example.com")

    def _run(self, coro):
        return asyncio.run(coro)

    def test_get_without_name_returns_error(self):
        for name in (None, ""):
            result = self._run(self.tool.load_instana_skills("get", name))
            self.assertIn("error", result)
            self.assertNotIn("content", result)

    def test_invalid_operation_returns_valid_operations(self):
        result = self._run(self.tool.load_instana_skills("delete"))
        self.assertIn("error", result)
        self.assertIn("list", result["valid_operations"])
        self.assertIn("get", result["valid_operations"])
        self.assertIn("get_reference", result["valid_operations"])

    def test_path_traversal_names_are_rejected(self):
        for bad in ("../skills_tool", "../../README", "/etc/passwd", "change-timeline/../change-timeline", ".."):
            result = self._run(self.tool.load_instana_skills("get", bad))
            self.assertIn("error", result, bad)
            self.assertIn("available", result, bad)
            self.assertNotIn("content", result, bad)


class TestFrontmatterParser(unittest.TestCase):
    """Test the stdlib frontmatter parser."""

    def setUp(self):
        from src.skills.skill_files import parse_frontmatter
        self.parse = parse_frontmatter

    def test_plain_key_value(self):
        meta = self.parse("---\nname: my-skill\ndescription: Does a thing\n---\nBody")
        self.assertEqual(meta, {"name": "my-skill", "description": "Does a thing"})

    def test_comments_are_ignored(self):
        text = "---\n# comment here\n# note: author\nname: my-skill\n# another comment\ndescription: Does a thing\n---\nBody"
        meta = self.parse(text)
        self.assertEqual(meta, {"name": "my-skill", "description": "Does a thing"})

    def test_folded_block_is_joined(self):
        meta = self.parse("---\nname: s\ndescription: >\n  line one\n  line two\n---\n")
        self.assertEqual(meta["description"], "line one line two")

    def test_literal_block_is_joined(self):
        for indicator in ("|", "|-", "|+", ">-", ">+"):
            meta = self.parse(f"---\nname: s\ndescription: {indicator}\n  line one\n  line two\n---\n")
            self.assertIsNotNone(meta)
            self.assertEqual(meta["description"], "line one line two")

    def test_folded_block_followed_by_key(self):
        meta = self.parse("---\ndescription: >\n  a\n  b\nname: s\n---\n")
        self.assertEqual(meta, {"description": "a b", "name": "s"})

    def test_missing_frontmatter_returns_none(self):
        self.assertIsNone(self.parse("# Title\nno frontmatter"))

    def test_unterminated_frontmatter_returns_none(self):
        self.assertIsNone(self.parse("---\nname: s\ndescription: d\n"))


class TestDiscoveryWithTempDir(unittest.TestCase):
    """Test discovery against a temporary skills directory."""

    def _make_skill(self, root: Path, skill_id: str, text: str):
        (root / skill_id).mkdir()
        (root / skill_id / "SKILL.md").write_text(text, encoding="utf-8")

    def test_invalid_frontmatter_skipped_and_warned(self):
        from src.skills import skills_tool

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_skill(root, "good", "---\nname: good\ndescription: ok\n---\nBody")
            self._make_skill(root, "no-fm", "# no frontmatter")
            self._make_skill(root, "no-desc", "---\nname: no-desc\n---\nBody")

            # Patch the module logger rather than using assertLogs: some other test
            # modules replace sys.modules["logging"] with a MagicMock at import time,
            # which breaks unittest's assertLogs when the whole suite runs together.
            with patch.object(skills_tool, "_SKILLS_DIR", root), \
                    patch.object(skills_tool, "logger") as mock_logger:
                skills = skills_tool._discover_skills()
                available = skills_tool._available_skills()

            self.assertEqual([s["id"] for s in skills], ["good"])
            self.assertEqual(available, ["good"])
            joined = " ".join(
                str(arg) for call in mock_logger.warning.call_args_list for arg in call.args
            )
            self.assertIn("no-fm", joined)
            self.assertIn("no-desc", joined)
            self.assertNotIn("good", joined)

    def test_get_skips_invalid_skill(self):
        from src.skills import skills_tool

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_skill(root, "bad", "# no frontmatter")
            with patch.object(skills_tool, "_SKILLS_DIR", root):
                tool = skills_tool.SkillsMCPTool("t", "https://example.com")
                result = asyncio.run(tool.load_instana_skills("get", "bad"))
            self.assertEqual(result["available"], [])


class TestToolDescription(unittest.TestCase):
    """Test the dynamic tool description."""

    def test_description_lists_skills_and_operations(self):
        from src.skills.skills_tool import _build_tool_description
        desc = _build_tool_description()
        self.assertIn("change-timeline:", desc)
        self.assertIn("what changed", desc)
        self.assertIn("list", desc)
        self.assertIn("get", desc)
        self.assertIn("get_reference", desc)
        self.assertIn("valid_operations", desc)


class TestGetResponseIncludesReferencesList(unittest.TestCase):
    """Test that operation='get' response includes a references list."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_get_includes_references_key(self):
        from src.skills.skills_tool import SkillsMCPTool
        tool = SkillsMCPTool(read_token="t", base_url="https://example.com")
        result = self._run(tool.load_instana_skills("get", "change-timeline"))
        self.assertIn("references", result)
        self.assertIsInstance(result["references"], list)

    def test_get_references_contains_output_schema(self):
        from src.skills.skills_tool import SkillsMCPTool
        tool = SkillsMCPTool(read_token="t", base_url="https://example.com")
        result = self._run(tool.load_instana_skills("get", "change-timeline"))
        self.assertIn("output-schema.md", result["references"])
        self.assertIn("phase1-call-params.md", result["references"])
        self.assertIn("phase2-k8s-events.md", result["references"])

    def test_get_references_empty_when_no_references_dir(self):
        from src.skills import skills_tool

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "my-skill").mkdir()
            (root / "my-skill" / "SKILL.md").write_text(
                "---\nname: my-skill\ndescription: does things\n---\nBody",
                encoding="utf-8",
            )
            with patch.object(skills_tool, "_SKILLS_DIR", root):
                tool = skills_tool.SkillsMCPTool("t", "https://example.com")
                result = asyncio.run(tool.load_instana_skills("get", "my-skill"))
        self.assertEqual(result["references"], [])

    def test_get_references_excludes_noise_files_and_uses_posix_paths(self):
        from src.skills import skills_tool

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refs = root / "my-skill" / "references"
            (refs / "sub").mkdir(parents=True)
            (refs / "__pycache__").mkdir()
            (root / "my-skill" / "SKILL.md").write_text(
                "---\nname: my-skill\ndescription: does things\n---\nBody", encoding="utf-8"
            )
            (refs / "a.md").write_text("a", encoding="utf-8")
            (refs / "sub" / "b.md").write_text("b", encoding="utf-8")
            (refs / ".DS_Store").write_bytes(b"x")
            (refs / "__pycache__" / "x.pyc").write_bytes(b"x")
            (refs / "stale.pyc").write_bytes(b"x")
            with patch.object(skills_tool, "_SKILLS_DIR", root):
                tool = skills_tool.SkillsMCPTool("t", "https://example.com")
                result = asyncio.run(tool.load_instana_skills("get", "my-skill"))
        self.assertEqual(result["references"], ["a.md", "sub/b.md"])


class TestGetReferenceSuccess(unittest.TestCase):
    """Test get_reference returns the file content."""

    def _run(self, coro):
        return asyncio.run(coro)

    def setUp(self):
        from src.skills.skills_tool import SkillsMCPTool
        self.tool = SkillsMCPTool(read_token="t", base_url="https://example.com")

    def test_returns_correct_keys(self):
        result = self._run(
            self.tool.load_instana_skills("get_reference", "change-timeline", "output-schema.md")
        )
        self.assertIn("skill", result)
        self.assertIn("reference", result)
        self.assertIn("content", result)
        self.assertNotIn("error", result)

    def test_skill_key_equals_name(self):
        result = self._run(
            self.tool.load_instana_skills("get_reference", "change-timeline", "output-schema.md")
        )
        self.assertEqual(result["skill"], "change-timeline")

    def test_reference_key_equals_path(self):
        result = self._run(
            self.tool.load_instana_skills("get_reference", "change-timeline", "output-schema.md")
        )
        self.assertEqual(result["reference"], "output-schema.md")

    def test_content_is_non_empty_string(self):
        result = self._run(
            self.tool.load_instana_skills("get_reference", "change-timeline", "output-schema.md")
        )
        self.assertIsInstance(result["content"], str)
        self.assertGreater(len(result["content"]), 0)

    def test_content_matches_file_on_disk(self):
        from src.skills.skills_tool import _SKILLS_DIR
        expected = (_SKILLS_DIR / "change-timeline" / "references" / "output-schema.md").read_text(
            encoding="utf-8"
        )
        result = self._run(
            self.tool.load_instana_skills("get_reference", "change-timeline", "output-schema.md")
        )
        self.assertEqual(result["content"], expected)


class TestGetReferenceTraversal(unittest.TestCase):
    """Path-traversal attempts against get_reference are rejected; legitimate paths work."""

    def setUp(self):
        from src.skills import skills_tool

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._root = Path(tmp.name)

        self._skill_dir = self._root / "my-skill"
        self._skill_dir.mkdir()
        (self._skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: does things\n---\nBody",
            encoding="utf-8",
        )
        self._refs = self._skill_dir / "references"
        self._refs.mkdir()
        (self._refs / "safe.md").write_text("safe content", encoding="utf-8")
        (self._refs / "sub").mkdir()
        (self._refs / "sub" / "nested.md").write_text("nested content", encoding="utf-8")

        # Files OUTSIDE my-skill/references/ that an attacker might try to reach.
        (self._root / "secret.txt").write_text("LEAK-MARKER-OUTSIDE", encoding="utf-8")
        (self._skill_dir / "scripts").mkdir()
        (self._skill_dir / "scripts" / "tool.py").write_text("LEAK-MARKER-SCRIPT", encoding="utf-8")

        # A sibling skill with its own references/, plus a directory whose name merely
        # starts with "references" (prefix-confusion attack).
        other = self._root / "other-skill"
        (other / "references").mkdir(parents=True)
        (other / "SKILL.md").write_text(
            "---\nname: other-skill\ndescription: another\n---\nBody", encoding="utf-8"
        )
        (other / "references" / "private.md").write_text("LEAK-MARKER-SIBLING-SKILL", encoding="utf-8")
        (self._skill_dir / "references-evil").mkdir()
        (self._skill_dir / "references-evil" / "x.md").write_text("LEAK-MARKER-PREFIX-DIR", encoding="utf-8")

        patcher = patch.object(skills_tool, "_SKILLS_DIR", self._root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self._tool = skills_tool.SkillsMCPTool("t", "https://example.com")

    def _get(self, path):
        return asyncio.run(self._tool.load_instana_skills("get_reference", "my-skill", path))

    def _check_rejected(self, path):
        result = self._get(path)
        self.assertIn("error", result, f"Expected rejection for path {path!r}")
        self.assertNotIn("content", result, f"Content leaked for path {path!r}")
        for marker in (
            "LEAK-MARKER-OUTSIDE", "LEAK-MARKER-SCRIPT",
            "LEAK-MARKER-SIBLING-SKILL", "LEAK-MARKER-PREFIX-DIR",
        ):
            self.assertNotIn(marker, str(result))

    def _symlink(self, link: Path, target: Path, is_dir=False):
        try:
            link.symlink_to(target, target_is_directory=is_dir)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not supported in this environment")

    # --- classic traversal ---
    def test_parent_traversal_rejected(self):
        self._check_rejected("../../secret.txt")

    def test_absolute_path_rejected(self):
        self._check_rejected("/etc/passwd")

    def test_leading_slash_is_treated_as_relative_to_references(self):
        for path in ("/safe.md", "//safe.md", "\\safe.md", "  /safe.md  ", "/sub/nested.md"):
            result = self._get(path)
            self.assertNotIn("error", result, f"Unexpected rejection for {path!r}")
        self.assertEqual(self._get("/safe.md")["content"], "safe content")
        self.assertEqual(self._get("/sub/nested.md")["content"], "nested content")

    def test_leading_slash_does_not_enable_traversal(self):
        self._check_rejected("/../secret.txt")
        self._check_rejected("//../../secret.txt")
        self._check_rejected("/../SKILL.md")
        self._check_rejected("/../scripts/tool.py")

    def test_whitespace_and_slash_only_paths_rejected(self):
        for path in ("   ", "/", "//", "\\", " / "):
            self._check_rejected(path)

    def test_absolute_path_to_real_file_inside_references_rejected_or_contained(self):
        # An absolute path replaces the base in pathlib joins; it must not escape.
        result = self._get(str(self._root / "secret.txt"))
        self.assertIn("error", result)
        self.assertNotIn("content", result)

    def test_double_dot_rejected(self):
        self._check_rejected("../SKILL.md")

    def test_traversal_into_scripts_rejected(self):
        self._check_rejected("../scripts/tool.py")

    def test_deep_traversal_rejected(self):
        self._check_rejected("sub/../../../secret.txt")

    def test_traversal_into_sibling_skill_references_rejected(self):
        self._check_rejected("../../other-skill/references/private.md")

    def test_prefix_confusion_sibling_directory_rejected(self):
        # "references-evil" shares the string prefix "references" with the real root.
        self._check_rejected("../references-evil/x.md")

    # --- odd inputs ---
    def test_empty_path_rejected(self):
        self._check_rejected("")

    def test_dot_path_rejected(self):
        self._check_rejected(".")

    def test_directory_path_rejected(self):
        self._check_rejected("sub")
        self._check_rejected("sub/")

    def test_null_byte_in_path_rejected(self):
        self._check_rejected("safe.md\x00../../secret.txt")
        self._check_rejected("\x00")

    def test_backslash_traversal_is_not_a_separator_on_posix(self):
        if os.sep == "\\":
            self.skipTest("backslash is a separator on Windows")
        self._check_rejected("..\\..\\secret.txt")

    def test_url_encoded_traversal_is_treated_literally(self):
        self._check_rejected("%2e%2e/%2e%2e/secret.txt")

    def test_very_long_path_rejected_without_exception(self):
        self._check_rejected("a/" * 5000 + "x.md")

    # --- symlinks ---
    def test_symlink_file_escaping_references_rejected(self):
        self._symlink(self._refs / "escape.md", self._root / "secret.txt")
        self._check_rejected("escape.md")

    def test_symlink_dir_escaping_references_rejected(self):
        self._symlink(self._refs / "linkdir", self._root, is_dir=True)
        self._check_rejected("linkdir/secret.txt")

    def test_symlink_to_sibling_skill_reference_rejected(self):
        self._symlink(
            self._refs / "other.md", self._root / "other-skill" / "references" / "private.md"
        )
        self._check_rejected("other.md")

    def test_symlink_staying_inside_references_is_allowed(self):
        self._symlink(self._refs / "alias.md", self._refs / "safe.md")
        result = self._get("alias.md")
        self.assertNotIn("error", result)
        self.assertEqual(result["content"], "safe content")

    # --- legitimate paths ---
    def test_valid_path_accepted(self):
        result = self._get("safe.md")
        self.assertNotIn("error", result)
        self.assertEqual(result["content"], "safe content")

    def test_nested_valid_path_accepted(self):
        result = self._get("sub/nested.md")
        self.assertNotIn("error", result)
        self.assertEqual(result["content"], "nested content")

    def test_dotdot_that_stays_inside_references_is_allowed(self):
        result = self._get("sub/../safe.md")
        self.assertNotIn("error", result)
        self.assertEqual(result["content"], "safe content")

    def test_error_response_does_not_leak_filesystem_paths(self):
        result = self._get("../../secret.txt")
        self.assertEqual(result, {"error": "Invalid reference path: ../../secret.txt"})
        self.assertNotIn(str(self._root), str(result))


class TestGetReferenceErrors(unittest.TestCase):
    """Test error responses for get_reference with bad parameters."""

    def _run(self, coro):
        return asyncio.run(coro)

    def setUp(self):
        from src.skills.skills_tool import SkillsMCPTool
        self.tool = SkillsMCPTool(read_token="t", base_url="https://example.com")

    def test_unknown_skill_returns_error(self):
        result = self._run(
            self.tool.load_instana_skills("get_reference", "no-such-skill", "output-schema.md")
        )
        self.assertIn("error", result)
        self.assertIn("available", result)

    def test_missing_name_returns_error(self):
        result = self._run(self.tool.load_instana_skills("get_reference", None, "output-schema.md"))
        self.assertIn("error", result)
        self.assertNotIn("content", result)

    def test_missing_path_returns_error(self):
        result = self._run(self.tool.load_instana_skills("get_reference", "change-timeline", None))
        self.assertIn("error", result)
        self.assertNotIn("content", result)

    def test_nonexistent_file_returns_error(self):
        result = self._run(
            self.tool.load_instana_skills("get_reference", "change-timeline", "does-not-exist.md")
        )
        self.assertIn("error", result)
        self.assertNotIn("content", result)


class TestUnreadableFiles(unittest.TestCase):
    """Unreadable or non-UTF-8 files yield a generic error dict, never an exception."""

    def setUp(self):
        from src.skills import skills_tool

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self._skill_dir = root / "my-skill"
        (self._skill_dir / "references").mkdir(parents=True)
        (self._skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: does things\n---\nBody",
            encoding="utf-8",
        )
        patcher = patch.object(skills_tool, "_SKILLS_DIR", root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self._tool = skills_tool.SkillsMCPTool("t", "https://example.com")

    def test_non_utf8_reference_returns_generic_error(self):
        (self._skill_dir / "references" / "bad.md").write_bytes(b"\xff\xfe\x00bad")
        result = asyncio.run(
            self._tool.load_instana_skills("get_reference", "my-skill", "bad.md")
        )
        self.assertEqual(result, {"error": "Reference could not be read: bad.md"})

    def test_os_error_on_reference_returns_generic_error(self):
        (self._skill_dir / "references" / "ok.md").write_text("x", encoding="utf-8")
        real_read_text = Path.read_text

        def deny_reference(self_path, *args, **kwargs):
            if self_path.name == "ok.md":
                raise PermissionError("/secret/path")
            return real_read_text(self_path, *args, **kwargs)

        with patch.object(Path, "read_text", deny_reference):
            result = asyncio.run(
                self._tool.load_instana_skills("get_reference", "my-skill", "ok.md")
            )
        self.assertEqual(result, {"error": "Reference could not be read: ok.md"})
        self.assertNotIn("/secret/path", str(result))

    def test_os_error_on_get_returns_generic_error(self):
        # _discover_skills must still see the skill, so only fail the second read.
        real_read_text = Path.read_text
        calls = {"n": 0}

        def flaky(self_path, *args, **kwargs):
            if self_path.name == "SKILL.md":
                calls["n"] += 1
                if calls["n"] > 1:
                    raise PermissionError("/secret/path")
            return real_read_text(self_path, *args, **kwargs)

        with patch.object(Path, "read_text", flaky):
            result = asyncio.run(self._tool.load_instana_skills("get", "my-skill"))
        self.assertEqual(result, {"error": "Skill could not be read: my-skill"})
        self.assertNotIn("/secret/path", str(result))


class TestNoGovernanceTelemetry(unittest.TestCase):
    """The unwired session-governance telemetry has been removed."""

    def test_module_has_no_process_lifetime_session_state(self):
        import src.skills.skills_tool as st

        for attr in ("_sessions_with_skill", "_ungoverned_calls", "record_governance_check"):
            self.assertFalse(hasattr(st, attr), attr)


class TestGetReferencePhase1Params(unittest.TestCase):
    """Smoke test: phase1-call-params.md is loadable and contains expected content."""

    def test_returns_content_with_application_scope_resolution(self):
        from src.skills.skills_tool import SkillsMCPTool
        tool = SkillsMCPTool(read_token="t", base_url="https://example.com")
        result = asyncio.run(
            tool.load_instana_skills("get_reference", "change-timeline", "phase1-call-params.md")
        )
        self.assertNotIn("error", result, f"get_reference failed: {result.get('error')}")
        self.assertIn("Application Scope Resolution", result["content"])

    def test_returns_content_with_service_scope_resolution(self):
        from src.skills.skills_tool import SkillsMCPTool
        tool = SkillsMCPTool(read_token="t", base_url="https://example.com")
        result = asyncio.run(
            tool.load_instana_skills("get_reference", "change-timeline", "phase1-call-params.md")
        )
        self.assertNotIn("error", result, f"get_reference failed: {result.get('error')}")
        self.assertIn("Service Scope Resolution", result["content"])


class TestGetReferencePhase2K8s(unittest.TestCase):
    """Smoke test: phase2-k8s-events.md is loadable and contains expected content."""

    def test_returns_content_with_k8s_info_events_call(self):
        from src.skills.skills_tool import SkillsMCPTool
        tool = SkillsMCPTool(read_token="t", base_url="https://example.com")
        result = asyncio.run(
            tool.load_instana_skills("get_reference", "change-timeline", "phase2-k8s-events.md")
        )
        self.assertNotIn("error", result, f"get_reference failed: {result.get('error')}")
        self.assertIn("get_kubernetes_info_events", result["content"])

    def test_returns_content_with_truncation_rules(self):
        from src.skills.skills_tool import SkillsMCPTool
        tool = SkillsMCPTool(read_token="t", base_url="https://example.com")
        result = asyncio.run(
            tool.load_instana_skills("get_reference", "change-timeline", "phase2-k8s-events.md")
        )
        self.assertNotIn("error", result, f"get_reference failed: {result.get('error')}")
        self.assertIn("Tool cap:", result["content"])
        self.assertIn("API cap:", result["content"])


if __name__ == "__main__":
    unittest.main()
