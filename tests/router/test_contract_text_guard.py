"""
Guard: LLM-facing text must advertise the SDK spelling only.

The SDK reads ``groupbyTag`` (lowercase b) and ``tagFilterExpression`` (lowercase t)
and silently drops the other spellings. Routers and prompt templates are copied
verbatim by the LLM, so a wrong spelling in them reappears in tool calls.

Scans every string constant (``description=`` text, docstrings, examples, prompt
templates) under ``src/router`` and ``src/prompts``.
"""

import ast
import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
SCANNED_DIRS = ("router", "prompts")

# The SDK type name TagFilterExpressionElement is legitimate; only the bare
# capital-T key is the wrong spelling.
FORBIDDEN = {
    "groupByTag": re.compile(r"groupByTag"),
    "TagFilterExpression": re.compile(r"(?<![A-Za-z])TagFilterExpression(?![A-Za-z])"),
}


def _violations():
    found = []
    for directory in SCANNED_DIRS:
        for path in sorted((SRC / directory).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                    continue
                for label, pattern in FORBIDDEN.items():
                    if pattern.search(node.value):
                        found.append(f"{path.relative_to(SRC.parent)}:{node.lineno}: {label}")
    return found


class TestContractTextGuard(unittest.TestCase):
    def test_no_wrong_spellings_in_router_and_prompt_text(self):
        violations = _violations()
        self.assertEqual(
            violations,
            [],
            "Use 'groupbyTag' / 'groupbyTagEntity' / 'tagFilterExpression' in LLM-facing text:\n"
            + "\n".join(violations),
        )

    def test_guard_detects_wrong_spellings(self):
        """The patterns themselves must match what they are meant to catch."""
        self.assertTrue(FORBIDDEN["groupByTag"].search('{"groupByTag": "x"}'))
        self.assertTrue(FORBIDDEN["TagFilterExpression"].search('"TagFilterExpression": {}'))
        self.assertFalse(FORBIDDEN["TagFilterExpression"].search("TagFilterExpressionElement"))
        self.assertFalse(FORBIDDEN["TagFilterExpression"].search('"tagFilterExpression": {}'))
        self.assertFalse(FORBIDDEN["groupByTag"].search('{"groupbyTag": "x"}'))


if __name__ == "__main__":
    unittest.main()
