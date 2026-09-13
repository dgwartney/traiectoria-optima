"""heuristic-admissibility: why this heuristic is safe, and a better one is not.

A* returns an optimal path only if its heuristic never overestimates the cost
still to go. Report §4.3 claims this project's heuristic clears that bar, and
makes a second, less obvious claim alongside it: that **Vincenty, the more
physically accurate formula, would be the worse heuristic.** Both claims lived
only in module docstrings, reproduced by nothing. This experiment is what
makes them evidence.

The argument has three steps, and each one is a section of the output.

**One: admissibility here is an invariant, not a theorem.** Haversine is not a
universal lower bound on geodesic distance. It is safe in *this* graph because
`src/data/flight_network.py` generates the `distance_km` column with the same
`Haversine()` at the same 6371.0 km radius, so the estimate and the weights
are one measurement rather than two. A great-circle arc is never longer than a
chain of great-circle arcs between the same endpoints, so `h` cannot exceed
the true remaining cost. That holds only while the pipeline and the heuristic
agree, which makes it a property of the build rather than of geometry.

**Two: the invariant is what the data is checked against.** Every edge, with
no sampling.

**Three: precision and admissibility are different properties.** Swapping in
Vincenty -- measured on the WGS-84 ellipsoid, semi-major axis 6378.137 km --
makes the estimates *more* accurate and the search *less* correct, because the
weights are still haversine numbers. This section counts how often that breaks
the bar the previous section clears.

A note on method. The docstrings this replaces quoted figures over "5,000
pairs", which turned out to mean the first 5,000 routes in snapshot order --
deterministic, but arbitrary, and not evidently reproducible. The whole edge
set takes 0.4 seconds, so this samples nothing it does not have to. The one
place a sample is unavoidable is the consistency sweep, where every goal would
be 224.6 million checks; there the goals are drawn from a recorded seed.

The data is pinned by `experiment.toml` and verified on load: if a byte of the
snapshot changes, this script raises instead of quietly producing a different
answer.

Run it from anywhere:
    uv run python experiments/heuristic-admissibility/run.py
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List, Sequence

from flight_planner.experiments import Experiment
from flight_planner.geo import Haversine, Vincenty, haversine_heuristic
from flight_planner.geo.haversine import _EARTH_RADIUS_KM as HAVERSINE_RADIUS_KM
from flight_planner.geo.vincenty import _SEMI_MAJOR_AXIS_KM as VINCENTY_SEMI_MAJOR_KM


def summarise(excesses: Sequence[float], epsilon: float, total: int) -> Dict[str, Any]:
    """Reduce a list of signed excesses to the four numbers that matter.

    An *excess* is `estimate - truth`: positive means the estimate is above
    the value it must not exceed, which is what breaks admissibility.

    Args:
        excesses: Signed `estimate - truth` per edge, in kilometres.
        epsilon: Below this, a positive excess is float noise rather than a
            breach.
        total: Population the excesses were drawn from.

    Returns:
        Mapping of the violation count, its share, the worst excess, and the
        largest margin by which the estimate came in *under* the truth.
    """
    violations = [value for value in excesses if value > epsilon]
    return {
        "checked": total,
        "violations": len(violations),
        "violation_rate": len(violations) / total if total else 0.0,
        # Signed, so a clean run reports a negative number -- the estimate's
        # closest approach to the bound rather than a bare "zero violations".
        "worst_excess_km": max(excesses) if excesses else 0.0,
        "largest_understatement_km": -min(excesses) if excesses else 0.0,
    }


def pipeline_invariant(routes, epsilon: float) -> Dict[str, Any]:
    """Check the heuristic against the weight of every edge in the graph.

    This is the single-edge case of admissibility, and it is the one that can
    actually fail: if the estimate can exceed one edge it can exceed a path,
    and A* -- which closes a vertex on first expansion -- would then return a
    longer route and report it as optimal, silently.

    Args:
        routes: Every route in the snapshot.
        epsilon: Tolerance in kilometres.

    Returns:
        The summary from `summarise`, plus the worst edge by excess so a
        reader can check one case rather than only a total.
    """
    heuristic = haversine_heuristic(memoize=False)
    excesses = [
        heuristic(route.origin, route.destination) - route.distance_km
        for route in routes
    ]
    result = summarise(excesses, epsilon, len(routes))
    worst = routes[excesses.index(max(excesses))]
    result["worst_edge"] = {
        "origin": worst.origin.iata_code,
        "destination": worst.destination.iata_code,
        "weight_km": worst.distance_km,
        "estimate_km": heuristic(worst.origin, worst.destination),
    }
    return result


def consistency(routes, airports, goals: int, seed: int, epsilon: float) -> Dict[str, Any]:
    """Check `h(u) <= w(u, v) + h(v)` over every edge, against sampled goals.

    Consistency, not admissibility, is what this implementation actually
    requires: it closes a vertex permanently when popped, so an admissible but
    inconsistent heuristic can still produce a wrong answer. `astar-consistency`
    establishes that on random graphs and on the 94-airport slice; this asks
    the same question of the whole world network.

    Args:
        routes: Every route in the snapshot.
        airports: Every airport, to draw goals from.
        goals: How many goals to sample.
        seed: Seed for the goal sample, recorded so the answer is
            reproducible rather than merely repeatable.
        epsilon: Tolerance in kilometres.

    Returns:
        Checks performed, violations, and the worst breach of the triangle
        inequality found.
    """
    heuristic = haversine_heuristic(memoize=False)
    sampled = random.Random(seed).sample(list(airports), min(goals, len(airports)))

    checks = 0
    violations = 0
    worst = 0.0
    for goal in sampled:
        for route in routes:
            checks += 1
            # Positive slack means the inequality holds with room to spare.
            slack = (
                route.distance_km
                + heuristic(route.destination, goal)
                - heuristic(route.origin, goal)
            )
            if slack < -epsilon:
                violations += 1
            worst = max(worst, -slack)
    return {
        "goals_sampled": len(sampled),
        "goals_available": len(airports),
        "checks": checks,
        "violations": violations,
        "worst_violation_km": worst,
    }


def formula_comparison(routes, epsilon: float, legacy_slice: int) -> Dict[str, Any]:
    """Compare haversine against the WGS-84 geodesic, two ways.

    The first comparison answers "does haversine underestimate the geodesic?",
    which the textbook intuition says yes to and the data says no. The second
    answers the question that actually decides the heuristic: "would Vincenty
    exceed the edge weights?"

    Args:
        routes: Every route in the snapshot.
        epsilon: Tolerance in kilometres.
        legacy_slice: Size of the leading slice the superseded docstring
            figures were measured over, recorded for traceability.

    Returns:
        Both comparisons over the full edge set, and both again over the
        legacy slice.
    """
    haversine, vincenty = Haversine(), Vincenty()

    # estimate - truth, for each of the two questions.
    versus_geodesic: List[float] = []
    vincenty_versus_weight: List[float] = []
    for route in routes:
        spherical = haversine.calculate(route.origin, route.destination)
        ellipsoidal = vincenty.calculate(route.origin, route.destination)
        versus_geodesic.append(spherical - ellipsoidal)
        vincenty_versus_weight.append(ellipsoidal - route.distance_km)

    head = slice(0, legacy_slice)
    return {
        "haversine_exceeds_geodesic": summarise(versus_geodesic, 0.0, len(routes)),
        "vincenty_as_heuristic_would_violate": summarise(
            vincenty_versus_weight, epsilon, len(routes)
        ),
        # The superseded docstrings quoted these. Kept so their figures can be
        # traced to a slice rather than appearing to have been invented.
        "legacy_leading_slice": {
            "size": legacy_slice,
            "haversine_exceeds_geodesic": summarise(
                versus_geodesic[head], 0.0, legacy_slice
            ),
            "vincenty_as_heuristic_would_violate": summarise(
                vincenty_versus_weight[head], epsilon, legacy_slice
            ),
        },
    }


def main() -> int:
    """Run the experiment and record its answer.

    Returns:
        Process exit status. Non-zero if the invariant is broken, so a
        pipeline change that silently breaks A* fails here rather than
        producing a quietly wrong route map.
    """
    experiment = Experiment.open(Path(__file__).parent)
    parameters = experiment.parameters
    epsilon = parameters["epsilon_km"]

    catalog = experiment.snapshot.catalog()
    routes, airports = catalog.routes, catalog.airports

    invariant = pipeline_invariant(routes, epsilon)
    triangle = consistency(
        routes,
        airports,
        parameters["consistency_goals"],
        parameters["goal_sample_seed"],
        epsilon,
    )
    formulas = formula_comparison(routes, epsilon, parameters["legacy_slice"])

    results = {
        "graph": {"airports": len(airports), "routes": len(routes)},
        # The whole argument turns on these two constants differing.
        "radii": {
            "haversine_sphere_km": HAVERSINE_RADIUS_KM,
            "vincenty_wgs84_semi_major_km": VINCENTY_SEMI_MAJOR_KM,
        },
        "pipeline_invariant": invariant,
        "consistency": triangle,
        "formulas": formulas,
    }
    experiment.record(results)

    print(f"airports {len(airports):,}  routes {len(routes):,}")
    print(
        f"invariant:   {invariant['violations']} violations of "
        f"{invariant['checked']:,} edges, worst excess "
        f"{invariant['worst_excess_km']:.9f} km"
    )
    print(
        f"consistency: {triangle['violations']} violations of "
        f"{triangle['checks']:,} checks over {triangle['goals_sampled']} goals, "
        f"worst {triangle['worst_violation_km']:.2e} km"
    )
    exceeds = formulas["haversine_exceeds_geodesic"]
    print(
        f"haversine exceeds the WGS-84 geodesic on {exceeds['violations']:,} of "
        f"{exceeds['checked']:,} edges, by up to "
        f"{exceeds['worst_excess_km']:.2f} km"
    )
    would = formulas["vincenty_as_heuristic_would_violate"]
    print(
        f"vincenty as heuristic would violate on {would['violations']:,} of "
        f"{would['checked']:,} edges, by up to {would['worst_excess_km']:.2f} km"
    )

    broken = invariant["violations"] or triangle["violations"]
    if broken:
        print("\nADMISSIBILITY IS BROKEN -- A* is no longer guaranteed optimal.")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
