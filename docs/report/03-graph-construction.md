# 3. Graph Construction and Data Structures

The rubric's first stage asks for a correct graph built from scratch. This
chapter is the argument for how it is built; the class-by-class reference is
[Appendix B](13-appendix-b-data-structures.md).

Two claims are worth separating, because only the first is about airports.
**The graph is a general-purpose weighted digraph that has never heard of an
airport.** The flight network is one thing you can put in it. Everything in
this chapter follows from having drawn that line, and the strongest evidence
that it is drawn in the right place is that the line is visible from the
outside.

## 3.1 Four layers, and why the line is where it is

The obvious design is one `FlightPlanner` class holding the airports, storing
their coordinates, and implementing Dijkstra's algorithm as a method. It works.
It is also a dead end: the search cannot be reused for anything that is not an
airport, a second algorithm cannot be swapped in without editing the class, and
every new question — fewest stops? cheapest? — makes that one file bigger.

So the package splits along the line rather than around it:

| Layer | Holds | Knows nothing about |
|---|---|---|
| `core/` | `Vertex`, `Edge`, `Graph[V, E]` | airports, distance, algorithms |
| `geo/` | `Point`, `DistanceFormula`, `Haversine`, `Vincenty` | graphs |
| `pathfinding/` | `Dijkstra`, `BFS`, `AStar`, `SearchResult` | airports; reads only "which edges leave this vertex" and "what does an edge cost" |
| `flights/` | `Airport`, `Route`, `FlightPlanner` | — the only layer where the word *airport* appears |

That table is a claim, and it is checkable. Nothing in the bottom three layers
imports `flights`, which means the graph and the searches can be handed
something that is not a flight network at all:

```python
>>> from flight_planner import Vertex, Edge, Graph, Dijkstra
>>> g = Graph()
>>> cities = {name: Vertex(name) for name in ['Portland', 'Boise', 'Reno']}
>>> g.add_edge(Edge(cities['Portland'], cities['Boise'], weight=690))
>>> g.add_edge(Edge(cities['Boise'], cities['Reno'], weight=680))
>>> g.add_edge(Edge(cities['Portland'], cities['Reno'], weight=1450))
>>> cost, legs = g.shortest_path(cities['Portland'], cities['Reno'], Dijkstra())
>>> cost
1370.0
>>> legs
[Edge('Portland' -> 'Boise', weight=690.0), Edge('Boise' -> 'Reno', weight=680.0)]
```

Those are road distances between three cities. Dijkstra neither knows nor
cares, and prefers two hops totalling 1,370 to one direct leg of 1,450 —
which is the same shape of answer §7 reports for flights, on machinery that
contains no aviation.

## 3.2 Composition, against a named alternative

![The core and flight layers. Solid arrows are inheritance; dotted arrows are a strategy being handed in.](../images/flight-planner-class-diagram.svg)

Earlier iterations of this design considered making `Graph` — or
`FlightPlanner` — **derive from** Dijkstra's algorithm. Recording the rejected
option matters more than restating the chosen one, because the reason it was
rejected is the design:

- Every graph would carry the method surface of every algorithm ever added.
- "No algorithm" would not be expressible.
- An algorithm could not be chosen at run time, which is exactly what §4.4's
  mode switch and §7's comparison both need.

Instead, behaviour is a value that gets passed in:

```python
graph.shortest_path(start, goal, Dijkstra())     # the graph is given an algorithm
point.distance_to(other, Haversine())            # the point is given a formula
AStar(haversine_heuristic())                     # the search is given a heuristic
```

This is the Strategy pattern, and the property it buys is stated as a negative:
**adding a new algorithm never changes `Graph`, and adding a new formula never
changes `Point`.** §4's three algorithms are three files in `pathfinding/`, and
none of them required a line of `core/`.

One distinction the layering makes easy to get wrong, so it is stated
explicitly. `DistanceFormula` and `Edge.weight` are unrelated axes.
A `DistanceFormula` only ever estimates straight-line distance between two
points, and exists to guide A\*'s heuristic. `Edge.weight` — here
`Route.distance_km` — is the real accumulated cost the algorithms sum, supplied
as **domain data**. They coincide in this project only because §2.3's pipeline
made them coincide, which is precisely the invariant §4.3's correctness rests
on. Weighting edges by duration or fare instead would mean subclassing `Edge`
and changing no algorithm.

<div class="deck-slide" id="why-the-layers-exist">

