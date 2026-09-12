import ast
import inspect
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

class TestBuiltFromScratch:
    """The deliverable is the structure itself, not a wrapper around `heapq`."""

    def test_module_does_not_import_heapq(self):
        # Checked against the import statements rather than the raw text, so
        # the module stays free to name `heapq` in prose and say why it is
        # not used.
        import flight_planner.adt.min_heap as module

        tree = ast.parse(inspect.getsource(module))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        assert "heapq" not in imported

    def test_backing_array_satisfies_the_heap_invariant(self):
        # Every parent must order before both children. A wrapper hides its
        # array; an array-backed heap can be asked about it directly.
        heap = MinHeap()
        for priority in [9.0, 4.0, 7.0, 1.0, 8.0, 2.0, 6.0, 3.0, 5.0, 0.0]:
            heap.push(f"v{priority}", priority)

        data = heap._data
        for child in range(1, len(data)):
            parent = (child - 1) // 2
            assert not (data[child] < data[parent]), (
                f"heap invariant violated at index {child}"
            )


class TestDeepAndWideHeaps:
    """The other cases here use at most three items, which never sifts far."""

    def test_pops_a_deep_heap_in_full_priority_order(self):
        # 100 items is seven levels, so a sift that stops one level early
        # shows up here and nowhere else in this file.
        heap = MinHeap()
        priorities = [(i * 37) % 100 for i in range(100)]
        for i, priority in enumerate(priorities):
            heap.push(i, float(priority))

        popped = [heap.pop() for _ in range(100)]
        assert [priorities[i] for i in popped] == sorted(priorities)

    def test_ties_stay_fifo_across_a_deep_heap(self):
        # Every item shares one priority, so ordering is decided purely by
        # the tie-break, through many sift operations.
        heap = MinHeap()
        for i in range(64):
            heap.push(i, 1.0)

        assert [heap.pop() for _ in range(64)] == list(range(64))

    def test_interleaved_push_and_pop_on_a_deep_heap(self):
        heap = MinHeap()
        for i in range(50):
            heap.push(f"a{i}", float(50 - i))
        first_half = [heap.pop() for _ in range(25)]
        for i in range(25):
            heap.push(f"b{i}", float(i))
        rest = [heap.pop() for _ in range(len(heap))]

        assert first_half == [f"a{i}" for i in range(49, 24, -1)]
        assert rest == [f"b{i}" for i in range(25)] + [f"a{i}" for i in range(24, -1, -1)]
