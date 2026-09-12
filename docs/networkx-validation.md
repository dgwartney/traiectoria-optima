# Validating `flight_planner` against NetworkX

`flight_planner` implements its own `Graph`, `Vertex`, `Edge`, `MinHeap`, and
three pathfinding strategies. That is the point of the project — the
algorithms are the deliverable, not a means to an end. But hand-written
Dijkstra, BFS and A\* need an answer to "how do we know these are right?", and
today the answer is 311 tests, most of them against four-vertex graphs built
by hand, plus two committed experiments that pin real numbers
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
> which is weaker than the condition its docstring states. On the project's
> own data the heuristic is consistent (verified below), so no committed
> result is wrong. See [§3, Option E](#option-e--randomized-differential-testing).

---

## 1. What is already there to build on

The existing machinery does most of the work. Nothing below needs new
infrastructure:

| Piece | Where | What it gives a validation effort |
| --- | --- | --- |
| `Snapshot` | `flight_planner/experiments/snapshot.py` | Checksummed, immutable input — a parity run and a re-run months later provably read the same bytes |
| `Catalog` | `flight_planner/experiments/catalog.py` | A vocabulary for choosing the scope to validate on, and a `summary()` recording how it was derived |
| `Experiment` | `flight_planner/experiments/experiment.py` | A directory pinning a snapshot, declared parameters, and `record()` writing `results.json` next to the data's identity |
| `PathfindingAlgorithm` | `flight_planner/pathfinding/algorithms.py` | A Strategy interface — anything with `find_path(graph, start, goal)` is a drop-in engine |
| `Graph.get_outgoing_edges` | `flight_planner/core/graph.py` | The *only* traversal method the algorithms use, so an adapter has exactly one surface to cover |
| `tests/experiments/test_committed.py` | tests | The precedent for "the committed artifacts must keep producing the committed answers" |
| `make experiment SLUG=...` | `Makefile:275` | Scaffolds an experiment directory that runs end to end as written |

Two committed experiments are the natural subjects:

- **`experiments/sfo-bos-dijkstra`** — the whole world, narrowed in the
  notebook: 66,332 routes / 3,387 airports frozen, narrowed to 861 / 88.
- **`experiments/shortest-vs-fewest`** — the tutorial's experiment, narrowed at
  freeze time to US large airports: 7,005 routes / 94 airports. Its finding is
  that BFS returns *a* minimum-hop route, not the shortest one among them.

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
run:

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
7.85s call     test_dijkstra_agrees_with_networkx_on_every_pair
4.50s call     test_bfs_hop_counts_agree_with_unweighted_networkx
0.36s call     test_dijkstra_returns_a_path_whose_legs_sum_to_its_cost
4 passed in 16.85s
```

Zero disagreements. Both engines also agree on the path itself, edge for edge,
on the tutorial's three pairs:

```
SFO-BOS: fp=4341.022085 nx=4341.022085  SFO->BOS
BOI-CHS: fp=3376.003135 nx=3376.003135  BOI->DEN->BNA->CHS
HNL-BDL: fp=8071.513691 nx=8071.513691  HNL->SLC->DTW->BDL
```

**Cost.** ~90 lines. 16.85 s added to a suite that currently runs in 27.28 s —
a 60 % increase, so sample pairs by default (a seeded random subset) and gate
the exhaustive sweep behind `pytest -m slow`.

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

**Cost.** One experiment directory. No new infrastructure.

**Caveats.** Adds a NetworkX version to the reproducibility surface. Put it in
`[parameters]` so the result states its own oracle.

**Verdict.** Cheap, and it fits the project's existing model exactly.

---

### Option C — NetworkX behind the `PathfindingAlgorithm` interface

**What it is.** An adapter implementing the existing Strategy, so the engine
becomes a *parameter* of an experiment exactly as `Dijkstra()` vs `BFS()`
already is in `shortest-vs-fewest`. Written and run:

```python
class NetworkXDijkstra(PathfindingAlgorithm):
    """Reference engine: NetworkX does the search, we return our own types.

    The graph is built once and cached, so the planner must not be mutated
    afterwards. NetworkX returns a node path, not edges, so each hop is mapped
    back to the cheapest parallel Route between those two airports -- which
    reproduces the cost exactly, but not necessarily the same flight number
    when several legs tie.
    """

    def __init__(self) -> None:
        self._graph = None
        self._planner = None

    def find_path(self, graph, start, goal):
        if graph is not self._planner:
            self._planner = graph
            self._graph = to_networkx(graph)

        if start == goal:
            return 0.0, []
        try:
            nodes = nx.shortest_path(self._graph, start.key, goal.key, weight="weight")
        except nx.NetworkXNoPath:
            return float("inf"), []

        legs = []
        for origin, destination in zip(nodes, nodes[1:]):
            candidates = [
                edge
                for edge in graph.get_outgoing_edges(graph.find_airport(origin))
                if edge.target.key == destination
            ]
            legs.append(min(candidates, key=lambda edge: edge.weight))
        return sum(leg.weight for leg in legs), legs
```

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
result can be expressed as `(float, List[Route])`, that `(inf, [])` and
`(0.0, [])` mean the same in both, and that downstream code (leg counting,
flight numbers, `results.json` shape) is engine-agnostic.

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

**What it found.** Dijkstra and BFS pass all 50 seeds clean. A\* does not:

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
cause is at `pathfinding/algorithms.py:189`: a vertex is added to `visited` on
pop and skipped forever after, so when a later, cheaper route to `A` is found,
`predecessors` is updated but the improved cost never propagates to `G`.

Removing the closed set — skipping stale queue entries by g-score instead,
which is the standard formulation — fixes every case:

```
ReopeningAStar: 2.5 via S->B->A->G legs sum 2.5
shipped AStar : 3.0 legs sum 2.5 <- returned cost and returned path disagree

suboptimal results -- shipped AStar: 42, reopening AStar: 0
of the shipped failures, cost disagrees with its own returned path: 33
```

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

**Cost.** ~90 lines, 1.1 s. **Verdict.** The strongest bug-finder of the five.

---

### Option F — Benchmarking, with honest framing

On 25 random reachable pairs from the global snapshot's largest strongly
connected component (3,318 airports, 66,332 routes), all 25 in agreement for
both Dijkstra and A\*:

| engine | total |
| --- | --- |
| `flight_planner` Dijkstra | 0.31 s |
| NetworkX Dijkstra | 0.36 s |
| `flight_planner` A\* (memoized haversine) | 0.08 s |
| NetworkX A\* (same heuristic) | 0.06 s |

**The honest caveat.** These are not comparable systems: NetworkX walks
dict-of-dicts with string keys; `flight_planner` walks objects and allocates
`Route` lists. Graph construction (0.11 s for the whole world) sits outside the
loop. The useful conclusion is the modest one — *`flight_planner` is in the
same performance class as a mature library, and A\* is roughly 4× faster than
Dijkstra on this data* — not a leaderboard.

**Verdict.** A supporting table inside Option B's experiment. Do not build a
benchmark suite around it.

---

## 4. Recommendation

1. **Option A** — oracle tests, sampled by default, exhaustive under a marker.
   *~90 lines.*
2. **Option E** — randomized differential testing, and a decision on the A\*
   docstring-vs-implementation gap it surfaced. *~90 lines, 1.1 s.*
3. **Option D** — structural checks, plus the `all_shortest_paths` rewrite of
   the tutorial's two-leg comprehension. *Mostly documentation work.*
4. **Option B** — `experiments/networkx-parity`, folding in Option F's timing
   table. *No new infrastructure.*
5. **Option C** — the Strategy adapter, only if the goal grows to "run any
   experiment on either engine".

Steps 1–3 are a day's work and would take algorithm correctness from
"four-vertex fixtures plus two pinned results" to "agrees with an independent
implementation on 8,742 real pairs and on 150 randomized graphs".

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

If Option C is ever taken, the adapter belongs in `tests/` or `src/demos/` —
not in `flight_planner/pathfinding/` — for the same reason.

---

## 6. Risks and how to avoid them

| Risk | Avoidance |
| --- | --- |
| Comparing a collapsed graph and thinking parity is proven | Always `MultiDiGraph`; assert `G.number_of_edges() == len(planner.edges)` — a `DiGraph` discards 29,615 of 66,332 routes |
| Tie-breaking differences read as bugs | Assert on total cost; treat identical paths as a secondary, non-blocking check |
| A\* heuristic signature mismatch | NetworkX passes node keys, `flight_planner` passes vertices — bridge with `planner.iata_lookup` |
| Float comparison noise | `pytest.approx` / `math.isclose` with an explicit tolerance; observed agreement is exact to 1e-9 relative |
| Runtime blowing up the suite | Sample by default, exhaustive behind a marker — the full sweep is 16.85 s against a 27.28 s baseline |
| The oracle itself drifting | Pin a floor in `dev`, record the NetworkX version in any `results.json` |
| Validation quietly becoming the implementation | Keep NetworkX out of `flight_planner/`; the hand-written algorithms are the deliverable |

---

## Appendix A — How these were run

Every figure and every output above came from scripts run against this
worktree on 2026-09-12 with `uv run --with networkx ...`, which resolves
NetworkX 3.6.1 without touching `pyproject.toml`:

```
uv run --with networkx python <script>.py
PYTHONPATH=src uv run --with networkx pytest -q <test module>
```

Baseline for the timing claims: `uv run pytest -q` → **311 passed in 27.28s**.

| Section | What was run | Key output |
| --- | --- | --- |
| §2 | `MultiDiGraph` vs `DiGraph` on the global snapshot | `66332` vs `36717` edges; `ORD->ATL` carries 20 |
| A | 4-test parity module on `shortest-vs-fewest` | `4 passed in 16.85s`, 8,742 pairs, 0 disagreements |
| C | `NetworkXDijkstra` through `find_shortest_route` | 8,742 pairs, 0 cost mismatches, 8,742 identical flight-number sequences |
| D | structure + `all_shortest_paths` | `components: 42`, `one-way-only: 33`; 4341.022 / 3531.417 / 8076.038 |
| E | 150 parametrized random-graph tests | `7 failed, 143 passed`; all failures A\*; 42 suboptimal results, 0 after the fix |
| E | consistency of the haversine heuristic | `658470` checks, `0` violations |
| F | 25 random pairs on the global snapshot | Dijkstra 0.31 s / 0.36 s; A\* 0.08 s / 0.06 s |

The scripts live outside the repository — they were written to establish these
numbers, and Options A, B, C and E are what turning them into committed code
looks like.

## See also

- [Experiments](experiments.md) — snapshots, the `Catalog` vocabulary, and the
  experiment model this document builds on.
- [Tutorial](tutorial.md) — builds `experiments/shortest-vs-fewest`, whose
  finding Option D re-derives.
- [Graph Algorithm Notes](graph-algorithms-notes.md) — Dijkstra, BFS and A\*.
- [Package design](../src/flight_planner/README.md) — where a new algorithm
  strategy hooks in, which is the seam Option C uses.
