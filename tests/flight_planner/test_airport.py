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
