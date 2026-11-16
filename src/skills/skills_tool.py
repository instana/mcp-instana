"""
skills_tool.py — SkillsMCPTool

load_instana_skills tool — the universal polyfill for MCP clients that
do not surface resources to the model.  Supports three operations:

* ``list``          — returns ``[{id, name, description}]`` for every skill (metadata only).
* ``get``           — returns the exact SKILL.md text for a named skill, plus a
                      ``references`` list of paths available under ``references/``.
* ``get_reference`` — returns the text of one file from a skill's ``references/``
                      directory, identified by skill name and relative path.
                      Protected by allowlist + realpath containment to prevent
                      path-traversal attacks.

Any directory under ``src/skills/`` containing a ``SKILL.md`` with valid YAML
frontmatter (``name`` and ``description``) is automatically a skill.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool
from src.skills.skill_files import list_reference_files, parse_frontmatter

logger = logging.getLogger(__name__)

# Resolved once at import time; skills live alongside this file in src/skills/.
_SKILLS_DIR = Path(__file__).parent

_VALID_OPERATIONS = ["list", "get", "get_reference"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_reference_path(skill_dir: Path, path: str) -> Optional[Path]:
    """Resolve and containment-check a caller-supplied reference path.

    Leading slashes/backslashes are stripped so ``/output-schema.md`` is treated
    as relative to ``references/`` (an absolute path would otherwise make
    pathlib discard the ``references/`` base).

    Returns the resolved absolute ``Path`` when the path is safely contained
    within ``<skill_dir>/references/``, or ``None`` when it escapes (path
    traversal attempt) or the file does not exist.
    """
    clean_path = path.strip().lstrip("/\\") if path else ""
    if not clean_path:
        return None
    ref_root = (skill_dir / "references").resolve()
    try:
        candidate = (ref_root / clean_path).resolve()
    except (OSError, ValueError):
        return None
    try:
        common = os.path.commonpath([str(ref_root), str(candidate)])
    except ValueError:
        # commonpath raises ValueError on Windows when paths are on different drives.
        return None
    if common != str(ref_root):
        return None
    try:
        if not candidate.is_file():
            return None
    except OSError:
        # e.g. "File name too long" - Path.is_file() only swallows ENOENT-style errors.
        return None
    return candidate


def _discover_skills() -> List[Dict[str, str]]:
    """Return ``[{id, name, description}]`` for every valid skill, sorted by id.

    Skills whose SKILL.md has missing or malformed frontmatter are skipped and a
    warning is logged.
    """
    skills: List[Dict[str, str]] = []
    for entry in sorted(_SKILLS_DIR.iterdir()):
        skill_md = entry / "SKILL.md"
        if not (entry.is_dir() and skill_md.exists()):
            continue
        try:
            meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Skipping skill %r: cannot read SKILL.md (%s)", entry.name, e)
            continue
        if not meta or not meta.get("name") or not meta.get("description"):
            logger.warning(
                "Skipping skill %r: SKILL.md has missing or malformed frontmatter "
                "(requires 'name' and 'description')",
                entry.name,
            )
            continue
        skills.append({"id": entry.name, "name": meta["name"], "description": meta["description"]})
    return skills


def _available_skills() -> List[str]:
    """Return the ids of all valid skills (the allowlist for ``get`` and ``get_reference``)."""
    return [s["id"] for s in _discover_skills()]


def _build_tool_description() -> str:
    """Build the load_instana_skills tool description dynamically from available skills."""
    skills = _discover_skills()
    skill_bullets = (
        "\n".join(f"  • {s['id']}: {s['description']}" for s in skills)
        if skills
        else "  (none available)"
    )
    return f"""\
Load Instana skill instructions, list available skills, or load a skill reference file.

ROUTING: Before answering with other Instana tools, check the skills below. If the user's
request matches a skill's "Use when" description, call operation="get" for that skill FIRST
and follow its protocol instead of improvising with lower-level tools.

Operations:
  list          — returns metadata only (no SKILL.md body) for every skill.
  get           — returns the full SKILL.md content for the skill given in `name`,
                  plus a `references` list of paths available under references/.
  get_reference — returns the text of one file from a skill's references/ directory.
                  Requires both `name` (skill id) and `path` (relative path within
                  references/, e.g. "output-schema.md").  Protected against
                  path-traversal: any path escaping references/ is rejected.

Available skills:
{skill_bullets}

Args:
    operation: "list", "get", or "get_reference".
    name:      Skill id.  Required for "get" and "get_reference"; ignored for "list".
               Must be one of the available skills listed above.
    path:      Reference file path relative to the skill's references/ directory.
               Required for "get_reference"; ignored for other operations.

