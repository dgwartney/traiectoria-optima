"""Loads OpenFlights and OurAirports source data into a SQLite database."""

import sqlite3
import pandas as pd
from pandas import DataFrame
import os
from pathlib import Path


class FlightDataToDB:
    """Loads selected data files into a SQLite database for easy exploration."""

    def __init__(self):
        """Configure relative directories for the two main data sources."""
        self._open_flights_data_dir = "data/raw/open_flights"
        self._our_airports_data_dir = "data/raw/our_airports"

    def get_root_path(self):
        """Return the project root path.

        Returns:
            Absolute `Path` to the repository root, derived from this file's
            location.
        """
        return Path(os.path.dirname(__file__)).parent.parent

    def get_data_path(self, dir_path, file):
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

    def get_open_flights_airports(self):
        """Read the OpenFlights airport data file, naming its columns.

        Returns:
            `pandas.DataFrame` of airport records.
        """
        return pd.read_csv(
            self.get_data_path(self._open_flights_data_dir, "airports.dat"),
            names=[
                "airport_id", "name", "city", "country", "iata", "icao",
                "lat", "long", "altitude", "timezone", "dst",
                "tz", "type", "source"
            ],
            na_values="\\N"  # OpenFlights uses \N for missing values
        )

    def get_open_flights_routes(self):
        """Read the OpenFlights routes data file, naming its columns.

        Returns:
            `pandas.DataFrame` of route records.
        """
        return pd.read_csv(
            self.get_data_path(self._open_flights_data_dir, "routes.dat"),
            names=[
                "airline_code", "airline_id", "source_airport_code", "source_airport_id", "destination_airport_code", "destination_airport_id",
                "codeshare", "stops", "equipment"
            ],
            na_values="\\N"  # OpenFlights uses \N for missing values
        )

    def get_our_airports(self, file) -> DataFrame:
        """Read an OurAirports data file.

        Args:
            file: File name under the OurAirports data directory.

        Returns:
            `pandas.DataFrame` of the file's contents.
        """
        return pd.read_csv(
                self.get_data_path(
                    self._our_airports_data_dir, file)
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

    def write_data_frame_to_csv(self, df, path) -> None:
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


    def read_csv_write_to_db(self, path: str, db_path: str, table: str) -> None:
        """Read a CSV file into a dataframe then write to a sqlite database
           with the provided path to the sqlite database and table.

        Args:
            path: Relative or absolute path to CSV file
            db_path: Path to the sqlite database
        """
        df = pd.read_csv(path)
        self.append_to_database(df, db_path, table)



if __name__ == "__main__":
    cleaner = FlightDataToDB()

    SQLITE_DB_PATH = cleaner.get_data_path(os.path.join(cleaner.get_root_path(), "data/processed"), "flight_data.db")

    #
    # Open Flights Data
    #

    df = cleaner.get_open_flights_airports()
    cleaner.append_to_database(df, SQLITE_DB_PATH, "airports_open_flights")

    df = cleaner.get_open_flights_routes()
    cleaner.append_to_database(df, SQLITE_DB_PATH, "routes_open_flights")

    #
    # Our Airports Data
    #

    df = cleaner.get_our_airports("airports.csv")
    cleaner.append_to_database(df, SQLITE_DB_PATH, "airports_our_airports")

    #
    # International airports
    #
    intl_airports_path = os.path.join(cleaner.get_root_path(), "data/processed", "international_airports.csv")
    cleaner.read_csv_write_to_db(intl_airports_path, SQLITE_DB_PATH, "intl_airports")
