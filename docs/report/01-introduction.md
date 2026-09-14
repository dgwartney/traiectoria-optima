# 1. Introduction

## 1.1 Executive summary

We built a flight route planner over the world airline network and used it to
settle one question: does informed search actually pay for itself, or is that
just something textbooks assert? The answer is yes, and by a wider margin than
we expected.

On the full OpenFlights network — **3,387 airports and 66,332 routes** — A\*
with a haversine heuristic returned **exactly** Dijkstra's shortest distance on
every long-haul query we asked, to the last decimal place, while expanding
**130× to 784× fewer airports** and running **7× to 25× faster**. That is the
result the project asks for, and §7 measures it rather than claiming it.

| | |
|---|---|
| Graph, heap, BFS, Dijkstra and A\* | Written from scratch on Python dicts, lists, sets and `deque`. `heapq` appears nowhere in the package |
| Libraries | Loading, plotting and **validating** only, per the assignment's rules |
| A\* against Dijkstra | Identical distance on all five benchmark queries; 130×–784× fewer expansions; 25× faster on the world graph |
| Cross-validated | 200 long-haul queries against NetworkX, three algorithms, **0 cost mismatches** |
| Heuristic checked, not assumed | **658,470** consistency checks on real data, **0 violations** — plus a four-vertex counterexample showing why *admissible* alone would not have been enough |
| Tests | **1,052 passing** across 57 files, `ruff` clean |

Two findings complicate the tidy story, and we think they are the more
interesting half of the report. **BFS is not simply "the slow one"** — on some
queries it expands *fewer* nodes than Dijkstra and still returns a worse route,
because it is answering a different question (§7.5). And **our A\* needs a
*consistent* heuristic, not merely an admissible one**, because it closes each
airport permanently on first expansion; randomized differential testing found
that gap as a real defect on 27 of 10,866 generated queries before we went
looking for it on flight data (§4.3). Our heuristic *is* consistent here, so
every committed result stands — but the reason is not spherical geometry. It is
that the pipeline generates the edge weights with the same formula at the same
radius the heuristic uses, which makes admissibility an **invariant between two
parts of the build** rather than a theorem about the earth. The corollary is
§9.4's: substituting a *more accurate* distance formula breaks it.

## 1.2 The problem

From the project catalog:

> Given the world airline network, find the cheapest / shortest / fewest-stop
> route between two airports, and show how informed search (A\*) expands fewer
> nodes than uninformed search (BFS/Dijkstra) while returning the same answer.

OpenFlights carries no fare data, so "cheapest" needs a definition. We read it
in the graph sense — lowest total edge cost — with edge cost equal to
great-circle (haversine) distance between the two airports. That gives three
query modes, and each one gets its own algorithm:

| Query | What it minimizes | Edge weight | Algorithm |
|---|---|---|---|
| Fewest stops | Layovers | Uniform, 1 per hop | BFS |
| Cheapest / shortest | Total great-circle distance | Haversine | Dijkstra |
| Cheapest / shortest, faster | Total great-circle distance | Haversine + heuristic | A\* |

The three are not interchangeable, and that matters for how the numbers read:
BFS's cost column is a hop count, Dijkstra's and A\*'s are kilometres. They are
never summed, and "BFS won" never means "BFS found a shorter route."

## 1.3 Goals

Three, in priority order:

1. **Build the data structures and the algorithms ourselves.** An adjacency-list
   graph, an array-backed binary min-heap, then BFS, Dijkstra on that heap, and
   A\*. Nothing that a library could have handed us.
2. **Prove it works** — unit tests for the shape of the code, and an
   independent implementation (NetworkX) for the correctness of the design,
   since the same people wrote the code and its tests.
3. **Measure the A\* claim on real data**, with instrumentation that counts what
   each search actually did rather than timing a black box.

## 1.4 The approach, in one page

We load the OpenFlights airport and route tables into SQLite, clean them, and
freeze the result as a content-hashed **snapshot** (§2). Every experiment names
the snapshot it ran against and re-verifies it by checksum, so a result can
never quietly drift away from the data that produced it.

From a snapshot we build an adjacency list keyed by IATA code, weighting each
route with the haversine distance between its endpoints (§3). On top of that
sit the three searches, all behind one interface: a search takes an origin and
a destination and returns a `SearchResult` carrying the route, its cost, and
the counters — nodes expanded, nodes pushed, peak frontier — that §6 and §7 are
built from (§4). Because the algorithm is a *parameter* to the planner rather
than baked into it, NetworkX could be wrapped as three more engines and run
through the identical code path, which is what makes the parity comparison
meaningful (§5).

## 1.5 How the rest of this report goes

§2 and §3 cover the data and the graph we build from it. §4 is the algorithms,
including the admissibility-versus-consistency argument for A\*. §5 is how we
know they are right. §6 derives the complexity bounds and then checks each one
against a measurement of our own code. §7 is the evaluation — the headline
numbers above, plus the three results that complicate them. §8 shows a route on
a map, §9 covers what went wrong, and §10 concludes.

Everything reported here is reproducible: each figure comes from a committed
`results.json` written by a committed notebook or script, and §7.1 says which
numbers are properties of the algorithms (and will reproduce anywhere) and
which are properties of our laptop (and will not).
