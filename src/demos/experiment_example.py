"""Example: an experiment — pinned data, declared inputs, recorded results.

An experiment is a directory: `experiment.toml` names the snapshot it runs
against and the parameters it runs with, and `results.json` records what came
out next to the identity of the data that went in.

This demo does both halves. First it reads the experiment committed at
`experiments/sfo-bos-dijkstra` without running it, to show what the config and
the recorded result hold. Then it scaffolds a fresh experiment in a temporary
directory, runs it, and records the result — a throwaway so the demo never
overwrites a committed run.

Run from anywhere:
    uv run python src/demos/experiment_example.py
"""

import json
import tempfile
from pathlib import Path

from flight_planner.experiments import Experiment
from flight_planner.pathfinding import BFS

REPOSITORY = Path(__file__).resolve().parents[2]
COMMITTED_EXPERIMENT = REPOSITORY / "experiments" / "sfo-bos-dijkstra"
SNAPSHOT = REPOSITORY / "data" / "snapshots" / "2026-09-11-bb90a8"

# The experiment this demo builds and runs: do the fewest-hops and the
# shortest-distance itineraries agree, once the network is narrowed to one
# carrier's large US airports?
CONFIG = """\
slug = "hops-vs-distance"
description = "Does the fewest-hops itinerary cost more kilometres than the shortest one?"
notebooks = []
snapshot = "{snapshot}"

[parameters]
airline = "UA"
airport_type = "large"
country = "US"
pairs = [["SFO", "BOS"], ["BOI", "CHS"], ["HNL", "BDL"]]
"""


def read_committed() -> None:
    """Report what the committed experiment declares and last recorded."""
    experiment = Experiment.open(COMMITTED_EXPERIMENT)
    print(f"--- {experiment.slug} ---")
    print(f"Question:   {experiment.description}")
    print(f"Notebooks:  {', '.join(experiment.notebooks) or 'none'}")
    print(f"Parameters: {experiment.parameters}")

    # The snapshot is named relative to experiment.toml and resolved against
    # that file's own location — never against the working directory — so the
    # experiment finds its data from any cwd, and from any clone.
    print(f"Snapshot:   {experiment.snapshot_reference}")
    print(f"  resolves to {experiment.snapshot_path}")

    # Opening the snapshot is deferred until the data is wanted, because
    # verification re-hashes every file.
    print(f"  id {experiment.snapshot.snapshot_id}, frozen {experiment.snapshot.created}")

    recorded = experiment.results()
    if recorded is None:
        print("No run recorded yet.")
        return
    results = recorded["results"]
    print(f"\nLast recorded {recorded['recorded']}, against {recorded['snapshot']['id']}:")
    print(
        f"  {results['pair']}: {results['whole_network_km']:.1f} km over the whole "
        f"network, {results['narrowed_km']:.1f} km once narrowed"
    )
    print(f"  narrowing chain: {recorded['catalog']['routes']} routes")


def run_throwaway(directory: Path) -> None:
    """Scaffold, run and record an experiment in a temporary directory.

    Args:
        directory: Directory to write `experiment.toml` and `results.json` to.
    """
    # An absolute snapshot path is accepted; a committed experiment uses a
    # relative one so that it travels with the repository.
    (directory / "experiment.toml").write_text(CONFIG.format(snapshot=SNAPSHOT))

    experiment = Experiment.open(directory)
    parameters = experiment.parameters
    print(f"\n--- {experiment.slug} (temporary) ---")
    print(f"Question: {experiment.description}")

    # Narrow the snapshot exactly as the parameters declare, so the recorded
    # derivation and the declared inputs cannot drift apart.
    catalog = (
        experiment.catalog()
        .airline(parameters["airline"])
        .airport_type(parameters["airport_type"])
        .country(parameters["country"])
    )
    planner = catalog.planner()
    print(f"Scope:    {len(catalog.routes)} routes / {len(catalog.airports)} airports")

    comparison = []
    for origin, destination in parameters["pairs"]:
        shortest_km, shortest_legs = planner.find_shortest_route(origin, destination)
        hops, hop_legs = planner.find_shortest_route(origin, destination, algorithm=BFS())
        hop_km = sum(leg.distance_km for leg in hop_legs)
        comparison.append(
            {
                "pair": f"{origin}-{destination}",
                "shortest_km": shortest_km,
                "shortest_legs": len(shortest_legs),
                "fewest_hops": int(hops),
                "fewest_hops_km": hop_km,
                "detour_km": round(hop_km - shortest_km, 1),
            }
        )

    # record() opens the snapshot — which verifies every checksum — before it
    # writes, so no result can claim to come from data it did not read.
    results_path = experiment.record({"comparison": comparison}, catalog=catalog)

    print(f"{'pair':<10}{'shortest':>12}{'legs':>6}{'hops':>6}{'hops km':>12}{'detour':>10}")
    for row in comparison:
        print(
            f"{row['pair']:<10}{row['shortest_km']:>12.1f}{row['shortest_legs']:>6}"
            f"{row['fewest_hops']:>6}{row['fewest_hops_km']:>12.1f}{row['detour_km']:>10.1f}"
        )

    recorded = json.loads(results_path.read_text())
    print(f"\nWrote {results_path.name}. What a result carries with it:")
    print(f"  snapshot:   {recorded['snapshot']}")
    print(f"  parameters: {recorded['parameters']}")
    print(f"  catalog:    routes {recorded['catalog']['routes']}, "
          f"airports {recorded['catalog']['airports']}")


if __name__ == "__main__":
    read_committed()
    with tempfile.TemporaryDirectory() as workspace:
        run_throwaway(Path(workspace))
