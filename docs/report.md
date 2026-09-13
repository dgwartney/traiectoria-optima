---
title: "A1: Flight Route Planner"
subtitle: "Final Report"
author: "Aastha Sharma-Flores, Jake Lu, David Gwartney"
date: 2026-08-23
---

# A1: Flight Route Planner — Final Report

## 1. Introduction
- Problem statement: finding cheapest / shortest / fewest-stop routes between airports
- Motivation and goals
- Summary of approach (BFS, Dijkstra, A*)

## 2. Dataset
- Data sources (OpenFlights airports/routes, OurAirports)
- Scope: the world airline network — 3,387 airports and 66,332 routes after
  cleaning. One experiment (`shortest-vs-fewest`) works on a 94-airport US
  large-airport slice of it, frozen as its own snapshot; the evaluation in §7
  uses the whole network, because the queries it asks are long-haul
- Cleaning and preparation steps
- Basic dataset statistics (airport count, route count, degree distribution, disconnected airports)

## 3. Graph Construction
- Adjacency-list representation
- Haversine edge-weight computation
- Handling of missing/invalid data (nulls, duplicates, self-loops)

## 4. Algorithms

### 4.1 BFS (Fewest Stops)
- Description and implementation notes

### 4.2 Dijkstra's Algorithm
- From-scratch binary min-heap implementation
- Dijkstra implementation using the custom heap
- Validation against NetworkX

### 4.3 A* Search (Stretch Concept)
- Haversine admissible heuristic
- A* implementation using the custom heap
- Admissibility argument/proof
  — drop in [results-astar-consistency.md](results-astar-consistency.md);
  note that the implementation requires *consistency*, not merely
  admissibility, and that the project's heuristic satisfies it
  (658,470 checks, 0 violations)

### 4.4 Secondary Features
- Fewest-stops vs. cheapest-distance mode switch
- Nearest-airports-to-a-point lookup

## 5. Correctness Testing
- Unit test strategy (empty, single-node, disconnected, cyclic/duplicate cases)
- Known-route validation
- Library cross-validation results (NetworkX)
  — drop in [results-networkx-parity.md](results-networkx-parity.md);
  200 long-haul queries over the world network, three algorithms, 0 cost
  mismatches, recorded in `experiments/networkx-parity/results.json`
- Randomized differential testing
  — [results-astar-consistency.md](results-astar-consistency.md);
  10,866 queries on random graphs, which found a real defect in A*

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
exponent of **1.01** with **r² = 0.9999**:

| Narrowing | V | E | V + E | Build (ms) |
|---|---|---|---|---|
| `airline DL` | 352 | 1,977 | 2,329 | 1.16 |
| `airline UA` | 427 | 2,170 | 2,597 | 1.27 |
| US large | 94 | 7,005 | 7,099 | 3.45 |
| US large+medium | 467 | 10,243 | 10,710 | 5.36 |
| US all | 613 | 10,702 | 11,315 | 5.60 |
| large | 1,062 | 50,474 | 51,536 | 26.43 |
| large+medium | 2,792 | 63,969 | 66,761 | 34.09 |
| world | 3,387 | 66,332 | 69,719 | 35.65 |

A 29.9× increase in V + E produces a 30.7× increase in build time. Linear, as
predicted.

### 6.2 BFS — O(V + E) time, O(V) space

BFS dequeues each reachable airport at most once and examines each of its
outgoing routes once, giving O(V + E). It marks an airport visited at *push*
time rather than at pop time, so no airport enters the queue twice and the queue
holds at most V entries: O(V) space.

Measured growth exponent: **0.48** (r² = 0.967) — see §6.6 for why this is
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

Measured growth exponent: **0.40** (r² = 0.738).

### 6.4 A\* — O((V + E) log V) time, O(V) space

A\* is Dijkstra with the priority `f = g + h`, so its worst-case bound is
identical: an uninformative heuristic makes it expand exactly what Dijkstra
expands. The haversine heuristic is admissible (§4.3) — great-circle distance
can never exceed the distance of any actual route between two airports, since a
route is a sequence of great-circle legs and the direct arc is the shortest path
on the sphere — and it is also consistent, which is what guarantees A\* never
expands an airport twice and never needs to reopen one.

