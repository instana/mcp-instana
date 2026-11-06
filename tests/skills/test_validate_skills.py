"""Unit tests for src/skills/validate_skills.py."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# SDK stubs
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

# A minimal set of known operations that satisfies the drift lint in tests.
_KNOWN_OPS = frozenset(
    {
        "get_all_releases",
        "get_events",
        "get_kubernetes_info_events",
        "get_applications",
        "get_services",
        "get_grouped_calls_metrics",
    }
)

_VALID_SKILL_MD = """\
---
name: my-skill
description: >
  Use when investigating things. Does NOT diagnose incidents or rank root causes.
---

# My Skill

Some content with operation="get_all_releases" and operation="get_events".
"""


def _write_skill(root: Path, skill_id: str, text: str) -> Path:
    skill_dir = root / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
    return skill_dir


class TestValidateSkillPasses(unittest.TestCase):
    """A well-formed skill passes all checks."""

    def test_valid_skill_passes(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_skill(root, "my-skill", _VALID_SKILL_MD)
            r = validate_skill(root / "my-skill", _KNOWN_OPS)
        self.assertTrue(r.ok, r.failures)
        self.assertEqual(r.failures, [])


class TestValidateSkillNameMismatch(unittest.TestCase):
    """Skill with name != dirname fails check 2."""

    def test_name_mismatch_fails(self):
        from src.skills.validate_skills import validate_skill

        text = _VALID_SKILL_MD.replace("name: my-skill", "name: wrong-name")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_skill(root, "my-skill", text)
            r = validate_skill(root / "my-skill", _KNOWN_OPS)
        self.assertFalse(r.ok)
        self.assertTrue(any("does not match" in f for f in r.failures))


class TestValidateSkillDescriptionTooLong(unittest.TestCase):
    """Skill with description > 600 chars fails check 3."""

    def test_long_description_fails(self):
        from src.skills.validate_skills import validate_skill

        long_desc = "Use when " + ("x" * 600) + ". Does NOT do other things."
        text = f"---\nname: my-skill\ndescription: >\n  {long_desc}\n---\nBody"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_skill(root, "my-skill", text)
            r = validate_skill(root / "my-skill", _KNOWN_OPS)
        self.assertFalse(r.ok)
        self.assertTrue(any("exceeds cap" in f for f in r.failures))


class TestValidateSkillUnknownOperation(unittest.TestCase):
    """Skill body referencing a non-existent operation fails drift lint."""

    def test_unknown_operation_fails(self):
        from src.skills.validate_skills import validate_skill

        text = """\
---
name: my-skill
description: Use when checking. Does NOT diagnose.
---
Some operation="nonexistent_operation_xyz" call here.
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_skill(root, "my-skill", text)
            r = validate_skill(root / "my-skill", _KNOWN_OPS)
        self.assertFalse(r.ok)
        self.assertTrue(any("Drift lint" in f for f in r.failures))
        self.assertTrue(any("nonexistent_operation_xyz" in f for f in r.failures))


