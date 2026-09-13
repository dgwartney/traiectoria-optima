"""Small hand-built graphs the validation tests share.

Every fixture here is small enough to reason about by hand, which is the point:
a parity test that only ever runs on 7,005 real routes can tell you the two
libraries disagree, but not why. These say why.
"""

import pytest

from flight_planner.core import Edge, Graph, Vertex
from flight_planner.flights import Airport, FlightPlanner, Route


@pytest.fixture
def diamond():
    """Return a four-vertex graph with two routes to the goal.

    ```
    S --2.0--> A --1.0--> G
     \\                   /
      1.0--> B --0.5--> A
    ```

    The cheapest route is `S -> B -> A -> G` at 2.5, while the direct
    `S -> A -> G` costs 3.0. A* under an admissible-but-inconsistent
    heuristic pops `A` early with the dearer route and, if it closes `A`,
    never propagates the improvement. This is the smallest graph that
    exposes it.

    Returns:
        `(graph, start, a, b, goal)`.
    """
    graph: Graph[Vertex, Edge] = Graph()
    start, a, b, goal = Vertex("S"), Vertex("A"), Vertex("B"), Vertex("G")
    for edge in (
        Edge(start, a, 2.0),
        Edge(start, b, 1.0),
        Edge(b, a, 0.5),
        Edge(a, goal, 1.0),
    ):
        graph.add_edge(edge)
    return graph, start, a, b, goal


@pytest.fixture
def inconsistent_scores():
    """Return an admissible, inconsistent heuristic for `diamond`.

    True remaining cost to `G`: `S=2.5`, `B=1.5`, `A=1.0`, `G=0`. Nothing
    below overestimates, so it is admissible. It is not consistent:
    `h(S)=0` but `h(B)=1.5` across an edge of weight 1.0, which violates
    `h(S) <= w(S, B) + h(B)`.

    Returns:
        Callable over `(vertex, goal)`, as `AStar` expects.
    """
    scores = {"S": 0.0, "B": 1.5, "A": 0.0, "G": 0.0}

    def heuristic(vertex, _goal):
        return scores[vertex.key]

    return heuristic


@pytest.fixture
def parallel_edges():
    """Return two vertices joined by three routes of different weights.

    A `DiGraph` would keep one of the three. The mirror must keep all of
    them, and a shortest path must still choose the cheapest.

    Returns:
        `(graph, start, goal)`.
    """
    graph: Graph[Vertex, Edge] = Graph()
    start, goal = Vertex("X"), Vertex("Y")
    for weight in (5.0, 1.0, 3.0):
        graph.add_edge(Edge(start, goal, weight))
    return graph, start, goal


@pytest.fixture
def disconnected():
    """Return a graph in two components with no edge between them.

    Returns:
        `(graph, inside, outside)`, where `outside` is unreachable from
        `inside`.
    """
    graph: Graph[Vertex, Edge] = Graph()
    inside, middle, outside = Vertex("I"), Vertex("M"), Vertex("O")
    graph.add_edge(Edge(inside, middle, 1.0))
    graph.add_vertex(outside)
    return graph, inside, outside


@pytest.fixture
def cyclic():
    """Return a three-cycle, plus a self-loop and a zero-weight edge.

    The real data contains exactly one self-loop (`PKN -> PKN`), which is
    also its only zero-weight edge, so a harness has to expect both rather
    than assert them away.

    Returns:
        `(graph, a, b, c)` with edges `a->b->c->a`, `a->a`, and `b->c` at
        zero cost.
    """
    graph: Graph[Vertex, Edge] = Graph()
    a, b, c = Vertex("A"), Vertex("B"), Vertex("C")
    for edge in (
        Edge(a, b, 1.0),
        Edge(b, c, 2.0),
        Edge(c, a, 3.0),
        Edge(a, a, 0.0),
        Edge(b, c, 0.0),
    ):
        graph.add_edge(edge)
    return graph, a, b, c


@pytest.fixture
def mini_planner():
    """Return a four-airport planner with real coordinates.

    Coordinates are the published ones, so the great-circle heuristic is
    meaningful rather than arbitrary and the admissibility argument can be
    checked on this fixture too.

    Returns:
        The planner. Routes carry airlines and flight numbers, including two
        parallel SFO->DEN legs.
    """
    sfo = Airport("SFO", "San Francisco", latitude=37.6189, longitude=-122.375)
    den = Airport("DEN", "Denver", latitude=39.8617, longitude=-104.673)
    ord_ = Airport("ORD", "Chicago O'Hare", latitude=41.9786, longitude=-87.9048)
    bos = Airport("BOS", "Boston Logan", latitude=42.3643, longitude=-71.0052)

    # Weights are the great-circle distances between those coordinates, not
    # invented round numbers. A fabricated distance shorter than the great
    # circle it spans makes the heuristic inadmissible on the fixture, which
    # is a property of the fixture rather than of the code under test -- and
    # the admissibility test here caught exactly that on the first run.
    def leg(origin, destination, offset=0.0):
        return origin.distance_to(destination) + offset

    planner = FlightPlanner()
    for route in (
        Route(sfo, den, leg(sfo, den), "UA", "UA0001"),
        # A dearer parallel leg, so "the cheapest of several" is testable.
        Route(sfo, den, leg(sfo, den, 2.0), "WN", "WN0002"),
        Route(den, ord_, leg(den, ord_), "UA", "UA0003"),
        Route(ord_, bos, leg(ord_, bos), "AA", "AA0004"),
        # Direct, and dearer than the two-stop routing, so Dijkstra and BFS
        # disagree about the best answer the way they do on real data.
        Route(sfo, bos, leg(sfo, bos, 1500.0), "DL", "DL0005"),
    ):
        planner.add_edge(route)
    return planner