Returns:
    list:          {{"skills": [{{"id": ..., "name": ..., "description": ...}}, ...]}}
    get:           {{"skill": <id>, "content": <markdown>, "references": [<paths>]}}
    get_reference: {{"skill": <id>, "reference": <path>, "content": <text>}}
    errors:
      {{"error": "Unknown skill: <name>", "available": [<ids>]}}
      {{"error": "Invalid reference path: <path>"}}
      {{"error": "...", "valid_operations": {_VALID_OPERATIONS}}}
"""


_TOOL_DESCRIPTION = _build_tool_description()


class SkillsMCPTool(BaseInstanaClient):
    """Reads local SKILL.md files and returns their metadata, content, or reference files."""

    def __init__(self, read_token: str, base_url: str):
        super().__init__(read_token=read_token, base_url=base_url)
        logger.info("SkillsMCPTool initialized")

    @register_as_tool(
        title="Load Instana Skills",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        description=_TOOL_DESCRIPTION,
    )
    async def load_instana_skills(
        self,
        operation: str,
        name: Optional[str] = None,
        path: Optional[str] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """List available skills, return a SKILL.md body, or load a reference file.

        Args:
            operation: "list", "get", or "get_reference".
            name:      Skill id (e.g. "change-timeline"); required for "get" / "get_reference".
            path:      Reference file path within references/ (e.g. "output-schema.md");
                       required for "get_reference".
            ctx:       MCP context (internal).

        Returns:
            list:          {"skills": [{"id", "name", "description"}, ...]}
            get:           {"skill": <id>, "content": <SKILL.md text>, "references": [<paths>]}
            get_reference: {"skill": <id>, "reference": <path>, "content": <text>}
            Otherwise a dict with "error" (and "available" or "valid_operations").
        """
        if operation == "list":
            return {"skills": _discover_skills()}

        if operation == "get":
            if not name:
                return {"error": "Parameter 'name' is required for operation 'get'"}

            available = _available_skills()
            if name not in available:
                logger.warning("load_instana_skills: unknown skill %r (available: %s)", name, available)
                return {"error": f"Unknown skill: {name}", "available": available}

            skill_dir = _SKILLS_DIR / name
            skill_md_path = (skill_dir / "SKILL.md").resolve()

            # Belt-and-braces containment check: the name is allowlisted above, but
            # verify the resolved path stays within _SKILLS_DIR anyway.
            try:
                common = os.path.commonpath([str(_SKILLS_DIR.resolve()), str(skill_md_path)])
            except ValueError:
                return {"error": f"Invalid skill path for: {name}", "available": available}
            if common != str(_SKILLS_DIR.resolve()):
                logger.warning("load_instana_skills: path containment failed for skill %r", name)
                return {"error": f"Invalid skill path for: {name}", "available": available}

            try:
                content = skill_md_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                logger.error("load_instana_skills: cannot read SKILL.md for %r", name, exc_info=True)
                return {"error": f"Skill could not be read: {name}"}
            references = list_reference_files(skill_dir)

            logger.debug(
                "load_instana_skills: loaded %d chars for skill %r (references: %s)",
                len(content),
                name,
                references,
            )
            return {"skill": name, "content": content, "references": references}

        if operation == "get_reference":
            if not name:
                return {"error": "Parameter 'name' is required for operation 'get_reference'"}
            if not path:
                return {"error": "Parameter 'path' is required for operation 'get_reference'"}

            available = _available_skills()
            if name not in available:
                logger.warning(
                    "load_instana_skills get_reference: unknown skill %r (available: %s)",
                    name,
                    available,
                )
                return {"error": f"Unknown skill: {name}", "available": available}

            skill_dir = _SKILLS_DIR / name
            safe_path = _safe_reference_path(skill_dir, path)
            if safe_path is None:
                logger.warning(
                    "load_instana_skills get_reference: invalid/traversal path %r for skill %r",
                    path,
                    name,
                )
                return {"error": f"Invalid reference path: {path}"}

            try:
                content = safe_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                logger.error(
                    "load_instana_skills get_reference: cannot read %r for skill %r",
                    path,
                    name,
                    exc_info=True,
                )
                return {"error": f"Reference could not be read: {path}"}
            logger.debug(
                "load_instana_skills: loaded reference %r (%d chars) for skill %r",
                path,
                len(content),
                name,
            )
            return {"skill": name, "reference": path, "content": content}

        logger.warning("load_instana_skills: invalid operation %r", operation)
        return {
            "error": f"Invalid operation: {operation}",
            "valid_operations": _VALID_OPERATIONS,
        }
