import math

import pytest

from flight_planner.flights import Airport
from flight_planner.loaders import AirportLoader, RouteLoader, load_flight_planner
from flight_planner.flights import Route

AIRPORT_HEADER = "name,iso_country,iso_region,iata_code,latitude_deg,longitude_deg,type\n"
ROUTE_HEADER = (
    "airline_code,source_airport_code,destination_airport_code,"
    "codeshare,stops,equipment,distance_km\n"
)


def _write(tmp_path, filename, contents):
    path = tmp_path / filename
    path.write_text(contents)
    return path


class TestAirportLoader:
    def test_loads_real_airports_file(self, airports_csv):
        loader = AirportLoader(airports_csv)
        airports = loader.load()

        assert loader.skipped == []
        assert len(airports) == 88
        assert all(isinstance(airport, Airport) for airport in airports)

    def test_known_airport_has_expected_fields(self, airports_csv):
        sfo = AirportLoader(airports_csv).load_by_iata()["SFO"]

        assert sfo.name == "San Francisco International Airport"
        assert sfo.country == "US"
        assert sfo.latitude == pytest.approx(37.619806)
        assert sfo.longitude == pytest.approx(-122.374821)

    def test_iata_code_is_normalized(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            AIRPORT_HEADER + '"Test Field",US,US-CA," sfo ",37.6,-122.4,large_airport\n',
        )

        assert AirportLoader(path).load()[0].iata_code == "SFO"

    def test_row_without_iata_code_is_skipped(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            AIRPORT_HEADER
            + '"No Code",US,US-CA,,37.6,-122.4,large_airport\n'
            + '"Has Code",US,US-CO,DEN,39.86,-104.67,large_airport\n',
        )
        loader = AirportLoader(path)
        airports = loader.load()

        assert [airport.iata_code for airport in airports] == ["DEN"]
        assert loader.skipped == [(1, "missing iata_code")]

    def test_row_without_coordinates_is_skipped(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            AIRPORT_HEADER + '"No Coords",US,US-CA,XXX,,,large_airport\n',
        )
        loader = AirportLoader(path)

        assert loader.load() == []
        assert loader.skipped == [(1, "XXX: missing coordinates")]

    def test_missing_required_column_raises(self, tmp_path):
        path = _write(tmp_path, "airports.csv", "name,iata_code\n" '"Nowhere",XXX\n')

        with pytest.raises(ValueError, match="missing required column"):
            AirportLoader(path).load()


class TestRouteLoader:
    def test_loads_real_routes_file(self, airports_csv, routes_csv):
        airports = AirportLoader(airports_csv).load_by_iata()
        loader = RouteLoader(airports, routes_csv)
        routes = loader.load()

        assert loader.skipped == []
        assert len(routes) == 861
        assert all(isinstance(route, Route) for route in routes)

    def test_routes_reuse_the_supplied_airport_instances(self, airports_csv, routes_csv):
        airports = AirportLoader(airports_csv).load_by_iata()
        routes = RouteLoader(airports, routes_csv).load()

        first = routes[0]
        assert first.origin is airports[first.origin.iata_code]
        assert first.destination is airports[first.destination.iata_code]

    def test_route_fields_come_from_the_row(self, tmp_path):
        airports = {"SFO": Airport("SFO", latitude=37.6, longitude=-122.4),
                    "BOS": Airport("BOS", latitude=42.4, longitude=-71.0)}
        path = _write(tmp_path, "routes.csv", ROUTE_HEADER + 'UA,SFO,BOS,,0,"752 753",4341.0\n')

        route = RouteLoader(airports, path).load()[0]

        assert route.airline == "UA"
        assert route.distance_km == 4341.0
        assert route.origin is airports["SFO"]
        assert route.destination is airports["BOS"]

    def test_unknown_airport_code_is_skipped(self, tmp_path):
        airports = {"SFO": Airport("SFO", latitude=37.6, longitude=-122.4)}
        path = _write(
            tmp_path,
            "routes.csv",
            ROUTE_HEADER + "UA,SFO,ZZZ,,0,752,4341.0\n" + "UA,ZZZ,SFO,,0,752,4341.0\n",
        )
        loader = RouteLoader(airports, path)

        assert loader.load() == []
        assert loader.skipped == [
            (1, "unknown airport code 'ZZZ'"),
            (2, "unknown airport code 'ZZZ'"),
        ]

    def test_missing_distance_falls_back_to_great_circle(self, tmp_path):
        airports = {"SFO": Airport("SFO", latitude=37.619806, longitude=-122.374821),
                    "BOS": Airport("BOS", latitude=42.36197, longitude=-71.0079)}
        path = _write(tmp_path, "routes.csv", ROUTE_HEADER + "UA,SFO,BOS,,0,752,\n")

        route = RouteLoader(airports, path).load()[0]

        assert math.isfinite(route.distance_km)
        assert route.distance_km == pytest.approx(
            airports["SFO"].distance_to(airports["BOS"])
        )
        assert route.distance_km > 0

    def test_missing_required_column_raises(self, tmp_path):
        path = _write(tmp_path, "routes.csv", "airline_code,source_airport_code\nUA,SFO\n")

        with pytest.raises(ValueError, match="missing required column"):
            RouteLoader({}, path).load()


