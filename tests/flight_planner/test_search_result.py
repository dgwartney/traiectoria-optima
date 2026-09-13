import math

import pytest

from flight_planner.core import Edge, Graph, Vertex
from flight_planner.flights import Airport, FlightPlanner, Route
from flight_planner.pathfinding import (
    COST_HOPS,
    COST_WEIGHT,
    AStar,
    BFS,
    Dijkstra,
    SearchResult,
)


def _diamond():
    """A -> B -> C, plus the longer direct A -> C, and an orphan D.

    C is reached first at 4.0 via the direct edge, then at 2.0 via B, so the
    queue is guaranteed to hold a superseded entry by the time C is settled.
    """
    graph = Graph()
    a, b, c, d = Vertex("A"), Vertex("B"), Vertex("C"), Vertex("D")
    graph.add_edge(Edge(a, b, weight=1.0))
    graph.add_edge(Edge(a, c, weight=4.0))
    graph.add_edge(Edge(b, c, weight=1.0))
    graph.add_vertex(d)  # unreachable from A
    return graph, a, b, c, d


def _zero_heuristic(_from, _to):
    return 0.0


ALGORITHMS = [
    ("Dijkstra", lambda: Dijkstra()),
    ("BFS", lambda: BFS()),
    ("AStar", lambda: AStar(_zero_heuristic)),
]


class TestSearchResult:
    """Every algorithm reports what the search cost, not just its answer."""

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_search_returns_a_search_result(self, name, build):
        graph, a, _, c, _ = _diamond()
        result = build().search(graph, a, c)

        assert isinstance(result, SearchResult)

    def test_dijkstra_reports_the_route_and_what_it_cost_to_find(self):
        graph, a, _, c, _ = _diamond()
        result = Dijkstra().search(graph, a, c)

        assert result.cost == 2.0
        assert [edge.weight for edge in result.path] == [1.0, 1.0]
        # A and B are expanded; C is the goal and breaks before expanding.
        assert result.nodes_expanded == 2

    def test_bfs_reports_hops_not_distance(self):
        graph, a, _, c, _ = _diamond()
        result = BFS().search(graph, a, c)

        assert result.cost == 1.0  # one hop, via the direct 4.0 km edge
        # A is expanded, queueing B and C; B is expanded next; C is the goal
        # and breaks before expanding. BFS ignores that C was already reachable
        # in one hop -- it still drains the queue ahead of it.
        assert result.nodes_expanded == 2

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_find_path_still_returns_the_plain_tuple(self, name, build):
        """The contract ~20 call sites and two committed experiments rely on."""
        graph, a, _, c, _ = _diamond()
        algorithm = build()

        tuple_form = algorithm.find_path(graph, a, c)
        result = algorithm.search(graph, a, c)

        assert isinstance(tuple_form, tuple)
        assert len(tuple_form) == 2
        assert tuple_form == (result.cost, result.path)


class TestEarlyReturns:
    """The two paths that never run a full search, and what they report."""

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_start_equals_goal_reports_no_work(self, name, build):
        graph, a, _, _, _ = _diamond()
        result = build().search(graph, a, a)

        assert (result.cost, result.path) == (0.0, [])
        assert result.nodes_expanded == 0
        assert result.nodes_pushed == 0
        assert result.peak_frontier == 0

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_unreachable_goal_still_reports_the_work_it_did(self, name, build):
        # The search exhausts the reachable component before giving up, and
        # that is the most expensive kind of query the benchmark will see.
        # Zeroing the counters alongside the infinite cost would hide it.
        graph, a, _, _, d = _diamond()
        result = build().search(graph, a, d)

        assert result.cost == math.inf
        assert result.path == []
        assert result.nodes_expanded == 3  # A, B and C all expanded
        assert result.nodes_pushed >= result.nodes_expanded


class TestCounterInvariants:
    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_never_expands_more_than_it_queued(self, name, build):
        graph, a, _, c, _ = _diamond()
        result = build().search(graph, a, c)

        assert result.nodes_expanded <= result.nodes_pushed

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_peak_frontier_is_positive_when_a_search_ran(self, name, build):
        graph, a, _, c, _ = _diamond()
        result = build().search(graph, a, c)

        assert result.peak_frontier >= 1
        assert result.peak_frontier <= result.nodes_pushed


class TestCostUnit:
    """A result must say what its cost counts, on every path out of a search.

    `cost` means kilometres for Dijkstra and A* and a hop count for BFS. Before
    `unit` existed, a caller holding a `SearchResult` had no way to ask, and
    `search_instrumentation_example.py` recovered it by string-matching the
    algorithm's display name.
    """

    EXPECTED = {"Dijkstra": COST_WEIGHT, "BFS": COST_HOPS, "AStar": COST_WEIGHT}

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_declared_on_the_algorithm(self, name, build):
        assert build().unit == self.EXPECTED[name]

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_reported_on_a_found_route(self, name, build):
        graph, a, _, c, _ = _diamond()

        assert build().search(graph, a, c).unit == self.EXPECTED[name]

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_reported_when_start_equals_goal(self, name, build):
        # An unlabelled 0.0 is the same trap as an unlabelled 4341.02.
        graph, a, _, _, _ = _diamond()

        assert build().search(graph, a, a).unit == self.EXPECTED[name]

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_reported_when_the_goal_is_unreachable(self, name, build):
        graph, a, _, _, d = _diamond()
        result = build().search(graph, a, d)

        assert result.cost == math.inf
        assert result.unit == self.EXPECTED[name]

    def test_bfs_and_dijkstra_disagree_on_the_unit_of_the_same_query(self):
        """The reason the field exists, stated as a test."""
        graph, a, _, c, _ = _diamond()
        hops = BFS().search(graph, a, c)
        kilometres = Dijkstra().search(graph, a, c)

        assert hops.unit != kilometres.unit
        assert hops.cost != kilometres.cost

    def test_defaults_to_empty_for_a_hand_built_result(self):
        assert SearchResult(1.0).unit == ""


class TestSearchRouteReportsTheUnit:
    """`FlightPlanner.search_route` has its own start == goal shortcut."""

    @staticmethod
    def _planner():
        planner = FlightPlanner()
        sfo = Airport("SFO", latitude=37.6213, longitude=-122.3790)
        bos = Airport("BOS", latitude=42.3620, longitude=-71.0079)
        planner.add_edge(Route(sfo, bos, distance_km=4341.0))
        return planner

    @pytest.mark.parametrize(
        "algorithm,expected",
        [
            (None, COST_WEIGHT),  # defaults to Dijkstra
            (Dijkstra(), COST_WEIGHT),
            (BFS(), COST_HOPS),
            (AStar(_zero_heuristic), COST_WEIGHT),
        ],
    )
    def test_unit_survives_a_query(self, algorithm, expected):
        assert self._planner().search_route("SFO", "BOS", algorithm).unit == expected

    @pytest.mark.parametrize(
        "algorithm,expected",
        [(None, COST_WEIGHT), (BFS(), COST_HOPS), (Dijkstra(), COST_WEIGHT)],
    )
    def test_unit_survives_a_self_query(self, algorithm, expected):
        # search_route short-circuits before any algorithm runs, so it has to
        # read the unit off the algorithm rather than off a result.
        assert self._planner().search_route("SFO", "SFO", algorithm).unit == expected
