"""Lint the slide wrapper markup in the report chapters.

The wrapper is `<div class="deck-slide" id="...">` rather than pandoc's
`::: deck-slide`, because GitHub has no fenced-div support and would render the
colons literally when someone browses a chapter. The HTML form parses to the
same pandoc AST node while GitHub hides it.

That choice costs one rule: **CommonMark ends an HTML block at a blank line**,
so the blank line after the opening tag and before the closing tag are what
make the inner markdown parse as markdown. Omit either and pandoc takes the
whole block as one raw HTML node -- at which point `deck-slides.lua` never sees
a Div, and the slide disappears from the deck with no error and no warning.

A silent omission is the worst failure mode a build can have, so it is a test.
"""

from pathlib import Path
from typing import List

import pytest

REPORT_DIR = Path(__file__).resolve().parents[2] / "docs" / "report"

OPEN_PREFIX = '<div class="deck-slide"'
CLOSE = "</div>"


def chapters() -> List[Path]:
    """Return the report chapters, in document order.

    Returns:
        Sorted chapter paths.
    """
    return sorted(REPORT_DIR.glob("[0-9][0-9]-*.md"))


@pytest.mark.parametrize("chapter", chapters(), ids=lambda path: path.name)
def test_slide_wrappers_are_delimited_by_blank_lines(chapter: Path) -> None:
    """Every opening wrapper is followed by a blank line."""
    lines = chapter.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        if not line.startswith(OPEN_PREFIX):
            continue
        assert number < len(lines) and lines[number].strip() == "", (
            f"{chapter.name}:{number} opens a deck-slide with no blank line "
            "after it. Pandoc would swallow the whole block as raw HTML and "
            "the slide would vanish from the deck."
        )


@pytest.mark.parametrize("chapter", chapters(), ids=lambda path: path.name)
def test_slide_wrappers_carry_an_id(chapter: Path) -> None:
    """Every slide has an id, which is its name in the manifest."""
    for number, line in enumerate(chapter.read_text(encoding="utf-8").splitlines(), start=1):
        if line.startswith(OPEN_PREFIX):
            assert 'id="' in line, (
                f"{chapter.name}:{number} has no id. The id is how "
                "docs/deck/manifest.txt orders the slide."
            )


@pytest.mark.parametrize("chapter", chapters(), ids=lambda path: path.name)
def test_slide_wrappers_are_balanced(chapter: Path) -> None:
    """Open and close tags match, and every close is preceded by a blank line.

    Counting `<div` against `</div>` across the whole chapter catches the
    other half of the delimiter rule: a closing tag pressed against the line
    above it leaves pandoc reading raw HTML to the end of the block.
    """
    lines = chapter.read_text(encoding="utf-8").splitlines()
    opens = sum(1 for line in lines if line.lstrip().startswith("<div"))
    closes = sum(1 for line in lines if line.strip() == CLOSE)
    assert opens == closes, (
        f"{chapter.name} has {opens} <div> against {closes} </div>. An "
        "unbalanced wrapper drops content from one deliverable or the other."
    )
    for number, line in enumerate(lines, start=1):
        if line.strip() == CLOSE:
            assert lines[number - 2].strip() == "", (
                f"{chapter.name}:{number} closes a div with no blank line "
                "before it, so the block above it stays raw HTML."
            )


def test_every_chapter_slide_is_in_the_manifest() -> None:
    """A slide missing from the manifest would be left out of the deck.

    `scripts/build_deck.py` fails on this too, but only when the deck is
    built. Authoring a slide and running the tests is the likelier order.
    """
    manifest = REPORT_DIR.parent / "deck" / "manifest.txt"
    listed = {
        line.split("#", 1)[0].strip()
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.split("#", 1)[0].strip()
    }
    authored = set()
    for chapter in chapters():
        for line in chapter.read_text(encoding="utf-8").splitlines():
            if line.startswith(OPEN_PREFIX) and 'id="' in line:
                authored.add(line.split('id="', 1)[1].split('"', 1)[0])
    assert authored <= listed, (
        "these slides are authored in a chapter but absent from "
        f"{manifest.name}, so `make deck` would leave them out: "
        f"{sorted(authored - listed)}"
    )
