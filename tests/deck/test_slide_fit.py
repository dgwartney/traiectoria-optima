"""Check that no slide overflows its own frame.

A reveal.js slide does not warn when its content is taller than the frame --
it just scrolls, and a scrolled slide on a projector means the bottom line is
simply not delivered. The deck is generated from chapter prose, so this is a
live risk on every chapter edit: nobody lengthens a slide on purpose, they
lengthen a paragraph.

Two details make the measurement trustworthy, and both were found by
deliberately breaking a slide to confirm the test fails:

*   **It runs in `?print-pdf` mode.** In the presentation view reveal leaves
    slides it is not near at `display: none`, where every height reads as
    zero -- so a naive probe silently passes on all but the first few slides.
    Print mode lays them all out at once, and is also what `make deck-pdf`
    exports, so this measures the artifact that gets presented.

*   **It compares the bottom of the content against the frame**, not
    `scrollHeight` against `clientHeight`. In print mode reveal sizes the
    section to its content, so those two are always equal and the comparison
    is vacuous.
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DECK_HTML = REPO_ROOT / "build" / "html" / "deck.html"

# The deck's configured size, from the Makefile. reveal scales the slide to the
# viewport, so the viewport has to match or every slide looks overfull.
VIEWPORT = {"width": 1280, "height": 720}

# Sub-pixel rounding in reveal's own layout. A slide four pixels over is not a
# slide anyone can see is over.
TOLERANCE_PX = 4

# A frame smaller than this means the probe measured a slide that was not laid
# out, which is the failure mode that made the first version of this test pass
# on slides it never looked at.
MIN_PLAUSIBLE_FRAME_PX = 400

# Measures the bottom edge of the lowest child rather than the section's own
# scroll height, which print mode makes meaningless.
MEASURE_JS = """() => Array.from(
  document.querySelectorAll('.reveal .slides section')
).map((section, index) => {
  let content = 0;
  for (const child of section.children) {
    content = Math.max(content, child.offsetTop + child.offsetHeight);
  }
  return {
    index,
    title: ((section.querySelector('h1,h2') || {}).textContent || '(untitled)').trim(),
    content,
    frame: section.clientHeight,
  };
})"""

pytest.importorskip("playwright.sync_api")


def measure(html: Path) -> List[Dict[str, Any]]:
    """Return one fit measurement per slide.

    Args:
        html: A built `deck.html`.

    Returns:
        A list of `{"index", "title", "content", "frame"}` dicts, in slide
        order.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(f"{html.resolve().as_uri()}?print-pdf", wait_until="networkidle")
        page.emulate_media(media="print")
        page.wait_for_function(
            "() => document.querySelectorAll('.reveal .slides section').length > 0"
        )
        measurements = page.evaluate(MEASURE_JS)
        browser.close()
    return measurements


@pytest.fixture(scope="module")
def slides() -> List[Dict[str, Any]]:
    """Measure the built deck once for the whole module.

    Returns:
        The per-slide fit measurements.
    """
    if not DECK_HTML.exists():
        pytest.skip(f"{DECK_HTML.relative_to(REPO_ROOT)} not built -- run `make deck`")
    return measure(DECK_HTML)


def test_the_deck_has_slides(slides: List[Dict[str, Any]]) -> None:
    """A deck that built to zero slides would pass every other check here."""
    assert len(slides) > 0


def test_every_slide_was_actually_laid_out(slides: List[Dict[str, Any]]) -> None:
    """Guard against measuring slides the browser never rendered.

    Without this, a slide left at `display: none` reports a zero frame and a
    zero content height, and an overflow check on those two numbers passes.
    """
    unrendered = [
        f"slide {slide['index'] + 1} ({slide['title']!r}) has a "
        f"{slide['frame']}px frame, so it was not laid out"
        for slide in slides
        if slide["frame"] < MIN_PLAUSIBLE_FRAME_PX
    ]
    assert not unrendered, "\n".join(unrendered)


def test_no_slide_overflows_its_frame(slides: List[Dict[str, Any]]) -> None:
    """Content bottom does not fall below the frame on any slide.

    Reported all at once rather than one failure at a time: after a chapter
    edit it is useful to know every slide that needs attention, not just the
    first.
    """
    overflowing = [
        f"slide {slide['index'] + 1} ({slide['title']!r}) overflows by "
        f"{slide['content'] - slide['frame']}px "
        f"(content {slide['content']}px in a {slide['frame']}px frame)"
        for slide in slides
        if slide["content"] - slide["frame"] > TOLERANCE_PX
    ]
    assert not overflowing, "\n".join(overflowing)
