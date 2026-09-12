"""Pathfinding Strategy interface and concrete algorithms.

The interface lives in `strategy.py`; each algorithm has its own module beside
it, the way `geo/` keeps `DistanceFormula` and its implementations apart.
"""

from .strategy import PathfindingAlgorithm
from .dijkstra import Dijkstra
from .bfs import BFS
from .astar import AStar

__all__ = ["PathfindingAlgorithm", "Dijkstra", "BFS", "AStar"]
