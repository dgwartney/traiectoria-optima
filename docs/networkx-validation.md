# Validating `flight_planner` against NetworkX

`flight_planner` implements its own `Graph`, `Vertex`, `Edge`, `MinHeap`, and
three pathfinding strategies. That is the point of the project — the
algorithms are the deliverable, not a means to an end. But hand-written
Dijkstra, BFS and A\* need an answer to "how do we know these are right?", and
today the answer is 382 tests, most of them against four-vertex graphs built
by hand, plus three committed experiments that pin real numbers
([`tests/experiments/test_committed.py`](../tests/experiments/test_committed.py)).

[NetworkX](https://networkx.org) is the obvious external oracle: a
BSD-licensed, pure-Python graph library with no required runtime dependencies,
whose shortest-path implementations are independently maintained and heavily
exercised. It can answer the same questions on the same data, and disagreement
is a bug in one of the two.

This document lays out the options, from a twenty-line adapter to a second
engine behind the existing Strategy interface. **Every code block below was
run against this repository's committed snapshots, and every output shown is
the output it produced** — nothing here is a sketch. The commands are in
[Appendix A](#appendix-a--how-these-were-run).

> **It already found something.** Option E's randomized testing shows
> `AStar` returning suboptimal costs — and costs that disagree with the path
> it hands back — whenever the heuristic is admissible but not *consistent*,
> which is weaker than the condition its docstring states. The defect is at
> `src/flight_planner/pathfinding/astar.py:84`, it still
> reproduces on current code, and [Option E](#option-e--randomized-differential-testing)
> now carries the patch. On the project's own data the heuristic is consistent
> (verified below), so no committed result is wrong — and the fix leaves the
> committed comparison table bit-for-bit unchanged, which is measured rather
> than assumed.

> **Which code this describes.** Everything here was re-run against
> `f40ee82` (`feature/search-instrumentation`), which is a linear superset of
> `main` and carries the from-scratch `MinHeap`, the one-module-per-algorithm
> split of `pathfinding/`, and the `SearchResult` / `SearchObserver`
> instrumentation. The first pass was written against `fd475e1`, before any of
> that; every figure has been re-measured rather than carried over. See
> [§1, What the refactor changed](#what-the-refactor-changed) and
> [Appendix A](#appendix-a--how-these-were-run).
>
> This document itself sits on `worktree-NetworkX`, which branches from
> `fd475e1` — so the files it names under `pathfinding/` are not in *this*
> branch's tree. They appear once this branch is rebased onto
> `feature/search-instrumentation`, which is where it should land.

---

## 1. What is already there to build on

The existing machinery does most of the work. Nothing below needs new
infrastructure:

| Piece | Where | What it gives a validation effort |
| --- | --- | --- |
| `Snapshot` | `flight_planner/experiments/snapshot.py` | Checksummed, immutable input — a parity run and a re-run months later provably read the same bytes |
| `Catalog` | `flight_planner/experiments/catalog.py` | A vocabulary for choosing the scope to validate on, and a `summary()` recording how it was derived |
| `Experiment` | `flight_planner/experiments/experiment.py` | A directory pinning a snapshot, declared parameters, and `record()` writing `results.json` next to the data's identity |
| `PathfindingAlgorithm` | `flight_planner/pathfinding/strategy.py` | A Strategy interface — anything implementing `search(graph, start, goal, observer=None)` is a drop-in engine, and inherits `find_path` |
| `SearchResult` | `flight_planner/pathfinding/result.py` | `cost`, `path`, and the three counters — `nodes_expanded`, `nodes_pushed`, `peak_frontier`. Turns "same answer" parity into "same answer, less work" parity |
| `SearchObserver`, `ExpansionTrace` | `flight_planner/pathfinding/observers.py` | Per-event hooks, so a parity harness can compare the *order* two searches looked, not just the totals |
| `MinHeap` | `flight_planner/adt/min_heap.py` | The from-scratch priority queue `Dijkstra` and `AStar` run on. `pop()` returns the item without its priority — which constrains the A\* fix in Option E |
| `Graph.get_outgoing_edges` | `flight_planner/core/graph.py` | The *only* traversal method the algorithms use, so an adapter has exactly one surface to cover |
| `tests/experiments/test_committed.py` | tests | The precedent for "the committed artifacts must keep producing the committed answers" |
| `make experiment SLUG=...` | `Makefile:275` | Scaffolds an experiment directory that runs end to end as written |

Two committed experiments are the natural subjects:

- **`experiments/sfo-bos-dijkstra`** — the whole world, narrowed in the
  notebook: 66,332 routes / 3,387 airports frozen, narrowed to 861 / 88.
- **`experiments/shortest-vs-fewest`** — the tutorial's experiment, narrowed at
  freeze time to US large airports: 7,005 routes / 94 airports. Its finding is
  that BFS returns *a* minimum-hop route, not the shortest one among them.
- **`experiments/search-cost`** — the comparison table and the runtime plot,
  pinned to the world snapshot, five long-haul pairs and eight narrowings from
  2,329 to 69,719 V+E. The experiment this document's Option G validates, and
  the one whose numbers the A\* fix must not disturb.

### What the refactor changed

`pathfinding/algorithms.py` no longer exists. Anything written against the
first draft of this document needs these five substitutions:

| Was | Is now |
| --- | --- |
| `pathfinding/algorithms.py` | `pathfinding/strategy.py`, `dijkstra.py`, `bfs.py`, `astar.py`, plus `result.py` and `observers.py` |
| `find_path` is the abstract method | `search` is abstract; `find_path` is a concrete adapter on the ABC returning `(cost, path)` |
| a search returns `(cost, path)` | `search` returns `SearchResult` — `cost`, `path`, `nodes_expanded`, `nodes_pushed`, `peak_frontier` |
| `heapq` inside `Dijkstra`/`AStar` | `MinHeap` from `adt/min_heap.py`; `pop()` yields the item alone, no priority |
| `planner.find_shortest_route(...)` only | also `planner.search_route(origin, destination, algorithm=None, observer=None)`, and `Graph.search` beside `Graph.shortest_path` |

`find_path` and `find_shortest_route` are untouched, so **every code block in
Options A, B, D, E and F still runs as printed** — re-verified, not assumed.
[Option C](#option-c--networkx-behind-the-pathfindingalgorithm-interface) is
the exception and the one thing the refactor genuinely breaks: it implemented
`find_path`, which is no longer the hook, so its class will not instantiate.
That option carries the corrected version.

What the refactor *adds* is a validation target the first draft could not
describe, because `find_path` discarded it: the counters. See
[Option G](#option-g--counter-parity-validating-the-claim-itself).

Three counter semantics matter to a parity harness, because they are choices
rather than facts:

- The goal is **never** expanded — every algorithm breaks on popping it.
- `BFS` marks visited at *push* time, so it carries an explicit expansion
  counter (`bfs.py:69`) rather than reporting `len(visited)`.
- `Dijkstra` and `AStar` report `len(settled)` / `len(visited)`, which is
  exact only because neither re-expands. That coupling is why the Option E
  patch has to add a counter when it drops the closed set.

---

## 2. The adapter, and the one decision that matters

Everything below rests on twenty lines. This is the whole bridge:

```python
"""Build a NetworkX view of a FlightPlanner, losing nothing."""

from __future__ import annotations

import networkx as nx

from flight_planner.flights.planner import FlightPlanner


def to_networkx(planner: FlightPlanner) -> nx.MultiDiGraph:
    """Return the planner as a NetworkX multigraph.

    A MultiDiGraph, not a DiGraph: the data has up to 20 parallel routes
    between one airport pair, and a DiGraph would silently keep only the last.

    Args:
        planner: Flight network to mirror.

    Returns:
        Graph whose nodes are IATA codes and whose edges carry `weight` in km.
    """
    graph = nx.MultiDiGraph()
    for airport in planner.vertices:
        graph.add_node(
            airport.iata_code,
            lat=airport.latitude,
            lon=airport.longitude,
            name=airport.name,
        )
    for route in planner.edges:
        graph.add_edge(
            route.origin.iata_code,
            route.destination.iata_code,
            key=route.flight_number or None,
            weight=route.distance_km,
            airline=route.airline,
        )
    return graph
```

**`MultiDiGraph` is not a style preference.** Choosing `DiGraph` would make
every parity test below pass while comparing a graph nobody built:

```python
planner = Snapshot.open("data/snapshots/2026-09-11-bb90a8").catalog().planner()

multi = to_networkx(planner)
simple = nx.DiGraph()
for route in planner.edges:
    simple.add_edge(route.origin.iata_code, route.destination.iata_code,
                    weight=route.distance_km)

print("routes in the snapshot :", len(planner.edges))
print("MultiDiGraph edges     :", multi.number_of_edges())
print("DiGraph edges          :", simple.number_of_edges())
```

```
routes in the snapshot : 66332
MultiDiGraph edges     : 66332
DiGraph edges          : 36717 (29615 routes discarded)
most parallel routes   : ORD->ATL 20
```

Nearly half the network vanishes. With the multigraph, nothing does — the
adapter's edge count equals the snapshot's route count exactly, which is worth
asserting in the test suite rather than trusting.

The rest of the mapping is direct:

| `flight_planner` | NetworkX | Note |
| --- | --- | --- |
| `Airport` (identity = IATA code) | node, keyed by the IATA string | Coordinates and metadata become node attributes |
| `Route` | edge with `weight=distance_km` | |
| `FlightPlanner` | `nx.MultiDiGraph` | See above |
| `Dijkstra().find_path` | `nx.shortest_path(_length)(G, o, d, weight="weight")` | |
| `BFS().find_path` | `nx.shortest_path(_length)(G, o, d)` (unweighted) | Both return hop count |
| `AStar(h).find_path` | `nx.astar_path(_length)(G, o, d, heuristic=..., weight=...)` | NetworkX passes *node keys*, `flight_planner` passes *vertices* — bridge with `planner.iata_lookup` |
| `Catalog.planner()` | build the graph after narrowing | Narrowing stays on the `Catalog` side |

One more thing the real data contains: exactly one self-loop, `PKN → PKN`
(airline `IL`, flight `IL0016`), which is also the only zero-weight edge.
Neither breaks either library, but a harness has to expect them rather than
assert them away.

---

## 3. The options

### Option A — NetworkX as an oracle in the test suite

**What it is.** The adapter above plus one test module. This is the module, as
run.

**Where the two files go.** `tests/networkx_parity/`, the adapter beside the
test module. The bare `from nx_adapter import to_networkx` works because no
directory under `tests/` has an `__init__.py`, so pytest's default `prepend`
import mode puts each test file's own directory on `sys.path` — adding `tests`
to `pythonpath` in `pyproject.toml` is not needed and was not done. The
adapter stays out of `src/flight_planner/`: the wheel imports pandas and
nothing else, and NetworkX is a `dev` concern (§5).

```python
"""NetworkX as an oracle: our answers must be NetworkX's answers."""

import math

import networkx as nx
import pytest

from flight_planner import BFS, Dijkstra
from flight_planner.experiments import Experiment

from nx_adapter import to_networkx


@pytest.fixture(scope="module")
def planner(repo_root):
    return Experiment.open(
        repo_root / "experiments" / "shortest-vs-fewest"
    ).catalog().planner()


@pytest.fixture(scope="module")
def oracle(planner):
    return to_networkx(planner)


@pytest.fixture(scope="module")
def pairs(planner):
    codes = sorted(airport.iata_code for airport in planner.vertices)
    return [(o, d) for o in codes for d in codes if o != d]


def test_the_two_graphs_are_the_same_graph(planner, oracle):
    # A DiGraph would pass every parity test below while comparing a graph we
    # never built: 7005 routes span only 3060 airport pairs.
    assert oracle.number_of_nodes() == len(planner.vertices)
    assert oracle.number_of_edges() == len(planner.edges)


def test_dijkstra_agrees_with_networkx_on_every_pair(planner, oracle, pairs):
    reference = dict(nx.all_pairs_dijkstra_path_length(oracle, weight="weight"))

    disagreements = []
    for origin, destination in pairs:
        ours, _ = planner.find_shortest_route(origin, destination, Dijkstra())
        theirs = reference[origin].get(destination, math.inf)
        if not (math.isinf(ours) and math.isinf(theirs)) and not math.isclose(
            ours, theirs, rel_tol=1e-9
        ):
            disagreements.append((origin, destination, ours, theirs))

    assert disagreements == []


def test_bfs_hop_counts_agree_with_unweighted_networkx(planner, oracle, pairs):
    reference = dict(nx.all_pairs_shortest_path_length(oracle))

    disagreements = []
    for origin, destination in pairs:
        hops, _ = planner.find_shortest_route(origin, destination, BFS())
        theirs = reference[origin].get(destination, math.inf)
        if hops != float(theirs):
            disagreements.append((origin, destination, hops, theirs))

    assert disagreements == []


def test_dijkstra_returns_a_path_whose_legs_sum_to_its_cost(planner, oracle, pairs):
    # Cost parity is the durable contract; with up to 20 parallel edges the two
    # libraries may legitimately pick different equal-cost paths. What must
    # hold is that our path is really the route we charged for.
    for origin, destination in pairs[:200]:
        cost, legs = planner.find_shortest_route(origin, destination, Dijkstra())
        assert sum(leg.distance_km for leg in legs) == pytest.approx(cost)
        assert nx.shortest_path_length(
            oracle, origin, destination, weight="weight"
        ) == pytest.approx(cost)
```

**What it produced.** Every one of the 8,742 ordered pairs on the tutorial
snapshot, for both algorithms:

```
....                                                                     [100%]
============================= slowest 5 durations ==============================
9.66s call     test_dijkstra_agrees_with_networkx_on_every_pair
4.83s call     test_bfs_hop_counts_agree_with_unweighted_networkx
0.43s call     test_dijkstra_returns_a_path_whose_legs_sum_to_its_cost
0.06s setup    test_the_two_graphs_are_the_same_graph
4 passed in 16.87s
```

Zero disagreements. Both engines also agree on the path itself, edge for edge,
on the tutorial's three pairs:

```
SFO-BOS: fp=4341.022085 nx=4341.022085  SFO->BOS
BOI-CHS: fp=3376.003135 nx=3376.003135  BOI->DEN->BNA->CHS
HNL-BDL: fp=8071.513691 nx=8071.513691  HNL->SLC->DTW->BDL
```

Both figures are unchanged from the first pass, min-heap and all — the paths
match NetworkX's edge for edge, not merely in cost.

**Cost.** ~90 lines. 16.87 s added to a suite that now runs in 42.78 s over
382 tests — a 39 % increase, so sample pairs by default (a seeded random
subset) and gate the exhaustive sweep behind a marker:

```toml
[tool.pytest.ini_options]
markers = ["slow: exhaustive sweeps, excluded from the default run"]
addopts = "-m 'not slow'"
```

There is no `markers` key in `pyproject.toml` today, and `--strict-markers` is
not set, so an unregistered `@pytest.mark.slow` would silently become a
warning rather than an error. Register it in the same change.

**Caveats.** Compare *costs* first and paths second: with up to 20 parallel
edges, ties are common and the two libraries may break them differently.
Asserting on equal total cost is the durable contract.

**Verdict.** Highest value per line of code. Do this first.

---

### Option B — A parity *experiment*, recorded like any other result

**What it is.** `experiments/networkx-parity/`, scaffolded with
`make experiment SLUG=networkx-parity`, pinned to a committed snapshot. Its
code sweeps pairs and calls `experiment.record()`:

```python
experiment.record(
    {
        "oracle": f"networkx {nx.__version__}",
        "pairs_checked": len(pairs),
        "cost_mismatches": len(disagreements),
        "largest_absolute_divergence_km": worst_abs,
        "algorithms": ["Dijkstra", "BFS", "AStar"],
    },
    catalog=catalog,
)
```

`results.json` then carries the snapshot id, its source commit, and the
narrowing chain — the same provenance every other result has.

**Why it is not redundant with Option A.** A test says today's code is right.
A recorded experiment says *when* parity was established and against which
oracle version, which a green CI run does not — and it extends naturally to
reporting divergence as a distribution rather than a boolean.

#### This is the artifact the final report cites

`docs/report.md` already reserves the section: §5, *Correctness Testing* →
"Library cross-validation results (NetworkX)". A green test suite is not
citable in prose — "our tests pass" is an assertion, and the reader cannot see
what was compared or against which oracle. A committed
`experiments/networkx-parity/results.json` is a number with provenance
attached, and the report can quote it the way it quotes
`experiments/search-cost`.

So record more than a boolean. Everything the report's §5 and §7 need, in one
payload:

```python
experiment.record(
    {
        "oracle": f"networkx {nx.__version__}",
        "snapshot_scope": catalog.summary(),
        "pairs_checked": len(pairs),
        "cost_mismatches": len(disagreements),
        "largest_absolute_divergence_km": worst_abs,
        # Option G's half of the claim, so the table in the report comes from
        # a recorded run rather than a console session.
        "expansions": {"BFS": bfs_total, "Dijkstra": dijkstra_total, "AStar": astar_total},
        "pairs_where_astar_expanded_more": worse,
        # Option F, honestly framed: two engines, same queries.
        "seconds": {
            "flight_planner": {"Dijkstra": ours_d, "AStar": ours_a},
            "networkx": {"Dijkstra": nx_d, "AStar": nx_a},
        },
        "randomized": {"queries": 10866, "suboptimal": 0},
    },
    catalog=catalog,
)
```

That one file supports four of the report's sections: §5 cross-validation, §6's
complexity write-up (the measured `peak_frontier` against the claimed `O(V)`
bound), §7's nodes-expanded and runtime comparisons, and §10's conclusion.
Choose the **world** snapshot rather than the US slice, for the same reason
`search-cost` does: the catalog asks for long-haul queries, and only the world
graph has long hauls in it.

**Cost.** One experiment directory. No new infrastructure.

**Caveats.** Adds a NetworkX version to the reproducibility surface. Put it in
`[parameters]` so the result states its own oracle. Note also that this is the
one option that *needs* re-running whenever the oracle floor moves — a test
fails loudly on drift, a recorded result just goes stale.

**Verdict.** Cheap, fits the project's existing model exactly, and it is the
only option on this list that produces something the final report can cite.

---

### Option C — NetworkX behind the `PathfindingAlgorithm` interface

**What it is.** An adapter implementing the existing Strategy, so the engine
becomes a *parameter* of an experiment exactly as `Dijkstra()` vs `BFS()`
already is in `shortest-vs-fewest`.

> **This is the one option the refactor breaks.** The first pass implemented
> `find_path`, which was the abstract method then. It is now a concrete
> adapter on the ABC and `search` is abstract, so the original class no longer
> instantiates at all:
>
> ```
> TypeError: Can't instantiate abstract class NetworkXDijkstra without an
> implementation for abstract method 'search'
> ```
>
> The body is unchanged; it moves into `search` and returns a `SearchResult`.
> Below is the corrected version.

```python
class NetworkXDijkstra(PathfindingAlgorithm):
    """Reference engine: NetworkX does the search, we return our own types.

    The graph is built once and cached, so the planner must not be mutated
    afterwards. NetworkX returns a node path, not edges, so each hop is mapped
    back to the cheapest parallel Route between those two airports -- which
    reproduces the cost exactly, but not necessarily the same flight number
    when several legs tie.

    The counters are reported as zero rather than guessed at: NetworkX does
    not expose how many nodes it expanded, and a fabricated number here would
    quietly corrupt any comparison table this engine appears in.
    """

    def __init__(self) -> None:
        self._graph = None
        self._planner = None

    def search(self, graph, start, goal, observer=None):
        if graph is not self._planner:
            self._planner = graph
            self._graph = to_networkx(graph)

        if start == goal:
            return SearchResult(0.0, [])
        try:
            nodes = nx.shortest_path(self._graph, start.key, goal.key, weight="weight")
        except nx.NetworkXNoPath:
            return SearchResult(float("inf"), [])

        legs = []
        for origin, destination in zip(nodes, nodes[1:]):
            candidates = [
                edge
                for edge in graph.get_outgoing_edges(graph.find_airport(origin))
                if edge.target.key == destination
            ]
            legs.append(min(candidates, key=lambda edge: edge.weight))
        return SearchResult(sum(leg.weight for leg in legs), legs)
```

`find_path` is inherited, so the call site below is untouched — which is the
point of `find_path` having become an adapter rather than the hook.

Nothing else changes — the existing call site takes it directly:

```python
for origin, destination in experiment.parameters["pairs"]:
    for name, engine in {"flight_planner": Dijkstra(),
                         "networkx": NetworkXDijkstra()}.items():
        km, legs = planner.find_shortest_route(origin, destination, engine)
```

```
SFO-BOS  flight_planner    4341.022 km  SFO->BOS
SFO-BOS  networkx          4341.022 km  SFO->BOS
BOI-CHS  flight_planner    3376.003 km  BOI->DEN->BNA->CHS
BOI-CHS  networkx          3376.003 km  BOI->DEN->BNA->CHS
HNL-BDL  flight_planner    8071.514 km  HNL->SLC->DTW->BDL
HNL-BDL  networkx          8071.514 km  HNL->SLC->DTW->BDL

8742 pairs: cost mismatches=0, identical flight numbers=8742
```

**What it validates beyond Option A.** The *return contract* — that a NetworkX
result can be expressed as a `SearchResult` over `Route` legs, that
`(inf, [])` and `(0.0, [])` mean the same in both, and that downstream code
(leg counting, flight numbers, `results.json` shape) is engine-agnostic. The
run below is from the first pass, at `fd475e1`; the costs are data facts and
unchanged, but it has not been re-run through `search`.

**Caveats.** The re-selection of parallel edges *could* pick different flight
numbers than `flight_planner` does; on this snapshot it never did, in all
8,742 pairs. Two other failure modes hide here: rebuilding the graph per call
makes the adapter look pathologically slow, and caching it goes stale if the
planner is mutated — hence the identity check and the docstring warning.

**Verdict.** Worth it if the goal is *comparison as an experiment*. Skip it if
Option A is the whole ambition.

---

### Option D — Use NetworkX for what `flight_planner` has no vocabulary for

**What it is.** Not parity: using NetworkX's structural analysis to validate
the *data and the questions*. One screenful, run against the global snapshot:

```python
world = to_networkx(Snapshot.open("data/snapshots/2026-09-11-bb90a8").catalog().planner())

components = sorted(nx.strongly_connected_components(world), key=len, reverse=True)
print("components:", len(components), "| largest:", len(components[0]),
      "| one-way-only airports:", sum(1 for c in components if len(c) == 1))
print("self-loops:", nx.number_of_selfloops(world))
weights = [data["weight"] for *_, data in world.edges(data=True)]
print("min weight:", min(weights), "| negative weights:", sum(w < 0 for w in weights))
```

```
components: 42 | largest: 3318 | one-way-only airports: 33
self-loops: 1
min weight: 0.0 | negative weights: 0
```

Each line is a validation statement `flight_planner` cannot currently make:

- **42 strongly connected components, 33 of them singletons.** Those 33
  airports can be reached but never left (or vice versa). Any experiment
  sampling random pairs will hit unreachable ones, and *knowing which* turns
  "no route found" from a suspicion into a fact.
- **No negative weights** is precisely Dijkstra's precondition, now checked
  rather than assumed.

**And it can replace hand-rolled analysis.** The `shortest-vs-fewest`
experiment computes "the best route at BFS's hop count" with a nested
comprehension that only works because the answer happens to be two legs.
NetworkX enumerates every minimum-hop path directly, at any hop count:

```python
for row in experiment.results()["results"]["pairs"]:
    origin, destination = row["pair"].split("-")
    best = min(
        sum(min(data["weight"] for data in graph[u][v].values())
            for u, v in zip(path, path[1:]))
        for path in nx.all_shortest_paths(graph, origin, destination)
    )
```

```
SFO-BOS:  4341.022 km at 1 hops   (results.json says  4341.022)
BOI-CHS:  3531.417 km at 2 hops   (results.json says  3531.417)
HNL-BDL:  8076.038 km at 2 hops   (results.json says  8076.038)
```

Exact agreement with the recorded results, from four lines that generalize.

**Cost.** Near zero. **Verdict.** Highest insight per unit of effort, and the
option that most strengthens the docs.

---

### Option E — Randomized differential testing

**What it is.** Random small graphs, both engines on every pair, assert equal
costs. No project data involved — this reaches the cases flight data never
produces: dense graphs, disconnected graphs, zero weights, ties, and
heuristics that are admissible without being consistent.

```python
def random_graph(seed):
    """Return a random weighted digraph as both a Graph and an nx.DiGraph."""
    rng = random.Random(seed)
    order = rng.randint(2, 25)
    size = rng.randint(0, order * 3)

    ours, theirs = Graph(), nx.DiGraph()
    vertices = [Vertex(f"n{i}") for i in range(order)]
    for vertex in vertices:
        ours.add_vertex(vertex)
        theirs.add_node(vertex.key)
    for _ in range(size):
        source, target = rng.choice(vertices), rng.choice(vertices)
        # Ties and zero weights on purpose; negative weights are outside
        # Dijkstra's contract, so not generated.
        weight = rng.choice([0.0, 1.0, 1.0, 2.5, rng.random() * 10])
        ours.add_edge(Edge(source, target, weight=weight))
        if theirs.has_edge(source.key, target.key):
            weight = min(weight, theirs[source.key][target.key]["weight"])
        theirs.add_edge(source.key, target.key, weight=weight)
    return ours, theirs, vertices


def reference(theirs, origin, destination, weight="weight"):
    """Return NetworkX's shortest-path length, or infinity if none exists."""
    try:
        return nx.shortest_path_length(theirs, origin, destination, weight=weight)
    except nx.NetworkXNoPath:
        return math.inf


@pytest.mark.parametrize("seed", range(50))
def test_astar_stays_optimal_under_an_inconsistent_heuristic(seed):
    """Admissible but deliberately not consistent.

    h(v) is a random fraction of the true remaining distance: it never
    overestimates, so A* must still return the optimal cost, but it violates
    the triangle inequality that a visited-set A* implicitly relies on.
    """
    ours, theirs, vertices = random_graph(seed)
    rng = random.Random(seed ^ 0xA5)

    for goal in vertices:
        remaining = dict(nx.shortest_path_length(theirs, target=goal.key, weight="weight"))

        def heuristic(vertex, _goal, remaining=remaining, rng=rng):
            return remaining.get(vertex.key, 0.0) * rng.random()

        for start in vertices:
            if start == goal:
                continue
            optimal = reference(theirs, start.key, goal.key, "weight")
            cost, _ = AStar(heuristic).find_path(ours, start, goal)
            assert cost == pytest.approx(optimal), f"seed={seed} {start.key}->{goal.key}"
```

**What it found.** Dijkstra and BFS pass all 50 seeds clean. A\* does not
(this run is from the first pass, at `fd475e1`):

```
7 failed, 143 passed in 1.14s
E   AssertionError: seed=38 n17->n0
E   assert 4.5 == 4.0 ± 4.0e-06
```

Reduced to four vertices:

```python
s, a, b, g = Vertex("S"), Vertex("A"), Vertex("B"), Vertex("G")
graph = Graph()
for edge in (Edge(s, a, 2.0), Edge(s, b, 1.0), Edge(b, a, 0.5), Edge(a, g, 1.0)):
    graph.add_edge(edge)

# True remaining cost to G: S=2.5, B=1.5, A=1.0, G=0.
# This heuristic never overestimates any of them, so it is admissible.
# It is not consistent: h(S)=0 but h(B)=1.5 across an edge of weight 1.0.
ADMISSIBLE = {"S": 0.0, "B": 1.5, "A": 0.0, "G": 0.0}
```

```
networkx       2.5
Dijkstra       2.5
AStar          3.0 via S->B->A->G
```

Two distinct defects in one line of output. A\* returns **3.0** where the
optimum is 2.5, and the path it returns — `S->B->A->G` — has legs summing to
2.5, so the cost it reports does not describe the route it hands back. The
cause is `pathfinding/astar.py:84-86`: a vertex is added to `visited` on pop
and skipped forever after, so when a later, cheaper route to `A` is found,
`predecessors` is updated but the improved cost never propagates to `G`.

The same four vertices, run against the post-refactor `AStar` so the counters
are visible too:

```
Dijkstra  cost 2.5  path S->B->A->G   legs sum 2.5  expanded 3 pushed 5 peak 2
AStar     cost 3.0  path S->B->A->G   legs sum 2.5  expanded 3 pushed 5 peak 2
```

#### The patch

Removing the closed set — skipping stale queue entries instead, which is the
standard formulation — fixes every case. Two details are forced by the code as
it now stands:

- **`MinHeap.pop()` returns the item without its priority**, so a stale entry
  cannot be recognised the usual way, by comparing the popped `f` against
  `g[v] + h(v)`. Comparing `g[v]` against the g-score it carried at its last
  expansion does the same job, and also permits a *genuine* re-expansion,
  which is the whole point.
- **`nodes_expanded` is `len(visited)`** (`astar.py:103`). Dropping the closed
  set deletes the set the counter counts, so the patch has to carry an
  explicit counter — exactly as `bfs.py` already does.

```python
        g_score: Dict[V, float] = {start: 0.0}
        predecessors: Dict[V, E] = {}
        # g-score this vertex carried the last time it was expanded. A pop
        # whose g is no better than that is a superseded queue entry; a pop
        # whose g is better is a route found after the vertex was closed, and
        # under an inconsistent heuristic that is the case the shipped
        # `visited` set silently discarded.
        expanded_at: Dict[V, float] = {}
        expanded = 0

        while open_set:
            current = open_set.pop()

            if current == goal:
                break
            if g_score[current] >= expanded_at.get(current, float("inf")):
                continue
            expanded_at[current] = g_score[current]
            expanded += 1
            watcher.on_expand(current, g_score[current])
            ...

        counters = {
            "nodes_expanded": expanded,          # not len(visited)
            "nodes_pushed": pushed,
            "peak_frontier": peak,
        }
```

The rest of `search` is unchanged. Run against NetworkX over the 50 random
graphs — every ordered pair, every vertex as goal, with the deliberately
inconsistent heuristic:

```
queries                      : 10866
shipped AStar suboptimal     : 43
  of those, cost != path sum : 35
ReopeningAStar suboptimal    : 0
nodes_expanded, shipped      : 40118
nodes_expanded, reopening    : 40352
first failure                : (0, 'n3', 'n5', 14.17652491252719, 9.14466863291336)
```

Correctness costs **0.58 % more expansions** across the whole sweep, and only
on inconsistent heuristics — the re-expansions are the fix doing its job.

#### The fix does not move the committed comparison table

That was the open question the refactor created, since `experiments/search-cost`
publishes A\*'s expansion counts. Both engines on the experiment's five
long-haul pairs, against the world snapshot with the real haversine heuristic:

```
airports 3387  routes 66332
pair       BFS exp  Dij exp  A* exp  reopen exp        A* km    reopen km
SFO-BOS          10      746       1           1     4341.022     4341.022
LAX-JFK          62      590       1           1     3974.164     3974.164
SEA-MIA          52      784       1           1     4379.358     4379.358
HNL-BOS         132     1056       3           3     8192.794     8192.794
ANC-MIA         174      778       6           6     6459.622     6459.622

Dijkstra            8.29 ms/query
AStar               0.28 ms/query
ReopeningAStar      0.26 ms/query
```

Identical expansions and identical distances on all five, because a consistent
heuristic never triggers a re-expansion. The comparison table, the runtime
plot and `results.json` all stand as committed.

**No committed result is affected.** `AStar`'s docstring promises optimality
for *admissible* heuristics; the implementation delivers it only for
*consistent* ones. On this project's data the great-circle heuristic is
consistent, which is verifiable rather than assumed — for every edge and every
possible goal in the tutorial snapshot:

```python
for goal in airports:
    for route in planner.edges:
        left = formula.calculate(route.origin, goal)
        right = route.distance_km + formula.calculate(route.destination, goal)
        if left > right + 1e-9:
            violations += 1
```

```
consistency checks: 658470, violations: 0 (worst 0.000000 km)
A* vs Dijkstra on every pair: mismatches 0
```

So the fix is a choice, not an emergency: either tighten the docstring to say
*consistent*, or drop the closed set and honour what it already claims. Either
way the finding is exactly the kind of thing four-vertex fixtures never reach.

**Recommendation, now that the cost is measured.** Take the patch. It is a
dozen lines, it costs 0.58 % more expansions only where the heuristic is
inconsistent, it moves no committed number, and it removes a state where the
returned cost contradicts the returned path — which is far harder to explain
in a report than a re-expansion is. If the patch is *not* taken, all three
places `astar.py` says *admissible* — lines 25, 35 and 61 — must say
*consistent* instead, and the report's admissibility argument has to make the
stronger claim, which the project's own heuristic does satisfy.

**Cost.** ~90 lines for the harness, 1.1 s; ~12 lines for the patch, plus a
regression test built from the four-vertex graph above.

**Note on the counts.** The first pass reported 42 suboptimal results and 33
cost/path disagreements; the recount at `f40ee82` gives 43 and 35 over 10,866
queries. The harness above is the one that produced the second pair, and is
the one to commit.

**Verdict.** The strongest bug-finder of the five.

---

### Option F — Benchmarking, with honest framing

On 25 random reachable pairs from the global snapshot's largest strongly
connected component (3,318 airports, 66,332 routes), all 25 in agreement for
both Dijkstra and A\*:

| engine | first pass, `fd475e1` (`heapq`) | re-run, `f40ee82` (`MinHeap`) |
| --- | --- | --- |
| `flight_planner` Dijkstra | 0.31 s | **0.42 s** |
| NetworkX Dijkstra | 0.36 s | 0.25 s |
| `flight_planner` A\* (memoized haversine) | 0.08 s | 0.08 s |
| NetworkX A\* (same heuristic) | 0.06 s | 0.04 s |

**The min-heap is visible here, and that is the point.** Replacing `heapq` —
C, and not the graded deliverable — with the from-scratch `MinHeap` cost
Dijkstra roughly 35 % on the same query set, while A\* barely moved because it
pops so few entries. Both columns agreed with NetworkX to the last decimal
(worst absolute delta 0.00e+00 km on the re-run). The two columns are not
strictly comparable: the pairs are drawn with a different seed, so read the
*ratios*, not the deltas.

**The honest caveat.** These are not comparable systems: NetworkX walks
dict-of-dicts with string keys; `flight_planner` walks objects and allocates
`Route` lists. Graph construction (0.37 s for the whole world) sits outside the
loop. The useful conclusion is the modest one — *`flight_planner` is in the
same performance class as a mature library, and A\* is roughly 5× faster than
Dijkstra on this data* — not a leaderboard.

**Verdict.** A supporting table inside Option B's experiment. Do not build a
benchmark suite around it.

---

### Option G — Counter parity: validating the claim itself

**What it is.** The option the first draft could not describe, because
`find_path` threw the counters away. Options A–F all validate *what* a search
found. The instructor's problem statement is about something else:

> show how informed search (A\*) expands fewer nodes than uninformed search
> (BFS/Dijkstra) **while returning the same answer**

That is two assertions, and `SearchResult` makes the second one testable
against an oracle and the first one testable at all. This is the module, as
run:

```python
"""A* parity, on both halves of the claim: same answer, less work."""

import math

import networkx as nx
import pytest

from flight_planner import AStar, Dijkstra
from flight_planner.experiments import Experiment
from flight_planner.geo import Haversine, Memoized

from nx_adapter import to_networkx


@pytest.fixture(scope="module")
def planner(repo_root):
    return Experiment.open(
        repo_root / "experiments" / "shortest-vs-fewest"
    ).catalog().planner()


@pytest.fixture(scope="module")
def oracle(planner):
    return to_networkx(planner)


@pytest.fixture(scope="module")
def formula():
    return Memoized(Haversine())


@pytest.fixture(scope="module")
def pairs(planner):
    codes = sorted(airport.iata_code for airport in planner.vertices)
    return [(o, d) for o in codes for d in codes if o != d]


def test_astar_agrees_with_networkx_astar(planner, oracle, formula, pairs):
    lookup = planner.iata_lookup
    heuristic = lambda a, b: a.distance_to(b, formula=formula)  # noqa: E731

    # NetworkX hands the heuristic node keys; `flight_planner` hands it
    # vertices. `iata_lookup` is the whole bridge.
    def nx_heuristic(a, b):
        return lookup[a].distance_to(lookup[b], formula=formula)

    disagreements = []
    for origin, destination in pairs[:500]:
        ours = planner.search_route(origin, destination, AStar(heuristic))
        try:
            theirs = nx.astar_path_length(
                oracle, origin, destination, heuristic=nx_heuristic, weight="weight"
            )
        except nx.NetworkXNoPath:
            theirs = math.inf
        if not (math.isinf(ours.cost) and math.isinf(theirs)) and not math.isclose(
            ours.cost, theirs, rel_tol=1e-9
        ):
            disagreements.append((origin, destination, ours.cost, theirs))

    assert disagreements == []


def test_astar_does_less_work_than_dijkstra_for_the_same_answer(
    planner, formula, pairs
):
    heuristic = lambda a, b: a.distance_to(b, formula=formula)  # noqa: E731

    worse = []
    for origin, destination in pairs[:500]:
        dijkstra = planner.search_route(origin, destination, Dijkstra())
        astar = planner.search_route(origin, destination, AStar(heuristic))
        assert astar.cost == pytest.approx(dijkstra.cost)
        if astar.nodes_expanded > dijkstra.nodes_expanded:
            worse.append((origin, destination, astar.nodes_expanded,
                          dijkstra.nodes_expanded))

    assert worse == []
```

**What it produced.**

```
expansions over 500 pairs: Dijkstra 23346, A* 1302
2 passed in 1.98s
```

A\* never expanded more than Dijkstra on any of the 500 pairs, and expanded
**18× fewer** in total — with NetworkX's own A\* confirming the distances, so
"same answer" is not being taken on trust from our other algorithm.

**Why this is worth more than it looks.** `experiments/search-cost` already
publishes the comparison table, but nothing *guards* it: a future change to
the heuristic, the closed set, or the frontier could quietly invert the
project's headline result and every existing test would still pass. This is
the regression test for the thesis. It is also what catches the Option E
defect from the other direction — a search whose reported cost disagrees with
its own path will fail `test_astar_agrees_with_networkx_astar` the moment the
heuristic stops being consistent.

**Caveat.** `nodes_expanded` means "vertices whose outgoing edges were
requested, goal excluded", and `BFS` counts it differently from the weighted
pair for a real reason (§1). Do not assert BFS's count against theirs; assert
each algorithm against its own history, and A\* against Dijkstra.

**Cost.** ~70 lines, 2.0 s. **Verdict.** Do this with Option A. Same fixtures,
same adapter, and it tests the sentence the project is graded on.

---

## 4. Recommendation

One change, `tests/networkx_parity/`, in this order:

1. **Option A** — `nx_adapter.py` plus the oracle module, sampled by default,
   exhaustive under `-m slow`. Register the marker in the same commit.
   *~90 lines, 16.87 s exhaustive.*
2. **Option G** — counter parity, in the same directory on the same fixtures.
   The regression test for the project's headline claim. *~70 lines, 2.0 s.*
3. **Option E** — the randomized harness, **and take the patch**: drop A\*'s
   closed set, add the explicit expansion counter, and keep the four-vertex
   graph as a named regression test. *~90 lines for the harness, ~12 for the
   patch.*
4. **Option B** — `experiments/networkx-parity` on the **world** snapshot,
   folding in Option G's expansion totals and Option F's timing table. This is
   the step that makes the work citable: it is what `docs/report.md` §5 quotes,
   and it reuses steps 1–3's code rather than adding any. *One experiment
   directory, no new infrastructure.*
5. **Option D** — structural checks, plus the `all_shortest_paths` rewrite of
   the tutorial's two-leg comprehension. *Mostly documentation work.*
6. **Option C** — the Strategy adapter, only if the goal grows to "run any
   experiment on either engine".

Steps 1–3 are a day's work and would take algorithm correctness from
"four-vertex fixtures plus three pinned results" to "agrees with an
independent implementation on 8,742 real pairs and 10,866 randomized queries,
expands fewer nodes than Dijkstra on every one of 500 pairs, and fails loudly
if that stops being true".

Two of the three are also rubric items rather than nice-to-haves: "validated
against a library reference" is the instructor's Stage 2 milestone, and A1
names NetworkX specifically.

Step 4 is what turns steps 1–3 into a graded output. Tests satisfy the
milestone; only the recorded experiment gives the report a number with a
snapshot id, a narrowing chain and an oracle version attached. Budget it as
part of the same change rather than as a follow-up — the sweep code is already
written by then, and `make experiment SLUG=networkx-parity` scaffolds the rest.

---

## 5. Dependency placement

NetworkX must **not** enter `[project.dependencies]`. `pyproject.toml` states
the wheel's runtime contract deliberately: *"The package imports pandas and
nothing else."* Validation is the repository's concern, not the package's.

```toml
[dependency-groups]
dev = [
    ...
    "networkx>=3.4",
]
```

NetworkX 3.6.1 is BSD-3-Clause, requires Python `>=3.11` (this project pins
3.12+), and has **no required runtime dependencies** — `numpy`, `scipy`,
`matplotlib` and `pandas` are all behind its `default` extra, and `dev`
already carries all four. Adding it costs the wheel nothing and Colab nothing.

For Options A and G the adapter goes in `tests/networkx_parity/` beside the
test modules. If Option C is ever taken, its engine belongs in `tests/` or
`src/demos/` — not in `flight_planner/pathfinding/`, which is now six modules
that all import from `strategy.py` and nothing outside the package.

---

## 6. Risks and how to avoid them

| Risk | Avoidance |
| --- | --- |
| Comparing a collapsed graph and thinking parity is proven | Always `MultiDiGraph`; assert `G.number_of_edges() == len(planner.edges)` — a `DiGraph` discards 29,615 of 66,332 routes |
| Tie-breaking differences read as bugs | Assert on total cost; treat identical paths as a secondary, non-blocking check |
| A\* heuristic signature mismatch | NetworkX passes node keys, `flight_planner` passes vertices — bridge with `planner.iata_lookup` |
| Float comparison noise | `pytest.approx` / `math.isclose` with an explicit tolerance; observed agreement is exact to 1e-9 relative |
| Runtime blowing up the suite | Sample by default, exhaustive behind a marker — the full sweep is 16.87 s against a 42.78 s baseline |
| An unregistered `slow` marker silently doing nothing | `pyproject.toml` has no `markers` key and `--strict-markers` is unset, so a typo'd mark is a warning, not a failure — register it |
| The oracle itself drifting | Pin a floor in `dev`, record the NetworkX version in any `results.json` |
| Validation quietly becoming the implementation | Keep NetworkX out of `flight_planner/`; the hand-written algorithms are the deliverable |
| Comparing counters across algorithms | `nodes_expanded` excludes the goal, and `BFS` derives it differently from `Dijkstra`/`AStar` (§1) — compare A\* against Dijkstra, and each against its own history |
| Patching A\* and forgetting the counter | `nodes_expanded` is `len(visited)`; dropping the closed set silently zeroes it unless an explicit counter replaces it (Option E) |

---

## Appendix A — How these were run

There are **two measurement passes**, and the table below says which figures
came from which. Both used `uv run --with networkx ...`, which resolves
NetworkX 3.6.1 without touching `pyproject.toml`:

```
uv run --with networkx python <script>.py
PYTHONPATH=src uv run --with networkx pytest -q <test module>
```

**Pass 1 — `fd475e1`, 2026-09-12.** Run in this worktree, before the min-heap
and before the `pathfinding/` split. Baseline `uv run pytest -q` →
**311 passed in 27.28s**.

**Pass 2 — `f40ee82` (`feature/search-instrumentation`), 2026-09-12.** That
commit is checked out in another worktree, so it was extracted read-only and
run from there:

```
git archive f40ee82 | tar -x -C /tmp/nxfull
uv run --project /tmp/nxfull pytest -q /tmp/nxfull/tests
uv run --project /tmp/nxfull --with networkx pytest -q /tmp/nxfull/tests/networkx_parity
```

Baseline at `f40ee82`: **382 passed in 42.78s**.

| Section | Pass | What was run | Key output |
| --- | --- | --- | --- |
| §2 | 1 | `MultiDiGraph` vs `DiGraph` on the global snapshot | `66332` vs `36717` edges; `ORD->ATL` carries 20 |
| A | 1 | 4-test parity module on `shortest-vs-fewest` | `4 passed in 16.85s`, 8,742 pairs, 0 disagreements |
| A | **2** | the same module, unchanged, on current code | `4 passed in 16.87s`; three tutorial pairs identical in cost *and* path |
| C | 1 | `NetworkXDijkstra` through `find_shortest_route` | 8,742 pairs, 0 cost mismatches, 8,742 identical flight-number sequences |
| D | 1 | structure + `all_shortest_paths` | `components: 42`, `one-way-only: 33`; 4341.022 / 3531.417 / 8076.038 |
| E | 1 | 150 parametrized random-graph tests | `7 failed, 143 passed`; all failures A\* |
| E | 1 | consistency of the haversine heuristic | `658470` checks, `0` violations |
| E | **2** | four-vertex repro against post-split `AStar` | cost 3.0, path legs sum 2.5, expanded 3 |
| E | **2** | shipped vs `ReopeningAStar` vs NetworkX, 50 graphs | 10,866 queries; 43 suboptimal / 35 cost≠path shipped, **0** reopening; +0.58 % expansions |
| E | **2** | both A\* variants on `search-cost`'s five pairs | expansions and distances identical; 8.29 / 0.28 / 0.26 ms per query |
| F | 1 | 25 random pairs on the global snapshot | Dijkstra 0.31 s / 0.36 s; A\* 0.08 s / 0.06 s |
| F | **2** | 25 random pairs, re-seeded, on current code | Dijkstra 0.42 s / 0.25 s; A\* 0.08 s / 0.04 s; worst delta 0.00e+00 km |
| G | **2** | 2-test counter-parity module, 500 pairs | `2 passed in 1.98s`; Dijkstra 23,346 expansions vs A\* 1,302 |

Where a figure exists in both passes, the Pass 2 number is the one quoted in
the body. Anything still marked Pass 1 only — Options C and D, and the
consistency sweep — was not re-run; nothing in the refactor should move it,
but that is an expectation rather than a measurement.

The scripts live outside the repository. Options A, E and G are what turning
them into committed code looks like, and their modules are reproduced in full
above precisely so that the scripts are not the only copy.

## See also

- [Experiments](experiments.md) — snapshots, the `Catalog` vocabulary, and the
  experiment model this document builds on.
- [Tutorial](tutorial.md) — builds `experiments/shortest-vs-fewest`, whose
  finding Option D re-derives.
- [Graph Algorithm Notes](graph-algorithms-notes.md) — Dijkstra, BFS and A\*.
- [Final report](report.md) — §5 *Correctness Testing* is the section Option
  B's recorded result is written for; §6 and §7 consume its counters and
  timings.
- [Package design](../src/flight_planner/README.md) — where a new algorithm
  strategy hooks in, which is the seam Option C uses, and the layering table
  naming `SearchResult` and `SearchObserver`.
