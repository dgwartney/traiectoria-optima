from vertex import Vertex
from edge import Edge
from graph import Graph
from pathfinding.algorithms import PathfindingAlgorithm


class _StubAlgorithm(PathfindingAlgorithm):
    """Test double that records how it was called instead of pathfinding."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def find_path(self, graph, start, goal):
        self.calls.append((graph, start, goal))
        return self.result


class TestGraph:
    def test_add_vertex(self):
        graph = Graph()
        a = Vertex("A")
        graph.add_vertex(a)
        assert graph.vertices == [a]

    def test_add_edge_adds_both_vertices(self):
        graph = Graph()
        a, b = Vertex("A"), Vertex("B")
        graph.add_edge(Edge(a, b, weight=1.0))
        assert set(graph.vertices) == {a, b}
        assert len(graph.edges) == 1

    def test_get_outgoing_edges(self):
        graph = Graph()
        a, b, c = Vertex("A"), Vertex("B"), Vertex("C")
        edge_ab = Edge(a, b, weight=1.0)
        edge_ac = Edge(a, c, weight=2.0)
        graph.add_edge(edge_ab)
        graph.add_edge(edge_ac)

        assert graph.get_outgoing_edges(a) == [edge_ab, edge_ac]
        assert graph.get_outgoing_edges(b) == []

    def test_get_outgoing_edges_unknown_vertex_returns_empty(self):
        graph = Graph()
        assert graph.get_outgoing_edges(Vertex("Z")) == []

    def test_shortest_path_delegates_to_algorithm(self):
        graph = Graph()
        a, b = Vertex("A"), Vertex("B")
        expected = (5.0, [Edge(a, b, weight=5.0)])
        algorithm = _StubAlgorithm(expected)

        result = graph.shortest_path(a, b, algorithm)

        assert result == expected
        assert algorithm.calls == [(graph, a, b)]