class TestLoadFlightPlanner:
    def test_planner_is_populated_from_the_processed_files(self, airports_csv, routes_csv):
        planner = load_flight_planner(airports_csv, routes_csv)

        assert len(planner.vertices) == 88
        assert len(planner.edges) == 861
        assert planner.find_airport("ord") is not None

    def test_planner_finds_a_route_between_real_airports(self, airports_csv, routes_csv):
        planner = load_flight_planner(airports_csv, routes_csv)

        distance, legs = planner.find_shortest_route("SFO", "BOS")

        assert math.isfinite(distance)
        assert legs
        assert legs[0].origin.iata_code == "SFO"
        assert legs[-1].destination.iata_code == "BOS"
        assert distance == pytest.approx(sum(leg.distance_km for leg in legs))

    def test_planner_finds_a_multi_leg_route(self, airports_csv, routes_csv):
        planner = load_flight_planner(airports_csv, routes_csv)

        distance, legs = planner.find_shortest_route("PSP", "SYR")

        assert len(legs) > 1
        assert distance == pytest.approx(sum(leg.distance_km for leg in legs))


EXTENDED_AIRPORT_HEADER = (
    "name,iso_country,iso_region,continent,municipality,iata_code,icao_code,"
    "latitude_deg,longitude_deg,elevation_ft,scheduled_service,type,wikipedia_link\n"
)
INTERNATIONAL_AIRPORT_HEADER = (
    "name,iso_country,iata_code,latitude_deg,longitude_deg,is_international\n"
)
EXTENDED_ROUTE_HEADER = (
    "flight_number,airline_code,source_airport_code,destination_airport_code,"
    "codeshare,stops,equipment,distance_km\n"
)


class TestAirportLoaderDescriptiveFields:
    def test_region_and_type_come_from_todays_columns(self, tmp_path):
        # airports.csv already carries iso_region and type; the loader used to
        # drop both for want of a field to put them in.
        path = _write(
            tmp_path,
            "airports.csv",
            AIRPORT_HEADER
            + '"Test Field",US,US-CA,SFO,37.6,-122.4,large_airport\n',
        )

        airport = AirportLoader(path).load()[0]

        assert airport.region == "US-CA"
        assert airport.type == "large_airport"

    def test_absent_columns_fall_back_to_defaults(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            AIRPORT_HEADER
            + '"Test Field",US,US-CA,SFO,37.6,-122.4,large_airport\n',
        )

        airport = AirportLoader(path).load()[0]

        assert airport.city == ""
        assert airport.continent == ""
        assert airport.icao_code == ""
        assert airport.wikipedia_link == ""
        assert airport.elevation_ft is None
        assert airport.has_scheduled_service is False

    def test_extended_columns_are_read(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            EXTENDED_AIRPORT_HEADER
            + '"San Francisco International Airport",US,US-CA,NA,'
            '"San Francisco",SFO,KSFO,37.619806,-122.374821,13,yes,large_airport,'
            "https://en.wikipedia.org/wiki/San_Francisco_International_Airport\n",
        )

        airport = AirportLoader(path).load()[0]

        assert airport.city == "San Francisco"
        assert airport.continent == "NA"
        assert airport.icao_code == "KSFO"
        assert airport.elevation_ft == 13.0
        assert airport.has_scheduled_service is True
        assert airport.wikipedia_link.endswith("San_Francisco_International_Airport")

    def test_scheduled_service_no_reads_as_false(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            EXTENDED_AIRPORT_HEADER
            + '"Quiet Field",US,US-CA,NA,"Nowhere",XXX,KXXX,37.6,-122.4,13,no,small_airport,\n',
        )

        assert AirportLoader(path).load()[0].has_scheduled_service is False

    def test_missing_elevation_stays_none(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            EXTENDED_AIRPORT_HEADER
            + '"No Elevation",US,US-CA,NA,"Nowhere",XXX,KXXX,37.6,-122.4,,yes,small_airport,\n',
        )

        assert AirportLoader(path).load()[0].elevation_ft is None


class TestRouteLoaderFlightNumber:
    def test_flight_number_is_read_when_present(self, tmp_path):
        airports = {
            "SFO": Airport("SFO", latitude=37.6, longitude=-122.4),
            "BOS": Airport("BOS", latitude=42.4, longitude=-71.0),
        }
        path = _write(
            tmp_path,
            "routes.csv",
            EXTENDED_ROUTE_HEADER + "UA1876,UA,SFO,BOS,,0,320,4341.0\n",
        )

        assert RouteLoader(airports, path).load()[0].flight_number == "UA1876"

    def test_flight_number_defaults_to_empty_when_absent(self, tmp_path):
        airports = {
            "SFO": Airport("SFO", latitude=37.6, longitude=-122.4),
            "BOS": Airport("BOS", latitude=42.4, longitude=-71.0),
        }
        path = _write(
            tmp_path,
            "routes.csv",
            ROUTE_HEADER + "UA,SFO,BOS,,0,320,4341.0\n",
        )

        assert RouteLoader(airports, path).load()[0].flight_number == ""


