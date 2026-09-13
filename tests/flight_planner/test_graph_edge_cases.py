"""The rubric's named edge cases, against `Graph` and against the real network.

The term project names four structural cases a graph must handle: **empty,
single-element, cyclic/duplicate, and disconnected.** One of the four was
already covered — `test_unreachable_goal` in `test_bfs.py`, `test_dijkstra.py`
and `test_astar.py` each build a graph with a vertex the search cannot reach.
This file is the other three.

Two decisions about how they are tested are worth stating.

**Every case runs against all three algorithms.** An edge case handled by
`Graph` but mishandled by one search is still a defect, and the three searches
do not share a code path — BFS has no priority queue, and Dijkstra and A*
differ only in what they push. Parametrizing is what makes the claim "the structure
handles this" rather than "Dijkstra handles this".

**Cyclic and duplicate are also tested on the world snapshot**, not only on
fixtures. Report §3.6 argues that the cleaned data supplies one real self-loop
(`IL0016 PKN->PKN`, 0.0 km) and 29,615 real parallel edges, and that filtering
them would have been the tidier choice and the worse one — because then the
handling would never be exercised on anything but a fixture. That argument is
only honest if the tests actually use the data.
"""

import math

import pytest

from flight_planner.core import Edge, Graph, Vertex
from flight_planner.experiments import Snapshot
from flight_planner.geo import haversine_heuristic
from flight_planner.pathfinding import AStar, BFS, Dijkstra

SNAPSHOT_ID = "2026-09-11-bb90a8"

# The airport carrying the only self-loop that survives cleaning, and its
# six genuine departures. See report §3.6.
SELF_LOOP_AIRPORT = "PKN"
SELF_LOOP_FLIGHT = "IL0016"

# The pair with the most parallel edges in the cleaned network (§2.4).
BUSIEST_PARALLEL_PAIR = ("ORD", "ATL")


def zero_heuristic(origin, goal):
    """An estimate of nothing, for graphs whose vertices have no location.

    The fixtures below are plain `Vertex` objects with keys and no
    coordinates, so the haversine heuristic cannot be used on them -- it
    reads `latitude`. Estimating zero is admissible for any graph with
    non-negative weights, and reduces A* to Dijkstra, which is the point: it
    exercises A*'s own code path on data that is not geographic.

    Args:
        origin: Vertex being scored. Unused.
        goal: Vertex being searched for. Unused.

    Returns:
        `0.0`, always.
    """
    return 0.0


# For the fixture graphs, whose vertices carry no coordinates.
ALGORITHMS = pytest.mark.parametrize(
    "algorithm",
    [BFS(), Dijkstra(), AStar(zero_heuristic)],
    ids=["bfs", "dijkstra", "astar"],
)

# For the world snapshot, where A* gets the heuristic it ships with.
REAL_ALGORITHMS = pytest.mark.parametrize(
    "algorithm",
    [BFS(), Dijkstra(), AStar(haversine_heuristic())],
    ids=["bfs", "dijkstra", "astar"],
)


@pytest.fixture(scope="module")
def world(repo_root):
    """The cleaned world network, as a `FlightPlanner`."""
    snapshot = Snapshot.open(repo_root / "data" / "snapshots" / SNAPSHOT_ID)
    return snapshot.catalog().planner()


class TestEmptyGraph:
    """A graph with no vertices at all.

    The interesting question is not whether it crashes but whether it
    *distinguishes* itself from a graph where the goal happens to be
    unreachable. It does not, deliberately: both report infinite cost, because
    from the searcher's side "there are no edges out of the start" is the same
    observation.
    """

    def test_it_has_no_vertices_and_no_edges(self):
        graph = Graph()

        assert graph.vertices == []
        assert graph.edges == []

    def test_asking_for_edges_of_an_absent_vertex_is_not_an_error(self):
        """`get_outgoing_edges` answers rather than raising.

        This is what lets a search be aimed at a vertex the graph has never
        seen -- which `graph-stats` relies on to turn `BFS` into a
        reachability probe.
        """
        assert Graph().get_outgoing_edges(Vertex("nobody")) == []

    @ALGORITHMS
    def test_every_search_reports_infinite_cost_and_no_path(self, algorithm):
        graph = Graph()
        start, goal = Vertex("A"), Vertex("B")

        result = graph.search(start, goal, algorithm)

        assert math.isinf(result.cost)
        assert result.path == []

    @ALGORITHMS
    def test_the_counters_are_real_rather_than_absent(self, algorithm):
        """An empty graph still produced a search, and says so.

        One expansion: the start comes off the frontier, has no outgoing
        edges, and the search ends. Reporting zero would be claiming no work
        happened.
        """
        graph = Graph()

        result = graph.search(Vertex("A"), Vertex("B"), algorithm)

        assert result.nodes_pushed == 1
        assert result.nodes_expanded == 1


