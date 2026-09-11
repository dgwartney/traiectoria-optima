"""Freeze a slice of the processed network as an immutable snapshot.

The processed CSV files are rebuilt whenever the pipeline runs, so an
experiment cannot pin them. This script takes what is in `data/processed/`
right now, narrows it with the same `Catalog` vocabulary an experiment uses,
and writes the result to `data/snapshots/<date>-<hash>/` with a manifest of
checksums.

Narrowing goes through `Catalog` rather than a second filter language, so a
snapshot's criteria mean exactly what they mean in a notebook, and the
manifest records the chain step by step -- each narrowing's arguments and what
it cost in routes and airports.

Rows are carried across verbatim. Every column is read as text and written
back unchanged, so a snapshot's bytes are the processed file's bytes for the
rows that survived: no re-formatted floats, no drift.

This half of the experiment machinery knows the repository's layout, which is
why it lives in `scripts/` and is not shipped in the wheel.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "data"))

import pandas as pd  # noqa: E402
from pandas import DataFrame  # noqa: E402

from flight_network import (  # noqa: E402
    AIRPORT_OUTPUT_COLUMNS,
    ROUTE_OUTPUT_COLUMNS,
    FlightNetworkBuilder,
    NetworkBuild,
)
from flight_planner.experiments import Catalog  # noqa: E402
from flight_planner.loaders.csv_loader import AirportLoader, RouteLoader  # noqa: E402

DEFAULT_AIRPORTS_CSV = REPO_ROOT / "data" / "processed" / "airports.csv"
DEFAULT_ROUTES_CSV = REPO_ROOT / "data" / "processed" / "routes.csv"
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "data" / "snapshots"


def read_text_frame(path: Path, columns: Sequence[str]) -> DataFrame:
    """Read a processed CSV file without interpreting any of its values.

    Everything is read as a string and nothing is treated as missing, which is
    what makes writing the frame back out byte-identical to reading it. It
    also sidesteps pandas reading the literal `NA` as null, which would blank
    the continent of every North American airport.

    Args:
        path: CSV file to read.
        columns: Columns expected in the file.

    Returns:
        `DataFrame` of strings, in the file's own column order.
    """
    return pd.read_csv(
        path, converters={column: str for column in columns}, keep_default_na=False
    )


def narrow(catalog: Catalog, args: argparse.Namespace) -> Catalog:
    """Apply the requested narrowings to a catalog.

    Steps run in a fixed order -- airline, type, country, international --
    which under the default `both` endpoint mode makes no difference to the
    result, because closed narrowing commutes. It does matter under
    `--endpoints airports`, and the chain the manifest records shows the order
    that ran.

    Args:
        catalog: The full catalog to narrow.
        args: Parsed command-line arguments.

    Returns:
        The narrowed `Catalog`.
    """
    if args.airline:
        catalog = catalog.airline(*args.airline)
    if args.airport_type:
        catalog = catalog.airport_type(*args.airport_type, endpoints=args.endpoints)
    if args.country:
        catalog = catalog.country(*args.country, endpoints=args.endpoints)
    if args.international is not None:
        catalog = catalog.international(args.international, endpoints=args.endpoints)
    return catalog


def criteria_for(catalog: Catalog) -> Dict[str, Any]:
    """Return the flat description of a slice, for the manifest.

    Read back off the narrowing chain rather than off the command line, so the
    recorded values are the normalized ones the catalog actually applied:
    `--airport-type large` and `--airport-type large_airport` describe the
    same slice and must record the same criteria.

    A single value is recorded as itself rather than a one-element list, which
    keeps the format of the snapshots frozen before this script existed.

    Args:
        catalog: The narrowed catalog.

    Returns:
        Mapping of criterion to value, empty for a full snapshot.
    """
    criteria: Dict[str, Any] = {}
    for step in catalog.summary()["chain"]:
        arguments: List[Any] = list(step["arguments"])
        criteria[step["operation"]] = (
            arguments[0] if len(arguments) == 1 else arguments
        )
        if step["endpoints"] not in (None, "both"):
            criteria["endpoints"] = step["endpoints"]
    return criteria


def slice_frames(
    catalog: Catalog, airports: DataFrame, routes: DataFrame
) -> NetworkBuild:
    """Cut the processed frames down to what the catalog kept.

    Routes are matched on `(airline, source, destination)`, which is unique
    across the whole dataset, rather than on flight number -- so a snapshot
    can still be taken of data numbered differently or not at all.

    Args:
        catalog: The narrowed catalog defining the scope.
        airports: The full processed airports frame.
        routes: The full processed routes frame.

    Returns:
        A `NetworkBuild` holding only the surviving rows, in file order.
    """
    codes = set(catalog.iata_codes)
    keys = {
        (
            route.airline.upper(),
            route.origin.iata_code,
            route.destination.iata_code,
        )
        for route in catalog.routes
    }

    route_mask = [
        (airline.upper(), source.upper(), destination.upper()) in keys
        for airline, source, destination in zip(
            routes["airline_code"],
            routes["source_airport_code"],
            routes["destination_airport_code"],
        )
    ]
    return NetworkBuild(
        airports=airports[airports["iata_code"].isin(codes)],
        routes=routes[route_mask],
    )


def report(catalog: Catalog) -> None:
    """Print what each narrowing did.

    Args:
        catalog: The narrowed catalog whose chain should be reported.
    """
    summary = catalog.summary()
    for step, routes, airports in zip(
        summary["chain"], summary["routes"][1:], summary["airports"][1:]
    ):
        arguments = ", ".join(str(argument) for argument in step["arguments"])
        print(
            f"  {step['operation']}({arguments}) -> "
            f"{routes} routes / {airports} airports"
        )
    if summary["dangling"]:
        print(
            f"  warning: {summary['dangling']} route(s) reach airports outside "
            f"the slice and will be dropped from the snapshot"
        )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse the narrowings and paths from the command line.

    Args:
        argv: Argument list, or `None` to read `sys.argv`.

    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--airline", nargs="+", metavar="CODE", help="Airline codes to keep.")
    parser.add_argument(
        "--airport-type",
        nargs="+",
        metavar="TYPE",
        help="Airport types to keep; 'large', 'medium' and 'small' are accepted.",
    )
    parser.add_argument("--country", nargs="+", metavar="ISO", help="ISO country codes to keep.")
    parser.add_argument(
        "--international",
        dest="international",
        action="store_const",
        const=True,
        default=None,
        help="Keep only airports listed as international.",
    )
    parser.add_argument(
        "--domestic",
        dest="international",
        action="store_const",
        const=False,
        help="Keep only airports not listed as international.",
    )
    parser.add_argument(
        "--endpoints",
        choices=("both", "either", "airports"),
        default="both",
        help="How airport narrowings treat a route's two ends (default: both).",
    )
    parser.add_argument("--airports-csv", type=Path, default=DEFAULT_AIRPORTS_CSV)
    parser.add_argument("--routes-csv", type=Path, default=DEFAULT_ROUTES_CSV)
    parser.add_argument("--root", type=Path, default=DEFAULT_SNAPSHOT_ROOT)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Freeze a slice of the processed network.

    Args:
        argv: Argument list, or `None` to read `sys.argv`.

    Returns:
        Process exit status.
    """
    args = parse_args(argv)

    airport_index = AirportLoader(args.airports_csv).load_by_iata()
    routes = RouteLoader(airport_index, args.routes_csv).load()
    catalog = Catalog(airport_index.values(), routes)
    print(f"processed: {len(catalog.routes)} routes / {len(catalog.airports)} airports")

    narrowed = narrow(catalog, args)
    report(narrowed)

    build = slice_frames(
        narrowed,
        read_text_frame(args.airports_csv, AIRPORT_OUTPUT_COLUMNS),
        read_text_frame(args.routes_csv, ROUTE_OUTPUT_COLUMNS),
    )
    directory = FlightNetworkBuilder().write_snapshot(
        build,
        args.root,
        criteria_for(narrowed),
        narrowing=narrowed.summary()["chain"],
        generator="scripts/new_snapshot.py",
    )
    print(f"snapshot: {directory}")
    print(f"  {len(build.routes)} routes / {len(build.airports)} airports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
