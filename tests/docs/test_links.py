"""Resolve every relative link in the project's markdown.

Moving a document is the operation that breaks links, and this project moves
them: five references became report appendices, and a sixth was deleted with
nine inbound links to repoint. Every one of those was found by running this
check rather than by reading, which is the argument for it being a test.

Only *relative* links are resolved. An external URL would need the network,
which would make the suite fail on a train rather than on a mistake.
"""

import re
from pathlib import Path
from typing import List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Generated, vendored, or not ours.
SKIP_DIRS = {".git", ".venv", "vendor", "build", "node_modules", ".ipynb_checkpoints"}

# `](target)` or `](target "title")`.
LINK = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")


def markdown_files() -> List[Path]:
    """Return every markdown file that is part of this project.

    Returns:
        Sorted paths, repository-relative order.
    """
    return sorted(
        path
        for path in REPO_ROOT.rglob("*.md")
        if not SKIP_DIRS.intersection(path.parts)
    )


def broken_links(path: Path) -> List[Tuple[int, str]]:
    """Return the unresolvable relative links in one file.

    Args:
        path: The markdown file to check.

    Returns:
        `(line number, link target)` pairs.
    """
    text = path.read_text(encoding="utf-8")
    broken = []
    for match in LINK.finditer(text):
        target = match.group(1)
        if target.startswith(EXTERNAL_PREFIXES):
            continue
        # Strip any anchor: whether a heading exists is a separate question,
        # and a false alarm on a renamed heading would train people to ignore
        # this test.
        relative = target.split("#", 1)[0]
        if not relative:
            continue
        if not (path.parent / relative).resolve().exists():
            broken.append((text[: match.start()].count("\n") + 1, target))
    return broken


@pytest.mark.parametrize(
    "markdown",
    markdown_files(),
    ids=lambda path: str(path.relative_to(REPO_ROOT)),
)
def test_relative_links_resolve(markdown: Path) -> None:
    """Every relative link in the file points at something that exists."""
    broken = broken_links(markdown)
    assert not broken, "\n".join(
        f"{markdown.relative_to(REPO_ROOT)}:{line} -> {target}" for line, target in broken
    )