### The graph has never heard of an airport

<div class="cards two">

<div class="card figure">

![](../../slides/images/flight-planner-class-diagram.png)

<p class="caption">The core and flight layers. Solid arrows are inheritance; dotted arrows are a strategy being handed in.</p>

</div>

<div class="card">

<span class="pill bfs">Built from scratch</span>

**1,591 lines, no `heapq`.** `core/` digraph · `adt/` binary min-heap ·
`pathfinding/` three searches · `geo/` two geodesic formulas.

<span class="pill">Composition, not inheritance</span>

**Behaviour is passed in.** `graph.shortest_path(a, b, Dijkstra())` — adding
an algorithm never changes `Graph`. The rejected alternative — `Graph`
deriving *from* Dijkstra — forces every graph to carry every algorithm.

</div>

</div>

</div>

## 3.3 `Airport` is a `Vertex` that is also a `Point`

`Airport` is the one class in the project with two parents, and it is worth
saying why that is composition's exception rather than its contradiction. An
airport has to answer two unrelated questions — *what is adjacent to me?*, which
is a graph question, and *where am I?*, which is a geographic one. Inheriting
both is how it answers both without a graph layer that knows about latitude:

```python
class Airport(Vertex, Point):
```

`Route(Edge[Airport])` is a flight leg whose `weight` is `distance_km`, plus the
domain fields — airline, flight number, codeshare flag, stops, equipment.
`FlightPlanner(Graph[Airport, Route])` adds exactly two things to the generic
graph: an IATA-code index, and the convenience wrappers §4.4 describes.

**Identity is the IATA code, and nothing else.** `Airport.__hash__` and
`__eq__` read only `iata_code`, which is what makes `BOS` one vertex however
many times the loader encounters it. It also produces one sharp edge, recorded
here because §5 tests it rather than fixing it:

```python
>>> catalog_bos = planner.find_airport('BOS')
>>> (catalog_bos.latitude, catalog_bos.longitude)
(42.36197, -71.0079)
>>> Airport('BOS') == catalog_bos          # equal, despite knowing no coordinates
True
>>> (Airport('BOS').latitude, Airport('BOS').longitude)
(0.0, 0.0)
```

`Graph.add_vertex` is **first-wins** — adding an existing vertex is a no-op that
leaves its edges untouched — so mixing a bare `Airport('BOS')` into a
catalog-built graph would keep whichever arrived first and silently discard the
other's coordinates. A\*'s heuristic would then measure from the Gulf of Guinea.
Entities that come from a catalog are safe by construction, which is why this is
documented and tested rather than prevented: making `Airport` unhashable without
coordinates would break the hand-built graphs §5's edge-case tests depend on.
[Appendix F](17-appendix-f-reproducibility.md) §F.5 states it as a caveat for
anyone using the library directly.

## 3.4 Adjacency list, and what the alternative would cost

`Graph` stores `Dict[V, List[E]]` — per vertex, only the edges that exist. The
justification is §2.5's measurement rather than a general preference for sparse
structures.

The cleaned network has **3,387 airports and 66,332 routes**, collapsing to
36,717 distinct directed pairs. A complete directed graph on 3,387 vertices has
11,468,382 ordered pairs, so the network uses **0.32%** of them. An adjacency
matrix would allocate all 11.5 million cells to record 36,717 facts, spending
more than **99.6% of itself recording the absence of a route** — and paying for
it twice, in the memory that holds the zeros and in the row scan that reads them
to find the four or five edges that are really there. §6.1 carries the
O(V + E) construction bound and §6.5 the measured space.

The adjacency list also keeps the multigraph, which a matrix cannot. 29,615 of
the 66,332 routes run parallel to another on the same pair — ORD (Chicago)→ATL (Atlanta) alone has
20 — and a single cell has nowhere to put twenty airlines. §2.4 explains why
those parallel edges are real rather than dirty data, and §5 records that a
NetworkX mirror built with the wrong graph type silently discards exactly those
29,615 rows.

**One method is the entire traversal interface.** `get_outgoing_edges(vertex)`
returns a copy of the vertex's edge list, empty for a vertex the graph does not
know. That is all §4's algorithms use — which is why they work on the
three-city road graph in §3.1, and why §5 can verify a search's self-reported
expansion count against an independent count taken through the same method.

<div class="deck-slide" id="adjacency-list">

### Why an adjacency list, in numbers

<div class="cards">

