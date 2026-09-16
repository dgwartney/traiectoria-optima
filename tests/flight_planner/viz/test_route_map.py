"""Composing layers into a map, and framing it on what was actually drawn.

The framing tests are the reason this class exists rather than a function. A
dateline route is drawn with longitudes past +180, outside the bounding box of
its own endpoints -- so a map framed on airport positions frames the line out
of view, and the bug is invisible on any US-only network.
"""

import re

import pytest

from flight_planner import Airport, Route
from flight_planner.viz import (
    ESRI_LIGHT_GRAY,
    ESRI_LIGHT_GRAY_ATTRIBUTION,
    AirportLayer,
    Geodesic,
    NetworkLayer,
    Palette,
    PathLayer,
    RouteMap,
)

folium = pytest.importorskip("folium")

SFO = Airport("SFO", name="San Francisco", latitude=37.619, longitude=-122.375)
BOS = Airport("BOS", name="Logan", latitude=42.364, longitude=-71.005)
DEN = Airport("DEN", name="Denver", latitude=39.862, longitude=-104.673)
AKL = Airport("AKL", name="Auckland", latitude=-37.008, longitude=174.792)
LAX = Airport("LAX", name="Los Angeles", latitude=33.943, longitude=-118.408)
SYD = Airport("SYD", name="Sydney", latitude=-33.946, longitude=151.177)
JFK = Airport("JFK", name="Kennedy", latitude=40.640, longitude=-73.779)


def route(origin, destination, distance_km):
    return Route(
        origin=origin,
        destination=destination,
        distance_km=distance_km,
        flight_number="XX0001",
    )


SFO_DEN = route(SFO, DEN, 1525.0)
DEN_BOS = route(DEN, BOS, 2828.0)
SFO_BOS = route(SFO, BOS, 4341.0)
AKL_LAX = route(AKL, LAX, 10490.0)
SYD_LAX = route(SYD, LAX, 12051.0)
LAX_JFK = route(LAX, JFK, 3983.0)


class TestTheTileLayer:
    def test_it_defaults_to_openstreetmap(self):
        # Every Carto style is watermarked with API KEY REQUIRED and every
        # Stadia style 401s, so this is the only keyless option, not a taste.
        assert RouteMap().tiles == "OpenStreetMap"

    def test_the_rendered_map_carries_no_api_key_warning(self):
        html = RouteMap().airports([SFO, BOS]).finish().get_root().render()

        assert "API KEY REQUIRED" not in html

    def test_a_watermarked_style_is_refused(self):
        # Better to fail here than to discover it after the map is in a report.
        with pytest.raises(ValueError, match="API key"):
            RouteMap(tiles="CartoDB dark_matter")


