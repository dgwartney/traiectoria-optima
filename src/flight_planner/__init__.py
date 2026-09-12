"""A layered flight-network model built on a reusable weighted-graph core.

The package is layered from generic to specific, and each layer is usable
without the ones above it:

- `flight_planner.core` — `Vertex`, `Edge`, `Graph`: a generic weighted,
  directed graph that knows nothing about airports or algorithms.
- `flight_planner.geo` — `Point` and the `DistanceFormula` family: geography,
  independent of graphs entirely.
- `flight_planner.pathfinding` — `Dijkstra`, `BFS`, `AStar`: Strategy
  implementations generic over any `Graph[V, E]`.
- `flight_planner.flights` — `Airport`, `Route`, `FlightPlanner`: the domain
  layer composing all of the above.
- `flight_planner.loaders` — building a planner from the processed CSV files.

The names below are re-exported here for convenience, so the common case reads
`from flight_planner import FlightPlanner, Dijkstra`. Runnable examples live in
`src/demos/`, outside the package.
"""

from .core import Edge, Graph, Vertex
from .flights import Airport, FlightPlanner, Route
from .geo import DistanceFormula, Haversine, Memoized, Point, Vincenty
from .pathfinding import (
    AStar,
    BFS,
    Dijkstra,
    ExpansionTrace,
    PathfindingAlgorithm,
    SearchObserver,
    SearchResult,
)

__all__ = [
    "AStar",
    "Airport",
    "BFS",
    "DistanceFormula",
    "Dijkstra",
    "Edge",
    "ExpansionTrace",
    "FlightPlanner",
    "Graph",
    "Haversine",
    "Memoized",
    "PathfindingAlgorithm",
    "Point",
    "Route",
    "SearchObserver",
    "SearchResult",
    "Vertex",
    "Vincenty",
]
