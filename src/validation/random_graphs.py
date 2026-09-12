"""Random graphs built for both libraries, and a heuristic chosen to hurt.

Flight data is well behaved in ways that hide bugs. Every route has a positive
weight, the network is dense and mostly connected, and the great-circle
heuristic is consistent because geometry makes it so. None of the interesting
failure modes live there.

These two classes generate the cases that are missing: graphs with zero
weights, ties, self-loops, parallel edges, disconnected components, and — the
one that found a real defect — a heuristic that is admissible without being
consistent.

`RandomGraphPair` builds one graph *twice*, once in each library, from a
single seed. Building it once and converting would test the converter; building
it twice from the same decisions tests the algorithms.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Mapping, Tuple

import networkx as nx

from flight_planner.core.edge import Edge
from flight_planner.core.graph import Graph
from flight_planner.core.vertex import Vertex

#: Edge weights drawn from this list. `1.0` appears twice so ties are common,
#: `0.0` because a zero-weight edge is legal for Dijkstra and easy to get
#: wrong, and a continuous draw so most weights are distinct. Negative weights
#: are outside Dijkstra's contract and are never generated.
WEIGHTS: Tuple[float, ...] = (0.0, 1.0, 1.0, 2.5)


class RandomGraphPair:
    """The same random weighted digraph, built for both libraries.

    Reproducible from the seed alone, which matters twice over: a failing
    parametrized test names the seed in its id, and a recorded experiment can
    state the seeds it swept instead of the graphs.

    The NetworkX side is a `DiGraph`, not a `MultiDiGraph`, and so cannot hold
    parallel edges. Where the generator produces one, the *cheapest* weight is
    kept — which makes the oracle answer the same question our multigraph
    answers, since a shortest path would never choose the dearer of two
    parallel edges. Getting this backwards is the subtle way to make a parity
    suite that passes while comparing two different graphs.

    Attributes:
        seed: The seed this pair was built from.
        ours: The `flight_planner` `Graph`.
        theirs: The equivalent `nx.DiGraph`.
        vertices: Our vertices, in creation order.
    """

    def __init__(self, seed: int, max_order: int = 25, density: int = 3) -> None:
        """Build one graph pair.

        Args:
            seed: Seed for every decision made here. The same seed always
                produces the same pair.
            max_order: Largest number of vertices to generate. The actual
                order is drawn from `[2, max_order]`, so small graphs — where
                a bug is easy to read — are well represented.
            density: Multiplier on the vertex count bounding the edge draw, so
                a graph gets between zero and `order * density` edges. Zero
                edges is a case worth generating, not an accident.
        """
        rng = random.Random(seed)
        order = rng.randint(2, max_order)
        size = rng.randint(0, order * density)

        self.seed = seed
        self.ours: Graph[Vertex, Edge] = Graph()
        self.theirs = nx.DiGraph()
        self.vertices: List[Vertex] = [Vertex(f"n{index}") for index in range(order)]

        for vertex in self.vertices:
            self.ours.add_vertex(vertex)
            self.theirs.add_node(vertex.key)

        for _ in range(size):
            source = rng.choice(self.vertices)
            target = rng.choice(self.vertices)
            weight = rng.choice(WEIGHTS + (rng.random() * 10,))
            self.ours.add_edge(Edge(source, target, weight=weight))
            if self.theirs.has_edge(source.key, target.key):
                weight = min(weight, self.theirs[source.key][target.key]["weight"])
            self.theirs.add_edge(source.key, target.key, weight=weight)

    @property
    def order(self) -> int:
        """Return the vertex count."""
        return len(self.vertices)

    def distance(self, origin: Vertex, goal: Vertex) -> float:
        """Return NetworkX's weighted shortest-path length, or infinity.

        Args:
            origin: Vertex to start from.
            goal: Vertex to reach.

        Returns:
            Total weight of the cheapest path, or `inf` if unreachable.
            Disconnected graphs are the common case here, not the exception.
        """
        try:
            return nx.shortest_path_length(
                self.theirs, origin.key, goal.key, weight="weight"
            )
        except nx.NetworkXNoPath:
            return math.inf

    def hops(self, origin: Vertex, goal: Vertex) -> float:
        """Return NetworkX's unweighted shortest-path length, or infinity.

        Args:
            origin: Vertex to start from.
            goal: Vertex to reach.

        Returns:
            Number of edges in the shortest path, or `inf` if unreachable.
        """
        try:
            return float(nx.shortest_path_length(self.theirs, origin.key, goal.key))
        except nx.NetworkXNoPath:
            return math.inf

    def remaining_costs(self, goal: Vertex) -> Mapping[str, float]:
        """Return the true remaining cost to `goal` from every vertex.

        The ground truth an admissible heuristic must not exceed, which is how
        `InconsistentHeuristic` can guarantee admissibility by construction
        rather than by argument.

        Args:
            goal: Vertex the costs are measured to.

        Returns:
            Mapping from vertex key to true remaining cost. Vertices that
            cannot reach `goal` are absent.
        """
        return dict(
            nx.shortest_path_length(self.theirs, target=goal.key, weight="weight")
        )

    def ordered_pairs(self) -> List[Tuple[Vertex, Vertex]]:
        """Return every ordered pair of distinct vertices, goal-major.

        Goal-major because a per-goal heuristic is built once and reused
        across every start, which is the expensive part.

        Returns:
            `(start, goal)` pairs.
        """
        return [
            (start, goal)
            for goal in self.vertices
            for start in self.vertices
            if start != goal
        ]

    def __repr__(self) -> str:
        """Return a debugging representation.

        Returns:
            String of the form `RandomGraphPair(seed=7, order=12, size=30)`.
        """
        return (
            f"RandomGraphPair(seed={self.seed}, order={self.order}, "
            f"size={self.theirs.number_of_edges()})"
        )


class InconsistentHeuristic:
    """Admissible by construction, deliberately not consistent.

    `h(v)` is a fixed random fraction of the true remaining distance to the
    goal. It therefore never overestimates — admissible — while freely
    violating `h(u) <= w(u, v) + h(v)`, the triangle inequality a closed-set
    A* implicitly relies on.

    **Every vertex is scored once, at construction, and that is the point.**
    The obvious shortcut is a closure calling `rng.random()` inside the body:

        def heuristic(vertex, goal):
            return remaining[vertex.key] * rng.random()   # WRONG

    That returns a different estimate every time it is asked about the same
    vertex, which is not a function and therefore not a heuristic. It makes
    results irreproducible, inflates the failure count, and produces a flaky
    test. Scoring up front costs one dict and removes the whole class of
    problem.

    Vertices that cannot reach the goal score `0.0`, which is admissible
    against an infinite true cost and keeps the estimator total.
    """

    def __init__(self, pair: RandomGraphPair, goal: Vertex, seed: int) -> None:
        """Score every vertex once, so the heuristic is a fixed function.

        Args:
            pair: Graph pair to take true remaining costs from.
            goal: The goal these estimates are relative to. A heuristic is
                only admissible with respect to one goal, so one instance is
                needed per goal.
            seed: Seed for the fractions. Keep it distinct from the graph's —
                the sweeps use `seed ^ 0xA5` — so the estimates do not
                correlate with the graph's own structure.
        """
        rng = random.Random(seed)
        remaining = pair.remaining_costs(goal)
        self.goal = goal
        self._scores: Dict[str, float] = {
            vertex.key: remaining.get(vertex.key, 0.0) * rng.random()
            for vertex in pair.vertices
        }

    def __call__(self, vertex: Vertex, _goal: Vertex) -> float:
        """Return the estimate for `vertex`.

        Args:
            vertex: Vertex being scored.
            _goal: Ignored. The goal was fixed at construction, since the
                scores are relative to it; `PathfindingAlgorithm` passes it
                anyway, so the signature accepts it.

        Returns:
            The stored estimate.

        Raises:
            KeyError: If asked about a vertex outside the graph it was built
                from — which would mean the heuristic and the search disagree
                about what they are searching.
        """
        return self._scores[vertex.key]

    def over_keys(self, origin_key: str, _goal_key: str) -> float:
        """Return the estimate for a *node key*, for NetworkX.

        Args:
            origin_key: Key of the node being scored.
            _goal_key: Ignored, as above.

        Returns:
            The stored estimate.
        """
        return self._scores[origin_key]

    def is_admissible(self, pair: RandomGraphPair) -> bool:
        """Verify admissibility rather than assuming it.

        The class guarantees this by construction, so a failure means the
        construction is wrong — which is worth a test of its own, since every
        conclusion drawn from this heuristic rests on it.

        Args:
            pair: The graph pair the scores came from.

        Returns:
            `True` if no estimate exceeds the true remaining cost.
        """
        remaining = pair.remaining_costs(self.goal)
        return all(
            estimate <= remaining.get(key, math.inf) + 1e-9
            for key, estimate in self._scores.items()
        )

    def is_consistent(self, pair: RandomGraphPair) -> bool:
        """Report whether the heuristic happens to be consistent.

        Expected to be `False` — that is the entire purpose — but a random
        draw on a tiny or edgeless graph can produce a consistent one by
        accident, and a sweep should be able to say how often.

        Args:
            pair: The graph pair the scores came from.

        Returns:
            `True` if `h(u) <= w(u, v) + h(v)` holds for every edge.
        """
        for edge in pair.ours.edges:
            left = self._scores[edge.source.key]
            right = edge.weight + self._scores[edge.target.key]
            if left > right + 1e-9:
                return False
        return True

    def __repr__(self) -> str:
        """Return a debugging representation.

        Returns:
            String of the form `InconsistentHeuristic(goal='n3', scored=12)`.
        """
        return (
            f"InconsistentHeuristic(goal={self.goal.key!r}, "
            f"scored={len(self._scores)})"
        )
