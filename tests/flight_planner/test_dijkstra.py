import ast
import inspect

from flight_planner.core import Vertex
from flight_planner.core import Edge
from flight_planner.core import Graph
from flight_planner.pathfinding import Dijkstra


def _build_graph():
    graph = Graph()
    a, b, c, d = Vertex("A"), Vertex("B"), Vertex("C"), Vertex("D")
    edge_ab = Edge(a, b, weight=1.0)
    edge_ac = Edge(a, c, weight=4.0)
    edge_bc = Edge(b, c, weight=1.0)
    graph.add_edge(edge_ab)
    graph.add_edge(edge_ac)
    graph.add_edge(edge_bc)
    graph.add_vertex(d)  # unreachable from A
    return graph, a, b, c, d


class TestDijkstra:
    def test_prefers_lower_weight_multi_hop_path(self):
        graph, a, _, c, _ = _build_graph()
        distance, path = Dijkstra().find_path(graph, a, c)

        assert distance == 2.0
        assert [edge.weight for edge in path] == [1.0, 1.0]

    def test_same_start_and_goal(self):
        graph, a, _, _, _ = _build_graph()
        assert Dijkstra().find_path(graph, a, a) == (0.0, [])

    def test_unreachable_goal(self):
        graph, a, _, _, d = _build_graph()
        assert Dijkstra().find_path(graph, a, d) == (float("inf"), [])


class _CountingGraph(Graph):
    """A graph that records how often each vertex's edges are requested.

    Expanding a vertex means asking for its outgoing edges, so these counts
    are the search's expansion record.
    """

    def __init__(self):
        super().__init__()
        self.expansions = []

    def get_outgoing_edges(self, vertex):
        self.expansions.append(vertex)
        return super().get_outgoing_edges(vertex)


class TestRunsOnOurOwnHeap:
    """T3/T6: Dijkstra must consume the from-scratch heap, not `heapq`."""

    def test_module_imports_minheap_and_not_heapq(self):
        import flight_planner.pathfinding.algorithms as module

        tree = ast.parse(inspect.getsource(module))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.update(alias.name for alias in node.names)

        assert "heapq" not in imported
        assert "MinHeap" in imported


class TestExpansionDiscipline:
    """The queue holds superseded entries; the search must not act on them."""

    def test_expands_each_vertex_at_most_once(self):
        # C is queued at 4.0 via A->C, then again at 2.0 via A->B->C. The
        # stale entry is still in the queue when the better one is popped.
        graph = _CountingGraph()
        a, b, c, d = Vertex("A"), Vertex("B"), Vertex("C"), Vertex("D")
        graph.add_edge(Edge(a, b, weight=1.0))
        graph.add_edge(Edge(a, c, weight=4.0))
        graph.add_edge(Edge(b, c, weight=1.0))
        graph.add_edge(Edge(c, d, weight=1.0))

        Dijkstra().find_path(graph, a, d)

        assert len(graph.expansions) == len(set(graph.expansions))

    def test_superseded_entry_does_not_corrupt_the_distance(self):
        graph = _CountingGraph()
        a, b, c, d = Vertex("A"), Vertex("B"), Vertex("C"), Vertex("D")
        graph.add_edge(Edge(a, b, weight=1.0))
        graph.add_edge(Edge(a, c, weight=4.0))
        graph.add_edge(Edge(b, c, weight=1.0))
        graph.add_edge(Edge(c, d, weight=1.0))

        distance, path = Dijkstra().find_path(graph, a, d)

        assert distance == 3.0
        assert [edge.weight for edge in path] == [1.0, 1.0, 1.0]

    def test_equal_cost_paths_resolve_to_the_first_one_found(self):
        # Both routes to D cost 2.0. The heap's FIFO tie-break makes the
        # outcome deterministic rather than dependent on object identity.
        graph = Graph()
        a, b, c, d = Vertex("A"), Vertex("B"), Vertex("C"), Vertex("D")
        graph.add_edge(Edge(a, b, weight=1.0))
        graph.add_edge(Edge(a, c, weight=1.0))
        graph.add_edge(Edge(b, d, weight=1.0))
        graph.add_edge(Edge(c, d, weight=1.0))

        distance, path = Dijkstra().find_path(graph, a, d)

        assert distance == 2.0
        assert path[0].target == b

    def test_finds_the_goal_across_a_long_chain(self):
        # Deep enough that the heap sifts repeatedly during the search.
        graph = Graph()
        chain = [Vertex(f"V{i}") for i in range(60)]
        for left, right in zip(chain, chain[1:]):
            graph.add_edge(Edge(left, right, weight=1.0))

        distance, path = Dijkstra().find_path(graph, chain[0], chain[-1])

        assert distance == 59.0
        assert len(path) == 59
