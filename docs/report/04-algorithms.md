# 4. Algorithms

Three searches, one interface. `PathfindingAlgorithm` declares a single method —
`search(graph, start, goal, observer)` returning a `SearchResult` — and BFS,
Dijkstra and A\* are three implementations of it. §3 explains why the graph is
*given* an algorithm rather than containing one; this chapter is what those
algorithms do, and what had to be decided to make them comparable.

They are not three answers to one question. BFS answers *fewest stops*;
Dijkstra and A\* answer *shortest distance*. The single query below is the whole
chapter in miniature — same graph, same endpoints, three algorithms:

```
BFS       cost=     2.000 hops     legs=2  expanded=  125   HNL->ATL->BDL
Dijkstra  cost=  8071.514 weight   legs=3  expanded= 1019   HNL->SLC->DTW->BDL
A*        cost=  8071.514 weight   legs=3  expanded=   10   HNL->SLC->DTW->BDL
```

Three things to read off it, each developed below. **BFS disagrees** because it
was asked something else: its two-leg itinerary is 8,616.2 km against
Dijkstra's 8,071.5 km, so skipping one stop costs 544.7 km. **A\* agrees with
Dijkstra exactly** — not approximately, to the last digit of a float.
And **A\* paid 102× less** to get there.

That last pair of facts is the project's claim, and §4.3 is about why the
agreement is guaranteed rather than lucky.

## 4.1 BFS — fewest stops

Breadth-first search explores the graph in rings: everything one hop from the
origin, then everything two hops away, and so on. The first time it reaches the
destination it has reached it by the fewest edges possible, because a shorter
route would have been found in an earlier ring. A FIFO queue is what produces
that order, and it is the whole algorithm — `collections.deque`, no priority,
no weights.

`edge.weight` is ignored entirely. `SearchResult.cost` here is a **hop count**,
which is why every result carries a `unit` field declaring itself `COST_HOPS`
rather than `COST_WEIGHT`. Two numbers that are both "cost" and are measured in
different things are how a comparison table becomes wrong, and the unit tag is
what stops one being summed with the other.

**One subtlety that changes what gets reported.** BFS marks a vertex `visited`
when it is *enqueued*, not when it is taken off the queue — it has to, or the
same vertex would be queued once per inbound edge. That means `len(visited)` is
the number of airports *discovered*, not the number *expanded*, and those
differ by the size of the queue at the moment the search stops. Reporting
`len(visited)` would silently inflate BFS's cost against the two algorithms it
is being compared with. So BFS keeps a separate counter, incremented where the
expansion actually happens:

```python
while queue:
    current = queue.popleft()
    if current == goal:
        break
    expanded += 1
```

The goal is excluded, in all three algorithms, because it is found rather than
expanded. §7's comparison table is only meaningful because `nodes_expanded`
means the same thing in every row of it.

<div class="deck-slide" id="bfs">

### BFS — fewest stops, and an honest counter

<div class="cards two">

<div class="card">

<span class="pill bfs">The algorithm</span>

### Rings, on a FIFO queue

Everything one hop out, then everything two hops out. The first arrival at the
destination is by the fewest edges possible, because a shorter route would have
been found in an earlier ring.

`collections.deque`, no priority, no weights. `SearchResult.unit` says
`COST_HOPS`, so a hop count can never be summed with a distance.

</div>

<div class="card">

<span class="pill warn">The subtlety that changes the numbers</span>

### `len(visited)` is not the expansion count

BFS marks a vertex visited at **enqueue**, not at pop — it must, or a vertex
is queued once per inbound edge. So `visited` counts airports *discovered*.

Reporting it would have inflated BFS's cost against the two algorithms it is
compared with, by the size of the queue at the moment the search stopped. BFS
keeps a **separate counter**, incremented where expansion actually happens.

</div>

</div>

<p class="footnote">The goal is excluded in all three algorithms — it is found, not expanded. §7's table is only meaningful because `nodes_expanded` means the same thing in every row of it.</p>

</div>

## 4.2 Dijkstra — shortest distance, on our own heap

Dijkstra replaces the FIFO queue with a priority queue keyed on distance from
the origin, and adds *relaxation*: on reaching an airport by a cheaper route
than any known so far, record the new distance and queue it again. The
invariant that makes it correct is that **the first time a vertex is popped,
its distance is final** — nothing still on the queue is cheaper, and no edge
can reduce it, because edge weights are non-negative.

### The min-heap

The priority queue is `flight_planner.adt.MinHeap`, written for this project.
`heapq` is not imported anywhere in the package; the heap is the stretch
concept, so importing one would be importing the deliverable.

