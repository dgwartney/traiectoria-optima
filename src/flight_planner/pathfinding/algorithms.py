"""Pathfinding Strategy interface and concrete algorithms.

These operate purely on the generic Graph/Vertex/Edge interface
(get_outgoing_edges, edge.source/target/weight) and know nothing about any
specific domain (e.g. Airport/Route) — they work on any Graph[V, E].
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from collections import deque
from typing import Callable, Dict, Generic, List, Set, Tuple, TypeVar, TYPE_CHECKING

from ..adt.min_heap import MinHeap
from ..core.vertex import Vertex
from ..core.edge import Edge

if TYPE_CHECKING:
    from ..core.graph import Graph

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)


class PathfindingAlgorithm(ABC, Generic[V, E]):
    """Strategy interface: compute a path between two vertices of a Graph."""

    @abstractmethod
    def find_path(self, graph: "Graph[V, E]", start: V, goal: V) -> Tuple[float, List[E]]:
        """Find a path from `start` to `goal`.

        Args:
            graph: Graph to search, used only through `get_outgoing_edges`.
            start: Vertex to search from.
            goal: Vertex to search for.

        Returns:
            Tuple of `(total_cost, ordered_edges_forming_the_path)`.
            `(float("inf"), [])` if `goal` is unreachable from `start`, and
            `(0.0, [])` if `start == goal`.
        """
        raise NotImplementedError


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


class BFS(PathfindingAlgorithm[V, E]):
    """Shortest path by HOP COUNT — every edge costs 1, edge.weight is IGNORED.

    NOTE: This is NOT the same as weighted shortest distance. For weighted
    graphs (e.g. flight distances), prefer Dijkstra or AStar. The returned
    float cost here is a hop count, not a distance.
    """

    def find_path(self, graph: "Graph[V, E]", start: V, goal: V) -> Tuple[float, List[E]]:
        """Find the path with the fewest edges from `start` to `goal`.

        Args:
            graph: Graph to search.
            start: Vertex to search from.
            goal: Vertex to search for.

        Returns:
            Tuple of `(hop_count, ordered_edges)` — the first element is a
            count of edges, not a distance, since `edge.weight` is ignored.
            `(float("inf"), [])` if `goal` is unreachable, or `(0.0, [])` if
            `start == goal`.
        """
        if start == goal:
            return 0.0, []

        visited = {start}
        predecessors: Dict[V, E] = {}
        queue: deque = deque([start])

        while queue:
            current = queue.popleft()
            if current == goal:
                break

            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.target
                if neighbor not in visited:
                    visited.add(neighbor)
                    predecessors[neighbor] = edge
                    queue.append(neighbor)

        if goal not in predecessors:
            return float("inf"), []

        path = _reconstruct_path(predecessors, goal)
        return float(len(path)), path


class AStar(PathfindingAlgorithm[V, E]):
    """Weighted shortest-path search guided by a heuristic.

    heuristic: Callable[[V, V], float] must be admissible (never overestimate
    the true remaining cost to the goal) for the result to be optimal, e.g.
    great-circle distance when edge weights are real travel distances.
    """

    def __init__(self, heuristic: Callable[[V, V], float]) -> None:
        """Configure the search with the heuristic that guides it.

        Args:
            heuristic: Callable estimating the remaining cost from a vertex to
                the goal. Must be admissible — never overestimating the true
                remaining cost — for the returned path to be optimal.
        """
        self._heuristic = heuristic

    def find_path(self, graph: "Graph[V, E]", start: V, goal: V) -> Tuple[float, List[E]]:
        """Find the lowest-total-weight path, guided by the heuristic.

        Args:
            graph: Graph to search.
            start: Vertex to search from.
            goal: Vertex to search for.

        Returns:
            Tuple of `(total_weight, ordered_edges)`, `(float("inf"), [])` if
            `goal` is unreachable, or `(0.0, [])` if `start == goal`. The path
            is optimal only if the configured heuristic is admissible.
        """
        if start == goal:
            return 0.0, []

        open_set: MinHeap[V] = MinHeap()
        open_set.push(start, self._heuristic(start, goal))
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

            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.target
                tentative_g = g_score[current] + edge.weight

                if tentative_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = tentative_g
                    predecessors[neighbor] = edge
                    f_score = tentative_g + self._heuristic(neighbor, goal)
                    open_set.push(neighbor, f_score)

        if goal not in predecessors:
            return float("inf"), []

        return g_score[goal], _reconstruct_path(predecessors, goal)


def _reconstruct_path(predecessors: Dict[V, E], goal: V) -> List[E]:
    path: List[E] = []
    current = goal
    while current in predecessors:
        edge = predecessors[current]
        path.append(edge)
        current = edge.source
    path.reverse()
    return path
