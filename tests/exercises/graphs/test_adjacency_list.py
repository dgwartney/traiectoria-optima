import math

from exercises.graphs.adjacency_list import Graph, Vertex


def test_vertex_starts_isolated_and_unvisited():
    vertex: Vertex = Vertex(1, label="origin")
    assert vertex.id == 1
    assert list(vertex.get_adjacent()) == []
    assert vertex.distance == math.inf
    assert vertex.visited is False
    assert vertex.previous is None


def test_add_adjacent_records_weight_and_overwrites_on_repeat():
    a, b = Vertex("a"), Vertex("b")
    a.add_adjacent(b, 4)
    assert list(a.get_adjacent()) == [b]
    assert a.get_weight(b) == 4
    a.add_adjacent(b, 9)
    assert a.get_weight(b) == 9
    assert len(list(a.get_adjacent())) == 1


def test_add_edge_is_undirected_and_creates_missing_vertices():
    graph = Graph()
    graph.add_edge("a", "b", 4)
    assert sorted(graph.get_vertices()) == ["a", "b"]
    assert graph["a"].get_weight(graph["b"]) == 4
    assert graph["b"].get_weight(graph["a"]) == 4


def test_get_edges_reports_each_undirected_edge_twice():
    graph = Graph()
    graph.add_edge("a", "b", 4)
    graph.add_edge("a", "c", 1)
    assert len(graph) == 3
    assert sorted(graph.get_edges()) == [
        ("a", "b", 4),
        ("a", "c", 1),
        ("b", "a", 4),
        ("c", "a", 1),
    ]


def test_subscript_assignment_adds_a_vertex_and_ignores_the_value():
    graph = Graph()
    graph["a"] = "ignored"
    assert list(graph.get_vertices()) == ["a"]
    assert graph["a"].id == "a"


def test_lookup_of_an_unknown_key_returns_none():
    assert Graph()["missing"] is None
