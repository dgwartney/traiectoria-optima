# 5. Correctness Testing

§4 describes three algorithms and claims they are right. This chapter is how
that is known, and it is a harder question than it looks: the person who wrote
the searches also wrote the tests, so a suite that passes proves the code
behaves as its author expected, not that the expectation was correct.

The project answers that in four layers, each addressing a different way of
being wrong:

| Layer | What it can catch | What it cannot |
|---|---|---|
| A known small input (§5.1) | A wrong answer on a graph a human can check by hand | Anything the seven-airport graph does not contain |
| Structural edge cases (§5.2) | A crash or a silent wrong answer on an empty, single-vertex, cyclic or disconnected graph | An answer that is well-formed and wrong |
| Cross-validation against NetworkX (§5.4) | A wrong *design*, because the oracle shares no code and no author | Anything both implementations get wrong the same way |
| Randomized differential testing (§5.5) | The case nobody thought to write — it found the A\* defect §4.3 is about | Failure modes the generator cannot produce |

The suite is **1,118 tests across 61 files**, of which 77 need the
`notebooks` dependency group — the map geometry cannot be tested without
pyproj, so those skip rather than fail on a plain `uv sync`. Its shape says something about
where the risk was judged to be:

| Area | Tests |
|---|---|
| `tests/flight_planner/` — the graph, heap, searches and formulas | 413 |
| `tests/validation/` — the oracle and differential harness | 256 |
| `tests/experiments/` — re-derives every committed result | 145 |
| `tests/deck/` and `tests/docs/` — the report and deck builds | 120 |
| `tests/data/` and `tests/scripts/` — the cleaning pipeline and tooling | 80 |
| `tests/demos/`, `tests/models/`, `tests/exercises/` | 87 |

`tests/validation/` is 1,349 lines of test against 1,336 lines of source — the
only subsystem in the repository with more test than code, which is what it
should be for the thing whose job is deciding whether everything else is
right.

## 5.1 A known small input

The first question to ask of a shortest-path implementation is whether it gets
the right answer on a graph small enough to work out by hand. `src/demos/book_example.py`
is that graph: **seven airports and eleven flights transcribed from the
flight-network example** in Goodrich, Tamassia and Goldwasser, *Data Structures
and Algorithms in Python* — the same textbook the course works from — with the
book's distances rather than computed ones. Nothing about it depends on the
cleaning pipeline, the snapshot, or the haversine formula. If the searches are
wrong, they are wrong here in a way a reader can see.

`BOS → LAX`, all three algorithms:

| | Cost | Route | Distance |
|---|---|---|---|
| Dijkstra | 4,526.0 km | `BOS→JFK→DFW→LAX` | 4,526.0 km |
| BFS | 2 hops | `BOS→MIA→LAX` | 5,791.0 km |
| A\* | 4,526.0 km | `BOS→JFK→DFW→LAX` | 4,526.0 km |

The disagreement is the one §4 opens with, at a scale where it can be checked:
BFS saves a stop and pays **1,265.0 km** for it.

This was a demo that printed, which is not evidence — a demo proves nothing
unless someone reads the output and knows what it should say.
`tests/demos/test_book_example.py` now asserts every number above, so a
regression in any of the three searches fails before anyone opens a console.

Two things the book's graph supplies for free. **SFO is a sink** — the figure
gives it an arrival and no departure — so `SFO → BOS` is a genuine unreachable
query on a hand-checkable graph, returning `(inf, [])` from all three
algorithms. And **the book gives no coordinates**, so every `Airport` defaults
to (0.0, 0.0) and the great-circle heuristic returns 0 for every pair. A zero
heuristic is admissible and consistent, so A\* is still correct — but it is
uninformed, and A\* expands exactly what Dijkstra expands. That is asserted
rather than glossed over, because "A\* matched Dijkstra" on this graph is a
weaker statement than it sounds and the test says which one it is.

## 5.2 The four structural edge cases

The assignment names four graph shapes the structure must handle: **empty,
single-element, cyclic or duplicate-edge, and disconnected.** One of the four
was already covered before this chapter was planned — `test_unreachable_goal`
in `test_bfs.py`, `test_dijkstra.py` and `test_astar.py` each build a graph
with a vertex no search can reach. `tests/flight_planner/test_graph_edge_cases.py`
is the other three, in 36 tests.

Two decisions about how they are tested are worth stating, because they are
what make the coverage mean something.