class TestACustomBasemap:
    """A tile URL template, for the case the named styles cannot serve.

    `OpenStreetMap` needs no API key but does need a `Referer`, and OSM
    answers an unattributable request with a block notice served as HTTP 200
    -- so a map saved for someone to open from `file://` cannot use it.
    `ESRI_LIGHT_GRAY` is the way out, and `experiments/us-route-map` is the
    caller that needed it.
    """

    def test_a_url_template_needs_an_attribution(self):
        # folium raises for this deep inside Map, where the message says
        # nothing about which call was wrong.
        with pytest.raises(ValueError, match="attribution"):
            RouteMap(tiles=ESRI_LIGHT_GRAY)

    def test_a_url_template_with_an_attribution_is_accepted(self):
        route_map = RouteMap(
            tiles=ESRI_LIGHT_GRAY, attribution=ESRI_LIGHT_GRAY_ATTRIBUTION
        )

        assert route_map.tiles == ESRI_LIGHT_GRAY

    def test_a_named_style_needs_no_attribution(self):
        assert RouteMap().attribution is None

    def test_a_named_style_labels_itself(self):
        assert RouteMap().basemap_name == "OpenStreetMap"

    def test_a_url_template_is_not_labelled_with_its_own_url(self):
        # folium would otherwise put the whole tile URL in the layer control,
        # which on a faceted map is the legend.
        route_map = RouteMap(
            tiles=ESRI_LIGHT_GRAY, attribution=ESRI_LIGHT_GRAY_ATTRIBUTION
        )

        assert "http" not in route_map.basemap_name

    def test_the_layer_control_labels_the_basemap_by_name(self):
        # Asserted against the layer control's own base-layer mapping, not
        # merely against the name appearing somewhere in the document. The
        # first version of this test checked the latter and passed while the
        # control still showed the raw tile URL: `name=` on `folium.Map` is
        # ignored, because Map builds its own TileLayer and names it from the
        # tile string.
        route_map = RouteMap(
            tiles=ESRI_LIGHT_GRAY,
            attribution=ESRI_LIGHT_GRAY_ATTRIBUTION,
            basemap_name="Esri light gray",
        )
        html = route_map.airports([SFO, BOS]).finish().get_root().render()

        assert re.search(r'"Esri light gray"\s*:', html)
        assert not re.search(r'"https://server\.arcgisonline[^"]*"\s*:', html)

    def test_the_credit_line_reaches_the_rendered_map(self):
        route_map = RouteMap(
            tiles=ESRI_LIGHT_GRAY, attribution=ESRI_LIGHT_GRAY_ATTRIBUTION
        )
        html = route_map.airports([SFO, BOS]).finish().get_root().render()

        assert "Esri" in html
        assert "arcgisonline" in html


class TestBuildingItUp:
    def test_it_is_fluent(self):
        route_map = RouteMap()

        assert route_map.airports([SFO]) is route_map

    def test_each_call_adds_one_layer(self):
        route_map = (
            RouteMap()
            .airports([SFO, BOS])
            .path([SFO_DEN, DEN_BOS], name="Dijkstra")
            .path([SFO_BOS], name="BFS")
        )

        assert len(route_map.layers) == 3

    def test_it_accepts_a_prebuilt_layer(self):
        route_map = RouteMap().add(AirportLayer([SFO]))

        assert len(route_map.layers) == 1

    def test_the_layer_control_names_carry_the_totals(self):
        html = (
            RouteMap()
            .path([SFO_DEN, DEN_BOS], name="Dijkstra")
            .finish()
            .get_root()
            .render()
        )

        assert "Dijkstra (4,353 km)" in html

    def test_finishing_twice_does_not_double_the_layers(self):
        route_map = RouteMap().airports([SFO, BOS])
        route_map.finish()
        first = len(route_map.finish()._children)

        assert len(route_map.finish()._children) == first


