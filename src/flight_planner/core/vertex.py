"""Base graph vertex."""

from __future__ import annotations
from typing import Any


class Vertex:
    """Base Vertex class representing a node in a graph."""

    def __init__(self, key: Any) -> None:
        """Create a vertex identified by `key`.

        Args:
            key: Value establishing this vertex's identity. Must be hashable;
                two vertices are equal exactly when their keys are equal.
        """
        self._key = key

    @property
    def key(self) -> Any:
        """Return the value identifying this vertex.

        Returns:
            The identity key supplied at construction.
        """
        return self._key

    def __hash__(self) -> int:
        """Hash the vertex by its key, so it can be used as a dict key.

        Returns:
            Hash of the identity key.
        """
        return hash(self._key)

    def __eq__(self, other: object) -> bool:
        """Compare two vertices by identity key.

        Args:
            other: Object to compare against.

        Returns:
            `True` if `other` is a `Vertex` with an equal key.
        """
        if isinstance(other, Vertex):
            return self._key == other._key
        return False

    def __repr__(self) -> str:
        """Return a debugging representation showing the key.

        Returns:
            String of the form `Vertex(key=...)`.
        """
        return f"Vertex(key={self._key!r})"
