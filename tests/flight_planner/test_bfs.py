from flight_planner.core import Vertex
from flight_planner.core import Edge
from flight_planner.core import Graph
from flight_planner.pathfinding import BFS


def _build_graph():
    graph = Graph()
    a, b, c, d = Vertex("A"), Vertex("B"), Vertex("C"), Vertex("D")
    edge_ab = Edge(a, b, weight=1.0)
    edge_ac = Edge(a, c, weight=4.0)  # direct, heavier, but fewer hops
    edge_bc = Edge(b, c, weight=1.0)
    graph.add_edge(edge_ab)
    graph.add_edge(edge_ac)
    graph.add_edge(edge_bc)
    graph.add_vertex(d)  # unreachable from A
    return graph, a, b, c, d


class TestBFS:
    def test_prefers_fewer_hops_over_lower_weight(self):
        graph, a, _, c, _ = _build_graph()
        hops, path = BFS().find_path(graph, a, c)

        assert hops == 1.0
        assert [edge.weight for edge in path] == [4.0]  # the heavier direct edge

    def test_same_start_and_goal(self):
        graph, a, _, _, _ = _build_graph()
        assert BFS().find_path(graph, a, a) == (0.0, [])

    def test_unreachable_goal(self):
        graph, a, _, _, d = _build_graph()
        assert BFS().find_path(graph, a, d) == (float("inf"), [])
