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
              SearchResult, observers        what a search cost, not just what it found
  |
flights/      Airport, Route, FlightPlanner  domain layer composing all of the above
  |
loaders/      CsvRecordLoader family         the CSV -> domain boundary
  |
experiments/  Snapshot, Catalog, Experiment  reproducibility: pinned data and results
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
- **`Snapshot`** / **`Catalog`** / **`Experiment`** (`experiments/`) — the
  reproducibility layer. A `Snapshot` is frozen CSV data verified against a
  manifest of checksums; a `Catalog` narrows it to the scope an experiment
  works in and records what each narrowing cost; an `Experiment` binds a
  directory to one snapshot and records what the run produced. Like every
  other layer, these take directories from their caller and hold no knowledge
  of where a repository keeps its data.

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
other than distance (duration, price, ...), subclass `Edge` — see the
`custom_edge_weight_example` demo in the project repository.

## Extensibility

- **New pathfinding algorithm**: implement `PathfindingAlgorithm.search(self,
  graph, start, goal, observer=None) -> SearchResult[E]` in a new module in
  `pathfinding/` (one algorithm per module, beside `dijkstra.py`, `bfs.py` and
  `astar.py`). `find_path` is inherited — it reads `cost` and `path` off your
  result — so the class works with `Graph.shortest_path`,
  `FlightPlanner.find_shortest_route`, and their `search` counterparts straight
  away. Populate `nodes_expanded` / `nodes_pushed` / `peak_frontier` and call
  the observer's `on_expand` / `on_push` so the benchmark can see your
  algorithm the way it sees the others.
- **New distance formula**: implement `DistanceFormula.calculate(self, a, b)
  -> float` (see `geo/formula.py` for the interface and a list of
  formulas not yet implemented — Spherical Law of Cosines, Equirectangular,
  Karney's algorithm, UTM projection). See the
  `custom_distance_formula_example` demo for a worked example.
- **New edge-weight semantics**: subclass `Edge[V]`, pass whatever you want
  `weight` to represent to `Edge.__init__`. Every `PathfindingAlgorithm`
  works with it unchanged, since they only ever read `edge.weight`
  generically. See the `custom_edge_weight_example` demo.

## Demos

Runnable examples live in `src/demos/` in the project repository, one idea
each. They are deliberately outside this package and are not installed with it:
each imports `flight_planner` the way any outside consumer would, so they
double as a check that the re-exports in `__init__.py` are right.

From a clone:

```bash
uv run python src/demos/dijkstra_example.py
```

The full list, and what each one demonstrates, is in [the demos
documentation](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/demos.md)
— an absolute link, because this file ships inside the wheel, where the rest of
the repository is not on disk.

## Testing

```
uv run pytest tests/flight_planner/
```

One `pytest` test class per production class (`TestVertex`, `TestEdge`,
`TestPoint`, `TestAirport`, `TestRoute`, `TestGraph`, `TestMinHeap`,
`TestHaversine`, `TestVincenty`, `TestMemoized`, `TestDijkstra`, `TestBFS`,
`TestAStar`, `TestFlightPlanner`, `TestAirportLoader`, `TestRouteLoader`,
`TestSearchResult`, `TestSearchObserver`, `TestExpansionTrace`),
covering equality/identity semantics, the Strategy-delegation contracts
(`Graph.shortest_path`, `Point.distance_to`), and each algorithm's
path/cost/unreachable/same-start-goal behavior.

The instrumentation carries its own checks: each algorithm's self-reported
`nodes_expanded` is verified against an independent count taken through
`get_outgoing_edges`, and the project's central claim — A* reaching the same
answer as Dijkstra on fewer expansions — is an executable test rather than a
sentence in the report.

`tests/flight_planner/experiments/` is organized by behavior instead
(`TestIntegrity`, `TestNarrowing`, `TestResolvingTheSnapshot`,
`TestRecording`, ...), because what matters there is what the machinery
guarantees — that a changed byte is caught, that a snapshot path resolves
against its own config rather than the working directory — rather than which
class implements it.
