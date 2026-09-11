"""Loading the processed CSV files into domain objects.

The package's I/O boundary: the only subpackage that touches the filesystem,
and the only one that depends on `pandas`. Everything above it is pure.
"""

from .csv_loader import AirportLoader, CsvRecordLoader, RouteLoader, load_flight_planner

__all__ = ["AirportLoader", "CsvRecordLoader", "RouteLoader", "load_flight_planner"]
