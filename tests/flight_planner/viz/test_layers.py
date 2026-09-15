"""The three drawable layers, tested without rendering a map.

Each layer is asked what it is called, whether it starts visible, what it drew,
and what folium object it builds. That last one is inspected as a folium
object rather than as HTML: the point is the *shape* of what was built -- one
GeoJson rather than N PolyLines -- which HTML would only tell us indirectly.
"""

import pytest

from flight_planner import Airport, Route
from flight_planner.pathfinding import SearchResult
from flight_planner.viz import (
    AirportLayer,
    Geodesic,
    MapLayer,
    NetworkLayer,
    Palette,
    PathLayer,
)

folium = pytest.importorskip("folium")

SFO = Airport("SFO", name="San Francisco", city="San Francisco", country="US",
              latitude=37.619, longitude=-122.375)
BOS = Airport("BOS", name="Logan", city="Boston", country="US",
              latitude=42.364, longitude=-71.005)
JFK = Airport("JFK", name="Kennedy", city="New York", country="US",
              latitude=40.640, longitude=-73.779)
AKL = Airport("AKL", name="Auckland", city="Auckland", country="NZ",
              latitude=-37.008, longitude=174.792)
LAX = Airport("LAX", name="Los Angeles", city="Los Angeles", country="US",
              latitude=33.943, longitude=-118.408)


def route(origin, destination, distance_km, flight_number="XX0001"):
    """Build one Route for a layer to draw."""
    return Route(
        origin=origin,
        destination=destination,
        distance_km=distance_km,
        flight_number=flight_number,
        airline="XX",
    )


SFO_BOS = route(SFO, BOS, 4341.0)
SFO_JFK = route(SFO, JFK, 4152.0)
AKL_LAX = route(AKL, LAX, 10490.0)


class TestTheInterface:
    def test_every_layer_is_a_maplayer(self):
        assert issubclass(AirportLayer, MapLayer)
        assert issubclass(NetworkLayer, MapLayer)
        assert issubclass(PathLayer, MapLayer)

    def test_maplayer_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            MapLayer()


class TestAirportLayer:
    def test_it_reports_every_airport_it_drew(self):
        layer = AirportLayer([SFO, BOS])
        layer.build(folium)

        assert len(layer.drawn_points()) == 2

    def test_it_builds_one_feature_group(self):
        built = AirportLayer([SFO, BOS]).build(folium)

        assert isinstance(built, folium.FeatureGroup)

    def test_it_starts_visible(self):
        assert AirportLayer([SFO]).show() is True

    def test_it_is_named_for_the_layer_control(self):
        assert AirportLayer([SFO], name="Hubs").name() == "Hubs"

    def test_it_draws_a_marker_per_airport(self):
        built = AirportLayer([SFO, BOS, JFK]).build(folium)

        assert len(built._children) == 3


class TestNetworkLayer:
    def test_it_starts_hidden(self):
        # The context is rarely what the experiment is about, and it buries
        # the answer when drawn on top of it.
        assert NetworkLayer([SFO_BOS]).show() is False

    def test_it_builds_exactly_one_geojson_however_many_routes(self):
        # The measured 109 MB -> 4.6 MB difference on the world snapshot is
        # entirely this: one blob of coordinates instead of a JavaScript
        # statement per route.
        built = NetworkLayer([SFO_BOS, SFO_JFK, AKL_LAX]).build(folium)

        assert isinstance(built, folium.GeoJson)

    def test_it_draws_one_feature_per_distinct_airport_pair(self):
        # The route table is keyed by flight number, so a busy city pair
        # arrives three or four times and would be painted over itself.
        duplicated = [
            route(SFO, BOS, 4341.0, "AA1"),
            route(SFO, BOS, 4341.0, "UA2"),
            route(SFO, BOS, 4341.0, "DL3"),
            route(SFO, JFK, 4152.0, "B64"),
        ]
        built = NetworkLayer(duplicated).build(folium)

        assert len(built.data["features"]) == 2

    def test_it_treats_both_directions_as_one_pair(self):
        built = NetworkLayer([route(SFO, BOS, 4341.0),
                              route(BOS, SFO, 4341.0)]).build(folium)

        assert len(built.data["features"]) == 1

    def test_it_writes_geojson_longitude_first(self):
        # GeoJSON is [lon, lat] while folium.PolyLine takes [lat, lon]. This
        # is the easiest thing here to get backwards and the hardest to see.
        built = NetworkLayer([SFO_BOS]).build(folium)
        first = built.data["features"][0]["geometry"]["coordinates"][0]

        assert first == [pytest.approx(SFO.longitude, abs=0.01),
                         pytest.approx(SFO.latitude, abs=0.01)]

    def test_it_rounds_coordinates(self):
        # Three decimals is about 110 m, far finer than a line drawn at
        # continental zoom can resolve, and most of the remaining file size.
        built = NetworkLayer([SFO_BOS], decimals=3).build(folium)

        for lon, lat in built.data["features"][0]["geometry"]["coordinates"]:
            assert lon == round(lon, 3)
            assert lat == round(lat, 3)

    def test_it_keeps_a_label_and_a_distance_per_feature(self):
        # Batching must not cost the per-route tooltip, which is the obvious
        # worry about collapsing into one layer.
        built = NetworkLayer([SFO_BOS]).build(folium)
        properties = built.data["features"][0]["properties"]

        assert properties["label"] == "BOS-SFO"
        assert properties["km"] == 4341

    def test_it_reports_the_points_it_drew(self):
        layer = NetworkLayer([SFO_BOS], geodesic=Geodesic(segments=6))
        layer.build(folium)

        assert len(layer.drawn_points()) == 8

    def test_it_draws_nothing_when_given_nothing(self):
        built = NetworkLayer([]).build(folium)

        assert built.data["features"] == []


