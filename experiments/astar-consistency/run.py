"""astar-consistency: admissible, or consistent?

`AStar`'s docstring promises an optimal path for any *admissible* heuristic —
one that never overestimates the remaining cost. Its implementation closes a
vertex when it is popped and never reconsiders it, which is only sound under
the stronger condition of *consistency*: `h(u) <= w(u, v) + h(v)` for every
edge. This experiment measures the gap between the two claims.

It has two halves, and they ask different questions of different data.

**Half one, on random graphs.** The project's own data cannot expose this.
Great-circle distance is consistent as a matter of geometry, so no quantity
of real routes reaches the case. Fifty random graphs with a heuristic that is
admissible by construction and inconsistent on purpose reach it immediately,
with NetworkX — whose A* reopens nodes, and so is optimal for any admissible
heuristic — as the oracle.

**Half two, on the snapshot.** Having established the defect, the question
that actually matters to this project is whether it bites *here*. That is a
question only the real data answers, and answering it is what earns this
experiment its snapshot pin rather than being a unit test: it checks the
triangle inequality across every edge and every possible goal, then confirms
A* and Dijkstra agree on every pair.

The data is pinned by `experiment.toml` and verified on load: if a byte of the
snapshot changes, this script raises instead of quietly producing a different
answer.

Run it from anywhere:
    uv run python experiments/astar-consistency/run.py
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List

import networkx as nx

from flight_planner.core import Edge, Graph, Vertex
from flight_planner.experiments import Experiment
from flight_planner.geo import haversine_heuristic
from flight_planner.pathfinding import AStar, Dijkstra
from validation import (
    InconsistentHeuristic,
    RandomGraphPair,
    ReopeningAStar,
    environment,
)


def minimal_case() -> Dict[str, Any]:
    r"""Reduce the defect to four vertices.

    An aggregate over 10,000 random queries proves a defect exists; it does
    not let a reader see it. This is the smallest graph that does, and the one
    the report prints:

    ```
    S --2.0--> A --1.0--> G
     \\                    /
      1.0--> B --0.5--> A
    ```

    The optimum is `S -> B -> A -> G` at 2.5. `h(S) = 0` while `h(B) = 1.5`
    across an edge of weight 1.0, so the heuristic is admissible — no estimate
    exceeds the true remaining cost — but inconsistent. `AStar` pops `A` early
    carrying the 2.0 route, closes it, and never propagates the improvement
    that arrives via `B`.

    Returns:
        Mapping of each engine's cost, the sum of the legs it returned, and
        the route itself. The gap between cost and leg-sum is the second,
        worse half of the defect.
    """
    graph: Graph[Vertex, Edge] = Graph()
    start, a, b, goal = Vertex("S"), Vertex("A"), Vertex("B"), Vertex("G")
    for edge in (
        Edge(start, a, 2.0),
        Edge(start, b, 1.0),
        Edge(b, a, 0.5),
        Edge(a, goal, 1.0),
    ):
        graph.add_edge(edge)

    admissible = {"S": 0.0, "B": 1.5, "A": 0.0, "G": 0.0}

    def heuristic(vertex, _goal):
        return admissible[vertex.key]

    described: Dict[str, Any] = {"heuristic": admissible, "optimum": 2.5}
    for name, engine in (
        ("Dijkstra", Dijkstra()),
        ("AStar", AStar(heuristic)),
        ("ReopeningAStar", ReopeningAStar(heuristic)),
    ):
        result = engine.search(graph, start, goal)
        described[name] = {
            "cost": result.cost,
            "legs_sum_to": sum(leg.weight for leg in result.path),
            "route": "->".join(["S"] + [leg.target.key for leg in result.path]),
            "nodes_expanded": result.nodes_expanded,
        }
    return described


def randomized_sweep(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Compare both A* implementations against NetworkX on random graphs.

    Every ordered pair of every graph, with a fresh heuristic per goal — a
    heuristic is only admissible with respect to one goal, so one instance per
    goal is required rather than merely tidy.

    Args:
        parameters: The experiment's declared parameters.

    Returns:
        Mapping of query count, how often each implementation was suboptimal,
        how often the shipped one reported a cost its own path contradicts,
        the expansion totals, and the first failure found — so a reader can
        reproduce one case rather than only read a total.
    """
    tolerance = parameters["tolerance"]
    mask = parameters["heuristic_seed_mask"]

    queries = 0
    shipped_suboptimal = 0
    shipped_contradictory = 0
    reopening_suboptimal = 0
    oracle_suboptimal = 0
    inconsistent_goals = 0
    total_goals = 0
    expansions = {"AStar": 0, "ReopeningAStar": 0}
    first_failure: Dict[str, Any] = {}

    for seed in range(parameters["seeds"]):
        pair = RandomGraphPair(
            seed,
            max_order=parameters["max_order"],
            density=parameters["density"],
        )
        for goal in pair.vertices:
            heuristic = InconsistentHeuristic(pair, goal, seed ^ mask)
            total_goals += 1
            if not heuristic.is_consistent(pair):
                inconsistent_goals += 1
            # Every conclusion below rests on this, so it is verified per
            # goal rather than trusted to the constructor.
            assert heuristic.is_admissible(pair), f"seed={seed} goal={goal.key}"

            for start in pair.vertices:
                if start == goal:
                    continue
                queries += 1
                optimal = pair.distance(start, goal)

                shipped = AStar(heuristic).search(pair.ours, start, goal)
                fixed = ReopeningAStar(heuristic).search(pair.ours, start, goal)
                try:
                    theirs = nx.astar_path_length(
                        pair.theirs,
                        start.key,
                        goal.key,
                        heuristic=heuristic.over_keys,
                        weight="weight",
                    )
                except nx.NetworkXNoPath:
                    theirs = math.inf

                expansions["AStar"] += shipped.nodes_expanded
                expansions["ReopeningAStar"] += fixed.nodes_expanded

                def off(cost: float, optimal: float = optimal) -> bool:
                    if math.isinf(cost) and math.isinf(optimal):
                        return False
                    return not math.isclose(cost, optimal, rel_tol=tolerance)

                if off(shipped.cost):
                    shipped_suboptimal += 1
                    if not first_failure:
                        first_failure = {
                            "seed": seed,
                            "pair": f"{start.key}->{goal.key}",
                            "astar": shipped.cost,
                            "optimal": optimal,
                        }
                if off(fixed.cost):
                    reopening_suboptimal += 1
                if off(theirs):
                    oracle_suboptimal += 1
                if shipped.path and not math.isclose(
                    sum(leg.weight for leg in shipped.path),
                    shipped.cost,
                    rel_tol=tolerance,
                ):
                    shipped_contradictory += 1

    overhead = (
        expansions["ReopeningAStar"] / expansions["AStar"] - 1.0
        if expansions["AStar"]
        else 0.0
    )
    return {
        "graphs": parameters["seeds"],
        "queries": queries,
        "goals": total_goals,
        "inconsistent_goals": inconsistent_goals,
        "astar_suboptimal": shipped_suboptimal,
        "astar_cost_contradicts_its_path": shipped_contradictory,
        "reopening_astar_suboptimal": reopening_suboptimal,
        "networkx_astar_suboptimal": oracle_suboptimal,
        "nodes_expanded": expansions,
        "reopening_expansion_overhead": overhead,
        "first_failure": first_failure,
    }