It is an array-backed complete binary tree, following Goodrich, Tamassia &
Goldwasser ch. 9. The parent/child links are index arithmetic rather than
pointers — children of `j` at `2j+1` and `2j+2`, parent at `(j-1)//2` — so the
tree needs no node objects and no rebalancing. `push` appends and sifts up;
`pop` swaps the root with the last entry, truncates, and sifts down. Both walk
one root-to-leaf path, which is O(log n) on a complete tree. §6.2 carries the
derivation.

**Entries order on `(priority, sequence)`, never on the item.** Each push
records an incrementing sequence number, so two airports at the same distance
come out in insertion order and `Airport` never has to be comparable. This is
not a detail: without it, a tie between two equal-distance airports would fall
through to comparing the airports themselves, and the natural implementations
of that are either an exception or an ordering nobody chose.

<div class="deck-slide" id="min-heap">

### The min-heap, written rather than imported

<div class="cards">

<div class="card">

<span class="pill">The structure</span>

### An array, read as a tree

Goodrich ch. 9: the backing list holds the complete binary tree level by level,
so the links are **index arithmetic rather than pointers**.

```python
children of j: 2j+1, 2j+2
parent  of j: (j-1)//2
```

No node objects, no rebalancing. `push` appends and sifts up; `pop` swaps the
root with the last entry, truncates, and sifts down — one root-to-leaf walk
each, **O(log n)**.

</div>

<div class="card">

<span class="pill dijkstra">The tie-break</span>

### Order on `(priority, sequence)`

Every push records an incrementing sequence number, so equal distances come out
in insertion order and **`Airport` never has to be comparable**.

Without it a tie falls through to comparing the airports themselves — and the
natural implementations of that are an exception, or an ordering nobody chose.

</div>

<div class="card">

<span class="pill mute">The whole surface</span>

### `push` · `pop` · `peek`

No handles, no index map, no `decrease_key`. That interface is a deliberate
constraint rather than an omission, and the next slide is what it costs.

`heapq` is imported nowhere in the package: the heap is the stretch concept, so
importing one would be importing the deliverable.

</div>

</div>

</div>

### No decrease-key

The textbook Dijkstra repositions an entry already in the queue when it finds a
cheaper route. That needs a `decrease_key` operation, which needs a handle to
each entry, which needs the heap to maintain a vertex-to-index map and update
it on every swap.

This implementation does none of that. It pushes a **second** entry and lets
the first go stale — *lazy deletion*. A `settled` set records what has already
been expanded, and a pop that surfaces an already-settled vertex is discarded:

```python
current = pq.pop()
if current == goal:
    break
if current in settled:
    continue
settled.add(current)
```

The trade is explicit. The heap's interface stays at `push`/`pop`/`peek` with no
bookkeeping, and the heap grows to hold one entry per *improvement* rather than
one per vertex. That cost is measured rather than assumed:
`nodes_pushed − nodes_expanded` is exactly the work thrown away, and on the
world network Dijkstra pushes 1.69–1.88 entries per expansion (§6.3). Roughly
four in ten pops are discarded — which is the price of not writing
`decrease_key`, stated as a number.

### Validation

Dijkstra's answers are cross-validated against NetworkX over 200 long-haul
queries on the world network: **0 cost mismatches**, worst divergence
3.6 × 10⁻¹² km, and identical paths on 200 of 200. §5 covers the method and
[Appendix D](15-appendix-d-networkx-parity.md) the full results.

<div class="deck-slide" id="dijkstra">

### Dijkstra — and the price of not writing `decrease_key`

<div class="cards">

<div class="card">

<span class="pill dijkstra">The invariant</span>

### First pop is final

Priority is distance from the origin; *relaxation* re-queues an airport reached
more cheaply than before.

Nothing still on the queue is cheaper and no edge can reduce it, **because
weights are non-negative** — which is the whole correctness argument, and the
reason the one 0.0 km self-loop in the data is harmless.

</div>

<div class="card">

<span class="pill warn">Lazy deletion instead</span>

### Push a second entry, discard the stale one

Textbook Dijkstra repositions a queued entry. That needs a handle per entry,
which needs a vertex→index map maintained on every swap.

Ours pushes again and skips any pop that is already settled. The heap stays at
`push`/`pop`/`peek`, and grows to one entry **per improvement** rather than per
vertex.

</div>

<div class="card">

<span class="pill">The cost, measured</span>

### 1.69–1.88 pushes per expansion

`nodes_pushed − nodes_expanded` is exactly the work thrown away, so the trade
is a number rather than a caveat. **Roughly four pops in ten are discarded.**

Cross-validated against NetworkX over 200 long-haul queries: **0 cost
mismatches**, worst divergence 3.6e-12 km.

