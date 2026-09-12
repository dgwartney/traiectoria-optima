"""Weighted shortest-path search, running on our own min-heap."""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, TypeVar, TYPE_CHECKING

from ..adt.min_heap import MinHeap
from ..core.vertex import Vertex
from ..core.edge import Edge
from .strategy import PathfindingAlgorithm, _reconstruct_path

if TYPE_CHECKING:
    from ..core.graph import Graph

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)


class Dijkstra(PathfindingAlgorithm[V, E]):
    """Weighted shortest-path search using edge.weight.

    Priority-queue based. Requires non-negative edge weights.
    """

    def find_path(self, graph: "Graph[V, E]", start: V, goal: V) -> Tuple[float, List[E]]:
        """Find the lowest-total-weight path from `start` to `goal`.

        Args:
            graph: Graph to search.
            start: Vertex to search from.
            goal: Vertex to search for.

        Returns:
            Tuple of `(total_weight, ordered_edges)`, `(float("inf"), [])` if
            `goal` is unreachable, or `(0.0, [])` if `start == goal`.
        """
        if start == goal:
            return 0.0, []

        pq: MinHeap[V] = MinHeap()
        pq.push(start, 0.0)
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

            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.target
                distance_to_neighbor = current_dist + edge.weight

                if distance_to_neighbor < distances.get(neighbor, float("inf")):
                    distances[neighbor] = distance_to_neighbor
                    predecessors[neighbor] = edge
                    pq.push(neighbor, distance_to_neighbor)

        if goal not in predecessors:
            return float("inf"), []

        return distances[goal], _reconstruct_path(predecessors, goal)
