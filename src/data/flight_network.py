"""Builds the processed airport and route network from the raw sources.

Replaces the SQL transform that previously derived `data/processed/*.csv`.
The move to pandas buys three things the `.sql` file could not offer: the
distance calculation reuses `flight_planner.geo.Haversine` instead of a second
hand-written formula, every stage is reachable from the test suite, and routes
dropped for unresolvable endpoints are reported rather than silently lost to an
INNER JOIN.

The raw sources are read, routes whose endpoints cannot both be resolved are
set aside, distances are computed, and the result is written as CSV and as
SQLite tables built from the very same frames -- so the two representations
cannot drift apart.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import sqlite3

import pandas as pd
from pandas import DataFrame

from flight_planner.geo import Haversine, Point

PathLike = Union[str, Path]

# OpenFlights `routes.dat` is headerless; these are its columns in order.
ROUTE_COLUMNS = [
    "airline_code",
    "airline_id",
    "source_airport_code",
    "source_airport_id",
    "destination_airport_code",
    "destination_airport_id",
    "codeshare",
    "stops",
    "equipment",
]

# Columns read verbatim rather than through pandas' missing-value handling.
# "NA" is a real value in two of them -- North America in `continent`, Namibia
# in `iso_country` -- and is also one of pandas' default NA sentinels.
AIRPORT_TEXT_COLUMNS = {
    "iso_country": str,
    "continent": str,
    "iata_code": str,
    "icao_code": str,
    "iso_region": str,
    "municipality": str,
    "type": str,
    "scheduled_service": str,
    "name": str,
}

ROUTE_TEXT_COLUMNS = {
    "airline_code": str,
    "source_airport_code": str,
    "destination_airport_code": str,
    "codeshare": str,
    "equipment": str,
}

# Column order of the emitted files, shared by the CSVs and the SQLite tables.
AIRPORT_OUTPUT_COLUMNS = [
    "name",
    "iso_country",
    "iso_region",
    "continent",
    "municipality",
    "iata_code",
    "icao_code",
    "latitude_deg",
    "longitude_deg",
    "elevation_ft",
    "scheduled_service",
    "type",
    "is_international",
    "wikipedia_link",
]

ROUTE_OUTPUT_COLUMNS = [
    "flight_number",
    "airline_code",
    "source_airport_code",
    "destination_airport_code",
    "codeshare",
    "stops",
    "equipment",
    "distance_km",
]


# Drop categories, used as the prefix of every `skipped` reason so the
# breakdown can be grouped without parsing airport codes out of a sentence.
ORIGIN_DOES_NOT_RESOLVE = "origin does not resolve"
DESTINATION_DOES_NOT_RESOLVE = "destination does not resolve"
NEITHER_ENDPOINT_RESOLVES = "neither endpoint resolves"

DROP_CATEGORIES = (
    ORIGIN_DOES_NOT_RESOLVE,
    DESTINATION_DOES_NOT_RESOLVE,
    NEITHER_ENDPOINT_RESOLVES,
)


@dataclass
class NetworkBuild:
    """The outcome of one build.

    Attributes:
        airports: Airports referenced by at least one surviving route.
        routes: Surviving routes, with `distance_km` computed.
        skipped: `(row, reason)` pairs for routes that could not be built,
            mirroring `CsvRecordLoader.skipped`.
    """

    airports: DataFrame
    routes: DataFrame
    skipped: List[Tuple[int, str]] = field(default_factory=list)


class FlightNetworkBuilder:
    """Derives the processed network from raw OpenFlights and OurAirports data."""

    def read_airports(self, path: PathLike) -> DataFrame:
        """Read the OurAirports airports file.

        Args:
            path: Path to the OurAirports `airports.csv`.

        Returns:
            `DataFrame` of every airport row in the file.
        """
        return pd.read_csv(path, converters=AIRPORT_TEXT_COLUMNS)

    def read_routes(self, path: PathLike) -> DataFrame:
        """Read the OpenFlights routes file, naming its columns.

        Args:
            path: Path to the OpenFlights `routes.dat`.

        Returns:
            `DataFrame` of every route row in the file.
        """
        return pd.read_csv(
            path,
            names=ROUTE_COLUMNS,
            converters=ROUTE_TEXT_COLUMNS,
            na_values="\\N",  # OpenFlights uses \N for missing values
        )

    def assign_flight_numbers(self, routes: DataFrame) -> DataFrame:
        """Attach a stable `flight_number` to every route.

        OpenFlights carries no flight numbers, so they are synthesized:
        routes are ordered by `(source, destination)` within each airline and
        numbered from one, formatted `{airline}{0000}`. `(airline, source,
        destination)` is unique across the dataset, so the mapping is 1:1.

        Call this on the **complete** route set. Numbering before resolution
        and before any filtering is what makes an identifier permanent -- a
        route dropped later still consumes its number, leaving a gap, so
        adding an IATA override or narrowing to one airline never renumbers
        anything that survived.

        Args:
            routes: Route rows, as read from OpenFlights.

        Returns:
            A copy with a `flight_number` column. An existing column is left
            alone, so a caller may supply its own numbering.
        """
        if "flight_number" in routes.columns:
            return routes

        numbered = routes.copy()
        ordered = numbered.sort_values(
            ["airline_code", "source_airport_code", "destination_airport_code"]
        )
        sequence = ordered.groupby("airline_code").cumcount() + 1
        numbered.loc[ordered.index, "flight_number"] = [
            f"{airline}{number:04d}"
            for airline, number in zip(ordered["airline_code"], sequence)
        ]
        return numbered

    @staticmethod
    def read_international_codes(path: Optional[PathLike]) -> set:
        """Read the IATA codes listed as international airports.

        The list is scraped from Wikipedia and is editorially maintained, so
        absence means "not listed" rather than "has no international
        service". It is a weaker source than OurAirports, which supplies
        every other airport field.

        Args:
            path: Path to the international-airports CSV, or `None`.

        Returns:
            Set of upper-cased IATA codes, empty when no path is given.
        """
        if path is None:
            return set()
        frame = pd.read_csv(path, converters={"iata": str})
        return {code.strip().upper() for code in frame["iata"] if code.strip()}

    def build(
        self,
        airports: DataFrame,
        routes: DataFrame,
        airline: Optional[str] = None,
        airport_type: Optional[str] = None,
        country: Optional[str] = None,
        international: Optional[PathLike] = None,
    ) -> NetworkBuild:
        """Resolve routes against airports and compute their distances.

        A route survives only when **both** endpoints resolve to an airport
        that passes every supplied filter. Filtering endpoints rather than
        routes is what keeps the result self-consistent: no surviving route
        can point at an airport absent from the airport set.

        Args:
            airports: Airport rows, as read from OurAirports.
            routes: Route rows, as read from OpenFlights.
            airline: Keep only this airline's routes, or all when `None`.
            airport_type: Keep only airports of this type, or all when `None`.
            country: Keep only airports in this ISO country, or all when
                `None`.
            international: Path to the international-airports CSV used to set
                the `is_international` column. Every airport reads `no` when
                omitted.

        Returns:
            A `NetworkBuild` holding the referenced airports, the surviving
            routes, and the reasons any route was dropped.
        """
        routes = self.assign_flight_numbers(routes)

        usable = self._usable_airports(airports, airport_type, country)
        locations = {
            row.iata_code: Point(
                latitude=float(row.latitude_deg), longitude=float(row.longitude_deg)
            )
            for row in usable.itertuples(index=False)
        }

        if airline is not None:
            routes = routes[routes["airline_code"] == airline]

        kept_rows: List[int] = []
        skipped: List[Tuple[int, str]] = []
        for position, row in enumerate(routes.itertuples(index=True), start=1):
            origin_missing = row.source_airport_code not in locations
            destination_missing = row.destination_airport_code not in locations
            if origin_missing or destination_missing:
                # The category is named first so a reader -- and
                # `drop_breakdown` -- can group on it without parsing codes
                # out of prose. Which endpoint failed is the informative part:
                # a near-even origin/destination split points at airports
                # missing from OurAirports, while a lopsided one would point
                # at a directional bug in the resolution itself.
                if origin_missing and destination_missing:
                    category = NEITHER_ENDPOINT_RESOLVES
                    codes = [row.source_airport_code, row.destination_airport_code]
                elif origin_missing:
                    category = ORIGIN_DOES_NOT_RESOLVE
                    codes = [row.source_airport_code]
                else:
                    category = DESTINATION_DOES_NOT_RESOLVE
                    codes = [row.destination_airport_code]
                skipped.append((position, f"{category}: {', '.join(codes)}"))
                continue
            kept_rows.append(row.Index)

        surviving = routes.loc[kept_rows].copy()
        surviving["distance_km"] = [
            self._distance(locations, source, destination)
            for source, destination in zip(
                surviving["source_airport_code"],
                surviving["destination_airport_code"],
            )
        ]

        referenced = set(surviving["source_airport_code"]) | set(
            surviving["destination_airport_code"]
        )
        airports_out = usable[usable["iata_code"].isin(referenced)].copy()
        listed = self.read_international_codes(international)
        airports_out["is_international"] = [
            "yes" if code in listed else "no" for code in airports_out["iata_code"]
        ]

        return NetworkBuild(
            airports=airports_out.sort_values("name").reset_index(drop=True),
            routes=surviving.sort_values(
                ["source_airport_code", "destination_airport_code"]
            ).reset_index(drop=True),
            skipped=skipped,
        )

    def write_csv(
        self, build: NetworkBuild, airports_path: PathLike, routes_path: PathLike
    ) -> None:
        """Write the build to the two processed CSV files.

        Args:
            build: The build to serialize.
            airports_path: Destination for the airports CSV.
            routes_path: Destination for the routes CSV.
        """
        self._airport_output(build).to_csv(airports_path, index=False)
        self._route_output(build).to_csv(routes_path, index=False)

    @staticmethod
    def drop_breakdown(build: NetworkBuild) -> Dict[str, int]:
        """Count dropped routes by category.

        Args:
            build: The build whose `skipped` pairs to tally.

        Returns:
            Every category in `DROP_CATEGORIES` mapped to its count, zeros
            included. Zeros are kept deliberately: a category that vanishes
            from a report reads as "not measured" rather than "did not
            happen".
        """
        counts = {category: 0 for category in DROP_CATEGORIES}
        for _, reason in build.skipped:
            category = reason.split(":", 1)[0]
            counts[category] = counts.get(category, 0) + 1
        return counts

    def build_report(self, build: NetworkBuild, raw: Mapping[str, int]) -> Dict[str, Any]:
        """Summarise what the build kept and what it discarded.

        The pipeline used to print only `len(skipped)` and persist nothing, so
        the cleaning figures in the report were the one set of numbers with no
        committed artifact behind them. This is that artifact.

        Args:
            build: The completed build.
            raw: Input row counts, keyed by source name.

        Returns:
            A JSON-serialisable mapping of input counts, output counts, the
            per-category drop breakdown, and every dropped row with its
            reason.
        """
        breakdown = self.drop_breakdown(build)
        return {
            "raw": dict(raw),
            "kept": {
                "airports": int(len(build.airports)),
                "routes": int(len(build.routes)),
            },
            "dropped": {
                "routes": len(build.skipped),
                "by_reason": breakdown,
                "total_checks_out": sum(breakdown.values()) == len(build.skipped),
            },
            # Every row, not a sample. At 1,331 rows this costs about 90 KB
            # and turns "1,331 were dropped" into something a reader can
            # audit -- which is the difference between a reported figure and
            # an asserted one.
            "skipped": [
                {"row": position, "reason": reason} for position, reason in build.skipped
            ],
        }

    def write_build_report(
        self, build: NetworkBuild, path: PathLike, raw: Mapping[str, int]
    ) -> None:
        """Write the build report beside the processed CSVs.

        Args:
            build: The completed build.
            path: Destination for the JSON report.
            raw: Input row counts, keyed by source name.
        """
        Path(path).write_text(
            json.dumps(self.build_report(build, raw), indent=2) + "\n",
            encoding="utf-8",
        )

    def write_sqlite(self, build: NetworkBuild, database: PathLike) -> None:
        """Write the build to the `airports` and `routes` tables.

        The tables come from the same frames the CSVs do, so the database and
        the CSVs cannot disagree.

        Args:
            build: The build to serialize.
            database: SQLite file to write, created if absent.
        """
        with sqlite3.connect(database) as connection:
            self._airport_output(build).to_sql(
                "airports", connection, if_exists="replace", index=False
            )
            self._route_output(build).to_sql(
                "routes", connection, if_exists="replace", index=False
            )

    def write_snapshot(
        self,
        build: NetworkBuild,
        root: PathLike,
        criteria: Mapping[str, Any],
        narrowing: Sequence[Mapping[str, Any]] = (),
        generator: str = "src/data/flight_network.py",
    ) -> Path:
        """Freeze a build into an immutable, checksummed snapshot directory.

        The directory is named `<date>-<short content hash>`, so identical
        data always lands on the same name and re-freezing it is a no-op
        rather than a duplicate.

        Args:
            build: The build to freeze.
            root: Directory to create the snapshot inside.
            criteria: The narrowing that produced this slice, recorded in the
                manifest so a reader can tell what the snapshot represents.
            narrowing: The `Catalog` narrowing chain that produced the slice,
                step by step. `criteria` says what the slice is; this says how
                it was arrived at, including each step's effect.
            generator: The tool that produced the snapshot, recorded so a
                reader can tell which path the data came down.

        Returns:
            Path to the created snapshot directory.
        """
        airports_csv = self._airport_output(build).to_csv(index=False).encode()
        routes_csv = self._route_output(build).to_csv(index=False).encode()

        digest = hashlib.sha256(airports_csv + routes_csv).hexdigest()[:6]
        directory = Path(root) / f"{datetime.now(timezone.utc):%Y-%m-%d}-{digest}"
        directory.mkdir(parents=True, exist_ok=True)

        contents = {"airports.csv": airports_csv, "routes.csv": routes_csv}
        rows = {"airports.csv": len(build.airports), "routes.csv": len(build.routes)}
        for filename, payload in contents.items():
            (directory / filename).write_bytes(payload)

        manifest: Dict[str, Any] = {
            "snapshot_id": directory.name,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_commit": self._source_commit(),
            "generator": generator,
            "criteria": dict(criteria),
            "files": {
                filename: {
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "rows": rows[filename],
                }
                for filename, payload in contents.items()
            },
        }
        if narrowing:
            manifest["narrowing"] = [dict(step) for step in narrowing]
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return directory

    @staticmethod
    def _source_commit() -> Optional[str]:
        """Return the current git commit, when one can be determined.

        Returns:
            The commit SHA, or `None` outside a git checkout.
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        return result.stdout.strip()

    def _airport_output(self, build: NetworkBuild) -> DataFrame:
        """Return the airports frame in emitted column order.

        Args:
            build: The build to serialize.

        Returns:
            `DataFrame` restricted and ordered to `AIRPORT_OUTPUT_COLUMNS`.
        """
        return build.airports[AIRPORT_OUTPUT_COLUMNS]

    def _route_output(self, build: NetworkBuild) -> DataFrame:
        """Return the routes frame in emitted column order.

        Args:
            build: The build to serialize.

        Returns:
            `DataFrame` restricted and ordered to `ROUTE_OUTPUT_COLUMNS`.
        """
        return build.routes[ROUTE_OUTPUT_COLUMNS]

    @staticmethod
    def _usable_airports(
        airports: DataFrame, airport_type: Optional[str], country: Optional[str]
    ) -> DataFrame:
        """Return airports with a usable identity, location, and matching filters.

        Args:
            airports: Airport rows, as read from OurAirports.
            airport_type: Required `type` value, or `None` for any.
            country: Required `iso_country` value, or `None` for any.

        Returns:
            `DataFrame` of airports eligible to anchor a route.
        """
        usable = airports[
            (airports["iata_code"].str.len() == 3)
            & airports["latitude_deg"].notna()
            & airports["longitude_deg"].notna()
        ]
        if airport_type is not None:
            usable = usable[usable["type"] == airport_type]
        if country is not None:
            usable = usable[usable["iso_country"] == country]
        return usable.drop_duplicates(subset="iata_code")

    @staticmethod
    def _distance(locations: dict, source: str, destination: str) -> float:
        """Return the great-circle distance between two airports.

        Uses `flight_planner.geo.Haversine` so the pipeline and the graph
        algorithms measure distance the same way. Coordinates come from a
        dict rather than a frame lookup -- at 66,000 routes, `DataFrame.loc`
        per row dominates the runtime.

        Args:
            locations: Mapping of IATA code to `Point`.
            source: Origin IATA code.
            destination: Destination IATA code.

        Returns:
            Distance in kilometers.
        """
        return Haversine().calculate(locations[source], locations[destination])


