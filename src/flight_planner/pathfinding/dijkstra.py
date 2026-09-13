"""Weighted shortest-path search, running on our own min-heap."""

from __future__ import annotations
from typing import Dict, Optional, Set, TypeVar, TYPE_CHECKING

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


class Dijkstra(PathfindingAlgorithm[V, E]):
    """Weighted shortest-path search using edge.weight.

    Priority-queue based. Requires non-negative edge weights.
    """

    #: Dijkstra sums `edge.weight`; the graph defines what that measures.
    unit = COST_WEIGHT

    def search(
        self,
        graph: "Graph[V, E]",
        start: V,
        goal: V,
        observer: Optional[SearchObserver] = None,
    ) -> SearchResult[E]:
        """Find the lowest-total-weight path from `start` to `goal`.

        Args:
            graph: Graph to search.
            start: Vertex to search from.
            goal: Vertex to search for.
            observer: Optional `SearchObserver` notified on each push and
                expansion.

        Returns:
            A `SearchResult` whose `cost` is the total weight, with the
            counters the search accumulated. Unreachable goals give an
            infinite cost and an empty path, keeping the real counters.
        """
        if start == goal:
            return SearchResult(0.0, [], unit=self.unit)

        watcher = observer if observer is not None else _NULL_OBSERVER

        pq: MinHeap[V] = MinHeap()
        pq.push(start, 0.0)
        watcher.on_push(start, 0.0)
        pushed = 1
        peak = 1

        distances: Dict[V, float] = {start: 0.0}
        predecessors: Dict[V, E] = {}
        settled: Set[V] = set()

        while pq:
            current = pq.pop()

            if current == goal:
                break
            # Relaxing a vertex queues it again rather than repositioning the
            # entry already there, so the queue accumulates superseded copies.
            # `settled` discards them: the first pop of a vertex carries its
            # final distance, and every later one is stale by construction.
            if current in settled:
                continue
            settled.add(current)
            current_dist = distances[current]
            watcher.on_expand(current, current_dist)

            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.target
                distance_to_neighbor = current_dist + edge.weight

                if distance_to_neighbor < distances.get(neighbor, float("inf")):
                    distances[neighbor] = distance_to_neighbor
                    predecessors[neighbor] = edge
                    pq.push(neighbor, distance_to_neighbor)
                    watcher.on_push(neighbor, distance_to_neighbor)
                    pushed += 1
                    peak = max(peak, len(pq))

        counters = {
            "nodes_expanded": len(settled),
            "nodes_pushed": pushed,
            "peak_frontier": peak,
        }
        if goal not in predecessors:
            return SearchResult(float("inf"), [], unit=self.unit, **counters)

        return SearchResult(
            distances[goal],
            _reconstruct_path(predecessors, goal),
            unit=self.unit,
            **counters,
        )
