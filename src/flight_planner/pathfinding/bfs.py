"""Fewest-hops search, ignoring edge weights entirely."""

from __future__ import annotations
from collections import deque
from typing import Dict, Optional, TypeVar, TYPE_CHECKING

from ..core.vertex import Vertex
from ..core.edge import Edge
from .observers import SearchObserver
from .result import COST_HOPS, SearchResult
from .strategy import PathfindingAlgorithm, _reconstruct_path

if TYPE_CHECKING:
    from ..core.graph import Graph

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)

_NULL_OBSERVER: SearchObserver = SearchObserver()


class BFS(PathfindingAlgorithm[V, E]):
    """Shortest path by HOP COUNT — every edge costs 1, edge.weight is IGNORED.

    NOTE: This is NOT the same as weighted shortest distance. For weighted
    graphs (e.g. flight distances), prefer Dijkstra or AStar. The returned
    float cost here is a hop count, not a distance.
    """

    #: BFS counts edges, not weight -- `cost` is a hop count.
    unit = COST_HOPS

    def search(
        self,
        graph: "Graph[V, E]",
        start: V,
        goal: V,
        observer: Optional[SearchObserver] = None,
    ) -> SearchResult[E]:
        """Find the path with the fewest edges from `start` to `goal`.

        Args:
            graph: Graph to search.
            start: Vertex to search from.
            goal: Vertex to search for.
            observer: Optional `SearchObserver` notified on each push and
                expansion. BFS has no priority queue, so it reports hop depth
                as the priority — the quantity its FIFO ordering stands in for.

        Returns:
            A `SearchResult` whose `cost` is a **hop count**, not a distance,
            since `edge.weight` is ignored. Unreachable goals give an infinite
            cost and an empty path, keeping the real counters.
        """
        if start == goal:
            return SearchResult(0.0, [], unit=self.unit)

        watcher = observer if observer is not None else _NULL_OBSERVER

        visited = {start}
        predecessors: Dict[V, E] = {}
        depth: Dict[V, float] = {start: 0.0}
        queue: deque = deque([start])

        watcher.on_push(start, 0.0)
        pushed = 1
        peak = 1
        # `visited` is marked when a vertex is *queued*, not when it is taken
        # off, so its size is not the expansion count. Count expansions where
        # they happen, so this number means the same thing it does for the
        # weighted algorithms.
        expanded = 0

        while queue:
            current = queue.popleft()
            if current == goal:
                break

            expanded += 1
            watcher.on_expand(current, depth[current])

            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.target
                if neighbor not in visited:
                    visited.add(neighbor)
                    predecessors[neighbor] = edge
                    depth[neighbor] = depth[current] + 1
                    queue.append(neighbor)
                    watcher.on_push(neighbor, depth[neighbor])
                    pushed += 1
                    peak = max(peak, len(queue))

        counters = {
            "nodes_expanded": expanded,
            "nodes_pushed": pushed,
            "peak_frontier": peak,
        }
        if goal not in predecessors:
            return SearchResult(float("inf"), [], unit=self.unit, **counters)

        path = _reconstruct_path(predecessors, goal)
        return SearchResult(float(len(path)), path, unit=self.unit, **counters)
