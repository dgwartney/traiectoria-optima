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
        frame = pd.read_csv(self._path)
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

    @abstractmethod
    def _build_record(self, row: Any, position: int) -> Optional[Any]:
        """Convert a single CSV row into a domain object.

        Args:
            row: One row of the data frame, as a named tuple.
            position: 1-based row number, for reporting skipped rows.

        Returns:
            The domain object, or `None` if the row should be skipped.
        """


class AirportLoader(CsvRecordLoader):
    """Loads `airports.csv` into `Airport` instances.

    The `iso_region` and `type` columns are intentionally dropped: `Airport`
    models graph identity and geography only, and neither column maps onto one
    of its fields. `city` is left empty because the file has no city column.
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
            country=self._text(row.iso_country),
            latitude=float(row.latitude_deg),
            longitude=float(row.longitude_deg),
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

    Args:
        airports_path: Airports CSV to load.
        routes_path: Routes CSV to load.

    Returns:
        A `FlightPlanner` containing every loaded airport as a vertex and every
        loaded route as a directed edge.
    """
    airports = AirportLoader(airports_path).load_by_iata()

    planner = FlightPlanner()
    for airport in airports.values():
        planner.add_vertex(airport)
    for route in RouteLoader(airports, routes_path).load():
        planner.add_edge(route)
    return planner
