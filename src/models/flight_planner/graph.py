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
        """Create an empty graph."""
        self._adjacency: Dict[V, List[E]] = {}

    @property
    def vertices(self) -> List[V]:
        """Return every vertex in the graph.

        Returns:
            List of vertices, in insertion order.
        """
        return list(self._adjacency.keys())

    @property
    def edges(self) -> List[E]:
        """Return every edge in the graph.

        Returns:
            List of edges, grouped by source vertex in insertion order.
        """
        edge_list: List[E] = []
        for edges in self._adjacency.values():
            edge_list.extend(edges)
        return edge_list

    def add_vertex(self, vertex: V) -> None:
        """Add a vertex to the graph if it is not already present.

        Args:
            vertex: Vertex to add. Adding an existing vertex is a no-op and
                leaves its edges untouched.
        """
        if vertex not in self._adjacency:
            self._adjacency[vertex] = []

    def add_edge(self, edge: E) -> None:
        """Add a directed edge, registering either endpoint if it is new.

        Args:
            edge: Edge to add. Only the source-to-target direction is created;
                a reverse edge must be added explicitly.
        """
        if edge.source not in self._adjacency:
            self.add_vertex(edge.source)
        if edge.target not in self._adjacency:
            self.add_vertex(edge.target)
        self._adjacency[edge.source].append(edge)

    def get_outgoing_edges(self, vertex: V) -> List[E]:
        """Return the edges leaving a vertex.

        This is the only method the pathfinding algorithms use to traverse the
        graph, which is what lets them work on any `Graph[V, E]`.

        Args:
            vertex: Vertex whose outgoing edges are wanted.

        Returns:
            Copy of the vertex's edge list, empty if the vertex is unknown.
        """
        return list(self._adjacency.get(vertex, []))

    def shortest_path(
        self, start: V, goal: V, algorithm: "PathfindingAlgorithm[V, E]"
    ) -> Tuple[float, List[E]]:
        """Find a path between two vertices using the supplied algorithm.

        Delegates to a pathfinding Strategy; `Graph` has no knowledge of
        algorithm internals (see `pathfinding/algorithms.py`).

        Args:
            start: Vertex to search from.
            goal: Vertex to search for.
            algorithm: Strategy instance that performs the search.

        Returns:
            Tuple of `(total_cost, ordered_edges)`, as defined by the
            algorithm's own `find_path` contract.
        """
        return algorithm.find_path(self, start, goal)
