"""Unit tests for `validation.engines` — NetworkX behind the Strategy.

The contract matters as much as the answers here. These engines exist so that
an experiment can take the engine as a parameter, which only works if a
NetworkX result is indistinguishable in *shape* from one of ours.
"""

import math

import pytest

from flight_planner.core import Edge, Graph, Vertex
from flight_planner.pathfinding import (
    AStar,
    BFS,
    Dijkstra,
    ExpansionTrace,
    PathfindingAlgorithm,
    SearchResult,
)
from validation.engines import NetworkXAStar, NetworkXBFS, NetworkXDijkstra


class TestNetworkXDijkstra:
    """The reference engine for `Dijkstra`."""

    def test_it_is_a_pathfinding_algorithm(self):
        assert isinstance(NetworkXDijkstra(), PathfindingAlgorithm)

    def test_it_agrees_with_our_dijkstra(self, diamond):
        graph, start, _, _, goal = diamond

        ours = Dijkstra().search(graph, start, goal)
        theirs = NetworkXDijkstra().search(graph, start, goal)

        assert theirs.cost == pytest.approx(ours.cost)
        assert theirs.cost == pytest.approx(2.5)

    def test_it_returns_our_edge_types_not_node_keys(self, diamond):
        graph, start, _, _, goal = diamond
        result = NetworkXDijkstra().search(graph, start, goal)

        assert all(isinstance(leg, Edge) for leg in result.path)
        assert [leg.source.key for leg in result.path] == ["S", "B", "A"]
        assert [leg.target.key for leg in result.path] == ["B", "A", "G"]

    def test_the_returned_path_sums_to_the_returned_cost(self, diamond):
        graph, start, _, _, goal = diamond
        result = NetworkXDijkstra().search(graph, start, goal)

        assert sum(leg.weight for leg in result.path) == pytest.approx(result.cost)

    def test_find_path_is_inherited_and_gives_the_two_value_view(self, diamond):
        # The adapter on the ABC. An engine implementing find_path instead of
        # search would not even instantiate.
        graph, start, _, _, goal = diamond
        cost, legs = NetworkXDijkstra().find_path(graph, start, goal)

        assert cost == pytest.approx(2.5)
        assert len(legs) == 3

    def test_a_start_equal_to_the_goal_costs_nothing(self, diamond):
        graph, start, *_ = diamond
        result = NetworkXDijkstra().search(graph, start, start)

        assert result.cost == pytest.approx(0.0)
        assert result.path == []
        assert result.found

    def test_an_unreachable_goal_is_infinite_and_not_found(self, disconnected):
        graph, inside, outside = disconnected
        result = NetworkXDijkstra().search(graph, inside, outside)

        assert math.isinf(result.cost)
        assert result.path == []
        assert not result.found

    def test_the_counters_are_zero_rather_than_invented(self, diamond):
        # NetworkX does not expose expansions. A plausible substitute would sit
        # in the same column as Dijkstra's measured count, in a table whose
        # whole purpose is comparing them.
        graph, start, _, _, goal = diamond
        result = NetworkXDijkstra().search(graph, start, goal)

        assert result.nodes_expanded == 0
        assert result.nodes_pushed == 0
        assert result.peak_frontier == 0

    def test_an_observer_is_accepted_and_never_notified(self, diamond):
        graph, start, _, _, goal = diamond
        trace = ExpansionTrace()

        result = NetworkXDijkstra().search(graph, start, goal, observer=trace)

        assert result.cost == pytest.approx(2.5)
        assert trace.expansions == []
        assert trace.pushes == []

    def test_it_picks_the_cheapest_of_several_parallel_edges(self, parallel_edges):
        graph, start, goal = parallel_edges
        result = NetworkXDijkstra().search(graph, start, goal)

        assert result.cost == pytest.approx(1.0)
        assert len(result.path) == 1
        assert result.path[0].weight == pytest.approx(1.0)

    def test_it_handles_a_cycle_and_a_self_loop(self, cyclic):
        graph, a, _, c = cyclic
        result = NetworkXDijkstra().search(graph, a, c)

        assert result.cost == pytest.approx(1.0)

    def test_a_single_vertex_graph_searched_to_itself(self):
        graph: Graph[Vertex, Edge] = Graph()
        only = Vertex("A")
        graph.add_vertex(only)

        assert NetworkXDijkstra().search(graph, only, only).cost == pytest.approx(0.0)

    def test_a_goal_absent_from_the_graph_is_unreachable_not_an_error(self, diamond):
        graph, start, *_ = diamond
        stranger = Vertex("Z")

        result = NetworkXDijkstra().search(graph, start, stranger)

        assert math.isinf(result.cost)

    def test_the_mirror_is_reused_across_searches_on_one_graph(self, diamond):
        graph, start, _, _, goal = diamond
        engine = NetworkXDijkstra()

        engine.search(graph, start, goal)
        first = engine._mirror
        engine.search(graph, start, goal)

        assert engine._mirror is first

    def test_a_different_graph_gets_its_own_mirror(self, diamond, parallel_edges):
        graph, start, _, _, goal = diamond
        other, other_start, other_goal = parallel_edges
        engine = NetworkXDijkstra()

        engine.search(graph, start, goal)
        first = engine._mirror
        engine.search(other, other_start, other_goal)

        assert engine._mirror is not first
        assert engine._mirror.mirrors(other)

    def test_one_engine_serves_many_planners(self, mini_planner):
        # The experiment loops engines outside pairs, so an engine instance
        # outlives any one graph.
        engine = NetworkXDijkstra()
        for origin, destination in (("SFO", "BOS"), ("SFO", "DEN")):
            cost, _ = mini_planner.find_shortest_route(origin, destination, engine)
            assert cost > 0