class TestSingleVertexGraph:
    """One vertex, no edges. The boundary between "trivial" and "impossible"."""

    def test_it_holds_exactly_one_vertex(self):
        graph = Graph()
        only = Vertex("A")
        graph.add_vertex(only)

        assert graph.vertices == [only]
        assert graph.edges == []

    def test_adding_the_same_vertex_twice_is_a_no_op(self):
        """First-wins, and it keeps the edges the first one had.

        Report §3.3 leans on this: it is why a bare `Airport("BOS")` mixed
        into a catalog-built graph would silently discard coordinates.
        """
        graph = Graph()
        a, b = Vertex("A"), Vertex("B")
        graph.add_edge(Edge(a, b, weight=1.0))

        graph.add_vertex(Vertex("A"))  # equal by key, a different object

        assert graph.vertices == [a, b]
        assert len(graph.get_outgoing_edges(a)) == 1

    @ALGORITHMS
    def test_start_equal_to_goal_costs_nothing_and_runs_no_search(self, algorithm):
        """Zero cost, zero legs, and zero work -- the search never starts.

        Distinct from the unreachable case, which reports infinity *and*
        non-zero counters because a search really did run.
        """
        graph = Graph()
        only = Vertex("A")
        graph.add_vertex(only)

        result = graph.search(only, only, algorithm)

        assert result.cost == 0.0
        assert result.path == []
        assert result.nodes_expanded == 0
        assert result.nodes_pushed == 0

    @ALGORITHMS
    def test_a_goal_outside_a_one_vertex_graph_is_unreachable(self, algorithm):
        graph = Graph()
        only = Vertex("A")
        graph.add_vertex(only)

        result = graph.search(only, Vertex("B"), algorithm)

        assert math.isinf(result.cost)
        assert result.path == []


class TestCyclesAndSelfLoops:
    """Cycles must not trap a search, and zero-weight ones must stay legal.

    The illegal case -- a *negative* cycle -- is covered in
    `test_reconstruct_path.py`, where it raises rather than looping forever.
    Here the concern is the legal case, which must simply work.
    """

    @staticmethod
    def cyclic_graph():
        """Return `A->B->C->A` plus a self-loop at B, and its vertices.

        Returns:
            `(graph, a, b, c)`.
        """
        graph = Graph()
        a, b, c = Vertex("A"), Vertex("B"), Vertex("C")
        for edge in (
            Edge(a, b, weight=1.0),
            Edge(b, c, weight=1.0),
            Edge(c, a, weight=1.0),
            Edge(b, b, weight=0.0),
        ):
            graph.add_edge(edge)
        return graph, a, b, c

    @ALGORITHMS
    def test_a_cycle_does_not_prevent_termination(self, algorithm):
        graph, a, _, c = self.cyclic_graph()

        result = graph.search(a, c, algorithm)

        assert result.path, "the goal is reachable, so a path is expected"
        assert len(result.path) == 2

    @ALGORITHMS
    def test_a_zero_weight_self_loop_is_never_traversed(self, algorithm):
        """It is legal, it is present, and it changes no answer.

        Relaxation is strictly-less-than, so arriving at B again for `0 + 0`
        is not an improvement.
        """
        graph, a, _, c = self.cyclic_graph()

        result = graph.search(a, c, algorithm)

        assert [edge.source.key for edge in result.path] == ["A", "B"]
        assert all(
            edge.source != edge.target for edge in result.path
        ), "a self-loop should never appear in a returned path"

    @ALGORITHMS
    def test_a_search_back_around_the_cycle_terminates(self, algorithm):
        """B to A must go the long way round: B -> C -> A."""
        graph, _, b, _ = self.cyclic_graph()

        result = graph.search(b, Vertex("A"), algorithm)

        assert len(result.path) == 2


