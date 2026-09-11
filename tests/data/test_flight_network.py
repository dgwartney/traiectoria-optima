import pandas as pd
import pytest

from flight_network import FlightNetworkBuilder
from flight_planner.geo import Haversine, Point


AIRPORT_COLUMNS = [
    "name", "iso_country", "iso_region", "continent", "municipality",
    "iata_code", "icao_code", "latitude_deg", "longitude_deg",
    "elevation_ft", "scheduled_service", "type", "wikipedia_link",
]


def airports_frame(rows):
    return pd.DataFrame(rows, columns=AIRPORT_COLUMNS)


def routes_frame(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "airline_code", "airline_id", "source_airport_code",
            "source_airport_id", "destination_airport_code",
            "destination_airport_id", "codeshare", "stops", "equipment",
        ],
    )


def airport(iata, name=None, country="US", type_="large_airport", lat=0.0, lon=0.0):
    return [
        name or f"{iata} Field", country, f"{country}-XX", "NA", "City",
        iata, f"K{iata}", lat, lon, 100, "yes", type_, "",
    ]


def route(src, dst, airline="UA"):
    return [airline, "1", src, "2", dst, "3", "", 0, "320"]


@pytest.fixture
def builder():
    return FlightNetworkBuilder()


class TestResolution:
    def test_route_survives_when_both_endpoints_are_known(self, builder):
        airports = airports_frame([airport("SFO"), airport("BOS")])
        routes = routes_frame([route("SFO", "BOS")])

        result = builder.build(airports, routes)

        assert len(result.routes) == 1
        assert result.skipped == []

    def test_route_dropped_and_reported_when_an_endpoint_is_unknown(self, builder):
        airports = airports_frame([airport("SFO")])
        routes = routes_frame([route("SFO", "TXL")])

        result = builder.build(airports, routes)

        assert len(result.routes) == 0
        assert len(result.skipped) == 1
        position, reason = result.skipped[0]
        assert "TXL" in reason

    def test_airports_are_limited_to_those_routes_reference(self, builder):
        airports = airports_frame([airport("SFO"), airport("BOS"), airport("LAX")])
        routes = routes_frame([route("SFO", "BOS")])

        result = builder.build(airports, routes)

        assert sorted(result.airports["iata_code"]) == ["BOS", "SFO"]


class TestDistances:
    def test_distance_matches_the_haversine_implementation(self, builder):
        airports = airports_frame([
            airport("SFO", lat=37.619806, lon=-122.374821),
            airport("BOS", lat=42.364347, lon=-71.005181),
        ])
        routes = routes_frame([route("SFO", "BOS")])

        result = builder.build(airports, routes)

        expected = Haversine().calculate(
            Point(latitude=37.619806, longitude=-122.374821),
            Point(latitude=42.364347, longitude=-71.005181),
        )
        assert result.routes["distance_km"].iloc[0] == pytest.approx(expected)


class TestOrdering:
    def test_routes_are_sorted_by_endpoints(self, builder):
        airports = airports_frame([airport("SFO"), airport("BOS"), airport("LAX")])
        routes = routes_frame([
            route("SFO", "LAX"), route("BOS", "SFO"), route("SFO", "BOS"),
        ])

        result = builder.build(airports, routes)

        pairs = list(zip(
            result.routes["source_airport_code"],
            result.routes["destination_airport_code"],
        ))
        assert pairs == sorted(pairs)

    def test_airports_are_sorted_by_name(self, builder):
        airports = airports_frame([
            airport("SFO", name="Zulu Field"), airport("BOS", name="Alpha Field"),
        ])
        routes = routes_frame([route("SFO", "BOS")])

        result = builder.build(airports, routes)

        names = list(result.airports["name"])
        assert names == sorted(names)


class TestLegacyFilter:
    """The filter today's committed CSVs were produced by.

    `flight_data.sql:16-17` reads `source IN (...) OR destination IN (...)`,
    but `united_airlines_airports` holds only US large airports and the
    distance join is an INNER JOIN against it on *both* endpoints — which
    silently tightens the OR into an AND. The committed 861 rows are the AND.
    """

    def test_both_endpoints_must_match_not_either(self, builder):
        airports = airports_frame([
            airport("SFO"), airport("BOS"),
            airport("XXX", type_="medium_airport"),
            airport("YYY", country="FR"),
        ])
        routes = routes_frame([
            route("SFO", "BOS"),   # both US large      -> kept
            route("SFO", "XXX"),   # one is medium      -> dropped
            route("SFO", "YYY"),   # one is not US      -> dropped
        ])

        result = builder.build(
            airports, routes, airline="UA", airport_type="large_airport", country="US",
        )

        pairs = list(zip(
            result.routes["source_airport_code"],
            result.routes["destination_airport_code"],
        ))
        assert pairs == [("SFO", "BOS")]

    def test_other_airlines_are_excluded(self, builder):
        airports = airports_frame([airport("SFO"), airport("BOS")])
        routes = routes_frame([route("SFO", "BOS", airline="AA")])

        result = builder.build(
            airports, routes, airline="UA", airport_type="large_airport", country="US",
        )

        assert len(result.routes) == 0


