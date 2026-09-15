"""The taxicab formula, and the properties that make it a useful counterexample.

`Manhattan` is committed to be wrong in a specific, measured way, so these
tests pin the *shape* of the wrongness as well as the arithmetic. Two of them
would fail on a plausible-looking implementation that nonetheless ruins the
experiment:

*   **The antimeridian wrap.** Without it a trans-Pacific pair is estimated
    going the long way round, and the overestimate is a bug rather than a
    property of the L1 norm.
*   **The shared radius.** `Manhattan` must measure on the same sphere as
    `Haversine`, so the comparison in `experiments/manhattan-heuristic`
    isolates the norm and is not confounded by a disagreement about the size
    of the Earth.
"""

from math import cos, radians

import pytest

from flight_planner.experiments import Snapshot
from flight_planner.geo import (
    Haversine,
    Manhattan,
    Point,
    manhattan_heuristic,
)
from flight_planner.geo.haversine import _EARTH_RADIUS_KM

SNAPSHOT_ID = "2026-09-11-bb90a8"

JFK = Point(40.6413, -73.7781)
ORD = Point(41.9742, -87.9073)
SYD = Point(-33.9461, 151.1772)

# Same latitude, so the meridian leg is zero and only the parallel leg is
# measured. Makes the cosine scaling testable in isolation.
EQUATOR_WEST = Point(0.0, 0.0)
EQUATOR_EAST = Point(0.0, 10.0)
LAT_SIXTY_WEST = Point(60.0, 0.0)
LAT_SIXTY_EAST = Point(60.0, 10.0)


@pytest.fixture(scope="module")
def world_routes(repo_root):
    """Every route in the world snapshot, for the inadmissibility guard."""
    snapshot = Snapshot.open(repo_root / "data" / "snapshots" / SNAPSHOT_ID)
    return snapshot.catalog().routes


class TestManhattan:
    def test_same_point_is_zero(self):
        assert Manhattan().calculate(JFK, JFK) == 0.0

    def test_is_symmetric(self):
        formula = Manhattan()

        assert formula.calculate(JFK, ORD) == pytest.approx(
            formula.calculate(ORD, JFK)
        )

    def test_is_the_sum_of_the_two_legs(self):
        """The formula, restated independently rather than re-run."""
        expected = _EARTH_RADIUS_KM * (
            abs(radians(ORD.latitude) - radians(JFK.latitude))
            + abs(radians(ORD.longitude) - radians(JFK.longitude))
            * cos((radians(JFK.latitude) + radians(ORD.latitude)) / 2)
        )

        assert Manhattan().calculate(JFK, ORD) == pytest.approx(expected)

    def test_a_pure_latitude_difference_is_an_exact_meridian_arc(self):
        """A meridian is a great circle, so this leg is not an approximation."""
        north = Point(10.0, 25.0)
        south = Point(0.0, 25.0)

        assert Manhattan().calculate(south, north) == pytest.approx(
            Haversine().calculate(south, north)
        )

    def test_the_parallel_leg_shrinks_with_latitude(self):
        """Ten degrees of longitude is a shorter arc at 60N than at the equator.

        cos(60 degrees) is exactly 0.5, so the higher-latitude pair should
        measure half of the equatorial one.
        """
        at_equator = Manhattan().calculate(EQUATOR_WEST, EQUATOR_EAST)
        at_sixty = Manhattan().calculate(LAT_SIXTY_WEST, LAT_SIXTY_EAST)

        assert at_sixty == pytest.approx(at_equator * 0.5)

    def test_it_measures_on_the_same_sphere_as_haversine(self):
        """Ten degrees along the equator is the same arc for both formulas.

        On the equator the parallel *is* a great circle and the latitude leg is
        zero, so the two formulas must agree exactly. They only can if they
        share an earth radius -- which is what keeps the experiment's
        comparison about the norm rather than about the sphere.
        """
        assert Manhattan().calculate(
            EQUATOR_WEST, EQUATOR_EAST
        ) == pytest.approx(Haversine().calculate(EQUATOR_WEST, EQUATOR_EAST))

    def test_an_antimeridian_pair_is_measured_the_short_way(self):
        """SYD-JFK spans 225 degrees of longitude, which is 135 the short way.

        Without the wrap the estimate would be larger still, and the formula
        would be overestimating for the wrong reason.
        """
        span_the_long_way = abs(SYD.longitude - JFK.longitude)
        assert span_the_long_way > 180.0  # the case exists

        wrapped = 360.0 - span_the_long_way
        expected = _EARTH_RADIUS_KM * (
            abs(radians(JFK.latitude) - radians(SYD.latitude))
            + radians(wrapped)
            * cos((radians(SYD.latitude) + radians(JFK.latitude)) / 2)
        )

        assert Manhattan().calculate(SYD, JFK) == pytest.approx(expected)

    def test_it_never_falls_below_the_flat_plane_l2_norm(self, world_routes):
        """L1 >= L2, which is why it is at least as inadmissible.

        `Equirectangular` in `src/demos/custom_distance_formula_example.py` is
        the same two legs combined with the L2 norm, and is presented there as
        a precision trade. This is the relationship that makes the L1 version a
        correctness one instead.
        """
        formula = Manhattan()

        for route in world_routes[:2000]:
            a, b = route.origin, route.destination
            lat1, lat2 = radians(a.latitude), radians(b.latitude)
            dlon = abs(a.longitude - b.longitude)
            x = radians(min(dlon, 360.0 - dlon)) * cos((lat1 + lat2) / 2)
            y = lat2 - lat1
            equirectangular = _EARTH_RADIUS_KM * (x**2 + y**2) ** 0.5

            assert formula.calculate(a, b) >= equirectangular - 1e-9


class TestManhattanHeuristic:
    def test_returns_a_callable_of_two_points(self):
        heuristic = manhattan_heuristic()

        assert heuristic(JFK, ORD) == pytest.approx(Manhattan().calculate(JFK, ORD))

    def test_memoized_and_uncached_agree(self):
        assert manhattan_heuristic()(JFK, ORD) == manhattan_heuristic(memoize=False)(
            JFK, ORD
        )

    def test_each_call_returns_an_independent_callable(self):
        first, second = manhattan_heuristic(), manhattan_heuristic()

        assert first is not second
        assert first(JFK, ORD) == second(JFK, ORD)

    def test_distance_to_self_is_zero(self):
        assert manhattan_heuristic()(JFK, JFK) == pytest.approx(0.0)


class TestInadmissibility:
    """The counterexample must keep being a counterexample.

    `experiments/manhattan-heuristic` rests on this formula overestimating,
    and a well-meaning "fix" -- switching to L2, or scaling the legs down --
    would leave the experiment's prose describing something the code no longer
    does. This is what notices.
    """

    def test_it_exceeds_almost_every_real_edge_weight(self, world_routes):
        formula = Manhattan()

        violations = sum(
            1
            for route in world_routes
            if formula.calculate(route.origin, route.destination)
            > route.distance_km + 1e-9
        )

        # 66,331 of 66,332 as recorded. The exception is a zero-length
        # self-loop, where every formula returns zero -- asserted below rather
        # than hidden in this margin.
        assert violations == len(world_routes) - 1

    def test_the_one_edge_it_does_not_exceed_is_a_zero_length_self_loop(
        self, world_routes
    ):
        formula = Manhattan()

        clean = [
            route
            for route in world_routes
            if formula.calculate(route.origin, route.destination)
            <= route.distance_km + 1e-9
        ]

        assert len(clean) == 1
        assert clean[0].distance_km == 0.0
        assert clean[0].origin.iata_code == clean[0].destination.iata_code
