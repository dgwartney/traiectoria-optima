# 8. Visualization

§7 compares the algorithms in a table of numbers, and for two of the three
query pairs the table is enough. For the third it is not. `SYD→JFK` is answered
by BFS and Dijkstra in **the same two legs**, so nothing in the hop column
distinguishes them — and yet the answers are 7,057 km apart, because the two
itineraries leave Sydney in opposite directions. No column in §7 says that. A
map does.

So the visualization work is not decoration on a finished result. It is the
only representation in which one of the project's findings is legible at all.

`flight_planner.viz` is 1,401 lines in nine modules, built on **folium for the
map, pyproj for the geometry, and Playwright for the screenshot** — all three
imported lazily, inside the method that needs them, so a reader who only wants
the graph library never installs a browser. All three sit in the `notebooks`
or `dev` dependency groups; the published wheel still depends on `pandas` and
nothing else (§3).

## 8.1 What an answer looks like

The comparison the chapter exists to draw: `HNL→BDL`, both algorithms on one
map, each route its own toggleable layer.

![HNL (Honolulu)→BDL (Hartford) by both algorithms. BFS in blue takes two legs via Atlanta;
Dijkstra in orange takes three via Salt Lake City and Detroit, and is 544.7 km
shorter.](../images/route-map-hnl-bdl.png)

The picture makes the trade concrete in a way the numbers do not: BFS's
two-leg itinerary is a longer *line*, visibly bending south to Atlanta before
turning back up the coast, while Dijkstra's three-leg route runs closer to the
great circle it is trying to approximate. Fewest stops and shortest distance
are different questions, and here that difference has a shape.

`experiments/route-map` records three pairs, each chosen to make a different
point:

| Pair | Dijkstra | BFS | The point |
|---|---|---|---|
| `HNL–BDL` | 8,071.5 km, 3 legs | 8,616.2 km, 2 legs | The ordinary trade: one fewer stop costs **544.7 km** |
| `ANC–PVD` | 5,876.9 km, 3 legs | 7,497.2 km, 2 legs | The widest gap found — one stop for **1,620.3 km** |
| `SYD–JFK` | 16,035.3 km, 2 legs | 23,092.6 km, 2 legs | **Same leg count, 7,057.3 km apart.** Hops cannot explain it |

That last row is the one §5.4 predicted. The parity sweep found BFS returning a
different-but-equally-short itinerary from NetworkX on 58 of 200 pairs, because
"fewest stops" does not name a single route when several exist. `SYD–JFK` is
what that ambiguity costs when the tie is broken badly: Dijkstra goes east
through Los Angeles, BFS goes west through Abu Dhabi, both in two legs, and one
is 44% longer.

## 8.2 Great circles, not straight lines

A `PolyLine` between two coordinate pairs draws as a straight line in Web
Mercator. That is neither the path an aircraft flies nor the distance
`Route.distance_km` reports — so drawing it straight would put a picture next
to a number that contradicts it. Appendix C makes this argument for distance;
a map has to make it too.

`viz.Geodesic` interpolates along the great circle with pyproj's `Geod.npts`
and returns the intermediate points. Every curve in this chapter's figures is
that, not styling.

Six interpolated segments is the default, and the reason is measured rather
than chosen: at the line weight the context network is drawn with, 6 segments
is indistinguishable from 24 and less than half the file size (§8.4).

## 8.3 The antimeridian, and the framing problem underneath it

`Geod.npts` returns longitudes normalized into [−180, 180]. A route crossing
the dateline therefore yields a coordinate list that jumps from `−179` to
`+179`, and Leaflet draws a line straight back across the entire map:

![Auckland to Los Angeles with no unwrapping: the line runs east across the
whole Pacific to a point off Chile, then back up to
California.](../images/viz-dateline-naive.png)

This is not hypothetical, and it is not rare. The committed world snapshot
holds **647 route rows — 137 distinct airport pairs — whose shorter great
circle crosses the antimeridian.** Any map of this network hits the bug 137
times.

