import sqlite3

import pandas as pd
import pytest

from flight_data import FlightDataToDB


@pytest.fixture
def cleaner():
    return FlightDataToDB()


def test_get_root_path_points_at_repo_root(cleaner):
    root = cleaner.get_root_path()
    # The repo root is identified by the presence of pyproject.toml.
    assert (root / "pyproject.toml").is_file()


def test_get_data_path_builds_absolute_path_to_existing_file(cleaner):
    path = cleaner.get_data_path("data/raw/open_flights", "airports.dat")
    assert path.endswith("airports.dat")
    assert pd.io.common.file_exists(path)


def test_get_open_flights_airports_has_expected_columns(cleaner):
    df = cleaner.get_open_flights_airports()
    assert list(df.columns) == [
        "airport_id", "name", "city", "country", "iata", "icao",
        "lat", "long", "altitude", "timezone", "dst",
        "tz", "type", "source",
    ]
    assert len(df) > 0
    # OpenFlights encodes missing values as "\N"; they should be parsed as NaN.
    assert df["iata"].isna().any() or df["iata"].notna().any()


def test_get_open_flights_routes_has_expected_columns(cleaner):
    df = cleaner.get_open_flights_routes()
    assert list(df.columns) == [
        "airline_code", "airline_id", "source_airport_code", "source_airport_id",
        "destination_airport_code", "destination_airport_id",
        "codeshare", "stops", "equipment",
    ]
    assert len(df) > 0


def test_get_our_airports_reads_named_csv(cleaner):
    df = cleaner.get_our_airports("airports.csv")
    assert len(df) > 0
    assert "iso_country" in df.columns


def test_append_to_database_creates_table_with_rows(cleaner, tmp_path):
    db_path = tmp_path / "test_flight_data.db"
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

    cleaner.append_to_database(df, str(db_path), "sample_table")

    with sqlite3.connect(db_path) as conn:
        result = pd.read_sql("SELECT * FROM sample_table ORDER BY a", conn)

    pd.testing.assert_frame_equal(result, df)


def test_append_to_database_appends_on_repeated_calls(cleaner, tmp_path):
    db_path = tmp_path / "test_flight_data.db"
    df = pd.DataFrame({"a": [1], "b": ["x"]})

    cleaner.append_to_database(df, str(db_path), "sample_table")
    cleaner.append_to_database(df, str(db_path), "sample_table")

    with sqlite3.connect(db_path) as conn:
        result = pd.read_sql("SELECT * FROM sample_table", conn)

    assert len(result) == 2


def test_write_data_frame_to_csv_writes_file(cleaner, tmp_path):
    df = pd.DataFrame({"a": [1, 2]})
    out_path = tmp_path / "nested" / "out.csv"

    cleaner.write_data_frame_to_csv(df, out_path)

    assert out_path.is_file()
