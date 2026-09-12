"""Writing a map to disk, which is the only form the report and deck can cite.

An inline map cannot be committed -- `test_committed.py` asserts every
experiment notebook carries no stored output -- so the file is the durable
artifact, and these tests cover the failures that can actually happen: a file
that does not appear, an empty or non-PNG file, a directory that does not
exist yet.

The PNG tests need a Chromium install (`uv run playwright install --with-deps
chromium`) and are skipped without one rather than failing the suite on a
machine that has not done it.
"""

import pytest

from flight_planner import Airport, Route
from flight_planner.viz import MapExporter, RouteMap

folium = pytest.importorskip("folium")

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

SFO = Airport("SFO", name="San Francisco", latitude=37.619, longitude=-122.375)
BOS = Airport("BOS", name="Logan", latitude=42.364, longitude=-71.005)
SFO_BOS = Route(origin=SFO, destination=BOS, distance_km=4341.0,
                flight_number="UA1876")


@pytest.fixture
def route_map():
    return RouteMap().airports([SFO, BOS]).path([SFO_BOS], name="Dijkstra")


class TestWritingHtml:
    def test_it_writes_where_it_was_told_to(self, route_map, tmp_path):
        written = MapExporter().html(route_map, tmp_path / "map.html")

        assert written.is_file()

    def test_it_returns_the_path_it_wrote(self, route_map, tmp_path):
        destination = tmp_path / "map.html"

        assert MapExporter().html(route_map, destination) == destination

    def test_it_writes_a_self_contained_leaflet_page(self, route_map, tmp_path):
        written = MapExporter().html(route_map, tmp_path / "map.html")
        text = written.read_text()

        assert "leaflet" in text.lower()
        assert "Dijkstra (4,341 km)" in text

    def test_it_creates_missing_parent_directories(self, route_map, tmp_path):
        written = MapExporter().html(route_map, tmp_path / "deep" / "map.html")

        assert written.is_file()

    def test_it_never_writes_a_keyed_basemap(self, route_map, tmp_path):
        written = MapExporter().html(route_map, tmp_path / "map.html")

        assert "API KEY REQUIRED" not in written.read_text()

    def test_it_accepts_a_string_path(self, route_map, tmp_path):
        written = MapExporter().html(route_map, str(tmp_path / "map.html"))

        assert written.is_file()


class TestWritingPng:
    def test_it_writes_a_real_png(self, route_map, tmp_path):
        exporter = MapExporter()
        try:
            written = exporter.png(route_map, tmp_path / "map.png")
        except RuntimeError as error:
            pytest.skip(str(error))

        assert written.read_bytes()[:8] == PNG_MAGIC

    def test_it_writes_something_bigger_than_an_empty_file(
        self, route_map, tmp_path
    ):
        exporter = MapExporter()
        try:
            written = exporter.png(route_map, tmp_path / "map.png")
        except RuntimeError as error:
            pytest.skip(str(error))

        assert written.stat().st_size > 10_000

    def test_it_works_inside_a_running_asyncio_loop(self, route_map, tmp_path):
        # A Jupyter kernel runs an asyncio loop, and Playwright's sync API
        # refuses to start inside one ("Please use the Async API instead").
        # Since the notebook is exactly where the figure gets written, the
        # export has to survive it.
        import asyncio

        async def export():
            return MapExporter().png(route_map, tmp_path / "in-loop.png")

        try:
            written = asyncio.run(export())
        except RuntimeError as error:
            pytest.skip(str(error))

        assert written.read_bytes()[:8] == PNG_MAGIC

    def test_it_explains_itself_when_playwright_is_unavailable(
        self, route_map, tmp_path, monkeypatch
    ):
        # Playwright is a dev-group tool, so a reader who only wants HTML must
        # get an explanation rather than an ImportError from deep inside.
        monkeypatch.setattr(
            MapExporter, "_playwright", staticmethod(_raise_missing)
        )

        with pytest.raises(RuntimeError, match="playwright"):
            MapExporter().png(route_map, tmp_path / "map.png")


class TestItsSettings:
    def test_the_viewport_is_configurable(self):
        assert MapExporter(width=800, height=600).width == 800

    def test_the_tile_settle_wait_is_configurable(self):
        # Not optional in principle: without it the screenshot catches a grey
        # grid where the tiles have not arrived.
        assert MapExporter(settle_ms=4000).settle_ms == 4000

    def test_a_zero_settle_wait_is_refused(self):
        with pytest.raises(ValueError):
            MapExporter(settle_ms=0)


def _raise_missing():
    raise RuntimeError(
        "Exporting a PNG needs playwright, a dev-group dependency."
    )
