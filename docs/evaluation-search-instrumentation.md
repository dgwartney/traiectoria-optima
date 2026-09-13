# Manual Evaluation: Search Instrumentation

A walkthrough for checking, by hand, the work on `feature/search-instrumentation`
— four commits that make the cost of a search a reported property of it, and
then measure that cost on the world network to produce deliverable **T8**'s
comparison table and runtime plot ([project_plan.md](project_plan.md), line 70).

This is written for someone who did not write the code. Every command below was
run to produce the output shown; if yours differs in anything other than the
timings called out in [§8](#8-expected-variation-versus-real-failure), that is a
finding worth raising.

Budget about 15 minutes. Nothing here writes to `main`, pushes, or needs network
access — the data is pinned in a committed snapshot.

## Contents

1. [What is under evaluation](#1-what-is-under-evaluation)
2. [Before you start](#2-before-you-start)
3. [The automated gate](#3-the-automated-gate)
4. [The contract that must not have moved](#4-the-contract-that-must-not-have-moved)
5. [The new capability, by hand](#5-the-new-capability-by-hand)
6. [The committed experiment](#6-the-committed-experiment)
7. [Deliverables: what this closes and what it does not](#7-deliverables-what-this-closes-and-what-it-does-not)
8. [Expected variation versus real failure](#8-expected-variation-versus-real-failure)

## 1. What is under evaluation

```
f40ee82  Measure the search cost on the world network        <- the experiment
24c8676  Export the instrumentation, document it, and demo it
cd498c9  Report what a search cost, not just what it found    <- the capability
75fc1e0  Split pathfinding/algorithms.py into one module per algorithm
```

The first three are the work; `75fc1e0` is a deliberately behaviour-neutral
file split that precedes it, so the instrumentation diff reads as instrumentation
rather than as a reorganisation.

The problem being solved: the project's central claim is that A\* reaches
Dijkstra's answer while expanding far fewer nodes, and until `cd498c9` nothing
in the codebase measured that. `find_path()` returned `(cost, path)` and
discarded everything the search had learned. There are now two seams:

| Seam | File | Answers |
|---|---|---|
| `SearchResult` | [`pathfinding/result.py:20`](../src/flight_planner/pathfinding/result.py) | Aggregate counters — `nodes_expanded`, `nodes_pushed`, `peak_frontier`. What a comparison table needs. |
| `SearchObserver` | [`pathfinding/observers.py:22`](../src/flight_planner/pathfinding/observers.py) | Per-event hooks. `ExpansionTrace` ([line 55](../src/flight_planner/pathfinding/observers.py)) records the *order* a search looked — its shape rather than its size. |

One deliverable from `main` is in scope too, because Dijkstra consumes it:
**T3**, the from-scratch min-heap (`4b101fe`). [§5.4](#54-the-from-scratch-heap-is-still-from-scratch) checks it.

## 2. Before you start

```bash
git clone <repo> && cd traiectoria-optima     # or use your existing clone
git checkout feature/search-instrumentation
uv sync                                        # installs the dev group, incl. matplotlib
git log --oneline -4                           # expect the four commits above
```

`uv` is the only prerequisite; [setup.md](setup.md) covers installing it. Do not
run `make flight_network` — it regenerates `data/processed/`, and everything here
reads a pinned snapshot instead, which is the point of the experiments model
([experiments.md](experiments.md)).

## 3. The automated gate

Run this first. If it fails, stop and report it — the rest of the walkthrough
assumes it passes.

```bash
make check          # = make lint + make test
```

```
============================= 382 passed in 12.30s =============================
```

`make lint` is `ruff` with the Google docstring convention enforced on
everything outside `tests/`, so a missing `Args:` block fails the build. The
382 include the suite's pre-existing tests plus the new ones:

| Test file | Tests | Covers |
|---|---|---|
| `tests/flight_planner/test_search_result.py` | 20 | The counters, their invariants, and the early-return cases |
| `tests/flight_planner/test_observers.py` | 24 | Observer hooks, `ExpansionTrace`, and the central claim as an executable test |
| `tests/experiments/test_committed.py` | 27 | Every committed experiment still reproduces, including the new one |
| `tests/experiments/test_search_cost_plots.py` | 8 | Both charts render on both surfaces |
| `tests/flight_planner/test_min_heap.py` | 19 | T3's heap (landed on `main`) |

The one to read if you read only one:

```bash
uv run pytest "tests/flight_planner/test_observers.py::TestTheProjectsCentralClaim" -v
```

```
test_astar_expands_fewer_nodes_for_the_same_answer PASSED
test_astar_never_enters_the_dead_end PASSED
test_dijkstra_does_enter_the_dead_end PASSED
test_a_heuristic_cannot_help_when_every_route_is_equal PASSED
```

That is the whole thesis, on a hand-built graph whose numbers are checkable by
eye ([`test_observers.py:97`](../tests/flight_planner/test_observers.py)). Read
the four names as a sentence: A\* expands fewer nodes for the same answer
because it never enters the dead end that Dijkstra does — and when every route
is equal, the heuristic has nothing to offer and the advantage vanishes. The
last one matters most in review, because a claim with no stated limit is
usually a claim nobody tested the edge of.

## 4. The contract that must not have moved

The risk in this change is collateral: `search()` became the abstract method and
`find_path()` became a concrete adapter on the base class. About twenty call
sites, both pre-existing committed experiments and the Colab notebook depend on
`find_path()` returning a plain `(cost, path)` tuple. Confirm it still does:

```bash
uv run python -c "
from flight_planner import AStar, BFS, Dijkstra, haversine_heuristic
from flight_planner.experiments import Snapshot

planner = Snapshot.open('data/snapshots/2026-09-11-bb90a8').catalog().planner()
for name, algo in (('BFS', BFS()), ('Dijkstra', Dijkstra()),
                   ('A*', AStar(haversine_heuristic()))):
    cost, path = planner.find_shortest_route('SFO', 'BOS', algo)
    print(f'{name:<9} tuple of {len(path)} legs, cost {cost:.6f}')
"
```

```
BFS       tuple of 1 legs, cost 1.000000
Dijkstra  tuple of 1 legs, cost 4341.022085
A*        tuple of 1 legs, cost 4341.022085
```

Two things to notice, both intended. Dijkstra and A\* agree to the last decimal
place — that is the admissibility of the haversine heuristic showing up as data.
And BFS's "cost" is `1.0`, not kilometres: it minimises hops, so its cost column
counts legs. The three algorithms do not answer the same question, and any table
that puts their costs in one column has to say so.

The stronger version of this check is already automated: the two experiments
committed *before* this branch existed reproduce their recorded numbers to nine
decimal places, which is what proves the refactor changed no answer. That is
`tests/experiments/test_committed.py`, run in [§3](#3-the-automated-gate).

## 5. The new capability, by hand

### 5.1 What a search cost

```bash
uv run python -c "
from flight_planner import AStar, BFS, Dijkstra, haversine_heuristic
from flight_planner.experiments import Snapshot

planner = Snapshot.open('data/snapshots/2026-09-11-bb90a8').catalog().planner()
print(f'{\"algorithm\":<9} {\"expanded\":>9} {\"pushed\":>7} {\"peak\":>5} {\"km\":>10}')
for name, algo in (('BFS', BFS()), ('Dijkstra', Dijkstra()),
                   ('A*', AStar(haversine_heuristic()))):
    r = planner.search_route('SFO', 'BOS', algo)
    print(f'{name:<9} {r.nodes_expanded:>9} {r.nodes_pushed:>7} {r.peak_frontier:>5} {r.cost:>10.2f}')
"
```

```
algorithm  expanded  pushed  peak         km
BFS              10     476   466       1.00
Dijkstra        746    1264   418    4341.02
A*                1     105   104    4341.02
```

`search_route()` is the instrumented sibling of `find_shortest_route()`, and
returns the `SearchResult` rather than a tuple. A\* settles this query on a
single expansion where Dijkstra needs 746.

Note that BFS expands only 10 — *fewer* than Dijkstra. Uninformed search is not
uniformly expensive, and a write-up claiming otherwise would be contradicted by
its own data. BFS is cheap here because it stops at the first route it finds,
which is a route it has no reason to believe is short.

### 5.2 The shape of a search, not just its size

The counters say how much. The trace says what it looked at, which is the part
that explains *why*:

```bash
uv run python -c "
from flight_planner import AStar, Dijkstra, ExpansionTrace
from flight_planner.experiments import Snapshot

planner = Snapshot.open('data/snapshots/2026-09-11-bb90a8').catalog().planner()
for name, algo in (('Dijkstra', Dijkstra()), ('A*', AStar(haversine_heuristic()))):
    trace = ExpansionTrace()
    planner.search_route('HNL', 'BOS', algo, observer=trace)
    codes = [v.iata_code for v in trace.order]
    print(f'{name:<9} {trace!r}')
    print(f'          first 12 expanded: {\" \".join(codes[:12])}')
"
```

```
Dijkstra  ExpansionTrace(expanded=1056, pushed=1985)
          first 12 expanded: HNL MKK LNY JHM OGG LIH HNM KOA MUE ITO CXI MAJ
A*        ExpansionTrace(expanded=3, pushed=123)
          first 12 expanded: HNL SMF SLC
```

This is the finding in one screen, and it is worth a slide. Honolulu to Boston:
Dijkstra's first eleven expansions are Molokai, Lanai, Kapalua, Kahului, Kauai,
Hana, Kona, Waimea, Hilo, then Christmas Island and the Marshall Islands — it
works outward through every Hawaiian island because they are *near Honolulu*.
A\* expands Honolulu, Sacramento, Salt Lake City: it never looks at Molokai,
because Molokai is near the start and far from the goal, and only a heuristic
can tell those two things apart.

### 5.3 The observer as an extension point

```bash
uv run python src/demos/search_instrumentation_example.py
```

Its network is eight airports on one line of longitude — a corridor from SFO
east to BOS, plus a spur running the wrong way over the Pacific — so the numbers
are verifiable by hand rather than taken on trust:

```
1. What each search cost
   algorithm    expanded  pushed  peak        cost  route
   BFS                 7       8     2        5 hops SFO->SLC->DEN->ORD->CLE->BOS
   Dijkstra            7       8     2    4,375 km  SFO->SLC->DEN->ORD->CLE->BOS
   A*                  5       7     2    4,375 km  SFO->SLC->DEN->ORD->CLE->BOS

2. Where each search looked, in order
   Dijkstra   SFO SLC DEN OGG ORD HNL CLE
   A*         SFO SLC DEN ORD CLE
```

Section 3 of its output subclasses `SearchObserver` and overrides one hook, which
is the demonstration that the seam is open to questions nobody has asked yet —
per-expansion memory sampling, cost-accumulation curves, anything an experiment
later invents. Section 4 re-confirms `find_path()` is untouched.

The demo is registered in the catalogue at [demos.md:36](demos.md), which is the
convention every other capability in the package follows.

### 5.4 The from-scratch heap is still from scratch

T3 requires a binary min-heap written from scratch, not a wrapper around
`heapq`. The guard is a test rather than a convention:

```bash
uv run pytest "tests/flight_planner/test_dijkstra.py::TestRunsOnOurOwnHeap" -v
```

```
test_no_pathfinding_module_imports_heapq PASSED
test_dijkstra_runs_on_our_own_heap PASSED
```

It walks every module in the `flight_planner.pathfinding` package
([`test_dijkstra.py:82`](../tests/flight_planner/test_dijkstra.py)), so a future
algorithm cannot quietly reintroduce `heapq` in a file the test never heard of.
Confirm by hand if you like:

```bash
grep -rn "import heapq" src/flight_planner/     # expect no matches
```

Grep for the *import*, not the word. A bare `grep heapq` matches
`adt/min_heap.py:6`, where the module docstring explains that it deliberately
does not use `heapq` — a mention, not a dependency.

## 6. The committed experiment

### 6.1 Read what was recorded

An experiment directory records the numbers *and* what produced them — which
snapshot, which commit, which parameters ([experiments.md](experiments.md)):

```bash
uv run python -c "
from flight_planner.experiments import Experiment
e = Experiment.open('experiments/search-cost')
r = e.results()
print('snapshot  ', r['snapshot']['id'], '  commit', r['snapshot']['source_commit'][:8])
print('graph     ', r['catalog']['airports'][0], 'airports /', r['catalog']['routes'][0], 'routes')
print()
print(f'{\"pair\":<9}{\"BFS\":>6}{\"Dijkstra\":>10}{\"A*\":>5}   {\"Dijkstra km\":>12}{\"A* km\":>14}  agree')
for row in r['results']['comparison']:
    x = row['expanded']; c = row['cost']
    print(f'{row[\"pair\"]:<9}{x[\"BFS\"]:>6}{x[\"Dijkstra\"]:>10}{x[\"A*\"]:>5}   {c[\"Dijkstra\"]:>12.6f}{c[\"A*\"]:>14.6f}  {c[\"Dijkstra\"]==c[\"A*\"]}')
"
```

```
snapshot   2026-09-11-bb90a8   commit 610936de
graph      3387 airports / 66332 routes

pair        BFS  Dijkstra   A*    Dijkstra km         A* km  agree
SFO-BOS      10       746    1    4341.022085   4341.022085  True
LAX-JFK      62       590    1    3974.164252   3974.164252  True
SEA-MIA      52       784    1    4379.358290   4379.358290  True
HNL-BOS     132      1056    3    8192.794110   8192.794110  True
ANC-MIA     174       778    6    6459.621513   6459.621513  True
```

That is T8's comparison table. Check three things about it:

- **The graph is the world**, 3,387 airports and 66,332 routes, not the
  94-airport US slice the earlier experiments use. The claim is about long-haul
  queries, and those only exist if the graph has long hauls in it.
- **Every `agree` is `True`** — A\* matches Dijkstra's distance exactly on all
  five pairs, while expanding 130× to 780× fewer nodes.
- **The pairs survive every narrowing.** The runtime series below re-asks the
  same five queries at eight graph sizes. If a pair's airports vanished from a
  smaller graph, the curve would be comparing different questions at different
  sizes. `test_every_query_pair_survives_every_narrowing` asserts this, so it
  cannot rot silently.

### 6.2 Re-run it and confirm it reproduces

This is the check that distinguishes a recorded result from a claimed one.

```bash
cd experiments/search-cost
uv run --project ../.. jupyter nbconvert --execute --to notebook --inplace explore.ipynb
cd ../..
git status --short
```

Takes about 13 seconds. Exactly four files should be dirty:

```
 M docs/images/runtime-light.png
 M experiments/search-cost/explore.ipynb
 M experiments/search-cost/results.json
 M slides/images/runtime.png
```

Read that list closely, because *which* files changed is itself the result:

- The two **`nodes-expanded`** PNGs are absent — byte-identical across runs.
  Expansion counts are deterministic, so the headline chart is reproducible
  pixel for pixel.
- The two **`runtime`** PNGs changed because they plot wall-clock timings, which
  cannot repeat exactly.
- **`explore.ipynb`** is dirty only because `--inplace` stored cell outputs in
  it. Committed notebooks in this repo carry none, and
  `test_its_notebook_carries_no_stored_output` enforces that.

Now confirm the non-timing payload is unchanged:

```bash
python3 -c "
import json, subprocess
before = json.loads(subprocess.run(['git','show','HEAD:experiments/search-cost/results.json'],
                                   capture_output=True, text=True).stdout)
after = json.load(open('experiments/search-cost/results.json'))

def strip(d):
    d = json.loads(json.dumps(d)); d.pop('recorded', None)
    for row in d['results']['runtime_series']:
        row.pop('median_ms'); row.pop('build_ms')
    # 'scaling' holds log-log fits OVER those timings, so it moves with them.
    # Excluding it is not a loosening of the check -- an exponent derived from
    # wall-clock was never a deterministic value.
    d['results'].pop('scaling')
    return d

print('deterministic payload identical:', strip(before) == strip(after))
for x, y in zip(before['results']['runtime_series'], after['results']['runtime_series']):
    for k in ('BFS', 'Dijkstra', 'A*'):
        u, v = x['median_ms'][k], y['median_ms'][k]
        print(f'  {x[\"label\"]:<16} {k:<9} {u:7.3f} -> {v:7.3f}  {100*(v-u)/u:+6.1f}%')
"
```

Expect `deterministic payload identical: True`, and timing drift in the single
digits of percent. Then restore the tree:

```bash
git checkout -- experiments/search-cost slides/images docs/images
git status --short          # expect clean
```

**Do not commit the re-run.** Its only real change is the timestamp and fresh
timings; committing it adds churn and, if you forget to strip the notebook,
breaks the suite.

### 6.3 Look at the charts

The palette was validated with a checker for colour-vision deficiency on both
surfaces, but a validator checks colour, not layout. Label collisions and
overflow are found by eye, so open all four:

```bash
open slides/images/runtime.png slides/images/nodes-expanded.png \
     docs/images/runtime-light.png docs/images/nodes-expanded-light.png
```

What to look for:

- **No white box on the dark chart.** A default-white axes panel on a black
  slide is the standard matplotlib failure and it survives every other check.
  Both the figure and the axes are painted.
- **Each series carries a marker shape as well as a hue** — circle, square,
  triangle — so identity survives greyscale printing and colour-blind readers.
  Lines are also labelled directly at their right-hand ends, not by legend only.
- **`nodes-expanded` is on a linear axis**, which makes A\*'s bars nearly
  invisible beside Dijkstra's. That is not a rendering fault; it is the finding.
  Value labels sit above all fifteen bars, so the invisible ones are still
  readable.
- **`runtime` is log-log**, so a power law reads as a straight-line slope, which
  is what the Big-O write-up needs.

One thing on the runtime chart will look like a bug and is not. **Dijkstra's
curve is not monotonic** — it dips from 5.24 ms at 11,315 V+E down to 3.31 ms at
51,536. The `large` narrowing is 1,062 airports holding 50,474 routes, so the
five query pairs sit one or two hops apart in it and Dijkstra settles fewer
vertices before reaching the goal. Runtime tracks nodes settled, not graph size.
Raise it if the Big-O write-up plots around this instead of explaining it.

Also note the x-axis is **V+E, not airport count**. The two do not move
together: the US-large narrowing has 94 airports but 7,005 routes, while airline
UA has 427 airports and 2,170 routes. Ordering by airports alone produces a
curve that crosses itself, and V+E is the term in O((V+E) log V) anyway.

## 7. Deliverables: what this closes and what it does not

Measured against T8 ([project_plan.md:70](project_plan.md)) and the required
outputs checklist ([project_plan.md:97](project_plan.md)):

| Requirement | State |
|---|---|
| T8: BFS/Dijkstra/A\* comparison table, nodes expanded and runtime, on long-haul queries | **Complete** — [§6.1](#61-read-what-was-recorded), reproducible |
| Required output: empirical runtime study, at least one plot of time against input size | **Complete** — `slides/images/runtime.png`, eight sizes spanning 30× |
| T8: Big-O write-up | **Evidence only.** The counters, `peak_frontier` and the size series are all measured; the prose argument is unwritten. `slides/index.html:352` still reads `TODO: confirm against our actual implementation, not the textbook`. |
| T8: one rendered route map | **Not started.** `ExpansionTrace` gives it better source data than a bare route line, but nothing renders a map. |
| Slides consuming these numbers | **Not started, deliberately** — out of scope for this branch. `slides/index.html:333` still reads `TODO: fill from the long-haul query set`, and line 359 asks for `images/runtime.png`, which now exists. |

So the honest summary: this branch closes the measurement half of T8 and leaves
the presentation half open. Anyone reviewing the deck should expect the
placeholders to still be placeholders.

## 8. Expected variation versus real failure

| You see | Verdict |
|---|---|
| `median_ms` differs from the recorded values by a few percent | **Expected.** Wall-clock timings on different hardware. The series are separated by 5× to 26×, so the shape holds. |
| `recorded` timestamp changes after a re-run | **Expected.** It records when the run happened. |
| `runtime*.png` differ after a re-run; `nodes-expanded*.png` do not | **Expected**, and the point — see [§6.2](#62-re-run-it-and-confirm-it-reproduces). |
| A\* and Dijkstra disagree on cost by any amount | **Real failure.** The heuristic is no longer admissible, or the search is wrong. |
| Any `nodes_expanded`, `pushed`, `peak`, or `vertices`/`edges` value differs | **Real failure.** These are deterministic. |
| A `scaling` exponent or `r²` moves by a few hundredths | **Expected.** They are least-squares fits over `median_ms` and `build_ms`, so they inherit the timing noise. Only the *shape* is portable: construction stays near 1.0, and every search stays well below its bound. |
| `cost_unit` is absent from a row of `comparison` | **Real failure.** Every cost must say whether it counts hops or weight; a bare `cost` mapping mixes the two. |
| `find_path()` returns anything but a 2-tuple | **Real failure.** The contract twenty call sites rely on has moved. |
| `grep -rn "import heapq" src/flight_planner/` matches | **Real failure.** T3 requires the heap be written from scratch. |
| Dijkstra's runtime curve dips in the middle | **Expected** — explained in [§6.3](#63-look-at-the-charts). |
| BFS expands fewer nodes than Dijkstra | **Expected** — explained in [§5.1](#51-what-a-search-cost). |
| Test count is not 382 | **Worth asking about.** Not necessarily wrong — a later commit adds tests — but this document was written against 382. |
