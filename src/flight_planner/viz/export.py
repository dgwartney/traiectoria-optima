"""Writing a map to HTML, and to PNG for the report and the deck."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Union

PathLike = Union[str, Path]


class MapExporter:
    """Writes a `RouteMap` to HTML, and optionally screenshots it to PNG.

    Separate from `RouteMap` because the two need different things. HTML needs
    only folium; the PNG needs a headless browser, and Playwright is a
    `dev`-group repository tool rather than part of the package contract. A
    reader who only wants the interactive map must not need a browser
    installed, so the dependency stays behind the method that uses it.

    The file matters more than it first appears:
    `tests/experiments/test_committed.py` asserts that every committed
    experiment notebook carries no stored output, so an inline map is gone the
    moment the kernel dies. Anything the report or the deck cites has to be
    written out.

    Attributes:
        width: Screenshot viewport width in pixels.
        height: Screenshot viewport height in pixels.
        settle_ms: How long to wait for tiles after load, in milliseconds.
    """

    def __init__(
        self, width: int = 1200, height: int = 800, settle_ms: int = 2500
    ) -> None:
        """Create an exporter.

        Args:
            width: Screenshot viewport width in pixels.
            height: Screenshot viewport height in pixels.
            settle_ms: Milliseconds to wait after load so tiles can arrive.
                Measured at 2,500 for a continental view; without it the
                screenshot catches a grey grid.

        Raises:
            ValueError: If `settle_ms` is not positive. Zero is refused rather
                than allowed, because the resulting blank-tile PNG looks like
                a rendering bug rather than a missing wait.
        """
        if settle_ms <= 0:
            raise ValueError(
                "settle_ms must be positive: without a wait the screenshot "
                "catches a grey grid where the tiles have not arrived"
            )
        self.width = width
        self.height = height
        self.settle_ms = settle_ms

    def html(self, route_map: Any, destination: PathLike) -> Path:
        """Write the map as a self-contained HTML page.

        Args:
            route_map: A `RouteMap`, or anything with `finish()`.
            destination: Where to write. Parent directories are created.

        Returns:
            The path written.
        """
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        route_map.finish().save(str(path))
        return path

    def png(self, route_map: Any, destination: PathLike) -> Path:
        """Screenshot the map to a PNG.

        Writes the HTML to a sibling temporary file first, because Leaflet has
        to actually run in a browser for there to be anything to capture.

        The browser runs in a **subprocess**, which is not incidental. A
        Jupyter kernel is an asyncio loop, and Playwright's sync API refuses
        to start inside one: "It looks like you are using Playwright Sync API
        inside the asyncio loop." Since a notebook is exactly where a figure
        gets written, the export has to work there -- so the screenshot runs
        in a fresh interpreter with no loop of its own, and works identically
        from a notebook, a script, a test, and pytest.

        Args:
            route_map: A `RouteMap`, or anything with `finish()`.
            destination: Where to write the PNG. Parents are created.

        Returns:
            The path written.

        Raises:
            RuntimeError: If Playwright or its Chromium build is unavailable,
                or the screenshot subprocess fails -- with its stderr and the
                command that installs what is missing.
        """
        self._playwright()

        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        page_path = path.with_suffix(".tmp.html")
        self.html(route_map, page_path)

        try:
            self._screenshot(page_path, path)
        finally:
            page_path.unlink(missing_ok=True)

        return path

    def _screenshot(self, page_path: Path, destination: Path) -> None:
        """Drive a headless browser in a subprocess to capture the page.

        Args:
            page_path: The saved HTML to open.
            destination: Where the PNG should land.

        Raises:
            RuntimeError: If the subprocess fails, carrying its stderr.
        """
        script = _SCREENSHOT_SCRIPT.format(
            width=self.width, height=self.height, settle_ms=self.settle_ms
        )
        completed = subprocess.run(
            [sys.executable, "-c", script, str(page_path.resolve()), str(destination)],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            if "executable doesn't exist" in stderr.lower():
                raise RuntimeError(
                    "playwright has no Chromium build installed. Run:\n"
                    "    uv run playwright install --with-deps chromium"
                )
            raise RuntimeError(f"screenshot failed:\n{stderr}")

    @staticmethod
    def _playwright() -> None:
        """Check Playwright is importable, or explain how to get it.

        Checked here rather than at module scope so that importing `viz`, or
        writing HTML from it, never needs a browser automation library.

        Raises:
            RuntimeError: If playwright is not installed.
        """
        try:
            import playwright  # noqa: F401
        except ModuleNotFoundError as error:  # pragma: no cover - env specific
            raise RuntimeError(
                "Exporting a PNG needs playwright, which is a dev-group "
                "dependency rather than part of the flight_planner package.\n"
                "    uv sync --group dev\n"
                "    uv run playwright install --with-deps chromium\n"
                "The interactive HTML map needs none of this -- use .html()."
            ) from error


# Run in a fresh interpreter by `_screenshot`, so that no asyncio loop from
# the calling process (a Jupyter kernel, say) is in scope.
_SCREENSHOT_SCRIPT = """
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

page_path, destination = Path(sys.argv[1]), sys.argv[2]
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    try:
        page = browser.new_page(viewport={{"width": {width}, "height": {height}}})
        page.goto(page_path.as_uri())
        page.wait_for_timeout({settle_ms})  # let the tiles finish loading
        page.screenshot(path=destination)
    finally:
        browser.close()
"""
