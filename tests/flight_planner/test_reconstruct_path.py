"""The shared path reconstruction, including the case that used to hang.

`_reconstruct_path` is private and reached through all three algorithms, so it
had no test file of its own. It got one after a review found that violating
Dijkstra's documented non-negative-weight precondition made it spin forever
rather than raise -- and a search that hangs is much harder to diagnose than
one that fails.
"""

import math

import pytest

from flight_planner.core.edge import Edge
from flight_planner.core.graph import Graph
from flight_planner.core.vertex import Vertex
from flight_planner.pathfinding import AStar, Dijkstra
from flight_planner.pathfinding.strategy import _reconstruct_path


def vertices(*keys):
    """Return one `Vertex` per key.

    Args:
        *keys: Identity keys.

    Returns:
        Tuple of vertices.
    """
    return tuple(Vertex(key) for key in keys)


def test_returns_edges_in_travel_order():
    a, b, c = vertices("A", "B", "C")
    ab, bc = Edge(a, b, 1.0), Edge(b, c, 2.0)
    assert _reconstruct_path({b: ab, c: bc}, c) == [ab, bc]


def test_returns_empty_for_an_unreached_goal():
    a, b = vertices("A", "B")
    assert _reconstruct_path({}, b) == []
    assert _reconstruct_path({b: Edge(a, b, 1.0)}, a) == []


def test_a_negative_cycle_raises_rather_than_looping_forever():
    """The regression. A naive walk over this chain never terminates."""
    a, b, c = vertices("A", "B", "C")
    # B was reached from C and C from B: a chain with no start.
    predecessors = {b: Edge(c, b, -3.0), c: Edge(b, c, 1.0)}
    with pytest.raises(ValueError, match="revisits"):
        _reconstruct_path(predecessors, c)


def negative_cycle_graph():
    """Return the smallest graph whose search used to hang, and its endpoints.

    `A->B` 5, `B->C` 1, `C->B` -3, `C->D` 1. Relaxing the negative edge keeps
    lowering B's distance, so B's predecessor ends up pointing back into the
    cycle.

    Returns:
        `(graph, start, goal)`.
    """
    graph = Graph()
    a, b, c, d = vertices("A", "B", "C", "D")
    for edge in (Edge(a, b, 5.0), Edge(b, c, 1.0), Edge(c, b, -3.0), Edge(c, d, 1.0)):
        graph.add_edge(edge)
    return graph, a, d


@pytest.mark.parametrize(
    "algorithm",
    [Dijkstra(), AStar(lambda u, v: 0.0)],
    ids=["dijkstra", "astar"],
)
def test_a_negative_cycle_fails_loudly_through_a_real_search(algorithm):
    """Both heap-based searches raise instead of hanging.

    Neither algorithm supports negative weights -- that is a documented
    precondition, not a gap. The point is the failure mode: violating it now
    reports what is wrong with the graph.
    """
    graph, start, goal = negative_cycle_graph()
    with pytest.raises(ValueError, match="negative cycle"):
        graph.search(start, goal, algorithm)


@pytest.mark.parametrize(
    "algorithm",
    [Dijkstra(), AStar(lambda u, v: 0.0)],
    ids=["dijkstra", "astar"],
)
def test_zero_weight_cycles_and_self_loops_still_terminate(algorithm):
    """Zero is not negative, and the guard must not reject it.

    Zero-weight edges are the boundary of the precondition and are legal:
    relaxation is strictly-less-than, so a zero-weight edge never re-enters a
    settled vertex and the chain stays acyclic.
    """
    graph = Graph()
    chain = vertices(0, 1, 2, 3, 4, 5)
    for source, target in zip(chain, chain[1:]):
        graph.add_edge(Edge(source, target, 0.0))
    graph.add_edge(Edge(chain[2], chain[2], 0.0))  # self-loop
    graph.add_edge(Edge(chain[3], chain[1], 0.0))  # cycle back

    result = graph.search(chain[0], chain[-1], algorithm)
    assert result.cost == 0.0
    assert len(result.path) == 5
    assert math.isfinite(result.cost)
