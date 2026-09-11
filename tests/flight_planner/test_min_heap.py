import math

import pytest

from flight_planner.adt import MinHeap


class Incomparable:
    """A payload that raises if anything tries to order it.

    Guards the heap's central promise: ties are broken by insertion order, so
    stored items are never compared against each other.
    """

    def __init__(self, name):
        self.name = name

    def __lt__(self, other):
        raise AssertionError("MinHeap compared two stored items")

    def __gt__(self, other):
        raise AssertionError("MinHeap compared two stored items")


class TestMinHeap:
    def test_new_heap_is_empty(self):
        heap = MinHeap()
        assert len(heap) == 0
        assert not heap

    def test_peek_on_empty_returns_none(self):
        assert MinHeap().peek() is None

    def test_pop_on_empty_raises(self):
        with pytest.raises(IndexError):
            MinHeap().pop()

    def test_push_then_pop_returns_the_item(self):
        heap = MinHeap()
        heap.push("only", 1.0)
        assert heap.pop() == "only"

    def test_pops_in_priority_order_not_insertion_order(self):
        heap = MinHeap()
        for item, priority in [("c", 3.0), ("a", 1.0), ("b", 2.0)]:
            heap.push(item, priority)
        assert [heap.pop() for _ in range(3)] == ["a", "b", "c"]

    def test_ties_break_by_insertion_order(self):
        # Deliberately inserted against alphabetical order: if the heap ever
        # fell back to comparing the items themselves, this would come out
        # sorted instead of FIFO, and the assertion would catch it.
        heap = MinHeap()
        for name in ["zulu", "alpha", "mike"]:
            heap.push(name, 5.0)
        assert [heap.pop() for _ in range(3)] == ["zulu", "alpha", "mike"]

    def test_items_are_never_compared(self):
        heap = MinHeap()
        for name in ["x", "y", "z"]:
            heap.push(Incomparable(name), 0.0)
        assert [heap.pop().name for _ in range(3)] == ["x", "y", "z"]

    def test_peek_does_not_remove(self):
        heap = MinHeap()
        heap.push("a", 1.0)
        assert heap.peek() == "a"
        assert len(heap) == 1
        assert heap.pop() == "a"

    def test_len_tracks_pushes_and_pops(self):
        heap = MinHeap()
        assert len(heap) == 0
        heap.push("a", 1.0)
        heap.push("b", 2.0)
        assert len(heap) == 2
        heap.pop()
        assert len(heap) == 1

    def test_truthiness_follows_emptiness(self):
        heap = MinHeap()
        assert not heap
        heap.push("a", 1.0)
        assert heap
        heap.pop()
        assert not heap

    def test_interleaved_push_and_pop_keeps_order(self):
        heap = MinHeap()
        heap.push("b", 2.0)
        heap.push("d", 4.0)
        assert heap.pop() == "b"
        heap.push("a", 1.0)
        heap.push("c", 3.0)
        assert [heap.pop() for _ in range(3)] == ["a", "c", "d"]

    def test_handles_negative_and_infinite_priorities(self):
        heap = MinHeap()
        heap.push("inf", math.inf)
        heap.push("zero", 0.0)
        heap.push("negative", -10.0)
        assert [heap.pop() for _ in range(3)] == ["negative", "zero", "inf"]

    def test_duplicate_items_are_kept_separately(self):
        heap = MinHeap()
        heap.push("same", 2.0)
        heap.push("same", 1.0)
        assert len(heap) == 2
        assert [heap.pop() for _ in range(2)] == ["same", "same"]

    def test_repr_reports_size(self):
        heap = MinHeap()
        assert repr(heap) == "MinHeap(size=0)"
        heap.push("a", 1.0)
        assert repr(heap) == "MinHeap(size=1)"