def style_of(built):
    """Return a built GeoJson's style dict."""
    return built.style_function(None)


class TestNetworkLayerAsAFacet:
    """`experiments/us-route-map` draws one of these per airline.

    Everything that makes the class cheap as a backdrop -- batching, pair
    collapsing -- makes thirteen of them affordable at once. What it needed to
    become a facet was a colour, a stroke and a say in its own visibility.
    """

    def test_the_backdrop_defaults_are_unchanged(self):
        # Every existing caller relies on these, so the facet arguments must
        # be additions rather than a change of behaviour.
        layer = NetworkLayer([SFO_BOS])
        built = layer.build(folium)

        assert layer.show() is False
        assert style_of(built)["color"] == Palette().context()
        assert "dashArray" not in style_of(built)

    def test_it_takes_a_colour(self):
        built = NetworkLayer([SFO_BOS], colour="#0072b2").build(folium)

        assert style_of(built)["color"] == "#0072b2"

    def test_it_takes_a_dash_array(self):
        built = NetworkLayer([SFO_BOS], dash_array="6,4").build(folium)

        assert style_of(built)["dashArray"] == "6,4"

    def test_a_solid_layer_carries_no_dash_key_at_all(self):
        # Present-but-null would be bytes per feature across 4,647 features,
        # in a file that ships committed.
        built = NetworkLayer([SFO_BOS], dash_array=None).build(folium)

        assert "dashArray" not in style_of(built)

    def test_it_can_start_visible(self):
        # A carrier layer is the finding, not the backdrop: the reader
        # switches carriers *off* to isolate one.
        layer = NetworkLayer([SFO_BOS], show=True)

        assert layer.show() is True
        assert layer.build(folium).show is True

    def test_it_carries_the_airline_into_the_feature_properties(self):
        # Without this the tooltip cannot say who flies the arc, which on a
        # faceted map is the one thing a reader most wants from it.
        built = NetworkLayer([SFO_BOS]).build(folium)

        assert built.data["features"][0]["properties"]["airline"] == "XX"

    def test_the_tooltip_offers_the_airline_when_the_routes_name_one(self):
        built = NetworkLayer([SFO_BOS]).build(folium)
        tooltip = next(
            child
            for child in built._children.values()
            if isinstance(child, folium.GeoJsonTooltip)
        )

        assert tooltip.fields == ["label", "km", "airline"]

    def test_it_omits_the_airline_field_when_no_route_names_one(self):
        # Advertising a field every feature leaves blank would render an
        # empty row in every tooltip.
        anonymous = Route(
            origin=SFO,
            destination=BOS,
            distance_km=4341.0,
            flight_number="XX0001",
            airline="",
        )
        built = NetworkLayer([anonymous]).build(folium)
        tooltip = next(
            child
            for child in built._children.values()
            if isinstance(child, folium.GeoJsonTooltip)
        )

        assert tooltip.fields == ["label", "km"]
        assert "airline" not in built.data["features"][0]["properties"]


class TestPathLayer:
    def test_it_builds_one_polyline_per_leg(self):
        # A path is a handful of legs, each with its own tooltip, so batching
        # would cost more than it saves here.
        built = PathLayer([SFO_JFK, SFO_BOS]).build(folium)

        assert len(built._children) == 2

    def test_its_name_carries_the_kilometre_total(self):
        # The legend restates the finding rather than just naming a colour.
        layer = PathLayer([SFO_JFK, SFO_BOS], name="Dijkstra")

        assert layer.name() == "Dijkstra (8,493 km)"

    def test_it_names_itself_from_the_airports_when_unnamed(self):
        assert PathLayer([SFO_JFK]).name().startswith("SFO-JFK")

    def test_it_takes_its_colour_from_the_palette_by_series_name(self):
        built = PathLayer([SFO_BOS], name="Dijkstra").build(folium)
        line = next(iter(built._children.values()))

        assert line.options["color"] == Palette().series("Dijkstra")

    def test_an_unknown_series_name_still_draws(self):
        # A path named for something that is not an algorithm is legitimate --
        # "Great circle", say -- and must not raise.
        built = PathLayer([SFO_BOS], name="Great circle").build(folium)

        assert len(built._children) == 1

    def test_it_reports_the_points_it_drew(self):
        layer = PathLayer([SFO_BOS], geodesic=Geodesic(segments=24))
        layer.build(folium)

        assert len(layer.drawn_points()) == 26

    def test_it_reports_unwrapped_longitudes_for_a_dateline_leg(self):
        # The framing bug this guards: the drawn line lives past +180, outside
        # the bounding box of its own endpoints.
        layer = PathLayer([AKL_LAX])
        layer.build(folium)

        assert max(lon for _, lon in layer.drawn_points()) > 180

    def test_it_accepts_a_search_result_and_reports_its_counters(self):
        # Purely additive: the counters appear in the legend when they are
        # available and the layer works without them.
        result = SearchResult(
            cost=8493.0, path=[SFO_JFK, SFO_BOS], nodes_expanded=746
        )
        layer = PathLayer.from_result(result, name="Dijkstra")

        assert "746 expanded" in layer.name()

    def test_it_draws_nothing_when_given_no_legs(self):
        built = PathLayer([]).build(folium)

        assert len(built._children) == 0