class TestNetworkXBFS:
    """The reference engine for `BFS`, whose cost is a hop count."""

    def test_it_agrees_with_our_bfs(self, diamond):
        graph, start, _, _, goal = diamond

        ours = BFS().search(graph, start, goal)
        theirs = NetworkXBFS().search(graph, start, goal)

        assert theirs.cost == pytest.approx(ours.cost)

    def test_its_cost_is_a_hop_count_not_a_distance(self, diamond):
        graph, start, _, _, goal = diamond

        hops = NetworkXBFS().search(graph, start, goal)
        distance = NetworkXDijkstra().search(graph, start, goal)

        # Two legs the expensive way, three legs the cheap way.
        assert hops.cost == pytest.approx(2.0)
        assert distance.cost == pytest.approx(2.5)
        assert len(hops.path) == 2

    def test_the_hop_count_equals_the_number_of_legs(self, diamond):
        graph, start, _, _, goal = diamond
        result = NetworkXBFS().search(graph, start, goal)

        assert result.cost == pytest.approx(float(len(result.path)))

    def test_an_unreachable_goal_is_infinite(self, disconnected):
        graph, inside, outside = disconnected

        assert math.isinf(NetworkXBFS().search(graph, inside, outside).cost)

    def test_a_start_equal_to_the_goal_costs_nothing(self, diamond):
        graph, start, *_ = diamond

        assert NetworkXBFS().search(graph, start, start).cost == pytest.approx(0.0)


