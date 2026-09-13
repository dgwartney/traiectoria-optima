"""networkx-parity: do our answers match NetworkX's?

The question the instructor's Stage 2 milestone asks -- "validated against a
library reference" -- put to the world network.

Three hand-written algorithms are the project's deliverable, and 629 unit
tests say they behave as designed. They cannot say the design is *right* —
for that the same questions have to be put to an implementation that shares
no code with ours. NetworkX is that implementation, and any disagreement here
is a bug in one of the two.

The comparison runs through `PathfindingAlgorithm`, so NetworkX is not called
directly: it is wrapped as `NetworkXDijkstra`, `NetworkXBFS` and
`NetworkXAStar` and handed to the same `planner.find_shortest_route` every
other experiment uses. That makes the engine a *parameter*, and it means the
result being compared is the same kind of object in both cases — `Route` legs
with airlines and flight numbers, not node keys — so what is validated is the
whole answer rather than just a number.

The data is pinned by `experiment.toml` and verified on load: if a byte of the
snapshot changes, this script raises instead of quietly producing a different
answer.

Run it from anywhere:
    uv run python experiments/networkx-parity/run.py
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import networkx as nx

from flight_planner.experiments import Experiment
from flight_planner.geo import haversine_heuristic
from flight_planner.pathfinding import AStar, BFS, Dijkstra
from validation import (
    NetworkXAStar,
    NetworkXBFS,
    NetworkXDijkstra,
    NetworkXView,
    environment,
    median_ms,
)


def collapse_cost(planner) -> Dict[str, int]:
    """Measure what a `DiGraph` would have discarded.

    The mirror is a `MultiDiGraph`, and this is the number that justifies it.
    Recorded rather than asserted in a comment, because a future reader
    weighing "why not the simpler graph type?" deserves the figure.

    Args:
        planner: The flight network.

    Returns:
        Mapping of the route count, the distinct airport-pair count, and the
        difference — routes a collapsing graph type would drop.
    """
    pairs = {
        (route.origin.iata_code, route.destination.iata_code)
        for route in planner.edges
    }
    return {
        "routes": len(planner.edges),
        "airport_pairs": len(pairs),
        "routes_a_digraph_would_discard": len(planner.edges) - len(pairs),
    }


def compare(
    planner,
    pairs: Sequence[Tuple[str, str]],
    ours,
    theirs,
    tolerance: float,
) -> Dict[str, Any]:
    """Run both engines over `pairs` and describe where they differ.

    Costs are the durable contract and are compared first. Paths are compared
    second and reported without being treated as a failure: with up to 20
    parallel routes between one airport pair, ties are common and the two
    libraries may break them differently while both being right.

    Args:
        planner: The flight network.
        pairs: Ordered `(origin, destination)` IATA-code pairs.
        ours: A `flight_planner` engine.
        theirs: The corresponding NetworkX engine.
        tolerance: Relative tolerance for comparing costs.

    Returns:
        Mapping summarizing agreement, including every disagreement found so
        a non-zero count can be investigated rather than merely noticed.
    """
    mismatches: List[Dict[str, Any]] = []
    worst = 0.0
    identical_paths = 0
    identical_flights = 0
    unreachable = 0

    for origin, destination in pairs:
        mine = planner.search_route(origin, destination, ours)
        yours = planner.search_route(origin, destination, theirs)

        if math.isinf(mine.cost) and math.isinf(yours.cost):
            unreachable += 1
            continue

        divergence = abs(mine.cost - yours.cost)
        worst = max(worst, divergence)
        if not math.isclose(mine.cost, yours.cost, rel_tol=tolerance):
            mismatches.append(
                {
                    "pair": f"{origin}-{destination}",
                    "ours": mine.cost,
                    "theirs": yours.cost,
                }
            )

        my_route = [leg.destination.iata_code for leg in mine.path]
        your_route = [leg.destination.iata_code for leg in yours.path]
        if my_route == your_route:
            identical_paths += 1
            if [leg.flight_number for leg in mine.path] == [
                leg.flight_number for leg in yours.path
            ]:
                identical_flights += 1

    checked = len(pairs) - unreachable
    return {
        "pairs_checked": checked,
        "unreachable_pairs": unreachable,
        "cost_mismatches": len(mismatches),
        "mismatches": mismatches,
        "largest_absolute_divergence_km": worst,
        "identical_paths": identical_paths,
        "identical_flight_numbers": identical_flights,
    }


def named_pairs_table(
    planner, pairs: Sequence[Sequence[str]], heuristic
) -> List[Dict[str, Any]]:
    """Build the per-pair table the report prints.

    Args:
        planner: The flight network.
        pairs: The named long-haul pairs from `experiment.toml`.
        heuristic: Great-circle heuristic over airports.

    Returns:
        One row per pair, carrying each engine's cost and our own expansion
        counts. NetworkX's counters are absent rather than zero here, since a
        column of zeros in a comparison table invites being read as a result.
    """
    engines = {
        "Dijkstra": Dijkstra(),
        "BFS": BFS(),
        "A*": AStar(heuristic),
        "nx Dijkstra": NetworkXDijkstra(),
        "nx BFS": NetworkXBFS(),
        "nx A*": NetworkXAStar(heuristic),
    }

    rows: List[Dict[str, Any]] = []
    for origin, destination in pairs:
        row: Dict[str, Any] = {"pair": f"{origin}-{destination}"}
        costs: Dict[str, float] = {}
        units: Dict[str, str] = {}
        expanded: Dict[str, int] = {}
        legs: Dict[str, int] = {}
        for name, engine in engines.items():
            result = planner.search_route(origin, destination, engine)
            costs[name] = result.cost
            # BFS's cost is a hop count and the others' are kilometres. Both
            # land in one `cost` mapping, so the unit has to travel with them
            # -- a reader of results.json has only the JSON, not the prose.
            units[name] = result.unit
            legs[name] = len(result.path)
            if not name.startswith("nx "):
                expanded[name] = result.nodes_expanded
        row["cost"] = costs
        row["cost_unit"] = units
        row["legs"] = legs
        row["expanded"] = expanded
        rows.append(row)
    return rows


def time_engines(
    planner, pairs: Sequence[Tuple[str, str]], heuristic, repeats: int
) -> Dict[str, float]:
    """Time each engine over the whole sample.

    Not a leaderboard, and the report says so: NetworkX walks dicts of dicts
    keyed by strings while `flight_planner` walks objects and allocates
    `Route` lists. The useful reading is the ratio between our own engines,
    and the modest observation that ours are in the same class as a mature
    library's.

    Args:
        planner: The flight network.
        pairs: Pairs to sweep.
        heuristic: Great-circle heuristic over airports.
        repeats: Timed runs per engine, median reported.

    Returns:
        Mapping from engine name to median milliseconds for the whole sweep.
    """
    engines = {
        "Dijkstra": Dijkstra(),
        "BFS": BFS(),
        "A*": AStar(heuristic),
        "nx Dijkstra": NetworkXDijkstra(),
        "nx BFS": NetworkXBFS(),
        "nx A*": NetworkXAStar(heuristic),
    }

    timings: Dict[str, float] = {}
    for name, engine in engines.items():

        def sweep(engine=engine):
            for origin, destination in pairs:
                planner.find_shortest_route(origin, destination, engine)

        timings[name] = median_ms(sweep, repeats=repeats)
    return timings


def main() -> int:
    """Run the experiment and record what it found.

    Returns:
        Process exit status. Non-zero if the two libraries disagreed, since a
        parity experiment that finds a disagreement has found a bug and
        should not exit quietly.
    """
    # A script must locate itself: Path.cwd() is wherever you ran it from.
    experiment = Experiment.open(Path(__file__).resolve().parent)
    parameters = experiment.parameters

    # Opening the snapshot re-hashes every file against the manifest.
    snapshot = experiment.snapshot
    print(f"{experiment.slug}: snapshot {snapshot.snapshot_id}")

    # No narrowing: the whole world, so "long haul" means something.
    catalog = experiment.catalog()
    planner = catalog.planner()
    view = NetworkXView(planner)
    heuristic = haversine_heuristic()

    print(f"  airports {view.order:,}  routes {view.size:,}")
    graph = collapse_cost(planner)
    assert view.order == len(planner.vertices), "the mirror lost an airport"
    assert view.size == len(planner.edges), "the mirror lost a route"
    print(
        f"  a DiGraph would discard "
        f"{graph['routes_a_digraph_would_discard']:,} of {graph['routes']:,} routes"
    )

    sample = view.reachable_pairs(
        parameters["sample_pairs"], seed=parameters["sample_seed"]
    )
    tolerance = parameters["tolerance"]

    parity: Dict[str, Any] = {}
    for name, ours, theirs in (
        ("Dijkstra", Dijkstra(), NetworkXDijkstra()),
        ("BFS", BFS(), NetworkXBFS()),
        ("A*", AStar(heuristic), NetworkXAStar(heuristic)),
    ):
        parity[name] = compare(planner, sample, ours, theirs, tolerance)
        summary = parity[name]
        print(
            f"  {name:<9} {summary['pairs_checked']:>4} pairs  "
            f"{summary['cost_mismatches']} cost mismatches  "
            f"{summary['identical_paths']} identical paths  "
            f"worst {summary['largest_absolute_divergence_km']:.2e} km"
        )

    # The unreachable case, which the reachable sample deliberately excludes.
    # Both libraries must agree that there is no route, not merely agree on
    # the routes that exist.
    stranded = [
        (origin, destination)
        for origin, destination in view.ordered_pairs()[:400]
        if math.isinf(view.distance(origin, destination))
    ]
    unreachable_agreement = sum(
        1
        for origin, destination in stranded
        if math.isinf(
            planner.find_shortest_route(origin, destination, Dijkstra())[0]
        )
    )
    print(f"  unreachable  {unreachable_agreement}/{len(stranded)} agreed")

    table = named_pairs_table(planner, parameters["pairs"], heuristic)
    for row in table:
        print(
            f"  {row['pair']:<9} "
            f"ours {row['cost']['Dijkstra']:>10.3f} km  "
            f"nx {row['cost']['nx Dijkstra']:>10.3f} km  "
            f"A* expanded {row['expanded']['A*']:>4}  "
            f"Dijkstra expanded {row['expanded']['Dijkstra']:>5}"
        )

    timings = time_engines(planner, sample, heuristic, parameters["repeats"])
    for name, milliseconds in timings.items():
        print(f"  {name:<12} {milliseconds:8.1f} ms for {len(sample)} queries")

    disagreements = sum(summary["cost_mismatches"] for summary in parity.values())
    experiment.record(
        {
            "oracle": f"networkx {nx.__version__}",
            "graph": graph,
            "parity": parity,
            "unreachable": {
                "pairs_tested": len(stranded),
                "both_agree_no_route": unreachable_agreement,
            },
            "named_pairs": table,
            "sweep_ms": timings,
            "sweep_queries": len(sample),
            "environment": environment(),
            "total_cost_mismatches": disagreements,
        },
        catalog=catalog,
    )
    print(f"  recorded {experiment.results_path.name}")

    if disagreements:
        print(f"DISAGREEMENT: {disagreements} cost mismatches -- see results.json")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