</div>

</div>

</div>

## 4.3 A\* — the stretch concept, and the argument it rests on

A\* is Dijkstra with one change: the priority is `f = g + h`, where `g` is the
distance already travelled and `h` estimates the distance still to go. A good
estimate makes the search lean toward the destination instead of expanding
outward in all directions. On HNL–BDL that is the difference between 1,019
expansions and 10.

`h` here is the great-circle distance from an airport to the destination,
through `geo.haversine_heuristic()`. The estimate ignores whether any flight
exists along that line, which is the point — it is a lower bound on what the
remaining journey could possibly cost, not a prediction of the route.

### Admissible is not enough

The textbook condition for A\* to return an optimal path is **admissibility**:
`h` never overestimates the true remaining cost. That condition is stated for
an A\* that can *reopen* a closed vertex when a cheaper route to it turns up
later.

**This implementation cannot reopen.** Like Dijkstra, it adds a vertex to
`visited` on first expansion and skips it thereafter. For that to be sound the
heuristic must satisfy the stronger condition of **consistency** — that it
never drops faster than an edge costs:

$$h(u) \le w(u, v) + h(v) \quad \text{for every edge } (u, v)$$

The gap between the two conditions is not hypothetical, and the smallest case
that shows it has four vertices:

```
S --2.0--> A --1.0--> G
 \                    ^
  1.0--> B --0.5-----/
```

with `h(S) = 0`, `h(B) = 1.5`, `h(A) = h(G) = 0`. Every estimate is at or below
the true remaining cost, so the heuristic **is admissible**. It is not
consistent: `h` falls from 1.5 at `B` to 0 at `A` across an edge costing 0.5.

A\* pops `A` early carrying the 2.0 route, closes it, and never propagates the
cheaper arrival that comes via `B`. Dijkstra reports 2.5. Ours reports **3.0**:

| | Cost | Route returned | Legs sum to |
|---|---|---|---|
| Dijkstra | 2.5 | `S→B→A→G` | 2.5 |
| `AStar` | **3.0** | `S→B→A→G` | **2.5** |
| `ReopeningAStar` | 2.5 | `S→B→A→G` | 2.5 |

Read the last row of `AStar` carefully. It is not merely that the cost is
wrong — **the cost contradicts the path printed beside it.** The legs of the
returned itinerary add to 2.5 while the reported total says 3.0. A caller
checking the answer by summing the legs would get a different number than the
one the search handed back.

Over 10,866 randomized queries on 50 graphs with admissible-but-inconsistent
heuristics, `AStar` returned a suboptimal cost **27 times** and a cost
contradicting its own path **25 times**. NetworkX's A\*, which reopens, and a
reopening variant of ours both returned 0 of each. The reopening fix costs
**0.52% more expansions** — 40,792 against 40,580.

### Why this heuristic is safe here — and it is not geometry

So the question for this project is not whether haversine is admissible. It is
whether haversine is **consistent** on this graph. It is, and the reason is
narrower and more interesting than the textbook one.

It is tempting to argue that a great-circle arc is the shortest path on a
sphere, so the direct distance can never exceed a chain of flights. That
argument assumes the flights are measured as great-circle arcs. **They are,
but only because the pipeline made them so.** `src/data/flight_network.py`
generates the `distance_km` column by calling the same `Haversine()` class, at
the same 6371.0 km radius, that the heuristic calls. The estimate and the edge
weights are not two measurements that happen to agree — they are one
measurement, used twice.

**Admissibility here is therefore an invariant between two parts of the build,
not a theorem about the earth.** Measured on the world snapshot by
`experiments/heuristic-admissibility/`:

| | Checks | Violations | Worst |
|---|---|---|---|
| Estimate against each edge's own weight | 66,332 | **0** | 1.8 × 10⁻¹² km |
| Consistency, `h(u) ≤ w(u,v) + h(v)` | 6,633,200 | **0** | 1.8 × 10⁻¹² km |
| Consistency, US large-airport slice | 658,470 | **0** | 0.0 km |

The worst excess is not a small margin — it is **zero plus one bit of float
rounding**, which is what "the same computation run twice" looks like. The
worst case on the whole network is AKL→CAN, where the weight is
9299.934868223923 km and the estimate 9299.934868223925 km.

Because it is an invariant rather than a theorem, it can be broken by an edit
somewhere else. `tests/flight_planner/geo/test_heuristic.py` and
`tests/experiments/test_heuristic_admissibility.py` therefore check it against
real routes: change the pipeline's formula or its earth radius and those tests
fail, rather than A\* quietly starting to return longer routes and calling them
optimal.

### The corollary: a better formula makes a worse heuristic