**Every case runs against all three algorithms.** A case handled by `Graph` but
mishandled by one search is still a defect, and the three do not share a code
path — BFS has no priority queue at all, and Dijkstra and A\* differ in what
they push. Parametrizing is what turns the claim from "Dijkstra handles this"
into "the structure handles this".

| Case | Behaviour, all three algorithms |
|---|---|
| Empty graph | `get_outgoing_edges` on an unknown vertex returns `[]`; a search returns `(inf, [])` having expanded nothing |
| Single vertex | Origin equals destination gives `(0.0, [])` with no search at all; any other destination is unreachable |
| Self-loop | Traversed, ignored, and never appears in a returned itinerary |
| Parallel edges | All are kept and all are considered; the cheapest wins |
| Disconnected | `(inf, [])` with the counters still populated — the search ran |

**The cyclic and duplicate cases also run on the real network, not only on
fixtures.** §3.6 argues that the cleaned data supplies one genuine self-loop
and 29,615 genuine parallel edges, and that filtering them would have been the
tidier choice and the worse one, because the handling would then never be
exercised on anything but a test fixture. That argument is only honest if the
tests use the data, so they do:

- **The self-loop.** Exactly one survives cleaning — flight `IL0016`,
  `PKN→PKN`, 0.0 km. It is not quarantined: it sits in a live adjacency list as
  one of PKN's seven departures. A real query out of PKN runs through
  all three algorithms, and the assertion is that the loop never appears in the
  itinerary handed back.
- **The parallel edges.** 66,332 routes collapse to 36,717 distinct directed
  pairs, so 29,615 run parallel to another — the figure §2.5 reports and the
  one §5.4 turns out to depend on. ORD→ATL carries twenty, and the test checks
  they are several airlines rather than one airline duplicated, because twenty
  copies of one carrier would mean the cleaning had a bug rather than that the
  route is busy.

### Three answers that are contract, not accident

§4.4 lists three boundary behaviours; they are tested here because the choice
between them is a correctness decision rather than a convenience.

| Query | Answer | Why not the alternative |
|---|---|---|
| Unreachable destination | `(inf, [])` | The search ran and found nothing. Counters stay populated, so "no route" is distinguishable from "no search" |
| Origin equals destination | `(0.0, [])` | Not an error. Zero cost, zero legs |
| Unknown IATA code | `AirportNotFoundError` | **Not** `(inf, [])`. "There is no such airport" and "there is no such route" are different facts, and collapsing them lets a typo return what looks like a routing result |

### One defect the edge cases found

The three structural cases were written to satisfy the assignment. Probing
`_reconstruct_path` while writing them turned up something the assignment does
not ask about: on a graph with a **negative cycle**, walking the predecessor
chain back from the goal never terminates. Negative weights are outside
Dijkstra's contract, so the search's answer would be meaningless either way —
but a function that hangs is far harder to diagnose than one that raises, and
a hang in a notebook looks like a slow query rather than a bug.

`_reconstruct_path` now tracks the vertices it has walked through and raises
`ValueError` naming the revisited one. `tests/flight_planner/test_reconstruct_path.py`
covers it in 7 tests, including the check that matters more: zero-weight
cycles and self-loops, which are *inside* the contract, still terminate
normally.

## 5.3 What the counters claim, and what checks them

§6 and §7 are built entirely out of `nodes_expanded`, `nodes_pushed` and
`peak_frontier`. Every one of those is a number the algorithm reports about
itself, which is the weakest kind of evidence there is — a search that
miscounts its own work would make §7's comparison wrong in a way no amount of
route-checking would reveal.

So they are verified against a count taken from outside. §3.4 notes that
`get_outgoing_edges` is the *entire* traversal interface: an algorithm cannot
touch a vertex without asking the graph for its edges. A `Graph` subclass that
records every such request therefore has an independent tally of what was
expanded, collected through the one door all three searches must use.
`tests/flight_planner/test_observers.py` asserts that
`result.nodes_expanded == len(graph.expanded)` for all three, and — separately
— that no vertex appears in that list twice.

That is the sense in which this project's central claim is **an executable test
rather than a sentence.** "A\* expands fewer nodes than Dijkstra for the same
answer" is not an assertion in the report backed by a printed counter; it is a
test that fails if either half stops being true.

## 5.4 Cross-validation against an independent implementation

