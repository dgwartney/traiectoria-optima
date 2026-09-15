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
- `flight_planner.viz` — `RouteMap` and its layers: drawing what an experiment
  found. **The only layer that reaches outside the package's declared
  dependencies**, and deliberately not imported here: it needs `folium` and
  `pyproj`, which are notebook concerns in the `notebooks` dependency group
  rather than wheel dependencies. `import flight_planner` stays pandas-only,
  and `from flight_planner.viz import RouteMap` succeeds even without folium —
  what fails is building a map, with a message saying how to fix it.

The names below are re-exported here for convenience, so the common case reads
`from flight_planner import FlightPlanner, Dijkstra`. Runnable examples live in
`src/demos/`, outside the package.
"""

from .core import Edge, Graph, Vertex
from .flights import Airport, FlightPlanner, Route
from .geo import (
    DistanceFormula,
    Haversine,
    Manhattan,
    Memoized,
    Point,
    Vincenty,
    haversine_heuristic,
    manhattan_heuristic,
)
from .pathfinding import (
    COST_HOPS,
    COST_WEIGHT,
    AStar,
    BFS,
    Dijkstra,
    ExpansionTrace,
    PathfindingAlgorithm,
    SearchObserver,
    SearchResult,
)

__all__ = [
    "COST_HOPS",
    "COST_WEIGHT",
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
    "Manhattan",
    "Memoized",
    "PathfindingAlgorithm",
    "Point",
    "Route",
    "SearchObserver",
    "SearchResult",
    "Vertex",
    "Vincenty",
    "haversine_heuristic",
    "manhattan_heuristic",
]
