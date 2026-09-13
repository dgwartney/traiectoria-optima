# 2. Dataset
- Data sources (OpenFlights airports/routes, OurAirports)
- Scope: the world airline network — 3,387 airports and 66,332 routes after
  cleaning, measured in §2.1. One experiment (`shortest-vs-fewest`) works on a
  94-airport US large-airport slice of it, frozen as its own snapshot; the
  evaluation in §7 uses the whole network, because the queries it asks are
  long-haul
- Cleaning and preparation steps

## 2.1 Basic graph statistics

Every number in this section comes from `experiments/graph-stats/`, whose
`results.json` is committed alongside the notebook that produced it. It runs on
the same pinned snapshot as the correctness testing in §5 and the evaluation in
§7, so the graph described here is exactly the graph those chapters measure.

**Size and density.** The cleaned network holds **3,387 airports** and **66,332
routes**. Those routes are directed and may repeat: two airlines flying the same
city pair are two routes. Collapsing them leaves **36,717 distinct airport
pairs**, so **29,615 routes — 45% of the table — run parallel to another on the
same pair.** That figure is why the graph is a multigraph rather than a simple
one, and it is independently confirmed by the NetworkX mirror in §5, which
records the same 29,615 as the routes a collapsing graph type would discard.

A complete directed graph on 3,387 airports would have 11,468,382 ordered pairs.
The network uses **0.32%** of them. That sparsity is the argument for the
adjacency-list representation in §3: an adjacency matrix would need all 11.5
million cells to store 36,717 facts, and would spend more than 99.6% of itself
recording the absence of a route.

**Degree.** An airport's out-degree is the number of routes departing it.

| | min | median | mean | max |
|---|---|---|---|---|
| out-degree | 0 | 4 | 19.6 | 915 (ATL) |
| in-degree | 0 | 4 | 19.6 | 911 (ATL) |

The mean and median disagree by a factor of five, and that gap is the single most
important fact about this graph's shape. The distribution is heavy-tailed:
**38.4% of airports have two or fewer departures**, while the 1.2% with more than
256 carry a disproportionate share of the network. The ten busiest airports alone
account for 8.1% of all routes.

![How many airports have each out-degree](../images/degree-distribution-light.png)

Both axes are logarithmic. On linear axes the entire distribution but a handful
of points would collapse onto the origin; on log-log the heavy tail reads as a
falling line spanning three orders of magnitude in each direction.

![The ten busiest airports, in- and out-degree](../images/top-hubs-light.png)

In- and out-degree track each other closely at every hub — ATL's 915 departures
against 911 arrivals, AMS's 450 against 447 — which is what scheduled aviation
should look like, since aircraft that arrive must leave. The near-symmetry is a
useful sanity check on the cleaning: a large gap at a major airport would point
to dropped rows rather than to real one-way service.

**Disconnected airports.** Three kinds of dead end, and they are not the same
thing:

| | count |
|---|---|
| no departures (routes arrive, none leave) | 16 |
| no arrivals (routes leave, none come in) | 7 |
| isolated (in no route at all) | 0 |

Every airport in the table appears in at least one route, so the 3,387 vertices
are all real. The 16 airports a search can enter and not leave are the concrete
instances of the disconnected case that §5's edge-case tests pin down.

**Connectivity.** Ignoring direction, the network falls into **8 weakly connected
components**, and one of them holds **3,359 airports — 99.2% of the total**. The
other seven are tiny: one of ten airports and six of two to four.

Restricting to mutual reachability, **3,318 airports (98.0%) form a single
strongly connected core** — from any one of them, every other is reachable by
some sequence of flights, and back again. This is what makes the long-haul
queries in §7 meaningful: a route between two arbitrary busy airports almost
always exists, so the algorithms being compared are doing real search rather than
discovering "no route". It also explains the zero unreachable pairs in §5's
200-query NetworkX sweep.

The measurement uses no traversal code of its own. `BFS` compares its goal only
for equality and never asks the graph for the goal's edges, so a search aimed at
a sentinel airport that is not in the graph visits everything reachable from its
origin and then reports infinite cost — the documented behaviour for an
unreachable destination. A `SearchObserver` subclass overriding one hook collects
what it visited. Reachability here is therefore measured with the same searcher
§4 describes and §5 validates, not with a second implementation written to
measure the first.
