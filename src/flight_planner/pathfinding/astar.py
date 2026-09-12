"""Heuristic-guided weighted shortest-path search."""

from __future__ import annotations
from typing import Callable, Dict, List, Set, Tuple, TypeVar, TYPE_CHECKING

from ..adt.min_heap import MinHeap
from ..core.vertex import Vertex
from ..core.edge import Edge
from .strategy import PathfindingAlgorithm, _reconstruct_path

if TYPE_CHECKING:
    from ..core.graph import Graph

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)


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
