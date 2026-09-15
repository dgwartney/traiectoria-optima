# 1. Introduction

## 1.1 Executive summary

We built a flight route planner over the world airline network and used it to
settle one question: does informed search actually pay for itself, or is that
just something textbooks assert? The answer is yes, and by a wider margin than
we expected.

On the full cleaned network — **3,387 airports and 66,332 routes**, its routes
from OpenFlights and its airports from OurAirports (§2.1) — A\*
with a haversine heuristic returned **exactly** Dijkstra's shortest distance on
every long-haul query we asked, to the last decimal place, while expanding
**130× to 784× fewer airports** and running **9× to 31× faster**. That is the
result the project asks for, and §7 measures it rather than claiming it.

| | |
|---|---|
| Graph, heap, BFS, Dijkstra, A\* and both distance formulas | Written from scratch on Python dicts, lists, sets and `deque`. `heapq` and `networkx` appear nowhere in the package, and `scipy` is not a dependency of the project |
| Libraries | Loading, plotting and **validating** only, per the assignment's rules |
| A\* against Dijkstra | Identical distance on all five benchmark queries; 130×–784× fewer expansions; 31× faster on the world graph |
| Cross-validated | 200 long-haul queries against NetworkX, three algorithms, **0 cost mismatches** |
| Heuristic checked, not assumed | **6,633,200** consistency checks across all 66,332 real edges, **0 violations**, worst gap 1.8 × 10⁻¹² km — plus a four-vertex counterexample showing why *admissible* alone would not have been enough |
| Tests | **1,118 passing** across 61 files (1,041 with a plain `uv sync`; the mapping tests skip without the `notebooks` extras), `ruff` clean |

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
parts of the build** rather than a theorem about the earth. §9.2 draws the corollary: substituting a *more accurate* distance formula
breaks it.

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

<div class="deck-slide" id="travelers-dilemma">

### One question, three different right answers

<div class="cards">

<div class="card">

<span class="pill bfs">Fewest stops</span>

### BFS — 2 legs, 8,616 km

`HNL→ATL→BDL`. Every hop costs 1, so `edge.weight` is ignored entirely and the
cost column is a **hop count**.

</div>

<div class="card">

<span class="pill dijkstra">Shortest distance</span>

### Dijkstra — 3 legs, 8,071 km

`HNL→SLC→DTW→BDL`. Weight is great-circle distance. Skipping BFS's extra stop
costs **544.7 km**.

</div>

<div class="card">

<span class="pill astar">Same answer, less search</span>

### A\* — 3 legs, 8,071 km

The same route and the same cost **to the last digit of a float** — reached in
**10 expansions against Dijkstra's 1,019**.

</div>

</div>

<p class="footnote">"Cheapest" means distance: OpenFlights carries no fare data. BFS never "wins" — it was asked a different question, and its cost is measured in different units.</p>

</div>

## 1.3 Goals

Three, in priority order:

1. **Build the data structures and the algorithms ourselves.** An adjacency-list
   graph, an array-backed binary min-heap, then BFS, Dijkstra on that heap, and
   A\*. Nothing that a library could have handed us — and layered so that the
   graph and the searches have never heard of an airport (§3).
2. **Prove it works** — four layers, because each catches what the one before
   it cannot (§5): a known small input from the textbook, the structural edge
   cases, an independent implementation (NetworkX) for the correctness of the
   *design* rather than the code, and randomized differential testing for the
   case nobody thought to write. The last of those found a real defect.
3. **Measure the A\* claim on real data**, with instrumentation that counts what
   each search actually did rather than timing a black box.

## 1.4 The approach, in one page

We load the airport and route tables with pandas, clean them, and freeze the
result as a content-hashed **snapshot** (§2). SQLite is written from the same
frames as a second representation of the same data, but it is an output rather
than a stage — no part of `flight_planner` imports `sqlite3` (§3.5). Every experiment names
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
numbers above, plus three *further* complications it turns up that are not the
two named in §1.1. §8 shows a route on a map, §9 covers what went wrong, §10
concludes and §11 lists the sources.

Seven appendices carry what the chapters argue from rather than about:
[A](12-appendix-a-code-inventory.md) accounts for every line of code,
[B](13-appendix-b-data-structures.md) and [C](14-appendix-c-distance-formulas.md)
back §3 and §4.3, [D](15-appendix-d-networkx-parity.md) and
[E](16-appendix-e-astar-consistency.md) hold the full results §5 summarises,
[F](17-appendix-f-reproducibility.md) describes the snapshot and experiment
machinery every figure depends on, and [G](18-appendix-g-glossary.md) is the
glossary.

Everything reported here is reproducible: each figure comes from a committed
`results.json` written by a committed notebook or script, and §7.1 says which
numbers are properties of the algorithms (and will reproduce anywhere) and
which are properties of our laptop (and will not).
