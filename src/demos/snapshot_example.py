"""Example: reading a snapshot, and what its manifest guarantees.

A snapshot is frozen data: the CSV files an experiment ran against, plus a
manifest recording a SHA-256 for each of them. `Snapshot.open` re-hashes every
file, so an experiment can prove it read the same bytes as the run before it.

This demo opens the repository's full-network snapshot, reports what the
manifest says about it, routes across it, and then shows the guarantee doing
its job: a tampered copy in a temporary directory refuses to open.

Run from anywhere:
    uv run python src/demos/snapshot_example.py
"""

import shutil
import tempfile
from pathlib import Path

from flight_planner.experiments import Snapshot, SnapshotIntegrityError

# The package takes directories from its caller, so the demo locates the
# repository's snapshots relative to this file rather than the process's cwd.
SNAPSHOTS_DIR = Path(__file__).resolve().parents[2] / "data" / "snapshots"
SNAPSHOT_ID = "2026-09-11-bb90a8"

DEPARTURE = "SFO"
ARRIVAL = "BOS"


def tamper_with(snapshot: Snapshot, directory: Path) -> Path:
    """Copy a snapshot and change one byte of its routes file.

    Args:
        snapshot: Snapshot to copy.
        directory: Directory to copy it into.

    Returns:
        Path to the modified copy.
    """
    copy = directory / "tampered"
    shutil.copytree(snapshot.directory, copy)
    with (copy / "routes.csv").open("a") as handle:
        handle.write("\n")
    return copy


if __name__ == "__main__":
    print("--- Snapshots in this repository ---")
    for candidate in sorted(SNAPSHOTS_DIR.iterdir()):
        if (candidate / "manifest.json").is_file():
            # verify=False: this is a listing, not a run. Hashing every file
            # of every snapshot to print its id would be wasted work.
            listed = Snapshot.open(candidate, verify=False)
            criteria = listed.criteria or "none (the whole network)"
            print(f"  • {listed.snapshot_id}: {criteria}")

    # Opening without verify=False re-hashes every file the manifest lists.
    snapshot = Snapshot.open(SNAPSHOTS_DIR / SNAPSHOT_ID)

    print(f"\n--- {snapshot.snapshot_id} ---")
    print(f"Frozen:        {snapshot.created}")
    print(f"From commit:   {snapshot.source_commit}")
    print(f"Criteria:      {snapshot.criteria or 'none (the whole network)'}")
    print(f"Files:         {', '.join(snapshot.filenames)}")
    for filename in snapshot.filenames:
        print(f"  • {filename}: {snapshot.path(filename)}")

    # Only files the manifest vouches for can be reached, so nothing
    # unverified is ever handed out.
    try:
        snapshot.path("airlines.csv")
    except KeyError as error:
        print(f"\nAsking for a file the manifest does not list: {error}")

    planner = snapshot.load_planner()
    print("\n--- Routing across the snapshot ---")
    print(f"Airports: {len(planner.vertices)}   Routes: {len(planner.edges)}")
    total_km, legs = planner.find_shortest_route(DEPARTURE, ARRIVAL)
    print(f"{DEPARTURE} -> {ARRIVAL}: {total_km:.1f} km over {len(legs)} leg(s)")
    for leg in legs:
        print(
            f"  • {leg.flight_number} ({leg.airline}): "
            f"{leg.origin.iata_code} -> {leg.destination.iata_code} "
            f"({leg.distance_km:.1f} km)"
        )

    print("\n--- What the manifest is for ---")
    with tempfile.TemporaryDirectory() as workspace:
        tampered = tamper_with(snapshot, Path(workspace))
        print(f"Appended one byte to a copy of routes.csv in {tampered.name}/")
        try:
            Snapshot.open(tampered)
        except SnapshotIntegrityError as error:
            print(f"Reopening it raised SnapshotIntegrityError:\n  {error}")
        else:
            print("Reopening it succeeded — which it should not have.")