Measured growth exponent: **0.13** (r² = 0.585). In practice A\* settled every
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
| Graph construction | **1.01** | 0.9999 | O(V + E) |
| BFS | 0.48 | 0.967 | O(V + E) |
| Dijkstra | 0.40 | 0.738 | O((V + E) log V) |
| A\* | 0.13 | 0.585 | O((V + E) log V) |

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
still fairly well described by graph size (r² = 0.967) because it fans out
blindly. Dijkstra's 0.738 reflects a real non-monotonicity discussed in §7.5.
A\*'s 0.585 says graph size barely explains its runtime at all — the honest
reading is that A\*'s cost on this network is dominated by fixed per-call
overhead, because the search itself is only a handful of expansions.

## 7. Empirical Evaluation

### 7.1 Methodology

Everything in this section comes from `experiments/search-cost/`, whose
`results.json` is committed alongside the notebook that produced it. The data is
a verified snapshot — if a byte of it changes, the notebook raises rather than
quietly producing different numbers.

| | |
|---|---|
| Snapshot | `2026-09-11-bb90a8` — 3,387 airports / 66,332 routes, no narrowing criteria |
| Query set | SFO–BOS, LAX–JFK, SEA–MIA, HNL–BOS, ANC–MIA — long-haul pairs, per the problem statement |
| Repeats | 15 per measurement, after one discarded warm-up call; **median** reported, which is robust to GC pauses in a way the mean is not |
| Timing | `time.perf_counter()` around the search only. The graph is built once *outside* the timed region, and no observer is attached while timing |
| Size series | Eight narrowings of the world network, 2,329 to 69,719 V + E — a 30× span |
| CPU | Apple M2 Pro, 10 cores |
| Software | Python 3.12.12, macOS 26.6.2 (arm64) |

Three methodological points that materially affect whether the numbers mean
anything:

- **The x-axis is V + E, not airport count.** The two do not move together: the
  US large-airport network has 94 airports but 7,005 routes, while Delta's has
  352 airports and 1,977 routes. Ordering by airports produces a curve that
  crosses itself. V + E is also the term in O((V + E) log V).
- **The same five queries run at every size.** Every airport in the query set
  survives all eight narrowings, which is asserted by a test. Had a pair
  vanished partway down the series, the curve would be comparing different
  questions at different sizes.
- **Which results are portable, and which are not.** Nodes expanded, the
  distances, and the growth exponents are properties of the algorithms and
  reproduce on any machine — across three consecutive runs the exponents moved
  by at most 0.01. The absolute millisecond figures are properties of the
  machine above and should not be compared against a run on different hardware.
  Re-executing the notebook in Google Colab is the cheapest way for a reader to
  reproduce the timings on a stated, selectable configuration; the workload is
  single-threaded pure Python, so a GPU runtime changes nothing.

### 7.2 Nodes expanded: informed against uninformed search

| Query | BFS | Dijkstra | A\* | Dijkstra (km) | A\* (km) | A\* saving |
|---|---|---|---|---|---|---|
| SFO–BOS | 10 | 746 | **1** | 4341.022 | 4341.022 | 746× |
| LAX–JFK | 62 | 590 | **1** | 3974.164 | 3974.164 | 590× |
| SEA–MIA | 52 | 784 | **1** | 4379.358 | 4379.358 | 784× |
| HNL–BOS | 132 | 1,056 | **3** | 8192.794 | 8192.794 | 352× |
| ANC–MIA | 174 | 778 | **6** | 6459.622 | 6459.622 | 130× |

**A\* returned exactly Dijkstra's distance on all five queries — to the last
decimal place — while expanding 130× to 784× fewer airports.** That is the
project's central claim, measured rather than asserted.

![Nodes expanded per query, by algorithm](images/nodes-expanded-light.png)

### 7.3 Runtime

| Narrowing | V + E | BFS (ms) | Dijkstra (ms) | A\* (ms) |
|---|---|---|---|---|
| `airline DL` | 2,329 | 0.314 | 1.456 | 0.196 |
| `airline UA` | 2,597 | 0.351 | 1.715 | 0.200 |
| US large | 7,099 | 0.424 | 1.889 | 0.161 |
| US large+medium | 10,710 | 0.719 | 4.351 | 0.234 |
| US all | 11,315 | 0.757 | 4.898 | 0.233 |
| large | 51,536 | 1.229 | 3.391 | 0.222 |
| large+medium | 66,761 | 1.631 | 6.790 | 0.312 |
| world | 69,719 | 1.744 | 7.907 | 0.317 |

