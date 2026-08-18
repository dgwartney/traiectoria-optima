import sqlite3
import pandas as pd
import os
from pathlib import Path


class FlightDataToDB:
    """
    Loads selected data files into a SQLite database for easy
    data exploration
    """

    def __init__(self):
        """
        Configure member variables with relative directories
        to our two main data sources
        """
        self._open_flights_data_dir = "data/raw/open_flights"
        self._our_airports_data_dir = "data/raw/our_airports"

    def get_root_path(self):
        """
        Create the root path to the project
        """
        return Path(os.path.dirname(__file__)).parent.parent

    def get_data_path(self, dir_path, file):
        """
        Create a file path to a data file
        """
        dir_path = Path(dir_path)
        # Combine and create an absolute path
        return os.path.abspath(os.path.join(self.get_root_path() , dir_path, file))

    def get_open_flights_airports(self):
        """
        Read the Open Flights airport data file and add missing column names
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
        """
        Read the Open Flights routes data file and add missing column names
        """
        return pd.read_csv(
            self.get_data_path(self._open_flights_data_dir, "routes.dat"),
            names=[
                "airline_code", "airline_id", "source_airport_code", "source_airport_id", "destination_airport_code", "destination_airport_id",
                "codeshare", "stops", "equipment"
            ],
            na_values="\\N"  # OpenFlights uses \N for missing values
        )

    def get_our_airports(self, file):
        """
        Read the Our Airports airport data
        """
        return pd.read_csv(
                self.get_data_path(
                    self._our_airports_data_dir, file)
        )

    def append_to_database(self, df, database_path, table):
        """
        Appends the input data frame to the specified SQLite data base file
        with the give table name
        """
        # Connect to SQLite database (creates the file if it does not exist)
        conn = sqlite3.connect(database_path)

        # Write data to a table 
        # index=False prevents the Pandas row counter from becoming a column
        df.to_sql(table, conn, if_exists="append", index=False)

        # Close the connection
        conn.close()

    def write_data_frame_to_csv(self, df, path):
        """
        Write out the data with the added headers
        """
        # Create the parent directories if the do not exist
        dir_path = os.path.dirname(path)
        dir_path.mkdir(parents=True, exist_ok=True)

        # Write the dataframe to a CSV file
        df.to_csv(path, index=False)

if __name__ == "__main__":
    cleaner = FlightDataToDB()

    SQLITE_DB_PATH = cleaner.get_data_path(os.path.join(cleaner.get_root_path(), "data/processed"), "flight_data.db")

    #
    # Open Flights Data
    #

    df = cleaner.get_open_flights_airports()
    cleaner.append_to_database(df, SQLITE_DB_PATH, "airport_open_flights")

    df = cleaner.get_open_flights_routes()
    cleaner.append_to_database(df, SQLITE_DB_PATH, "routes_open_flights")

    #
    # Our Airports Data
    #

    df = cleaner.get_our_airports("airports.csv")
    cleaner.append_to_database(df, SQLITE_DB_PATH, "airports_our_airports")
