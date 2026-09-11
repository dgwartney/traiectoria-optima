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
    def test_loads_real_airports_file(self):
        loader = AirportLoader()
        airports = loader.load()

        assert loader.skipped == []
        assert len(airports) == 88
        assert all(isinstance(airport, Airport) for airport in airports)

    def test_known_airport_has_expected_fields(self):
        sfo = AirportLoader().load_by_iata()["SFO"]

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
    def test_loads_real_routes_file(self):
        airports = AirportLoader().load_by_iata()
        loader = RouteLoader(airports)
        routes = loader.load()

        assert loader.skipped == []
        assert len(routes) == 861
        assert all(isinstance(route, Route) for route in routes)

    def test_routes_reuse_the_supplied_airport_instances(self):
        airports = AirportLoader().load_by_iata()
        routes = RouteLoader(airports).load()

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
    def test_planner_is_populated_from_the_processed_files(self):
        planner = load_flight_planner()

        assert len(planner.vertices) == 88
        assert len(planner.edges) == 861
        assert planner.find_airport("ord") is not None

    def test_planner_finds_a_route_between_real_airports(self):
        planner = load_flight_planner()

        distance, legs = planner.find_shortest_route("SFO", "BOS")

        assert math.isfinite(distance)
        assert legs
        assert legs[0].origin.iata_code == "SFO"
        assert legs[-1].destination.iata_code == "BOS"
        assert distance == pytest.approx(sum(leg.distance_km for leg in legs))

    def test_planner_finds_a_multi_leg_route(self):
        planner = load_flight_planner()

        distance, legs = planner.find_shortest_route("PSP", "SYR")

        assert len(legs) > 1
        assert distance == pytest.approx(sum(leg.distance_km for leg in legs))