class TestDuplicateAndParallelEdges:
    """Two edges between the same pair are two edges, not one.

    This is the case the real data exercises hardest: 29,615 of 66,332 routes
    are parallel to another (§2.5).
    """

    @staticmethod
    def parallel_graph():
        """Return `A->B` twice, cheap and expensive, and the endpoints.

        Returns:
            `(graph, a, b, cheap, expensive)`.
        """
        graph = Graph()
        a, b = Vertex("A"), Vertex("B")
        expensive = Edge(a, b, weight=9.0)
        cheap = Edge(a, b, weight=2.0)
        graph.add_edge(expensive)
        graph.add_edge(cheap)
        return graph, a, b, cheap, expensive

    def test_both_edges_are_stored(self):
        """The adjacency list keeps them. An adjacency matrix could not."""
        graph, a, b, cheap, expensive = self.parallel_graph()

        assert graph.vertices == [a, b]
        assert graph.get_outgoing_edges(a) == [expensive, cheap]

    def test_a_weighted_search_takes_the_cheaper_parallel_edge(self):
        """And it does so even though the expensive one was added first."""
        graph, a, b, cheap, _ = self.parallel_graph()

        result = graph.search(a, b, Dijkstra())

        assert result.cost == 2.0
        assert result.path == [cheap]

    def test_bfs_counts_one_hop_regardless_of_which_edge(self):
        """Parallel edges are alternative ways to fly one leg, so BFS sees one."""
        graph, a, b, _, _ = self.parallel_graph()

        result = graph.search(a, b, BFS())

        assert result.cost == 1.0
        assert len(result.path) == 1

    def test_adding_the_identical_edge_object_twice_stores_it_twice(self):
        """`add_edge` appends; it does not deduplicate.

        Recorded because it is a deliberate choice rather than an oversight:
        the loader decides what is a duplicate, since only the domain knows
        whether two rows are two airlines or one row read twice.
        """
        graph = Graph()
        a, b = Vertex("A"), Vertex("B")
        edge = Edge(a, b, weight=1.0)
        graph.add_edge(edge)
        graph.add_edge(edge)

        assert len(graph.get_outgoing_edges(a)) == 2


class TestTheRealGraphSuppliesBothCases:
    """§3.6 claims the data supplies a self-loop and parallel edges. Check it.

    The chapter argues that filtering these would have been the tidier choice
    and the worse one, because the handling would then never be exercised on
    anything but a fixture. These tests are what make that argument true.
    """

    def test_exactly_one_self_loop_survives_cleaning(self, world):
        loops = [
            edge
            for edge in world.edges
            if edge.origin.iata_code == edge.destination.iata_code
        ]

        assert len(loops) == 1
        assert loops[0].flight_number == SELF_LOOP_FLIGHT
        assert loops[0].origin.iata_code == SELF_LOOP_AIRPORT
        assert loops[0].distance_km == 0.0

    def test_the_self_loop_sits_in_a_live_adjacency_list(self, world):
        """It is not quarantined -- it is one of PKN's seven outgoing edges."""
        departures = world.get_outgoing_edges(world.find_airport(SELF_LOOP_AIRPORT))

        assert len(departures) == 7
        assert sum(1 for e in departures if e.destination.iata_code == SELF_LOOP_AIRPORT) == 1

    @REAL_ALGORITHMS
    def test_searching_through_the_self_loop_airport_still_works(self, world, algorithm):
        """A real query out of PKN, with the loop sitting in its edge list."""
        result = world.search_route(SELF_LOOP_AIRPORT, "SIN", algorithm)

        assert math.isfinite(result.cost)
        assert result.path
        assert all(
            leg.origin.iata_code != leg.destination.iata_code for leg in result.path
        ), "the self-loop should never appear in a returned itinerary"

    def test_the_network_really_is_a_multigraph(self, world):
        """29,615 parallel edges is the figure §2.5 and §5 both depend on."""
        pairs = {
            (edge.origin.iata_code, edge.destination.iata_code) for edge in world.edges
        }

        assert len(world.edges) == 66332
        assert len(pairs) == 36717
        assert len(world.edges) - len(pairs) == 29615

    def test_the_busiest_pair_carries_twenty_parallel_routes(self, world):
        """ORD->ATL, the example §2.4 prints."""
        origin, destination = BUSIEST_PARALLEL_PAIR
        parallel = [
            edge
            for edge in world.get_outgoing_edges(world.find_airport(origin))
            if edge.destination.iata_code == destination
        ]

        assert len(parallel) == 20
        assert len({edge.airline for edge in parallel}) > 1, (
            "twenty rows on one pair should be several airlines, not one "
            "airline duplicated -- if this fails the cleaning has a bug"
        )
