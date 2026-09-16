# Talk track — A1 Flight Route Planner

A spoken script for the 24-slide deck (`make deck`, order per `manifest.txt`)
plus a live switch to `notebooks/demo.ipynb`. Budget: **30 minutes**, hard
ceiling. This is a script, not the deck — nothing here is projected; read it,
don't put it on a screen.

Numbers below were spot-checked against
`experiments/search-cost/results.json` and the executed cells in
`notebooks/demo.ipynb`, not copied from memory.

This is the relaxed version of this talk track — a tighter 20-minute cut
existed first and felt rushed. This one gives every technical slide room to
land, and lets the live demo actually show its scaling and correctness
evidence instead of only the single comparison query.

## Time budget (sums to 30:00 exactly)

| Section | Slides | Target |
|---|---|---|
| Open | title, agenda | 0:55 |
| The problem | travelers-dilemma | 1:30 |
| The data | dataset-and-sources, cleaning, snapshots | 2:30 |
| The design | why-the-layers-exist, adjacency-list, core-api | 2:00 |
| The algorithms | bfs, min-heap, dijkstra, astar-consistency | 6:00 |
| Correctness | correctness-parity | 1:30 |
| The cost | complexity, nodes-expanded, runtime | 3:45 |
| Seeing it | route-map, us-route-map | 2:30 |
| **Live demo** | demo (Jupyter) | **6:30** |
| Close | lessons, conclusion | 2:20 |
| Reference | references, questions | 0:30 |

---

## 1. Title

**0:25**

Traiectoria Optima — a flight route planner over the real OpenFlights
network: 3,387 airports, 66,332 routes. The question we're answering
tonight: does informed search actually pay for itself, or is that just
something textbooks assert? Everything I show you is measured against a
pinned snapshot of that network, not a toy example.

## 2. Agenda

**0:30**

Six stops: the problem, the data, the design, the algorithms, the evidence,
and seeing it — then a live demo against the real network. [give this one
a beat per bullet, this is the map for the next 25 minutes, worth letting
it land]

## 3. One question, three different right answers (travelers-dilemma)

**1:30**

Same query, Honolulu to Hartford, three algorithms, three different answers.
Fewest stops: two legs through Atlanta, 8,616 kilometers. Shortest distance:
three legs, 8,071 kilometers — 545 kilometers shorter, despite the extra
stop. A*: identical route to Dijkstra, same cost to the decimal, but only 10
node expansions against Dijkstra's 1,019. [pause here] That's the whole talk
in one line — same answer, over a hundred times less search — and everything
from here forward is us explaining why that's true and proving it holds up.
One footnote worth saying out loud: "cheapest" here means distance, because
OpenFlights has no fare data. BFS isn't wrong here — it's answering a
different question, and that distinction is going to come back more than
once.

## 4. Two sources, because the edges are the harder half (dataset-and-sources)

**1:00**

Two raw sources: OurAirports for vertices, OpenFlights `routes.dat` for
edges. 85,884 raw airports and 67,663 raw routes get cleaned down to 3,387
airports and 66,332 routes — a density of 0.32 percent. [point at the degree
chart] Look at the shape of that distribution: the top 10 airports carry 8
percent of all routes, and 38 percent of airports have two or fewer
departures. This is a hub-and-spoke network, not a uniform grid, and that
shape is exactly why A*'s heuristic gets to be so effective later — most of
the graph is irrelevant to most queries.

## 5. Cleaning: what got dropped, and why

**0:40**

Airports without a real three-letter IATA code or without a single route get
dropped; routes missing a valid origin or destination get dropped too — 1,331
of them, split almost evenly between origin and destination, which suggests
missing airports rather than some directional bias in the data. Every one of
those drops is logged as a row and a reason, not silently discarded — that
matters later when I talk about a bug we caught precisely because a drop
wasn't silent.

## 6. Why every number in this deck names a snapshot (snapshots)

**0:50**

`data/processed` is build output — `make flight_network` can overwrite it
without the filename changing, so a notebook reading it live could get a
different answer next month with nothing to say the data moved rather than
the code. So we freeze one working set at a time into a `Snapshot`, and its
id is a hash of its own contents — it can be superseded, but it can never be
silently edited. `Snapshot.open()` re-hashes every file against that manifest
before it hands back a single row, and on the full 66,332-route network that
costs about one hundredth of a second — cheap enough to do live, which is
exactly what the demo does in a few minutes. So when I say "8,071
kilometers," I mean "8,071 kilometers, from snapshot `bb90a8`," not
"whatever happens to be on disk right now."

