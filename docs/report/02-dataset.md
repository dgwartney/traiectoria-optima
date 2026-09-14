# 2. Dataset

## 2.1 Data sources

The project catalog names one source — OpenFlights airports and routes — and we
use two. The edges come from OpenFlights `routes.dat`, which is the only open
table of scheduled airline service at this scale. The vertices come from
**OurAirports** instead of OpenFlights' own `airports.dat`, because the edges
are the harder half and the airports have to be good enough to resolve them.

| Source | Raw rows | What we take from it |
|---|---|---|
| OurAirports `airports.csv` | 85,884 | Airport identity, coordinates, and the descriptive columns |
| OpenFlights `routes.dat` | 67,663 | Airline, origin, destination, codeshare flag, stops, equipment |
| Wikipedia list of international airports | 1,329 airports | The `is_international` flag |

`airports.dat` carries 14 fields for 7,698 airports; OurAirports carries 85,884
rows and adds `iso_region`, `continent`, `scheduled_service`, `type` and
`wikipedia_link`, and gives country as an ISO code rather than a free-text name.
That difference is load-bearing rather than cosmetic: `type` and `iso_country`
are the two columns the experiment catalog narrows on, so the 94-airport US
slice in §2.2 exists only because the airport table has them. A third
column, `is_international`, is not in either source — it comes from a scrape of
Wikipedia's list of international airports, and marks 1,329 of the 3,387. It is
independent of `type`: 116 large airports are absent from that list and 364
medium ones appear on it, so "large" and "international" are two different
questions rather than two spellings of one.

<div class="deck-slide" id="dataset-and-sources">

### Two sources, because the edges are the harder half

<div class="cards two figure-left">

<div class="card figure">

![](../../slides/images/degree-distribution.png)

<p class="caption">Out-degree, log–log. **38.4% of airports have two or fewer departures**; ATL has 915. Mean 19.6 against a median of 4 — the gap *is* the shape of the network.</p>

</div>

<div class="card">

<span class="pill">Where it comes from</span>

### 85,884 vertices, 67,663 edges

**OurAirports** for the airports, not OpenFlights' own `airports.dat` — it
carries `type` and `iso_country`, which are the columns every narrowing in
this project filters on.

**OpenFlights `routes.dat`** for the routes: the only open table of scheduled
service at this scale.

<span class="pill mute">What it becomes</span>

### 3,387 airports, 66,332 routes

Sparse — **0.32%** of the 11,468,382 ordered pairs a complete digraph would
have. 98.0% of airports sit in one strongly connected core, which is why a
long-haul query is real search rather than "no route".

</div>

</div>

</div>

## 2.2 Scope

The catalog's subject is the whole world airline network, and after cleaning
that is **3,387 airports and 66,332 routes** — measured in §2.5, not
estimated. The evaluation in §7 runs on all of it: its queries are long-haul
by design, and a route across an ocean is exactly the case where an
informed search has room to win. One experiment,
`experiments/shortest-vs-fewest`, deliberately works on a narrower slice — the
**94 US large airports and the 7,005 routes among them**, frozen as snapshot
`2026-09-12-3e4f9d` — because the question it asks is what skipping a layover
costs on a dense domestic network, where a fewest-stops answer and a
shortest-distance answer actually differ.

Every experiment names the frozen **snapshot** it ran against and re-verifies it
by checksum before reading a row, so a number in this report cannot quietly
drift away from the data that produced it. §2.5 and the evaluation in §7 both
run on the world snapshot `2026-09-11-bb90a8`.

A snapshot is the two cleaned CSVs plus a manifest recording, per file, its
SHA-256, its byte count, its row count, the narrowing criteria that produced it
and the commit of the code that wrote it. Opening one re-hashes every file
against that manifest and refuses to proceed on a mismatch, which costs 0.01 s
on the world network — cheap enough that a live demo can afford to verify its
own data. The processed CSVs under `data/processed/` are build output and are
rewritten whenever the pipeline runs, so nothing that needs a stable answer
reads them directly. That is the distinction that matters here: "3,387
airports" names a specific, hashed set of rows rather than whatever the last
build happened to produce.

## 2.3 Cleaning and preparation

Two filters, applied in that order, and each one reports what it discarded.
Every figure in this section is recorded by `experiments/data-cleaning/`, which
re-runs the pipeline over the committed raw files.

**Airports: 85,884 → 9,053 → 3,387.** An airport is *usable* if it has exactly
three characters of IATA code and both coordinates, and duplicate codes are
collapsed. Measured, **the IATA-code test does all of the work**: it removes
76,831 rows, and of the 9,053 that survive it, none is missing a coordinate and
none duplicates another's code. The other two conditions are guards that never
fire on this data — worth keeping, because a source that begins publishing a
coordinate-less airport should lose that row rather than acquire a vertex at
(0, 0), but worth reporting honestly as defensive rather than load-bearing.

