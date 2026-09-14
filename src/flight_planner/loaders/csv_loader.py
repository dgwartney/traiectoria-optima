"""Load the processed airport and route CSV files into domain objects.

Bridges `data/processed/airports.csv` and `data/processed/routes.csv` to the
`Airport` / `Route` / `FlightPlanner` domain layer, so a planner can be built
from the real network instead of hand-written examples.

`AirportLoader` and `RouteLoader` share `CsvRecordLoader`, which owns reading,
column validation, and the row-by-row load loop; each subclass only supplies
the mapping from one CSV row to one domain object.

Callers always say which file to read. The package deliberately holds no
knowledge of where the repository keeps its data, so it behaves identically
whether imported from a source checkout or an installed wheel.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Tuple, Union

import pandas as pd

from ..flights.airport import Airport
from ..flights.route import Route
from ..flights.planner import FlightPlanner

PathLike = Union[str, Path]


class CsvRecordLoader(ABC):
    """Base loader turning rows of a processed CSV file into domain objects.

    Subclasses declare which columns they depend on (`REQUIRED_COLUMNS`) and
    how a single row becomes an object (`_build_record`). Everything else —
    reading the file, validating its header, and skipping unusable rows — is
    handled here.

    Attributes:
        skipped: `(row_index, reason)` pairs for rows the most recent `load()`
            could not build an object from.
    """

    REQUIRED_COLUMNS: ClassVar[Tuple[str, ...]] = ()

    #: Columns read verbatim rather than through pandas' missing-value
    #: handling. pandas treats the literal string `NA` as null, which would
    #: silently blank the continent of every North American airport and the
    #: country of every Namibian one. Listing a column that the file does not
    #: contain is harmless -- pandas ignores converters for absent columns.
    TEXT_COLUMNS: ClassVar[Tuple[str, ...]] = (
        "name",
        "iata_code",
        "icao_code",
        "iso_country",
        "iso_region",
        "continent",
        "municipality",
        "type",
        "scheduled_service",
        "is_international",
        "wikipedia_link",
        "flight_number",
        "airline_code",
        "source_airport_code",
        "destination_airport_code",
        "codeshare",
        "equipment",
    )

    def __init__(self, path: PathLike) -> None:
        """Configure the loader with the CSV file it should read.

        Args:
            path: CSV file to load.
        """
        self._path = Path(path)
        self.skipped: List[Tuple[int, str]] = []

    @property
    def path(self) -> Path:
        """Return the CSV file this loader reads.

        Returns:
            Path to the CSV file.
        """
        return self._path

    def read_frame(self) -> pd.DataFrame:
        """Read the CSV file and verify it has the columns this loader needs.

        Returns:
            `pandas.DataFrame` of the file's contents.

        Raises:
            ValueError: If any of `REQUIRED_COLUMNS` is absent from the file.
        """
        frame = pd.read_csv(
            self._path,
            converters={column: str for column in self.TEXT_COLUMNS},
        )
        missing = [column for column in self.REQUIRED_COLUMNS if column not in frame.columns]
        if missing:
            raise ValueError(
                f"{self._path} is missing required column(s): {', '.join(missing)}"
            )
        return frame

    def load(self) -> List[Any]:
        """Build a domain object for every usable row in the CSV file.

        Rows that cannot be converted are recorded in `skipped` rather than
        raising, so a single bad record never discards the whole dataset.

        Returns:
            List of domain objects, in file order.
        """
        self.skipped = []
        records: List[Any] = []
        for position, row in enumerate(self.read_frame().itertuples(index=False), start=1):
            try:
                record = self._build_record(row, position)
            except (TypeError, ValueError) as error:
                self._skip(position, str(error))
                continue
            if record is None:
                continue
            records.append(record)
        return records

    def _skip(self, position: int, reason: str) -> None:
        """Record that a row could not be converted into a domain object.

        Args:
            position: 1-based row number within the CSV file's data rows.
            reason: Why the row was skipped.
        """
        self.skipped.append((position, reason))

    @staticmethod
    def _text(value: Any) -> str:
        """Normalize a CSV cell to a stripped string.

        Args:
            value: Raw cell value, possibly NaN.

        Returns:
            Stripped string, or `""` when the cell is missing.
        """
        if value is None or pd.isna(value):
            return ""
        return str(value).strip()

    @classmethod
    def _optional_text(cls, row: Any, column: str) -> str:
        """Read a column that may not exist in this file.

        Columns are added to the processed CSVs over time, and snapshots are
        immutable — so a snapshot frozen before a column existed must still
        load. Absent columns read as missing rather than raising.

        Args:
            row: One row of the data frame.
            column: Column name to read.

        Returns:
            Stripped string, or `""` when the column or the value is missing.
        """
        return cls._text(getattr(row, column, None))

    @staticmethod
    def _optional_number(row: Any, column: str) -> Optional[float]:
        """Read a numeric column that may not exist in this file.

        Args:
            row: One row of the data frame.
            column: Column name to read.

        Returns:
            The value as a float, or `None` when the column or the value is
            missing. `None` rather than `0.0`, which is a meaningful value.
        """
        value = getattr(row, column, None)
        if value is None or pd.isna(value):
            return None
        return float(value)

    @abstractmethod
    def _build_record(self, row: Any, position: int) -> Optional[Any]:
        """Convert a single CSV row into a domain object.

        Args:
            row: One row of the data frame, as a named tuple.
            position: 1-based row number, for reporting skipped rows.

        Returns:
            The domain object, or `None` if the row should be skipped.
            **An implementation returning `None` must call `_skip` first**:
            `load` does not record the row itself, so a bare `None` drops it
            without saying so.
        """


class AirportLoader(CsvRecordLoader):
    """Loads `airports.csv` into `Airport` instances.

    Every column the file carries maps onto an `Airport` field. Columns added
    to the processed CSVs after a snapshot was frozen are read as missing
    rather than raising, so older snapshots keep loading.
    """

    REQUIRED_COLUMNS: ClassVar[Tuple[str, ...]] = (
        "name",
        "iso_country",
        "iata_code",
        "latitude_deg",
        "longitude_deg",
    )

    def _build_record(self, row: Any, position: int) -> Optional[Airport]:
        """Build one `Airport` from an `airports.csv` row.

        Args:
            row: One row of the airports data frame.
            position: 1-based row number, for reporting skipped rows.

        Returns:
            The `Airport`, or `None` if the row has no IATA code or unusable
            coordinates.
        """
        iata_code = self._text(row.iata_code)
        if not iata_code:
            self._skip(position, "missing iata_code")
            return None

        if pd.isna(row.latitude_deg) or pd.isna(row.longitude_deg):
            self._skip(position, f"{iata_code}: missing coordinates")
            return None

        return Airport(
            iata_code=iata_code,
            name=self._text(row.name),
            city=self._optional_text(row, "municipality"),
            country=self._text(row.iso_country),
            latitude=float(row.latitude_deg),
            longitude=float(row.longitude_deg),
            region=self._optional_text(row, "iso_region"),
            continent=self._optional_text(row, "continent"),
            elevation_ft=self._optional_number(row, "elevation_ft"),
            type=self._optional_text(row, "type"),
            icao_code=self._optional_text(row, "icao_code"),
            has_scheduled_service=(
                self._optional_text(row, "scheduled_service").lower() == "yes"
            ),
            is_international=(
                self._optional_text(row, "is_international").lower() == "yes"
            ),
            wikipedia_link=self._optional_text(row, "wikipedia_link"),
        )

    def load(self) -> List[Airport]:
        """Load every airport in the CSV file.

        Returns:
            List of `Airport` instances, in file order.
        """
        return super().load()

    def load_by_iata(self) -> Dict[str, Airport]:
        """Load the airports and index them by IATA code.

        Later duplicates of a code overwrite earlier ones.

        Returns:
            Mapping of normalized IATA code to `Airport`.
        """
        return {airport.iata_code: airport for airport in self.load()}


class RouteLoader(CsvRecordLoader):
    """Loads `routes.csv` into `Route` instances between known airports.

    Routes are built against a caller-supplied IATA map so every `Route`
    references the same `Airport` objects the graph holds — `FlightPlanner`
    resolves airports by identity in its adjacency dict, so sharing instances
    matters. The `codeshare`, `stops`, and `equipment` columns are dropped;
    `Route` has no field for them.

    Edges are directed and created exactly as listed: `routes.csv` already
    carries both directions for bidirectional city pairs, so no reverse edges
    are synthesized.
    """

    REQUIRED_COLUMNS: ClassVar[Tuple[str, ...]] = (
        "airline_code",
        "source_airport_code",
        "destination_airport_code",
        "distance_km",
    )

    def __init__(self, airports: Mapping[str, Airport], path: PathLike) -> None:
        """Configure the loader with the airports its routes may connect.

        Args:
            airports: Mapping of IATA code to `Airport`, as produced by
                `AirportLoader.load_by_iata()`.
            path: CSV file to load.
        """
        super().__init__(path)
        self._airports = dict(airports)

    def _build_record(self, row: Any, position: int) -> Optional[Route]:
        """Build one `Route` from a `routes.csv` row.

        A missing or unusable `distance_km` falls back to the great-circle
        distance between the two airports via `Point.distance_to`.

        Args:
            row: One row of the routes data frame.
            position: 1-based row number, for reporting skipped rows.

        Returns:
            The `Route`, or `None` if either endpoint is unknown.
        """
        origin_code = self._text(row.source_airport_code).upper()
        destination_code = self._text(row.destination_airport_code).upper()

        origin = self._airports.get(origin_code)
        destination = self._airports.get(destination_code)
        if origin is None or destination is None:
            unknown = origin_code if origin is None else destination_code
            self._skip(position, f"unknown airport code {unknown!r}")
            return None

        distance_km = row.distance_km
        if distance_km is None or pd.isna(distance_km):
            distance_km = origin.distance_to(destination)

        return Route(
            origin=origin,
            destination=destination,
            distance_km=float(distance_km),
            airline=self._text(row.airline_code),
            flight_number=self._optional_text(row, "flight_number"),
        )

    def load(self) -> List[Route]:
        """Load every route in the CSV file whose endpoints are known.

        Returns:
            List of `Route` instances, in file order.
        """
        return super().load()


def load_flight_planner(
    airports_path: PathLike,
    routes_path: PathLike,
) -> FlightPlanner:
    """Build a `FlightPlanner` populated from the processed CSV files.

    The convenience wrapper over the two loaders. It returns only the planner,
    so the per-row `skipped` lists the loaders build are not reachable through
    it -- and a caller who never sees them cannot tell a clean file from one
    that lost half its rows. Rather than change the return type, unusable rows
    are **warned about**, the same way `Catalog.planner()` reports a route
    reaching outside its scope. Construct `AirportLoader` and `RouteLoader`
    directly when the reasons themselves are wanted.

    Args:
        airports_path: Airports CSV to load.
        routes_path: Routes CSV to load.

    Returns:
        A `FlightPlanner` containing every loaded airport as a vertex and every
        loaded route as a directed edge.

    Warns:
        UserWarning: If either file had rows that could not be loaded.
    """
    airport_loader = AirportLoader(airports_path)
    airports = airport_loader.load_by_iata()

    route_loader = RouteLoader(airports, routes_path)
    routes = route_loader.load()

    for loader, what in ((airport_loader, "airport"), (route_loader, "route")):
        if loader.skipped:
            first = "; ".join(reason for _, reason in loader.skipped[:3])
            warnings.warn(
                f"{len(loader.skipped)} {what} row(s) in {loader.path.name} "
                f"could not be loaded and are absent from the planner "
                f"({first}{'; ...' if len(loader.skipped) > 3 else ''}). "
                f"Use {type(loader).__name__} directly for the full list.",
                UserWarning,
                stacklevel=2,
            )

    planner = FlightPlanner()
    for airport in airports.values():
        planner.add_vertex(airport)
    for route in routes:
        planner.add_edge(route)
    return planner
