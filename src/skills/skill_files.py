"""skill_files.py — stdlib-only helpers shared by skills_tool.py and validate_skills.py.

Owns the two pieces of logic that must behave identically in the server and in the
build-time validator: SKILL.md frontmatter parsing and the skill content hash.

This module must stay free of third-party imports so ``validate_skills.py`` can run
as a plain script without the server dependencies installed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union

# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> Optional[Dict[str, Union[str, List[str]]]]:
    """Parse the leading ``---`` frontmatter block of a SKILL.md.

    Supports ``key: value`` pairs, folded (``>``) multi-line values (joined into a
    single line) and block lists::

        references:
          - a.md
          - b.md

    A key with no inline value followed by ``- item`` lines maps to ``List[str]``;
    every other key maps to ``str``.  Returns None when the frontmatter is missing
    or unterminated.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None

    result: Dict[str, Union[str, List[str]]] = {}
    key: Optional[str] = None
    folded: List[str] = []
    is_folded = False

    def _flush() -> None:
        if key is not None and is_folded:
            result[key] = " ".join(folded).strip()

    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[0] in (" ", "\t") or (line.startswith("- ") and not is_folded):
            if is_folded:
                folded.append(stripped)
            elif key is not None and stripped.startswith("- "):
                item = stripped[2:].strip().strip("\"'")
                current = result.get(key)
                if current == "":
                    result[key] = [item]
                elif isinstance(current, list):
                    current.append(item)
            continue
        if ":" not in line:
            continue
        _flush()
        k, _, v = line.partition(":")
        key, v = k.strip(), v.strip()
        folded = []
        is_folded = v in (">", ">-", ">+", "|", "|-", "|+")
        if not is_folded:
            result[key] = v.strip("\"'")
    _flush()
    return result


# Files ignored by both the content hash and the reference listing.
_HASH_EXCLUDED_DIRS = frozenset({"__pycache__"})
_HASH_EXCLUDED_NAMES = frozenset({".DS_Store"})
_HASH_EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo"})

# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------


def list_reference_files(skill_dir: Path) -> List[str]:
    """Sorted POSIX paths (relative to ``references/``) of the skill's reference files.

    Generated/OS noise (``__pycache__``, ``*.pyc``, ``.DS_Store``) is ignored, matching
    what the content hash ignores.  Returns ``[]`` when ``references/`` is absent.
    """
    ref_dir = skill_dir / "references"
    if not ref_dir.is_dir():
        return []
    found = []
    for p in ref_dir.rglob("*"):
        rel = p.relative_to(ref_dir)
        if not p.is_file() or _HASH_EXCLUDED_DIRS.intersection(rel.parts):
            continue
        if p.name in _HASH_EXCLUDED_NAMES or p.suffix in _HASH_EXCLUDED_SUFFIXES:
            continue
        found.append(rel.as_posix())
    return sorted(found)


# ---------------------------------------------------------------------------
# Content hash
# ---------------------------------------------------------------------------


def _strip_content_hash_line(data: bytes) -> bytes:
    """Remove the ``content_hash:`` line from the frontmatter of SKILL.md bytes.

    The hash is stored inside SKILL.md, so it must not be part of its own input;
    otherwise writing the hash changes the file and invalidates it.
    """
    lines = data.splitlines(keepends=True)
    if not lines or lines[0].strip() != b"---":
        return data
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == b"---"), None)
    if end is None:
        return data
    kept = [
        line for i, line in enumerate(lines)
        if not (0 < i < end and line.startswith(b"content_hash:"))
    ]
    return b"".join(kept)


def _hashed_files(skill_dir: Path) -> List[Path]:
    """Return every file that contributes to the content hash, in sorted order."""
    files = []
    for p in skill_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(skill_dir)
        if _HASH_EXCLUDED_DIRS.intersection(rel.parts):
            continue
        if p.name in _HASH_EXCLUDED_NAMES or p.suffix in _HASH_EXCLUDED_SUFFIXES:
            continue
        files.append(p)
    return sorted(files, key=lambda p: p.relative_to(skill_dir).as_posix())


def compute_content_hash(skill_dir: Path) -> str:
    """sha256 over every file in the skill directory (SKILL.md, references/, scripts/, ...).

    Each file contributes its relative POSIX path and its bytes, delimited so that
    renames or content moving between files change the hash.  The ``content_hash:``
    frontmatter line in SKILL.md is excluded so the stored hash is stable.
    """
    h = hashlib.sha256()
    for p in _hashed_files(skill_dir):
        rel = p.relative_to(skill_dir).as_posix()
        data = p.read_bytes()
        if rel == "SKILL.md":
            data = _strip_content_hash_line(data)
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(str(len(data)).encode("ascii"))
        h.update(b"\0")
        h.update(data)
    return f"sha256:{h.hexdigest()}"
