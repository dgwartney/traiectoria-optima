# 10. Conclusion

## 10.1 The headline result

Does informed search pay off on a real network, or is that only a textbook
claim? It pays, by more than expected — and the margin is measured, not
asserted.

- **Full cleaned network — 3,387 airports, 66,332 routes.** A\* with a
  haversine heuristic matched Dijkstra's shortest distance exactly, on every
  long-haul query, to the last decimal place.
- **130× to 784× fewer airports expanded, 9× to 31× faster** (§7).

Everything the assignment requires is built from scratch: adjacency-list
digraph, array-backed binary min-heap, BFS, Dijkstra, A\* — on Python dicts,
lists, sets and `deque`. `heapq` and `networkx` appear nowhere in the
package. Libraries only load, plot and validate (§11).

Every figure in this report is pinned: a content-addressed snapshot,
re-hashed on open, and a committed `results.json` an experiment wrote
(Appendix F). Ten experiments, re-derived by `tests/experiments/` on every
run.

## 10.2 The two findings that complicate it

Both complications came from measurement disagreeing with something already
written down.

**BFS is not simply "the slow one."**
- On some queries it expands *fewer* nodes than Dijkstra and still returns a
  worse route — it answers *fewest stops*, not *shortest distance* (§7.5).
- Its cost is a hop count, not a distance, which is why `SearchResult`
  carries a unit tag.

**Our A\* needs a *consistent* heuristic, not merely an admissible one.**
- It closes each airport permanently on first expansion, so the docstring's
  admissibility condition was the right theorem for a different algorithm.
- Randomized differential testing found the gap on 27 of 10,866 generated
  queries — 25 of those had a reported cost that contradicted the itinerary
  handed back (§4.3, §5.5).
- Every committed result still stands: the heuristic *is* consistent here,
  but not because of spherical geometry. The pipeline generates each edge
  weight and the heuristic estimate with the same `Haversine()` class at the
  same 6371.0 km radius — **admissibility is an invariant between two parts
  of the build, not a theorem about the earth.**
- Corollary: substituting Vincenty, the *more accurate* formula, breaks it on
  38,901 of 66,332 edges. Precision and correctness are different properties
  (§9.2).

## 10.3 What this project does not do

One list, since §7.6 and §5.6 each carry a version of it:

- **"Cheapest" means shortest distance, not lowest fare.** OpenFlights carries
  no fare data (§1.2).
- **No schedules, so no connections.** A route is an edge whether or not the
  flights on either side of a stop can actually be connected — layover
  feasibility, minimum connection times, day-of-week service: all outside
  the model.
- **A route is a marketed service, not an aircraft movement.** 29,615 of the
  66,332 rows run parallel to another and 11,982 carry a codeshare flag
  (§2.4).
- **The evaluation covers one graph shape.** The airline network is
  small-world — dense hubs, short paths. A sparse or grid-like graph would
  put the heuristic under real pressure; the measured exponents would not
  carry over (§7.6).
- **The oracle is independent, not infallible.** Agreement with NetworkX means
  two implementations made the same decisions (§5.6).

## 10.4 Future work

Three extensions, in the order we would take them.

**1. Decide whether to close the correctness gap, or accept it as documented.**
- Allowing A\* to reopen a closed vertex eliminates the suboptimal-result
  cases entirely, at a cost of **0.52% more expansions** (§4.3, §5.5,
  Appendix E). Worth adopting unless the report is content to leave the
  edge case as a known, documented limitation.

**2. Physics-aware routing — the one substantial thing already prototyped.**
- `src/models/flight/` is **611 lines nothing in the delivered system
  imports**: aircraft performance model, International Standard Atmosphere to
  the tropopause, an interpolated wind field with wind-triangle calculations,
  a gate-to-gate time/fuel-burn simulator, a payload-range envelope. Own
  tests, own runnable example.
- The payoff: a **different edge weight** — block time or fuel burn into a
  headwind instead of great-circle km. §3's layering makes this contained:
  `Route.distance_km` is domain data behind `edge.weight`; searches never
  look at anything else.

**3. Close the coverage gaps this report admits.**
- Demo smoke tests catch drift from the API but not a demo that runs and
  says the wrong thing — the remaining work is assertions, not execution.
- Bidirectional search is also worth implementing. NetworkX's `shortest_path`
  uses it, which is why only the A\* row of §7.3's timing table compares
  like with like (§7.6).

## 10.5 The lesson worth keeping

If one thing here generalises past flight routing, it's §9.2's: **a
heuristic is not a measurement of the world. It is a lower bound on a cost
model, and has to agree with the cost model rather than be accurate about
reality.** Found by trying to justify something that already worked, and
discovering the justification was wrong.

The habit that follows: a number nothing re-derives is a number that drifts.
Every figure in this report either names a checksummed result, or shouldn't
have been printed.

<div class="deck-slide" id="conclusion">

### What it showed, and what is next

<div class="cards">

<div class="card">

<span class="pill astar">The result</span>

### Informed search pays

A\* returned **exactly** Dijkstra's distance on every long-haul query, while
expanding **130×–784× fewer** airports and running **9×–31× faster**.

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

`src/models/flight/` — 611 prototyped lines of aircraft performance, ISA
atmosphere and wind — is **not** part of the delivered system.

Wired in, it swaps great-circle km for **fuel burn into a headwind**. §3's
layering means nothing else changes.

</div>

</div>

<p class="footnote">§7 for the measurements, §4.3 and §9.2 for the consistency argument, Appendix F for how every figure is pinned.</p>

</div>
