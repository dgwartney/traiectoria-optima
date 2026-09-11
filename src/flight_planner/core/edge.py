"""Base graph edge."""

from __future__ import annotations
from typing import Generic, TypeVar

from .vertex import Vertex

V = TypeVar("V", bound=Vertex)


class Edge(Generic[V]):
    """Base weighted, directed Edge class connecting two vertices."""

    def __init__(self, source: V, target: V, weight: float = 1.0) -> None:
        """Create a directed edge from `source` to `target`.

        Args:
            source: Vertex the edge leaves from.
            target: Vertex the edge arrives at.
            weight: Cost of traversing the edge. Interpretation is left to the
                caller — subclasses may define it as distance, duration, price,
                or anything else a pathfinding algorithm should accumulate.
        """
        self._source = source
        self._target = target
        self._weight = float(weight)

    @property
    def source(self) -> V:
        """Return the vertex this edge leaves from.

        Returns:
            The source vertex.
        """
        return self._source

    @property
    def target(self) -> V:
        """Return the vertex this edge arrives at.

        Returns:
            The target vertex.
        """
        return self._target

    @property
    def weight(self) -> float:
        """Return the cost of traversing this edge.

        Returns:
            The edge weight, as supplied at construction.
        """
        return self._weight

    def __hash__(self) -> int:
        """Hash the edge by its endpoints and weight.

        Returns:
            Hash of the `(source, target, weight)` triple.
        """
        return hash((self._source, self._target, self._weight))

    def __eq__(self, other: object) -> bool:
        """Compare two edges by endpoints and weight.

        Args:
            other: Object to compare against.

        Returns:
            `True` if `other` is an `Edge` with the same source, target, and
            weight.
        """
        if isinstance(other, Edge):
            return (
                self._source == other._source
                and self._target == other._target
                and self._weight == other._weight
            )
        return False

    def __repr__(self) -> str:
        """Return a debugging representation showing both endpoints.

        Returns:
            String of the form `Edge(source -> target, weight=...)`.
        """
        return f"Edge({self._source.key!r} -> {self._target.key!r}, weight={self._weight})"
