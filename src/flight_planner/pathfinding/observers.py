"""Hooks for watching a search run, without changing what it does.

`SearchResult` answers the questions known in advance — how many nodes, how
big the frontier got. An observer answers the ones a later experiment invents:
the order vertices were reached in, how cost accumulated, where the search
spent its time. That is the same bargain the experiments package makes with
snapshots — ask a new question of fixed data without disturbing it.

Observation is free in practice: a per-expansion call measured at 1.00x on the
94-airport US network.
"""

from __future__ import annotations

from typing import Generic, List, Tuple, TypeVar

from ..core.vertex import Vertex

V = TypeVar("V", bound=Vertex)


class SearchObserver(Generic[V]):
    """Base class for watching a search; every hook defaults to doing nothing.

    Subclass and override only the hooks you care about. The base class is
    itself usable as a null observer.
    """

    def on_expand(self, vertex: V, cost_so_far: float) -> None:
        """Called when a vertex's outgoing edges are about to be examined.

        Fires once per expansion, in expansion order, and never for the goal —
        every algorithm stops on reaching it.

        Args:
            vertex: The vertex being expanded.
            cost_so_far: Cost of the best known route to it. Distance for the
                weighted algorithms; hop depth for `BFS`.
        """

    def on_push(self, vertex: V, priority: float) -> None:
        """Called when a vertex is placed on the frontier.

        Fires again each time a vertex is re-queued, so the call count is the
        result's `nodes_pushed`.

        Args:
            vertex: The vertex being queued.
            priority: Its ordering key — tentative distance for `Dijkstra`,
                `f = g + h` for `AStar`, hop depth for `BFS`, whose FIFO queue
                has no explicit priority.
        """


class ExpansionTrace(SearchObserver[V]):
    """Records what a search looked at, in the order it looked.

    The shape of a search, rather than its size: plot the expansions of
    Dijkstra and A* over the same query and one spreads outward in all
    directions while the other drives at the goal.

    Attributes:
        expansions: `(vertex, cost_so_far)` in expansion order.
        pushes: `(vertex, priority)` in queueing order.
    """

    def __init__(self) -> None:
        """Create an empty trace."""
        self.expansions: List[Tuple[V, float]] = []
        self.pushes: List[Tuple[V, float]] = []

    def on_expand(self, vertex: V, cost_so_far: float) -> None:
        """Record an expansion.

        Args:
            vertex: The vertex being expanded.
            cost_so_far: Cost of the best known route to it.
        """
        self.expansions.append((vertex, cost_so_far))

    def on_push(self, vertex: V, priority: float) -> None:
        """Record a queueing.

        Args:
            vertex: The vertex being queued.
            priority: Its ordering key.
        """
        self.pushes.append((vertex, priority))

    @property
    def order(self) -> List[V]:
        """Return just the expanded vertices, in order.

        Returns:
            The vertices from `expansions`, without their costs.
        """
        return [vertex for vertex, _ in self.expansions]

    def __repr__(self) -> str:
        """Return a debugging representation of the trace.

        Returns:
            String of the form `ExpansionTrace(expanded=12, pushed=30)`.
        """
        return f"ExpansionTrace(expanded={len(self.expansions)}, pushed={len(self.pushes)})"
