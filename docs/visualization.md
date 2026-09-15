# Visualizing Experiments

Every experiment in this repository currently ends in numbers. `shortest-vs-fewest`
prints `HNL -> BDL: Dijkstra 8,072 km in 3 legs, BFS 8,616 km in 2 legs` and records
that in `results.json`. The number is correct and the notebook argues it carefully,
but the reader has to hold three airports and two routes in their head to see what
happened.

This is the same pair, drawn:

![Dijkstra and BFS routes for HNL to BDL, drawn on an OpenStreetMap
base](images/viz-route-map.png)

The southern line is BFS's two-leg answer through LAX; the northern one is
Dijkstra's three legs. The picture makes the argument the notebook spends two
markdown cells on.

This document proposes a helper module that makes that picture a one-liner in every
experiment, lays out the design choices behind it, and compares Folium against the
alternatives.

> **Status: implemented.** `flight_planner.viz` now exists, built to
> [section 9](#9-recommendation), and `experiments/route-map/` demonstrates it
> against the world snapshot. [Section 12](#12-what-implementing-it-changed) records
> what building it taught that designing it had not — including two bugs this
> document's own prototype had. The design sections below are unchanged except
> where that section says otherwise, so they still read as the argument that was
> made before any of it was written.
>
> [Section 13](#13-what-faceting-changed) is a later addition, from
> `experiments/us-route-map/` — the first experiment to ask the layer system
> for thirteen simultaneous layers and a reader who filters them. It answers
> the pydeck caveat in [section 8](#8-competing-libraries) with a measurement,
> records a palette design that measuring **refuted** before it shipped, and
> names two things about the existing layer that nothing had exercised before.

It is also meant to be the *only* thing an implementer needs. Every number and
screenshot in it came from a working prototype run against committed snapshots —
the 94-airport `2026-09-12-3e4f9d` and the 3,387-airport world snapshot
`2026-09-11-bb90a8`. [Section 5](#5-what-the-prototype-measured) says what was
measured, [appendix A](#appendix-a--how-these-were-run) gives the exact commands so
any number here can be re-measured, and [appendix B](#appendix-b--the-prototype)
carries the prototype source, because a design document whose reference
implementation lives only in a scratch directory is a design document that has
already lost half of itself.

- [1. Where the project is today](#1-where-the-project-is-today)
- [2. What a helper actually has to do](#2-what-a-helper-actually-has-to-do)
- [3. Where the module should live](#3-where-the-module-should-live)
- [4. What the API should look like](#4-what-the-api-should-look-like)
  - [4.1 The class structure](#41-the-class-structure)
- [5. What the prototype measured](#5-what-the-prototype-measured)
- [6. Three problems the helper must solve once](#6-three-problems-the-helper-must-solve-once)
- [7. Getting a map into the PDF and onto a slide](#7-getting-a-map-into-the-pdf-and-onto-a-slide)
- [8. Competing libraries](#8-competing-libraries)
- [9. Recommendation](#9-recommendation)
- [10. What the rest of the repository has already decided](#10-what-the-rest-of-the-repository-has-already-decided)
- [11. Open questions](#11-open-questions)
- [12. What implementing it changed](#12-what-implementing-it-changed)
- [13. What faceting changed](#13-what-faceting-changed)
  - [13.1 What it measures](#131-what-it-measures)
  - [13.2 Answering section 8's objection](#132-answering-section-8s-objection)
  - [13.3 The palette had to be measured, and the measurement refuted the design](#133-the-palette-had-to-be-measured-and-the-measurement-refuted-the-design)
  - [13.4 Two things this found in the existing layer](#134-two-things-this-found-in-the-existing-layer)
  - [13.5 The committed HTML](#135-the-committed-html)
  - [13.6 The second tile trap: a key is not the only thing a basemap needs](#136-the-second-tile-trap-a-key-is-not-the-only-thing-a-basemap-needs)
- [Appendix A — how these were run](#appendix-a--how-these-were-run)
- [Appendix B — the prototype](#appendix-b--the-prototype)

---

## 1. Where the project is today

Three facts about the current state, all checkable:

**The experiments have no maps.** `experiments/sfo-bos-dijkstra/explore.ipynb` and
`experiments/shortest-vs-fewest/explore.ipynb` are entirely `print()` and
`experiment.record()`. Neither imports `folium`.

**The mapping that exists is exploratory and untransferable.**
`notebooks/view_routes.ipynb` draws a real map — airports as `folium.Marker`s in a
`FeatureGroup`, one route as a `pyproj` geodesic `PolyLine` — but it reads its data
straight out of `data/processed/flight_data.db` with `sqlite3` and hardcodes Boston
and San Francisco as literal `[lat, lon]` pairs. It knows nothing about `Airport`,
`Route`, `Catalog` or `Snapshot`. `notebooks/folium-groups.ipynb` is a nine-line
Folium tutorial about parks and cafés in San Francisco.

So the knowledge needed to draw a route — geodesic interpolation, feature groups,
layer control — exists in the repository exactly once, in a notebook that cannot be
imported, pinned to data that is not a snapshot. Copying it into each new experiment
is how every experiment ends up with a slightly different map.

**The dependencies are already in place.** `pyproject.toml` puts `folium>=0.20.0`
and `pyproj>=3.7.2` in the `notebooks` dependency group, which
`uv sync --group notebooks` (or `make notebook`) installs. The environment used for
the measurements below resolved to folium 0.20.0, pyproj 3.7.2.

`ipyleaflet>=0.20.0` was in that group too when this document was written, and was
dropped once the recommendation below settled on folium: nothing in `src/` ever
imported it. The comparison in [section 8](#8-competing-libraries) is why, and is
left as the record of the decision.

Note what is *not* there: the published wheel depends on `pandas` and nothing else,
deliberately. `pyproject.toml` says so in a comment — "everything a consumer needs,
nothing the repository merely uses". That constraint drives
[section 3](#3-where-the-module-should-live).

**And the data is already two orders of magnitude apart.** Three snapshots are
committed, and the helper has to survive both ends of them:

| Snapshot | Airports | Routes | Used by |
|---|---|---|---|
| `2026-09-12-3e4f9d` | 94 | 7,005 | `experiments/shortest-vs-fewest` |
| `2026-09-11-bb90a8` | 3,387 | 66,332 | `experiments/search-cost`, on `feature/search-instrumentation` |

That 9.5× in routes is the difference between "draw everything and don't worry" and
"drawing everything produces a file nobody can open", which is why
[section 5](#5-what-the-prototype-measured) measures both.

**There is also a deadline attached to this.** `docs/remaining_work.md` (on the
`docs/remaining-work-assessment` branch) records a rendered route map as a graded,
named project Outcome — task T8/#18, currently "Not started", alongside "at least
one plot of time vs. input size" which `experiments/search-cost` has since
delivered. Its Step 6 is titled "Visualization and graph statistics". So this is
not a nice-to-have refactor: the map is a deliverable, and slides 7/13/14/15 and
`report.md` §2 are the things waiting on it.

---

## 2. What a helper actually has to do

The domain types already carry everything a map needs, which is why this helper can
be small.

| Need | Where it already comes from |
|---|---|
| Airport position | `Airport(Vertex, Point)` — `.latitude`, `.longitude` |
| Airport labels | `.iata_code`, `.name`, `.city`, `.country`, `.type` |
| Leg endpoints | `Route.origin`, `Route.destination` — both `Airport` |
| Leg label | `.distance_km`, `.airline`, `.flight_number` |
| The set to draw | `Catalog.airports`, `Catalog.routes`, `Catalog.routes_from(...)` |
| The answer to draw | `FlightPlanner.find_shortest_route(...) -> (float, List[Route])` |

An `Airport` is a `Point`, so nothing has to translate coordinates. A `Route` holds
`Airport` objects rather than codes, so nothing has to look endpoints up. The
helper's whole job is:

1. Turn a list of `Route` into geodesic polylines (not straight lines — see
   [section 6](#6-three-problems-the-helper-must-solve-once)).
2. Turn a list of `Airport` into markers with consistent popups.
3. Put each of those in a named, toggleable layer.
4. Frame the map on what was actually drawn.
5. Use the same colors, weights and tile layer in every experiment.

Point 5 is the real deliverable. Any notebook author can write the first four in
twenty minutes; what they cannot do is guarantee that the red line means the same
thing in their experiment as in the one next door.

**The instrumentation branch does not change any of this.** `feature/search-instrumentation`
splits `pathfinding/algorithms.py` into one module per algorithm and adds a
`SearchResult`, but it is purely additive: `find_shortest_route()` still returns
`(cost, legs)`, and `Dijkstra` / `BFS` / `AStar` still import from
`flight_planner.pathfinding`, so every signature in the table above survives. What
it *offers* the helper is a richer source for a layer label — the new
`planner.search_route(origin, destination, algorithm)` returns a `SearchResult`
carrying `.cost` and `.path` plus `.nodes_expanded`, `.nodes_pushed` and
`.peak_frontier`. Layers named `Dijkstra (4,341 km, 746 expanded)` and
`A* (4,341 km, 1 expanded)` — the recorded SFO–BOS figures from that branch's
`results.json` — put the project's central claim in the legend. The helper should
therefore accept legs *or* a `SearchResult`, and read the counters only when they
are there — never depend on them, since the map has to keep working on `main`.

---

## 3. Where the module should live

Four options, and this is the decision that actually matters, because it determines
whether an experiment running in Colab can import the thing.

### Option A — a plain module under `notebooks/`

`notebooks/mapping.py`, imported as `from mapping import route_map`.

Cheapest possible change and it breaks nothing. But notebooks live in
`experiments/<slug>/`, not `notebooks/`, and the experiment notebooks are explicit
that they resolve nothing against a repository root — `Experiment.open(Path.cwd())`
with the comment "Nothing resolves against a repository root." A `sys.path` hack in
every experiment to reach `notebooks/` would undo exactly the property the
experiments layer was built for. **Rejected.**

### Option B — `src/viz/`, outside the wheel

Alongside `src/data/` and `src/demos/`, reachable through the `pythonpath` entries in
`[tool.pytest.ini_options]`.

Keeps the wheel's dependency contract pristine and gives the code a real home with
real tests. The problem is Colab: `docs/setup.md` and the experiment notebooks both
install the package with `%pip install -q ./traiectoria-optima`, which builds the
wheel — and `[tool.hatch.build.targets.wheel]` has `only-include = ["src/flight_planner"]`.
`src/viz/` would not be in it. A Colab user would get `ModuleNotFoundError` on a
notebook that works locally, which is the worst failure mode this project has.

### Option C — `flight_planner.viz`, in the wheel, with no folium dependency at all

A new layer in the package, next to `experiments/`, with Folium imported lazily
inside the functions that need it — and **nothing about folium in `pyproject.toml`**.

Not as a runtime dependency, and not as an optional extra either. An extra looks
tempting (`pip install 'flight_planner[viz]'`) but it still writes folium into the
published wheel's metadata and makes installing it the blessed path. The wheel's
contract is pandas and nothing else; mapping is a notebook concern, and the
`notebooks` dependency group is already where this project keeps notebook concerns.
`folium` and `pyproj` are in that group today and stay there.

So the package ships code that can use folium if it is present and says so plainly
if it is not. `import flight_planner` stays pandas-only: the top-level `__init__.py`
does not import `viz`, and `viz` itself imports nothing from folium at module scope
— so `from flight_planner.viz import RouteMap` succeeds in an environment without
it. The failure happens when a map is actually built, and the message is written for
the person who will see it, which is someone sitting in a notebook cell:

```python
def _folium():
    """Return the folium module, or explain how to install it.

    Deliberately imported here rather than at module scope: the package
    does not depend on folium, and nothing should fail until a caller
    actually asks for a map.
    """
    try:
        import folium
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "Mapping needs folium and pyproj, which are not part of the "
            "flight_planner package.\n"
            "  In a notebook (Colab or Jupyter), run in a cell:\n"
            "      %pip install folium pyproj\n"
            "  In a checkout of this repository:\n"
            "      uv sync --group notebooks\n"
            "Then restart the kernel and re-run this cell."
        ) from error
    return folium
```

Three things that message gets right, and that a bare `ModuleNotFoundError: No
module named 'folium'` does not:

- **It names both packages.** `pyproj` fails second, several cells later, otherwise.
- **It gives the notebook form first.** `%pip` rather than `pip`, because in Jupyter
  and Colab `!pip` installs into the wrong interpreter often enough to be a known
  trap, and this project's audience reaches this code from a notebook.
- **It says to restart the kernel.** Installing folium mid-session does not make the
  already-failed import succeed on a retry in every case, and "why is it still
  broken after I installed it" is the next question otherwise.

`pyproj` gets an identical guard. It is worth having the two checks share one helper
so the message stays in a single place rather than drifting between call sites.

Colab keeps its existing setup cell — `%pip install -q ./traiectoria-optima` —
unchanged, with `%pip install -q folium pyproj` alongside it in the notebooks that
draw maps. The experiment notebooks already have a setup cell that names exactly
what a Colab run needs; this adds one line to it in the notebooks that need it, and
nothing anywhere else.

The layering story holds up too. The package README describes a stack from `core/`
up through `experiments/`; `viz/` sits at the top, depending on `flights/` and
`geo/` and depended on by nothing. It is the only layer that reaches outside the
package's declared dependencies, which is worth a sentence in that README saying so
and saying why.

### How Option C sits with the rest of the repository

Option C is the one choice in this document that two sibling design efforts appear
to contradict, and an implementer will hit that within an hour. Recording it here
rather than leaving them to find it:

- **`experiments/search-cost/plots.py`** (on `feature/search-instrumentation`) opens
  with "Kept out of `flight_planner` on purpose: the wheel depends on `pandas` and
  nothing else, while `matplotlib` is a `dev`-group dependency. Plotting is
  something this repository does, not something the package offers."
- **`docs/networkx-validation.md`** (on `worktree-NetworkX`) says the same of its
  adapter: "Validation is the repository's concern, not the package's… the adapter
  belongs in `tests/` or `src/demos/` — not in `flight_planner/pathfinding/`."

Both of those are the principle Option C overrides, so the difference has to be
argued rather than assumed. It comes down to **how many callers there are**:

`plots.py` serves exactly one experiment. It lives beside its notebook, is imported
as `import plots` because the notebook's working directory *is* the experiment
directory, and no second caller ever needs it. Copying it would be the anomaly.
A route map is the opposite — every experiment wants one, which is the entire
premise of [section 2](#2-what-a-helper-actually-has-to-do)'s point 5. There is no
"beside its notebook" for code with five callers in five directories, and
[option A](#option-a--a-plain-module-under-notebooks) shows what reaching across
directories costs.

So the rule the repository is actually following is *"non-pandas concerns stay out
of the wheel's dependency metadata"*, not *"stay out of the package"* — and Option C
keeps the first rule exactly, since nothing about folium enters `pyproject.toml`.
`flight_planner.viz` is in the wheel; folium is not.

The honest cost of that position: `flight_planner.viz` is the only module in the
package that can raise `ModuleNotFoundError` on an install that satisfies its own
metadata. That is a real wart, it should be stated in `src/flight_planner/README.md`
next to the layer description, and it is the reason
[option B](#option-b--srcviz-outside-the-wheel) is worth re-reading before
committing to this. If a future reader decides the wart is worse than the `sys.path`
problem, Option B plus adding `src/viz` to `[tool.hatch.build.targets.wheel]`
`only-include` is the fallback — but then it ships in the wheel anyway and the
distinction was never real, which is itself the argument for Option C.

### Option D — a separate `flight-planner-viz` distribution

Cleanest dependency story, and completely disproportionate for one module in a term
project. It also doubles the release work every time `Route` gains a field.
**Rejected**, but worth revisiting if the viz layer ever grows a web app.

---

## 4. What the API should look like

**The implementation is class-based**, and not merely in the sense that `RouteMap`
happens to be a class. Each kind of thing that can be drawn is a class behind one
abstract base, the geometry is a class, the palette is a class, and the PNG export
is a class. Section 4.1 fixes that structure; the three API shapes that follow are
about what the *caller* types, which is a separate question from how the module is
built.

This is the repository's own pattern rather than an imported preference.
`geo/formula.py` holds a `DistanceFormula` ABC with `haversine.py` and
`vincenty.py` beside it; `pathfinding/strategy.py` holds a `PathfindingAlgorithm`
ABC with `dijkstra.py`, `bfs.py` and `astar.py` beside it, and its module docstring
says so explicitly — "each concrete algorithm lives in its own module beside this
one, mirroring how `geo/` keeps `DistanceFormula` in `formula.py` and each formula
in its own file". `viz/` should be the third instance of that shape, not a new one.

### 4.1 The class structure

```
flight_planner/viz/
    __init__.py      RouteMap, MapLayer, the layer classes, Palette
    layer.py         MapLayer (ABC)
    airports.py      AirportLayer(MapLayer)
    network.py       NetworkLayer(MapLayer)      -- the batched GeoJson bulk layer
    path.py          PathLayer(MapLayer)
    geodesic.py      Geodesic                    -- interpolation and unwrapping
    palette.py       Palette                     -- colours by meaning, not order
    routemap.py      RouteMap                    -- composes layers, owns the map
    export.py        MapExporter                 -- HTML and Playwright PNG
```

**`MapLayer`** is the abstraction that makes the rest work:

```python
class MapLayer(ABC):
    """One named, toggleable layer on a RouteMap.

    Subclasses decide what they draw and how they batch it; the map only
    needs a name, the folium object to add, and the coordinates actually
    drawn so that it can frame itself. That last one is not incidental --
    section 6 shows a dateline route whose drawn geometry lies outside its
    own endpoints' bounding box, so a layer that cannot report what it drew
    cannot be framed correctly.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the label shown in the layer control."""

    @abstractmethod
    def build(self, folium) -> Any:
        """Return the folium object to add to the map.

        Args:
            folium: The folium module, passed in rather than imported, so
                that the lazy-import guard lives in exactly one place.
        """

    @abstractmethod
    def drawn_points(self) -> Sequence[Tuple[float, float]]:
        """Return every [lat, lon] this layer actually drew, unwrapped."""

    def show(self) -> bool:
        """Report whether the layer starts visible. Overridden by NetworkLayer."""
        return True
```

Four things that structure buys, each of which is a defect in the prototype:

- **The `PolyLine`-versus-`GeoJson` split stops being a branch.** `PathLayer` emits
  one `PolyLine` per leg; `NetworkLayer` emits one deduplicated `GeoJson`
  ([below](#routes-is-not-path-with-different-arguments)). Same interface,
  different `build()`, and no `if len(routes) > some_threshold` anywhere.
- **Framing becomes correct by construction.** `RouteMap.finish()` fits to the union
  of every layer's `drawn_points()`, so the dateline bug in
  [section 6](#whatever-you-unwrap-you-have-to-frame) cannot recur by forgetting to
  accumulate — a layer that does not implement `drawn_points()` does not instantiate.
- **`Geodesic` is injectable.** `Geodesic(ellps="WGS84", segments=6)` as an object
  means the segment count and the unwrapping are set once and shared by every layer,
  and a test can substitute a straight-line stub without monkeypatching a module
  function.
- **A second backend stays possible.** [Section 8](#8-competing-libraries) floats
  Plotly or Cartopy as a later renderer; with `build(folium)` as the only
  folium-aware method, that is a sibling set of layer classes rather than a rewrite.

**`Palette`** is a class rather than a module dict because
[section 10](#10-what-the-rest-of-the-repository-has-already-decided) requires
per-surface colours keyed by algorithm identity and never cycled:

```python
class Palette:
    """Colours for map layers, by what the layer means.

    Series colours are shared with experiments/search-cost/plots.py, which
    validated them for colour-vision deficiency on both surfaces. Keyed by
    algorithm identity and never cycled, so adding a fourth algorithm cannot
    repaint the three already drawn.
    """

    def series(self, name: str) -> str:
        """Return the colour for an algorithm, raising on an unknown name."""

    def context(self) -> str:
        """Return the recessive colour for the network layer."""
```

Raising on an unknown series name is deliberate, and matches what
`plots.py`'s tests already assert about unknown surfaces — guessing a colour is how
two figures end up disagreeing.

**`RouteMap`** then holds a list of `MapLayer` and does very little: the fluent
methods below construct the right layer class and append it, `finish()` fits the
bounds and attaches the control, and `_repr_html_` calls `finish()`.

### 4.2 What the caller types

Three shapes, in increasing order of how much they hide. All three sit on the class
structure above; they differ only in what the notebook cell looks like.

#### Shape 1 — free functions

```python
from flight_planner.viz import route_map

m = route_map(legs, airports=catalog.airports)
```

One function per picture: `route_map`, `network_map`, `compare_map`. Trivially
learnable, and terrible at the third picture — every new question grows another
keyword argument, and comparing three algorithms instead of two means a new
function.

#### Shape 2 — a fluent builder

```python
from flight_planner.viz import RouteMap

m = (
    RouteMap()
    .airports(catalog.airports)
    .path(dijkstra_legs, name="Dijkstra", color="#d7263d")
    .path(bfs_legs, name="BFS", color="#1b6ca8")
    .finish()
)
```

Each call adds one named Leaflet layer; `finish()` fits the bounds to everything
drawn and attaches the layer control. It composes — three algorithms is a third
`.path()` — and it reads in a notebook, where the map *is* the output of the cell.
This is what the prototype implements, and what produced both screenshots in this
document.

Two details make it notebook-native:

- **`_repr_html_` calls `finish()`.** A bare `RouteMap()` chain as the last
  expression in a cell renders, so the common case never has to remember `.finish()`.
- **The layer name carries the number.** `.path(legs, name="Dijkstra")` labels the
  layer `Dijkstra (8,072 km)` — the total is computed from
  `sum(leg.distance_km ...)`, so the legend restates the finding rather than just
  naming a color. That is visible in the screenshot's layer control.

#### Shape 3 — declarative, driven by `experiment.toml`

```toml
[visualization]
layers = [
  { kind = "path", parameter = "pairs", algorithm = "dijkstra", color = "#d7263d" },
]
```

…with `experiment.map()` reading it. Genuinely appealing given how much this project
already invests in declaring things in TOML, and it would make maps *automatic*
rather than merely easy. But it needs the builder underneath it anyway, it can only
express questions the schema anticipated, and a schema for "what to draw" is a much
harder thing to get right than a schema for "what data to read". **Not now** — but
Shape 2 is the layer Shape 3 would be built on, so choosing it forecloses nothing.

#### The one-liner on top

Whatever the builder offers, the 80% case in an experiment notebook should be one
line. A named constructor on `RouteMap` rather than a module-level function, so the
entry point and the thing it returns stay in one class:

```python
class RouteMap:

    @classmethod
    def compare(cls, planner, origin, destination, algorithms,
                *, context=None) -> "RouteMap":
        """Draw one pair under several algorithms, one coloured layer each.

        Args:
            planner: The FlightPlanner to query.
            origin: Origin Airport or IATA code.
            destination: Destination Airport or IATA code.
            algorithms: Mapping of label to PathfindingAlgorithm. The label
                keys the palette, so 'Dijkstra' and 'A*' get the same colours
                here as in the committed charts.
            context: Optional Catalog whose routes become a NetworkLayer,
                switched off.

        Returns:
            A finished RouteMap, renderable as the value of a notebook cell.
        """
```

so that a notebook cell reads:

```python
RouteMap.compare(planner, 'HNL', 'BDL', {'Dijkstra': Dijkstra(), 'BFS': BFS()})
```

and produces the picture at the top of this document. A `classmethod` and not a
free function for a practical reason as well as a tidiness one: it is the natural
place to accept a `SearchResult` per algorithm instead of a bare algorithm
([section 2](#2-what-a-helper-actually-has-to-do)), and a second named constructor —
`RouteMap.network(catalog)` for the whole-network picture — costs nothing once the
first one exists.

### `.routes()` is not `.path()` with different arguments

The two look symmetrical in the builder and must not be implemented that way.
`.path()` draws a handful of legs and wants a `PolyLine` each, because each leg has
its own tooltip and the count is small. `.routes()` draws thousands and has to
collapse into **one** `GeoJson` feature collection — that is the 2.7× size and 4×
speed difference measured in [section 5](#5-what-the-prototype-measured), and it is
the single most important implementation detail in this document, because a
reasonable developer writes the slow version first and it works fine on 94 airports.

As a `MapLayer`, with the measured behaviour intact:

```python
class NetworkLayer(MapLayer):
    """Every route in a catalog, as one GeoJson layer.

    Folium emits a JavaScript statement per PolyLine, so a per-route layer
    costs 109 MB on the world snapshot against this class's 4.6 MB. The
    saving is entirely in how the geometry is packaged, not in drawing less.

    Off by default: the context is rarely what the experiment is about, and
    section 5's second screenshot shows it burying the answer.
    """

    def __init__(self, routes, geodesic=None, palette=None, *,
                 name="Routes", decimals=3):
        self._routes = routes
        self._geodesic = geodesic or Geodesic(segments=6)
        self._palette = palette or Palette()
        self._name = name
        self._decimals = decimals
        self._drawn = []

    def name(self) -> str:
        return self._name

    def show(self) -> bool:
        return False

    def drawn_points(self):
        return self._drawn

    def _distinct(self):
        """Collapse route rows to one per airport pair.

        The route table is keyed by flight number, so the world snapshot's
        66,332 rows are only 18,814 pairs. Drawing per row paints the same
        line three or four times over -- paying for it each time, and
        darkening it on screen in a way that misrepresents the geometry.
        """
        seen = {}
        for route in self._routes:
            key = tuple(sorted(
                (route.origin.iata_code, route.destination.iata_code)))
            seen.setdefault(key, route)
        return seen

    def build(self, folium):
        features = []
        for key, route in self._distinct().items():
            points = self._geodesic.between(route.origin, route.destination)
            self._drawn.extend(points)
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    # GeoJSON is [lon, lat]; folium.PolyLine takes [lat, lon].
                    # Easiest thing here to get backwards, hardest to see.
                    "coordinates": [
                        [round(lon, self._decimals), round(lat, self._decimals)]
                        for lat, lon in points
                    ],
                },
                "properties": {
                    "label": "-".join(key),
                    "km": round(route.distance_km),
                },
            })

        colour = self._palette.context()
        return folium.GeoJson(
            {"type": "FeatureCollection", "features": features},
            style_function=lambda _: {
                "color": colour, "weight": 1, "opacity": 0.3},
            # Batching does not cost per-route tooltips, which is the obvious
            # worry and the reason it was measured rather than assumed.
            tooltip=folium.GeoJsonTooltip(fields=["label", "km"]),
        )
```

Three decimal places is about 110 m — far finer than a line drawn at continental
zoom can resolve, and it is most of the remaining file size.

`Geodesic.between()` is the one method carrying
[section 6](#6-three-problems-the-helper-must-solve-once)'s two geometry problems,
and every layer goes through it:

```python
class Geodesic:
    """Great-circle interpolation between two Points, in [lat, lon].

    A straight PolyLine between two coordinates is a straight line in Web
    Mercator, which is neither the path flown nor the distance
    Route.distance_km reports. Longitudes are unwrapped past +/-180 rather
    than normalized into it, so a dateline route draws as one continuous
    line -- see section 6, and note that the unwrapped output is deliberately
    outside [-180, 180], which is why MapLayer has to report drawn_points().
    """

    def __init__(self, ellps: str = "WGS84", segments: int = 6):
        self._ellps = ellps
        self._segments = segments

    def between(self, origin, destination) -> List[List[float]]:
        """Return [lat, lon] points from origin to destination.

        Raises:
            ModuleNotFoundError: If pyproj is not installed. Deliberately not
                a straight-line fallback: a wrong picture beside a correct
                number is worse than a missing picture.
        """
```

Paths want a finer curve than context lines do, so the experiment-facing default is
`Geodesic(segments=24)` for `PathLayer` and `Geodesic(segments=6)` for
`NetworkLayer` — one object each, constructed by `RouteMap`, rather than a segment
count threaded through every call.

### The defaults, written down

[Section 2](#2-what-a-helper-actually-has-to-do)'s point 5 says consistency across
experiments is the real deliverable, so the constants are part of the design rather
than an implementation detail to be re-chosen. These are the values that produced
every screenshot in this document:

| Setting | Value | Why this one |
|---|---|---|
| `tiles` | `"OpenStreetMap"` | The only keyless basemap left — see [section 5](#tiles-the-default-is-not-free-any-more) |
| Path line | `weight=3.5`, `opacity=0.9` | Reads over tiles at continental zoom |
| Context line | `weight=1`, `opacity=0.3`, `#8899aa` | Recedes; must not compete with the answer |
| Context layer | `show=False` | Off unless asked for — [section 5](#5-what-the-prototype-measured) |
| Airport marker | `CircleMarker`, `radius=4`, `cadetblue`, `fill_opacity=0.9` | A `Marker` pin at 3,387 airports is unreadable and much heavier |
| Popup | `max_width=250` | Long airport names otherwise stretch the popup off-screen |
| Bounds | `fit_bounds(..., padding=(20, 20))` | Keeps endpoint markers off the frame edge |
| Layer control | `LayerControl(collapsed=False)` | The legend carries the finding; collapsed hides it |
| `segments` | **6** for bulk context, **24** for paths | 6 is visually indistinguishable at context weight and 2.2× smaller; a path is thick enough that faceting shows |
| Path colours | Adopt `plots.py`'s palette | See [section 10](#10-what-the-rest-of-the-repository-has-already-decided) — *not* the prototype's red/blue |

The `segments` split is the one row that is a judgement rather than a measurement:
both values were measured for size, but "6 looks the same at weight 1" is an
eyeball call on the screenshots, and a reviewer is entitled to disagree.

---

## 5. What the prototype measured

A working prototype of Shape 2 (about 120 lines, reproduced in
[appendix B](#appendix-b--the-prototype)) was run against
`experiments/shortest-vs-fewest`, whose snapshot `2026-09-12-3e4f9d` holds **94
airports and 7,005 routes**, and then again against the committed world snapshot
`2026-09-11-bb90a8` at **3,387 airports and 66,332 routes**. Everything below is
measured output from those runs, not an estimate;
[appendix A](#appendix-a--how-these-were-run) has the commands.

### Drawing the whole network is expensive

Rendering all 7,005 routes as individual `folium.PolyLine` objects, 24 interpolated
points each:

| Approach | Saved HTML | Build time |
|---|---|---|
| `folium.PolyLine` per route, 24 segments | 11.57 MB | 3.92 s |
| `folium.PolyLine` per route, 6 segments | 6.60 MB | 3.07 s |
| One `folium.GeoJson` layer, 24 segments, coords rounded to 3 dp | **4.22 MB** | **0.89 s** |
| One `folium.GeoJson` layer, 6 segments, coords rounded to 3 dp | **1.93 MB** | **0.38 s** |

A full map from the prototype — airports, all routes, and two highlighted paths —
saved at **12.1 MB in 4.1 s**. The same map with the all-routes layer left off:
**134 KB**.

### At world scale the same choices stop being optional

The identical benchmark against `2026-09-11-bb90a8` (3,387 airports, 66,332 routes):

| Approach | Saved HTML | Build + save |
|---|---|---|
| `folium.PolyLine` per route, 24 segments | 109.21 MB | 33.1 s |
| One `GeoJson` layer, 24 segments, 3 dp | 38.82 MB | 9.2 s |
| One `GeoJson` layer, 6 segments, 3 dp | 17.92 MB | 4.0 s |
| One `GeoJson` layer, 6 segments, 3 dp, **one feature per airport pair** | **4.61 MB** | **1.2 s** |

The last row is a finding the 94-airport snapshot could never have produced, and it
is worth more than every other optimisation here combined: **66,332 route rows are
only 18,814 distinct airport pairs.** The route table is keyed by flight number, so
a busy city pair appears three or four times, and drawing per row paints the same
line over itself — paying for it in file size every time, and darkening it on screen
in a way that misrepresents the geometry. Collapsing to distinct pairs is a 3.9×
saving *and* the more truthful picture, which is the rare case where the fast path
and the correct path are the same path.

Together: 109.21 MB → 4.61 MB, a 24× reduction, none of it from drawing less.

### Four conclusions the helper should bake in

1. **Batch bulk geometry into one `GeoJson` layer.** Folium emits a JavaScript
   statement per `PolyLine`; a single `GeoJson` layer emits one blob of coordinates.
   That is the 11.57 MB → 4.22 MB difference, and a 4× speedup.
2. **Round coordinates.** Three decimal places is about 110 m — far finer than a
   line drawn at continental zoom can show, and it is most of the remaining size.
3. **Draw distinct airport pairs, not route rows.** 3.9× on the world snapshot, and
   it stops the same line being painted over itself.
4. **The context layer is off by default.** Not just for size. Here is the same
   HNL→BDL comparison with all 7,005 routes drawn underneath:

   ![The same two routes with all 7,005 network routes drawn
   underneath](images/viz-route-map-context.png)

   The answer is still visible, but only just. `.routes(..., show=False)` puts it in
   the layer control switched off, so the reader turns the context on when they want
   it — which is the honest default, because the context is rarely what the
   experiment is about.

The size number matters less than it first appears, and
[section 10](#10-what-the-rest-of-the-repository-has-already-decided) explains why:
the repository already forbids committed notebook output, by test. A 12 MB inline
map can never reach git. What it *can* do is make the notebook unopenable for the
person running it, which is reason enough for all four conclusions above.

### Tiles: the default is not free any more

The prototype's first default was `tiles="CartoDB positron"`. Under folium 0.20.0 it
renders with **`API KEY REQUIRED` stamped diagonally across every tile** — visible
throughout the second screenshot above. Carto now gates that style. The plain
`OpenStreetMap` default (the first screenshot) has no such watermark.

Since a dark basemap turns out to matter for the slide deck
([section 7](#7-getting-a-map-into-the-pdf-and-onto-a-slide)), every plausible
alternative was rendered and screenshotted rather than assumed:

| Tile style | Result |
|---|---|
| `OpenStreetMap` | Clean. Zero failed tile requests |
| `CartoDB positron` | `API KEY REQUIRED` watermark on every tile |
| `CartoDB dark_matter` | `API KEY REQUIRED` watermark on every tile |
| `CartoDB voyager` | `API KEY REQUIRED` watermark on every tile |
| `Stadia.AlidadeSmoothDark` | **HTTP 401** on all 15 tile requests — blank grey map |
| `Stadia.StamenTonerLite` | **HTTP 401** on all 15 tile requests — blank grey map |

`xyzservices` reports the Stadia providers as `requires_token=False`, which is why
they were worth checking properly: they return 401 regardless, so provider metadata
is not a substitute for fetching a tile.

**So `tiles="OpenStreetMap"` is not a preference, it is the only keyless option
left**, and the helper should hard-default to it and say in the docstring that every
Carto and Stadia style needs a key. This is exactly the kind of thing that should be
decided once in a helper rather than rediscovered by each notebook author after
their map is already in a report.

> **Correction, 2026-09-15.** This table asked the right question of the wrong
> header. Every style above was tested for whether it needs an API *key*;
> `OpenStreetMap` does not, and that conclusion stands. But OSM's tile usage
> policy also requires the request to be **attributable**, which it enforces on
> `Referer` — so OSM works from a page served over HTTP and fails from the same
> file opened at a `file://` URL, which sends no `Referer`. The failure arrives
> as HTTP 200 with a PNG body reading `403 / Access blocked`, so "zero failed
> tile requests" in the row above would still be true while every tile was a
> block notice. §13.6 has the measurement, and the conclusion that "OpenStreetMap
> is the only keyless option" is now only true with "…for a page served over
> HTTP" attached. `ESRI_LIGHT_GRAY` in `viz/routemap.py` is the option for a map
> saved to be opened directly.

---

## 6. Three problems the helper must solve once

### Great circles, not straight lines

A `PolyLine` between two `[lat, lon]` pairs is a straight line in Web Mercator,
which is not the path an aircraft flies and not the distance
`Route.distance_km` reports. `docs/distance_formulas.md` already makes this point for
distance; the map has to make it too, or the picture contradicts the number beside
it. `notebooks/view_routes.ipynb` already gets this right with `pyproj`'s
`Geod.npts`, and the helper should lift that code:

```python
geod = Geod(ellps="WGS84")
inter = geod.npts(origin.longitude, origin.latitude,
                  destination.longitude, destination.latitude, segments)
```

The curve on the HNL→BOS lines in both screenshots is this, not decoration.

### The antimeridian

`Geod.npts` returns longitudes normalized to [-180, 180]. A route crossing the
dateline therefore produces a coordinate list that jumps from `-179` to `+179`, and
Leaflet dutifully draws a line straight back across the entire map. This is not a
hypothetical: **the committed world snapshot `2026-09-11-bb90a8` contains 647 route
rows — 137 distinct airport pairs — whose shorter great circle crosses the
antimeridian.** Auckland–Los Angeles is one of them, drawn here with no unwrapping:

![Auckland to Los Angeles drawn without unwrapping: the line runs east across the
entire Pacific to a point off Chile, then back up to
California](images/viz-dateline-naive.png)

That is one route. The fix is to unwrap: when consecutive longitudes differ by more
than 180°, keep adding or subtracting 360° so the sequence stays continuous. Real
snapshot airports, eight interpolated points, before and after:

```
AKL (174.8) -> LAX (-118.4)
  naive:      174.8  -176.0  -168.0  -160.9  -154.3  -147.9  -141.4  -134.5  -127.0  -118.4
  unwrapped:  174.8   184.0   192.0   199.1   205.7   212.1   218.6   225.5   233.0   241.6
```

Past +180 and still ascending — one continuous line eastward across the Pacific,
which is what Leaflet needs. Same result for SYD→LAX and NRT→SEA: one 180° jump
each before, zero after.

An earlier draft of this document claimed no committed snapshot had such a route and
that this was a bug nobody would hit yet. That was wrong — it is live on `main`
today, and any map of the world snapshot hits it 137 times.

### Whatever you unwrap, you have to frame

This one only appears once the unwrapping works, and it is why the two problems are
really one. Unwrapped geometry lives *outside* [-180, 180] — the AKL→LAX line is
drawn from 174.8° to 241.6°. The prototype's `_bounds()` takes the min and max of
the **airports'** own coordinates, which for this route is −118.4 to 174.8: a box
spanning the wrong way round the planet, and one that does not contain the line it
was asked to frame. Measured directly:

```
airports-box lon span:   -118.4 ..    174.8
drawn-box    lon span:    174.8 ..    241.6
drawn line inside the airports box? False
```

Fitting to the drawn coordinates instead gives the picture the map was for:

![The same route with bounds fitted to the drawn coordinates: one continuous
Auckland to Los Angeles line across the Pacific](images/viz-dateline-fixed.png)

Two rules follow, and both are easy to miss because they only fail on the routes a
US snapshot does not contain:

1. **`fit_bounds` takes the drawn coordinates, not the endpoints.** So the builder
   has to accumulate the unwrapped points it emitted, not just the airports it saw —
   a change to what the prototype's `_seen` list collects.
2. **Markers must be unwrapped into the same frame as the lines.** Look closely at
   the screenshot above: there is a marker on Auckland and none on Los Angeles. The
   LAX marker is at its raw −118.4°, which Leaflet renders in the *previous* copy of
   the world, off the left edge. A marker and the line that ends at it must agree
   about which world copy they are in.

---

## 7. Getting a map into the PDF and onto a slide

The `docs` Makefile target builds markdown to PDF through pandoc and XeLaTeX. An
interactive Leaflet map cannot go in a PDF, and `report.md` is a PDF. So a map that
only exists inline in a notebook cannot be cited by the report.

Folium's own `Map._to_png()` needs Selenium, which this project does not have. But
**Playwright is already a `dev` dependency**, and `docs/data.md` already documents
`uv run playwright install --with-deps chromium` for the Wikipedia scraper. So the
export path exists:

```python
page.goto(html_path.as_uri())
page.wait_for_timeout(2500)   # let the tiles finish loading
page.screenshot(path=str(png_path))
```

Measured: **4.2 s, a 301 KB PNG at 1200×800** — the first screenshot in this
document was produced exactly this way. The wait is not optional; without it the
screenshot catches a grey grid where the tiles have not arrived.

This belongs in its own class rather than as a method on `RouteMap`, because the two
have different dependencies and different homes: `RouteMap` needs folium, while the
export needs Playwright, which is a `dev`-group repository tool and not part of the
package contract at all.

```python
class MapExporter:
    """Write a RouteMap to HTML, and optionally to PNG via Playwright.

    Separate from RouteMap because Playwright is a dev-group tool: a reader
    who only wants HTML must not need a browser installed. Lives outside the
    wheel for the same reason plots.py lives outside it.
    """

    def __init__(self, width: int = 1200, height: int = 800,
                 settle_ms: int = 2500):
        ...

    def html(self, route_map, path) -> Path:
        """Save the map as self-contained HTML."""

    def png(self, route_map, path) -> Path:
        """Screenshot the map to PNG.

        The settle wait is not optional: without it the screenshot catches a
        grey grid where the tiles have not arrived.
        """
```

Committed diagram images already live in `docs/images/` under exactly this
"generated but committed" arrangement.

### There is already a convention for this, and it is not `scripts/`

`experiments/search-cost` does this today for its matplotlib figures, and the map
should follow it rather than invent a parallel path. Its notebook ends with:

```python
plots.nodes_expanded(comparison, '../../slides/images/nodes-expanded.png', mode='dark')
plots.nodes_expanded(comparison, '../../docs/images/nodes-expanded-light.png', mode='light')
```

Four things worth copying exactly:

- **The notebook writes the figure**, to a `../../` relative path, as the last thing
  it does. No separate script to remember to run, and no repository-root resolution.
- **Committed PNGs, stripped notebooks.** `tests/experiments/test_committed.py`
  asserts every committed experiment notebook carries no stored output, so the
  figure file *is* the durable artifact.
- **Two renders of every figure**, dark for `slides/images/` and light for
  `docs/images/`, with the `-light` suffix distinguishing them.
- **Figure code beside the notebook**, imported as `import plots`.

Only the last of those conflicts with [section 3](#3-where-the-module-should-live),
and for the reason argued there — a shared helper has no single notebook to sit
beside. The other three the map should adopt as-is.

### The dark-slide problem has no good answer

That "two renders" convention is not decoration. `plots.py` explains it: a
default-white axes box on a black reveal.js slide "is the classic failure here, and
it survives every other check". A map has exactly the same problem and, unlike
matplotlib, **no fix** — [section 5](#tiles-the-default-is-not-free-any-more)
measured every dark basemap as either watermarked or 401, so there is no dark
equivalent of `mode='dark'` to render.

The options, none of them free:

1. **Put the map only in the report**, which is light, and use the charts on the
   dark slides. Costs the deck its route map — which `docs/remaining_work.md` lists
   as a named Outcome, so this is the option that fails the rubric.
2. **Put the light map on a dark slide** inside a deliberate white card with padding,
   so it reads as an inset figure rather than a broken background. Cheap, honest,
   and the only option that needs no new dependency.
3. **Drop the basemap for the deck** and draw coastlines instead — which is Cartopy
   or Plotly's `scattergeo`, i.e. [section 8](#8-competing-libraries)'s second
   backend, and the one case in this document where the alternative libraries win
   outright.

**Option 2 for now, option 3 if the deck reviewer rejects it.** Worth deciding
before the first map is generated, because it determines whether `save()` needs a
`mode` argument at all — and on option 2 it does not, which is the other reason to
prefer it.

---

## 8. Competing libraries

Folium is already chosen and already installed. The question worth asking is not
whether something else is better in the abstract, but whether any of them solve a
problem this project actually has. The criteria that matter here: works inline in
Jupyter *and* Colab, produces something the PDF report can use, does not add a heavy
dependency to a package that currently needs only pandas, and draws geodesics on a
real basemap.

| Library | Inline in Jupyter | Colab | Static export | Extra weight | Verdict here |
|---|---|---|---|---|---|
| **Folium** | Yes (HTML iframe) | Yes | Via Playwright (§7) | Pure Python, small | **Keep** |
| **ipyleaflet** | Yes (real widget) | Needs `enable_custom_widget_manager` | No (widget state, not HTML) | Widget stack | Interesting, wrong trade |
| **Plotly** (`scatter_geo`/`scattermap`) | Yes | Yes, good support | `to_image` via Kaleido | +Plotly +Kaleido | Strongest alternative |
| **Matplotlib + Cartopy** | Static PNG | Yes | Native — it *is* the PNG | +Cartopy (GEOS/PROJ) | Best for the report only |
| **GeoPandas + contextily** | Static PNG | Workable | Native | +GeoPandas +Shapely | Overkill: no polygons here |
| **pydeck / kepler.gl** | Yes | Yes | Awkward | Heavy, WebGL | For 10⁵+ edges, not 7×10³ |
| **Bokeh** | Yes | Yes | PNG via Selenium | Medium | No advantage over Folium |
| **Altair / Vega-Lite** | Yes | Yes | PNG/SVG native | Medium | Weak basemap story |

Four of these deserve more than a table row.

### ipyleaflet — already installed, and the wrong tool anyway

It is in the `notebooks` dependency group already, so this is a live option. Being a
real Jupyter widget rather than an HTML blob, it is *bidirectional*: Python can react
to a click on an airport, and the map can be updated without re-rendering. For an
interactive explorer — click two airports, see the route computed — it is strictly
better than Folium.

But a widget's state lives in the kernel, not the file. Close the notebook and the
map is gone; there is no self-contained HTML to save, nothing to screenshot without
a live kernel, and in Colab it needs `output.enable_custom_widget_manager()` in the
setup cell. Every experiment notebook in this repository is written to be read after
the fact by someone who did not run it. Folium's "it's just HTML" is not a
limitation here, it is the requirement.

Worth keeping in mind for a future `explore_interactively()` — the builder shape in
[section 4](#4-what-the-api-should-look-like) is backend-agnostic enough that an
`ipyleaflet` backend behind the same `.airports()/.path()/.finish()` calls is a
plausible later addition.

### Plotly — the serious alternative

`px.line_geo` / `go.Scattergeo` gives real map projections (orthographic,
azimuthal-equidistant — projections where a great circle actually *looks* like the
shortest path, which Mercator never does), it handles thousands of segments in one
trace without the per-feature bloat measured in [section 5](#5-what-the-prototype-measured),
it renders in Colab without ceremony, and `fig.write_image()` gives the report its
PNG without Playwright.

What it costs: no tile basemap by default (you get coastlines and country fills, not
streets and city labels — fine at continental zoom, useless when the question is
which airport in the Bay Area), a large dependency, and Kaleido for static export.
Also, the repository's existing mapping knowledge and both committed map notebooks
are Folium.

**If this project were starting today with the report as the primary output, Plotly
would be the better default.** It is not starting today. The honest position:
Folium for the notebooks, and if the report ever needs a projection Mercator cannot
give, add a Plotly renderer behind the same builder rather than migrating.

### Matplotlib + Cartopy — for the report, if ever

`dev` already has matplotlib. Cartopy would give publication-quality static
geodesics (`transform=ccrs.Geodetic()` draws the great circle itself, no manual
interpolation) with no browser, no screenshot step and no tiles. That is a genuinely
better path to a figure in a PDF than screenshotting Leaflet.

The cost is a compiled GEOS/PROJ dependency, and zero interactivity — no hover, no
layer toggles, no zoom. Since the notebooks are the primary audience and the report
is the secondary one, this is a possible *second* backend, not the first.

### pydeck / kepler.gl

Built for hundreds of thousands of arcs on a WebGL canvas, with `ArcLayer` designed
for precisely this flight-route picture. At 7,005 routes — 1.93 MB of GeoJSON — this
project is two orders of magnitude below where that stops being overkill.

The earlier draft of this section said "revisit if a global snapshot ever puts the
full OpenFlights route table (~67,000 routes) on one map". That snapshot is
committed and in use: `2026-09-11-bb90a8`, 66,332 routes, measured in
[section 5](#at-world-scale-the-same-choices-stop-being-optional) at 4.61 MB and
1.2 s once deduplicated to 18,814 pairs. So the trigger has technically arrived and
the answer is still no — 4.61 MB of static HTML loads, and the deduplication that
got it there is a dozen lines rather than a WebGL dependency. The honest threshold
is not a route count but a *requirement*: pydeck earns its place when someone wants
to pan and filter 18,814 arcs at 60 fps, which no experiment in this repository
asks for.

---

## 9. Recommendation

1. **`flight_planner.viz`, in the wheel, with folium imported lazily and named
   nowhere in `pyproject.toml`** — not as a dependency and **not as an extra**
   ([option C](#option-c--flight_plannerviz-in-the-wheel-with-no-folium-dependency-at-all)).
   `folium` and `pyproj` stay in the `notebooks` dependency group where they already
   are. The wheel's pandas-only contract survives untouched; Colab's existing
   `%pip install -q ./traiectoria-optima` cell is unchanged, with
   `%pip install -q folium pyproj` added beside it in the notebooks that draw maps.
   The import guard's error message is the whole user interface for this decision,
   so write it as carefully as [section 3](#3-where-the-module-should-live) does.
2. **A class-based module behind a `MapLayer` ABC**
   ([section 4.1](#41-the-class-structure)) — `AirportLayer`, `NetworkLayer` and
   `PathLayer` each in their own file beside it, plus `Geodesic`, `Palette`,
   `RouteMap` and `MapExporter`. This mirrors `geo/formula.py` and
   `pathfinding/strategy.py` rather than inventing a fourth arrangement, and it is
   what makes items 4, 5 and 7 structural instead of conventions someone has to
   remember.
3. **A fluent `RouteMap` builder** ([shape 2](#shape-2--a-fluent-builder)), one
   named layer per call, `_repr_html_` calling `finish()`, layer names carrying the
   kilometre total — and the search counters too when handed a `SearchResult`. Plus
   a `RouteMap.compare()` named constructor for the common case.
4. **`.routes()` batches, `.path()` does not.** One `GeoJson` layer, coordinates
   rounded to 3 dp, **one feature per distinct airport pair**, 6 segments for context
   and 24 for paths, and the context layer `show=False` by default. 109.21 MB →
   4.61 MB on the world snapshot, 12.1 MB → 134 KB on the US one, and a more honest
   picture in both cases. [Section 4](#routes-is-not-path-with-different-arguments)
   has the code.
5. **Geodesic interpolation with antimeridian unwrapping**, once, in the helper —
   *and* `fit_bounds` fitted to the drawn coordinates with markers unwrapped into
   the same frame ([section 6](#whatever-you-unwrap-you-have-to-frame)). The
   unwrapping without the framing is worse than neither, because the line is correct
   and invisible.
6. **`tiles="OpenStreetMap"` as a hard default**, since it is the only keyless
   basemap that still works, with Carto's and Stadia's key requirements in the
   docstring rather than rediscovered.
7. **Adopt `plots.py`'s palette and its rules** — assigned by algorithm identity,
   never cycled, and never colour alone
   ([section 10](#10-what-the-rest-of-the-repository-has-already-decided)). Not the
   prototype's red and blue, which contradict the committed charts.
8. **A Playwright PNG export**, not in the wheel, written from the notebook to
   `../../docs/images/` and `../../slides/images/` the way `search-cost` already
   writes its charts ([section 7](#there-is-already-a-convention-for-this-and-it-is-not-scripts)).
   Light map in a white card on the dark slides until someone rejects it.
9. **Backfill both existing experiments** with one map cell each, and add one to the
   `scripts/new_experiment.py` starter notebook so every future experiment is
   visualized by default. That last point is what actually delivers "trivial to
   provide visualization for each experiment" — a helper nobody is prompted to call
   is a helper that does not get called.
10. **Test it the way `search-cost`'s charts are tested** — the module imported by
   path, smoke-tested against real recorded results, asserted on the things that can
   actually break ([section 10](#10-what-the-rest-of-the-repository-has-already-decided)).

Sequencing: 1–7 is one change and roughly a day, testable without touching any
notebook. 8, 9 and 10 follow independently. Items 4, 5 and 7 are the ones that will
be silently skipped if this document is skimmed, and the ones whose absence will not
show up until a world-snapshot map is already in a report.

---

## 10. What the rest of the repository has already decided

Three of this document's original open questions have answers already committed
elsewhere in the repository. Re-deciding them would produce a map layer that
disagrees with the charts sitting next to it on the same slide, so they are recorded
here as constraints rather than choices.

### Notebook output: settled, and enforced by a test

`tests/experiments/test_committed.py` asserts, for every committed experiment,
`test_its_notebook_carries_no_stored_output` — "Outputs are re-derivable and make
diffs unreadable". `experiments/search-cost/explore.ipynb` has 22 cells and zero
stored outputs.

So the question "does a 12 MB inline map get committed?" does not arise: **no map
ever reaches git as cell output.** The consequences for the design are firm rather
than open:

- A map that is only rendered inline is gone the moment the kernel dies, so anything
  the report or deck cites must be written to a file — which is item 7 of the
  [recommendation](#9-recommendation), not an optional extra.
- `_repr_html_` is still the right ergonomic default for the person *running* the
  notebook, but it is never the artifact.
- The 134 KB versus 12.1 MB difference is about whether the notebook is usable
  while open, not about repository size.

### Colours: settled, and the prototype is wrong

`experiments/search-cost/plots.py` defines the palette the committed charts already
use, per surface:

| Series | Dark (`slides/`) | Light (`docs/`) | Marker |
|---|---|---|---|
| BFS | `#3987e5` | `#2a78d6` | `o` |
| Dijkstra | `#d95926` | `#eb6834` | `s` |
| A\* | `#199e70` | `#1baf7a` | `^` |

It records why: the slots are "the first three of a categorical palette validated for
colour-vision deficiency against both surfaces (worst all-pairs CVD dE 9.4,
normal-vision dE 20.9, contrast >= 3:1 on the dark surface)", they are "assigned by
algorithm identity and never cycled, so adding a fourth algorithm cannot repaint the
three already on screen", and every series carries a marker shape as well as a hue
so that "identity must survive greyscale printing and colour-blind readers".

The prototype used `#d7263d` red for Dijkstra and `#1b6ca8` blue for BFS. That is
**directly contradictory**: on this palette Dijkstra is orange and blue means BFS.
A slide showing a chart and a map side by side would swap two of its three colours
between the two figures.

So: the map adopts `SERIES_COLOURS`, keyed by algorithm identity. Two consequences
worth stating, because they are what "adopt the palette" actually costs:

- **The values have to be shared, not copied.** `plots.py` is per-experiment and
  `viz` is in the package, so the palette must live in one of them and be imported
  by the other. Given the layering, it belongs in `flight_planner.viz` as the
  `Palette` class of [section 4.1](#41-the-class-structure), with `plots.py`
  importing it — which is a small change to committed, tested code on another
  branch, and needs coordinating rather than assuming.
- **A map has layers a chart does not** — the context network, the airport markers —
  so `viz` still needs its own non-series colours (`#8899aa`, `cadetblue`). Those are
  not part of the categorical palette and must not be drawn from its slots.

The original instinct here still stands, incidentally: key the colour by *what the
layer means* rather than by the order it was added. `plots.py` arrived at the same
answer independently, which is the strongest evidence available that it is right.

### What the test is: settled by example

`tests/experiments/test_search_cost_plots.py` is 134 lines answering exactly this
question for the charts, and the map's tests should be its sibling rather than
something new:

- **Import the module by path.** Experiment directories are not packages — "its name
  is not even a legal identifier" — so it uses `importlib.util.spec_from_file_location`.
  A package-resident `flight_planner.viz` is imported normally, so this part gets
  *easier*, but the fixture pattern is the model.
- **Smoke-test against the real recorded results**, not a hand-built dict, "so a
  change to the shape `record()` writes fails here too".
- **Assert what can actually break** — a file that does not appear, an empty or
  non-PNG file (it checks the PNG magic bytes), a surface that is not what was asked
  for, an unknown mode raising rather than guessing, every series having a colour and
  a marker on both surfaces — and explicitly not appearance: "Layout is checked by
  opening them, which is a human step the plan calls for explicitly."

The class structure in [section 4.1](#41-the-class-structure) is what makes this
straightforward, because each class is testable without a map:

| Unit | What the test asserts |
|---|---|
| `Geodesic` | Point count for a given `segments`; zero 180° jumps on all 137 crossing pairs in the world snapshot; `ModuleNotFoundError` without pyproj rather than a straight line |
| `NetworkLayer._distinct` | 66,332 rows collapse to 18,814 pairs; A→B and B→A are one entry |
| `NetworkLayer.build` | One `GeoJson`, not N; coordinates rounded to 3 dp; `[lon, lat]` order |
| `PathLayer.name` | Carries the kilometre total, and the counters when given a `SearchResult` |
| `MapLayer.drawn_points` | For a dateline route, includes longitudes past 180 |
| `RouteMap.finish` | Bounds contain every layer's drawn points, dateline case included |
| `Palette` | Every algorithm has a colour on both surfaces; an unknown name raises rather than guessing |
| `MapExporter` | PNG magic bytes, non-empty file, written where it was told |

The HTML can be asserted on coarsely — the layer exists, the coordinate count is
right, `API KEY REQUIRED` never appears in it — without pretending to test what it
looks like. The `drawn_points` and `finish` rows are the two that would not exist as
tests at all under a free-function design, because there would be nothing to ask.

---

## 11. Open questions

**Should `results.json` reference its map?** The experiments layer is built on the
idea that a result states what produced it. A recorded map path would extend that to
the picture — but it also means `record()` grows an opinion about files it does not
write. Probably a separate `experiment.artifacts` concern, if it happens at all.
`search-cost` currently sidesteps this: its notebook writes two PNGs and
`results.json` mentions neither.

**Where does the shared palette live?** Settled in principle above — in
`flight_planner.viz`, imported by `plots.py` — but that means editing tested code on
`feature/search-instrumentation`, so it is a sequencing question between branches
rather than a design one.

**Does the light map survive a dark slide in a white card?**
[Section 7](#the-dark-slide-problem-has-no-good-answer) picks that option on the
grounds that it needs no new dependency, but it is an aesthetic judgement that has
not been tried, and the fallback is a whole second backend.

**Is `segments=6` really indistinguishable at context weight?** Measured for size,
eyeballed for appearance. If a reviewer disagrees, the number is one keyword
argument and the file grows 2.2× (17.92 MB against 38.82 MB on the world snapshot).

**Should this document's internal links be pandoc-compatible instead of
GitHub-compatible?** They cannot be both. The two renderers slugify headings
differently: pandoc strips a leading section number (`## 3. Where the module
should live` becomes `#where-the-module-should-live`) and collapses the double
hyphen an em dash leaves behind, while GitHub keeps the number and the double
hyphen. The 49 internal links here are written for GitHub, which is the surface
these docs are actually read on — the Makefile commits diagram SVGs for the same
reason, "so the docs render in a fresh clone and on GitHub, neither of which
builds a PDF". The cost is about ten `LaTeX Warning: Hyper reference ... undefined`
lines in `make docs`, where those links render as plain text. Nothing fails.
Satisfying both means renaming every linked heading to drop its number and its em
dash, which is a larger edit than the problem deserves until someone is actually
reading the PDF and clicking. The other docs sidestep it by having two internal
links each rather than forty-nine.

**Where should the prototype live so it stays runnable?**
[Appendix B](#appendix-b--the-prototype) preserves the source as prose, which is
enough to re-derive but not enough to re-run: `bench.py`, `bench_world.py`,
`tiles.py`, `tiles_dark.py`, `dateline_check.py` and `shot.py` — the scripts behind
every number in [appendix A](#appendix-a--how-these-were-run) — are not in the
repository at all. That is deliberate for now, since committing a prototype
alongside a document that says "nothing here is implemented yet" invites someone to
import it. But it does mean the numbers are re-derivable rather than
re-runnable, and the obvious home when the helper is built is a `tests/` or
`scripts/` sibling that exercises the real classes instead — at which point these
scripts are throwaway and the question answers itself.

---

## 12. What implementing it changed

`flight_planner.viz` was built to [section 9](#9-recommendation) and
`experiments/route-map/` demonstrates it. Almost all of the design survived
contact: the `MapLayer` structure, the batched `NetworkLayer`, the palette, the
tile default and the `RouteMap.compare` one-liner all went in as written.

Four things did not, and all four were found by running the thing rather than
reading it.

### The PNG export cannot use Playwright's sync API

[Section 7](#7-getting-a-map-into-the-pdf-and-onto-a-slide) specifies a Playwright
screenshot called from the notebook, and the prototype's `shot.py` proved the
approach — from a *script*. From a notebook it fails outright:

```
Error: It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead.
```

A Jupyter kernel *is* an asyncio loop, so the sync API refuses to start inside one.
This was invisible to the prototype because the prototype never ran in a kernel —
the one place the design says the export belongs.

`MapExporter.png` therefore runs the browser in a **subprocess**: a fresh
interpreter has no loop of its own, and the same code then works from a notebook, a
script, a test and pytest alike. The alternative — an async API and an `await` in
the notebook — would have made the export the only cell in the repository that
cannot be copied into a plain script.

### Unwrapping has to be continuous across legs, not within them

[Section 6](#whatever-you-unwrap-you-have-to-frame) got the antimeridian half right.
`Geodesic` unwraps within one leg, starting from that leg's own origin — which is
correct for a single leg and wrong for a path made of several. `SYD-LAX-JFK` is the
case: the first leg unwraps to end at 241.6°, and the second then starts again at
its raw −118.4°, a 360° jump between two legs that are each individually right.
Leaflet draws the jump, and the map frames itself across 404° of longitude — more
than a whole globe, zoomed out past the route.

`PathLayer._join` shifts each leg into the copy of the world the previous one
finished in. The frame for `SYD-JFK` goes from 404° wide to 135°.

The prototype could not have found this: its `.path()` was only ever exercised on
US routes, where every leg unwraps to itself.

### One global marker offset is not enough either

[Section 6](#whatever-you-unwrap-you-have-to-frame)'s second rule — move markers
into the lines' frame — was implemented first as a single `±360` offset applied to
every marker. That works for a single dateline leg and breaks on `SYD-LAX-JFK`,
where SYD belongs at 151° and JFK belongs at 286°: one offset cannot be right for
both.

`RouteMap._nearest_copy` instead moves each marker to whichever copy of the world
is closest to the middle of the drawn lines, which reduces to "leave it alone" when
nothing was unwrapped.

### `Palette` needs to not raise

[Section 4.1](#41-the-class-structure) argues that `Palette.series` should raise on
an unknown name, and it does. But `PathLayer` takes its colour from its *layer
name*, and a layer legitimately named `"Great circle"` or `"SYD-JFK"` is not an
algorithm — so the layer falls back to the scenery colour rather than propagating
the `KeyError`. `Palette.series` still raises for callers asking for a series
colour directly, which is where a typo in an algorithm name actually matters.

### What the experiment measured

`experiments/route-map/` confirms the numbers this document predicted and adds one:

| Measurement | Value |
|---|---|
| Route rows → distinct airport pairs | 66,332 → 18,814 (3.5 rows per pair) |
| Map with the context layer | 4.83 MB |
| The same map, answer only | 0.02 MB |
| Ratio | **305×** |

That 305× is the number that justifies `show=False` more sharply than anything in
[section 5](#5-what-the-prototype-measured): the context is not a component of the
file, it is the file.

Its three pairs also make a point the design did not anticipate. `SYD-JFK` is
answered by Dijkstra in two legs via Los Angeles and by BFS in two legs via **Abu
Dhabi** — the same hop count, 7,057 km apart, leaving Sydney in opposite
directions. No column in a results table explains that. The map does, and it is the
clearest argument in the repository for why this layer exists.

---

## 13. What faceting changed

[`experiments/us-route-map`](../experiments/us-route-map) asks the layer system
for something no earlier experiment did: not two or three layers, but thirteen,
all switched on, each independently switchable. It is the first experiment here
whose deliverable is interactive, and the first whose question is about the
data's shape rather than an algorithm's behaviour — *who flies where* in the
United States, Alaska, Hawaii and Puerto Rico.

**Almost nothing had to be built.** The faceting is `Catalog.airline()` for the
filter, one `NetworkLayer` per carrier for the drawing, and the
`LayerControl(collapsed=False)` that [section 6](#6-three-problems-the-helper-must-solve-once)
already attaches. `NetworkLayer` needed three additions, all defaulted so no
existing caller changed: a `colour`, a `dash_array`, and a `show` argument to
override its hard `False`. It also now carries `route.airline` into the GeoJSON
properties and the tooltip, which [section 4](#4-what-the-api-should-look-like)
noted as available and unused. That is the whole diff to the package.

### 13.1 What it measures

`--country US PR --airport-type large medium`, both endpoints in scope. Puerto
Rico is `PR` and not `US`, so narrowing on `US` alone silently drops every
Caribbean arc; `large` alone leaves Alaska as essentially Anchorage by itself.

| Measurement | Value |
|---|---|
| Airports drawn | 473 (56 Alaska, 10 Hawaii, 6 Puerto Rico) |
| Route rows | 10,363 |
| Distinct airport pairs | 2,688 |
| Arcs drawn across 12 carrier layers | 4,515 |
| Pairs those twelve cover | 2,556 |
| Pairs they miss, in the bucket layer | 132 |
| Total features | 4,647 |
| Interactive HTML | 2,008,548 bytes (2.01 MB) |
| Longitude span of the frame | 111.3° (Adak −176.6° to Culebra −65.3°) |

The layer sum exceeding the pair count is the comparison, not an error: a pair
flown by both American and Delta is drawn once in each layer, which is what
makes switching one off informative. The bucket holds the pairs *no* named
carrier serves rather than everything the unnamed carriers fly, so the thirteen
layers partition the network — which is what makes "132" mean "what the majors
miss" rather than an arithmetic accident.

Filtering was verified in a browser, not inferred: on load the DOM carries
4,518 SVG paths (4,515 arcs plus three map decorations); unchecking every
carrier but Hawaiian leaves 28; adding Alaska back gives 275, which is
247 + 25 + 3.

### 13.2 Answering section 8's objection

[Section 8](#8-competing-libraries) rejected pydeck with a specific caveat:
"pydeck earns its place when someone wants to pan and filter 18,814 arcs at 60
fps, which no experiment in this repository asks for." This experiment is that
ask, at 4,647 features rather than 18,814 — a quarter of the load that
sentence was written about. Folium holds up: the map pans and toggles without
perceptible lag, and the recommendation in
[section 9](#9-recommendation) stands unchanged. The caveat was well drawn
rather than wrong, and it is worth keeping for whoever eventually wants the
whole world faceted this way.

### 13.3 The palette had to be measured, and the measurement refuted the design

Twelve simultaneously distinguishable hues do not exist for a colour-blind
reader, so a carrier's identity is hue **and** stroke — the same construction
`SERIES_MARKERS` uses when a chart series carries both a colour and a marker.

The first attempt was six Okabe–Ito hues over two dash patterns. Measuring it
killed it. Under tritanopia the three warm hues collapse into one another:

| Pair | ΔE under tritanopia |
|---|---|
| vermillion / reddish purple | **0.9** |
| orange / reddish purple | 13.9 |
| orange / vermillion | 14.9 |

Vermillion was Delta and reddish purple was US Airways — two legacy majors,
both drawn solid, effectively the same colour for a tritanope. And the problem
is structural rather than an unlucky assignment: six hues over two dash classes
puts every hue in *every* class, so the three warm hues always share a class
and no dash can separate them.

The fix is four hues over three dash classes — blue, sky blue, bluish green and
vermillion, only one of them warm, so no class ever holds two. Each class then
holds each hue exactly once, which makes the guarantee structural: the worst
same-stroke pair is the worst pair among four distinct hues.

| Surface | Worst same-stroke ΔE | Where |
|---|---|---|
| light | **19.6** | UA / US, tritanopia |
| dark | **30.4** | UA / US, tritanopia |

Same-stroke is the set that matters, because two carriers a reader must
separate by colour alone are two carriers drawn with the same dash. The dark
column was also stepped by measurement rather than by eye: lightening all four
hues uniformly pulled blue and bluish green to ΔE 12.6, so blue is left
unlightened. All four clear the 3:1 contrast against black that the series
colours are held to — 4.05, 7.30, 7.42 and 11.77 to 1.

One honesty note. The series-palette figures quoted in
[section 4](#4-what-the-api-should-look-like) and in `palette.py` ("worst
all-pairs CVD ΔE 9.4") came from an external checker with no script in this
repository, so they cannot be reproduced or compared against these. The carrier
figures above come from `palette_contrast()` in
`experiments/us-route-map/plots.py` — CIE76 over a Viénot–Brettel–Mollon
dichromat simulation — and `tests/experiments/test_us_route_map_plots.py` tests
that simulation against properties any correct implementation must have (grey
is unmoved by every deficiency; red and green converge under deuteranopia)
rather than against the numbers it happens to produce. Re-deriving the series
palette's own numbers the same way is worthwhile and is not done here.

### 13.4 Two things this found in the existing layer

**A hidden layer still counts toward the frame.** `RouteMap.bounds()` is the
union of what every layer drew, visible or not, so a switched-off 473-airport
layer pins the map to the full Adak-to-Culebra box. Every single-carrier still
came out as zoomed out as the whole network until the layer was left out
entirely. `plots.write_stills` omits it for the focus views, and framing on the
arcs alone is also how the lower-48 still works — no bounds override exists or
was added, because `RouteMap` frames itself on what was drawn and dropping the
offshore arcs is the whole mechanism.

Whether that is a defect is a real question, and it is left open deliberately.
`compare(context=...)` adds the whole world as a hidden layer, so framing on
visible layers only would change every committed figure that uses it. It is
recorded here rather than fixed.

**`AirportLayer` is unbatched, and it costs.** 473 `CircleMarker`s are 622,075
bytes of the 2.01 MB file — 31% of a committed deliverable for a layer that
starts switched off, or about 1.3 KB per marker, because folium emits a
JavaScript statement per marker. This is the same problem
[section 5](#5-what-the-prototype-measured) solved for routes by collapsing
them into one `GeoJson`, and the same solution would apply. Not done here: it
belongs in the package rather than in an experiment, and the experiment's own
philosophy is that copying drawing logic into a notebook is how every map ends
up slightly different. Worth doing when a second faceted map wants it.

For comparison, coarser coordinates are *not* where the bytes are: rounding the
arcs from 3 decimals to 2 saved 5% (1.35 MB → 1.28 MB) and to 1 decimal 10%, so
precision stayed at 3.

### 13.5 The committed HTML

This experiment commits generated output, which nothing else here does — a
folium HTML was removed from this repository once before as "147 KB of
generated Folium output committed as a source file". The judgement differs
because interactivity *is* the finding: a map whose point is toggling twelve
carriers cannot be delivered as a still, and one that needs a Jupyter kernel to
open is not delivered at all. It ships at
[`docs/maps/us-route-map.html`](maps/us-route-map.html) under a 2.5 MB bound
that `tests/experiments/test_us_route_map.py` enforces, which is the condition
that made committing it acceptable.

The stills are rendered **once and copied**, not rendered twice. Screenshot
output is not byte-deterministic — two renders of the same map came out 25
bytes apart, because basemap tiles arrive and labels settle on their own
schedule — and `tests/experiments/test_figures.py` requires the two copies to
be identical. Like `route-map`, the experiment ships one light PNG into both
image directories: no keyless dark basemap exists, and `RouteMap` refuses the
ones that need an API key.

### 13.6 The second tile trap: a key is not the only thing a basemap needs

Committing the HTML is what exposed this, and it is the sharpest finding here.

The map shipped with the package default, `OpenStreetMap`. Opened the way a
reader would open it — double-clicked, so `file://` — **every tile was a notice
reading `403 / Access blocked / App is not following the tile usage policy of
OpenStreetMap's volunteer-run servers`.** The arcs, the layer control and the
filtering all worked perfectly on top of it.

Three things made it survive review:

1. **It is not an error.** OSM serves the block as **HTTP 200 with a PNG
   body**. Nothing raises, nothing logs, no status code is out of place. The
   §5 measurement "zero failed tile requests" would report success.
2. **It depends on how the file is opened.** OSM enforces its policy on
   `Referer`. A page served over HTTP sends one; a `file://` page sends none.
3. **Every check had been done over HTTP.** The interactive map was verified
   through a local server, and the PNG stills are rendered by Playwright
   through one too. Both had a `Referer` and both were fine. The one access
   path that was never tested is the only one the deliverable is *for*.

Measured 2026-09-15, generic browser UA, no `Referer`:

| Request | Result |
|---|---|
| `tile.openstreetmap.org`, no `Referer` | HTTP 200, block notice PNG |
| `tile.openstreetmap.org`, identifying `User-Agent` | HTTP 200, real tile |
| `server.arcgisonline.com` World Light Gray, no `Referer` | HTTP 200, real tile |

A browser cannot set `User-Agent`, so the identifying-UA row is available to
`curl` and not to Leaflet. The fix is a provider that does not require
attribution by header: `ESRI_LIGHT_GRAY`. Verified from a `file://` URL, 35
tile requests, all 200, no block notices.

Two things came out better for it. A desaturated canvas stops the basemap
competing with the arcs — on OSM's green-and-blue base, four carrier hues fight
the landmass; on gray they do not. And `RouteMap` gained the ability to take a
tile URL template at all, with two guards: an unattributed template is refused
at construction rather than failing deep inside folium, and the basemap is
given a readable layer-control label.

That second guard is itself worth recording, because the first attempt at it
was wrong and a test passed anyway. `folium.Map` builds its own `TileLayer`
internally and names it from the tile string, so a `name=` handed to `Map` is
silently swallowed by `**kwargs`. It rendered *somewhere* in the document, so a
test asserting `"Esri light gray" in html` passed while the layer control still
displayed the entire tile URL. The corrected test asserts against the control's
own base-layer mapping, and the fix passes a prebuilt `folium.TileLayer`, which
is the supported path. A substring assertion over generated HTML is weaker
evidence than it looks.

`tests/experiments/test_us_route_map.py` now pins the committed artifact
directly: no `tile.openstreetmap.org`, an Esri URL present, attributed, and
named. The guard is on what shipped, not on the builder, because what shipped
is what was broken.

**Still open:** whether Esri's terms of service permit this use outside their
own SDKs. It demonstrably works, which is a different claim from being allowed,
and nothing in this document should be read as having checked. The irony is not
lost — §5's lesson was that provider metadata is no substitute for fetching a
tile, and the converse holds just as well: fetching a tile is no substitute for
reading the terms.

---

## Appendix A — how these were run

Every number and screenshot above came from scripts run against this worktree on
2026-09-12, in the `notebooks` group environment (`uv sync --group notebooks`),
which resolved **folium 0.20.0, pyproj 3.7.2, ipyleaflet 0.20.0**. Playwright came
from the `dev` group (`playwright>=1.48.0`), with `uv run playwright install
--with-deps chromium` already done for the Wikipedia scraper documented in
`docs/data.md`.

The prototype in [appendix B](#appendix-b--the-prototype) was saved as `maps.py` in
a scratch directory, with the repository as the working directory so that
`Experiment.open` and `Snapshot.open` resolve their relative paths:

```console
# The 94-airport / 7,005-route figures in section 5
$ uv run python bench.py out/
7005 routes
polyline-24seg          11.57 MB   3.92s
polyline-6seg            6.60 MB   3.07s
geojson-24seg            4.22 MB   0.89s
geojson-6seg             1.93 MB   0.38s

# The 3,387-airport / 66,332-route figures, including deduplication
$ uv run python bench_world.py out/
2026-09-11-bb90a8: 3387 airports, 66332 routes
polyline-24seg         109.21 MB  build  3.57s  total 33.14s
geojson-24seg           38.82 MB  build  4.72s  total  9.18s
geojson-6seg            17.92 MB  build  1.98s  total  4.02s
   distinct pairs: 18814 of 66332 rows
geojson-6seg-dedup       4.61 MB  build  0.64s  total  1.19s

# Every tile style, rendered and screenshotted rather than assumed
$ uv run python tiles.py tiles/
OpenStreetMap             167 KB  3.7s  tiles-OpenStreetMap.png
CartoDB positron          138 KB  3.5s  tiles-CartoDB-positron.png
CartoDB dark_matter       116 KB  3.4s  tiles-CartoDB-dark-matter.png
CartoDB voyager           151 KB  3.4s  tiles-CartoDB-voyager.png

$ uv run python tiles_dark.py tiles/
Stadia.AlidadeSmoothDark    60 KB  tile errors: 15  e.g. 401 tiles.stadiamaps.com/...
Stadia.StamenTonerLite      60 KB  tile errors: 15  e.g. 401 tiles.stadiamaps.com/...
OSM.Mapnik                 167 KB  tile errors: 0

# The dateline routes, from the committed world snapshot
$ uv run python dateline_check.py out/
AKL (174.8) -> LAX (-118.4)
  naive 180-degree jumps: 1   unwrapped: 0

# The bounds bug
$ uv run python dateline_bounds.py out/
airports-box lon span:   -118.4 ..    174.8
drawn-box    lon span:    174.8 ..    241.6
drawn line inside the airports box? False

# Every PNG in this document
$ uv run python shot.py out/HNL-BDL.html
HNL-BDL.png: 301 KB in 4.2s
```

The 647 crossing rows over 137 distinct pairs were counted directly from
`data/snapshots/2026-09-11-bb90a8/`, by loading `airports.csv` into an
IATA → (lat, lon) map and counting `routes.csv` rows whose endpoints differ by more
than 180° of longitude — the condition for the shorter great circle to cross the
antimeridian.

---

## Appendix B — the prototype

Roughly 120 lines, and the source of every screenshot and measurement above. It is
reproduced in full because the alternative is a design document that cannot be
checked, and because three of its details are wrong in ways that only running it
revealed. Each is marked.

**Read it as evidence, not as a skeleton.** Its structure is one class plus three
module-level functions, which is the shape a prototype takes and not the shape
[section 4.1](#41-the-class-structure) specifies: `_geodesic` becomes `Geodesic`,
`_bounds` disappears into `MapLayer.drawn_points()` and `RouteMap.finish()`, the
colour literals become `Palette`, and `.routes()` becomes `NetworkLayer` with the
batched `GeoJson` build. What is worth keeping verbatim is the unwrapping loop in
`_geodesic`, the `CircleMarker` and popup settings, and the layer-naming with the
kilometre total — those are measured or eyeballed decisions, and they are the parts
that took the longest to get right.

```python
"""Prototype of the proposed flight_planner.viz module (Folium backend)."""

from __future__ import annotations

from typing import Iterable, Optional, Sequence


def _folium():
    try:
        import folium
    except ModuleNotFoundError as error:
        # WRONG: section 3 rejects the extra. Use the message given there.
        raise ModuleNotFoundError(
            "mapping needs folium: pip install 'flight_planner[viz]'"
        ) from error
    return folium


def _geodesic(origin, destination, segments=24):
    """Great-circle points as [lat, lon], antimeridian-safe."""
    try:
        from pyproj import Geod
    except ModuleNotFoundError:
        # Silently straightens the line. Section 3 argues for raising instead:
        # a wrong picture is worse than a missing one.
        return [[origin.latitude, origin.longitude],
                [destination.latitude, destination.longitude]]
    geod = Geod(ellps="WGS84")
    inter = geod.npts(origin.longitude, origin.latitude,
                      destination.longitude, destination.latitude, segments)
    points = ([(origin.latitude, origin.longitude)]
              + [(lat, lon) for lon, lat in inter]
              + [(destination.latitude, destination.longitude)])
    out, previous = [], None
    for lat, lon in points:
        if previous is not None and lon - previous > 180:
            lon -= 360
        elif previous is not None and previous - lon > 180:
            lon += 360
        previous = lon
        out.append([lat, lon])
    return out


def _bounds(airports):
    # WRONG for dateline routes: these are endpoint coordinates, but the lines
    # are drawn in unwrapped longitude space. Accumulate drawn points instead.
    lats = [a.latitude for a in airports]
    lons = [a.longitude for a in airports]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


class RouteMap:
    """A Folium map built in layers from airports and routes."""

    def __init__(self, tiles: str = "CartoDB positron"):
        # WRONG: every Carto style is watermarked. Default to "OpenStreetMap".
        folium = _folium()
        self._folium = folium
        self.map = folium.Map(tiles=tiles, zoom_start=3, location=[39.0, -98.0])
        self._seen = []

    def airports(self, airports: Iterable, name: str = "Airports",
                 color: str = "cadetblue", show: bool = True) -> "RouteMap":
        folium = self._folium
        group = folium.FeatureGroup(name=name, show=show)
        for airport in airports:
            self._seen.append(airport)
            folium.CircleMarker(
                location=[airport.latitude, airport.longitude],
                radius=4, color=color, fill=True, fill_opacity=0.9,
                tooltip=f"{airport.iata_code} - {airport.name}",
                popup=folium.Popup(
                    f"<b>{airport.iata_code}</b><br>{airport.city}, "
                    f"{airport.country}", max_width=250),
            ).add_to(group)
        group.add_to(self.map)
        return self

    def routes(self, routes: Iterable, name: str = "Routes",
               color: str = "#8899aa", weight: float = 1.0,
               opacity: float = 0.35, show: bool = True) -> "RouteMap":
        # Replace with the batched, deduplicated GeoJson layer from section 4.
        folium = self._folium
        group = folium.FeatureGroup(name=name, show=show)
        for route in routes:
            self._seen.extend((route.origin, route.destination))
            folium.PolyLine(
                _geodesic(route.origin, route.destination),
                color=color, weight=weight, opacity=opacity,
                tooltip=(f"{route.origin.iata_code}-{route.destination.iata_code} "
                         f"{route.distance_km:,.0f} km"),
            ).add_to(group)
        group.add_to(self.map)
        return self

    def path(self, legs: Sequence, name: Optional[str] = None,
             color: str = "#d7263d", weight: float = 3.5) -> "RouteMap":
        # Colours: use plots.py's palette by algorithm identity (section 10),
        # not this red.
        if not legs:
            return self
        label = name or (legs[0].origin.iata_code + "-"
                         + "-".join(leg.destination.iata_code for leg in legs))
        total = sum(leg.distance_km for leg in legs)
        folium = self._folium
        group = folium.FeatureGroup(name=f"{label} ({total:,.0f} km)")
        for leg in legs:
            self._seen.extend((leg.origin, leg.destination))
            folium.PolyLine(
                _geodesic(leg.origin, leg.destination),
                color=color, weight=weight, opacity=0.9,
                tooltip=(f"{leg.origin.iata_code}-{leg.destination.iata_code} "
                         f"{leg.distance_km:,.0f} km"),
            ).add_to(group)
        group.add_to(self.map)
        return self

    def finish(self):
        folium = self._folium
        if self._seen:
            self.map.fit_bounds(_bounds(self._seen), padding=(20, 20))
        folium.LayerControl(collapsed=False).add_to(self.map)
        return self.map

    def _repr_html_(self):
        return self.finish()._repr_html_()
```

And the PNG export, which is a dozen lines and belongs beside the notebook rather
than in the wheel:

```python
"""Export a saved Folium map to PNG with Playwright (a dev-group dep)."""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

html = Path(sys.argv[1]).resolve()
png = html.with_suffix(".png")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1200, "height": 800})
    page.goto(html.as_uri())
    page.wait_for_timeout(2500)  # let the tiles finish loading
    page.screenshot(path=str(png))
    browser.close()
```
