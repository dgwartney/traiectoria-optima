"""NetworkX behind `PathfindingAlgorithm` — Option C of the validation plan.

An adapter implementing the Strategy the project already has, so the *engine*
becomes a parameter of an experiment exactly as `Dijkstra()` versus `BFS()`
already is. `planner.find_shortest_route(origin, destination, NetworkXDijkstra())`
returns `Route` legs, not node keys, and every downstream consumer — leg
counting, flight numbers, the shape of `results.json` — cannot tell which
engine produced them. That indifference is the thing being validated: it means
a NetworkX result and ours are the same *kind* of answer, not merely the same
number.

`search` is the hook, not `find_path`. `PathfindingAlgorithm` declares `search`
abstract and provides `find_path` as a concrete `(cost, path)` adapter, so an
engine implementing only `find_path` will not instantiate at all.

**The counters are reported as zero, deliberately.** NetworkX does not expose
how many nodes it expanded, and there is no honest way to recover it from the
outside. A plausible-looking substitute — counting heuristic calls, say — would
put a fabricated number in the same column as `Dijkstra`'s measured one, in a
table whose entire purpose is comparing those numbers. Zero is visibly not a
measurement; a wrong count is not. `SearchResult.found` still works, because it
reads `cost`.

These engines validate *costs and contracts*. Expansion parity is what our own
instrumented algorithms are for.
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, TypeVar

import networkx as nx

from flight_planner.core.edge import Edge
from flight_planner.core.graph import Graph
from flight_planner.core.vertex import Vertex
from flight_planner.pathfinding.observers import SearchObserver
from flight_planner.pathfinding.result import SearchResult
from flight_planner.pathfinding.result import COST_HOPS
from flight_planner.pathfinding.strategy import PathfindingAlgorithm

from .oracle import NetworkXMirror

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)


class _NetworkXEngine(PathfindingAlgorithm[V, E]):
    """Shared plumbing for the three reference engines.

    Subclasses answer one question each: which NetworkX call to make, and how
    to turn the node sequence it returns back into our edges.

    The mirror is built on first use and cached, since building it over the
    world snapshot costs about as much as the search does — and a benchmark
    that rebuilt it per query would report the adapter as pathologically slow
    for a reason that has nothing to do with NetworkX. The cache is keyed by
    *identity*, so a different graph rebuilds and a mutated one does not. That
    second case is a real hazard, documented rather than defended against:
    adding an edge after the first search leaves the mirror stale.
    """

    def __init__(self) -> None:
        """Create an engine with no mirror yet."""
        self._mirror: Optional[NetworkXMirror[V, E]] = None

    def _mirror_of(self, graph: Graph[V, E]) -> NetworkXMirror[V, E]:
        """Return the mirror of `graph`, building it if needed.

        Args:
            graph: Graph being searched.

        Returns:
            A mirror of `graph`, cached across calls on the same graph.
        """
        if self._mirror is None or not self._mirror.mirrors(graph):
            self._mirror = NetworkXMirror(graph)
        return self._mirror

    def _nodes(self, mirror: NetworkXMirror[V, E], start: V, goal: V) -> List[object]:
        """Return NetworkX's node sequence from `start` to `goal`.

        Args:
            mirror: Mirror to search.
            start: Vertex to search from.
            goal: Vertex to search for.

        Returns:
            Node keys in order.

        Raises:
            networkx.NetworkXNoPath: If the goal is unreachable.
        """
        raise NotImplementedError

    def _cost(self, legs: List[E]) -> float:
        """Return the cost of a path in this engine's own unit.

        Args:
            legs: Edges forming the path, in order.

        Returns:
            Total cost. Summed weight for the weighted engines; a hop count
            for `NetworkXBFS`, matching what `BFS` returns.
        """
        return sum(leg.weight for leg in legs)

    def search(
        self,
        graph: Graph[V, E],
        start: V,
        goal: V,
        observer: Optional[SearchObserver] = None,
    ) -> SearchResult[E]:
        """Find a path by asking NetworkX, and answer in our own types.

        Args:
            graph: Graph to search. Mirrored on first use and cached.
            start: Vertex to search from.
            goal: Vertex to search for.
            observer: Accepted and ignored. NetworkX exposes no per-expansion
                hook, and an observer that silently never fires is less
                misleading than one fed invented events. Never notified, so a
                trace taken through this engine is empty rather than wrong.

        Returns:
            A `SearchResult` carrying the route and its cost, with all three
            counters zero — see the module docstring. `(inf, [])` if the goal
            is unreachable and `(0.0, [])` if `start == goal`, matching the
            contract our own algorithms keep.
        """
        if start == goal:
            return SearchResult(0.0, [], unit=self.unit)

        mirror = self._mirror_of(graph)
        try:
            nodes = self._nodes(mirror, start, goal)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return SearchResult(math.inf, [], unit=self.unit)

        legs = self._legs(graph, mirror, nodes)
        return SearchResult(self._cost(legs), legs, unit=self.unit)

    @staticmethod
    def _legs(
        graph: Graph[V, E], mirror: NetworkXMirror[V, E], nodes: List[object]
    ) -> List[E]:
        """Turn a node sequence into the edges our types describe it with.

        NetworkX returns nodes, `SearchResult` carries edges, and between two
        airports there may be up to 20 parallel routes. The cheapest is chosen,
        which reproduces the reported cost exactly — but where several legs tie
        on distance, the flight number picked need not be the one
        `flight_planner` would pick. Costs are the durable contract; flight
        numbers are a secondary check.

        Args:
            graph: Graph the edges must come from.
            mirror: Mirror used to map keys back to vertices.
            nodes: Node keys in path order.

        Returns:
            Edges forming the path, in order.

        Raises:
            KeyError: If a consecutive pair has no edge between them, which
                would mean the mirror and the graph disagree.
        """
        legs: List[E] = []
        for origin, destination in zip(nodes, nodes[1:]):
            candidates = [
                edge
                for edge in graph.get_outgoing_edges(mirror.vertex(origin))
                if edge.target.key == destination
            ]
            if not candidates:
                raise KeyError(f"no edge {origin!r} -> {destination!r} in the graph")
            legs.append(min(candidates, key=lambda edge: edge.weight))
        return legs


class NetworkXDijkstra(_NetworkXEngine[V, E]):
    """Weighted shortest path, computed by NetworkX.

    The reference engine for `flight_planner.Dijkstra`. Same question, same
    graph, independently implemented — so a disagreement is a bug in one of
    the two.
    """

    def _nodes(self, mirror: NetworkXMirror[V, E], start: V, goal: V) -> List[object]:
        """Return NetworkX's weighted shortest path.

        Args:
            mirror: Mirror to search.
            start: Vertex to search from.
            goal: Vertex to search for.

        Returns:
            Node keys in order.
        """
        return mirror.path(start.key, goal.key)


class NetworkXBFS(_NetworkXEngine[V, E]):
    """Fewest edges, computed by NetworkX with the weights ignored.

    The reference engine for `flight_planner.BFS`, and its `cost` is a **hop
    count**, not a distance — the same unit `BFS` reports, so the two are
    comparable and neither is comparable with the weighted engines.
    """

    #: Matches `BFS.unit`, which is what makes the parity comparison valid.
    unit = COST_HOPS

    def _nodes(self, mirror: NetworkXMirror[V, E], start: V, goal: V) -> List[object]:
        """Return NetworkX's unweighted shortest path.

        Args:
            mirror: Mirror to search.
            start: Vertex to search from.
            goal: Vertex to search for.

        Returns:
            Node keys in order.
        """
        return mirror.hop_path(start.key, goal.key)

    def _cost(self, legs: List[E]) -> float:
        """Return the number of legs, not their total weight.

        Args:
            legs: Edges forming the path, in order.

        Returns:
            Hop count as a float, matching `BFS`.
        """
        return float(len(legs))


class NetworkXAStar(_NetworkXEngine[V, E]):
    """Heuristic-guided weighted shortest path, computed by NetworkX.

    The reference engine for `flight_planner.AStar`, and the more interesting
    of the three: NetworkX's A* *reopens* nodes rather than closing them on
    pop, so it is optimal for any admissible heuristic. `AStar` closes them,
    which requires the stronger condition of consistency. Where the two
    disagree, this engine is right — see `validation.reopening.ReopeningAStar`.

    The heuristic arrives here in `flight_planner` terms, over vertices, and is
    bridged to the node keys NetworkX passes. Callers write one heuristic and
    hand the same object to both engines.
    """

    def __init__(self, heuristic: Callable[[V, V], float]) -> None:
        """Configure the engine with the heuristic that guides it.

        Args:
            heuristic: Callable over *vertices*, estimating the remaining cost
                to the goal — the same signature `AStar` takes, so one
                heuristic serves both. Must be admissible.
        """
        super().__init__()
        self._heuristic = heuristic

    def _nodes(self, mirror: NetworkXMirror[V, E], start: V, goal: V) -> List[object]:
        """Return NetworkX's A* path under the configured heuristic.

        Args:
            mirror: Mirror to search.
            start: Vertex to search from.
            goal: Vertex to search for.

        Returns:
            Node keys in order.

        Raises:
            networkx.NetworkXNoPath: If the goal is unreachable.
        """

        def over_keys(origin_key: object, goal_key: object) -> float:
            return self._heuristic(mirror.vertex(origin_key), mirror.vertex(goal_key))

        return nx.astar_path(
            mirror.graph,
            start.key,
            goal.key,
            heuristic=over_keys,
            weight="weight",
        )
