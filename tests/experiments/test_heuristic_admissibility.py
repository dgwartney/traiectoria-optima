"""Re-derive the admissibility figures §4.3 rests its argument on.

§4.3 is the report's highest-stakes claim: that A* returns Dijkstra's answer
and is *guaranteed* to. That guarantee is not a property of geometry here --
it is an invariant between `src/data/flight_network.py` and
`flight_planner.geo.heuristic`, which both have to keep using the same formula
at the same earth radius. An invariant nobody checks is a coincidence, so this
re-derives it from the pinned snapshot rather than trusting the recorded
answer.

The expensive part of the experiment -- 6.6 million consistency checks -- is
not repeated here. This file re-derives the per-edge invariant over all 66,332
edges, which is the property that would actually break, and asserts the rest
against `results.json`.
"""

import json

import pytest

from flight_planner.experiments import Experiment
from flight_planner.geo import Haversine, Vincenty, haversine_heuristic

SLUG = "heuristic-admissibility"
SNAPSHOT_ID = "2026-09-11-bb90a8"


@pytest.fixture(scope="module")
def experiment(repo_root):
    """Open the committed experiment, verifying its snapshot on the way."""
    return Experiment.open(repo_root / "experiments" / SLUG)


@pytest.fixture(scope="module")
def recorded(repo_root):
    """Return the committed `results.json` payload."""
    path = repo_root / "experiments" / SLUG / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))["results"]


@pytest.fixture(scope="module")
def routes(experiment):
    """Every route in the pinned snapshot."""
    return experiment.snapshot.catalog().routes


def test_it_pins_the_world_snapshot(experiment, recorded):
    assert experiment.snapshot.snapshot_id == SNAPSHOT_ID
    assert recorded["graph"] == {"airports": 3387, "routes": 66332}


def test_the_two_radii_still_differ(recorded):
    """The whole Vincenty argument turns on these not being the same number."""
    radii = recorded["radii"]
    assert radii["haversine_sphere_km"] == 6371.0
    assert radii["vincenty_wgs84_semi_major_km"] == 6378.137


class TestPipelineInvariant:
    """The property §4.3's guarantee actually rests on.

    Re-derived rather than read, because this is the one that breaks if the
    data pipeline's distance formula or earth radius ever changes.
    """

    def test_no_edge_estimate_exceeds_its_own_weight(self, routes, recorded):
        heuristic = haversine_heuristic(memoize=False)
        epsilon = 1e-9

        violations = [
            route
            for route in routes
            if heuristic(route.origin, route.destination) > route.distance_km + epsilon
        ]

        assert not violations, (
            f"{len(violations)} of {len(routes)} edges estimate above their own "
            "weight. A* is no longer guaranteed optimal, and the cause is that "
            "src/data/flight_network.py and flight_planner.geo.heuristic have "
            "stopped agreeing on the distance formula or the earth radius."
        )
        assert recorded["pipeline_invariant"]["violations"] == 0
        assert recorded["pipeline_invariant"]["checked"] == len(routes)

    def test_the_margin_is_rounding_rather_than_slack(self, recorded):
        """Zero plus float noise, not a small positive margin.

        The estimate and the weight are the same computation run twice, so the
        honest statement is that they are equal to the last bit -- not that
        the heuristic comes in comfortably under.
        """
        worst = recorded["pipeline_invariant"]["worst_excess_km"]
        assert 0 < worst < 1e-9, worst

    def test_consistency_was_checked_and_held(self, recorded):
        """Consistency, not admissibility, is what this A* implementation needs.

        Asserted from the record rather than re-run: 6.6 million checks is
        about nine seconds, which does not belong in the default suite.
        `uv run python experiments/heuristic-admissibility/run.py` redoes it.
        """
        consistency = recorded["consistency"]
        assert consistency["violations"] == 0
        assert consistency["checks"] == 6_633_200
        assert consistency["worst_violation_km"] < 1e-9


class TestPrecisionIsNotAdmissibility:
    """The counterintuitive half, and the reason §4.3 is worth writing.

    A more physically accurate distance formula makes A* *less* correct here,
    because the edge weights are haversine numbers. These two tests are what
    stop that from being an assertion.
    """

    def test_haversine_is_not_a_lower_bound_on_the_geodesic(self, routes, recorded):
        """The textbook intuition is wrong on this data, and measurably so."""
        haversine, vincenty = Haversine(), Vincenty()

        exceeds = sum(
            1
            for route in routes
            if haversine.calculate(route.origin, route.destination)
            > vincenty.calculate(route.origin, route.destination)
        )

        assert exceeds == recorded["formulas"]["haversine_exceeds_geodesic"]["violations"]
        assert exceeds > 0, (
            "haversine no longer exceeds the WGS-84 geodesic anywhere, which "
            "would make the argument in geo/haversine.py's docstring false"
        )

    def test_vincenty_would_break_the_invariant_haversine_satisfies(self, routes, recorded):
        """Proof the invariant test above is not vacuous.

        Swapping in the more accurate formula fails the very guard the
        shipped one passes with zero violations.
        """
        vincenty = Vincenty()

        violations = sum(
            1
            for route in routes
            if vincenty.calculate(route.origin, route.destination)
            > route.distance_km + 1e-9
        )

        recorded_violations = recorded["formulas"][
            "vincenty_as_heuristic_would_violate"
        ]["violations"]
        assert violations == recorded_violations
        assert violations > recorded["pipeline_invariant"]["violations"]


def test_the_superseded_docstring_figures_are_still_traceable(recorded):
    """The earlier docstrings quoted a leading slice; keep it resolvable.

    `geo/haversine.py` and `geo/heuristic.py` used to cite 1,905 and 3,095
    "of 5,000 pairs". That turned out to mean the first 5,000 routes in
    snapshot order. Recording the slice means those numbers can be traced to
    a method rather than looking as though they were dropped.
    """
    legacy = recorded["formulas"]["legacy_leading_slice"]
    assert legacy["size"] == 5000
    assert legacy["haversine_exceeds_geodesic"]["violations"] == 1905
    assert legacy["vincenty_as_heuristic_would_violate"]["violations"] == 3095
