"""Loads OpenFlights and OurAirports source data into a SQLite database."""

import argparse
import sqlite3
import pandas as pd
from pandas import DataFrame
import os
from pathlib import Path
from typing import Optional, Union

# Directories the two source datasets are vendored into, relative to the
# project root. Constructor defaults only -- the Makefile passes every real
# path as an argument.
OPEN_FLIGHTS_DATA_DIR = "data/raw/open_flights"
OUR_AIRPORTS_DATA_DIR = "data/raw/our_airports"

# OurAirports uses "NA" as a real value in two columns -- North America in
# `continent`, Namibia in `iso_country` -- and "NA" is one of pandas' default
# NA sentinels. A per-column converter runs before NA detection, so it rescues
# exactly these columns without disabling missing-value handling everywhere
# else. Without it, 303 Namibian airports load as NULL.
OUR_AIRPORTS_STRING_COLUMNS = {"iso_country": str, "continent": str}


class FlightDataToDB:
    """Loads selected data files into a SQLite database for easy exploration."""

    def __init__(
        self,
        open_flights_data_dir: Union[str, Path] = OPEN_FLIGHTS_DATA_DIR,
        our_airports_data_dir: Union[str, Path] = OUR_AIRPORTS_DATA_DIR,
    ) -> None:
        """Configure the directories holding the two main data sources.

        Args:
            open_flights_data_dir: Directory holding the OpenFlights `.dat`
                files, relative to the project root.
            our_airports_data_dir: Directory holding the OurAirports CSV files,
                relative to the project root.
        """
        self._open_flights_data_dir = open_flights_data_dir
        self._our_airports_data_dir = our_airports_data_dir

    def get_root_path(self) -> Path:
        """Return the project root path.

        Returns:
            Absolute `Path` to the repository root, derived from this file's
            location.
        """
        return Path(os.path.dirname(__file__)).parent.parent

    def get_data_path(self, dir_path: Union[str, Path], file: str) -> str:
        """Build an absolute path to a data file under the project root.

        Args:
            dir_path: Directory containing `file`, relative to the project root.
            file: File name.

        Returns:
            Absolute path string to the data file.
        """
        dir_path = Path(dir_path)
        # Combine and create an absolute path
        return os.path.abspath(os.path.join(self.get_root_path() , dir_path, file))

    def get_open_flights_airports(self, path: Optional[Union[str, Path]] = None) -> DataFrame:
        """Read the OpenFlights airport data file, naming its columns.

        Args:
            path: Path to `airports.dat`. Defaults to the file in the
                OpenFlights data directory.

        Returns:
            `pandas.DataFrame` of airport records.
        """
        return pd.read_csv(
            path or self.get_data_path(self._open_flights_data_dir, "airports.dat"),
            names=[
                "airport_id", "name", "city", "country", "iata", "icao",
                "lat", "long", "altitude", "timezone", "dst",
                "tz", "type", "source"
            ],
            na_values="\\N"  # OpenFlights uses \N for missing values
        )

    def get_open_flights_routes(self, path: Optional[Union[str, Path]] = None) -> DataFrame:
        """Read the OpenFlights routes data file, naming its columns.

        Args:
            path: Path to `routes.dat`. Defaults to the file in the
                OpenFlights data directory.

        Returns:
            `pandas.DataFrame` of route records.
        """
        return pd.read_csv(
            path or self.get_data_path(self._open_flights_data_dir, "routes.dat"),
            names=[
                "airline_code", "airline_id", "source_airport_code", "source_airport_id", "destination_airport_code", "destination_airport_id",
                "codeshare", "stops", "equipment"
            ],
            na_values="\\N"  # OpenFlights uses \N for missing values
        )

    def get_our_airports(self, file: str, path: Optional[Union[str, Path]] = None) -> DataFrame:
        """Read an OurAirports data file.

        Args:
            file: File name under the OurAirports data directory.
            path: Full path to the file. Defaults to `file` resolved against
                the OurAirports data directory.

        Returns:
            `pandas.DataFrame` of the file's contents.
        """
        return pd.read_csv(
            path or self.get_data_path(self._our_airports_data_dir, file),
            converters=OUR_AIRPORTS_STRING_COLUMNS,
        )

    def append_to_database(self, df: DataFrame, database_path: str, table: str) -> None:
        """Append a data frame to a table in a SQLite database.

        Args:
            df: Data to write.
            database_path: Path to the SQLite database file, created if
                it does not already exist.
            table: Destination table name.
        """
        # Connect to SQLite database (creates the file if it does not exist)
        conn = sqlite3.connect(database_path)

        # Write data to a table
        # index=False prevents the Pandas row counter from becoming a column
        df.to_sql(table, conn, if_exists="append", index=False)

        # Close the connection
        conn.close()

    def write_data_frame_to_csv(self, df: DataFrame, path: Union[str, Path]) -> None:
        """Write a data frame to a CSV file, creating parent directories as needed.

        Args:
            df: Data to write.
            path: Destination CSV file path.
        """
        # Create the parent directories if the do not exist
        dir_path = Path(os.path.dirname(path))
        dir_path.mkdir(parents=True, exist_ok=True)

        # Write the dataframe to a CSV file
        df.to_csv(path, index=False)


    def read_csv_write_to_db(
        self, path: str, db_path: str, table: str, converters: Optional[dict] = None
    ) -> None:
        """Read a CSV file into a dataframe then write to a sqlite database.

        Args:
            path: Relative or absolute path to CSV file
            db_path: Path to the sqlite database
            table: Name of the destination table
            converters: Per-column converters passed to `pandas.read_csv`. Use
                `OUR_AIRPORTS_STRING_COLUMNS` for OurAirports files, whose "NA"
                values would otherwise be read as missing.
        """
        df = pd.read_csv(path, converters=converters or {})
        self.append_to_database(df, db_path, table)



def parse_args() -> argparse.Namespace:
    """Parse the input and output file paths from the command line.

    Returns:
        A namespace with `open_flights_airports`, `open_flights_routes`,
        `our_airports`, `intl_airports` and `database` attributes.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "open_flights_airports",
        help="Path to the OpenFlights airports.dat file.",
    )
    parser.add_argument(
        "open_flights_routes",
        help="Path to the OpenFlights routes.dat file.",
    )
    parser.add_argument(
        "our_airports",
        help="Path to the OurAirports airports.csv file.",
    )
    parser.add_argument(
        "intl_airports",
        help="Path to the international_airports.csv file produced by international_airports.py.",
    )
    parser.add_argument(
        "database",
        help="File path of the SQLite database to write, created if it does not exist.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cleaner = FlightDataToDB()

    #
    # Open Flights Data
    #

    df = cleaner.get_open_flights_airports(args.open_flights_airports)
    cleaner.append_to_database(df, args.database, "airports_open_flights")

    df = cleaner.get_open_flights_routes(args.open_flights_routes)
    cleaner.append_to_database(df, args.database, "routes_open_flights")

    #
    # Our Airports Data
    #

    cleaner.read_csv_write_to_db(
        args.our_airports,
        args.database,
        "airports_our_airports",
        converters=OUR_AIRPORTS_STRING_COLUMNS,
    )

    #
    # International airports
    #
    cleaner.read_csv_write_to_db(args.intl_airports, args.database, "intl_airports")
