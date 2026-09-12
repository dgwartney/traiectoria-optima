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

This document lays out seven options, from a single oracle class to a second
engine behind the existing Strategy interface. **Every code block below was
run against this repository's committed snapshots, and every output shown is
the output it produced** — nothing here is a sketch, and three of the options
are reproduced as the complete, class-based modules they should be committed
as. The commands are in [Appendix A](#appendix-a--how-these-were-run).

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

> **And a second thing, on the first run of Option G.** `peak_frontier`
> exceeds the number of vertices — Dijkstra on 375 of 500 real queries, up to
> 1.85 V for A\*. The O(V) space figure in `result.py`'s docstring and on
> `slides/index.html:348-349` is what a heap *with* decrease-key would give;
> `MinHeap` has no reposition, so the frontier carries superseded entries and
> its bound is O(E). Nothing is broken — but the complexity write-up currently
> claims the wrong number. See
> [§3, Option G](#it-found-a-second-thing-the-space-bound-in-the-write-up-is-wrong).

> **Which code this describes.** Everything here was re-run against
> `f40ee82` (`feature/search-instrumentation`), which is a linear superset of
> `main` and carries the from-scratch `MinHeap`, the one-module-per-algorithm
> split of `pathfinding/`, and the `SearchResult` / `SearchObserver`
> instrumentation. The first pass was written against `fd475e1`, before any of
> that; every figure has been re-measured rather than carried over. See
> [§1, What the refactor changed](#what-the-refactor-changed) and
> [Appendix A](#appendix-a--how-these-were-run).
>
> This document was drafted on `worktree-NetworkX` off `fd475e1` and has since
> been rebased onto `feature/search-instrumentation`, so the files it names
> under `pathfinding/` are present.

> **Status: Options B, C and E are built.** They are no longer proposals. The
> code lives in [`src/validation/`](../src/validation) — five classes,
> 256 unit tests — and the two experiments are recorded:
>
> | Option | Where it landed | Write-up |
> |---|---|---|
> | **C** — NetworkX behind the Strategy | `src/validation/engines.py` | used by both experiments below |
> | **B** — a parity experiment | [`experiments/networkx-parity`](../experiments/networkx-parity) | [results-networkx-parity.md](results-networkx-parity.md) |
> | **E** — randomized differential testing | [`experiments/astar-consistency`](../experiments/astar-consistency) | [results-astar-consistency.md](results-astar-consistency.md) |
>
> Options A, D, F and G remain proposals. Read the sections below for the
> reasoning and the design alternatives; read the two write-ups for what the
> built versions actually found. Where a figure differs, the experiment's
> `results.json` is authoritative — it was produced by committed code, and
> `tests/experiments/test_validation_experiments.py` re-derives it.

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

## 2. The oracle class, and the one decision that matters

**Everything here is class-based**, which is the repository's convention
rather than a preference of this document: `src/flight_planner/README.md:123`
states "one `pytest` test class per production class", and all 17 modules in
`tests/flight_planner/` follow it. So the bridge is a class, the reference
engine is a class, the random-graph generator is a class, and the parity tests
are grouped into behavior classes the way
`tests/flight_planner/experiments/` already groups its own
(`TestIntegrity`, `TestNarrowing`, ...).

Holding the bridge as a class earns its keep immediately. A bare
`to_networkx(planner)` function forces every A\* comparison to re-derive the
same awkward detail — NetworkX passes a heuristic *node keys* where
`flight_planner` passes *vertices* — so `iata_lookup` ends up copy-pasted into
each test. `NetworkXView` owns it once, and the oracle queries become methods
that read like the question being asked:

```python
"""A NetworkX view of a FlightPlanner, and the oracle queries it answers."""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import networkx as nx

from flight_planner.flights.planner import FlightPlanner
from flight_planner.geo import DistanceFormula, Haversine, Memoized


class NetworkXView:
    """The same flight network, as NetworkX sees it.

    A `MultiDiGraph`, not a `DiGraph`: the data carries up to 20 parallel
    routes between one airport pair, and a `DiGraph` would silently keep only
    the last of them.

    Holding this as a class rather than a bare conversion function puts the
    one awkward part of the bridge in a single place: NetworkX passes node
    keys to a heuristic where `flight_planner` passes vertices, so every A*
    comparison needs `iata_lookup` and none of them should re-derive it.

    Attributes:
        graph: The `nx.MultiDiGraph` mirror. Nodes are IATA codes; edges carry
            `weight` in kilometres, plus `airline`, keyed by flight number.
    """

    def __init__(
        self, planner: FlightPlanner, formula: DistanceFormula | None = None
    ) -> None:
        """Mirror a planner into NetworkX.

        Args:
            planner: Flight network to mirror. Must not be mutated afterwards;
                the mirror is built once.
            formula: Distance formula for the A* heuristic, memoized by
                default since the oracle asks for the same legs repeatedly.
        """
        self._planner = planner
        self._lookup = planner.iata_lookup
        self._formula = formula if formula is not None else Memoized(Haversine())
        self.graph = self._build(planner)

    @staticmethod
    def _build(planner: FlightPlanner) -> nx.MultiDiGraph:
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

    @property
    def order(self) -> int:
        """Return the node count."""
        return self.graph.number_of_nodes()

    @property
    def size(self) -> int:
        """Return the edge count, parallel routes included."""
        return self.graph.number_of_edges()

    def heuristic(self, origin_code: str, destination_code: str) -> float:
        """Return the great-circle distance between two IATA codes.

        The signature NetworkX's `astar_path_length` expects, over the
        coordinates `flight_planner` holds on its `Airport` vertices.

        Args:
            origin_code: IATA code of the node being scored.
            destination_code: IATA code of the goal.

        Returns:
            Great-circle distance in kilometres.
        """
        return self._lookup[origin_code].distance_to(
            self._lookup[destination_code], formula=self._formula
        )

    def dijkstra_length(self, origin: str, destination: str) -> float:
        """Return NetworkX's weighted shortest-path length, or infinity."""
        try:
            return nx.shortest_path_length(
                self.graph, origin, destination, weight="weight"
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return math.inf

    def astar_length(self, origin: str, destination: str) -> float:
        """Return NetworkX's A* length under the same heuristic, or infinity."""
        try:
            return nx.astar_path_length(
                self.graph,
                origin,
                destination,
                heuristic=self.heuristic,
                weight="weight",
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return math.inf

    def all_dijkstra_lengths(self) -> Dict[str, Dict[str, float]]:
        """Return every weighted shortest-path length, keyed origin then goal.

        One all-pairs sweep is dramatically cheaper than a query per pair.
        """
        return dict(nx.all_pairs_dijkstra_path_length(self.graph, weight="weight"))

    def all_hop_counts(self) -> Dict[str, Dict[str, int]]:
        """Return every unweighted shortest-path length — BFS's question."""
        return dict(nx.all_pairs_shortest_path_length(self.graph))

    def path(self, origin: str, destination: str) -> List[str]:
        """Return the node sequence of a weighted shortest path."""
        return nx.shortest_path(self.graph, origin, destination, weight="weight")

    def ordered_pairs(self) -> List[Tuple[str, str]]:
        """Return every ordered pair of distinct airports, sorted."""
        codes = sorted(airport.iata_code for airport in self._planner.vertices)
        return [(o, d) for o in codes for d in codes if o != d]
```

**Yes, NetworkX implements A\*** — `nx.astar_path` and
`nx.astar_path_length`, in `networkx.algorithms.shortest_paths.astar`. That
matters more than it first appears, and [Option E](#option-e--randomized-differential-testing)
depends on it: NetworkX's A\* *reopens* nodes. Its loop does not skip a
closed vertex outright but compares the queued cost first —

```python
        if curnode in explored:
            ...
            qcost, h = enqueued[curnode]
            if qcost < dist:
                continue
```

— and falls through to re-expand when a better route turned up. So it stays
optimal for any admissible heuristic, which is exactly what `flight_planner`'s
`AStar` does not do. Measured, not read off the source: 0 suboptimal results
across 10,866 queries under a deliberately inconsistent heuristic. It is
therefore a legitimate oracle for that case, and the patch in Option E is not
an invention — it is the formulation the oracle already uses. Note also
`enqueued[v] = (cost, h)`, the bookkeeping that lets NetworkX recognise a
stale entry; `MinHeap.pop()` returns no priority, so the patch reaches the
same end by a different route.

**`MultiDiGraph` is not a style preference.** Choosing `DiGraph` would make
every parity test below pass while comparing a graph nobody built:

```python
planner = Snapshot.open("data/snapshots/2026-09-11-bb90a8").catalog().planner()

multi = NetworkXView(planner).graph
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

**What it is.** `NetworkXView` above plus one test module. This is the
module, as run.

**Where the files go.** `tests/networkx_parity/` — `nx_oracle.py` beside
`test_parity.py`. The bare `from nx_oracle import NetworkXView` works because
no directory under `tests/` has an `__init__.py`, so pytest's default
`prepend` import mode puts each test file's own directory on `sys.path`;
adding `tests` to `pythonpath` in `pyproject.toml` is not needed and was not
done. The oracle stays out of `src/flight_planner/`: the wheel imports pandas
and nothing else, and NetworkX is a `dev` concern (§5).

`test_parity.py` holds this option's three classes and
[Option G](#option-g--counter-parity-validating-the-claim-itself)'s two, since
they share fixtures. Module-scoped fixtures matter here — building the planner
and the mirror once takes 0.06 s, and per-test would multiply that by eight.

```python
"""NetworkX as an oracle: our answers must be NetworkX's answers.

Organized by behavior rather than by production class, following
`tests/flight_planner/experiments/`: what matters here is which claim is being
checked, not which class does the checking.
"""

import math

import pytest

from flight_planner import AStar, BFS, Dijkstra
from flight_planner.experiments import Experiment
from flight_planner.geo import Haversine, Memoized

from nx_oracle import NetworkXView

SAMPLE = 500


@pytest.fixture(scope="module")
def planner(repo_root):
    return (
        Experiment.open(repo_root / "experiments" / "shortest-vs-fewest")
        .catalog()
        .planner()
    )


@pytest.fixture(scope="module")
def oracle(planner):
    return NetworkXView(planner)


@pytest.fixture(scope="module")
def pairs(oracle):
    return oracle.ordered_pairs()


@pytest.fixture(scope="module")
def heuristic():
    formula = Memoized(Haversine())
    return lambda origin, goal: origin.distance_to(goal, formula=formula)


class TestTheTwoGraphsAreTheSameGraph:
    """Parity means nothing if the graphs being compared differ."""

    def test_every_airport_and_every_route_survives_the_mirror(self, planner, oracle):
        # A DiGraph would pass every parity test below while comparing a graph
        # we never built: 7005 routes span only 3060 airport pairs.
        assert oracle.order == len(planner.vertices)
        assert oracle.size == len(planner.edges)


class TestDijkstraAgreesWithNetworkX:
    """Weighted shortest distance, on every ordered pair."""

    @pytest.mark.slow
    def test_costs_agree_on_every_pair(self, planner, oracle, pairs):
        reference = oracle.all_dijkstra_lengths()

        disagreements = []
        for origin, destination in pairs:
            ours, _ = planner.find_shortest_route(origin, destination, Dijkstra())
            theirs = reference[origin].get(destination, math.inf)
            if not (math.isinf(ours) and math.isinf(theirs)) and not math.isclose(
                ours, theirs, rel_tol=1e-9
            ):
                disagreements.append((origin, destination, ours, theirs))

        assert disagreements == []

    def test_the_returned_path_is_the_route_we_charged_for(
        self, planner, oracle, pairs
    ):
        # Cost parity is the durable contract; with up to 20 parallel edges the
        # two libraries may legitimately pick different equal-cost paths. What
        # must hold is that our path is really the route we billed.
        for origin, destination in pairs[:200]:
            cost, legs = planner.find_shortest_route(origin, destination, Dijkstra())
            assert sum(leg.distance_km for leg in legs) == pytest.approx(cost)
            assert oracle.dijkstra_length(origin, destination) == pytest.approx(cost)


class TestBFSAgreesWithNetworkX:
    """Hop counts, against NetworkX run unweighted."""

    @pytest.mark.slow
    def test_hop_counts_agree_on_every_pair(self, planner, oracle, pairs):
        reference = oracle.all_hop_counts()

        disagreements = []
        for origin, destination in pairs:
            hops, _ = planner.find_shortest_route(origin, destination, BFS())
            theirs = reference[origin].get(destination, math.inf)
            if hops != float(theirs):
                disagreements.append((origin, destination, hops, theirs))

        assert disagreements == []
```

**What it produced.** Every one of the 8,742 ordered pairs on the tutorial
snapshot, for both algorithms. Eight tests, because Option G's two classes
share the module:

```
........                                                                 [100%]
============================= slowest 6 durations ==============================
9.60s call  TestDijkstraAgreesWithNetworkX::test_costs_agree_on_every_pair
4.76s call  TestBFSAgreesWithNetworkX::test_hop_counts_agree_on_every_pair
1.04s call  TestAStarAgreesWithNetworkX::test_astar_and_dijkstra_agree_with_the_oracle_and_each_other
0.90s call  TestTheCentralClaimAtScale::test_the_weighted_frontier_is_bounded_by_edges_not_vertices
0.63s call  TestTheCentralClaimAtScale::test_astar_never_expands_more_than_dijkstra
0.41s call  TestDijkstraAgreesWithNetworkX::test_the_returned_path_is_the_route_we_charged_for
8 passed in 18.73s
```

Zero disagreements. Both engines also agree on the path itself, edge for edge,
on the tutorial's three pairs:

```
SFO-BOS: fp=4341.022085 nx=4341.022085  SFO->BOS
BOI-CHS: fp=3376.003135 nx=3376.003135  BOI->DEN->BNA->CHS
HNL-BDL: fp=8071.513691 nx=8071.513691  HNL->SLC->DTW->BDL
```

Those three are unchanged from the first pass, min-heap and all — matching
NetworkX edge for edge, not merely in cost.

**Cost.** ~150 lines across the two files. 18.73 s added to a suite that now
runs in 42.78 s over 382 tests, so sample pairs by default and gate the two
exhaustive all-pairs sweeps behind a marker:

```toml
[tool.pytest.ini_options]
markers = ["slow: exhaustive sweeps, excluded from the default run"]
addopts = "-m 'not slow'"
```

There is no `markers` key in `pyproject.toml` today, and `--strict-markers` is
not set, so the `@pytest.mark.slow` above is currently only a warning:

```
PytestUnknownMarkWarning: Unknown pytest.mark.slow - is this a typo?
```

That warning is real output from the run above. Register the marker in the
same change, or the gating silently does nothing.

**Caveats.** Compare *costs* first and paths second: with up to 20 parallel
edges, ties are common and the two libraries may break them differently.
Asserting on equal total cost is the durable contract.

**Verdict.** Highest value per line of code. Do this first.

---

### Option B — A parity *experiment*, recorded like any other result

> **Built.** [`experiments/networkx-parity`](../experiments/networkx-parity),
> written up in [results-networkx-parity.md](results-networkx-parity.md). The
> recorded payload below is close to what shipped; the built version also
> records the `DiGraph` collapse figure and an oracle version.

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

> **Built**, as three engines rather than one:
> `NetworkXDijkstra`, `NetworkXBFS` and `NetworkXAStar` in
> [`src/validation/engines.py`](../src/validation/engines.py), over a generic
> `NetworkXMirror` so they are testable on a four-vertex fixture. The sketch
> below is superseded by that code.

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
        self._view = None
        self._planner = None

    def search(self, graph, start, goal, observer=None):
        if graph is not self._planner:
            self._planner = graph
            self._view = NetworkXView(graph)

        if start == goal:
            return SearchResult(0.0, [])
        try:
            nodes = self._view.path(start.key, goal.key)
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
world = NetworkXView(
    Snapshot.open("data/snapshots/2026-09-11-bb90a8").catalog().planner()
).graph

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

> **Built.** [`experiments/astar-consistency`](../experiments/astar-consistency),
> written up in [results-astar-consistency.md](results-astar-consistency.md).
> `RandomGraphPair` and `InconsistentHeuristic` are in
> [`src/validation/random_graphs.py`](../src/validation/random_graphs.py) and
> the patch is `ReopeningAStar`. Final counts: **27 suboptimal / 25
> self-contradictory of 10,866 queries**, 0 after the patch, +0.52%
> expansions.

**What it is.** Random small graphs, both engines on every pair, assert equal
costs. No project data involved — this reaches the cases flight data never
produces: dense graphs, disconnected graphs, zero weights, ties, and
heuristics that are admissible without being consistent.

Three classes, in `tests/networkx_parity/`. `RandomGraphPair` builds one graph
twice, once for each library, so no test ever has to keep the two in step:

```python
class RandomGraphPair:
    """The same random weighted digraph, built for both libraries.

    Attributes:
        ours: The `flight_planner` `Graph`.
        theirs: The equivalent `nx.DiGraph`.
        vertices: Our vertices, in creation order.
    """

    def __init__(self, seed: int) -> None:
        """Build one graph pair from a seed.

        Args:
            seed: Anything hashable by `random.Random`. The same seed always
                produces the same pair, so a failure is reproducible from the
                parametrized test id alone.
        """
        rng = random.Random(seed)
        order = rng.randint(2, 25)
        size = rng.randint(0, order * 3)

        self.ours, self.theirs = Graph(), nx.DiGraph()
        self.vertices = [Vertex(f"n{index}") for index in range(order)]
        for vertex in self.vertices:
            self.ours.add_vertex(vertex)
            self.theirs.add_node(vertex.key)

        for _ in range(size):
            source, target = rng.choice(self.vertices), rng.choice(self.vertices)
            # Ties and zero weights on purpose; negative weights are outside
            # Dijkstra's contract, so not generated.
            weight = rng.choice([0.0, 1.0, 1.0, 2.5, rng.random() * 10])
            self.ours.add_edge(Edge(source, target, weight=weight))
            if self.theirs.has_edge(source.key, target.key):
                # A DiGraph keeps one edge per pair; keep the cheapest so the
                # oracle answers the question our multigraph answers.
                weight = min(weight, self.theirs[source.key][target.key]["weight"])
            self.theirs.add_edge(source.key, target.key, weight=weight)
```

It also carries the oracle queries (`distance`, `hops`, `remaining_costs`,
`ordered_pairs`), each wrapping the `NetworkXNoPath` that a disconnected
random graph produces constantly.

**The heuristic has to be a class, and the first draft got this wrong.** The
first pass built it as a closure calling `rng.random()` *inside* the function:

```python
        def heuristic(vertex, _goal, remaining=remaining, rng=rng):
            return remaining.get(vertex.key, 0.0) * rng.random()   # WRONG
```

That returns a different estimate every time it is asked about the same
vertex, which makes it not a heuristic at all — not a function of the vertex,
and not reproducible. It inflated the failure count and would have made any
committed test flaky. Scoring every vertex once, at construction, is the fix:

```python
class InconsistentHeuristic:
    """Admissible by construction, deliberately not consistent.

    `h(v)` is a random fraction of the true remaining distance to the goal, so
    it never overestimates — but it violates the triangle inequality that a
    closed-set A* implicitly relies on.
    """

    def __init__(self, pair: RandomGraphPair, goal: Vertex, seed: int) -> None:
        """Score every vertex once, so the heuristic is a fixed function.

        Args:
            pair: The graph pair to take true distances from.
            goal: The goal these estimates are relative to.
            seed: Seed for the fractions, kept distinct from the graph's.
        """
        rng = random.Random(seed)
        remaining = pair.remaining_costs(goal)
        self._scores = {
            vertex.key: remaining.get(vertex.key, 0.0) * rng.random()
            for vertex in pair.vertices
        }

    def __call__(self, vertex: Vertex, _goal: Vertex) -> float:
        """Return the estimate for `vertex`."""
        return self._scores[vertex.key]
```

The tests then read as three claims:

```python
SEEDS = range(50)


class TestDijkstraAndBFSOnRandomGraphs:
    """The uninformed pair, which have no heuristic to get wrong."""

    @pytest.mark.parametrize("seed", SEEDS)
    def test_dijkstra_matches_networkx_on_every_pair(self, seed):
        pair = RandomGraphPair(seed)
        for start, goal in pair.ordered_pairs():
            cost, _ = Dijkstra().find_path(pair.ours, start, goal)
            theirs = pair.distance(start, goal)
            assert cost == pytest.approx(theirs) or (
                math.isinf(cost) and math.isinf(theirs)
            ), f"seed={seed} {start.key}->{goal.key}"

    @pytest.mark.parametrize("seed", SEEDS)
    def test_bfs_matches_unweighted_networkx_on_every_pair(self, seed):
        pair = RandomGraphPair(seed)
        for start, goal in pair.ordered_pairs():
            hops, _ = BFS().find_path(pair.ours, start, goal)
            assert hops == pair.hops(start, goal), f"seed={seed} {start.key}->{goal.key}"


class TestAStarUnderAnInconsistentHeuristic:
    """The shipped `AStar` is suboptimal here; `ReopeningAStar` is not."""

    @pytest.mark.parametrize("seed", SEEDS)
    def test_the_reopening_variant_stays_optimal(self, seed):
        pair = RandomGraphPair(seed)
        for goal in pair.vertices:
            heuristic = InconsistentHeuristic(pair, goal, seed ^ 0xA5)
            for start in pair.vertices:
                if start == goal:
                    continue
                optimal = pair.distance(start, goal)
                result = ReopeningAStar(heuristic).search(pair.ours, start, goal)
                assert result.cost == pytest.approx(optimal) or (
                    math.isinf(result.cost) and math.isinf(optimal)
                ), f"seed={seed} {start.key}->{goal.key}"

    @pytest.mark.parametrize("seed", SEEDS)
    def test_a_returned_cost_always_describes_the_returned_path(self, seed):
        # The failure mode that is hardest to defend in a report: a cost that
        # does not add up to the itinerary printed beside it.
        ...


class TestTheShippedAStarIsOnlyCorrectForConsistentHeuristics:
    """Pins the defect, so the patch has something to flip."""

    def test_four_vertices_are_enough_to_break_it(self):
        start, a, b, goal = (Vertex("S"), Vertex("A"), Vertex("B"), Vertex("G"))
        graph = Graph()
        for edge in (
            Edge(start, a, 2.0),
            Edge(start, b, 1.0),
            Edge(b, a, 0.5),
            Edge(a, goal, 1.0),
        ):
            graph.add_edge(edge)

        # True remaining cost to G: S=2.5, B=1.5, A=1.0, G=0. This never
        # overestimates, so it is admissible. It is not consistent: h(S)=0 but
        # h(B)=1.5 across an edge of weight 1.0.
        admissible = {"S": 0.0, "B": 1.5, "A": 0.0, "G": 0.0}
        heuristic = lambda vertex, _goal: admissible[vertex.key]  # noqa: E731

        optimal = Dijkstra().search(graph, start, goal)
        shipped = AStar(heuristic).search(graph, start, goal)
        fixed = ReopeningAStar(heuristic).search(graph, start, goal)

        assert optimal.cost == pytest.approx(2.5)
        assert fixed.cost == pytest.approx(2.5)
        assert shipped.cost == pytest.approx(3.0)
        # And the second defect: the cost does not describe the path returned.
        assert sum(edge.weight for edge in shipped.path) == pytest.approx(2.5)
```

**What it produced.**

```
201 passed in 1.97s
```

The last class is the interesting one: it *passes* by asserting the shipped
A\* returns 3.0 where the optimum is 2.5. That is deliberate — a committed
test that pins current behavior is what turns the patch from a claim into a
one-line diff, and it fails loudly if anyone changes `astar.py` without
reading this document.

**The four vertices.** Run against the post-refactor `AStar`, so the counters
are visible too:

```
Dijkstra  cost 2.5  path S->B->A->G   legs sum 2.5  expanded 3 pushed 5 peak 2
AStar     cost 3.0  path S->B->A->G   legs sum 2.5  expanded 3 pushed 5 peak 2
```

Two distinct defects in one line of output. A\* returns **3.0** where the
optimum is 2.5, and the path it returns — `S->B->A->G` — has legs summing to
2.5, so the cost it reports does not describe the route it hands back. The
cause is `pathfinding/astar.py:84-86`: a vertex is added to `visited` on pop
and skipped forever after, so when a later, cheaper route to `A` is found,
`predecessors` is updated but the improved cost never propagates to `G`.

#### The patch

Removing the closed set — skipping stale queue entries instead, which is the
standard formulation and [the one NetworkX itself uses](#2-the-oracle-class-and-the-one-decision-that-matters)
— fixes every case. It goes in `tests/networkx_parity/reopening_astar.py`
first, as a subclass proving the point, and moves into
`pathfinding/astar.py` when the patch is accepted. Two details are forced by
the code as it now stands, and both are recorded in its docstring:

- **`MinHeap.pop()` returns the item without its priority**, so a stale entry
  cannot be recognised the usual way, by comparing the popped `f` against
  `g + h`. (NetworkX can: it keeps `enqueued[v] = (cost, h)` alongside its
  heap.) Comparing `g` against the g-score the vertex carried at its last
  expansion does the same job, and also permits a *genuine* re-expansion,
  which is the whole point.
- **`nodes_expanded` is `len(visited)`** (`astar.py:103`). Dropping the closed
  set deletes the set the counter counts, so the patch has to carry an
  explicit counter — exactly as `bfs.py` already does.

```python
        g_score: Dict[V, float] = {start: 0.0}
        predecessors: Dict[V, E] = {}
        expanded_at: Dict[V, float] = {}
        expanded = 0

        while open_set:
            current = open_set.pop()

            if current == goal:
                break
            # A pop whose g is no better than the one this vertex carried when
            # it was last expanded is a superseded queue entry. A pop whose g
            # *is* better is the case the closed set silently discarded.
            if g_score[current] >= expanded_at.get(current, math.inf):
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

The rest of `search` is unchanged. Both variants against NetworkX over the 50
random graphs — every ordered pair, every vertex as goal, under the fixed
inconsistent heuristic:

```
queries                      : 10866
shipped AStar suboptimal     : 27
  of those, cost != path sum : 25
ReopeningAStar suboptimal    : 0
nodes_expanded, shipped      : 40580
nodes_expanded, reopening    : 40792
first failure                : (6, 'n3', 'n12', 7.76407066564499, 7.0)
```

Correctness costs **0.52 % more expansions** across the whole sweep, and only
where the heuristic is inconsistent — the re-expansions are the fix doing its
job.

#### The fix does not move the committed comparison table

That was the open question the refactor created, since `experiments/search-cost`
publishes A\*'s expansion counts and `tests/experiments/test_committed.py`
pins every one of them. Both engines on the experiment's five long-haul pairs,
against the world snapshot with the real haversine heuristic:

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
plot, `results.json` and the tests that pin them all stand as committed.

One existing test deserves a note: `test_observers.py` asserts
`test_no_vertex_is_expanded_twice` for all three algorithms. The patch keeps
it green — its corridor heuristic is consistent — but that test does encode
"no re-expansion" as a requirement, so it needs a comment saying *why* it
holds, or it will look like the patch violated it.

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

**Recommendation, now that the cost is measured.** Take the patch. It is a
dozen lines, it costs 0.52 % more expansions only where the heuristic is
inconsistent, it moves no committed number, and it removes a state where the
returned cost contradicts the returned path — which is far harder to explain
in a report than a re-expansion is. If the patch is *not* taken, all three
places `astar.py` says *admissible* — lines 25, 35 and 61 — must say
*consistent* instead, and the report's admissibility argument has to make the
stronger claim, which the project's own heuristic does satisfy.

**Cost.** ~200 lines for the harness and the variant, 1.97 s; ~12 lines for
the patch itself.

**Note on the counts.** Three numbers have been reported for this sweep, and
only the last is sound. The first pass said 42 suboptimal / 33 cost-path
disagreements; a recount at `f40ee82` with the same flawed closure said
43 / 35; the class-based harness, with the heuristic fixed at construction,
says **27 / 25**. The first two were measuring a heuristic that changed its
answer on every call. Quote 27 / 25, and commit the class.

**Verdict.** The strongest bug-finder of the seven.

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

Two classes in `test_parity.py`, on the fixtures Option A already defines:

```python
class TestAStarAgreesWithNetworkX:
    """A*, against NetworkX's own A* under the same heuristic.

    This is the half of the claim that our own Dijkstra cannot witness: it
    shares the graph, the weights and `get_outgoing_edges` with A*, so the two
    agreeing is weaker evidence than it looks.
    """

    def test_costs_agree_with_networkx_astar(self, planner, oracle, heuristic, pairs):
        disagreements = []
        for origin, destination in pairs[:SAMPLE]:
            ours = planner.search_route(origin, destination, AStar(heuristic))
            theirs = oracle.astar_length(origin, destination)
            if not (math.isinf(ours.cost) and math.isinf(theirs)) and not math.isclose(
                ours.cost, theirs, rel_tol=1e-9
            ):
                disagreements.append((origin, destination, ours.cost, theirs))

        assert disagreements == []

    def test_astar_and_dijkstra_agree_with_the_oracle_and_each_other(
        self, planner, oracle, heuristic, pairs
    ):
        for origin, destination in pairs[:SAMPLE]:
            astar = planner.search_route(origin, destination, AStar(heuristic))
            dijkstra = planner.search_route(origin, destination, Dijkstra())
            assert astar.cost == pytest.approx(dijkstra.cost)
            assert astar.cost == pytest.approx(
                oracle.dijkstra_length(origin, destination)
            )


class TestTheCentralClaimAtScale:
    """"Fewer nodes for the same answer", on real data instead of a corridor.

    `tests/flight_planner/test_observers.py` already asserts this on a
    hand-built graph, and `tests/experiments/test_committed.py` pins the five
    recorded pairs. What is added here is scale and an independent oracle.
    """

    def test_astar_never_expands_more_than_dijkstra(self, planner, heuristic, pairs):
        worse = []
        totals = {"Dijkstra": 0, "AStar": 0}
        for origin, destination in pairs[:SAMPLE]:
            dijkstra = planner.search_route(origin, destination, Dijkstra())
            astar = planner.search_route(origin, destination, AStar(heuristic))
            totals["Dijkstra"] += dijkstra.nodes_expanded
            totals["AStar"] += astar.nodes_expanded
            if astar.nodes_expanded > dijkstra.nodes_expanded:
                worse.append(
                    (origin, destination, astar.nodes_expanded, dijkstra.nodes_expanded)
                )

        print(f"\nexpansions over {SAMPLE} pairs: {totals}")
        assert worse == []

    def test_the_weighted_frontier_is_bounded_by_edges_not_vertices(
        self, planner, heuristic, pairs
    ):
        # The complexity write-up claims O(V) space. That holds for BFS, which
        # marks visited at push time, but NOT for the weighted pair: lazy
        # deletion queues a vertex again on every improving relaxation instead
        # of repositioning its entry, so the frontier is bounded by E. Measured
        # over 500 pairs on a 94-airport graph, Dijkstra peaks at 1.65 V and
        # A* at 1.85 V. This test pins the real bound.
        order, size = len(planner.vertices), len(planner.edges)
        for origin, destination in pairs[:SAMPLE]:
            for algorithm in (Dijkstra(), AStar(heuristic)):
                result = planner.search_route(origin, destination, algorithm)
                assert result.peak_frontier <= result.nodes_pushed
                assert result.nodes_pushed <= size + 1

            hops = planner.search_route(origin, destination, BFS())
            assert hops.peak_frontier <= order
```

**What it produced.**

```
expansions over 500 pairs: {'Dijkstra': 23346, 'AStar': 1302}
```

A\* never expanded more than Dijkstra on any of the 500 pairs, and expanded
**18× fewer** in total — with NetworkX's own `astar_path_length` confirming
the distances, so "same answer" is not being taken on trust from our other
algorithm.

#### It found a second thing: the space bound in the write-up is wrong

`test_the_weighted_frontier_is_bounded_by_edges_not_vertices` was written as
`assert result.peak_frontier <= len(planner.vertices)`, because that is what
`result.py`'s own docstring says the counter is for — "the measured space
cost, against the O(V) bound the complexity write-up claims", and what
`slides/index.html:348-349` tabulates as Space `O(V)` for both Dijkstra and
A\*. It failed immediately:

```
E    AssertionError: assert 155 <= 94
E     +  where 155 = SearchResult(cost=2948.5469509252566, ...,
E                    nodes_expanded=83, nodes_pushed=214, peak_frontier=155)
```

Measured across the 500 pairs:

```
V = 94  E = 7005
BFS       max peak_frontier    86  =  0.91 V  = 0.0123 E  pairs over V: 0/500
Dijkstra  max peak_frontier   155  =  1.65 V  = 0.0221 E  pairs over V: 375/500
AStar     max peak_frontier   174  =  1.85 V  = 0.0248 E  pairs over V: 28/500
```

The cause is not a bug — it is the lazy-deletion design, stated plainly in
`dijkstra.py`'s own comment: "Relaxing a vertex queues it again rather than
repositioning the entry already there". Without `decrease-key`, the frontier
holds superseded copies, so its bound is **O(E)**, not O(V). BFS is unaffected
because it marks visited at push time and so queues each vertex once.

This is worth a paragraph in the report rather than a correction buried in a
test: the O(V) space figure is what a binary heap *with* decrease-key would
give, and the project deliberately did not build one — `MinHeap` has
`push`/`pop`/`peek` and no reposition. Dijkstra exceeding V on 375 of 500
real queries is the measured price of that choice, and it is exactly the kind
of claim an empirical evaluation is supposed to contain.

**What it does and does not add.** The claim is *already* tested — this option
does not introduce it. `tests/flight_planner/test_observers.py` has
`TestTheProjectsCentralClaim`, asserting `by_astar.nodes_expanded <
by_dijkstra.nodes_expanded` on a hand-built corridor, and
`tests/experiments/test_committed.py:288-310` re-derives every recorded
expansion count and every recorded cost from `search-cost`. What Option G adds
is narrower and still worth having:

| Already covered | What Option G adds |
| --- | --- |
| One hand-built corridor graph | 500 real pairs from a committed snapshot |
| Five recorded pairs, pinned by value | Every pair checked against a live oracle, so a *new* pair cannot regress unnoticed |
| "Same answer" = agrees with our own Dijkstra | "Same answer" = agrees with NetworkX, which shares no code, no graph and no traversal method with us |
| Expansions counted by our own code | Nothing — NetworkX does not expose expansions, so this half stays self-reported |

That third row is the real gain. A\* and Dijkstra agreeing is weaker evidence
than it looks: they share `Graph`, the weights, `get_outgoing_edges` and the
same `MinHeap`. A common-mode error in any of those is invisible to a test
that compares them to each other.

**Caveat.** `nodes_expanded` means "vertices whose outgoing edges were
requested, goal excluded", and `BFS` counts it differently from the weighted
pair for a real reason (§1). Do not assert BFS's count against theirs; assert
each algorithm against its own history, and A\* against Dijkstra.

**Cost.** ~70 lines, folded into Option A's module. **Verdict.** Do this with
Option A. Same fixtures, same oracle, and it found the space-bound error on
first run.

---

## 4. Recommendation

One change, `tests/networkx_parity/`, four files and in this order. All of it
is class-based, per `src/flight_planner/README.md:123`:

| File | Holds |
| --- | --- |
| `nx_oracle.py` | `NetworkXView` — the mirror and every oracle query |
| `test_parity.py` | Options A and G: five behavior classes, eight tests |
| `reopening_astar.py` | `ReopeningAStar` — the Option E patch, as a subclass |
| `test_randomized.py` | Option E: `RandomGraphPair`, `InconsistentHeuristic`, three test classes |

1. **Option A** — `nx_oracle.py` plus `test_parity.py`, sampled by default,
   the two all-pairs sweeps exhaustive under `-m slow`. Register the marker in
   the same commit or the gating is a no-op. *~150 lines, 18.73 s.*
2. **Option G** — counter parity, two more classes in `test_parity.py` on the
   same fixtures. Already paid for by step 1, and it is what caught the
   space-bound error. *~70 lines.*
3. **Option E** — the randomized harness, **and take the patch**: drop A\*'s
   closed set, add the explicit expansion counter, and keep the four-vertex
   graph as a named regression test. *~200 lines, 1.97 s, plus ~12 for the
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

Steps 1–3 are a day's work — 209 tests, 20.51 s, `ruff check` clean as
written — and would take algorithm correctness from "four-vertex fixtures plus
three pinned results" to "agrees with an independent implementation on 8,742
real pairs and 10,866 randomized queries, expands fewer nodes than Dijkstra on
every one of 500 pairs, and fails loudly if that stops being true".

They also produce two corrections the report needs and nothing else would have
surfaced: A\* is optimal only for *consistent* heuristics, and the frontier's
space bound is O(E), not the O(V) the write-up and the slides claim.

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
| A "random" heuristic that is not a function | Score every vertex once, at construction (`InconsistentHeuristic`). A closure calling `rng.random()` per invocation is not a heuristic, inflates the failure count, and makes the test flaky |
| Asserting the O(V) space bound | It does not hold for `Dijkstra`/`AStar` — no decrease-key means superseded frontier entries, so the bound is O(E). Assert `peak_frontier <= nodes_pushed <= E + 1`, and O(V) for `BFS` only |
| Writing tests as bare functions | The repository is class-based throughout (`README.md:123`); 17 of 17 modules in `tests/flight_planner/` use test classes |

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

**Pass 3 — the same commit, rewritten class-based.** Everything in Options A,
E and G was re-authored as classes (§2) and re-run, because the first two
passes wrote tests as bare functions, against the repository's convention.
That rewrite changed a result, not just a shape: see the note on the counts at
the end of Option E.

| Section | Pass | What was run | Key output |
| --- | --- | --- | --- |
| §2 | 1 | `MultiDiGraph` vs `DiGraph` on the global snapshot | `66332` vs `36717` edges; `ORD->ATL` carries 20 |
| A | 1 | 4-test parity module on `shortest-vs-fewest` | `4 passed in 16.85s`, 8,742 pairs, 0 disagreements |
| A | **2** | the same module, unchanged, on current code | `4 passed in 16.87s`; three tutorial pairs identical in cost *and* path |
| §2 | **3** | `nx.astar_path` under an inconsistent heuristic | `0` suboptimal of 10,866 — NetworkX reopens, so it is a valid oracle |
| A, G | **3** | class-based `test_parity.py` | `8 passed in 18.73s`; same parity results |
| G | **3** | `peak_frontier` against V over 500 pairs | Dijkstra `1.65 V` on 375/500, A\* `1.85 V` on 28/500, BFS `0.91 V` on 0/500 |
| E | **3** | class-based `test_randomized.py` | `201 passed in 1.97s` |
| E | **3** | shipped vs `ReopeningAStar`, fixed heuristic | 10,866 queries; **27** suboptimal / **25** cost≠path, `0` reopening; +0.52 % expansions |
| all | **3** | `tests/networkx_parity/` and `ruff check` | `209 passed in 20.51s`; `All checks passed!` |
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

Where a figure exists in more than one pass, **the highest-numbered pass is
the one quoted in the body.** Anything still marked Pass 1 only — Options C
and D, and the haversine consistency sweep — was not re-run; nothing in the
refactor should move it, but that is an expectation rather than a measurement.

Options A, E and G are no longer scripts living outside the repository: they
are four files under `tests/networkx_parity/`, reproduced in full above, and
committing them is a `git add` rather than a rewrite. Option C's engine and
Option B's `record()` call are still sketches.

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