A\* is the fastest algorithm at every one of the eight sizes, and on the full
network it answers the same question as Dijkstra **25× faster**.

### 7.4 Runtime against input size

![Median query time against graph size, log-log](images/runtime-light.png)

Log-log axes, so a power law appears as a straight line whose slope is the
growth exponent (§6.6). The ordering never changes across the whole 30× range:
A\* is **7× to 25× faster than Dijkstra** and **1.6× to 5.6× faster than BFS**,
with the gap widening as the graph grows. Those are ratios between series
measured in the same run on the same machine, so unlike the absolute
milliseconds they survive being re-run elsewhere.

### 7.5 Discussion

**Does A\* expand fewer nodes while returning the same answer? Yes,
unambiguously** — §7.2. The heuristic's admissibility guarantees the answers
match, and the measurement confirms the guarantee held on real data rather than
only in the proof.

Three findings complicate the simple story, and all three are more interesting
than the headline:

**BFS is not uniformly more expensive than Dijkstra.** It expands far fewer
nodes on every query here (10 against 746 on SFO–BOS) because it stops at the
first route it finds. But it answers a *different question*: fewest stops, not
shortest distance. Its "cost" column is a hop count, not kilometres, which is
why §7.2 reports Dijkstra's and A\*'s distances and not BFS's. On the 94-airport US
slice (snapshot `2026-09-12-3e4f9d`) the pair BOI–CHS shows the trade cleanly:

| Algorithm | Expanded | Route | Legs | Distance |
|---|---|---|---|---|
| BFS | 86 | BOI→ORD→CHS | 2 | 3,531.4 km |
| Dijkstra | 69 | BOI→DEN→BNA→CHS | 3 | 3,376.0 km |

BFS did *more* work than Dijkstra and returned a route 155 km longer — while
still being correct, because it was asked for the fewest stops and it found
them. Neither algorithm dominates, and the two are not comparable on a single
axis.

**A\* pushes far more than it expands.** On SFO–BOS it expands 1 airport but
pushes 105 entries onto the heap. Its saving is concentrated in expansions —
the expensive operation, since each one touches every outgoing route of an
airport — and not in heap traffic. Reporting only nodes expanded would overstate
the result; `nodes_pushed` is what makes the honest version visible.

**Dijkstra's runtime is not monotonic in graph size.** It drops from 4.898 ms at
11,315 V + E to 3.391 ms at 51,536 — a graph 4.6× larger answered 1.4× faster.
The `large` narrowing holds 50,474 routes among only 1,062 airports, so the query
pairs sit one or two hops apart and Dijkstra settles fewer airports before
reaching the goal. **Runtime tracks airports settled, not graph size** — the
same conclusion §6.6 reaches from the exponents, arrived at independently.

### 7.6 What this evaluation does not show

- **Worst-case behaviour.** Every query here succeeds and terminates early. An
  unreachable destination is the expensive case, because the search must exhaust
  the reachable component before answering; it is handled and tested, but it is
  not in this benchmark.
- **Behaviour on a different graph shape.** The airline network is small-world:
  dense hubs, short paths, high clustering. A sparse or grid-like graph would
  put A\*'s heuristic under real pressure, and these exponents would not carry
  over.
- **Comparability of absolute timings.** See §7.1.
- **Comparability with NetworkX's timings.** NetworkX's `shortest_path`
  runs a *bidirectional* search, so of the three algorithms only the A\*
  row compares like with like — see
  [results-networkx-parity.md](results-networkx-parity.md).

## 8. Visualization
- Rendered route map (Folium/ipyleaflet)
- Other supporting visualizations (graph stats, degree distribution)

## 9. Challenges and Lessons Learned
- Data quality issues encountered
- Algorithmic/implementation challenges
- What we would do differently

## 10. Conclusion
- Summary of findings
- Future work / extensions

## 11. References
- Course textbook and papers (Goodrich et al.; Hart, Nilsson & Raphael; CLRS)
- Dataset sources
- Libraries used (and how, per the "validation/plotting only" rule)

## Appendix
- Team contributions
- Repository/notebook links
