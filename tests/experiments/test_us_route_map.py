"""The faceted carrier map, checked by re-deriving what it recorded.

Same position as `test_committed.py` takes on every other experiment: the
numbers are re-computed from the pinned snapshot and compared, and what the
map *looks* like is left to a human. Two things here are specific to this
experiment:

- Its thirteen layers are supposed to partition the network. That is a
  property, not a number, and it is the one thing most likely to break quietly
  if `uncovered_routes` is ever "simplified".
- Its interactive HTML is committed, which nothing else in this repository
  does. The size bound is the condition that made committing it acceptable, so
  it is a test rather than a note.
"""

import json

import pytest

from flight_planner.experiments import Experiment

# The US + Puerto Rico slice, large and medium airports, both endpoints. The id
# embeds a hash of the contents, so changing the data changes the id and this
# constant has to be updated deliberately rather than silently.
US_SNAPSHOT_ID = "2026-09-15-8054eb"

SLUG = "us-route-map"

# What the committed HTML is allowed to weigh. Measured at 2,008,548 bytes;
# the ceiling leaves room for a basemap or folium change without leaving room
# for the file to double. A previously committed folium HTML was removed from
# this repository as "147 KB of generated Folium output committed as a source
# file", so this deliverable ships bounded or not at all.
MAX_INTERACTIVE_BYTES = 2_500_000


@pytest.fixture(scope="module")
def us_route_map(repo_root):
    return Experiment.open(repo_root / "experiments" / SLUG)


@pytest.fixture(scope="module")
def recorded(us_route_map):
    results = us_route_map.results()
    assert results is not None, "run experiments/us-route-map/explore.ipynb"
    return results["results"]


@pytest.fixture(scope="module")
def catalog(us_route_map):
    return us_route_map.catalog()


def pair_key(route):
    """Return a route's unordered airport pair, as the map draws it."""
    return tuple(sorted((route.origin.iata_code, route.destination.iata_code)))


class TestTheExperimentDirectory:
    def test_it_opens_and_pins_the_us_snapshot(self, us_route_map):
        assert us_route_map.slug == SLUG
        assert us_route_map.snapshot.snapshot_id == US_SNAPSHOT_ID

    def test_the_snapshot_path_is_relative(self, us_route_map):
        assert us_route_map.snapshot_reference.startswith("../../")

    def test_its_notebook_exists(self, us_route_map):
        assert us_route_map.notebooks
        assert all(path.is_file() for path in us_route_map.notebook_paths)

    def test_its_notebook_carries_no_stored_output(self, us_route_map):
        # A rendered folium map of 4,647 arcs is megabytes of inline HTML.
        for path in us_route_map.notebook_paths:
            for cell in json.loads(path.read_text())["cells"]:
                assert not cell.get("outputs")

    def test_it_has_been_run(self, us_route_map):
        results = us_route_map.results()
        assert results is not None
        assert results["snapshot"]["id"] == US_SNAPSHOT_ID

    def test_the_snapshot_criteria_match_the_stated_parameters(
        self, us_route_map
    ):
        # The notebook asserts this too, but it belongs in the suite: the
        # whole experiment is about a specific slice, and Puerto Rico being
        # `PR` rather than `US` is the easiest part of it to lose.
        parameters = us_route_map.parameters
        criteria = us_route_map.snapshot.criteria

        assert criteria["country"] == parameters["countries"]
        assert criteria["airport_type"] == [
            f"{kind}_airport" for kind in parameters["airport_types"]
        ]


class TestTheRecordedCounts:
    def test_the_snapshot_is_the_size_it_was_recorded_as(
        self, catalog, recorded
    ):
        assert len(catalog.airports) == recorded["airports_drawn"]
        assert len(catalog.routes) == recorded["route_rows"]

    def test_the_per_carrier_counts_are_still_the_counts(
        self, catalog, recorded
    ):
        for code, pairs in recorded["carrier_pairs"].items():
            drawn = {pair_key(route) for route in catalog.airline(code).routes}

            assert len(drawn) == pairs, code

    def test_the_layer_sum_exceeds_the_network(self, recorded):
        # Not a bug: a pair flown by two carriers is drawn once per layer,
        # which is exactly what makes switching one off informative.
        assert recorded["layer_sum"] > recorded["network_pairs"]
        assert recorded["layer_sum"] == sum(recorded["carrier_pairs"].values())

    def test_the_thirteen_layers_partition_the_network(self, catalog, recorded):
        # The property the bucket exists to preserve. If `uncovered_routes`
        # ever returns "every route the other carriers fly" instead, this
        # fails -- and the bucket's size stops meaning "what the majors miss".
        union = set()
        for code in recorded["carrier_pairs"]:
            union |= {
                pair_key(route) for route in catalog.airline(code).routes
            }
        network = {pair_key(route) for route in catalog.routes}

        assert len(union) == recorded["carrier_union"]
        assert len(network - union) == recorded["other_bucket"]
        assert recorded["carrier_union"] + recorded["other_bucket"] == len(
            network
        )

    def test_it_reaches_alaska_hawaii_and_puerto_rico(self, catalog, recorded):
        # The reason the slice is US + PR rather than US, and the reason it
        # keeps medium airports. If any of these goes to zero the experiment
        # has quietly become a map of the lower 48.
        counted = recorded["airports_by_region"]
        assert counted["US-AK"] > 0
        assert counted["US-HI"] > 0
        assert counted["PR-U-A"] > 0

        actual = {region: 0 for region in counted}
        for airport in catalog.airports:
            if airport.region in actual:
                actual[airport.region] += 1

        assert actual == counted

    def test_the_frame_spans_the_whole_footprint(self, recorded):
        # Adak to Culebra. Worth pinning because it is the cost of including
        # the territories, and because a shrinking span would mean the
        # offshore arcs had stopped being drawn.
        bounds = recorded["bounds"]

        assert bounds["west"] < -176
        assert bounds["east"] > -66
        assert bounds["longitude_span"] > 110


