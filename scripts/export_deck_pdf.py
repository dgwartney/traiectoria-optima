"""Export the built deck to PDF through reveal.js's own print mode.

reveal serves a print layout at `?print-pdf`: one page per slide, at the
deck's configured aspect ratio, with the fragments flattened. Screenshotting
the presentation instead would give one long scroll, so the query string is the
whole trick here.

Playwright drives it because it is already a dev dependency -- the repository
uses it to render Folium maps to PNG -- so this adds no new tooling.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

# The deck's own dimensions, from the Makefile's pandoc variables. reveal's
# print stylesheet reads the page size from CSS, so it has to be told.
SLIDE_WIDTH_PX = 1280
SLIDE_HEIGHT_PX = 720


def export(html: Path, out: Path) -> None:
    """Render a built deck to a one-page-per-slide PDF.

    Args:
        html: The `deck.html` written by `scripts/build_deck.py`.
        out: Where to write the PDF.

    Raises:
        SystemExit: If the deck has not been built.
    """
    if not html.exists():
        sys.exit(f"{html} does not exist -- run `make deck` first")
    from playwright.sync_api import sync_playwright

    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": SLIDE_WIDTH_PX, "height": SLIDE_HEIGHT_PX})
        page.goto(f"{html.resolve().as_uri()}?print-pdf", wait_until="networkidle")
        # reveal lays out the print view asynchronously after load; the
        # stylesheet it adds is what we are waiting for.
        page.wait_for_function("() => document.querySelectorAll('.reveal .slides section').length > 0")
        page.emulate_media(media="print")
        page.pdf(
            path=str(out),
            width=f"{SLIDE_WIDTH_PX}px",
            height=f"{SLIDE_HEIGHT_PX}px",
            print_background=True,
            page_ranges="1-",
        )
        browser.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Export the deck.

    Args:
        argv: Command-line arguments, or `None` to read `sys.argv`.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("html", type=Path, help="the built deck.html")
    parser.add_argument("out", type=Path, help="where to write the PDF")
    args = parser.parse_args(argv)
    export(args.html, args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
