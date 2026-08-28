"""Pathfinding Strategy interface and concrete algorithms.

These operate purely on the generic Graph/Vertex/Edge interface
(get_outgoing_edges, edge.source/target/weight) and know nothing about any
specific domain (e.g. Airport/Route) — they work on any Graph[V, E].
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from collections import deque
from typing import Callable, Dict, Generic, List, Tuple, TypeVar, TYPE_CHECKING
import heapq

from vertex import Vertex
from edge import Edge

if TYPE_CHECKING:
    from graph import Graph

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)


class PathfindingAlgorithm(ABC, Generic[V, E]):
    """Strategy interface: compute a path between two vertices of a Graph."""

    @abstractmethod
    def find_path(self, graph: "Graph[V, E]", start: V, goal: V) -> Tuple[float, List[E]]:
        """
        Returns (total_cost, ordered_edges_forming_the_path).
        Returns (float('inf'), []) if goal is unreachable from start.
        Returns (0.0, []) if start == goal.
        """
        raise NotImplementedError


class Dijkstra(PathfindingAlgorithm[V, E]):
    """Weighted shortest-path search using edge.weight (priority-queue based).
    Requires non-negative edge weights."""

    def find_path(self, graph: "Graph[V, E]", start: V, goal: V) -> Tuple[float, List[E]]:
        if start == goal:
            return 0.0, []

        counter = 0
        pq: List[Tuple[float, int, V]] = [(0.0, counter, start)]
        distances: Dict[V, float] = {start: 0.0}
        predecessors: Dict[V, E] = {}

        while pq:
            current_dist, _, current = heapq.heappop(pq)

            if current == goal:
                break
            if current_dist > distances.get(current, float("inf")):
                continue

            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.target
                distance_to_neighbor = current_dist + edge.weight

                if distance_to_neighbor < distances.get(neighbor, float("inf")):
                    distances[neighbor] = distance_to_neighbor
                    predecessors[neighbor] = edge
                    counter += 1
                    heapq.heappush(pq, (distance_to_neighbor, counter, neighbor))

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
        self._heuristic = heuristic

    def find_path(self, graph: "Graph[V, E]", start: V, goal: V) -> Tuple[float, List[E]]:
        if start == goal:
            return 0.0, []

        counter = 0
        open_set: List[Tuple[float, int, V]] = [(self._heuristic(start, goal), counter, start)]
        g_score: Dict[V, float] = {start: 0.0}
        predecessors: Dict[V, E] = {}
        visited = set()

        while open_set:
            _, _, current = heapq.heappop(open_set)

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
                    counter += 1
                    f_score = tentative_g + self._heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score, counter, neighbor))

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