1,118 tests say the code behaves as designed. They cannot say the design is
right, because the same person wrote both. For that the same questions have to
be put to an implementation sharing no code, no data structures and no author.
[NetworkX](https://networkx.org) 3.6.1 is that implementation.

**The comparison runs through our interface, not around it.** NetworkX is never
called directly. It is wrapped as three engines implementing
`PathfindingAlgorithm` — `NetworkXDijkstra`, `NetworkXBFS`, `NetworkXAStar` —
and handed to the same `planner.find_shortest_route(origin, destination, engine)`
every experiment uses. The engines return `Route` legs, not node keys, so leg
counting, flight numbers and the shape of `results.json` cannot tell which
engine produced them. That indifference is itself part of what is being
validated: it means a NetworkX result and ours are the same *kind* of answer,
not merely the same number.

Two decisions in the harness are worth more than the results they produced.

**The mirror is a `MultiDiGraph`, on purpose.** A `DiGraph` keeps only the last
edge added between any two nodes. On this network that **silently discards
29,615 of 66,332 routes** — the parallel edges §5.2 just finished testing —
after which every parity test passes while comparing a graph nobody built. The
failure is invisible precisely because it is total: both sides answer
confidently about a network that is not the one under test. Asserting `size`
against `len(graph.edges)` immediately after conversion is the assertion that
catches it, and it is the reason this appears in a chapter about correctness
rather than in a footnote about graph types. An oracle that agrees with you
about the wrong data is worse than no oracle.

**The NetworkX engines report their expansion counters as literal zero.**
NetworkX does not expose how many nodes it expanded, and there is no honest way
to recover it from outside. A plausible substitute — counting heuristic calls,
say — would put a fabricated number in the same column as Dijkstra's measured
one, in a table whose whole purpose is comparing those numbers. **Zero is
visibly not a measurement; a wrong count is not.** So these engines validate
costs and contracts, and expansion parity stays the job of §5.3's independent
count.

### Results

200 airport pairs drawn from the world snapshot under a recorded seed, run
through each engine:

| | Pairs | Cost mismatches | Worst divergence | Identical paths |
|---|---|---|---|---|
| Dijkstra | 200 | **0** | 3.6 × 10⁻¹² km | 200 / 200 |
| A\* | 200 | **0** | 3.6 × 10⁻¹² km | 200 / 200 |
| BFS | 200 | **0** | 0.0 | **142 / 200** |

Plus four deliberately unreachable pairs, where both implementations agree
there is no route.

The worst divergence is 3.6 × 10⁻¹² km — about four nanometres, and the same
order as the rounding in §4.3's consistency check. It is two implementations
summing the same floats in a different order, not two answers.

**The BFS row is the interesting one, and it is a finding rather than a
failure.** The cost column is what BFS is being asked about, and it matches on
all 200. What differs on 58 of them is *which* equal-hop itinerary comes back.
When several two-leg routes exist between two airports — and on a hub network
they usually do — "fewest stops" does not name one of them. Ours returns the
one its adjacency-list order reaches first; NetworkX returns the one its
adjacency order reaches first; both are correct answers to the question asked.
Reporting 142/200 as a pass rate would be mistaking a tie-break for a defect.
Dijkstra and A\* do not show it because distance almost never ties.

[Appendix D](15-appendix-d-networkx-parity.md) carries the full results.

## 5.5 Randomized differential testing

Cross-validation on real data has a blind spot: **flight data is well behaved
in ways that hide bugs.** Every weight is positive, the network is dense and
mostly connected, and the great-circle heuristic is consistent because §4.3's
pipeline invariant makes it so. None of the interesting failure modes live
there. Two hundred well-chosen queries over agreeable data can only confirm
what was already likely.

`src/validation/random_graphs.py` generates the cases that are missing: graphs
with zero weights, frequent ties, self-loops, parallel edges, disconnected
components, and — the one that mattered — **a heuristic that is admissible
without being consistent.** Weights are drawn from `(0.0, 1.0, 1.0, 2.5)`, with
`1.0` listed twice so ties are common and `0.0` present because a zero-weight
edge is legal for Dijkstra and easy to get wrong. Negative weights are outside
the contract and are never generated.

Two details of the generator are the reason the result can be trusted.

**Each case is built twice from one seed** — once as a `flight_planner.Graph`,
once as an `nx.DiGraph` — rather than built once and converted. Converting
would test the converter; building twice from the same sequence of decisions
tests the algorithms. It is the same argument as §5.4's `MultiDiGraph`, arrived
at from the other direction.

**The inconsistent heuristic scores every vertex once, at construction.** The
tempting version calls `rng.random()` inside the heuristic body, which is
shorter and wrong: a value that changes between calls is not a function, and
therefore not a heuristic. A\* would then be failing because it was handed
nonsense rather than because it has a defect.

### The defect it found

50 graphs, **10,866 queries**, under heuristics that are admissible but not
consistent:

| | Suboptimal results | Cost contradicts its own path |
|---|---|---|
| `AStar` | **27** | **25** |
| `ReopeningAStar` | 0 | 0 |
| NetworkX A\* | 0 | 0 |

The second column is the one that closes the argument. In 25 queries the
reported total and the itinerary returned beside it were different numbers: a
caller summing the legs would not get the figure the search handed back. That
is not a tolerance question, and no floating-point epsilon makes it go away.

This is the defect §4.3 is built around, and finding it this way is the point
of the layer. No unit test would have caught it, because the property it
violates — optimality under an inconsistent heuristic — is one nobody thought
to write a test for; the code's own docstring asserted admissibility was
enough. The minimal reproduction in §4.3 has four vertices, but it was
*extracted* from a random failure at seed 6, pair `n3→n12`, where A\* reported
7.764 against an optimum of 7.0. The search space found the case; the human
shrank it afterwards.

`src/validation/reopening.py` holds the fix — a closed set replaced by
`expanded_at: Dict[V, float]`, re-expanding when a cheaper g-score arrives —
deliberately kept *outside* `flight_planner` so the defect and the remedy could
be measured against each other before either was adopted. It costs **0.52% more
expansions** (40,792 against 40,580), and on this project's data the two
implementations agree exactly, because the heuristic here is consistent. §4.3
explains why the report documents the condition rather than adopting the patch.
[Appendix E](16-appendix-e-astar-consistency.md) carries the full study.

## 5.6 What this does not establish

Four honest limits, since the point of the chapter is knowing what is known.

**The oracle is not ground truth.** NetworkX is independent, not infallible.
Where both agree, the most that follows is that two implementations made the
same decisions — and §5.4's `DiGraph` trap is the concrete example of how two
confident answers can both be about the wrong thing.

**Coverage is not uniform, and the gaps are where the risk is lowest.** The
searches, the heap and the formulas carry 413 tests; the fourteen demos carry
42, and most of those are a smoke run — every demo is executed and required to
produce output, which catches the failure that actually happens to a demo
(an API it calls has moved) and not much else. One caveat is worth stating,
because it is why the smoke run is not the whole answer: `loader_example`
printed a heading reading `OMA -> OMA` above a route from OMA to SJC, and it
ran perfectly. Only reading the output found that. `src/models/flight/` has 34 tests for code the delivered
system never imports (§10), and `src/exercises/` is coursework outside the
deliverable (Appendix A). The suite is weighted toward the graded work, not
spread evenly across the repository.

**Randomized testing gives no coverage guarantee.** 10,866 queries is a
sampling of a space the generator defines, and the generator was written by
the same person as the code. It cannot produce a failure mode nobody imagined
putting into it — negative weights, for instance, are excluded by design, and
so the behaviour §5.2 hardened `_reconstruct_path` against came from probing
rather than from the sweep.

**Every number here is pinned to a snapshot, and to nothing else.** The parity
and consistency figures are measurements of `2026-09-11-bb90a8` and
`2026-09-12-3e4f9d`, re-verified by checksum on each run
([Appendix F](17-appendix-f-reproducibility.md)). They say the algorithms are
right about this network. A different network is a different measurement, which
is why the experiments are committed with their inputs rather than their
conclusions.

<div class="deck-slide" id="correctness-parity">

### How we know the answers are right

<div class="cards">

<div class="card">

<span class="pill">Four layers</span>

### 1,118 tests, then a second opinion

A known seven-airport graph from the textbook · the four structural edge cases
on fixtures **and on the real network** · NetworkX as an independent
implementation · randomized differential testing.

Unit tests show the code does what its author expected. Only the last two can
show the expectation was right.

</div>

<div class="card">

<span class="pill dijkstra">Parity</span>

### 200 pairs, 0 cost mismatches

Worst divergence **3.6e-12 km** — float summation order, not disagreement.

Identical paths 200/200 for Dijkstra and A\*, **142/200 for BFS**: equal-hop
ties, where "fewest stops" does not name one route. A finding, not a failure.

</div>

<div class="card">

<span class="pill warn">The defect</span>

### 10,866 random queries found it

Under an admissible-but-inconsistent heuristic: **27 suboptimal**, and **25
where the reported cost contradicted the path returned**.

No unit test would have caught it — the docstring asserted the wrong condition
was sufficient.

</div>

</div>

<p class="footnote">`experiments/networkx-parity` and `experiments/astar-consistency`; reference implementation NetworkX 3.6.1.</p>

</div>