class TestNaLikeCodesSurviveParsing:
    """`NA` is a real code, not a missing value.

    pandas treats the literal string `NA` as null by default, which would
    blank the continent of 39,715 North American airports and the country of
    303 Namibian ones.
    """

    def test_north_america_continent_is_not_parsed_as_missing(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            EXTENDED_AIRPORT_HEADER
            + '"Logan",US,US-MA,NA,"Boston",BOS,KBOS,42.36,-71.0,20,yes,large_airport,\n',
        )

        assert AirportLoader(path).load()[0].continent == "NA"

    def test_namibia_country_is_not_parsed_as_missing(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            EXTENDED_AIRPORT_HEADER
            + '"Hosea Kutako",NA,NA-KH,AF,"Windhoek",WDH,FYWH,-22.48,17.47,5640,yes,large_airport,\n',
        )

        airport = AirportLoader(path).load()[0]
        assert airport.country == "NA"
        assert airport.region == "NA-KH"


class TestInternationalFlag:
    def test_is_international_is_read_when_present(self, tmp_path):
        path = _write(
            tmp_path,
            "airports.csv",
            INTERNATIONAL_AIRPORT_HEADER
            + '"Logan",US,BOS,42.36,-71.0,yes\n'
            + '"Nowhere",US,XXX,37.6,-122.4,no\n',
        )

        airports = AirportLoader(path).load_by_iata()

        assert airports["BOS"].is_international is True
        assert airports["XXX"].is_international is False

    def test_absent_column_defaults_to_false(self, tmp_path):
        # Snapshots frozen before the column existed must still load.
        path = _write(
            tmp_path,
            "airports.csv",
            AIRPORT_HEADER + '"Logan",US,US-MA,BOS,42.36,-71.0,large_airport\n',
        )

        assert AirportLoader(path).load()[0].is_international is False


class TestLoadFlightPlannerReportsWhatItDropped:
    """The convenience wrapper returns only a planner, so `skipped` is lost.

    Found by the #72 code review. `AirportLoader` and `RouteLoader` each
    record a `(row, reason)` pair for every row they could not build, but
    `load_flight_planner` discards both loaders -- a caller who never sees
    them cannot tell a clean file from one that lost half its rows. That is
    the same defect report §2.3 argues against one layer up: "a cleaning step
    that cannot say what it removed is indistinguishable from a bug."

    The fix warns rather than changing the return type, matching what
    `Catalog.planner()` already does for a route reaching outside its scope.
    """

    def _files(self, tmp_path, airports, routes):
        return (
            _write(tmp_path, "airports.csv", AIRPORT_HEADER + airports),
            _write(tmp_path, "routes.csv", ROUTE_HEADER + routes),
        )

    def test_a_clean_pair_of_files_warns_about_nothing(self, tmp_path, recwarn):
        airports, routes = self._files(
            tmp_path,
            '"Logan",US,US-MA,BOS,42.36,-71.0,large_airport\n'
            '"SFO",US,US-CA,SFO,37.62,-122.37,large_airport\n',
            "UA,SFO,BOS,N,0,738,4340\n",
        )

        planner = load_flight_planner(airports, routes)

        assert len(planner.vertices) == 2
        assert len(planner.edges) == 1
        assert [w for w in recwarn if issubclass(w.category, UserWarning)] == []

    def test_an_unusable_airport_row_is_warned_about(self, tmp_path):
        airports, routes = self._files(
            tmp_path,
            '"Logan",US,US-MA,BOS,42.36,-71.0,large_airport\n'
            '"Nameless",US,US-CA,,37.62,-122.37,large_airport\n',
            "",
        )

        with pytest.warns(UserWarning, match="1 airport row"):
            planner = load_flight_planner(airports, routes)

        assert len(planner.vertices) == 1

    def test_a_route_to_an_unknown_airport_is_warned_about(self, tmp_path):
        airports, routes = self._files(
            tmp_path,
            '"Logan",US,US-MA,BOS,42.36,-71.0,large_airport\n'
            '"SFO",US,US-CA,SFO,37.62,-122.37,large_airport\n',
            "UA,SFO,BOS,N,0,738,4340\n" "UA,SFO,ZZZ,N,0,738,100\n",
        )

        with pytest.warns(UserWarning, match=r"1 route row.*ZZZ"):
            planner = load_flight_planner(airports, routes)

        assert len(planner.edges) == 1

    def test_the_warning_names_the_loader_that_holds_the_detail(self, tmp_path):
        airports, routes = self._files(
            tmp_path, '"Nameless",US,US-CA,,37.62,-122.37,large_airport\n', ""
        )

        with pytest.warns(UserWarning, match="AirportLoader"):
            load_flight_planner(airports, routes)
