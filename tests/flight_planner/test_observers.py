import pytest

from flight_planner.core import Edge, Graph, Vertex
from flight_planner.pathfinding import (
    AStar,
    BFS,
    Dijkstra,
    ExpansionTrace,
    SearchObserver,
)


class _CountingGraph(Graph):
    """Records which vertices had their outgoing edges requested.

    An independent measurement of expansion, so an algorithm's self-reported
    `nodes_expanded` can be checked against something other than itself.
    """

    def __init__(self):
        super().__init__()
        self.expanded = []

    def get_outgoing_edges(self, vertex):
        self.expanded.append(vertex)
        return super().get_outgoing_edges(vertex)


def _corridor(counting=False):
    """A straight run from 0 to 8, with a dead-end branch heading backwards.

    Every vertex sits at an integer position, and every edge costs 1, so
    `abs(position - goal position)` never overestimates the true remaining
    cost: an admissible heuristic.

    The branch is what separates the algorithms. Its vertices are *close to
    the start*, so Dijkstra expands them early, but *far from the goal*, so
    A* prices them out and never looks. This is the same shape as a real
    long-haul query, where Dijkstra fans out over nearby airports in the
    wrong direction.
    """
    graph = _CountingGraph() if counting else Graph()
    position = {}

    def vertex(index):
        node = Vertex(f"p{index}")
        position[node] = index
        return node

    corridor = [vertex(i) for i in range(9)]
    for left, right in zip(corridor, corridor[1:]):
        graph.add_edge(Edge(left, right, weight=1.0))

    branch = [vertex(-i) for i in range(1, 6)]
    graph.add_edge(Edge(corridor[0], branch[0], weight=1.0))
    for left, right in zip(branch, branch[1:]):
        graph.add_edge(Edge(left, right, weight=1.0))

    return graph, corridor[0], corridor[-1], position


def _by_position(position):
    """Distance along the line — admissible, since every edge costs 1."""

    def heuristic(a, b):
        return abs(position[a] - position[b])

    return heuristic


ALGORITHMS = [
    ("Dijkstra", lambda position: Dijkstra()),
    ("BFS", lambda position: BFS()),
    ("AStar", lambda position: AStar(_by_position(position))),
]


class TestReportedCountsAreTrue:
    """`nodes_expanded` is checked against an independent measurement."""

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_reported_expansions_match_the_graph_s_own_count(self, name, build):
        graph, start, goal, position = _corridor(counting=True)
        result = build(position).search(graph, start, goal)

        assert result.nodes_expanded == len(graph.expanded)

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_no_vertex_is_expanded_twice(self, name, build):
        graph, start, goal, position = _corridor(counting=True)
        build(position).search(graph, start, goal)

        assert len(graph.expanded) == len(set(graph.expanded))


class TestTheProjectsCentralClaim:
    """A* matches Dijkstra's answer while expanding fewer nodes."""

    def test_astar_expands_fewer_nodes_for_the_same_answer(self):
        graph, start, goal, position = _corridor()

        by_dijkstra = Dijkstra().search(graph, start, goal)
        by_astar = AStar(_by_position(position)).search(graph, start, goal)

        assert by_astar.cost == by_dijkstra.cost == 8.0
        assert by_astar.nodes_expanded < by_dijkstra.nodes_expanded

    def test_astar_never_enters_the_dead_end(self):
        graph, start, goal, position = _corridor()
        trace = ExpansionTrace()
        AStar(_by_position(position)).search(graph, start, goal, observer=trace)

        assert all(position[vertex] >= 0 for vertex in trace.order)

    def test_dijkstra_does_enter_the_dead_end(self):
        # The contrast is the point: uninformed search cannot tell that these
        # vertices lead away from the goal, because it never looks at the goal.
        graph, start, goal, position = _corridor()
        trace = ExpansionTrace()
        Dijkstra().search(graph, start, goal, observer=trace)

        assert any(position[vertex] < 0 for vertex in trace.order)

    def test_a_heuristic_cannot_help_when_every_route_is_equal(self):
        # Worth pinning down, because it bounds the claim. On a uniform grid
        # with edges only right and down, every route from corner to corner
        # costs the same, so g + h is identical for every vertex and A* has
        # nothing to discriminate on -- it expands exactly what Dijkstra does.
        graph = Graph()
        nodes = {(x, y): Vertex(f"{x},{y}") for x in range(3) for y in range(3)}
        for (x, y), node in nodes.items():
            for dx, dy in ((1, 0), (0, 1)):
                neighbour = nodes.get((x + dx, y + dy))
                if neighbour is not None:
                    graph.add_edge(Edge(node, neighbour, weight=1.0))
        coordinates = {node: key for key, node in nodes.items()}

        def manhattan(a, b):
            (ax, ay), (bx, by) = coordinates[a], coordinates[b]
            return abs(ax - bx) + abs(ay - by)

        start, goal = nodes[(0, 0)], nodes[(2, 2)]
        by_dijkstra = Dijkstra().search(graph, start, goal)
        by_astar = AStar(manhattan).search(graph, start, goal)

        assert by_astar.cost == by_dijkstra.cost
        assert by_astar.nodes_expanded == by_dijkstra.nodes_expanded


