from flight_planner.geo import Point
from flight_planner.geo import DistanceFormula
from flight_planner.geo import Memoized

_JFK = Point(40.6413, -73.7781)
_LAX = Point(33.9416, -118.4085)


class _CountingFormula(DistanceFormula):
    def __init__(self) -> None:
        self.calls = 0

    def calculate(self, a: Point, b: Point) -> float:
        self.calls += 1
        return 42.0


class TestMemoized:
    def test_caches_by_coordinate_value(self):
        counting = _CountingFormula()
        memoized = Memoized(counting)

        assert memoized.calculate(_JFK, _LAX) == 42.0
        assert memoized.calculate(_JFK, _LAX) == 42.0
        assert counting.calls == 1

    def test_cache_hit_across_distinct_instances_with_same_coordinates(self):
        counting = _CountingFormula()
        memoized = Memoized(counting)
        jfk_copy = Point(40.6413, -73.7781)

        memoized.calculate(_JFK, _LAX)
        memoized.calculate(jfk_copy, _LAX)

        assert counting.calls == 1

    def test_different_pairs_are_not_conflated(self):
        counting = _CountingFormula()
        memoized = Memoized(counting)

        memoized.calculate(_JFK, _LAX)
        memoized.calculate(_LAX, _JFK)

        assert counting.calls == 2
