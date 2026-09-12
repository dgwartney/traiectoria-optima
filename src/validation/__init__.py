"""Validating `flight_planner`'s algorithms against an independent oracle.

This package is **not** part of the wheel. `pyproject.toml` ships only
`src/flight_planner`, whose runtime contract is "imports pandas and nothing
else"; NetworkX is a `dev`-group dependency and validation is the
repository's concern, not the package's. The hand-written `Graph`, `MinHeap`,
`BFS`, `Dijkstra` and `AStar` are the deliverable — nothing here may ever
stand in for them.

What lives here, and why each piece is a class:

- `NetworkXMirror` — the same graph, as NetworkX sees it. Generic over any
  `Graph[V, E]`, so the reference engines below work on a four-vertex test
  fixture as readily as on the world network.
- `NetworkXView` — a mirror plus the flights-layer extras: airport
  coordinates as node attributes, flight numbers as edge keys, and the
  great-circle heuristic in the signature NetworkX's A* expects. It holds the
  keys-versus-vertices bridge so no caller re-derives it.
- `NetworkXDijkstra`, `NetworkXBFS`, `NetworkXAStar` — NetworkX behind
  `PathfindingAlgorithm`, so the *engine* becomes a parameter of an experiment
  exactly as `Dijkstra()` versus `BFS()` already is.
- `ReopeningAStar` — A* without a closed set, which is optimal for any
  admissible heuristic rather than only a consistent one.
- `RandomGraphPair`, `InconsistentHeuristic` — randomized differential
  testing: one graph built for both libraries, and a heuristic that is
  admissible by construction and deliberately not consistent.

See [`docs/networkx-validation.md`](../../docs/networkx-validation.md) for the
options this implements and the measurements behind them.
"""

from .engines import NetworkXAStar, NetworkXBFS, NetworkXDijkstra
from .oracle import NetworkXMirror, NetworkXView
from .random_graphs import InconsistentHeuristic, RandomGraphPair
from .reopening import ReopeningAStar

__all__ = [
    "InconsistentHeuristic",
    "NetworkXAStar",
    "NetworkXBFS",
    "NetworkXDijkstra",
    "NetworkXMirror",
    "NetworkXView",
    "RandomGraphPair",
    "ReopeningAStar",
]