class TestFraming:
    def test_it_frames_on_the_points_that_were_drawn(self):
        route_map = RouteMap().path([SFO_BOS], name="BFS")
        route_map.finish()

        (south, west), (north, east) = route_map.bounds()
        for latitude, longitude in route_map.drawn_points():
            assert south <= latitude <= north
            assert west <= longitude <= east

    def test_a_dateline_path_is_framed_to_include_its_own_line(self):
        # The bug: fitting to AKL and LAX gives -118.4..174.8, a box spanning
        # the wrong way round the planet and excluding the drawn line.
        route_map = RouteMap().path([AKL_LAX], name="Great circle")
        route_map.finish()

        (_, west), (_, east) = route_map.bounds()
        longitudes = [lon for _, lon in route_map.drawn_points()]

        assert west <= min(longitudes)
        assert east >= max(longitudes)

    def test_a_dateline_frame_is_not_the_endpoint_box(self):
        route_map = RouteMap().path([AKL_LAX], name="Great circle")
        route_map.finish()

        (_, _), (_, east) = route_map.bounds()

        assert east > 180

    def test_markers_are_moved_into_the_frame_the_lines_were_drawn_in(self):
        # A marker left at its raw longitude renders in the previous copy of
        # the world, off the edge of a map framed past +180.
        route_map = RouteMap().airports([AKL, LAX]).path([AKL_LAX], name="Great circle")
        route_map.finish()

        (_, west), (_, east) = route_map.bounds()
        for latitude, longitude in route_map.drawn_points():
            assert west <= longitude <= east

    def test_a_multi_leg_dateline_path_is_framed_within_one_globe(self):
        # SYD->LAX->JFK: the first leg unwraps past +180, the second does not
        # cross the dateline at all. Unwrapping each leg on its own leaves the
        # two in different copies of the world and the frame spans 404 degrees,
        # which zooms the map out past the route.
        route_map = RouteMap().path([SYD_LAX, LAX_JFK], name="Dijkstra")
        route_map.finish()

        (_, west), (_, east) = route_map.bounds()

        assert east - west < 360

    def test_consecutive_legs_stay_in_one_continuous_frame(self):
        route_map = RouteMap().path([SYD_LAX, LAX_JFK], name="Dijkstra")
        route_map.finish()

        longitudes = [lon for _, lon in route_map.drawn_points()]
        steps = [
            abs(after - before)
            for before, after in zip(longitudes, longitudes[1:])
        ]

        assert max(steps) < 180

    def test_markers_join_the_frame_of_a_multi_leg_dateline_path(self):
        route_map = (
            RouteMap()
            .path([SYD_LAX, LAX_JFK], name="Dijkstra")
            .airports([SYD, LAX, JFK])
        )
        route_map.finish()

        (_, west), (_, east) = route_map.bounds()
        for _latitude, longitude in route_map.drawn_points():
            assert west <= longitude <= east

    def test_it_frames_an_ordinary_route_without_unwrapping_anything(self):
        route_map = RouteMap().path([SFO_BOS], name="BFS")
        route_map.finish()

        (_, west), (_, east) = route_map.bounds()

        assert -180 <= west and east <= 180

    def test_an_empty_map_has_no_bounds_and_still_renders(self):
        route_map = RouteMap()

        assert route_map.bounds() is None
        assert route_map.finish() is not None


class TestExtrasDrawnOnTheFinishedMap:
    """The render-order trap that silently kills a map's whole layer control.

    folium's `LayerControl` collects its overlays when the document is
    *rendered*, by walking the map's children -- but it emits its own JS where
    it sits in the insertion order. Add a feature group after the control and
    the control still lists it, referencing a `var` declared further down the
    script. Hoisting makes that `undefined`, Leaflet calls `.setZIndex` on it,
    and the script throws: no layer control, no legend, and every plugin added
    after it silently missing too. Nothing raises in Python and the map still
    draws its lines, so only the browser console shows it.

    `finish(decorate=...)` is the way out: the callback runs after every layer
    is built -- so `drawn_points()` is populated and an overlay can trace a
    path already on the map -- and before the control is attached.
    """

    @staticmethod
    def _overlay_order(html):
        """Return `(control_index, {overlay_var: definition_index})`."""
        control = html.index("L.control.layers(")
        overlays = html[html.index("overlays :") : control]
        return control, {
            name: html.index(f"var {name} = ")
            for name in re.findall(r":\s*(feature_group_\w+|geo_json_\w+)", overlays)
        }

    def test_every_overlay_is_defined_before_the_control_lists_it(self):
        def add_an_extra(folium_map):
            folium.FeatureGroup(name="A* (animated)").add_to(folium_map)

        route_map = RouteMap().path([SFO_DEN, DEN_BOS], name="Dijkstra")
        html = route_map.finish(decorate=add_an_extra).get_root().render()

        control, definitions = self._overlay_order(html)
        assert definitions, "no overlays found -- the assertion below is vacuous"
        for name, defined_at in definitions.items():
            assert defined_at < control, f"{name} is used before it is defined"

    def test_the_extra_reaches_the_layer_control(self):
        def add_an_extra(folium_map):
            folium.FeatureGroup(name="A* (animated)").add_to(folium_map)

        route_map = RouteMap().path([SFO_DEN, DEN_BOS], name="Dijkstra")
        html = route_map.finish(decorate=add_an_extra).get_root().render()

        assert re.search(r'"A\* \(animated\)"\s*:', html)

    def test_the_callback_sees_the_points_the_layers_drew(self):
        # An overlay tracing a finished path is the reason the hook runs after
        # build rather than before it.
        seen = []
        path = PathLayer([SFO_DEN, DEN_BOS], name="Dijkstra")
        RouteMap().add(path).finish(
            decorate=lambda _map: seen.append(list(path.drawn_points()))
        )

        assert seen and seen[0]