The fix is to **unwrap rather than normalize**: when consecutive longitudes
differ by more than 180°, keep adding or subtracting 360° so the sequence stays
continuous. `AKL→LAX` at eight interpolated points, before and after:

```
naive:      174.8  -176.0  -168.0  -160.9  -154.3  -147.9  -141.4  -134.5  -127.0  -118.4
unwrapped:  174.8   184.0   192.0   199.1   205.7   212.1   218.6   225.5   233.0   241.6
```

Past +180 and still ascending — one continuous line east across the Pacific,
which is what Leaflet needs.

**And that creates a second problem, which is really the same one.** Unwrapped
geometry lives *outside* [−180, 180]: the `AKL→LAX` line is drawn from 174.8°
to 241.6°. A bounding box built from the two airports' own coordinates spans
−118.4 to 174.8 — the wrong way round the planet, and a box that **does not
contain the line it was asked to frame.** So `MapLayer` reports the points it
actually drew and `RouteMap` frames itself on those, rather than letting the
map infer bounds from airport positions. Markers are shifted into the same copy
of the world as the lines for the same reason: a marker left at its raw
longitude renders one globe to the west and falls off the edge of the frame.

![SYD (Sydney)→JFK (New York City) unwrapped and framed on the drawn coordinates: one continuous line
across the Pacific, both endpoints on it, and a frame 135° wide rather than
404°.](../images/route-map-syd-jfk.png)

One more subtlety appears only on multi-leg routes, and it is why that frame is
135° wide instead of 404°. `Geodesic` unwraps *within* a leg, starting from
that leg's own origin — so `SYD→LAX` ends at 241.6° while `LAX→JFK` begins
again at its raw −118.4°, a 360° discontinuity between two legs that are each
individually correct. `PathLayer` shifts each leg into the copy of the world
the previous one finished in. Without that, the map frames itself over more
than a full globe and zooms out past the route it was drawing.

Only Dijkstra is drawn in that figure, deliberately. BFS's `SYD→AUH→JFK` leaves
in the opposite direction, so drawn together the two answers span the whole
planet and neither is legible. That is also why §8.1's table has to carry the
`SYD–JFK` row in numbers *and* the chapter has to explain it in prose: it is
the one comparison that defeats both a table and a single picture.

`tests/flight_planner/viz/test_geodesic.py` pins all of it — the unwrapping,
the westward case, the 647 rows and 137 pairs in the snapshot, and that **every
one of those 647 routes draws with zero discontinuities.** The bug is invisible
on a US-only network, which is exactly why it needs a test rather than a
careful author.

## 8.4 Making the whole network drawable

The route layer that sits *under* an answer is the expensive part. Drawing all
66,332 routes the obvious way — one `folium.PolyLine` each, 24 interpolated
points — produces **109.21 MB of saved HTML in 33.1 s.** `NetworkLayer` brings
that to 4.61 MB in 1.2 s, and **none of the saving comes from drawing less:**

| Change | Saved HTML |
|---|---|
| One `PolyLine` per route, 24 segments | 109.21 MB |
| One `GeoJson` layer instead of N `PolyLine`s | 38.82 MB |
| 6 interpolated segments instead of 24 | 17.92 MB |
| One feature per **airport pair** instead of per route row | **4.61 MB** |

Each row is a different kind of saving. The first is about how folium emits
JavaScript — one statement per `PolyLine` against one blob of coordinates for a
`GeoJson` layer. The second is resolution nobody can see at continental zoom,
along with rounding coordinates to three decimal places (about 110 m).

**The last row is the interesting one, and it is not really an optimisation.**
66,332 route rows are only **18,814 distinct airport pairs** (§2.5's
undirected count), because the route table is keyed by flight number and a busy
city pair appears three or four times. Drawing per row paints the same line
over itself — paying in file size every time, *and* darkening it on screen in a
way that misrepresents the geometry. Collapsing to distinct pairs is a 3.9×
saving and the more truthful picture. The fast path and the correct path are
the same path, which does not happen often enough to pass up.

