"""Base graph vertex."""

from __future__ import annotations
from typing import Any


class Vertex:
    """Base Vertex class representing a node in a graph."""

    def __init__(self, key: Any) -> None:
        self._key = key

    @property
    def key(self) -> Any:
        return self._key

    def __hash__(self) -> int:
        return hash(self._key)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Vertex):
            return self._key == other._key
        return False

    def __repr__(self) -> str:
        return f"Vertex(key={self._key!r})"
