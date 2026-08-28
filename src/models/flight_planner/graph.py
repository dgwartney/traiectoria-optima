"""Weighted graph abstraction built on Vertex and Edge."""

from __future__ import annotations
from typing import Generic, TypeVar, Dict, List, Tuple, TYPE_CHECKING

from vertex import Vertex
from edge import Edge

if TYPE_CHECKING:
    from pathfinding import PathfindingAlgorithm

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)


class Graph(Generic[V, E]):
    """Weighted graph enclosing Vertex and Edge instances."""

    def __init__(self) -> None:
        self._adjacency: Dict[V, List[E]] = {}

    @property
    def vertices(self) -> List[V]:
        return list(self._adjacency.keys())

    @property
    def edges(self) -> List[E]:
        edge_list: List[E] = []
        for edges in self._adjacency.values():
            edge_list.extend(edges)
        return edge_list

    def add_vertex(self, vertex: V) -> None:
        if vertex not in self._adjacency:
            self._adjacency[vertex] = []

    def add_edge(self, edge: E) -> None:
        if edge.source not in self._adjacency:
            self.add_vertex(edge.source)
        if edge.target not in self._adjacency:
            self.add_vertex(edge.target)
        self._adjacency[edge.source].append(edge)

    def get_outgoing_edges(self, vertex: V) -> List[E]:
        return list(self._adjacency.get(vertex, []))

    def shortest_path(
        self, start: V, goal: V, algorithm: "PathfindingAlgorithm[V, E]"
    ) -> Tuple[float, List[E]]:
        """Delegates to a pathfinding Strategy; Graph has no knowledge of
        algorithm internals (see pathfinding/algorithms.py)."""
        return algorithm.find_path(self, start, goal)
