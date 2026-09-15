"""Heuristic-guided weighted shortest-path search."""

from __future__ import annotations
from typing import Callable, Dict, Optional, Set, TypeVar, TYPE_CHECKING

from ..adt.min_heap import MinHeap
from ..core.vertex import Vertex
from ..core.edge import Edge
from .observers import SearchObserver
from .result import COST_WEIGHT, SearchResult
from .strategy import PathfindingAlgorithm, _reconstruct_path

if TYPE_CHECKING:
    from ..core.graph import Graph

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)

_NULL_OBSERVER: SearchObserver = SearchObserver()


class AStar(PathfindingAlgorithm[V, E]):
    """Weighted shortest-path search guided by a heuristic.

    heuristic: Callable[[V, V], float] must be consistent (never overestimate
    the remaining cost to the goal by more than the true cost of any one
    edge) for the result to be optimal, e.g. great-circle distance when edge
    weights are real travel distances.
    """

    #: A* sums `edge.weight`, exactly as Dijkstra does -- the heuristic
    #: steers the search but never enters the reported cost.
    unit = COST_WEIGHT

    def __init__(self, heuristic: Callable[[V, V], float]) -> None:
        """Configure the search with the heuristic that guides it.

        Args:
            heuristic: Callable estimating the remaining cost from a vertex to
                the goal. Must be consistent — its estimate can never drop, on
                a single edge, by more than that edge's real weight — for the
                returned path to be optimal.
        """
        self._heuristic = heuristic

    def search(
        self,
        graph: "Graph[V, E]",
        start: V,
        goal: V,
        observer: Optional[SearchObserver] = None,
    ) -> SearchResult[E]:
        """Find the lowest-total-weight path, guided by the heuristic.

        Args:
            graph: Graph to search.
            start: Vertex to search from.
            goal: Vertex to search for.
            observer: Optional `SearchObserver` notified on each push and
                expansion. Pushes report `f = g + h`; expansions report `g`,
                so an expansion trace is directly comparable with Dijkstra's.

        Returns:
            A `SearchResult` whose `cost` is the total weight, with the
            counters the search accumulated. `nodes_expanded` is the number
            this project exists to compare against Dijkstra's. The path is
            optimal only if the configured heuristic is consistent.
        """
        if start == goal:
            return SearchResult(0.0, [], unit=self.unit)

        watcher = observer if observer is not None else _NULL_OBSERVER

        open_set: MinHeap[V] = MinHeap()
        start_f = self._heuristic(start, goal)
        open_set.push(start, start_f)
        watcher.on_push(start, start_f)
        pushed = 1
        peak = 1

        g_score: Dict[V, float] = {start: 0.0}
        predecessors: Dict[V, E] = {}
        visited: Set[V] = set()

        while open_set:
            current = open_set.pop()

            if current == goal:
                break
            if current in visited:
                continue
            visited.add(current)
            watcher.on_expand(current, g_score[current])

            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.target
                tentative_g = g_score[current] + edge.weight

                if tentative_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = tentative_g
                    predecessors[neighbor] = edge
                    f_score = tentative_g + self._heuristic(neighbor, goal)
                    open_set.push(neighbor, f_score)
                    watcher.on_push(neighbor, f_score)
                    pushed += 1
                    peak = max(peak, len(open_set))

        counters = {
            "nodes_expanded": len(visited),
            "nodes_pushed": pushed,
            "peak_frontier": peak,
        }
        if goal not in predecessors:
            return SearchResult(float("inf"), [], unit=self.unit, **counters)

        return SearchResult(
            g_score[goal],
            _reconstruct_path(predecessors, goal),
            unit=self.unit,
            **counters,
        )
