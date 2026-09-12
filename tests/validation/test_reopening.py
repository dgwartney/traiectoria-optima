"""Unit tests for `validation.reopening.ReopeningAStar`.

Two jobs. First, that it is a faithful drop-in for `AStar` everywhere the two
should agree — which is everywhere the heuristic is consistent, including all
of this project's real data. Second, that it differs exactly where it is
supposed to, and that the difference is the one the report will describe.
"""

import math

import pytest

from flight_planner.core import Edge, Graph, Vertex
from flight_planner.pathfinding import (
    AStar,
    Dijkstra,
    ExpansionTrace,
    PathfindingAlgorithm,
    SearchObserver,
)
from validation.reopening import ReopeningAStar


class _CountingObserver(SearchObserver):
    """Records how many times each hook fired."""

    def __init__(self):
        self.expansions = 0
        self.pushes = 0

    def on_expand(self, vertex, cost_so_far):
        self.expansions += 1

    def on_push(self, vertex, priority):
        self.pushes += 1


class TestReopeningAStar:
    """A* without a closed set."""

    def test_it_is_a_pathfinding_algorithm(self):
        assert isinstance(ReopeningAStar(lambda v, g: 0.0), PathfindingAlgorithm)

    def test_it_returns_the_optimum_under_an_inconsistent_heuristic(
        self, diamond, inconsistent_scores
    ):
        # The whole reason this class exists.
        graph, start, _, _, goal = diamond

        assert ReopeningAStar(inconsistent_scores).search(
            graph, start, goal
        ).cost == pytest.approx(2.5)

    def test_the_shipped_astar_does_not(self, diamond, inconsistent_scores):
        # Pins the defect. If this starts failing, `astar.py` was patched and
        # this whole module has done its job and can move into the package.
        graph, start, _, _, goal = diamond

        assert AStar(inconsistent_scores).search(
            graph, start, goal
        ).cost == pytest.approx(3.0)

    def test_the_shipped_astar_reports_a_cost_its_own_path_contradicts(
        self, diamond, inconsistent_scores
    ):
        # The second, worse half of the defect: 3.0 beside an itinerary that
        # adds to 2.5. Harder to defend in a report than a re-expansion is.
        graph, start, _, _, goal = diamond
        result = AStar(inconsistent_scores).search(graph, start, goal)

        assert result.cost == pytest.approx(3.0)
        assert sum(leg.weight for leg in result.path) == pytest.approx(2.5)

    def test_its_own_cost_always_describes_its_own_path(
        self, diamond, inconsistent_scores
    ):
        graph, start, _, _, goal = diamond
        result = ReopeningAStar(inconsistent_scores).search(graph, start, goal)

        assert sum(leg.weight for leg in result.path) == pytest.approx(result.cost)

    def test_it_agrees_with_dijkstra_under_a_zero_heuristic(self, diamond):
        graph, start, _, _, goal = diamond

        assert ReopeningAStar(lambda v, g: 0.0).search(
            graph, start, goal
        ).cost == pytest.approx(Dijkstra().search(graph, start, goal).cost)

    def test_it_agrees_with_the_shipped_astar_when_the_heuristic_is_consistent(
        self, mini_planner
    ):
        # Great-circle distance on real coordinates is consistent, so the two
        # must be indistinguishable -- costs *and* counters.
        heuristic = lambda origin, goal: origin.distance_to(goal)  # noqa: E731
        for origin, destination in (("SFO", "BOS"), ("SFO", "ORD"), ("DEN", "BOS")):
            shipped = mini_planner.search_route(
                origin, destination, AStar(heuristic)
            )
            fixed = mini_planner.search_route(
                origin, destination, ReopeningAStar(heuristic)
            )
            assert fixed.cost == pytest.approx(shipped.cost)
            assert fixed.nodes_expanded == shipped.nodes_expanded
            assert fixed.peak_frontier == shipped.peak_frontier

    def test_a_consistent_heuristic_never_triggers_a_re_expansion(self, mini_planner):
        # Why no committed number moves if the patch is taken.
        heuristic = lambda origin, goal: origin.distance_to(goal)  # noqa: E731
        trace = ExpansionTrace()

        mini_planner.search_route(
            "SFO", "BOS", ReopeningAStar(heuristic), observer=trace
        )

        assert len(trace.order) == len(set(trace.order))

    def test_an_inconsistent_heuristic_does_trigger_one(
        self, diamond, inconsistent_scores
    ):
        graph, start, _, _, goal = diamond
        trace = ExpansionTrace()

        result = ReopeningAStar(inconsistent_scores).search(
            graph, start, goal, observer=trace
        )

        assert len(trace.order) > len(set(trace.order))
        assert result.nodes_expanded == len(trace.order)

    def test_the_expansion_counter_is_explicit_not_a_set_size(
        self, diamond, inconsistent_scores
    ):
        # `AStar` reports len(visited); dropping the closed set deletes the
        # set that counter counted, so re-expansions must still be counted.
        graph, start, _, _, goal = diamond
        result = ReopeningAStar(inconsistent_scores).search(graph, start, goal)

        assert result.nodes_expanded > 0
        assert result.nodes_expanded >= len({"S", "B", "A"})

    def test_observation_does_not_change_the_result(
        self, diamond, inconsistent_scores
    ):
        graph, start, _, _, goal = diamond
        engine = ReopeningAStar(inconsistent_scores)

        without = engine.search(graph, start, goal)
        with_observer = engine.search(graph, start, goal, observer=ExpansionTrace())

        assert with_observer.cost == pytest.approx(without.cost)
        assert with_observer.nodes_expanded == without.nodes_expanded
        assert with_observer.nodes_pushed == without.nodes_pushed

    def test_the_observer_call_counts_match_the_counters(
        self, diamond, inconsistent_scores
    ):
        graph, start, _, _, goal = diamond
        counter = _CountingObserver()

        result = ReopeningAStar(inconsistent_scores).search(
            graph, start, goal, observer=counter
        )

        assert counter.expansions == result.nodes_expanded
        assert counter.pushes == result.nodes_pushed

    def test_a_start_equal_to_the_goal_costs_nothing_and_counts_nothing(self, diamond):
        graph, start, *_ = diamond
        result = ReopeningAStar(lambda v, g: 0.0).search(graph, start, start)

        assert result.cost == pytest.approx(0.0)
        assert result.path == []
        assert result.nodes_expanded == 0
        assert result.nodes_pushed == 0

    def test_an_unreachable_goal_is_infinite_but_keeps_the_real_counters(
        self, disconnected
    ):
        graph, inside, outside = disconnected
        result = ReopeningAStar(lambda v, g: 0.0).search(graph, inside, outside)

        assert math.isinf(result.cost)
        assert result.path == []
        assert not result.found
        # Exhausting the reachable component is real work and is reported.
        assert result.nodes_expanded > 0

    def test_an_empty_graph_yields_no_route(self):
        graph: Graph[Vertex, Edge] = Graph()
        a, b = Vertex("A"), Vertex("B")
        graph.add_vertex(a)
        graph.add_vertex(b)

        assert math.isinf(ReopeningAStar(lambda v, g: 0.0).search(graph, a, b).cost)

    def test_a_cycle_and_a_self_loop_do_not_make_it_loop(self, cyclic):
        graph, a, _, c = cyclic

        assert ReopeningAStar(lambda v, g: 0.0).search(graph, a, c).cost == (
            pytest.approx(1.0)
        )

    def test_zero_weight_edges_do_not_cause_endless_re_expansion(self, cyclic):
        # `>=` in the staleness guard, not `>`: an equal g-score must not
        # count as an improvement, or a zero-weight cycle never terminates.
        graph, a, b, _ = cyclic
        result = ReopeningAStar(lambda v, g: 0.0).search(graph, a, b)

        assert result.cost == pytest.approx(1.0)
        assert result.nodes_expanded <= len(graph.vertices) * 2

    def test_parallel_edges_take_the_cheapest(self, parallel_edges):
        graph, start, goal = parallel_edges

        assert ReopeningAStar(lambda v, g: 0.0).search(
            graph, start, goal
        ).cost == pytest.approx(1.0)

    def test_find_path_is_inherited(self, diamond, inconsistent_scores):
        graph, start, _, _, goal = diamond
        cost, legs = ReopeningAStar(inconsistent_scores).find_path(graph, start, goal)

        assert cost == pytest.approx(2.5)
        assert sum(leg.weight for leg in legs) == pytest.approx(cost)