class TestNetworkXAStar:
    """The reference engine for `AStar`, and the one that disagrees with it."""

    def test_it_agrees_with_our_astar_under_a_consistent_heuristic(self, mini_planner):
        # The great-circle heuristic on real coordinates is consistent, so the
        # two implementations must agree exactly.
        view_heuristic = (
            lambda origin, goal: origin.distance_to(goal)
        )  # noqa: E731
        for origin, destination in (("SFO", "BOS"), ("SFO", "ORD"), ("DEN", "BOS")):
            ours, _ = mini_planner.find_shortest_route(
                origin, destination, AStar(view_heuristic)
            )
            theirs, _ = mini_planner.find_shortest_route(
                origin, destination, NetworkXAStar(view_heuristic)
            )
            assert theirs == pytest.approx(ours), f"{origin}->{destination}"

    def test_it_stays_optimal_where_our_astar_does_not(
        self, diamond, inconsistent_scores
    ):
        # The defect, stated as a comparison. NetworkX reopens closed nodes;
        # AStar does not, so it reports 3.0 for a 2.5 route.
        graph, start, _, _, goal = diamond

        optimal = Dijkstra().search(graph, start, goal)
        ours = AStar(inconsistent_scores).search(graph, start, goal)
        theirs = NetworkXAStar(inconsistent_scores).search(graph, start, goal)

        assert optimal.cost == pytest.approx(2.5)
        assert theirs.cost == pytest.approx(2.5)
        assert ours.cost == pytest.approx(3.0)

    def test_the_heuristic_is_written_over_vertices_not_keys(self, diamond):
        # Callers hand the same object to AStar and to this engine; the
        # keys-to-vertices bridge is the engine's problem, not theirs.
        graph, start, _, _, goal = diamond
        seen = []

        def heuristic(vertex, goal_vertex):
            seen.append((vertex, goal_vertex))
            return 0.0

        NetworkXAStar(heuristic).search(graph, start, goal)

        assert seen, "the heuristic was never called"
        assert all(
            isinstance(vertex, Vertex) and isinstance(other, Vertex)
            for vertex, other in seen
        )

    def test_a_zero_heuristic_degenerates_to_dijkstra(self, diamond):
        graph, start, _, _, goal = diamond
        zero = NetworkXAStar(lambda vertex, goal_vertex: 0.0)

        assert zero.search(graph, start, goal).cost == pytest.approx(
            NetworkXDijkstra().search(graph, start, goal).cost
        )

    def test_an_unreachable_goal_is_infinite(self, disconnected):
        graph, inside, outside = disconnected
        engine = NetworkXAStar(lambda vertex, goal_vertex: 0.0)

        assert math.isinf(engine.search(graph, inside, outside).cost)

    def test_a_start_equal_to_the_goal_costs_nothing(self, diamond):
        graph, start, *_ = diamond
        engine = NetworkXAStar(lambda vertex, goal_vertex: 0.0)

        assert engine.search(graph, start, start).cost == pytest.approx(0.0)


class TestTheEnginesAreInterchangeableWithOurs:
    """The contract that makes 'engine as a parameter' work at all."""

    @pytest.mark.parametrize(
        "ours,theirs",
        [
            (Dijkstra(), NetworkXDijkstra()),
            (BFS(), NetworkXBFS()),
        ],
    )
    def test_both_return_a_search_result(self, ours, theirs, diamond):
        graph, start, _, _, goal = diamond

        assert isinstance(ours.search(graph, start, goal), SearchResult)
        assert isinstance(theirs.search(graph, start, goal), SearchResult)

    @pytest.mark.parametrize(
        "ours,theirs",
        [
            (Dijkstra(), NetworkXDijkstra()),
            (BFS(), NetworkXBFS()),
        ],
    )
    def test_they_agree_on_the_three_boundary_cases(self, ours, theirs, diamond):
        graph, start, _, _, goal = diamond
        stranger = Vertex("Z")

        for a, b in ((start, start), (start, goal), (start, stranger)):
            mine = ours.search(graph, a, b)
            yours = theirs.search(graph, a, b)
            assert mine.cost == pytest.approx(yours.cost) or (
                math.isinf(mine.cost) and math.isinf(yours.cost)
            )
            assert mine.found == yours.found

    def test_a_route_from_either_engine_carries_flight_numbers(self, mini_planner):
        # Downstream code reads route metadata off the legs; it must not care
        # which engine produced them.
        for engine in (Dijkstra(), NetworkXDijkstra()):
            _, legs = mini_planner.find_shortest_route("SFO", "BOS", engine)
            assert legs
            assert all(leg.flight_number for leg in legs)
            assert all(leg.airline for leg in legs)