class TestNotebookRendering:
    def test_it_renders_as_the_value_of_a_cell(self):
        # The common case must not have to remember .finish().
        html = RouteMap().airports([SFO, BOS])._repr_html_()

        assert "leaflet" in html.lower()


class TestTheNamedConstructors:
    def test_compare_draws_one_layer_per_algorithm_plus_the_airports(self):
        planner = _planner()
        algorithms = _algorithms()

        route_map = RouteMap.compare(planner, "SFO", "BOS", algorithms)

        assert len(route_map.layers) == 1 + len(algorithms)

    def test_compare_names_its_layers_for_the_algorithms(self):
        route_map = RouteMap.compare(_planner(), "SFO", "BOS", _algorithms())
        names = [layer.name() for layer in route_map.layers]

        # Each path layer leads with the pair it answers, so the algorithm is
        # named after it rather than at the front -- see PathLayer.name().
        assert any(name.startswith("SFO-BOS · Dijkstra") for name in names)
        assert any(name.startswith("SFO-BOS · BFS") for name in names)

    def test_compare_can_draw_the_network_underneath_it(self):
        catalog = _catalog()
        route_map = RouteMap.compare(
            _planner(), "SFO", "BOS", _algorithms(), context=catalog
        )

        assert any(isinstance(layer, NetworkLayer) for layer in route_map.layers)

    def test_the_context_layer_starts_switched_off(self):
        route_map = RouteMap.compare(
            _planner(), "SFO", "BOS", _algorithms(), context=_catalog()
        )
        network = next(
            layer for layer in route_map.layers if isinstance(layer, NetworkLayer)
        )

        assert network.show() is False

    def test_network_draws_the_whole_catalog(self):
        route_map = RouteMap.network(_catalog())

        assert any(isinstance(layer, NetworkLayer) for layer in route_map.layers)


class TestSurfaces:
    def test_it_takes_a_palette_and_passes_it_to_its_layers(self):
        route_map = RouteMap(palette=Palette("dark")).path([SFO_BOS], name="Dijkstra")
        built = route_map.layers[0].build(folium)
        line = next(iter(built._children.values()))

        assert line.options["color"] == Palette("dark").series("Dijkstra")

    def test_paths_and_context_use_different_segment_counts(self):
        # 24 for a thick path so it does not look faceted; 6 for context,
        # where it is indistinguishable and 2.2x smaller.
        route_map = RouteMap().path([SFO_BOS], name="BFS").routes([SFO_BOS])

        path_layer, network_layer = route_map.layers
        path_layer.build(folium)
        network_layer.build(folium)

        assert len(path_layer.drawn_points()) > len(network_layer.drawn_points())


def _catalog():
    """Return a tiny catalog-like object exposing airports and routes."""

    class Catalog:
        airports = (SFO, BOS, DEN)
        routes = (SFO_DEN, DEN_BOS, SFO_BOS)

    return Catalog()


def _planner():
    """Return a FlightPlanner over the small hand-built network."""
    from flight_planner import FlightPlanner

    planner = FlightPlanner()
    for airport in (SFO, BOS, DEN):
        planner.add_vertex(airport)
    for leg in (SFO_DEN, DEN_BOS, SFO_BOS):
        planner.add_edge(leg)
    return planner


def _algorithms():
    """Return the two algorithms available on every branch."""
    from flight_planner import BFS, Dijkstra

    return {"Dijkstra": Dijkstra(), "BFS": BFS()}
