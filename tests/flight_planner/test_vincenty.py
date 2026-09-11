from flight_planner.geo import Point
from flight_planner.geo import Haversine
from flight_planner.geo import Vincenty

_JFK = Point(40.6413, -73.7781)
_LAX = Point(33.9416, -118.4085)


class TestVincenty:
    def test_same_point_is_zero(self):
        assert Vincenty().calculate(_JFK, _JFK) == 0.0

    def test_known_pair_within_tolerance(self):
        distance = Vincenty().calculate(_JFK, _LAX)
        assert 3900 < distance < 4000

    def test_close_to_haversine_for_typical_distances(self):
        haversine_distance = Haversine().calculate(_JFK, _LAX)
        vincenty_distance = Vincenty().calculate(_JFK, _LAX)
        assert abs(haversine_distance - vincenty_distance) / vincenty_distance < 0.01
