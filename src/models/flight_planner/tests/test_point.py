from point import Point
from distance.formula import DistanceFormula
from distance.haversine import Haversine


class _StubFormula(DistanceFormula):
    """Test double that records its inputs instead of computing anything."""

    def __init__(self):
        self.calls = []

    def calculate(self, a, b):
        self.calls.append((a, b))
        return 42.0


class TestPoint:
    def test_latitude_longitude_properties(self):
        p = Point(latitude=10.0, longitude=20.0)
        assert p.latitude == 10.0
        assert p.longitude == 20.0

    def test_defaults_to_zero(self):
        p = Point()
        assert p.latitude == 0.0
        assert p.longitude == 0.0

    def test_distance_to_defaults_to_haversine(self):
        a, b = Point(0.0, 0.0), Point(0.0, 1.0)
        assert a.distance_to(b) == Haversine().calculate(a, b)

    def test_distance_to_delegates_to_given_formula(self):
        a, b = Point(0.0, 0.0), Point(1.0, 1.0)
        stub = _StubFormula()

        result = a.distance_to(b, stub)

        assert result == 42.0
        assert stub.calls == [(a, b)]