class TestThePaletteMeasurement:
    # The palette's claim is about same-stroke pairs, since carriers sharing a
    # stroke are the ones a reader must separate by colour alone. The floor is
    # the worst case over normal vision and three dichromacies.
    FLOORS = {"light": 19.0, "dark": 19.0}

    def test_both_surfaces_clear_the_floor(self, recorded):
        for mode, floor in self.FLOORS.items():
            measured = recorded["palette_contrast"][mode]["worst_same_stroke"]
            worst = min(entry["delta_e"] for entry in measured.values())

            assert worst >= floor, (mode, measured)

    def test_every_deficiency_was_measured(self, recorded):
        # A floor computed over fewer views than intended would pass while
        # meaning less, so the set of views is pinned too.
        for mode in self.FLOORS:
            measured = recorded["palette_contrast"][mode]["worst_same_stroke"]

            assert set(measured) == {
                "normal",
                "protanopia",
                "deuteranopia",
                "tritanopia",
            }

    def test_there_are_three_dash_classes_of_four(self, recorded):
        # What makes the floor structural: each class holds each hue once.
        for mode in self.FLOORS:
            strokes = recorded["palette_contrast"][mode]["strokes"]

            assert len(strokes) == 3
            assert sorted(len(members) for members in strokes.values()) == [
                4,
                4,
                4,
            ]


@pytest.fixture(scope="module")
def html(us_route_map):
    figures = us_route_map.parameters["figures"]
    directory = us_route_map.directory / figures["interactive"]
    return (directory / "us-route-map.html").resolve()


class TestTheCommittedInteractiveMap:
    def test_it_exists(self, html):
        assert html.is_file(), f"{html} -- re-run the notebook"

    def test_it_is_real_html_carrying_a_layer_control(self, html):
        text = html.read_text()

        assert text.lstrip().startswith("<!DOCTYPE html>")
        assert "L.control.layers" in text

    def test_every_carrier_appears_in_its_layer_control(
        self, html, us_route_map
    ):
        # The layer control is this map's only legend, so a carrier missing
        # from it is a carrier the reader cannot switch.
        text = html.read_text()

        for code, name in us_route_map.parameters["carriers"].items():
            assert f"{name} ({code})" in text, code

    def test_the_defunct_carriers_are_labelled_as_such(
        self, html, us_route_map
    ):
        # The data is circa 2014. Saying so on the map itself is the point.
        text = html.read_text()

        for code in us_route_map.parameters["defunct"]:
            name = us_route_map.parameters["carriers"][code]
            assert f"{name} ({code}) [defunct]" in text

    def test_its_basemap_does_not_require_a_referer(self, html):
        # The defect this test exists for. OSM needs no API key but does need
        # the request to be attributable, and it enforces that on `Referer`.
        # A committed file opened by double-clicking is a `file://` page,
        # which sends no `Referer`, so every OSM tile came back as a `403 /
        # Access blocked` notice -- served as HTTP 200 with a PNG body, so
        # nothing raised and the map rendered with the basemap reading
        # "Access blocked". It survived review because the map was first
        # checked over localhost, which *does* send a `Referer`.
        #
        # Asserted on the committed artifact rather than on RouteMap, because
        # what matters is what shipped.
        text = html.read_text()

        assert "tile.openstreetmap.org" not in text, (
            "OSM tiles are blocked for file:// readers; see "
            "ESRI_LIGHT_GRAY in flight_planner/viz/routemap.py"
        )
        assert "server.arcgisonline.com" in text

    def test_its_basemap_is_attributed(self, html):
        # Required by every provider's terms, and folium will not build a
        # URL-template basemap without it.
        assert "Esri" in html.read_text()

    def test_its_basemap_is_named_in_the_layer_control(self, html):
        # folium labels a URL-template basemap with the whole tile URL
        # otherwise, and on this map the layer control is the legend.
        assert "Esri light gray" in html.read_text()

    def test_it_stays_within_its_size_bound(self, html, recorded):
        size = html.stat().st_size

        assert size == recorded["interactive_bytes"]
        assert size <= MAX_INTERACTIVE_BYTES, (
            f"{size:,} bytes exceeds the {MAX_INTERACTIVE_BYTES:,} ceiling; "
            "shrink the map or raise the bound deliberately"
        )
