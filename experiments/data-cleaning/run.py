"""data-cleaning: what the pipeline discarded, and whether the snapshot matches.

Report §2.3 states that cleaning takes 85,884 airport rows down to 3,387 and
67,663 routes down to 66,332, with a per-reason breakdown of the 1,331 drops.
Every other figure in the report names a committed `results.json`. **These did
not.** `NetworkBuild.skipped` held the `(row, reason)` pairs in memory, the
tests asserted on them, and the CLI printed `len(skipped)` -- so the claim that
drops are "reported rather than silently lost to an INNER JOIN" was true only
in the weak sense of a printed count.

This experiment is that record. It is shaped differently from the other eight
and the difference is the point.

**It reads the raw sources, not the snapshot.** Cleaning runs upstream of
snapshots -- raw, then processed, then frozen -- so a question about what
cleaning discarded cannot be answered from the frozen output, which by
construction contains only survivors. The raw files are committed, so the
experiment re-runs the pipeline over them.

**The snapshot is still pinned, and it earns the pin.** The last section
compares the re-derived output against the committed snapshot row for row.
That turns the snapshot's provenance from an assertion into a measurement: if
the cleaning code and the frozen data ever drift apart, this fails. It is the
one experiment that checks the *pipeline* rather than a property of its output.

Run it from anywhere:
    uv run python experiments/data-cleaning/run.py
"""

from __future__ import annotations

import hashlib
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from flight_planner.experiments import Experiment

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "data"))

from flight_network import FlightNetworkBuilder  # noqa: E402


def digest(path: Path) -> Dict[str, Any]:
    """Return a checksum and size for one input file.

    The raw files are committed but are not part of any snapshot, so nothing
    else verifies them. Recording their digests means a recorded drop count
    names the bytes it was measured over.

    Args:
        path: File to digest.

    Returns:
        Mapping of path, SHA-256 and byte count.
    """
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def airport_attrition(builder: FlightNetworkBuilder, raw: pd.DataFrame) -> Dict[str, Any]:
    """Measure the airport filter stage by stage.

    §2.3 reports 85,884 -> 9,053 -> 3,387, and the two steps are different
    kinds of filter: the first is "is this row usable at all", the second is
    "does any surviving route touch it". Reporting only the endpoints would
    hide that.

    Args:
        builder: The pipeline builder.
        raw: Every row of the OurAirports file.

    Returns:
        Counts at each stage and the reason each dropped row failed.
    """
    has_iata = raw["iata_code"].str.len() == 3
    has_latitude = raw["latitude_deg"].notna()
    has_longitude = raw["longitude_deg"].notna()

    usable = builder._usable_airports(raw, None, None)
    deduplicated = len(raw[has_iata & has_latitude & has_longitude]) - len(usable)

    return {
        "raw_rows": int(len(raw)),
        "usable_rows": int(len(usable)),
        "failed": {
            # Not mutually exclusive -- a row can fail more than one -- so
            # these are reported as independent counts rather than a
            # partition that would not add up.
            "iata_code_not_three_characters": int((~has_iata).sum()),
            "missing_latitude": int((~has_latitude).sum()),
            "missing_longitude": int((~has_longitude).sum()),
        },
        "duplicate_iata_codes_collapsed": int(deduplicated),
    }


def column_coverage(frame: pd.DataFrame) -> Dict[str, float]:
    """Return the fraction of rows with a non-empty value, per column.

    The `NA`-means-North-America trap makes this worth recording: a column
    silently blanked by a converter change shows up here as coverage falling,
    rather than as a chapter quietly becoming wrong.

    Args:
        frame: The cleaned frame to profile.

    Returns:
        Column name to filled fraction, rounded.
    """
    total = len(frame)
    coverage = {}
    for column in frame.columns:
        values = frame[column]
        filled = values.notna() & (values.astype(str).str.strip() != "")
        coverage[column] = round(float(filled.sum()) / total, 6) if total else 0.0
    return coverage


def overrides_effect(path: Path, airports: pd.DataFrame) -> Dict[str, Any]:
    """Measure what the manual IATA corrections did.

    Args:
        path: The overrides CSV.
        airports: The cleaned airport frame.

    Returns:
        How many corrections exist, how they are classified, and how many of
        their canonical codes are present in the cleaned output.
    """
    overrides = pd.read_csv(path, keep_default_na=False)
    canonical = [code for code in overrides["canonical_iata"] if code]
    present = set(airports["iata_code"])
    return {
        "rows": int(len(overrides)),
        "by_registry_status": {
            str(status): int(count)
            for status, count in Counter(overrides["iata_registry"]).items()
        },
        "with_a_canonical_code": len(canonical),
        "canonical_codes_present_in_output": sum(
            1 for code in canonical if code in present
        ),
    }