class TestDriftLintCoversReferences(unittest.TestCase):
    """Operation names in references/*.md are linted, not just SKILL.md."""

    def _skill_with_ref(self, root: Path, ref_text: str, ref_name: str = "ref.md") -> Path:
        text = _VALID_SKILL_MD.replace("---\n\n# My Skill", f"references:\n  - {ref_name}\n---\n\n# My Skill")
        skill_dir = _write_skill(root, "my-skill", text)
        (skill_dir / "references").mkdir()
        (skill_dir / "references" / ref_name).write_text(ref_text, encoding="utf-8")
        return skill_dir

    def test_unknown_operation_in_reference_fails_and_names_file(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self._skill_with_ref(
                Path(tmp), 'Call operation="made_up_operation" here.'
            )
            r = validate_skill(skill_dir, _KNOWN_OPS)
        drift = [f for f in r.failures if "Drift lint" in f]
        self.assertEqual(len(drift), 1, r.failures)
        self.assertIn("made_up_operation", drift[0])
        self.assertIn("references/ref.md", drift[0])

    def test_unknown_operation_in_nested_reference_fails(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_skill(Path(tmp), "my-skill", _VALID_SKILL_MD)
            nested = skill_dir / "references" / "deep"
            nested.mkdir(parents=True)
            (nested / "x.md").write_text('operation="nested_bad_op"', encoding="utf-8")
            r = validate_skill(skill_dir, _KNOWN_OPS)
        self.assertTrue(any("references/deep/x.md" in f for f in r.failures), r.failures)

    def test_known_operation_in_reference_passes(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self._skill_with_ref(
                Path(tmp), 'operation="get_services" and operation="get_applications"'
            )
            r = validate_skill(skill_dir, _KNOWN_OPS)
        self.assertEqual([f for f in r.failures if "Drift lint" in f], [])

    def test_skill_tool_operations_in_reference_are_ignored(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self._skill_with_ref(
                Path(tmp), 'load_instana_skills(operation="get_reference", name="x", path="y.md")'
            )
            r = validate_skill(skill_dir, _KNOWN_OPS)
        self.assertEqual([f for f in r.failures if "Drift lint" in f], [])

    def test_skill_md_and_reference_each_reported(self):
        from src.skills.validate_skills import validate_skill

        text = _VALID_SKILL_MD + '\noperation="bad_in_skill"\n'
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_skill(Path(tmp), "my-skill", text)
            (skill_dir / "references").mkdir()
            (skill_dir / "references" / "r.md").write_text('operation="bad_in_ref"', encoding="utf-8")
            r = validate_skill(skill_dir, _KNOWN_OPS)
        drift = [f for f in r.failures if "Drift lint" in f]
        self.assertEqual(len(drift), 2, drift)
        self.assertTrue(any("SKILL.md" in f and "bad_in_skill" in f for f in drift))
        self.assertTrue(any("references/r.md" in f and "bad_in_ref" in f for f in drift))

    def test_unreadable_reference_is_a_failure_not_a_crash(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self._skill_with_ref(Path(tmp), "")
            (skill_dir / "references" / "ref.md").write_bytes(b"\xff\xfe\x00bad")
            r = validate_skill(skill_dir, _KNOWN_OPS)
        self.assertTrue(any("Cannot read references/ref.md" in f for f in r.failures), r.failures)


class TestKnownOperationsSource(unittest.TestCase):
    """_extract_known_operations reads only the routers, not prompts or tool modules."""

    def _tree(self, root: Path) -> Path:
        src = root / "src"
        (src / "router").mkdir(parents=True)
        (src / "prompts").mkdir()
        (src / "tools").mkdir()
        (src / "router" / "r.py").write_text(
            'OPERATION_X = "router_const_op"\n'
            'VALID = ["router_list_op"]\n'
            '"""Docs: operation="router_doc_op" """\n'
            'MSG = "not an identifier, has spaces"\n',
            encoding="utf-8",
        )
        (src / "prompts" / "p.py").write_text('x = "prompt_only_op"\noperation="prompt_doc_op"', encoding="utf-8")
        (src / "tools" / "t.py").write_text('operation_name="tool_only_op"', encoding="utf-8")
        return src

    def test_router_constants_lists_and_docstring_examples_are_known(self):
        from src.skills.validate_skills import _extract_known_operations

        with tempfile.TemporaryDirectory() as tmp:
            ops = _extract_known_operations(self._tree(Path(tmp)))
        self.assertTrue({"router_const_op", "router_list_op", "router_doc_op"} <= ops)

    def test_prompts_and_tool_modules_do_not_count(self):
        from src.skills.validate_skills import _extract_known_operations

        with tempfile.TemporaryDirectory() as tmp:
            ops = _extract_known_operations(self._tree(Path(tmp)))
        for name in ("prompt_only_op", "prompt_doc_op", "tool_only_op"):
            self.assertNotIn(name, ops)

    def test_non_identifier_strings_are_ignored(self):
        from src.skills.validate_skills import _extract_known_operations

        with tempfile.TemporaryDirectory() as tmp:
            ops = _extract_known_operations(self._tree(Path(tmp)))
        self.assertNotIn("not an identifier, has spaces", ops)

    def test_missing_router_dir_returns_empty(self):
        from src.skills.validate_skills import _extract_known_operations

        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_extract_known_operations(Path(tmp)), frozenset())

    def test_real_routers_cover_every_operation_the_real_skill_uses(self):
        from src.skills.validate_skills import _extract_known_operations

        src_dir = Path(__file__).resolve().parent.parent.parent / "src"
        ops = _extract_known_operations(src_dir)
        for name in (
            "get_all_releases", "get_events", "get_kubernetes_info_events",
            "get_applications", "get_services", "get_grouped_calls_metrics",
        ):
            self.assertIn(name, ops)


_REF_SKILL_MD = """\
---
name: my-skill
description: Use when checking things. Does NOT diagnose incidents.
{refs}---
Body with operation="get_events".
"""


def _ref_skill(root: Path, declared, on_disk) -> Path:
    refs = "" if declared is None else (
        "references:\n" + "".join(f"  - {d}\n" for d in declared)
    )
    skill_dir = _write_skill(root, "my-skill", _REF_SKILL_MD.format(refs=refs))
    for rel in on_disk:
        f = skill_dir / "references" / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x", encoding="utf-8")
    return skill_dir


class TestFrontmatterReferencesCheck(unittest.TestCase):
    """The frontmatter `references:` list must match the files under references/."""

    def _failures(self, declared, on_disk):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            r = validate_skill(_ref_skill(Path(tmp), declared, on_disk), _KNOWN_OPS)
        return r.failures

    def test_matching_list_passes(self):
        f = self._failures(["a.md", "sub/b.md"], ["a.md", "sub/b.md"])
        self.assertEqual([x for x in f if "references" in x], [])

    def test_listed_but_missing_file_fails(self):
        f = self._failures(["a.md", "gone.md"], ["a.md"])
        self.assertTrue(any("not found in references/" in x and "gone.md" in x for x in f), f)

    def test_unlisted_file_fails(self):
        f = self._failures(["a.md"], ["a.md", "extra.md"])
        self.assertTrue(any("not listed" in x and "extra.md" in x for x in f), f)

    def test_references_dir_without_frontmatter_list_fails(self):
        f = self._failures(None, ["a.md"])
        self.assertTrue(any("not listed" in x and "a.md" in x for x in f), f)

    def test_list_without_references_dir_fails(self):
        f = self._failures(["a.md"], [])
        self.assertTrue(any("not found in references/" in x for x in f), f)

    def test_no_references_at_all_passes(self):
        f = self._failures(None, [])
        self.assertEqual([x for x in f if "references" in x], [])

    def test_duplicate_entries_fail(self):
        f = self._failures(["a.md", "a.md"], ["a.md"])
        self.assertTrue(any("duplicate" in x and "a.md" in x for x in f), f)

    def test_scalar_references_value_fails(self):
        from src.skills.validate_skills import validate_skill

        text = _REF_SKILL_MD.format(refs="references: a.md\n")
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_skill(Path(tmp), "my-skill", text)
            r = validate_skill(skill_dir, _KNOWN_OPS)
        self.assertTrue(any("must be a list" in x for x in r.failures), r.failures)

    def test_pycache_in_references_is_ignored(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _ref_skill(Path(tmp), ["a.md"], ["a.md"])
            cache = skill_dir / "references" / "__pycache__"
            cache.mkdir()
            (cache / "x.pyc").write_bytes(b"\x00")
            r = validate_skill(skill_dir, _KNOWN_OPS)
        self.assertEqual([x for x in r.failures if "references" in x], [])


class TestDescriptionTriggerCheck(unittest.TestCase):
    """The trigger check needs a real 'when to use' phrase; NOT-clause is required too."""

    def _failures(self, description: str):
        from src.skills.validate_skills import validate_skill

        text = f"---\nname: my-skill\ndescription: {description}\n---\nBody"
        with tempfile.TemporaryDirectory() as tmp:
            r = validate_skill(_write_skill(Path(tmp), "my-skill", text), _KNOWN_OPS)
        return [f for f in r.failures if "description has no" in f]

    def test_real_trigger_phrases_pass(self):
        for desc in (
            "Use when asked what changed. Does NOT diagnose.",
            "Use for timelines. Do not rank causes.",
            "When asked about deploys, list them. Does not diagnose.",
            "Invoke when the user wants a timeline. NOT for root cause.",
        ):
            self.assertEqual(self._failures(desc), [], desc)

    def test_common_words_alone_are_not_a_trigger(self):
        for desc in (
            "Get a list of things for people. Does NOT diagnose.",
            "Shows the check results. Does NOT diagnose.",
            "A timeline tool to find changes. Does NOT diagnose.",
        ):
            f = self._failures(desc)
            self.assertTrue(any("no trigger phrase" in x for x in f), (desc, f))

    def test_missing_not_clause_is_a_failure(self):
        f = self._failures("Use when asked what changed.")
        self.assertTrue(any("no NOT-clause" in x for x in f), f)

    def test_missing_both_reports_both(self):
        f = self._failures("A timeline of things.")
        self.assertEqual(len(f), 2, f)


class TestFrontmatterListParsing(unittest.TestCase):
    """parse_frontmatter returns lists for `- item` blocks and still handles other forms."""

    def setUp(self):
        from src.skills.skill_files import parse_frontmatter
        self.parse = parse_frontmatter

    def test_block_list(self):
        meta = self.parse("---\nname: s\nreferences:\n  - a.md\n  - sub/b.md\n---\n")
        self.assertEqual(meta["references"], ["a.md", "sub/b.md"])

    def test_unindented_list_items(self):
        meta = self.parse("---\nreferences:\n- a.md\n- b.md\n---\n")
        self.assertEqual(meta["references"], ["a.md", "b.md"])

    def test_quoted_items_are_unquoted(self):
        meta = self.parse("---\nreferences:\n  - \"a.md\"\n  - 'b.md'\n---\n")
        self.assertEqual(meta["references"], ["a.md", "b.md"])

    def test_list_followed_by_key(self):
        meta = self.parse("---\nreferences:\n  - a.md\ncontent_hash: sha256:x\n---\n")
        self.assertEqual(meta["references"], ["a.md"])
        self.assertEqual(meta["content_hash"], "sha256:x")

    def test_empty_key_without_items_stays_empty_string(self):
        meta = self.parse("---\nreferences:\nname: s\n---\n")
        self.assertEqual(meta["references"], "")

    def test_folded_description_unaffected_by_dashes(self):
        meta = self.parse("---\ndescription: >\n  - looks like a list\n  but is prose\n---\n")
        self.assertEqual(meta["description"], "- looks like a list but is prose")

    def test_scalar_keys_unchanged(self):
        meta = self.parse("---\nname: s\nversion: 1.1.0\n---\n")
        self.assertEqual(meta, {"name": "s", "version": "1.1.0"})


class TestValidateSkillStaleContentHash(unittest.TestCase):
    """Skill with a wrong content_hash in frontmatter fails check 5."""

    def test_stale_hash_fails(self):
        from src.skills.validate_skills import validate_skill

        text = """\
---
name: my-skill
description: Use when checking. Does NOT diagnose.
content_hash: sha256:deadbeef
---
Body with operation="get_events".
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_skill(root, "my-skill", text)
            r = validate_skill(root / "my-skill", _KNOWN_OPS)
        self.assertFalse(r.ok)
        self.assertTrue(any("content_hash mismatch" in f for f in r.failures))


class TestValidateSkillMissingFrontmatter(unittest.TestCase):
    """Skill with no frontmatter fails check 1."""

    def test_missing_frontmatter_fails(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_skill(root, "my-skill", "# No frontmatter")
            r = validate_skill(root / "my-skill", _KNOWN_OPS)
        self.assertFalse(r.ok)
        self.assertTrue(any("Frontmatter" in f for f in r.failures))


_NO_HASH_SKILL_MD = """\
---
name: my-skill
description: Use when checking. Does NOT diagnose.
---
Body with operation="get_events".
"""


class TestValidateSkillFixWritesHash(unittest.TestCase):
    """--fix writes a content_hash that makes the next plain validation pass."""

    def test_fix_writes_hash_and_next_validation_passes(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_skill(Path(tmp), "my-skill", _NO_HASH_SKILL_MD)

            validate_skill(skill_dir, _KNOWN_OPS, fix=True)
            r = validate_skill(skill_dir, _KNOWN_OPS)

        self.assertTrue(r.ok, r.failures)
        self.assertEqual(r.warnings, [], "hash must be present after --fix")

    def test_fix_is_idempotent(self):
        from src.skills.validate_skills import validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_skill(Path(tmp), "my-skill", _NO_HASH_SKILL_MD)

            validate_skill(skill_dir, _KNOWN_OPS, fix=True)
            after_first = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            r = validate_skill(skill_dir, _KNOWN_OPS, fix=True)
            after_second = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

        self.assertEqual(after_first, after_second)
        self.assertTrue(r.ok, r.failures)

    def test_fix_repairs_stale_hash(self):
        from src.skills.validate_skills import validate_skill

        text = _NO_HASH_SKILL_MD.replace(
            "---\nBody", "content_hash: sha256:deadbeef\n---\nBody"
        )
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _write_skill(Path(tmp), "my-skill", text)

            fixed = validate_skill(skill_dir, _KNOWN_OPS, fix=True)
            r = validate_skill(skill_dir, _KNOWN_OPS)

        self.assertTrue(fixed.ok, fixed.failures)
        self.assertTrue(r.ok, r.failures)


class TestContentHashCoverage(unittest.TestCase):
    """The hash reacts to every relevant file and ignores its own line and caches."""

    def _skill(self, root: Path) -> Path:
        text = _NO_HASH_SKILL_MD.replace("---\nBody", "references:\n  - ref.md\n---\nBody")
        skill_dir = _write_skill(root, "my-skill", text)
        (skill_dir / "references").mkdir()
        (skill_dir / "references" / "ref.md").write_text("ref v1", encoding="utf-8")
        (skill_dir / "scripts").mkdir()
        (skill_dir / "scripts" / "tool.py").write_text("print('v1')", encoding="utf-8")
        return skill_dir

    def test_hash_ignores_its_own_frontmatter_line(self):
        from src.skills.validate_skills import _compute_content_hash

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self._skill(Path(tmp))
            before = _compute_content_hash(skill_dir)
            md = skill_dir / "SKILL.md"
            md.write_text(
                md.read_text(encoding="utf-8").replace(
                    "---\nBody", "content_hash: sha256:anything\n---\nBody"
                ),
                encoding="utf-8",
            )
            after = _compute_content_hash(skill_dir)
        self.assertEqual(before, after)

    def test_reference_change_changes_hash_and_fails_validation(self):
        from src.skills.validate_skills import _compute_content_hash, validate_skill

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self._skill(Path(tmp))
            validate_skill(skill_dir, _KNOWN_OPS, fix=True)
            hash_before = _compute_content_hash(skill_dir)

            (skill_dir / "references" / "ref.md").write_text("ref v2", encoding="utf-8")

            self.assertNotEqual(hash_before, _compute_content_hash(skill_dir))
            stale = validate_skill(skill_dir, _KNOWN_OPS)
            self.assertFalse(stale.ok)
            self.assertTrue(any("content_hash mismatch" in f for f in stale.failures))

            validate_skill(skill_dir, _KNOWN_OPS, fix=True)
            self.assertTrue(validate_skill(skill_dir, _KNOWN_OPS).ok)

    def test_script_change_changes_hash(self):
        from src.skills.validate_skills import _compute_content_hash

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self._skill(Path(tmp))
            before = _compute_content_hash(skill_dir)
            (skill_dir / "scripts" / "tool.py").write_text("print('v2')", encoding="utf-8")
            self.assertNotEqual(before, _compute_content_hash(skill_dir))

    def test_rename_changes_hash(self):
        from src.skills.validate_skills import _compute_content_hash

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self._skill(Path(tmp))
            before = _compute_content_hash(skill_dir)
            (skill_dir / "references" / "ref.md").rename(skill_dir / "references" / "other.md")
            self.assertNotEqual(before, _compute_content_hash(skill_dir))

    def test_pycache_is_excluded(self):
        from src.skills.validate_skills import _compute_content_hash

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = self._skill(Path(tmp))
            before = _compute_content_hash(skill_dir)
            cache = skill_dir / "scripts" / "__pycache__"
            cache.mkdir()
            (cache / "tool.cpython-314.pyc").write_bytes(b"\x00junk")
            (skill_dir / "scripts" / "stray.pyc").write_bytes(b"\x00junk")
            self.assertEqual(before, _compute_content_hash(skill_dir))


class TestRealSkillValidates(unittest.TestCase):
    """The actual change-timeline skill must pass all checks, with no filtering."""

    def test_change_timeline_passes(self):
        from src.skills.validate_skills import _extract_known_operations, validate_skill

        skills_dir = Path(__file__).resolve().parent.parent.parent / "src" / "skills"
        src_dir = skills_dir.parent
        known_ops = _extract_known_operations(src_dir)
        skill_dir = skills_dir / "change-timeline"
        r = validate_skill(skill_dir, known_ops)
        self.assertEqual(
            r.failures,
            [],
            f"change-timeline failed validation (run validate_skills.py --fix "
            f"after editing skill files): {r.failures}",
        )
        self.assertFalse(
            any("content_hash absent" in w for w in r.warnings),
            "change-timeline must carry a content_hash",
        )


class TestValidateAllAndMain(unittest.TestCase):
    """The CLI wrapper reports counts, exit codes and handles an empty skills dir."""

    def _run_validate_all(self, root: Path, fix: bool = False):
        import src.skills.validate_skills as vs

        with patch.object(vs, "_SKILLS_DIR", root), \
                patch.object(vs, "_extract_known_operations", return_value=_KNOWN_OPS):
            return vs.validate_all(fix=fix)

    def test_no_skills_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._run_validate_all(Path(tmp)), (0, 0))

    def test_directories_without_skill_md_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "not-a-skill").mkdir()
            (root / "stray.txt").write_text("x", encoding="utf-8")
            self.assertEqual(self._run_validate_all(root), (0, 0))

    def test_valid_skill_counts_warning_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_skill(root, "my-skill", _VALID_SKILL_MD)
            failures, warnings = self._run_validate_all(root)
        self.assertEqual(failures, 0)
        self.assertGreaterEqual(warnings, 1)  # content_hash absent

    def test_invalid_skill_counts_failures(self):
        bad = _VALID_SKILL_MD.replace("name: my-skill", "name: other-name")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_skill(root, "my-skill", bad)
            failures, _ = self._run_validate_all(root)
        self.assertGreaterEqual(failures, 1)

    def test_main_exit_codes(self):
        import src.skills.validate_skills as vs

        for result, expected in (((0, 0), 0), ((0, 2), 0), ((1, 0), 1)):
            with patch.object(vs, "validate_all", return_value=result) as m, \
                    patch.object(sys, "argv", ["validate_skills.py"]):
                self.assertEqual(vs.main(), expected)
                m.assert_called_once_with(fix=False)

    def test_main_passes_fix_flag(self):
        import src.skills.validate_skills as vs

        with patch.object(vs, "validate_all", return_value=(0, 0)) as m, \
                patch.object(sys, "argv", ["validate_skills.py", "--fix"]):
            self.assertEqual(vs.main(), 0)
            m.assert_called_once_with(fix=True)


if __name__ == "__main__":
    unittest.main()
