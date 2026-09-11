from flight_planner.core import Vertex
from flight_planner.core import Edge


class TestEdge:
    def test_source_target_weight(self):
        a, b = Vertex("A"), Vertex("B")
        edge = Edge(a, b, weight=2.5)
        assert edge.source == a
        assert edge.target == b
        assert edge.weight == 2.5

    def test_default_weight_is_one(self):
        edge = Edge(Vertex("A"), Vertex("B"))
        assert edge.weight == 1.0

    def test_equal_edges_are_equal(self):
        a, b = Vertex("A"), Vertex("B")
        assert Edge(a, b, weight=1.0) == Edge(a, b, weight=1.0)

    def test_different_weight_not_equal(self):
        a, b = Vertex("A"), Vertex("B")
        assert Edge(a, b, weight=1.0) != Edge(a, b, weight=2.0)

    def test_not_equal_to_other_types(self):
        assert Edge(Vertex("A"), Vertex("B")) != "edge"
