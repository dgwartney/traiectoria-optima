"""The A* heuristic, and the invariant that makes it admissible.

The admissibility guard here is the point of the file. `haversine_heuristic`
is safe not because haversine is a universal lower bound on geodesic distance
-- it is not -- but because the pipeline generates `distance_km` with the same
formula and the same earth radius. That is an invariant between two pieces of
the project, and this is what enforces it.
"""

import pytest

from flight_planner.experiments import Snapshot
from flight_planner.geo import (
    Haversine,
    Manhattan,
    Point,
    Vincenty,
    haversine_heuristic,
)

SNAPSHOT_ID = "2026-09-11-bb90a8"

SFO = Point(37.6213, -122.3790)
BOS = Point(42.3620, -71.0079)


@pytest.fixture(scope="module")
def world_routes(repo_root):
    """Every route in the world snapshot, for the admissibility guard."""
    snapshot = Snapshot.open(repo_root / "data" / "snapshots" / SNAPSHOT_ID)
    return snapshot.catalog().routes


class TestHaversineHeuristic:
    def test_returns_a_callable_of_two_points(self):
        heuristic = haversine_heuristic()

        assert heuristic(SFO, BOS) == pytest.approx(Haversine().calculate(SFO, BOS))

    def test_memoized_and_uncached_agree(self):
        cached = haversine_heuristic()
        uncached = haversine_heuristic(memoize=False)

        assert cached(SFO, BOS) == uncached(SFO, BOS)

    def test_repeated_calls_are_stable(self):
        heuristic = haversine_heuristic()

        assert heuristic(SFO, BOS) == heuristic(SFO, BOS)

    def test_each_call_returns_an_independent_callable(self):
        first, second = haversine_heuristic(), haversine_heuristic()

        assert first is not second
        assert first(SFO, BOS) == second(SFO, BOS)

    def test_distance_to_self_is_zero(self):
        assert haversine_heuristic()(SFO, SFO) == pytest.approx(0.0)

    def test_is_symmetric(self):
        heuristic = haversine_heuristic()

        assert heuristic(SFO, BOS) == pytest.approx(heuristic(BOS, SFO))


class TestAdmissibilityInvariant:
    """The heuristic must never exceed the weight of any single edge.

    If it can overestimate one edge it can overestimate a path, and A* -- which
    closes a vertex on first expansion -- may then return a suboptimal route
    while reporting it as optimal. Silently.
    """

    def test_never_exceeds_any_real_edge_weight(self, world_routes):
        heuristic = haversine_heuristic()

        violations = [
            route
            for route in world_routes
            if heuristic(route.origin, route.destination) > route.distance_km + 1e-9
        ]

        assert not violations, (
            f"{len(violations)} of {len(world_routes)} edges have a heuristic "
            f"estimate above their own weight, so the heuristic is no longer "
            f"admissible and A* is no longer guaranteed optimal. This means the "
            f"data pipeline and flight_planner.geo.heuristic have stopped using "
            f"the same distance formula -- see src/data/flight_network.py."
        )

    def test_vincenty_would_fail_this_same_guard(self, world_routes):
        """Proof the guard above can actually fail, rather than being vacuous.

        Vincenty is the more physically accurate formula and the worse
        heuristic, because the edge weights are haversine numbers.
        """
        vincenty = Vincenty()

        violations = sum(
            1
            for route in world_routes[:5000]
            if vincenty.calculate(route.origin, route.destination)
            > route.distance_km + 1e-9
        )

        assert violations > 0

    def test_manhattan_would_fail_it_on_essentially_every_edge(self, world_routes):
        """The other way a heuristic goes wrong, and the far larger one.

        Vincenty shows the guard can fail by a precision margin -- a better
        formula measured on a different figure of the Earth. Manhattan shows it
        can fail by a factor: a formula that is not measuring the same thing at
        all. Between them they establish that the guard is about the
        relationship between the estimate and the weights, and not about
        accuracy.

        Measured and explained in `experiments/manhattan-heuristic`.
        """
        manhattan = Manhattan()

        violations = sum(
            1
            for route in world_routes
            if manhattan.calculate(route.origin, route.destination)
            > route.distance_km + 1e-9
        )

        # Every edge but one, which is a zero-length self-loop. Asserted
        # exactly rather than as "most", so a formula change that quietly
        # halved the overestimate would still be caught here.
        assert violations == len(world_routes) - 1
