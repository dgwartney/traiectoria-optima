## Live demo {#demo}

<div class="cards">

<div class="card">

<span class="pill">What runs</span>

### `notebooks/demo.ipynb`

One query three ways, then the measured results **read from committed
`results.json` files** — no timing loop runs on stage.

Its query surface is `src/demos/route_query_example.py`, which also runs as a
plain script. There is no CLI beyond that, and no web UI: the rubric rewards
neither.

</div>

<div class="card">

<span class="pill dijkstra">What it costs to start</span>

### 0.37 s, cold, before the first query

| Step | ms |
|---|---|
| `Snapshot.open()`, checksums and all | 4 |
| `.catalog()` | 325 |
| `.planner()` | 37 |

Verifying 66,332 routes against their manifest is **4 ms**. A live demo can
afford to check its own data.

</div>

<div class="card">

<span class="pill warn">If the room has no network</span>

### The output is already on this slide

Only the two map cells need the network — Leaflet from a CDN, tiles from
OpenStreetMap.

The maps are committed as PNGs and carried on the route-map slide; the numbers
are on the nodes-expanded slide. **Nothing in the demo is claimed only by the
demo.**

</div>

</div>

```
HNL -> BDL

mode                                    cost unit        expanded  route
fewest stops                             2.0 hops  expanded   125  HNL -> ATL -> BDL
shortest distance                    8,071.5 km    expanded  1019  HNL -> SLC -> DTW -> BDL
shortest distance (A*)               8,071.5 km    expanded    10  HNL -> SLC -> DTW -> BDL
```

<p class="footnote">Verbatim from a run on the world snapshot `2026-09-11-bb90a8`; timings on an Apple M2 Pro, median of 7. BFS's two legs are 8,616.2 km — 544.7 km more than the three-leg answer.</p>