## 7. The graph has never heard of an airport (why-the-layers-exist)

**0:50**

Four layers — core graph, geometry, pathfinding, flights — and the core
graph layer has never heard the word "airport." That's deliberate: it's
built by composition, not inheritance. `graph.shortest_path(a, b,
Dijkstra())` — the algorithm is passed in as a value, not baked into a class
hierarchy. 1,591 lines of this, and — I'll say this a few times tonight
because it's load-bearing — no `heapq` import anywhere in the codebase.

## 8. Why an adjacency list, in numbers (adjacency-list)

**0:45**

Why not a matrix? A matrix would need 11.4 million cells to represent
36,717 facts — over 99.6 percent of it wasted on routes that don't exist.
And it flat out couldn't represent what's actually in this data: the ORD to
ATL pair alone has 20 separate rows, one per codeshare. An adjacency list
can hold that; a matrix can't even express it. [this is also how we caught a
real bug — mirroring the graph into a plain NetworkX `DiGraph` for testing
silently collapsed 29,615 of those parallel edges down to one, because a
`DiGraph` can only hold one edge per pair]

## 9. The API the algorithms actually see (core-api)

**0:25**

One call builds the graph — `add_edge` is genuinely enough, re-adding an
airport is just a no-op. One call queries it with any algorithm as an
argument. One result type comes back either way — cost, path, nodes
expanded — with typed boundaries: unreachable comes back as `(inf, [])`, an
unknown airport code raises an exception, on purpose, so a typo can never
quietly look like a real answer.

## 10. BFS — fewest stops, and an honest counter (bfs)

**1:10**

Plain FIFO ring expansion, no weights — its cost is hop count, not distance,
and that's tagged explicitly on every result so it's never confused with a
real distance metric. [hold here] I want to be clear about something: BFS
isn't the naive algorithm we're here to beat. It correctly answers "fewest
stops." It's just answering a different question than "shortest distance,"
and that distinction is going to matter again when we look at where BFS and
Dijkstra actually disagree on the map later.

## 11. The min-heap, written rather than imported (min-heap)

**1:00**

An array read as a binary tree — index arithmetic, no node objects, no
pointers. Ties are broken by insertion order, which means an `Airport`
object never needs to support comparison at all — the heap handles it.
The whole surface is three methods: push, pop, peek. No `decrease_key`.
And to say the thing I keep saying: `heapq` is never imported anywhere in
this codebase. Every one of these numbers you're about to see came out of
code we wrote and can point to.

## 12. Dijkstra — and the price of not writing decrease_key (dijkstra)

**1:20**

Because every edge weight is non-negative, the first time you pop a vertex,
its distance is final — that's the whole correctness argument. But without
`decrease_key`, you can't update a vertex already sitting in the heap, so
instead we push a second, cheaper entry when we find a better distance, and
let a settled-set discard the stale one later when it surfaces. That costs
something measurable: about 1.7 to 1.9 pushes per expansion, meaning
roughly four in ten pops get thrown away as stale. It's a deliberate
trade-off, not an oversight, and we validated it holds up: cross-checked
against NetworkX across 200 long-haul queries, zero cost mismatches.

## 13. A* needs consistency, not just admissibility (astar-consistency)

**2:30**

This is the sharpest technical result in the whole project, so I'm going to
take a bit longer on it. Our A* implementation can't reopen a vertex once
it's closed — which is a completely standard implementation choice — but it
means the heuristic needs to be *consistent*, not merely *admissible*.
Those sound like the same thing in most textbooks' treatment, and they are
not the same thing here. We built a four-vertex counterexample by hand
first, where an admissible-but-inconsistent heuristic makes A* return a cost
of 3.0 when the true shortest path costs 2.5 — and the reported cost doesn't
even match the legs of the path it hands back. Then we went looking for this
for real: randomized fuzz-testing across 10,866 queries on 50 different
graphs found 27 cases where this actually produced a wrong answer, and 25 of
those 27 were self-contradictory in exactly that way. [pause] So why are we
safe in the real flight-planner code? Because the heuristic and every edge
weight come from the exact same haversine function, called at the same
Earth radius — that's an invariant of the code, not a geometric theorem —
and we verified zero violations across 6.6 million consistency checks, one
for every edge. Here's the twist I like best in the whole report: swap in
Vincenty, the *more accurate* ellipsoid model of the Earth, as the
heuristic instead, and admissibility breaks on 58.6 percent of edges — by up
to 25 kilometers. A more physically accurate model of the Earth makes a
*worse* heuristic, because correctness here is about agreement with your own
cost model, not agreement with reality.

