#!/usr/bin/env python3
"""validate_skills.py — Build-time skill validator for mcp-instana.

Checks every skill under ``src/skills/`` for:

  1. Frontmatter parses without error.
  2. ``name`` in frontmatter equals the directory name.
  3. ``description`` is present and within 600 characters.
  4. ``description`` contains a trigger phrase saying when to use the skill
     ("Use when…", "When asked…") and a NOT-clause ("NOT", "Do not", "Does not").
     The frontmatter ``references:`` list must match the files under ``references/``
     exactly (no missing, unlisted or duplicate entries).
  5. Content hash: sha256 over every file in the skill directory (file names +
     bytes; the ``content_hash:`` line itself and ``__pycache__`` are excluded)
     matches the ``content_hash`` frontmatter field (warning only when the field
     is absent; hard failure when the field is present but wrong).
  6. Drift lint: every ``operation="..."`` name referenced in SKILL.md or any
     ``references/**/*.md`` exists in the set of operation names declared by the
     routers under ``src/router/``.

Usage::

    python src/skills/validate_skills.py            # validate only
    python src/skills/validate_skills.py --fix      # validate + write content_hash into frontmatter

Exit codes:
    0 — all checks passed (warnings may have been printed)
    1 — one or more hard failures
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import FrozenSet, List, Tuple

# Shared stdlib-only helpers.  Works both as a script (``python src/skills/validate_skills.py``,
# where src/skills/ is on sys.path) and as the module ``src.skills.validate_skills``.
if __package__:
    from .skill_files import compute_content_hash as _compute_content_hash
    from .skill_files import list_reference_files as _list_reference_files
    from .skill_files import parse_frontmatter as _parse_frontmatter
else:
    from skill_files import compute_content_hash as _compute_content_hash
    from skill_files import list_reference_files as _list_reference_files
    from skill_files import parse_frontmatter as _parse_frontmatter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # mcp-instana/
_SKILLS_DIR = Path(__file__).resolve().parent               # src/skills/
_SRC_DIR = _REPO_ROOT / "src"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SKILL_MD_FILENAME = "SKILL.md"
_MAX_DESCRIPTION_CHARS = 600

# Regex to find operation names referenced in manage_* calls inside a skill body.
# Matches patterns like:  operation="get_events"  or  operation='get_all_releases'
_OP_REFERENCE_RE = re.compile(r'operation\s*=\s*["\']([A-Za-z_]\w*)["\']')

# Pattern that a description must contain to show it says WHEN to use the skill.
# It is matched against the whole description (already capped at
# _MAX_DESCRIPTION_CHARS).  Common words like "for" or "get" deliberately do not
# count: "Use when …", "Use for …", "When asked …", "Invoke when …", "Trigger when …".
_TRIGGER_RE = re.compile(
    r'\b(use|invoke|trigger|call|load)\s+(this\s+skill\s+)?(when|for|if|to)\b'
    r'|\bwhen\s+(asked|the\s+user|a\s+user|users?|you\s+need|someone)\b',
    re.IGNORECASE,
)

# Pattern that a description must contain for a NOT-clause.
_NOT_CLAUSE_RE = re.compile(r'\bNOT\b|\bdo not\b|\bdoes not\b', re.IGNORECASE)

# ---------------------------------------------------------------------------
# Extract known router operation names from source
# ---------------------------------------------------------------------------


_IDENTIFIER_RE = re.compile(r"[A-Za-z_]\w*")


def _extract_known_operations(src_dir: Path) -> FrozenSet[str]:
    """Return the operation names the MCP routers accept.

    Only ``<src_dir>/router/*.py`` is read, so a name that appears solely in a
    prompt, a docstring elsewhere, or a lower-level tool module does not count as
    a real router operation.  Two kinds of evidence are collected:

    - identifier-like string constants (found with ``ast``), e.g.
      ``OPERATION_GET_EVENTS = "get_events"`` or ``valid_operations = ["get_services"]``;
    - ``operation="..."`` examples in router docstrings.  Some resource types (for
      example ``metrics``) dispatch without a literal allowlist, so their only
      declaration of an operation name is the documented example.
    """
    ops: set = set()
    router_dir = src_dir / "router"
    if not router_dir.is_dir():
        return frozenset()
    for py_file in sorted(router_dir.glob("*.py")):
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and _IDENTIFIER_RE.fullmatch(node.value)
            ):
                ops.add(node.value)
        ops.update(_OP_REFERENCE_RE.findall(text))
    return frozenset(ops)


def _write_content_hash(skill_md_path: Path, new_hash: str) -> None:
    """Insert or replace the ``content_hash`` key in SKILL.md frontmatter."""
    resolved_path = skill_md_path.resolve()
    if resolved_path.name != _SKILL_MD_FILENAME or not resolved_path.is_file():
        raise ValueError(f"Invalid SKILL.md path: {skill_md_path}")

    text = resolved_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Find frontmatter end marker
    end_idx = next(
        (i for i in range(1, len(lines)) if lines[i].strip() == "---"),
        None,
    )
    if end_idx is None:
        return  # No frontmatter to update

    # Check if content_hash already exists
    updated = False
    for i in range(1, end_idx):
        if lines[i].startswith("content_hash:"):
            lines[i] = f"content_hash: {new_hash}\n"
            updated = True
            break

    if not updated:
        # Insert before the closing ---
        lines.insert(end_idx, f"content_hash: {new_hash}\n")

    resolved_path.write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, skill_id: str):
        self.skill_id = skill_id
        self.failures: List[str] = []
        self.warnings: List[str] = []

    def fail(self, msg: str) -> None:
        self.failures.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.failures


def validate_skill(
    skill_dir: Path,
    known_ops: FrozenSet[str],
    fix: bool = False,
) -> _Result:
    """Run all checks for one skill directory.  Returns a _Result."""
    skill_id = skill_dir.name
    r = _Result(skill_id)

    skill_md_path = skill_dir / _SKILL_MD_FILENAME
    if not skill_md_path.exists():
        r.fail("SKILL.md not found")
        return r

    # --- Read ---
    try:
        text = skill_md_path.read_text(encoding="utf-8")
    except OSError as e:
        r.fail(f"Cannot read SKILL.md: {e}")
        return r

    # Check 1: frontmatter parses
    meta = _parse_frontmatter(text)
    if meta is None:
        r.fail("Frontmatter missing or unterminated")
        return r

    # Check 2: name == dirname
    name = meta.get("name", "")
    if name != skill_id:
        r.fail(f"name '{name}' in frontmatter does not match directory name '{skill_id}'")

    # Check 3: description present and within cap
    description = meta.get("description", "")
    if not description:
        r.fail("description is missing from frontmatter")
    elif len(description) > _MAX_DESCRIPTION_CHARS:
        r.fail(
            f"description is {len(description)} chars, exceeds cap of {_MAX_DESCRIPTION_CHARS}"
        )

    # Check 4: description contains a "when to use" trigger and a NOT-clause.
    # Both are hard failures: without them the model cannot tell when to load the
    # skill or when it must not.
    if description:
        if not _TRIGGER_RE.search(description):
            r.fail("description has no trigger phrase (e.g. 'Use when…', 'When asked…')")
        if not _NOT_CLAUSE_RE.search(description):
            r.fail("description has no NOT-clause (e.g. 'Does NOT…', 'Do NOT use for…')")

    # Check 4b: frontmatter `references:` must match the files under references/.
    declared_raw = meta.get("references", [])
    if isinstance(declared_raw, list):
        declared = declared_raw
    elif declared_raw:
        declared = [declared_raw]
    else:
        declared = []
    on_disk = _list_reference_files(skill_dir)
    if "references" in meta and not isinstance(declared_raw, list) and declared_raw:
        r.fail("frontmatter 'references' must be a list of file paths (one '- path' per line)")
    else:
        missing = sorted(set(declared) - set(on_disk))
        unlisted = sorted(set(on_disk) - set(declared))
        dupes = sorted({d for d in declared if declared.count(d) > 1})
        if missing:
            r.fail(f"references listed in frontmatter but not found in references/: {missing}")
        if unlisted:
            r.fail(f"files in references/ not listed in frontmatter 'references': {unlisted}")
        if dupes:
            r.fail(f"duplicate entries in frontmatter 'references': {dupes}")

    # Check 5: content hash
    computed_hash = _compute_content_hash(skill_dir)
    stored_hash = meta.get("content_hash", "")
    def _display_path(p: Path) -> str:
        try:
            return str(p.relative_to(_REPO_ROOT))
        except ValueError:
            return str(p)

    if not stored_hash:
        r.warn(f"content_hash absent from frontmatter (current: {computed_hash})")
        if fix:
            _write_content_hash(skill_md_path, computed_hash)
            print(f"  [fix] Wrote content_hash into {_display_path(skill_md_path)}")
    elif stored_hash != computed_hash:
        r.fail(
            f"content_hash mismatch — frontmatter has {stored_hash!r}, "
            f"computed {computed_hash!r}. Run with --fix to update."
        )
        if fix:
            _write_content_hash(skill_md_path, computed_hash)
            print(f"  [fix] Updated content_hash in {_display_path(skill_md_path)}")
            r.failures = [
                f
                for f in r.failures
                if "content_hash mismatch" not in f
            ]

    # Check 6: drift lint — operation names referenced anywhere the model can load
    # (SKILL.md and every references/**/*.md) must exist in the router sources.
    # Skip skill-tool operations (list / get / get_reference): those belong to
    # load_instana_skills, not to a router.
    skill_tool_ops = {"list", "get", "get_reference"}
    sources = [(skill_md_path.name, text)]
    ref_dir = skill_dir / "references"
    if ref_dir.is_dir():
        for ref in sorted(ref_dir.rglob("*.md")):
            try:
                sources.append((ref.relative_to(skill_dir).as_posix(), ref.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError) as e:
                r.fail(f"Cannot read {ref.relative_to(skill_dir).as_posix()}: {e}")
    for source_name, source_text in sources:
        unknown_ops = set(_OP_REFERENCE_RE.findall(source_text)) - skill_tool_ops - known_ops
        if unknown_ops:
            r.fail(
                f"Drift lint: operation name(s) {sorted(unknown_ops)} referenced in "
                f"{source_name} but not found in any router under src/router/. "
                f"Rename or remove these references."
            )

    return r


def validate_all(fix: bool = False) -> Tuple[int, int]:
    """Validate all skills.  Returns (failures, warnings)."""
    known_ops = _extract_known_operations(_SRC_DIR)

    total_failures = 0
    total_warnings = 0

    skill_dirs = sorted(
        entry for entry in _SKILLS_DIR.iterdir()
        if entry.is_dir() and (entry / _SKILL_MD_FILENAME).exists()
    )

    if not skill_dirs:
        print("No skills found.")
        return 0, 0

    for skill_dir in skill_dirs:
        r = validate_skill(skill_dir, known_ops, fix=fix)
        status = "✅ PASS" if r.ok else "❌ FAIL"
        print(f"{status}  {r.skill_id}")
        for w in r.warnings:
            print(f"  ⚠  {w}")
        for f in r.failures:
            print(f"  ✗  {f}")
        total_failures += len(r.failures)
        total_warnings += len(r.warnings)

    print()
    print(
        f"Result: {len(skill_dirs)} skill(s), "
        f"{total_failures} failure(s), {total_warnings} warning(s)."
    )
    return total_failures, total_warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate mcp-instana skill files.")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Compute and write content_hash into frontmatter (no other auto-fixes).",
    )
    args = parser.parse_args()
    failures, _ = validate_all(fix=args.fix)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
