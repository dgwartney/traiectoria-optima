"""Adjacency-list graph exercise.

An undirected weighted graph stored as an adjacency list, where each `Vertex`
holds a mapping of its neighbours to edge weights. Kept as a study exercise
alongside the textbook it comes from; the project's own graph implementation
lives in `src/flight_planner/`.

Adapted from Narasimha Karumanchi, *Data Structures And Algorithmic Thinking
With Python* (CareerMonk Publications, 2014). Provided without warranty of any
kind, express or implied.
"""

from __future__ import annotations

import collections.abc
import math
from typing import Any, Hashable


class Vertex:
    """A graph node and the weighted edges leaving it."""

    def __init__(self, vertex_id: Hashable, label: str = "") -> None:
        """Create an isolated vertex with no adjacent neighbours.

        Args:
            vertex_id: Value identifying this vertex within its graph. Any
                hashable key works — `Graph` uses the value passed to
                `add_vertex`, which need not be an integer.
            label: Human-readable name for the vertex.
        """
        self._id: Hashable = vertex_id
        self._adjacent: dict[Vertex, float] = {}
        self._label: str = label

        # Set distance to infinity for all nodes
        self._distance: float = math.inf

        # Mark all nodes unvisited
        self._visited: bool = False

        # Predecessor
        self._previous: Vertex | None = None

    def add_adjacent(self, adjacent_vertex: Vertex, weight: float = 0) -> None:
        """Record an edge from this vertex to a neighbour.

        Args:
            adjacent_vertex: Vertex at the far end of the edge.
            weight: Cost of traversing the edge. Re-adding an existing
                neighbour overwrites its weight.
        """
        self._adjacent[adjacent_vertex] = weight

    def get_adjacent(self) -> collections.abc.KeysView[Vertex]:
        """Return the neighbours reachable from this vertex.

        Returns:
            View of the adjacent vertices.
        """
        return self._adjacent.keys()

    @property
    def id(self) -> Hashable:
        """Return the value identifying this vertex.

        Returns:
            The identity key supplied at construction.
        """
        return self._id

    @id.setter
    def id(self, vertex_id: Hashable) -> None:
        """Set the value identifying this vertex.

        Args:
            vertex_id: New identity key. The owning `Graph` indexes vertices
                by their original key and is not updated by this setter.
        """
        self._id = vertex_id

    def get_weight(self, adjacent_vertex: Vertex) -> float:
        """Return the weight of the edge to a neighbour.

        Args:
            adjacent_vertex: Vertex at the far end of the edge.

        Returns:
            The edge weight.

        Raises:
            KeyError: If `adjacent_vertex` is not a neighbour of this vertex.
        """
        return self._adjacent[adjacent_vertex]

    @property
    def distance(self) -> float:
        """Return the working distance used by shortest-path traversals.

        Returns:
            Distance from whichever vertex a traversal started at, or
            `math.inf` if it has not been reached.
        """
        return self._distance

    @distance.setter
    def distance(self, distance: float) -> None:
        """Set the working distance for this vertex.

        Args:
            distance: Distance from the traversal's start vertex.
        """
        self._distance = distance

    @property
    def previous(self) -> Vertex | None:
        """Return the predecessor recorded by a traversal.

        Returns:
            The vertex this one was reached from, or `None` if unset.
        """
        return self._previous

    @previous.setter
    def previous(self, previous: Vertex | None) -> None:
        """Set the predecessor for path reconstruction.

        Args:
            previous: Vertex this one was reached from.
        """
        self._previous = previous

    @property
    def visited(self) -> bool:
        """Report whether a traversal has already processed this vertex.

        Returns:
            `True` once a traversal has marked it visited.
        """
        return self._visited

    @visited.setter
    def visited(self, visited: bool) -> None:
        """Mark this vertex visited or unvisited.

        Args:
            visited: Whether the vertex has been processed.
        """
        self._visited = visited

    def __str__(self) -> str:
        """Return the vertex's id alongside its neighbours' ids.

        Returns:
            String of the form `a adjacent: ['b', 'c']`.
        """
        return str(self.id) + ' adjacent: ' + str([x.id for x in self._adjacent])


class Graph:
    """An undirected weighted graph held as a mapping of key to `Vertex`."""

    def __init__(self) -> None:
        """Create an empty graph."""
        self._vertices: dict[Hashable, Vertex] = {}

    def __iter__(self) -> collections.abc.Iterator[Vertex]:
        """Iterate over the graph's vertices.

        Returns:
            Iterator over `Vertex` objects, in insertion order.
        """
        return iter(self._vertices.values())

    def add_vertex(self, node: Hashable) -> Vertex:
        """Add a vertex to the graph under the given key.

        Args:
            node: Key identifying the vertex. Reusing an existing key replaces
                that vertex, discarding its edges.

        Returns:
            The newly created `Vertex`.
        """
        vertex = Vertex(node)
        self._vertices[node] = vertex
        return vertex

    def __setitem__(self, node: Hashable, _value: Any) -> None:
        """Add a vertex via subscript assignment, ignoring the value.

        Args:
            node: Key identifying the vertex to add.
            _value: Ignored; only the key is used.
        """
        self.add_vertex(node)

    def __len__(self) -> int:
        """Return the number of vertices in the graph.

        Returns:
            Count of vertices.
        """
        return len(self._vertices)

    def __getitem__(self, node: Hashable) -> Vertex | None:
        """Look up a vertex by key.

        Args:
            node: Key identifying the vertex.

        Returns:
            The matching `Vertex`, or `None` if the key is unknown.
        """
        return self._vertices.get(node)

    def add_edge(self, frm: Hashable, to: Hashable, cost: float = 0) -> None:
        """Connect two vertices, adding either if it is not already present.

        The edge is undirected: it is recorded in both directions. For a
        directed graph, omit the second `add_adjacent` call.

        Args:
            frm: Key of the vertex at one end.
            to: Key of the vertex at the other end.
            cost: Weight of the edge.
        """
        if frm not in self._vertices:
            self.add_vertex(frm)
        if to not in self._vertices:
            self.add_vertex(to)

        self._vertices[frm].add_adjacent(self._vertices[to], cost)
        # For directed graph do not add this
        self._vertices[to].add_adjacent(self._vertices[frm], cost)

    def get_vertices(self) -> collections.abc.KeysView[Hashable]:
        """Return the keys of every vertex in the graph.

        Returns:
            View of the vertex keys.
        """
        return self._vertices.keys()

    def get_edges(self) -> list[tuple[Hashable, Hashable, float]]:
        """List every edge as a triple of endpoint ids and weight.

        Because the graph is undirected, each edge appears twice — once in
        each direction.

        Returns:
            List of `(from_id, to_id, weight)` triples.
        """
        edges = []
        for v in self:
            for w in v.get_adjacent():
                edges.append((v.id, w.id, v.get_weight(w)))
        return edges


if __name__ == '__main__':

    G = Graph()
    G['a'] = 'a'
    G.add_vertex('b')
    G.add_vertex('c')
    G.add_vertex('d')
    G.add_vertex('e')
    G.add_edge('a', 'b', 4)
    G.add_edge('a', 'c', 1)
    G.add_edge('c', 'b', 2)
    G.add_edge('b', 'e', 4)
    G.add_edge('c', 'd', 4)
    G.add_edge('d', 'e', 4)

    print('Graph data:')
    print(G.get_edges())
