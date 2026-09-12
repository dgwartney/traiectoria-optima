"""Pathfinding Strategy interface, and the path reconstruction all of it shares.

The interface operates purely on the generic Graph/Vertex/Edge contract
(`get_outgoing_edges`, `edge.source`/`target`/`weight`) and knows nothing about
any specific domain (e.g. Airport/Route) — it works on any `Graph[V, E]`.

Each concrete algorithm lives in its own module beside this one (`dijkstra.py`,
`bfs.py`, `astar.py`), mirroring how `geo/` keeps `DistanceFormula` in
`formula.py` and each formula in its own file.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Generic, List, Tuple, TypeVar, TYPE_CHECKING

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


def _reconstruct_path(predecessors: Dict[V, E], goal: V) -> List[E]:
    path: List[E] = []
    current = goal
    while current in predecessors:
        edge = predecessors[current]
        path.append(edge)
        current = edge.source
    path.reverse()
    return path
