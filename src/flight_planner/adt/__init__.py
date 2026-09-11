"""Abstract data types backing the algorithms.

Internal infrastructure rather than part of the flight-planning API: these are
the structures the pathfinding strategies are built on, exposed here so they
can be tested and swapped independently.
"""

from .min_heap import MinHeap

__all__ = ["MinHeap"]
