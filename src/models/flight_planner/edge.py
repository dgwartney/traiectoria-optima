"""Base graph edge."""

from __future__ import annotations
from typing import Generic, TypeVar

from vertex import Vertex

V = TypeVar("V", bound=Vertex)


class Edge(Generic[V]):
    """Base weighted, directed Edge class connecting two vertices."""

    def __init__(self, source: V, target: V, weight: float = 1.0) -> None:
        self._source = source
        self._target = target
        self._weight = float(weight)

    @property
    def source(self) -> V:
        return self._source

    @property
    def target(self) -> V:
        return self._target

    @property
    def weight(self) -> float:
        return self._weight

    def __hash__(self) -> int:
        return hash((self._source, self._target, self._weight))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Edge):
            return (
                self._source == other._source
                and self._target == other._target
                and self._weight == other._weight
            )
        return False

    def __repr__(self) -> str:
        return f"Edge({self._source.key!r} -> {self._target.key!r}, weight={self._weight})"