## 14. How we know the answers are right (correctness-parity)

**1:30**

Four layers of testing, 1,118 tests total: a hand-checkable textbook fixture,
structural edge cases, cross-validation against an independent
implementation, and the randomized differential testing that found the A*
defect I just described. The headline number: 200 long-haul queries checked
against NetworkX, zero cost mismatches, worst divergence 3.6 times ten to
the minus twelve kilometers — that's floating-point summation noise, not
disagreement. One number that looks like a problem but isn't: BFS only
matches NetworkX's exact path on 142 of those 200 queries. That's not a bug
— those are legitimate ties at equal hop count, and two correct
implementations of the same algorithm are allowed to break a tie
differently while still agreeing on cost.

## 15. Every bound, checked against a measurement of our own code (complexity)

**1:10**

We didn't just cite the textbook complexity bounds, we measured our own
code's actual growth rate across eight narrowings of the network, spanning
a thirty-fold range in size. Graph construction hits its theoretical
O(V+E) almost exactly — a measured exponent of 1.01. But BFS comes in at
0.49, Dijkstra at 0.41, and A* at just 0.14 — because none of these search
algorithms exhaust the graph the way construction does; they stop the
moment they arrive at the goal. The pattern is consistent: the smarter the
algorithm, the further below its own worst-case bound it actually runs.

## 16. A* pays for the same answer with 130× to 784× less search (nodes-expanded)

**1:20**

Five long-haul queries, and the same story every single time: A* matches
Dijkstra's distance exactly — zero kilometers of difference across all
five — while expanding 130 to 784 times fewer nodes to get there. [point at
the ANC-MIA and SEA-MIA rows specifically] ANC to MIA is the smallest
saving in this set, at 130 times fewer expansions, and SEA to MIA is the
largest, at 784 times. This isn't one cherry-picked example from slide
three — it's the general pattern across every query we tested.

## 17. The ordering never changes across a 30× range (runtime)

**1:15**

A* is fastest at every one of eight graph sizes we measured, from a
single-airline subgraph up to the full world network — 9 to 31 times faster
than Dijkstra on the full graph. [point at the US-all-to-large row
transition] And here's the genuinely counter-intuitive result worth calling
out live: Dijkstra actually runs *faster* on a graph over four times
bigger — 3.6 milliseconds versus 5.0 milliseconds — because runtime tracks
how many airports actually get settled between the origin and the goal, not
how big the whole graph happens to be. Total graph size is the wrong mental
model for how long a search takes.

## 18. What an answer looks like (route-map)

**1:30**

[point at the map] Honolulu to Hartford again, but drawn this time: BFS in
blue through Atlanta, Dijkstra in orange through Salt Lake City and
Detroit — 545 kilometers shorter, visibly so. But here's the pair that
actually matters most: Sydney to JFK. Both algorithms return two legs — tied
on hop count, a table would call this a wash — and the two routes are 7,057
kilometers apart, because they leave Sydney in opposite directions around
the globe. No column in any table can show you that difference. A map can,
immediately.

## 19. One layer per airline (us-route-map)

**1:00**

Thirteen togglable map layers over the US network, 4,515 arcs total, one
layer per carrier plus an "other" catch-all. [this is the easiest slide to
compress further if you're running long — see the note at the end of this
document] One detail worth a sentence: the first six-color palette we chose
failed color-blind testing outright — Delta and US Airways were nearly
indistinguishable under tritanopia. It's four hues plus three dash styles
now, which is a small thing, but it's the kind of thing you only catch by
actually testing it, not by picking colors that look fine to you.

## 20. Live demo

**6:30 — switch to Jupyter, `notebooks/demo.ipynb`**

This is a live run against the pinned snapshot, not a replay of slides.
Run these cells, in this order, narrating as you go:

- **Cell 4** (open + verify the snapshot) — **0:30**. Say out loud what's
  happening: this re-hashes every one of the 66,332 route rows before
  handing back a single result. Point at the printed count — 3,387
  airports, 66,332 routes — matching slide 4.
- **Cells 6 and 8** (three-mode comparison + exact-match assertion) —
  **1:30**. Re-runs the Honolulu-to-Hartford query live. After it prints,
  point at the expansion counts — 125, 1,019, 10 — and note this matches
  slide 3 exactly, because it's the same snapshot. Let the assertion cell
  actually run — the audience sees Python assert the two floats are equal
  to the last bit, not just claim it.