class TestFlightNumbers:
    """Identifiers assigned once, on the raw route set.

    OpenFlights carries no flight numbers, so they are synthesized here.
    Assignment happens before resolution and before any filtering, which is
    what makes an identifier permanent: adding an IATA override or narrowing
    to one airline must never renumber anything.
    """

    def test_numbers_are_per_airline_and_zero_padded(self, builder):
        airports = airports_frame([airport("AAA"), airport("BBB"), airport("CCC")])
        routes = routes_frame([
            route("BBB", "CCC", airline="UA"),
            route("AAA", "BBB", airline="UA"),
            route("AAA", "CCC", airline="AA"),
        ])

        result = builder.build(airports, routes)

        numbers = dict(zip(
            zip(result.routes["source_airport_code"],
                result.routes["destination_airport_code"]),
            result.routes["flight_number"],
        ))
        # Ordered by (source, destination) within each airline.
        assert numbers[("AAA", "BBB")] == "UA0001"
        assert numbers[("BBB", "CCC")] == "UA0002"
        # Each airline numbers from 1 independently.
        assert numbers[("AAA", "CCC")] == "AA0001"

    def test_numbering_survives_filtering_leaving_gaps(self, builder):
        # AAA->BBB would be UA0001 but is filtered out; BBB->CCC keeps UA0002
        # rather than sliding down to UA0001.
        airports = airports_frame([
            airport("AAA", type_="medium_airport"), airport("BBB"), airport("CCC"),
        ])
        routes = routes_frame([
            route("AAA", "BBB", airline="UA"),
            route("BBB", "CCC", airline="UA"),
        ])

        result = builder.build(airports, routes, airport_type="large_airport")

        assert list(result.routes["flight_number"]) == ["UA0002"]

    def test_numbering_is_unaffected_by_input_row_order(self, builder):
        airports = airports_frame([airport("AAA"), airport("BBB"), airport("CCC")])
        forward = routes_frame([route("AAA", "BBB"), route("BBB", "CCC")])
        reversed_ = routes_frame([route("BBB", "CCC"), route("AAA", "BBB")])

        a = builder.build(airports, forward).routes
        b = builder.build(airports, reversed_).routes

        assert list(a["flight_number"]) == list(b["flight_number"])


class TestOutputs:
    def test_write_csv_round_trips(self, builder, tmp_path):
        airports = airports_frame([airport("SFO", lat=37.6, lon=-122.4),
                                   airport("BOS", lat=42.4, lon=-71.0)])
        routes = routes_frame([route("SFO", "BOS")])
        result = builder.build(airports, routes)

        airports_csv = tmp_path / "airports.csv"
        routes_csv = tmp_path / "routes.csv"
        builder.write_csv(result, airports_csv, routes_csv)

        written = pd.read_csv(routes_csv)
        assert list(written["flight_number"]) == ["UA0001"]
        assert "wikipedia_link" in pd.read_csv(airports_csv).columns

    def test_sqlite_tables_match_the_csvs(self, builder, tmp_path):
        import sqlite3

        airports = airports_frame([airport("SFO", lat=37.6, lon=-122.4),
                                   airport("BOS", lat=42.4, lon=-71.0)])
        routes = routes_frame([route("SFO", "BOS")])
        result = builder.build(airports, routes)

        airports_csv = tmp_path / "airports.csv"
        routes_csv = tmp_path / "routes.csv"
        database = tmp_path / "flight_data.db"
        builder.write_csv(result, airports_csv, routes_csv)
        builder.write_sqlite(result, database)

        with sqlite3.connect(database) as connection:
            for table, path in (("airports", airports_csv), ("routes", routes_csv)):
                from_db = pd.read_sql_query(f"SELECT * FROM {table}", connection)
                from_csv = pd.read_csv(path, keep_default_na=False).astype(str)
                assert list(from_db.columns) == list(from_csv.columns)
                assert len(from_db) == len(from_csv)


