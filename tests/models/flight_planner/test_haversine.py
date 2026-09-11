from point import Point
from distance.haversine import Haversine

# JFK and LAX, real-world great-circle distance is ~3970 km.
_JFK = Point(40.6413, -73.7781)
_LAX = Point(33.9416, -118.4085)


class TestHaversine:
    def test_same_point_is_zero(self):
        assert Haversine().calculate(_JFK, _JFK) == 0.0

    def test_known_pair_within_tolerance(self):
        distance = Haversine().calculate(_JFK, _LAX)
        assert 3900 < distance < 4000

    def test_symmetric(self):
        haversine = Haversine()
        assert haversine.calculate(_JFK, _LAX) == haversine.calculate(_LAX, _JFK)
