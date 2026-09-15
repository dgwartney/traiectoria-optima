# 9. Challenges and Lessons Learned

The algorithms in §4 were the assignment. They were not the hard part. Almost
everything that cost real time fell into one of two categories: **data that was
wrong in a way that looked right**, and **a correct-looking claim about our own
code that measurement contradicted.**

Six lessons, each one paid for:

| | Lesson |
|---|---|
| §9.1 | Data lies quietly. A silent wrong value costs more than a crash |
| §9.2 | A more accurate formula made A\* less correct |
| §9.3 | What looked like defects and were not |

## 9.1 Data that lies quietly

Every data problem in this project shared a shape: nothing raised, nothing
logged, and the pipeline produced a plausible answer about the wrong rows.

**`NA` means North America, and pandas means null.** `pd.read_csv` treats the
literal string `NA` as a missing value. The OurAirports export uses `NA` for
the North America continent code and for Namibia's ISO country code, so the
default read **blanks the continent of 39,715 of 85,884 airports — 46% of the
file — and the country of 303 more.** Nothing fails. The frame loads, the row
count is right, and every North American airport has simply forgotten which
continent it is on. `CsvLoader.TEXT_COLUMNS` names the columns to read verbatim
through `converters={column: str}`, and `tests/flight_planner/test_loader.py`
asserts both cases by name so the guard cannot be removed quietly.

This is the single most instructive bug in the project, because the library was
behaving exactly as documented. The failure was ours, and no amount of care
reading our own code would have found it — only looking at the data would.

**Ten codes that genuinely disagree.** After normalisation, ten of 1,492
scraped codes still did not join, because Wikipedia and OurAirports disagree
about the IATA code or because neither assigns one. Each was checked against
IATA's registry by hand and recorded in
`data/reference/iata_code_overrides.csv` with its reason — four stale Wikipedia
codes (Cabo San Lucas is `CSW`, not `CSL`), two fields IATA still recognises
that OurAirports marks closed, and two with no IATA code in either source,
matched on ICAO instead.

**And the honest postscript: that file now changes nothing.** The
`data-cleaning` experiment measures its effect and finds **8 rows, of which 0
carry a canonical code and 0 appear in the output.** The overrides were built
when the pipeline resolved coordinates airport-by-airport; the current pipeline
joins the vendored OurAirports table directly, and these airports fall out at
the `is_international` stage instead. The file is kept as the record of the
adjudication and `docs/data.md` still describes the reasoning — but nothing in
the delivered dataset depends on it, and **that only became visible once an
experiment measured it** rather than describing it. A hand-curated reference
file is exactly the sort of thing that keeps being cited long after the code
stopped reading it.

**What "cleaning" actually removes.** Of 85,884 airport rows, **76,831 have no
three-character IATA code** — helipads, seaplane bases, closed strips, private
fields. That single test is the whole airport filter; the missing-latitude,
missing-longitude and duplicate-code checks each remove **zero** rows, which
§2.3 now says rather than implying that three filters combine. On the route
side, 1,331 of 67,663 rows (2.0%) are dropped because an endpoint does not
resolve — 663 origins, 660 destinations, 8 with neither. All 1,331 are
committed row-by-row with their reason, because a count is not a provenance
record.

## 9.2 A more accurate formula made A\* less correct

This is the project's best finding, and it arrived as a surprise while trying
to justify something that was already working.

`AStar`'s docstring claimed the heuristic was **admissible**, which the textbook
says is the condition for optimality. Randomized differential testing (§5.5)
disagreed: on 27 of 10,866 generated queries A\* returned a suboptimal cost, and
on 25 of those the reported cost **contradicted the itinerary it handed back**.
The docstring was citing the right theorem for a different algorithm — ours
closes a vertex permanently on first expansion, so it needs the stronger
condition of **consistency** (§4.3).

That raised the obvious question: why has nothing ever gone wrong on flight
data? The tempting answer is geometry — a great-circle arc is the shortest path
on a sphere, so a direct distance cannot exceed a chain of flights. **That
answer is wrong, or at least not the reason.** It assumes the edge weights are
great-circle arcs, and they are, but only because `src/data/flight_network.py`
generates them by calling the same `Haversine()` class at the same 6371.0 km
radius the heuristic uses. Estimate and weight are not two measurements that
agree. They are one measurement, used twice.

So admissibility here is **an invariant between two parts of the build, not a
theorem about the earth** — and an invariant can be broken by an edit somewhere
else.

The framing makes a prediction the geometric one does not: replacing the
heuristic with a *more accurate* formula should break it. It does. `Vincenty`
measures on the WGS-84 ellipsoid and is the better model of the planet by any
physical standard. Substituted as the heuristic while the weights stay
haversine, its estimates exceed the truth on **38,901 of 66,332 edges (58.6%)**,
by up to 25.66 km — every one a potential silently-wrong route.

The textbook intuition fails in the same place. Haversine is usually described
as *underestimating* geodesic distance, because a sphere cuts corners an
ellipsoid does not. Measured across all 66,332 edges, haversine **exceeds** the
WGS-84 geodesic on 27,430 of them (41.4%), by up to 35.18 km. The error runs
both ways.

