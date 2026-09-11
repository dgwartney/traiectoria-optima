# Flight Planner

A small example flight-network model that demonstrates building a generic,
reusable graph library and layering a specific domain (airports and flight
routes) on top of it, using **composition over inheritance**.

## Design overview

The module is layered from generic to specific:

```
core/         Vertex, Edge, Graph[V, E]      generic weighted-graph core
  |
geo/          Point, DistanceFormula         geography, independent of graphs
  |
pathfinding/  PathfindingAlgorithm family    Strategy, generic over any Graph[V, E]
  |
flights/      Airport, Route, FlightPlanner  domain layer composing all of the above
  |
loaders/      CsvRecordLoader family         the CSV -> domain boundary
```

- **`Vertex`** / **`Edge`** / **`Graph[V, E]`** (`core/`) — a minimal generic weighted, directed graph. `Graph` knows
  nothing about airports, distances, or algorithms; it just stores
  vertices/edges and exposes `get_outgoing_edges`.
- **`Point`** / **`DistanceFormula`** (`geo/`) — a
  geographic coordinate and pluggable formulas (`Haversine`, `Vincenty`) for
  computing distance between two `Point`s. Independent of `Graph` entirely.
- **`PathfindingAlgorithm`** family (`pathfinding/algorithms.py`) —
  `Dijkstra`, `BFS`, `AStar`. Each operates purely on the generic
  `Graph[V, E]` interface (`get_outgoing_edges`, `edge.source/target/weight`)
  and works on *any* graph, not just flight networks.
- **`Airport`** / **`Route`** / **`FlightPlanner`** (`flights/airport.py`,
  `flights/route.py`, `flights/planner.py`) — the domain layer. `Airport(Vertex,
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
`src/demos/custom_edge_weight_example.py`.

## Extensibility

- **New pathfinding algorithm**: implement `PathfindingAlgorithm.find_path(self,
  graph, start, goal) -> Tuple[float, List[E]]` in a new class in
  `pathfinding/algorithms.py` (or your own module). It automatically works
  with `Graph.shortest_path` and `FlightPlanner.find_shortest_route`.
- **New distance formula**: implement `DistanceFormula.calculate(self, a, b)
  -> float` (see `geo/formula.py` for the interface and a list of
  formulas not yet implemented — Spherical Law of Cosines, Equirectangular,
  Karney's algorithm, UTM projection). See
  `src/demos/custom_distance_formula_example.py` for a worked example.
- **New edge-weight semantics**: subclass `Edge[V]`, pass whatever you want
  `weight` to represent to `Edge.__init__`. Every `PathfindingAlgorithm`
  works with it unchanged, since they only ever read `edge.weight`
  generically. See `src/demos/custom_edge_weight_example.py`.

## Demos

The demos live in `src/demos/`, outside this package — they are illustrative
scripts, not part of the public API, and are not installed with it. Each is a
plain script that imports `flight_planner` the way any consumer would, so they
double as a check that the re-exports in `__init__.py` are right.

Run any of them from anywhere:

```bash
uv run python src/demos/dijkstra_example.py
```

| File | Demonstrates |
|---|---|
| `dijkstra_example.py` | Default weighted-shortest-path search |
| `bfs_example.py` | Fewest-hops search, contrasted with Dijkstra |
| `astar_example.py` | A* guided by `Point.distance_to` as an admissible heuristic |
| `custom_distance_formula_example.py` | Adding a new `DistanceFormula` (`Equirectangular`) without touching `Point`/`Haversine`/`Vincenty` |
| `custom_edge_weight_example.py` | Adding a new `Edge` subclass weighted by duration instead of distance |
| `end_to_end_example.py` | All three algorithms and both `DistanceFormula`s over one six-airport network |
| `loader_example.py` | Building a planner from the processed CSV files instead of by hand |

## Testing

```
uv run pytest tests/flight_planner/
```

One `pytest` test class per production class (`TestVertex`, `TestEdge`,
`TestPoint`, `TestAirport`, `TestRoute`, `TestGraph`, `TestHaversine`,
`TestVincenty`, `TestDijkstra`, `TestBFS`, `TestAStar`,
`TestFlightPlanner`), covering equality/identity semantics, the
Strategy-delegation contracts (`Graph.shortest_path`, `Point.distance_to`),
and each algorithm's path/cost/unreachable/same-start-goal behavior.