class TestEnrichedColumns:
    def test_descriptive_columns_are_emitted(self, builder, tmp_path):
        # The build frame carries every source column; what matters is which
        # ones survive into the written file.
        airports = airports_frame([airport("SFO"), airport("BOS")])
        routes = routes_frame([route("SFO", "BOS")])
        result = builder.build(airports, routes)

        airports_csv = tmp_path / "airports.csv"
        builder.write_csv(result, airports_csv, tmp_path / "routes.csv")

        emitted = pd.read_csv(airports_csv).columns
        for column in (
            "municipality", "continent", "icao_code",
            "elevation_ft", "scheduled_service", "wikipedia_link",
        ):
            assert column in emitted

    def test_airport_loader_reads_the_emitted_file(self, builder, tmp_path):
        # Closes the loop: the columns the pipeline writes are the ones
        # AirportLoader knows how to read.
        from flight_planner.loaders import AirportLoader

        airports = airports_frame([airport("SFO", lat=37.6, lon=-122.4),
                                   airport("BOS", lat=42.4, lon=-71.0)])
        result = builder.build(airports, routes_frame([route("SFO", "BOS")]))
        airports_csv = tmp_path / "airports.csv"
        builder.write_csv(result, airports_csv, tmp_path / "routes.csv")

        loaded = AirportLoader(airports_csv).load_by_iata()["SFO"]
        assert loaded.city == "City"
        assert loaded.continent == "NA"
        assert loaded.icao_code == "KSFO"
        assert loaded.elevation_ft == 100.0
        assert loaded.has_scheduled_service is True


class TestSnapshots:
    """A frozen, checksummed copy of a build."""

    def _build(self, builder):
        airports = airports_frame([airport("SFO", lat=37.6, lon=-122.4),
                                   airport("BOS", lat=42.4, lon=-71.0)])
        return builder.build(airports, routes_frame([route("SFO", "BOS")]))

    def test_snapshot_writes_data_and_manifest(self, builder, tmp_path):
        directory = builder.write_snapshot(self._build(builder), tmp_path, {})

        assert (directory / "airports.csv").is_file()
        assert (directory / "routes.csv").is_file()
        assert (directory / "manifest.json").is_file()

    def test_manifest_records_checksums_that_match_the_files(self, builder, tmp_path):
        import hashlib
        import json

        directory = builder.write_snapshot(self._build(builder), tmp_path, {})
        manifest = json.loads((directory / "manifest.json").read_text())

        for filename, recorded in manifest["files"].items():
            actual = hashlib.sha256((directory / filename).read_bytes()).hexdigest()
            assert recorded["sha256"] == actual
            assert recorded["bytes"] == (directory / filename).stat().st_size
        assert manifest["files"]["routes.csv"]["rows"] == 1

    def test_manifest_records_the_slice_criteria(self, builder, tmp_path):
        criteria = {"airline": "UA", "airport_type": "large_airport", "country": "US"}

        directory = builder.write_snapshot(self._build(builder), tmp_path, criteria)
        manifest = __import__("json").loads((directory / "manifest.json").read_text())

        assert manifest["criteria"] == criteria

    def test_identical_data_produces_the_same_id(self, builder, tmp_path):
        first = builder.write_snapshot(self._build(builder), tmp_path / "a", {})
        second = builder.write_snapshot(self._build(builder), tmp_path / "b", {})

        assert first.name == second.name


class TestInternationalFlag:
    """Marks airports listed on Wikipedia's international-airports list.

    A weaker source than the rest of the row -- OurAirports supplies every
    other field -- so the column records listing, not a claim about service.
    """

    def test_listed_airports_are_marked(self, builder, tmp_path):
        international = tmp_path / "international_airports.csv"
        international.write_text("location,airport,iata,latitude,longitude,region\n"
                                 "Boston,Logan,BOS,42.4,-71.0,Americas\n")
        airports = airports_frame([airport("SFO"), airport("BOS")])
        routes = routes_frame([route("SFO", "BOS")])

        result = builder.build(airports, routes, international=international)

        flags = dict(zip(result.airports["iata_code"], result.airports["is_international"]))
        assert flags["BOS"] == "yes"
        assert flags["SFO"] == "no"

    def test_column_is_emitted(self, builder, tmp_path):
        result = builder.build(
            airports_frame([airport("SFO"), airport("BOS")]),
            routes_frame([route("SFO", "BOS")]),
        )
        airports_csv = tmp_path / "airports.csv"
        builder.write_csv(result, airports_csv, tmp_path / "routes.csv")

        assert "is_international" in pd.read_csv(airports_csv).columns

    def test_without_the_list_everything_reads_domestic(self, builder):
        result = builder.build(
            airports_frame([airport("SFO"), airport("BOS")]),
            routes_frame([route("SFO", "BOS")]),
        )

        assert set(result.airports["is_international"]) == {"no"}

    def test_loader_round_trips_the_flag(self, builder, tmp_path):
        from flight_planner.loaders import AirportLoader

        international = tmp_path / "intl.csv"
        international.write_text("iata\nBOS\n")
        result = builder.build(
            airports_frame([airport("SFO", lat=37.6, lon=-122.4),
                            airport("BOS", lat=42.4, lon=-71.0)]),
            routes_frame([route("SFO", "BOS")]),
            international=international,
        )
        airports_csv = tmp_path / "airports.csv"
        builder.write_csv(result, airports_csv, tmp_path / "routes.csv")

        loaded = AirportLoader(airports_csv).load_by_iata()
        assert loaded["BOS"].is_international is True
        assert loaded["SFO"].is_international is False