Most of the 76,831 are airfields, heliports and seaplane bases with no
commercial service and so no IATA code, which makes this expected attrition
rather than a data problem. Of the 9,053 that remain, only the **3,387** that
at least one surviving route actually touches are written out — an airport no
flight reaches is not part of the airline network, and carrying it would
inflate every statistic in §2.5 and every denominator in §6.

**Routes: 67,663 → 66,332.** A route survives if *both* endpoints resolve to a
usable airport. **1,331 do not**, and the split is informative:

| Reason a route was dropped | Rows |
|---|---|
| origin does not resolve | 663 |
| destination does not resolve | 660 |
| neither resolves | 8 |
| **total** | **1,331** |

The near-symmetry of 663 against 660 is what you would expect if the cause is a
handful of airports missing from OurAirports rather than a systematic bias
against one direction of travel.

None of this is silent, and the standard for "not silent" is worth being
exact about, because this section used to fall short of it. The pipeline
records every skipped row as a `(row number, reason)` pair, and now **persists
them** — `make flight_network` writes `build-report.json` beside the processed
CSVs, and `experiments/data-cleaning/results.json` commits all 1,331, one
object each:

```json
{"row": 190, "reason": "origin does not resolve: LGP"}
```

Until that existed, the pipeline printed only `len(skipped)`. A count is a
claim; the rows are evidence. That reporting *is* the "data loading and
validation" the project asks for: a cleaning step that cannot say what it
removed is indistinguishable from a bug — and one that says only *how many* it
removed is closer to the bug than it looks.

The same experiment checks the cleaning against the frozen data it is supposed
to have produced. Re-deriving the network from the raw files yields 3,387
airports and 66,332 routes, and **every IATA code matches the committed
snapshot `2026-09-11-bb90a8` exactly** — none present in one and not the other.
So the snapshot's provenance is measured rather than asserted, and the
experiment exits non-zero if the two ever part company.

Edge weights are computed during this pass, with
`flight_planner.geo.Haversine` — the same tested implementation the search
algorithms use, rather than a second copy of the formula written in SQL. §3
explains why that matters more than it sounds, and §4.3 explains why the
heuristic depends on it.

<div class="deck-slide" id="cleaning">

### Cleaning: what got dropped, and why

<div class="cards">

<div class="card">

<span class="pill">Airports</span>

### 85,884 → 9,053 → 3,387

Usable means three IATA characters and both coordinates. Of the survivors, only
those a **surviving route actually touches** are written out.

</div>

<div class="card">

<span class="pill warn">Routes</span>

### 67,663 → 66,332

**1,331 dropped** — both endpoints must resolve. 663 origin, 660 destination,
8 neither. The near-symmetry says *missing airports*, not directional bias.

</div>

<div class="card">

<span class="pill mute">Not silent</span>

### Every drop is a `(row, reason)` pair

A cleaning step that cannot say what it removed is indistinguishable from a
bug.

</div>

</div>

</div>

## 2.4 What a cleaned route is, and is not

Two caveats belong here rather than in the results, because they qualify every
number that follows.

**A route is a marketed airline service, not a distinct flight.** 66,332 routes
run between 36,717 distinct airport pairs, so 29,615 of them are parallel to
another (§2.5). It is tempting to read that as competition, and partly it is —
564 distinct carriers appear in the table. But of the 45,754 route rows sitting
on a pair served more than once, **11,982 carry a codeshare flag**: the same
aircraft, sold under another airline's code. ORD→ATL has 20 rows. The graph is
therefore a multigraph of *marketing*, and the shortest-path algorithms treat
its parallel edges as what they are — alternative ways to fly one leg, all of
the same length.

**Eleven surviving rows have `stops > 0`**, so a handful of "routes" are not
nonstop legs. The edge weight is the great-circle distance between endpoints
regardless, which slightly understates those eleven. At 0.017% of the table it
changes no result in §7, and it is recorded here because the alternative —
noticing it later — is how a clean story becomes a wrong one.

## 2.5 Basic graph statistics

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

**Directed or undirected, and why both appear.** The 36,717 above counts
*ordered* pairs, so ATL→ORD and ORD→ATL are two. Collapsing direction as well
leaves **18,814** city pairs — which is the figure `experiments/route-map`
reports, because it is deciding how many arcs to draw and one arc serves both
directions. The two experiments are counting different things rather than
disagreeing, and each now states which in its own configuration.

Reconciling them yields a fact neither reports on its own: since every
undirected pair is served in one or two directions,
2 × 18,814 − 36,717 = **911 pairs fly in one direction only**. The other 17,903
are served both ways. That 911 is small — 4.8% of city pairs — and it is the
quantitative form of the in/out-degree symmetry noted below.

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