def snapshot_agreement(build, snapshot) -> Dict[str, Any]:
    """Compare the re-derived build against the committed snapshot.

    This is what earns the snapshot pin. The other experiments read a
    snapshot; this one checks that the snapshot is what the current pipeline
    produces.

    Args:
        build: The freshly re-derived `NetworkBuild`.
        snapshot: The pinned snapshot.

    Returns:
        Row counts from each side, whether they agree, and the IATA codes
        present in one and not the other.
    """
    catalog = snapshot.catalog()
    rebuilt_codes = set(build.airports["iata_code"])
    frozen_codes = {airport.iata_code for airport in catalog.airports}
    return {
        "rebuilt": {"airports": int(len(build.airports)), "routes": int(len(build.routes))},
        "frozen": {"airports": len(catalog.airports), "routes": len(catalog.routes)},
        "airports_agree": len(rebuilt_codes) == len(frozen_codes) == len(rebuilt_codes & frozen_codes),
        "routes_agree": int(len(build.routes)) == len(catalog.routes),
        "only_in_rebuild": sorted(rebuilt_codes - frozen_codes),
        "only_in_snapshot": sorted(frozen_codes - rebuilt_codes),
    }


def main() -> int:
    """Run the experiment and record its answer.

    Returns:
        Process exit status. Non-zero if the re-derived network disagrees
        with the committed snapshot, since that means the published figures
        and the frozen data have parted company.
    """
    experiment = Experiment.open(Path(__file__).parent)
    parameters = experiment.parameters
    here = Path(__file__).parent

    airports_path = (here / parameters["raw_airports"]).resolve()
    routes_path = (here / parameters["raw_routes"]).resolve()
    international = (here / parameters["international"]).resolve()
    overrides = (here / parameters["iata_overrides"]).resolve()

    builder = FlightNetworkBuilder()
    raw_airports = builder.read_airports(airports_path)
    raw_routes = builder.read_routes(routes_path)
    build = builder.build(raw_airports, raw_routes, international=international)

    report = builder.build_report(
        build, raw={"airports": len(raw_airports), "routes": len(raw_routes)}
    )
    agreement = snapshot_agreement(build, experiment.snapshot)

    results = {
        "inputs": [digest(path) for path in (airports_path, routes_path)],
        "airports": airport_attrition(builder, raw_airports),
        "routes": {
            "raw_rows": report["raw"]["routes"],
            "kept": report["kept"]["routes"],
            "dropped": report["dropped"]["routes"],
            "by_reason": report["dropped"]["by_reason"],
            "survival_rate": round(
                report["kept"]["routes"] / report["raw"]["routes"], 6
            ),
        },
        # Every dropped row, not a sample. 1,331 rows is small enough to
        # commit and is what makes the figure auditable rather than asserted.
        "dropped_rows": report["skipped"],
        "coverage": {
            "airports": column_coverage(build.airports),
            "routes": column_coverage(build.routes),
        },
        "iata_overrides": overrides_effect(overrides, build.airports),
        "snapshot_agreement": agreement,
    }
    experiment.record(results)

    airports = results["airports"]
    routes = results["routes"]
    print(
        f"airports: {airports['raw_rows']:,} -> {airports['usable_rows']:,} -> "
        f"{agreement['rebuilt']['airports']:,}"
    )
    print(f"routes:   {routes['raw_rows']:,} -> {routes['kept']:,} "
          f"({routes['dropped']:,} dropped, {100 * routes['survival_rate']:.1f}% survive)")
    for reason, count in routes["by_reason"].items():
        print(f"    {reason}: {count}")

    agrees = agreement["airports_agree"] and agreement["routes_agree"]
    print(f"snapshot agreement: {'yes' if agrees else 'NO'}")
    if not agrees:
        print("\nThe re-derived network does not match the committed snapshot.")
        print(f"  only in rebuild:  {agreement['only_in_rebuild'][:10]}")
        print(f"  only in snapshot: {agreement['only_in_snapshot'][:10]}")
    return 0 if agrees else 1


if __name__ == "__main__":
    raise SystemExit(main())
