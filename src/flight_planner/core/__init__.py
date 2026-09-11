"""Generic weighted-graph core.

`Vertex`, `Edge` and `Graph` know nothing about geography, airports, or
pathfinding algorithms. They are the reusable layer every other subpackage is
built on top of.
"""

from .edge import Edge
from .graph import Graph
from .vertex import Vertex

__all__ = ["Edge", "Graph", "Vertex"]
