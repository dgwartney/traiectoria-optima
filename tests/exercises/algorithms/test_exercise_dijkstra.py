import unittest

from exercises.algorithms.dijkstra.dijkstra import dijkstra


class TestDijkstraAlgorithm(unittest.TestCase):

    def setUp(self):
        """Define standard test graphs used across multiple test cases."""
        # Standard graph with multiple paths
        self.standard_graph = {
            "A": {"B": 4, "C": 2},
            "B": {"C": 1, "D": 5},
            "C": {"B": 1, "D": 8, "E": 10},
            "D": {"E": 2},
            "E": {},
        }

        # Disconnected graph (No path from A to E)
        self.disconnected_graph = {
            "A": {"B": 2},
            "B": {"C": 3},
            "C": {},
            "D": {"E": 1},
            "E": {},
        }

        # Graph with cyclic paths
        self.cyclic_graph = {
            "A": {"B": 1},
            "B": {"C": 2, "A": 4},
            "C": {"D": 1, "B": 1},
            "D": {},
        }

    def test_standard_shortest_path(self):
        """Test if the algorithm finds the optimal path when multiple options exist."""
        path, cost = dijkstra(self.standard_graph, "A", "E")
        self.assertEqual(path, ["A", "C", "B", "D", "E"])
        self.assertEqual(cost, 10)

    def test_start_is_target(self):
        """Test behavior when the start node is the target node."""
        path, cost = dijkstra(self.standard_graph, "A", "A")
        self.assertEqual(path, ["A"])
        self.assertEqual(cost, 0)

    def test_disconnected_graph(self):
        """Test that the algorithm safely handles completely unreachable target nodes."""
        path, cost = dijkstra(self.disconnected_graph, "A", "E")
        self.assertIsNone(path)
        self.assertEqual(cost, float("inf"))

    def test_graph_with_cycles(self):
        """Test that loops back to earlier nodes do not cause infinite iterations."""
        path, cost = dijkstra(self.cyclic_graph, "A", "D")
        self.assertEqual(path, ["A", "B", "C", "D"])
        self.assertEqual(cost, 4)

    def test_self_loops(self):
        """Test that nodes pointing to themselves are cleanly ignored."""
        loop_graph = {"A": {"A": 5, "B": 2}, "B": {}}
        path, cost = dijkstra(loop_graph, "A", "B")
        self.assertEqual(path, ["A", "B"])
        self.assertEqual(cost, 2)


if __name__ == "__main__":
    unittest.main()
