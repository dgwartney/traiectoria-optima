from flight_planner.core import Vertex
from flight_planner.geo import Point
from flight_planner.flights import Airport


class TestAirport:
    def test_is_a_vertex_and_a_point(self):
        jfk = Airport("JFK", latitude=40.6413, longitude=-73.7781)
        assert isinstance(jfk, Vertex)
        assert isinstance(jfk, Point)

    def test_vertex_before_point_in_mro(self):
        mro = Airport.__mro__
        assert mro.index(Vertex) < mro.index(Point)

    def test_iata_code_is_normalized(self):
        assert Airport("  jfk ").iata_code == "JFK"

    def test_equality_keyed_only_on_iata_code(self):
        a = Airport("JFK", latitude=40.0, longitude=-73.0)
        b = Airport("JFK", latitude=1.0, longitude=1.0)
        assert a == b
        assert hash(a) == hash(b)

    def test_different_iata_code_not_equal(self):
        assert Airport("JFK") != Airport("LAX")

    def test_default_coordinates_are_zero(self):
        airport = Airport("JFK")
        assert airport.latitude == 0.0
        assert airport.longitude == 0.0

    def test_distance_to_uses_point_behavior(self):
        jfk = Airport("JFK", latitude=40.6413, longitude=-73.7781)
        lax = Airport("LAX", latitude=33.9416, longitude=-118.4085)
        distance = jfk.distance_to(lax)
        assert 3900 < distance < 4000


class TestAirportDescriptiveFields:
    """Attributes carried for reporting and catalog filtering."""

    def test_descriptive_fields_default_to_empty(self):
        airport = Airport("JFK")

        assert airport.city == ""
        assert airport.type == ""
        assert airport.continent == ""
        assert airport.region == ""
        assert airport.icao_code == ""
        assert airport.wikipedia_link == ""

    def test_elevation_defaults_to_none(self):
        # None rather than 0.0: 1.8% of airports have no elevation, and sea
        # level is a real value that must not be confused with "unknown".
        assert Airport("JFK").elevation_ft is None

    def test_scheduled_service_defaults_to_false(self):
        assert Airport("JFK").has_scheduled_service is False

    def test_is_international_defaults_to_false(self):
        assert Airport("JFK").is_international is False

    def test_is_international_is_stored(self):
        assert Airport("JFK", is_international=True).is_international is True

    def test_is_international_is_independent_of_type(self):
        # 116 large airports are not international and 364 medium ones are,
        # so the flag carries information `type` does not.
        assert Airport("XXX", type="large_airport").is_international is False
        assert Airport("YYY", type="medium_airport", is_international=True).is_international

    def test_descriptive_fields_are_stored(self):
        sfo = Airport(
            "SFO",
            name="San Francisco International Airport",
            city="San Francisco",
            country="US",
            region="US-CA",
            continent="NA",
            latitude=37.619806,
            longitude=-122.374821,
            elevation_ft=13.0,
            type="large_airport",
            icao_code="KSFO",
            has_scheduled_service=True,
            wikipedia_link="https://en.wikipedia.org/wiki/San_Francisco_International_Airport",
        )

        assert sfo.city == "San Francisco"
        assert sfo.region == "US-CA"
        assert sfo.continent == "NA"
        assert sfo.elevation_ft == 13.0
        assert sfo.type == "large_airport"
        assert sfo.icao_code == "KSFO"
        assert sfo.has_scheduled_service is True
        assert sfo.wikipedia_link.endswith("San_Francisco_International_Airport")

    def test_descriptive_fields_do_not_affect_identity(self):
        # Graph identity stays keyed on iata_code alone.
        bare = Airport("SFO")
        rich = Airport("SFO", city="San Francisco", type="large_airport")

        assert bare == rich
        assert hash(bare) == hash(rich)
