"""Pathfinding Strategy interface and concrete algorithms.

The interface lives in `strategy.py`; each algorithm has its own module beside
it, the way `geo/` keeps `DistanceFormula` and its implementations apart.
`SearchResult` and the observers report what a search cost, not just what it
found.
"""

from .strategy import PathfindingAlgorithm
from .result import SearchResult
from .observers import SearchObserver, ExpansionTrace
from .dijkstra import Dijkstra
from .bfs import BFS
from .astar import AStar

__all__ = [
    "AStar",
    "BFS",
    "Dijkstra",
    "ExpansionTrace",
    "PathfindingAlgorithm",
    "SearchObserver",
    "SearchResult",
]
