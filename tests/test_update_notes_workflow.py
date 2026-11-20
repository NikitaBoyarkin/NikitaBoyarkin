"""Ratchet for the Recent Notes separator.

blog-post-workflow concatenates posts with no join, so the line break between
them must come from the template. `core.getInput('template')` trims whitespace,
which silently eats a trailing "\\n" and collapses all five notes onto one line
(commits 960c919, f481727, 2e79e83). `$newline` is substituted after the trim
and is the only separator that survives.
"""

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "update-notes.yml"


def _template() -> str:
    match = re.search(r'^\s*template:\s*"([^"]*)"', WORKFLOW.read_text(encoding="utf-8"), re.M)
    assert match, "template input not found in update-notes.yml"
    return match.group(1)


def test_template_uses_newline_placeholder():
    assert "$newline" in _template()


def test_template_does_not_rely_on_a_trailing_escape():
    assert not _template().endswith("\\n")
