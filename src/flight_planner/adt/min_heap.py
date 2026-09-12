"""A minimum binary heap used as the priority queue for graph search.

A priority queue implemented with an array-backed binary tree, following
Goodrich, Tamassia & Goldwasser, *Data Structures and Algorithms in Python*,
Ch. 9 (Priority Queues) §9.3. The structure is built here rather than taken
from `heapq`, since the heap itself is the point.

The array holds the tree level by level, so the parent/child links are index
arithmetic rather than pointers: the children of `j` live at `2j + 1` and
`2j + 2`, and its parent at `(j - 1) // 2`. Every entry orders before both of
its children, which puts the minimum at index 0 and makes `peek` a single
array read.

`Dijkstra` and `AStar` (`flight_planner.pathfinding.algorithms`) consume this
class. Each entry carries an insertion sequence number alongside its priority,
so equal priorities come out in the order they went in and the stored items
are never compared against each other. Owning that tie-break here is what
lets the algorithms push a bare vertex instead of maintaining their own
counters.
"""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class _Entry(Generic[T]):
    """One slot in the heap's backing array.

    Ordering is by `(priority, sequence)` alone, so two entries can always be
    compared even when the items they carry cannot be.

    Attributes:
        priority: Ordering key; lower comes out first.
        sequence: Insertion order, breaking ties between equal priorities.
        item: The stored value, never examined for ordering.
    """

    __slots__ = ("priority", "sequence", "item")

    def __init__(self, priority: float, sequence: int, item: T) -> None:
        """Store one item with the keys that order it.

        Args:
            priority: Ordering key; lower comes out first.
            sequence: Insertion order, used only to break ties.
            item: Value to store.
        """
        self.priority = priority
        self.sequence = sequence
        self.item = item

    def __lt__(self, other: "_Entry[T]") -> bool:
        """Order by priority, then by insertion sequence.

        Args:
            other: Entry to compare against.

        Returns:
            `True` if this entry should leave the heap first.
        """
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.sequence < other.sequence


class MinHeap(Generic[T]):
    """A priority queue that always yields the lowest-priority item first.

    Ties are broken by insertion order, so items themselves are never
    compared — they need not be orderable, or even comparable at all.

    Attributes:
        _data: Backing array of `_Entry` slots, maintained in heap order.
        _counter: Next insertion sequence number, used only for tie-breaking.
    """

    def __init__(self) -> None:
        """Create an empty heap."""
        self._data: List[_Entry[T]] = []
        self._counter: int = 0

    @staticmethod
    def _parent(index: int) -> int:
        """Return the array index of a node's parent.

        Args:
            index: Index of the node.

        Returns:
            Index of the parent. Meaningless for index 0, which has none.
        """
        return (index - 1) // 2

    @staticmethod
    def _left(index: int) -> int:
        """Return the array index of a node's left child.

        Args:
            index: Index of the node.

        Returns:
            Index of the left child, which may be past the end of the array.
        """
        return 2 * index + 1

    @staticmethod
    def _right(index: int) -> int:
        """Return the array index of a node's right child.

        Args:
            index: Index of the node.

        Returns:
            Index of the right child, which may be past the end of the array.
        """
        return 2 * index + 2

    def _swap(self, i: int, j: int) -> None:
        """Exchange the entries at two array positions.

        Args:
            i: First index.
            j: Second index.
        """
        self._data[i], self._data[j] = self._data[j], self._data[i]

    def _sift_up(self, index: int) -> None:
        """Move a too-small entry toward the root until the heap holds.

        Walks up the parent chain, which is `O(log n)` because the array is a
        complete tree.

        Args:
            index: Position of the entry that may be out of place.
        """
        while index > 0:
            parent = self._parent(index)
            if not self._data[index] < self._data[parent]:
                break
            self._swap(index, parent)
            index = parent

    def _sift_down(self, index: int) -> None:
        """Move a too-large entry toward the leaves until the heap holds.

        At each step the entry trades places with its smaller child, so the
        child promoted to the vacated slot still orders before its sibling.

        Args:
            index: Position of the entry that may be out of place.
        """
        size = len(self._data)
        while True:
            left = self._left(index)
            if left >= size:
                break

            smallest = left
            right = self._right(index)
            if right < size and self._data[right] < self._data[left]:
                smallest = right

            if not self._data[smallest] < self._data[index]:
                break
            self._swap(index, smallest)
            index = smallest

    def push(self, item: T, priority: float) -> None:
        """Add an item to the heap.

        Appends to the end of the array and sifts it up into place.

        Args:
            item: Value to store. Never compared against other items.
            priority: Ordering key; lower comes out first.
        """
        self._data.append(_Entry(priority, self._counter, item))
        self._counter += 1
        self._sift_up(len(self._data) - 1)

    def pop(self) -> T:
        """Remove and return the item with the lowest priority.

        Moves the last entry into the root so the array stays gap-free, then
        sifts it down into place.

        Returns:
            The lowest-priority item; the earliest-inserted one if several
            share that priority.

        Raises:
            IndexError: If the heap is empty.
        """
        if not self._data:
            raise IndexError("pop from an empty MinHeap")

        self._swap(0, len(self._data) - 1)
        entry = self._data.pop()
        if self._data:
            self._sift_down(0)
        return entry.item

    def peek(self) -> Optional[T]:
        """Return the lowest-priority item without removing it.

        Note the asymmetry with `pop`, which raises on an empty heap. `peek`
        is for asking, so it answers with `None`; `pop` is for taking, and
        taking from nothing is a caller error.

        Returns:
            The item `pop` would return next, or `None` if the heap is empty.
        """
        if not self._data:
            return None
        return self._data[0].item

    def __len__(self) -> int:
        """Return the number of items in the heap.

        Returns:
            Count of items currently stored.
        """
        return len(self._data)

    def __bool__(self) -> bool:
        """Report whether the heap holds anything.

        Returns:
            `True` if at least one item is stored, so a caller can write
            `while heap:` the way the algorithms write `while pq:` today.
        """
        return bool(self._data)

    def __repr__(self) -> str:
        """Return a debugging representation of the heap.

        Returns:
            String of the form `MinHeap(size=3)`.
        """
        return f"MinHeap(size={len(self._data)})"
