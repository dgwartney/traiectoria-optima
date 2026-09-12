"""Fewest-hops search, ignoring edge weights entirely."""

from __future__ import annotations
from collections import deque
from typing import Dict, List, Tuple, TypeVar, TYPE_CHECKING

from ..core.vertex import Vertex
from ..core.edge import Edge
from .strategy import PathfindingAlgorithm, _reconstruct_path

if TYPE_CHECKING:
    from ..core.graph import Graph

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)


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
