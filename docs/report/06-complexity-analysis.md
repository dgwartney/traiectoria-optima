## 6. Complexity Analysis

Every bound below is stated for *our* implementation and then checked against a
measurement of it. The measurements come from the `search-cost` experiment
(§7.1); `V` is airports, `E` is routes.

### 6.1 Graph construction — O(V + E) time, O(V + E) space

`Catalog.planner()` walks the airport table once, inserting each airport into a
dictionary, then walks the route table once, appending each route to its
origin's adjacency list. Dictionary insertion and list append are both amortised
O(1), so construction is O(V + E), and the structure it builds stores one entry
per airport and one per route, so its space is O(V + E) as well.

This is the only bound in the project that is **directly** testable, because
construction cannot stop early — a search can, by reaching its goal. Fitting a
line to log(build time) against log(V + E) across eight graph sizes gives an
exponent of **1.01** with **r² = 0.9997**:

| Narrowing | V | E | V + E | Build (ms) |
|---|---|---|---|---|
| `airline DL` | 352 | 1,977 | 2,329 | 1.24 |
| `airline UA` | 427 | 2,170 | 2,597 | 1.28 |
| US large | 94 | 7,005 | 7,099 | 3.72 |
| US large+medium | 467 | 10,243 | 10,710 | 5.70 |
| US all | 613 | 10,702 | 11,315 | 5.85 |
| large | 1,062 | 50,474 | 51,536 | 27.37 |
| large+medium | 2,792 | 63,969 | 66,761 | 35.41 |
| world | 3,387 | 66,332 | 69,719 | 37.81 |

A 29.9× increase in V + E produces a 30.5× increase in build time. Linear, as
predicted.

### 6.2 BFS — O(V + E) time, O(V) space

BFS dequeues each reachable airport at most once and examines each of its
outgoing routes once, giving O(V + E). It marks an airport visited at *push*
time rather than at pop time, so no airport enters the queue twice and the queue
holds at most V entries: O(V) space.

Measured growth exponent: **0.49** (r² = 0.963) — see §6.6 for why this is
below the bound rather than at it.

### 6.3 Dijkstra on our own binary min-heap — O((V + E) log V) time, O(V) space

The from-scratch heap (§4.2) gives O(log n) push and pop. Our Dijkstra uses
**lazy deletion** rather than decrease-key: when it finds a shorter route to an
airport already on the frontier it pushes a second entry instead of repositioning
the first, and discards stale entries on pop. That choice keeps the heap
interface small — push, pop, peek, no handle bookkeeping — at the cost of a
larger heap.

The heap therefore holds at most one entry per route improvement, which is
O(E), and each push and pop costs O(log E) = O(log V²) = O(log V). Every airport
is expanded at most once and every route is relaxed at most once, so the total
is **O((V + E) log V)**. Space is O(V) for the settled set and distances, plus
O(E) worst case for the heap itself.

The cost of lazy deletion is not a theoretical concern here — it is measured.
`nodes_pushed − nodes_expanded` is the wasted work, and on the world network
Dijkstra pushes roughly 1.7–1.9 entries per expansion:

| Query | Expanded | Pushed | Pushed / expanded | Peak frontier |
|---|---|---|---|---|
| SFO–BOS | 746 | 1,264 | 1.69 | 418 |
| LAX–JFK | 590 | 1,034 | 1.75 | 353 |
| SEA–MIA | 784 | 1,363 | 1.74 | 467 |
| HNL–BOS | 1,056 | 1,985 | 1.88 | 682 |
| ANC–MIA | 778 | 1,371 | 1.76 | 526 |

Measured growth exponent: **0.41** (r² = 0.759).

### 6.4 A\* — O((V + E) log V) time, O(V) space

A\* is Dijkstra with the priority `f = g + h`, so its worst-case bound is
identical: an uninformative heuristic makes it expand exactly what Dijkstra
expands. The haversine heuristic is admissible (§4.3) — great-circle distance
can never exceed the distance of any actual route between two airports, since a
route is a sequence of great-circle legs and the direct arc is the shortest path
on the sphere — and it is also consistent, which is what guarantees A\* never
expands an airport twice and never needs to reopen one.

Measured growth exponent: **0.14** (r² = 0.606). In practice A\* settled every
query in this benchmark in **1 to 6 expansions**.

### 6.5 Space, measured

The O(V) space claims are backed by `peak_frontier`, the largest the frontier
ever got during a search. Across all fifteen measured searches on the world
network (V = 3,387):

| Algorithm | Largest peak frontier | As a fraction of V |
|---|---|---|
| BFS | 1,246 | 37% |
| Dijkstra | 682 | 20% |
| A\* | 161 | 5% |

All three are comfortably inside the linear bound. BFS peaks highest despite
expanding fewest, which is not a contradiction: it enqueues an entire frontier
level at a time, so its queue is widest exactly when its expansion count is
still low.

### 6.6 Measured exponents against the bounds

| Series | Measured exponent | r² | Asymptotic bound |
|---|---|---|---|
| Graph construction | **1.01** | 0.9997 | O(V + E) |
| BFS | 0.49 | 0.963 | O(V + E) |
| Dijkstra | 0.41 | 0.759 | O((V + E) log V) |
| A\* | 0.14 | 0.606 | O((V + E) log V) |

Only construction reaches its exponent. Every search comes out well below its
bound, and the fits get *worse* as the algorithm gets smarter. Both facts have
the same cause, and it is worth stating plainly because it is the substance of
this section rather than a weakness in the measurement:

**A worst-case bound describes a search that exhausts the graph. None of these
searches do.** They are goal-directed and stop on arrival, so what predicts
their cost is how much of the graph lies between origin and goal — not how big
the graph is. Growing the network from 2,329 to 69,719 V + E adds airports that
the search never visits.

The r² values quantify how far each algorithm has escaped its own bound. BFS is
still fairly well described by graph size (r² = 0.963) because it fans out
blindly. Dijkstra's 0.759 reflects a real non-monotonicity discussed in §7.5.
A\*'s 0.606 says graph size barely explains its runtime at all — the honest
reading is that A\*'s cost on this network is dominated by fixed per-call
overhead, because the search itself is only a handful of expansions.
