import pytest

from airport import Airport
from route import Route
from flight_planner import FlightPlanner
from pathfinding import BFS


def _build_planner():
    planner = FlightPlanner()
    jfk = Airport("JFK")
    ord_ = Airport("ORD")
    lax = Airport("LAX")
    planner.add_edge(Route(jfk, lax, distance_km=3980.0, flight_number="DIRECT1"))
    planner.add_edge(Route(jfk, ord_, distance_km=1150.0, flight_number="LEG1"))
    planner.add_edge(Route(ord_, lax, distance_km=2800.0, flight_number="LEG2"))
    return planner, jfk, ord_, lax


class TestFlightPlanner:
    def test_default_algorithm_is_dijkstra(self):
        planner, _, _, _ = _build_planner()
        distance, legs = planner.find_shortest_route("JFK", "LAX")

        assert distance == 3950.0
        assert [leg.flight_number for leg in legs] == ["LEG1", "LEG2"]

    def test_accepts_iata_code_or_airport_instance(self):
        planner, jfk, _, lax = _build_planner()

        by_code = planner.find_shortest_route("JFK", "LAX")
        by_instance = planner.find_shortest_route(jfk, lax)

        assert by_code == by_instance

    def test_accepts_alternate_algorithm(self):
        planner, _, _, _ = _build_planner()
        hops, legs = planner.find_shortest_route("JFK", "LAX", algorithm=BFS())

        assert hops == 1.0
        assert [leg.flight_number for leg in legs] == ["DIRECT1"]

    def test_same_origin_and_destination(self):
        planner, _, _, _ = _build_planner()
        assert planner.find_shortest_route("JFK", "JFK") == (0.0, [])

    def test_unknown_iata_code_raises(self):
        planner, _, _, _ = _build_planner()
        with pytest.raises(ValueError):
            planner.find_shortest_route("JFK", "ZZZ")

    def test_airport_not_in_graph_raises(self):
        planner, _, _, _ = _build_planner()
        outsider = Airport("XXX")
        with pytest.raises(ValueError):
            planner.find_shortest_route("JFK", outsider)