- **Cells 10 and 12** (five-query benchmark table + expansion chart) —
  **1:45**. This is the scaling claim from slide 16, computed live rather
  than read off a table on a slide. Point at the "A* saving" column and
  the rendered chart together.
- **Cell 20** (interactive map, HNL→BDL) — **1:30**. The same BFS-vs-Dijkstra
  comparison as slide 18, but pannable and zoomable. Actually zoom into the
  Salt Lake City / Detroit routing for a few seconds — this is the most
  visual moment in the whole talk.
- **Cell 24** (NetworkX parity table) — **1:15**. Closes the demo on
  correctness rather than speed: point at "0" in the total-mismatches
  line, and specifically flag the BFS row — 142 of 200 identical paths — as
  the same legitimate-ties point made on slide 14, now backed by a live
  run instead of a claim.

Do not run cells 14–15 (runtime/scaling table and chart), the route-map
penalty table (cell 18), the antimeridian map (cell 21), or the boundary/
self-loop cells (26–28) — those either duplicate ground already covered on
slides 17–18, or add detail this budget doesn't have room for. If asked
about any of them live, answer from memory and point back to the relevant
slide rather than opening more cells.

[This assumes live execution goes fine — no fallback narration is scripted,
per instruction. If the room has no network, cell 20's map won't render;
skip straight to the close and mention the map is in the deck for anyone
who wants to see it after.]

## 21. What cost the most, and what it taught (lessons)

**1:15**

Three things, briefly. Data lies quietly: pandas read the literal string
"NA" as a null value, silently blanking the continent field for 39,715 of
85,884 airports, because OurAirports uses "NA" for both North America and
the country code for Namibia. Nothing crashed. Precision isn't correctness —
the Vincenty story from a few slides back, which is genuinely the headline
lesson of this whole project. And not every disagreement is a bug: parallel
codeshare edges, BFS losing on distance while winning on stop count, tied
paths against NetworkX — every one of those looked like a defect at first
and turned out to be a question that needed clarifying, not code that
needed fixing.

## 22. What it showed, and what is next (conclusion)

**1:05**

A* matched Dijkstra's answer exactly while expanding 130 to 784 times fewer
nodes and running 9 to 31 times faster — all built from scratch, no
`heapq`, anywhere. The bigger lesson is that measurement beat the docstring
twice: once finding that BFS answers a genuinely different question, once
finding that A* needs a consistent heuristic and not merely an admissible
one — found by a randomized query sweep, not a hunch. What's next: there's
an unused 611-line aircraft-performance prototype already sitting in the
repository that could swap great-circle distance for fuel-burn as the edge
weight, without any other layer of this design needing to change.

## 23. References

**0:15 — put the slide up, don't narrate it**

## 24. Questions

**0:15**

Repo is `traiectoria-optima`; `make report` and `make deck` build from the
same chapters, so they can't disagree with each other. Open it up.

---

## Suggested slide tweaks (not applied — for review before touching slide sources)

Slide content lives inside `docs/report/*.md` chapter files, which also feed
the PDF report via `drop-slides.lua`, so none of these were made directly.
Flagging them here instead:

- **`demo` slide** — its on-screen bullets don't mention that the notebook
  also has a full boundary/edge-case section (the PKN self-loop, unreachable
  destinations, unknown-airport handling). The live demo above still skips
  that section for time even at 30 minutes, so the audience only learns it
  exists if the slide or this talk track says so. Consider a one-line
  addition to the slide itself.
- **`nodes-expanded` / `runtime` slides** — the numbers on these slides were
  re-checked directly against `experiments/search-cost/results.json` while
  writing this talk track and match exactly (SFO-BOS 10/746/1, HNL-BOS
  132/1056/3, ANC-MIA 174/778/6; runtime 5.029 ms at 11,315 V+E vs. 3.610 ms
  at 51,536 V+E). No changes needed, but worth re-verifying again if the
  experiment is ever re-run before this talk is given.
- **`us-route-map`** — still the most tangential slide to the central
  A*-vs-Dijkstra claim; if rehearsal runs long even at 30 minutes, this is
  the first slide to cut entirely (saving ~1:00) rather than compress
  further, followed by trimming the demo's benchmark-table cells (cells 10
  and 12, saving ~1:45) if more time is needed.
