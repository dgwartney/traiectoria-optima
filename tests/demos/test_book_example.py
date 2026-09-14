"""The textbook network, asserted rather than printed.

`src/demos/book_example.py` transcribes the seven-airport flight network from
Goodrich, Tamassia and Goldwasser, *Data Structures and Algorithms in Python*
(Wiley) -- seven airports, eleven flights, the book's distances. It is the
project's "correctness on known small inputs" case: a graph small enough to
work by hand, whose answers do not depend on the cleaning pipeline, the
snapshot, or anything else this suite also tests.

As a demo it only printed. This file makes the same run an assertion, so a
regression in any of the three algorithms fails here before anyone reads a
console. Report §5.1 is the claim these tests back.
"""

import math

import pytest

from book_example import ARRIVAL, DEPARTURE, build_network
from flight_planner.geo import haversine_heuristic
from flight_planner.pathfinding import AStar, BFS, Dijkstra

#: BOS -> JFK -> DFW -> LAX, the weighted-shortest route and its total.
SHORTEST_LEGS = ("NW45", "AA1387", "DL335")
SHORTEST_KM = 4526.0

#: BOS -> MIA -> LAX, the fewest-stops route and what it costs in distance.
FEWEST_STOPS_LEGS = ("DL247", "AA523")
FEWEST_STOPS_KM = 5791.0


@pytest.fixture(scope="module")
def planner():
    return build_network()


def _legs(result):
    return tuple(leg.flight_number for leg in result.path)


class TestTheNetworkIsTheBooksNetwork:
    """Guard the transcription itself, before guarding what runs on it."""

    def test_seven_airports_and_eleven_flights(self, planner):
        assert len(planner.vertices) == 7
        assert len(planner.edges) == 11

    def test_sfo_is_a_sink(self, planner):
        """The book's figure gives SFO an arrival and no departure."""
        assert planner.get_outgoing_edges(planner.find_airport("SFO")) == []


class TestTheThreeAlgorithmsOnAKnownGraph:
    """BOS -> LAX, worked by hand off the book's figure."""

    def test_dijkstra_finds_the_shortest_route(self, planner):
        result = planner.search_route(DEPARTURE, ARRIVAL, Dijkstra())

        assert result.cost == pytest.approx(SHORTEST_KM)
        assert _legs(result) == SHORTEST_LEGS
        assert sum(leg.distance_km for leg in result.path) == pytest.approx(result.cost)

    def test_bfs_finds_the_fewest_stops_and_pays_for_them(self, planner):
        result = planner.search_route(DEPARTURE, ARRIVAL, BFS())

        assert result.cost == 2.0
        assert result.unit == "hops"
        assert _legs(result) == FEWEST_STOPS_LEGS
        assert sum(leg.distance_km for leg in result.path) == pytest.approx(
            FEWEST_STOPS_KM
        )

    def test_bfs_saves_a_stop_and_costs_1265_km(self, planner):
        """One fewer leg than Dijkstra, 1,265 km further. Report §4 and §5.1."""
        by_stops = planner.search_route(DEPARTURE, ARRIVAL, BFS())
        by_distance = planner.search_route(DEPARTURE, ARRIVAL, Dijkstra())

        assert len(by_stops.path) == len(by_distance.path) - 1
        assert sum(leg.distance_km for leg in by_stops.path) - by_distance.cost == (
            pytest.approx(1265.0)
        )

    def test_astar_agrees_with_dijkstra_exactly(self, planner):
        by_astar = planner.search_route(
            DEPARTURE, ARRIVAL, AStar(haversine_heuristic())
        )
        by_dijkstra = planner.search_route(DEPARTURE, ARRIVAL, Dijkstra())

        assert by_astar.cost == by_dijkstra.cost
        assert _legs(by_astar) == _legs(by_dijkstra)

    def test_the_books_airports_have_no_coordinates_so_the_heuristic_is_zero(
        self, planner
    ):
        """Why A* expands exactly what Dijkstra does here, rather than fewer.

        The book's figure carries no latitudes, so every `Airport` defaults to
        (0.0, 0.0) and the great-circle heuristic returns 0 for every pair. A
        zero heuristic is admissible and consistent -- A* is still correct --
        but it is uninformed, so A* degenerates to Dijkstra. The informed
        comparison needs real coordinates, which is report §7's job.
        """
        heuristic = haversine_heuristic()
        origin = planner.find_airport(DEPARTURE)

        assert all(heuristic(origin, v) == 0.0 for v in planner.vertices)

        by_astar = planner.search_route(DEPARTURE, ARRIVAL, AStar(heuristic))
        by_dijkstra = planner.search_route(DEPARTURE, ARRIVAL, Dijkstra())

        assert by_astar.nodes_expanded == by_dijkstra.nodes_expanded


class TestTheBooksGraphSuppliesItsOwnEdgeCases:
    """SFO's missing departures make the unreachable case a real one here."""

    @pytest.mark.parametrize(
        "algorithm",
        [Dijkstra(), BFS(), AStar(haversine_heuristic())],
        ids=["dijkstra", "bfs", "astar"],
    )
    def test_no_route_out_of_sfo(self, planner, algorithm):
        result = planner.search_route("SFO", "BOS", algorithm)

        assert math.isinf(result.cost)
        assert result.path == []
        assert not result.found

    @pytest.mark.parametrize(
        "algorithm",
        [Dijkstra(), BFS(), AStar(haversine_heuristic())],
        ids=["dijkstra", "bfs", "astar"],
    )
    def test_origin_equals_destination(self, planner, algorithm):
        result = planner.search_route(DEPARTURE, DEPARTURE, algorithm)

        assert result.cost == 0.0
        assert result.path == []
