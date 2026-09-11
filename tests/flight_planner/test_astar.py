from flight_planner.core import Vertex
from flight_planner.core import Edge
from flight_planner.core import Graph
from flight_planner.pathfinding import Dijkstra, AStar


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


def _zero_heuristic(v, goal):
    return 0.0  # admissible; degenerates AStar to Dijkstra


class TestAStar:
    def test_matches_dijkstra_with_admissible_heuristic(self):
        graph, a, _, c, _ = _build_graph()

        dijkstra_distance, dijkstra_path = Dijkstra().find_path(graph, a, c)
        astar_distance, astar_path = AStar(_zero_heuristic).find_path(graph, a, c)

        assert astar_distance == dijkstra_distance
        assert [e.weight for e in astar_path] == [e.weight for e in dijkstra_path]

    def test_same_start_and_goal(self):
        graph, a, _, _, _ = _build_graph()
        assert AStar(_zero_heuristic).find_path(graph, a, a) == (0.0, [])

    def test_unreachable_goal(self):
        graph, a, _, _, d = _build_graph()
        assert AStar(_zero_heuristic).find_path(graph, a, d) == (float("inf"), [])