def heuristic_consistency(planner, epsilon: float) -> Dict[str, Any]:
    """Check the triangle inequality over every edge and every goal.

    Consistency is `h(u) <= w(u, v) + h(v)`. For the great-circle heuristic
    that reads: the direct distance from `u` to the goal never exceeds the
    distance flown from `u` to `v` plus the direct distance from `v` to the
    goal. That is the triangle inequality on a sphere, and it holds as long as
    no route in the data is shorter than the great circle it spans — which is
    a property of the *data*, not of geometry, and so is measured rather than
    assumed.

    Args:
        planner: The flight network.
        epsilon: Kilometres of slack. Below this a violation is float noise in
            the haversine sum, not a real breach.

    Returns:
        Mapping of the number of checks, the number of violations, and the
        worst violation in kilometres.
    """
    heuristic = haversine_heuristic()
    checks = 0
    violations = 0
    worst = 0.0

    for goal in planner.vertices:
        for route in planner.edges:
            checks += 1
            direct = heuristic(route.origin, goal)
            through = route.distance_km + heuristic(route.destination, goal)
            excess = direct - through
            if excess > epsilon:
                violations += 1
                worst = max(worst, excess)

    return {
        "checks": checks,
        "violations": violations,
        "worst_violation_km": worst,
    }