<div class="card">

<span class="pill">What it is</span>

### `Dict[V, List[E]]`

Per airport, only the routes that exist. **One method is the entire traversal
interface:**

```python
graph.get_outgoing_edges(vertex)
```

That is all three searches ever ask for — which is why they run unchanged on a
graph of road distances.

</div>

<div class="card">

<span class="pill warn">What a matrix would cost</span>

### 11,468,382 cells for 36,717 facts

The network uses **0.32%** of the ordered pairs available to it, so a matrix
would spend **over 99.6% of itself recording the absence of a route** — and
pay twice, in the zeros it stores and the row scan that reads past them.

</div>

<div class="card">

<span class="pill dijkstra">What a matrix could not do at all</span>

### ORD (Chicago)→ATL (Atlanta) has 20 rows

**29,615 of 66,332 routes run parallel** to another on the same pair. One cell
has nowhere to put twenty airlines.

A NetworkX mirror built as a `DiGraph` silently discards exactly those 29,615
— which is how §5 caught it.

</div>

</div>

</div>

## 3.5 Edge weights come from one formula, used once

Every `Route.distance_km` is computed by `src/data/flight_network.py` calling
`flight_planner.geo.Haversine` — the same tested class §4.3's heuristic calls,
at the same 6371.0 km radius.

This replaced an earlier SQL transform, and the move is worth recording because
the chapter's correctness argument depends on it. **The graph is built with
pandas; no part of `flight_planner` imports `sqlite3`.** SQLite is still
written, from the same frames, as a second representation of the same data — so
the two cannot drift — but it is an output rather than a stage. What the move
bought:

- The distance calculation **reuses** `geo.Haversine` instead of a second
  hand-written copy of the formula in SQL. A second copy is how §4.3's
  invariant would be broken silently.
- Every stage is reachable from the test suite.
- Routes dropped for unresolvable endpoints are reported rather than lost to an
  INNER JOIN — §2.3's 1,331, with a reason each.

The pipeline also learned this the hard way. `src/sql/flight_data.sql` records
that its stated `OR` over two endpoint conditions was silently tightened to
`AND` by a downstream INNER JOIN: 1,996 routes became 861, and 861 is what got
published. §9 tells that story; it is here as the reason a formula is called
rather than re-typed.

## 3.6 Missing, duplicate and degenerate data

Four cases, and the decisions are different in each.

**Missing identity or coordinates — dropped before the graph exists.** An
airport is usable only with exactly three characters of IATA code and both
coordinates (§2.3). `Airport` therefore never holds a null coordinate, which is
what lets `Point` and the heuristic assume floats.

**Missing text that looks like a null.** `CsvRecordLoader` declares
`TEXT_COLUMNS` and forces them through `str`, because pandas reads the string
`NA` as a null. Without it, every North American airport loads with no
continent and every Namibian one with no country — 303 rows. This is the kind of
defect that produces a clean-looking dataset, so it is guarded at the loader
rather than noticed later.

**Duplicates, at two different levels, handled two different ways.** Duplicate
*airport identities* are collapsed: `_usable_airports` ends in
`drop_duplicates(subset="iata_code")`, since two rows claiming `BOS` are one
airport. Duplicate *routes* are kept: 29,615 parallel edges are 29,615 real
marketed services, and the adjacency list holds them all.

**Self-loops — kept, because they are harmless and real.** Exactly one survives
cleaning:

```
IL0016  IL  PKN->PKN  0.0 km  Iskandar Airport (ID)
```

It sits in the live adjacency list beside PKN (Pangkalanbun)'s six genuine departures, and
costs nothing to leave there. Relaxation in §4.2 is strictly-less-than, so
reaching PKN (Pangkalanbun) again at `0 + 0` is not an improvement and the edge is never
traversed:

```
PKN->SIN BFS       cost=2.0    legs=2  expanded=58  PKN->CGK->SIN
PKN->SIN Dijkstra  cost=1327.0 legs=4  expanded=49  PKN->KTG->PNK->KCH->SIN
PKN->SIN A*        cost=1327.0 legs=4  expanded=5   PKN->KTG->PNK->KCH->SIN
```

Filtering it would have been the tidier choice and the worse one: the rubric
names cyclic and duplicate edges as cases the structure must handle, and the
data supplies one of each. Removing them would mean the handling was never
exercised on anything but a test fixture. §5 covers both as edge cases, on this
graph.