class TestSearchObserver:
    """The base class is a usable null observer."""

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_attaching_a_bare_observer_changes_nothing(self, name, build):
        graph, start, goal, position = _corridor()

        without = build(position).search(graph, start, goal)
        with_observer = build(position).search(
            graph, start, goal, observer=SearchObserver()
        )

        assert (with_observer.cost, with_observer.path) == (without.cost, without.path)
        assert with_observer.nodes_expanded == without.nodes_expanded

    def test_a_subclass_need_only_override_what_it_wants(self):
        class OnlyExpansions(SearchObserver):
            def __init__(self):
                self.seen = 0

            def on_expand(self, vertex, cost_so_far):
                self.seen += 1

        graph, start, goal, _ = _corridor()
        observer = OnlyExpansions()
        result = Dijkstra().search(graph, start, goal, observer=observer)

        assert observer.seen == result.nodes_expanded


class TestExpansionTrace:
    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_records_one_entry_per_expansion(self, name, build):
        graph, start, goal, position = _corridor()
        trace = ExpansionTrace()
        result = build(position).search(graph, start, goal, observer=trace)

        assert len(trace.expansions) == result.nodes_expanded

    @pytest.mark.parametrize("name,build", ALGORITHMS)
    def test_push_count_matches_the_reported_total(self, name, build):
        graph, start, goal, position = _corridor()
        trace = ExpansionTrace()
        result = build(position).search(graph, start, goal, observer=trace)

        assert len(trace.pushes) == result.nodes_pushed

    def test_expansions_are_in_expansion_order(self):
        graph, start, goal, _ = _corridor(counting=True)
        trace = ExpansionTrace()
        Dijkstra().search(graph, start, goal, observer=trace)

        assert trace.order == graph.expanded

    def test_dijkstra_expands_in_nondecreasing_cost_order(self):
        # The invariant that makes Dijkstra correct, observable for the first
        # time: each vertex is settled no earlier than a cheaper one.
        graph, start, goal, _ = _corridor()
        trace = ExpansionTrace()
        Dijkstra().search(graph, start, goal, observer=trace)

        costs = [cost for _, cost in trace.expansions]
        assert costs == sorted(costs)

    def test_bfs_reports_hop_depth_as_its_priority(self):
        # BFS has no priority queue, so it stands in its hop depth -- which
        # must still rise monotonically, since that is what FIFO order means.
        graph, start, goal, _ = _corridor()
        trace = ExpansionTrace()
        BFS().search(graph, start, goal, observer=trace)

        depths = [depth for _, depth in trace.expansions]
        assert depths == sorted(depths)
        assert depths[0] == 0.0

    def test_repr_reports_both_counts(self):
        graph, start, goal, _ = _corridor()
        trace = ExpansionTrace()
        result = Dijkstra().search(graph, start, goal, observer=trace)

        assert repr(trace) == (
            f"ExpansionTrace(expanded={result.nodes_expanded}, "
            f"pushed={result.nodes_pushed})"
        )