def astar_matches_dijkstra(planner, heuristic, tolerance: float) -> Dict[str, Any]:
    """Confirm the two agree on every ordered pair of the snapshot.

    The consequence of consistency, stated as a measurement: if the heuristic
    is consistent then `AStar`'s closed set costs nothing, and this is where
    that shows up.

    Args:
        planner: The flight network.
        heuristic: Great-circle heuristic over airports.
        tolerance: Relative tolerance for comparing costs.

    Returns:
        Mapping of pairs checked, mismatches, and the expansion totals — which
        are the project's central claim on the same data.
    """
    codes = sorted(airport.iata_code for airport in planner.vertices)
    mismatches: List[Dict[str, Any]] = []
    expansions = {"Dijkstra": 0, "AStar": 0, "ReopeningAStar": 0}
    checked = 0

    for origin in codes:
        for destination in codes:
            if origin == destination:
                continue
            checked += 1
            dijkstra = planner.search_route(origin, destination, Dijkstra())
            astar = planner.search_route(origin, destination, AStar(heuristic))
            reopening = planner.search_route(
                origin, destination, ReopeningAStar(heuristic)
            )
            expansions["Dijkstra"] += dijkstra.nodes_expanded
            expansions["AStar"] += astar.nodes_expanded
            expansions["ReopeningAStar"] += reopening.nodes_expanded

            for name, result in (("AStar", astar), ("ReopeningAStar", reopening)):
                if math.isinf(result.cost) and math.isinf(dijkstra.cost):
                    continue
                if not math.isclose(result.cost, dijkstra.cost, rel_tol=tolerance):
                    mismatches.append(
                        {
                            "pair": f"{origin}-{destination}",
                            "engine": name,
                            "cost": result.cost,
                            "dijkstra": dijkstra.cost,
                        }
                    )

    return {
        "pairs_checked": checked,
        "mismatches": mismatches,
        "nodes_expanded": expansions,
        "patch_changes_expansions": (
            expansions["ReopeningAStar"] != expansions["AStar"]
        ),
    }


def main() -> int:
    """Run the experiment and record what it found.

    Returns:
        Process exit status. Non-zero only if the *snapshot* half finds a
        problem — an inconsistent real heuristic, or A* disagreeing with
        Dijkstra on real data. The randomized half is expected to find the
        shipped A* suboptimal; that is the finding, not a failure.
    """
    experiment = Experiment.open(Path(__file__).resolve().parent)
    parameters = experiment.parameters

    snapshot = experiment.snapshot
    print(f"{experiment.slug}: snapshot {snapshot.snapshot_id}")

    print("\n-- the minimal case --")
    minimal = minimal_case()
    for name in ("Dijkstra", "AStar", "ReopeningAStar"):
        row = minimal[name]
        flag = "" if math.isclose(row["cost"], row["legs_sum_to"]) else "  <- disagree"
        print(
            f"  {name:<15} cost {row['cost']:.1f}  via {row['route']}  "
            f"legs sum {row['legs_sum_to']:.1f}{flag}"
        )

    print("\n-- randomized sweep --")
    sweep = randomized_sweep(parameters)
    print(f"  {sweep['graphs']} graphs, {sweep['queries']:,} queries")
    print(
        f"  inconsistent heuristics       "
        f"{sweep['inconsistent_goals']}/{sweep['goals']}"
    )
    print(f"  AStar suboptimal              {sweep['astar_suboptimal']}")
    print(
        f"    of those, cost != path sum  "
        f"{sweep['astar_cost_contradicts_its_path']}"
    )
    print(f"  ReopeningAStar suboptimal     {sweep['reopening_astar_suboptimal']}")
    print(f"  NetworkX astar suboptimal     {sweep['networkx_astar_suboptimal']}")
    print(
        f"  expansion overhead of the fix {sweep['reopening_expansion_overhead']:+.2%}"
    )

    print("\n-- and on this project's own data --")
    catalog = experiment.catalog()
    planner = catalog.planner()
    heuristic = haversine_heuristic()

    print(f"  airports {len(planner.vertices):,}  routes {len(planner.edges):,}")
    consistency = heuristic_consistency(planner, parameters["consistency_epsilon_km"])
    print(
        f"  consistency: {consistency['checks']:,} checks, "
        f"{consistency['violations']} violations "
        f"(worst {consistency['worst_violation_km']:.6f} km)"
    )

    agreement = astar_matches_dijkstra(planner, heuristic, parameters["tolerance"])
    print(
        f"  A* vs Dijkstra: {agreement['pairs_checked']:,} pairs, "
        f"{len(agreement['mismatches'])} mismatches"
    )
    print(
        f"  expansions: "
        + "  ".join(
            f"{name} {count:,}"
            for name, count in agreement["nodes_expanded"].items()
        )
    )
    print(
        "  taking the patch would change the recorded expansion counts: "
        f"{agreement['patch_changes_expansions']}"
    )

    experiment.record(
        {
            "oracle": f"networkx {nx.__version__}",
            "minimal_case": minimal,
            "randomized": sweep,
            "snapshot_heuristic_consistency": consistency,
            "snapshot_agreement": agreement,
            "environment": environment(),
        },
        catalog=catalog,
    )
    print(f"\n  recorded {experiment.results_path.name}")

    if consistency["violations"] or agreement["mismatches"]:
        print("PROBLEM: the defect reaches this project's own data -- see results.json")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