**A heuristic is not a measurement of the world. It is a lower bound on a cost
model, and it has to be consistent with the cost model rather than accurate
about reality.** That generalises well past flight routing, and it is the one
thing in this report we would not have predicted at the start.

## 9.2 A More Accurate Formula Made A* Less Correct

Randomized differential testing revealed that our A* implementation returned suboptimal costs on 27 of 10,866 queries—with 25 reporting costs that contradicted their returned itineraries. The core findings:

* **Wrong Theoretical Guarantee:**
* **Admissible Heuristic (Never Overestimates):** The rule of thumb that an estimate should never guess a route is longer than it actually is. The docstring claimed this alone guaranteed the best route, but that only applies if the algorithm is allowed to revisit and correct paths it already explored.
* **Consistent Heuristic (Never Skips Corners):** A stricter rule ensuring your estimate steadily decreases as you take real steps forward—the estimated distance to the destination can't drop by more than the actual distance you just traveled. Because our algorithm locks down a location forever the first time it reaches it (to save memory and time), it requires this stronger guarantee to avoid locking in a bad route too early.

* **Accidental Correctness via Code Coupling:** Flight routing originally worked not because of Earth's true geometry, but because edge weights in `flight_network.py` and the heuristic both called the exact same `Haversine()` function (radius 6371.0 km). Admissibility was an invariant of shared code, not physical geography.
* **Real-World Precision Breaks the Heuristic:** Replacing the heuristic with the `Vincenty` formula (which models the accurate WGS-84 ellipsoid) while keeping edge weights on spherical Haversine broke admissibility:
* Vincenty overestimated the Haversine edge weights on **58.6% of edges** (38,901 of 66,332), by up to 25.66 km.
* Overestimating actual model costs breaks the lower-bound requirement, causing A* to silently discard optimal paths.


* **Bidirectional Geometric Error:** Contrary to the belief that spherical calculations strictly underestimate ellipsoidal geodesics, Haversine also exceeded Vincenty on **41.4% of edges** (by up to 35.18 km).

**Core Takeaway:** A heuristic is not a measurement of the physical world. It is a lower bound strictly bound to an internal cost model—improving its real-world accuracy without updating the model will break optimality.

## 9.3 What looked like defects and were not

Three results that read as failures until the question was stated precisely.
Each cost time, and in two cases nearly cost a "fix" that would have made the
project worse.

**29,615 parallel edges.** 66,332 routes collapse to 36,717 distinct directed
pairs, so 44.6% of rows run parallel to another; ORD (Chicago)→ATL (Atlanta) alone carries twenty.
The first instinct was to deduplicate. That would have been wrong: OpenFlights
routes are *marketed services*, not distinct aircraft movements, and 11,982 of
them carry a codeshare flag. Twenty rows on one pair is several airlines
selling the same flight, which is a fact about the industry rather than dirt in
the file (§2.4). Keeping them also kept the rubric's duplicate-edge case
testable on real data instead of a fixture (§5.2).

**BFS is not simply the slow one.** On some queries BFS expands *fewer* nodes
than Dijkstra and still returns a worse route. That is not a bug in either: BFS
is answering *fewest stops* and Dijkstra *shortest distance*, and comparing
their costs directly means summing hops with kilometres (§7.5). The unit tag on
`SearchResult` exists because of this — two numbers both called "cost", measured
in different things, is how a comparison table becomes wrong.

**BFS disagrees with NetworkX on 58 of 200 queries.** Also not a defect. The hop
counts match on all 200; what differs is *which* equal-hop itinerary comes back,
and "fewest stops" does not name a single route when several exist. `SYD→JFK`
is what that ambiguity costs at the extreme: both implementations answer in two
legs, one going east through Los Angeles and the other west through Abu Dhabi,
**7,057 km apart** (§8.1). Reporting 142/200 as a pass rate would have been
mistaking a tie-break for a failure.

**The pattern in all three:** the disagreement was real and the interpretation
was wrong. Each was resolved by stating what the algorithm had actually been
asked, not by changing the algorithm.

<div class="deck-slide" id="lessons">

### What cost the most, and what it taught

<div class="cards">

<div class="card">

<span class="pill warn">Data lies quietly</span>

### `NA` means North America

pandas reads the literal `NA` as null — blanking the continent of **39,715 of
85,884 airports** and the country of 303 Namibian ones. Nothing raises.

The library behaved as documented. Only looking at the data would find it.

</div>

<div class="card">

<span class="pill astar">The headline lesson</span>

### Precision ≠ correctness

Vincenty is the better earth model. As A\*'s heuristic it overestimates on
**38,901 of 66,332 edges**.

A heuristic is a lower bound on a **cost model**, not a measurement of the
world — it must agree with the weights, not with reality.

</div>

<div class="card">

<span class="pill dijkstra">Not every defect is one</span>

### 3 disagreements, 0 bugs

29,615 parallel edges are codeshares, not dirt. BFS expanding fewer nodes is a
different *question*. BFS differing from NetworkX on 58/200 is an equal-hop
**tie**.

Each was fixed by stating the question, not the code.

</div>

</div>

<p class="footnote">`experiments/data-cleaning`, `experiments/heuristic-admissibility`, `experiments/networkx-parity`; world snapshot `2026-09-11-bb90a8`.</p>

</div>