**The context layer is off by default**, and that is an honesty decision rather
than a size one. Drawn underneath, the whole network buries the answer it sits
beneath — [`docs/visualization.md`](../visualization.md#four-conclusions-the-helper-should-bake-in)
carries the side-by-side. `NetworkLayer.show()` returns `False`
unconditionally — the caller cannot forget to switch it off — so the context
sits in the layer control unchecked, and a reader turns it on when their
question becomes "what else was available?".

## 8.5 Colour, and what it has to survive

Three algorithms need three colours, and the constraints are more numerous than
they look. `viz.palette` assigns colour **by what a series means, never by the
order it was added**, so adding a fourth algorithm cannot repaint the three
already on screen.

The slots are validated rather than picked: worst all-pairs colour-vision-
deficiency ΔE of **9.4**, normal-vision ΔE **20.9**, and contrast at least
**3:1** against the surface they are drawn on. Each series also carries a
**shape** — circle, square, triangle — because identity has to survive
greyscale printing, and a reader with a monochrome printer is not an edge case
for a submitted report.

Two decisions worth stating:

- **The palette is shared with `experiments/search-cost/plots.py`.** A chart
  and a map on the same slide therefore agree about which colour is Dijkstra.
  Two modules each picking "blue for the first series" is how a deck ends up
  contradicting itself between adjacent figures.
- **Scenery is not drawn from a series slot.** The context network and the
  airport markers are grey, not a fourth categorical colour, because they are
  scenery rather than findings — given a series colour they would compete with
  an algorithm for meaning.

There are two palettes, stepped per surface rather than flipped: the report and
GitHub get the light one, the reveal.js deck the dark one.

## 8.6 Getting an interactive map into a static report

A Leaflet map cannot go into a PDF, and this report is a PDF. There is also a
committed-notebook rule in the way: `tests/experiments/test_committed.py`
asserts that **every committed experiment notebook carries no stored output**,
so an inline map is gone the moment the kernel dies. Anything the report or the
deck cites has to be written to a file.

`viz.MapExporter` does that — HTML always, and PNG through a headless
Playwright browser. It is a separate class from `RouteMap` because the two need
different things: HTML needs only folium, while the screenshot needs a browser
that is a repository tool rather than part of the package contract. Both
figures in this chapter were written by `experiments/route-map/explore.ipynb`
through that exporter, to `docs/images/` and `slides/images/` in the same call.

**One trap found by fetching a tile rather than reading documentation.** The
prototype's first basemap default was CartoDB positron, which under folium
0.20.0 renders **`API KEY REQUIRED` stamped diagonally across every tile.**
Stadia returns HTTP 401 for every tile request. So `RouteMap` refuses the whole
`cartodb` / `carto` / `stadia` / `stamen` family **at construction**, rather
than letting a watermarked map be discovered after it is already in a report.

The detail worth carrying forward: **`xyzservices` reports the Stadia providers
as requiring no token.** Provider metadata said the tiles were free; fetching
one said otherwise. Only `OpenStreetMap` works without a key, and it is the
default.

<div class="deck-slide" id="route-map">

### What an answer looks like

<div class="cards two figure-left">

<div class="card figure">

![](../../slides/images/route-map-hnl-bdl.png)

<p class="caption">`HNL→BDL`. BFS in blue, two legs via Atlanta. Dijkstra in orange, three legs via Salt Lake City and Detroit — and 544.7 km shorter.</p>

</div>

<div class="card">

<span class="pill warn">Where the table fails</span>

### SYD (Sydney)→JFK (New York City), same 2 legs

Dijkstra east via Los Angeles: **16,035 km**. BFS west via Abu Dhabi:
**23,092 km**.

**7,057 km apart at identical hop counts** — the two answers leave Sydney in
opposite directions, and no column in §7 says so.

<span class="pill dijkstra">The geometry is not free</span>

### 647 routes cross the dateline

Normalized longitudes jump ±180° and Leaflet draws the line back across the
map. Unwrap, then frame on the *drawn* points rather than the airports.

</div>

</div>

<p class="footnote">`experiments/route-map`, world snapshot `2026-09-11-bb90a8`; folium 0.20.0, pyproj 3.7.2.</p>

</div>