def parse_args() -> argparse.Namespace:
    """Parse the input and output paths from the command line.

    Returns:
        A namespace with the raw input paths, the two CSV destinations, and
        the optional filters.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("our_airports", help="Path to the OurAirports airports.csv file.")
    parser.add_argument("open_flights_routes", help="Path to the OpenFlights routes.dat file.")
    parser.add_argument("airports_csv", help="Destination for the processed airports CSV.")
    parser.add_argument("routes_csv", help="Destination for the processed routes CSV.")
    parser.add_argument("--database", help="Optional SQLite file to write the tables into.")
    parser.add_argument("--snapshot-root", help="Freeze the build as a snapshot under this directory.")
    parser.add_argument("--airline", help="Keep only this airline's routes.")
    parser.add_argument("--airport-type", help="Keep only airports of this type.")
    parser.add_argument("--country", help="Keep only airports in this ISO country.")
    parser.add_argument(
        "--international",
        help="Path to international_airports.csv, used to set is_international.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    network_builder = FlightNetworkBuilder()

    # Bound rather than inlined, so the build report can state what came in
    # as well as what came out. "1,331 dropped" means nothing without 67,663.
    raw_airports = network_builder.read_airports(args.our_airports)
    raw_routes = network_builder.read_routes(args.open_flights_routes)

    built = network_builder.build(
        raw_airports,
        raw_routes,
        airline=args.airline,
        airport_type=args.airport_type,
        country=args.country,
        international=args.international,
    )
    network_builder.write_csv(built, args.airports_csv, args.routes_csv)
    report_path = Path(args.airports_csv).with_name("build-report.json")
    network_builder.write_build_report(
        built,
        report_path,
        raw={"airports": len(raw_airports), "routes": len(raw_routes)},
    )
    if args.database:
        network_builder.write_sqlite(built, args.database)
    if args.snapshot_root:
        criteria = {
            name: value
            for name, value in (
                ("airline", args.airline),
                ("airport_type", args.airport_type),
                ("country", args.country),
            )
            if value is not None
        }
        snapshot = network_builder.write_snapshot(built, args.snapshot_root, criteria)
        print(f"snapshot: {snapshot}")

    print(f"airports: {len(built.airports)}  routes: {len(built.routes)}")
    if built.skipped:
        # The count, then where the rows themselves went. Printing only the
        # count is what made these the one figures in the report with no
        # committed artifact behind them.
        print(f"routes dropped for unresolvable endpoints: {len(built.skipped)}")
        for category, count in network_builder.drop_breakdown(built).items():
            print(f"  {category}: {count}")
    print(f"build report: {report_path}")
