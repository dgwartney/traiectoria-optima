# 10. Conclusion

## 10.1 What the project set out to settle

The question was whether informed search actually pays for itself on a real
network, or whether that is something textbooks assert. It pays, by a wider
margin than we expected, and the margin is measured rather than claimed.

On the full cleaned network — **3,387 airports and 66,332 routes** — A\* with a
haversine heuristic returned **exactly** Dijkstra's shortest distance on every
long-haul query asked, to the last decimal place, while expanding **130× to
784× fewer airports** and running **7× to 25× faster** (§7).

Everything the assignment names as from-scratch work is from scratch. The
adjacency-list digraph, the array-backed binary min-heap, BFS, Dijkstra and A\*
are built on Python dicts, lists, sets and `deque`; **`heapq` appears nowhere
in the package**, and neither does `networkx` or `scipy`. Libraries do loading,
plotting and validating, which is what the assignment permits (§11).

What makes those numbers worth more than the same numbers printed from a
console is that they are pinned. Every figure in this report names a
content-addressed snapshot whose files are re-hashed on open, and a committed
`results.json` that an experiment wrote (Appendix F). Nine experiments,
re-derived by `tests/experiments/` on every run.

## 10.2 The two findings that complicate it

The tidy result is not the interesting half, and both complications came from
measurement disagreeing with something already written down.

**BFS is not simply "the slow one."** On some queries it expands *fewer* nodes
than Dijkstra and still returns a worse route, because it is answering *fewest
stops* rather than *shortest distance* (§7.5). Its cost is a hop count, not a
distance, which is why `SearchResult` carries a unit tag — two numbers both
called "cost" and measured in different things is how a comparison table
becomes wrong.

**Our A\* needs a *consistent* heuristic, not merely an admissible one.** It
closes each airport permanently on first expansion, so the textbook condition
its docstring cited was the right theorem for a different algorithm.
Randomized differential testing found the gap as a real defect on 27 of 10,866
generated queries — and on 25 of those the reported cost contradicted the
itinerary handed back (§4.3, §5.5).

Every committed result stands, because the heuristic *is* consistent here. But
the reason is not spherical geometry. It is that the pipeline generates each
edge weight with the same `Haversine()` class, at the same 6371.0 km radius,
that the heuristic calls — so **admissibility here is an invariant between two
parts of the build rather than a theorem about the earth.** The corollary is
the thing we would least have predicted at the start: substituting Vincenty,
the *more accurate* formula, breaks it on 38,901 of 66,332 edges. Precision and
correctness are different properties (§9.4).

## 10.3 What this project does not do

Stated plainly, because §7.6 and §5.6 each carry a version of it and a reader
deserves one list.

- **"Cheapest" means shortest distance, not lowest fare.** OpenFlights carries
  no fare data (§1.2). Nothing here prices a ticket.
- **No schedules, so no connections.** A route is an edge whether or not the
  two flights on either side of a stop can actually be connected. Layover
  feasibility, minimum connection times and day-of-week service are all
  outside the model.
- **A route is a marketed service, not an aircraft movement.** 29,615 of the
  66,332 rows run parallel to another and 11,982 carry a codeshare flag
  (§2.4).
- **The evaluation covers one graph shape.** The airline network is
  small-world — dense hubs, short paths. A sparse or grid-like graph would put
  the heuristic under real pressure and the measured exponents would not carry
  over (§7.6).
- **The oracle is independent, not infallible.** Agreement with NetworkX means
  two implementations made the same decisions (§5.6).

## 10.4 Future work

Four extensions, in the order we would actually take them.

**1. Decide the A\* consistency question in code, not only in prose.**
`src/validation/reopening.py` already holds a working reopening variant that
returns 0 suboptimal results where `AStar` returns 27, at a cost of **0.52%
more expansions**. The report documents the condition; the honest next step is
to either adopt the patch or narrow `astar.py`'s docstring to say *consistent*
where it says *admissible*. Both are small. Leaving them both undone is the
one option that should not survive.

**2. Physics-aware routing, which is the one substantial thing already
prototyped.** `src/models/flight/` is **504 lines that nothing in the
delivered system imports**: a commercial aircraft performance model, an
International Standard Atmosphere up to the tropopause, an interpolated wind
field with wind-triangle calculations, a gate-to-gate time and fuel-burn
simulator, and a payload-range envelope. It has its own tests and its own
runnable example, and it was written before the graph work converged on
distance as the cost function.

It is future work, not a delivered feature, and this is the only section of
this report that mentions it. But it is the natural next step, because it
supplies a **different edge weight**: block time or fuel burn into a headwind
rather than great-circle kilometres. That change would be almost entirely
contained — §3's layering means `Route.distance_km` is domain data behind
`edge.weight`, and the searches never look at anything else.

One caveat it creates, worth stating since §11 lists the libraries: **`scipy`
is a `dev`-group dependency used by nothing except `wind.py`.** It is in the
tree for code the deliverable does not run.

**3. The secondary feature that was specified and not built.** The project plan
listed nearest-airport-to-a-coordinate lookup; airports resolve by IATA code
only (§4.4). The pieces exist — `Airport` is a `Point`, and `geo.Haversine`
measures between any two — so it is a short addition rather than a design
problem.

**4. Close the coverage gaps this report admits.** `src/demos/` is fourteen
modules and thirteen are unexercised by any test (§5.6); a smoke test per
module would catch the failure that matters, which is a demo drifting from the
API it demonstrates. And bidirectional search is worth implementing for its own
sake — NetworkX's `shortest_path` uses it, which is why only the A\* row of
§7.3's timing table compares like with like (§7.6).

## 10.5 The lesson worth keeping

If one thing from this project generalises past flight routing, it is §9.4's:
**a heuristic is not a measurement of the world. It is a lower bound on a cost
model, and it has to agree with the cost model rather than be accurate about
reality.** We found that by trying to justify something that already worked,
and discovering the justification we had written down was the wrong one.

The corresponding habit is the one the experiment framework exists to enforce:
a number that nothing re-derives is a number that drifts. Every figure in this
report either names a checksummed result or should not have been printed.

<div class="deck-slide" id="conclusion">

### What it showed, and what is next

<div class="cards">

<div class="card">

<span class="pill astar">The result</span>

### Informed search pays

A\* returned **exactly** Dijkstra's distance on every long-haul query, while
expanding **130×–784× fewer** airports and running **7×–25× faster**.

Graph, heap and all three searches from scratch. `heapq` appears nowhere.

</div>

<div class="card">

<span class="pill warn">The lesson</span>

### Measurement beat the docstring

BFS is not "the slow one" — it answers a different question. And A\* needs
**consistency**, not admissibility; a randomized sweep found that as a real
defect before we went looking.

A heuristic must agree with the **cost model**, not with reality.

</div>

<div class="card">

<span class="pill">Next</span>

### A different edge weight

`src/models/flight/` — 504 prototyped lines of aircraft performance, ISA
atmosphere and wind — is **not** part of the delivered system.

Wired in, it swaps great-circle km for **fuel burn into a headwind**. §3's
layering means nothing else changes.

</div>

</div>

<p class="footnote">§7 for the measurements, §4.3 and §9.4 for the consistency argument, Appendix F for how every figure is pinned.</p>

</div>
