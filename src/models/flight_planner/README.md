# Flight Planner

A small example flight-network model that demonstrates building a generic,
reusable graph library and layering a specific domain (airports and flight
routes) on top of it, using **composition over inheritance**.

## Design overview

The module is layered from generic to specific:

```
Vertex, Edge, Graph[V, E]        generic weighted-graph core
       |
Point, DistanceFormula           geography, independent of graphs
       |
PathfindingAlgorithm family      Strategy pattern, generic over any Graph[V, E]
       |
Airport, Route, FlightPlanner    domain layer composing all of the above
```

- **`Vertex`** / **`Edge`** / **`Graph[V, E]`** (`vertex.py`, `edge.py`,
  `graph.py`) — a minimal generic weighted, directed graph. `Graph` knows
  nothing about airports, distances, or algorithms; it just stores
  vertices/edges and exposes `get_outgoing_edges`.
- **`Point`** / **`DistanceFormula`** (`point.py`, `distance/`) — a
  geographic coordinate and pluggable formulas (`Haversine`, `Vincenty`) for
  computing distance between two `Point`s. Independent of `Graph` entirely.
- **`PathfindingAlgorithm`** family (`pathfinding/algorithms.py`) —
  `Dijkstra`, `BFS`, `AStar`. Each operates purely on the generic
  `Graph[V, E]` interface (`get_outgoing_edges`, `edge.source/target/weight`)
  and works on *any* graph, not just flight networks.
- **`Airport`** / **`Route`** / **`FlightPlanner`** (`airport.py`,
  `route.py`, `flight_planner.py`) — the domain layer. `Airport(Vertex,
  Point)` is both a graph node and a geographic location. `Route(Edge[Airport])`
  is a flight leg. `FlightPlanner(Graph[Airport, Route])` adds IATA-code
  lookup and a `find_shortest_route` convenience wrapper.

## Why composition over inheritance

Earlier iterations of this design considered making `FlightPlanner` (or
`Graph`) *derive from* Dijkstra's algorithm directly. That doesn't generalize:
every graph would be forced to carry the method surface of every algorithm
ever added, and you couldn't choose "no algorithm" or swap one at runtime.

Instead:
- `Graph.shortest_path(start, goal, algorithm)` takes a `PathfindingAlgorithm`
  **instance** and delegates to it — the algorithm is passed in, not derived
  from.
- `Point.distance_to(other, formula)` takes a `DistanceFormula` **instance**
  the same way.
- `AStar(heuristic)` takes any `Callable[[V, V], float]` as its heuristic —
  it doesn't need to know it's `Point.distance_to` versus anything else.

This is the Strategy pattern: behavior is a value you pass around, not a
base class you extend. Adding a new algorithm or formula never requires
touching `Graph`, `Point`, or any existing algorithm/formula class.

`DistanceFormula` and `Edge.weight` are two separate, unrelated axes — don't
conflate them. `DistanceFormula` only ever estimates straight-line distance
between two `Point`s, used to guide `AStar`'s heuristic. `Edge.weight`
(`Route.distance_km`) is the real, accumulated path cost every algorithm
sums along the way, and is supplied as domain data (real flight distance can
differ from great-circle distance). If you want edges weighted by something
other than distance (duration, price, ...), subclass `Edge` — see
`examples/custom_edge_weight_example.py`.

## Extensibility

- **New pathfinding algorithm**: implement `PathfindingAlgorithm.find_path(self,
  graph, start, goal) -> Tuple[float, List[E]]` in a new class in
  `pathfinding/algorithms.py` (or your own module). It automatically works
  with `Graph.shortest_path` and `FlightPlanner.find_shortest_route`.
- **New distance formula**: implement `DistanceFormula.calculate(self, a, b)
  -> float` (see `distance/formula.py` for the interface and a list of
  formulas not yet implemented — Spherical Law of Cosines, Equirectangular,
  Karney's algorithm, UTM projection). See
  `examples/custom_distance_formula_example.py` for a worked example.
- **New edge-weight semantics**: subclass `Edge[V]`, pass whatever you want
  `weight` to represent to `Edge.__init__`. Every `PathfindingAlgorithm`
  works with it unchanged, since they only ever read `edge.weight`
  generically. See `examples/custom_edge_weight_example.py`.

## Examples

Run any of these from this directory (`src/models/flight_planner/`):

| File | Demonstrates |
|---|---|
| `python -m examples.dijkstra_example` | Default weighted-shortest-path search |
| `python -m examples.bfs_example` | Fewest-hops search, contrasted with Dijkstra |
| `python -m examples.astar_example` | A* guided by `Point.distance_to` as an admissible heuristic |
| `python -m examples.custom_distance_formula_example` | Adding a new `DistanceFormula` (`Equirectangular`) without touching `Point`/`Haversine`/`Vincenty` |
| `python -m examples.custom_edge_weight_example` | Adding a new `Edge` subclass weighted by duration instead of distance |

`main.py` (`python main.py`) is a larger end-to-end demo combining all three
algorithms and both `DistanceFormula` implementations over a small flight
network.

## Testing

```
pytest src/models/flight_planner/tests/
```

One `pytest` test class per production class (`TestVertex`, `TestEdge`,
`TestPoint`, `TestAirport`, `TestRoute`, `TestGraph`, `TestHaversine`,
`TestVincenty`, `TestDijkstra`, `TestBFS`, `TestAStar`,
`TestFlightPlanner`), covering equality/identity semantics, the
Strategy-delegation contracts (`Graph.shortest_path`, `Point.distance_to`),
and each algorithm's path/cost/unreachable/same-start-goal behavior.