The invariant framing predicts something the geometric one does not. If
admissibility depends on the heuristic using *the same formula as the weights*,
then replacing the heuristic with a **more accurate** one should break it.

It does. `Vincenty` measures on the WGS-84 ellipsoid — semi-major axis
6378.137 km rather than a 6371.0 km sphere — and is the better model of the
earth by any physical standard. Substituted as the heuristic, while the edge
weights remain haversine numbers, its estimates exceed the truth on **38,901 of
66,332 edges (58.6%)**, by as much as 25.66 km. Every one of those is a
potential silently-wrong route.

The textbook intuition fails in the same place. Haversine is often described as
underestimating true geodesic distance, because a sphere cuts corners an
ellipsoid does not. Measured across all 66,332 edges, haversine **exceeds** the
WGS-84 geodesic on 27,430 of them (41.4%), by up to 35.18 km. The error runs
both ways.

**Precision and admissibility are different properties, and improving the first
can break the second.** That is the most useful thing this project learned, and
it generalises past flight routing: a heuristic is not a measurement of the
world, it is a lower bound on a cost model, and it must be consistent with the
cost model rather than accurate about reality.

[Appendix E](16-appendix-e-astar-consistency.md) carries the full consistency
study; [Appendix C](14-appendix-c-distance-formulas.md) compares the formulas
themselves.

<div class="deck-slide" id="astar-consistency">

### A\* needs consistency, not just admissibility

<div class="cards">

<div class="card">

<span class="pill astar">The gap</span>

### Admissible ≠ safe

Our A\* closes a vertex on first pop and never reopens it. That needs
`h(u) ≤ w(u,v) + h(v)` — **consistency** — not merely "never overestimates".

On 10,866 randomized queries: **27 suboptimal**, and **25 where the reported
cost contradicted the path returned**.

</div>

<div class="card">

<span class="pill">Why we are safe</span>

### The weights *are* haversine

The pipeline generates `distance_km` with the same `Haversine()` at the same
6371.0 km radius. Estimate and weight are one measurement.

**0 violations in 6,633,200 checks.** Worst gap 1.8e-12 km — float rounding,
not slack.

</div>

<div class="card">

<span class="pill warn">The corollary</span>

### A better formula breaks it

Vincenty is the more accurate earth model. As the heuristic it overestimates on
**38,901 of 66,332 edges**, by up to 25.66 km.

Precision and admissibility are different properties.

</div>

</div>

<p class="footnote">`experiments/heuristic-admissibility` and `experiments/astar-consistency`, world snapshot `2026-09-11-bb90a8`.</p>

</div>

## 4.4 Secondary features

**The mode switch is the Strategy pattern, exposed.** `FlightPlanner` takes the
algorithm as an argument rather than choosing one:

```python
planner.find_shortest_route("HNL", "BDL")                          # Dijkstra
planner.find_shortest_route("HNL", "BDL", BFS())                   # fewest stops
planner.find_shortest_route("HNL", "BDL", AStar(haversine_heuristic()))
```

Dijkstra is the default because "cheapest" in this project means distance
(§1). Switching mode changes no other line of the call, and adding a fourth
algorithm requires no change to `FlightPlanner` at all — which is the property
§3 argues the layering buys.

`search_route` is the same query returning a `SearchResult`: the itinerary plus
`nodes_expanded`, `nodes_pushed` and `peak_frontier`. §7's entire comparison is
read off that one return value, and §5 verifies the counters against an
independent count rather than trusting them.

**Airports resolve by code or by object.** Every query accepts either an
`Airport` or its three-letter IATA string, so a caller holding data need not
first look up an object. Three boundary behaviours are defined and tested:

| Query | Result | Why this and not something else |
|---|---|---|
| Unreachable destination | `(inf, [])` | A real answer: the search ran and found nothing. The counters are still populated — `SPI→JFK` expands 1 node before concluding |
| Origin equals destination | `(0.0, [])` | Zero cost, zero legs, and no search at all |
| Unknown IATA code | `AirportNotFoundError` | **Not** `(inf, [])`. "There is no such airport" and "there is no such route" are different facts, and collapsing them would let a typo look like a routing result |

That last row is the one that matters. `AirportNotFoundError` derives from
`KeyError` and `ValueError` as well as the project's own base, so it is a
strict superset of the three conventions it replaced and adopting it broke no
existing caller (§3).

**Not built: nearest-airport-to-a-coordinate lookup.** The project plan listed
it as a secondary feature and it was never implemented. Airports are found by
IATA code only. The pieces are present — `Airport` is a `Point`, and
`geo.Haversine` measures between any two — so it is a short addition rather
than a design problem, and §10 lists it with the other future work.
