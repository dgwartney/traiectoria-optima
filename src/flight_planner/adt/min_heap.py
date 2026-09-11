"""A minimum binary heap used as the priority queue for graph search.

`Dijkstra` and `AStar` (`flight_planner.pathfinding.algorithms`) currently call
`heapq` directly, pushing `(priority, counter, vertex)` tuples where `counter`
is a monotonically increasing integer that exists only to keep the heap from
ever comparing two vertices when their priorities tie. Both algorithms
maintain that counter themselves, identically. Owning the tie-break here is
the point of this class: callers push an item and a priority, and never see
the sequencing.

Nothing imports this yet -- the algorithms still use `heapq` directly, and
switching them over is a separate change.
"""

from __future__ import annotations

import heapq
from typing import Generic, List, Optional, Tuple, TypeVar

T = TypeVar("T")


class MinHeap(Generic[T]):
    """A priority queue that always yields the lowest-priority item first.

    Ties are broken by insertion order, so items themselves are never
    compared — they need not be orderable, or even comparable at all.

    Attributes:
        _entries: Backing array of `(priority, sequence, item)` triples,
            maintained in heap order.
        _counter: Next insertion sequence number, used only for tie-breaking.
    """

    def __init__(self) -> None:
        """Create an empty heap."""
        self._entries: List[Tuple[float, int, T]] = []
        self._counter: int = 0

    def push(self, item: T, priority: float) -> None:
        """Add an item to the heap.

        Args:
            item: Value to store. Never compared against other items.
            priority: Ordering key; lower comes out first.
        """
        heapq.heappush(self._entries, (priority, self._counter, item))
        self._counter += 1

    def pop(self) -> T:
        """Remove and return the item with the lowest priority.

        Returns:
            The lowest-priority item; the earliest-inserted one if several
            share that priority.

        Raises:
            IndexError: If the heap is empty.
        """
        if not self._entries:
            raise IndexError("pop from an empty MinHeap")
        return heapq.heappop(self._entries)[2]

    def peek(self) -> Optional[T]:
        """Return the lowest-priority item without removing it.

        Note the asymmetry with `pop`, which raises on an empty heap. `peek`
        is for asking, so it answers with `None`; `pop` is for taking, and
        taking from nothing is a caller error.

        Returns:
            The item `pop` would return next, or `None` if the heap is empty.
        """
        if not self._entries:
            return None
        return self._entries[0][2]

    def __len__(self) -> int:
        """Return the number of items in the heap.

        Returns:
            Count of items currently stored.
        """
        return len(self._entries)

    def __bool__(self) -> bool:
        """Report whether the heap holds anything.

        Returns:
            `True` if at least one item is stored, so a caller can write
            `while heap:` the way the algorithms write `while pq:` today.
        """
        return bool(self._entries)

    def __repr__(self) -> str:
        """Return a debugging representation of the heap.

        Returns:
            String of the form `MinHeap(size=3)`.
        """
        return f"MinHeap(size={len(self._entries)})"
