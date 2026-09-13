# Design: Search Instrumentation

The design record for `feature/search-instrumentation` — what was decided, what
was rejected and why, what was measured, and what is deliberately left for
later. Written so the work can be reviewed, extended, or re-derived by someone
who was not in the room.

The code answers *what* was built. This answers *why*, which is the part that
does not survive in a diff. [evaluation-search-instrumentation.md](evaluation-search-instrumentation.md)
is the third piece: how to check by hand that it works.

**Status: implemented.** This is not a plan — all four commits are in the tree
at `f40ee82` and 382 tests pass against them. Every decision below is already
realised in code, and every behaviour stated was run against the built code and
its output pasted. Nothing has been pushed.

## Contents

1. [Provenance](#1-provenance)
2. [The problem](#2-the-problem)
3. [Decision log](#3-decision-log)
4. [The API as built](#4-the-api-as-built)
5. [What was measured](#5-what-was-measured)
6. [Experiment design](#6-experiment-design)
7. [Breaking change and migration](#7-breaking-change-and-migration)
8. [Deliberately out of scope](#8-deliberately-out-of-scope)
9. [Remaining work, and doing it in parallel](#9-remaining-work-and-doing-it-in-parallel)
10. [Self-review record](#10-self-review-record)

## 1. Provenance

The design was settled in a brainstorming session on 2026-09-12 (21:19–21:28
UTC), refined across nine successive plan drafts, and implemented 21:57–22:31.
Three decisions were put to the project owner as explicit choices; those are
marked **[owner decision]** in [§3](#3-decision-log).

| Commit | Content |
|---|---|
| `75fc1e0` | Split `pathfinding/algorithms.py` into one module per algorithm. Pure move. |
| `cd498c9` | `SearchResult`, `SearchObserver`, `ExpansionTrace`; propagation to `Graph` and `FlightPlanner`. |
| `24c8676` | Top-level re-exports, the two extension-point docs, and `src/demos/search_instrumentation_example.py`. |
| `f40ee82` | `experiments/search-cost/` — the measurement, its charts, and its tests. |

The reasoning lived only in a session transcript, which is why this document
exists — the code and its tests survived, the argument for it did not. Claims
here were re-checked against the built code rather than copied from the plan
that preceded it: the line counts, the two overhead figures in
[§5](#5-what-was-measured) and the semantics table in
[§4](#4-the-api-as-built) were all re-run at `f40ee82`.

## 2. The problem

Deliverable **T8** ([project_plan.md:70](project_plan.md)) requires a
BFS/Dijkstra/A\* comparison table reporting *nodes expanded*, plus a
runtime-versus-input-size plot and a Big-O write-up of our own code. The A1
Outcome behind it states the project's thesis: informed search reaches the same
answer as uninformed search while expanding fewer nodes.

Nothing in the codebase measured that. `PathfindingAlgorithm.find_path()`
returned `(cost, path)` and discarded everything the search had learned. The
thesis was therefore an assertion, not a result.

An ad-hoc measurement through a `get_outgoing_edges` hook confirmed the number
was worth having before any design work started — on the 94-airport US network:

| Query | BFS | Dijkstra | A\* | cost (Dijkstra = A\*) |
|---|---|---|---|---|
| SFO→BOS | 5 | 92 | **1** | 4341.02 km |
| HNL→BDL | 28 | 89 | **7** | 8071.51 km |
| BOI→CHS | 86 | 69 | **3** | 3376.00 km |

BOI→CHS is why the measurement was worth doing rather than assuming: BFS expands
*more* than Dijkstra there while returning a worse route. "Uninformed search is
expensive" is too simple a story, and the data says so.

## 3. Decision log

### D1. How to expose nodes-expanded **[owner decision]**

Four options were put forward. The two chosen were **`SearchResult` + `search()`**
and the **observer callback** — not as a compromise, but because the data has two
shapes: aggregate counts known in advance, and per-event sequences invented
later.

| Option | Verdict |
|---|---|
| **`SearchResult` returned by a new `search()`** | **Chosen.** One implementation per algorithm; counts are a property of the search rather than of a harness watching it. |
| **Instrumented `Graph` decorator** — promote the `_CountingGraph` test double into the package | **Rejected.** Counts `get_outgoing_edges` calls, which is a *proxy* for expansion. It happens to coincide today; it would silently diverge the moment an algorithm peeked at a neighbour without expanding it. A measured deliverable should not rest on a coincidence. |
| **Observer callback** — an optional `on_expand` callable | **Chosen as well**, for traces rather than counts. Matches the project's composition idiom (pluggable `DistanceFormula`, `Memoized` wrapper). |
| **Stats on the algorithm instance** — read `Dijkstra().nodes_expanded` after the call | **Rejected.** Smallest diff, worst consequence: it makes the Strategy objects stateful, so a shared instance is clobbered by the next call and concurrent use is silently wrong. |

The decisive argument for `SearchResult` over the decorator: the rubric asks
what the *algorithm* did, so the algorithm should be the thing that reports it.

### D2. Which counters to carry **[owner decision]**

Chosen: **`nodes_expanded` + `nodes_pushed` + `peak_frontier`**, over
`nodes_expanded` alone.

- `nodes_expanded` is the required Outcome.
- `nodes_pushed` quantifies the wasted work the lazy-deletion heap design
  creates — the gap between the two *is* the cost of not having decrease-key.
- `peak_frontier` is the measured space bound. The complexity table claims O(V)
  space; this is the evidence for it rather than a citation of the textbook.

The argument against — "don't add speculative fields" — lost to a practical one:
adding a counter later means re-recording every committed result to keep the
experiments comparable. The cost of a field you don't use is zero; the cost of a
field you need after recording is a re-run of everything.

### D3. Build the observer seam now, or defer it **[owner decision]**

Chosen: **now**. Deferring was the safer-sounding option, and the case against it
is that the algorithms would have to be re-opened later for the T8 route map,
which is the one thing this branch is trying to avoid. Observation was measured
free ([§5](#5-what-was-measured)), so the runtime argument for deferring did not
exist either.

The owner's own question settled the shape: *"does the observer model not also
allow collecting other information at run time — memory used, other metrics?"*
Yes, and that is the point of the seam. It is the same bargain the experiments
framework already makes with snapshots: ask a new question of fixed data without
disturbing the thing being measured.

### D4. Observer passed per-run, not per-constructor

`search(graph, start, goal, observer=None)`, not `Dijkstra(observer=...)`. Keeps
the Strategy objects stateless — which is exactly the flaw that sank the
"stats on the instance" option in D1 — and lets one algorithm instance be reused
with different observers.

### D5. BFS reports hop depth as its `on_push` priority

BFS has a `deque`, not a priority queue, so it has no priority to report. Left
unspecified, it becomes `None` at implementation time and every observer ever
written inherits the obligation to defend against it. Resolved to **hop depth** —
its implicit priority, and the quantity that makes a BFS trace comparable to the
other two.

### D6. Runtime and memory stay out of `SearchResult`

They are properties of a whole run, not of an expansion, and belong to the
harness wrapped around `search()`. `tracemalloc` also measured **4.10×**
overhead, so a memory pass has to be a separate run from a timing pass no matter
where the code lives.

### D7. Split `algorithms.py` into one module per algorithm

`pathfinding/` was the only place in the package where a Strategy ABC and its
implementations shared a file. `geo/` is the exact precedent: `formula.py` holds
the ABC, and `haversine.py` / `vincenty.py` / `memoized.py` each get their own
file. The tests were *already* split that way (`test_bfs.py`, `test_dijkstra.py`,
`test_astar.py`) — the source was the odd one out.

Adding three classes plus counter logic to a 221-line file would have pushed it
past 400 lines and made it the second-largest module in the package.

Two further reasons that are about people, not lines: the three algorithms are
separately-owned deliverables (T5 BFS, T6 Dijkstra, T7 A\*), so one file per
algorithm makes ownership boundaries real and stops two people editing different
algorithms from colliding in one file. And the package README documents "where to
hook in a new algorithm" — an instruction that is self-evident once you add
`bellman_ford.py` beside `dijkstra.py`.

An objection was raised during design and then withdrawn: that the move would
destroy `git blame`. It does not — `git log --follow` and `git blame -C` track
moves.

### D8. The split landed as its own commit, before any instrumentation

So that `git show 75fc1e0` is provably behaviour-preserving, and `cd498c9`
contains only the real change instead of being unreadable against a simultaneous
reshuffle. This is why there are four commits and not two.

### D9. `find_path()` becomes a concrete adapter on the ABC

```python
def find_path(self, graph, start, goal):
    result = self.search(graph, start, goal)
    return result.cost, result.path
```

Defined once on `PathfindingAlgorithm` rather than three times. This is the
decision that protects roughly twenty call sites, both pre-existing committed
experiments, and the Colab notebook from the change entirely.

## 4. The API as built

```python
@dataclass(frozen=True)
class SearchResult(Generic[E]):
    cost: float
    path: List[E]
    nodes_expanded: int
    nodes_pushed: int
    peak_frontier: int
```

**Definition of "expanded":** a vertex whose outgoing edges were requested. All
three algorithms check `current == goal` and break *before* expanding, so the
goal is never counted. That was already consistent across the three; it is
written down here so it stays that way.

**The two early-return paths.** Neither was specified anywhere before this work,
and each is now a test case:

| Case | `cost` | `path` | counters |
|---|---|---|---|
| `start == goal` | `0.0` | `[]` | **all zero** — no search ran |
| goal unreachable | `inf` | `[]` | **the real counts** — the search exhausted the reachable component, and that work is exactly what a benchmark should see |

The unreachable case is the one that would have gone wrong by default: zeroing
the counters alongside the `inf` cost would silently under-report the single most
expensive query type in the benchmark. As built:

```
start==goal     cost=0.0  path=[]  expanded=0  pushed=0  peak=0
unreachable     cost=inf  path=[]  expanded=1  pushed=1  peak=1
```

The second line is two vertices with no edge between them — one expansion, which
is the real cost of establishing that there is no route.

`FlightPlanner.find_shortest_route` returns `(0.0, [])` *before* calling the
algorithm at all, so `search_route` constructs the zero result itself rather
than delegating.

**`cost` is not one unit across algorithms.** BFS returns a hop count; Dijkstra
and A\* return kilometres. That was already true, but `SearchResult` and the
comparison table put them side by side where it can mislead. Any table must give
them separate columns — never one column labelled "cost".

The observer seam, in full:

```python
class SearchObserver:
    def on_expand(self, vertex, cost_so_far: float) -> None: ...
    def on_push(self, vertex, priority: float) -> None: ...

class ExpansionTrace(SearchObserver):
    """Ordered record of what a search looked at."""
```

`on_push` fires again on each re-queue, so its call count equals
`nodes_pushed` — the two seams agree by construction rather than by assertion.

## 5. What was measured

D3 and D6 rest on two overhead measurements. Both were taken during design and
**re-run against the built code** for this document — SFO→BOS on the 94-airport
US network (94 airports / 7,005 routes), median of 200 runs after a discarded
warm-up:

| Measurement | Result | Decided |
|---|---|---|
| Bare `search_route` | 1.774 ms | baseline |
| With a `SearchObserver` attached | 1.773 ms → **1.00×** | D3: observation is free, so the seam was built now rather than deferred |
| Under `tracemalloc` (50 runs) | 6.059 ms → **3.42×** | D6: memory sampling has to be a separate run from timing |

The design-time `tracemalloc` figure was 4.10×; this machine measures 3.42×. The
ratio is hardware- and load-dependent, and the decision only needed it to be
large, which it is either way. The 1.00× observer figure reproduced exactly.

## 6. Experiment design

`experiments/search-cost/` is where the API meets real data. Its decisions:

- **The world snapshot, not the US slice.** 3,387 airports and 66,332 routes.
  The claim is about long-haul queries, and those only exist if the graph has
  long hauls in it. The earlier experiments use the 94-airport slice; this one
  deliberately does not.
- **Size axis is V+E, not airport count.** They do not move together: the
  US-large narrowing is 94 airports / 7,005 routes, while `airline("UA")` is
  427 / 2,170. An x-axis of airports produces a curve that crosses itself. V+E
  is also the term in O((V+E) log V), so it is the axis the Big-O argument
  needs. Eight narrowings span ~30×, 2,329 to 69,719 V+E.
- **Query pairs must survive every narrowing.** Narrowing removes airports, so
  pairs are chosen to exist in all eight graphs and reused at every size.
  Otherwise the series compares different questions at different sizes and the
  curve means nothing. This is the easiest thing here to get wrong, so
  `test_every_query_pair_survives_every_narrowing` asserts it.
- **Timing method:** `perf_counter()` around `search()` with no observer
  attached, graph built once outside the timed region, one warm-up call
  discarded, then 15 repeats reporting the **median** — robust to GC pauses in a
  way the mean is not.
- **Plots live beside the notebook, not in the package.** The wheel depends on
  `pandas` alone; `matplotlib` is a dev-group dependency. Plotting is something
  this repository does, not something the package offers.
- **One function per chart with a `mode="dark"|"light"` argument**, so the
  reveal.js deck and the pandoc report render from the same code rather than two
  drifting copies.
- **Colour assigned by identity and never cycled**, validated for colour-vision
  deficiency on both surfaces (worst all-pairs CVD ΔE 9.4), with a distinct
  marker shape per series so identity survives greyscale printing. Adding a
  fourth algorithm cannot repaint the three already on screen.

One finding the write-up has to address rather than smooth over: **Dijkstra's
runtime curve is not monotonic**, dipping from 5.24 ms at 11,315 V+E to 3.31 ms
at 51,536. The `large` narrowing is 1,062 airports holding 50,474 routes, so the
query pairs sit one or two hops apart and Dijkstra settles fewer vertices before
reaching the goal. **Runtime tracks nodes settled, not graph size** — which is a
more interesting sentence than the one the plot was expected to produce.

## 7. Breaking change and migration

Making `search()` the abstract method means **any subclass of
`PathfindingAlgorithm` implementing only `find_path` no longer instantiates.**

In this repository that is exactly one class, a test double in
`tests/flight_planner/test_graph.py`. For an outside consumer it is a migration:
rename `find_path` to `search` and return a `SearchResult` instead of a tuple.
The two extension-point docs a consumer would read
([`src/flight_planner/README.md:80`](../src/flight_planner/README.md) and
[flight_planner.md:425](report/13-appendix-b-data-structures.md)) were updated in `24c8676` to say
`search`.

Callers are unaffected — that is D9's entire purpose.

## 8. Deliberately out of scope

Recorded so it is not mistaken for oversight:

- Changing the `(cost, path)` tuple contract.
- Timing or memory fields on `SearchResult` (D6).
- The T8 route map. This branch supplies the `ExpansionTrace` that makes a
  Dijkstra-blob-versus-A\*-cone map possible and proves the data is there, but
  renders nothing.
- The slide and report updates that consume these numbers.
- The Big-O prose write-up. The evidence is measured; the argument is unwritten.
- Splitting any other module. `adt/min_heap.py` (243 lines),
  `experiments/catalog.py` (670) and `loaders/csv_loader.py` (374) are all
  single-concept files and stay as they are.
- Pushing anything.

## 9. Remaining work, and doing it in parallel

Short answer: **yes, and the branch was built so that it can be.** The evidence,
not the assurance:

### The four live branches have zero file overlap

Measured with `git diff --name-only $(git merge-base main <branch>) <branch>`:

| Branch | Files touched | Overlap with this work |
|---|---|---|
| `feature/search-instrumentation` | 31 | — |
| `worktree-NetworkX` | `docs/index.md`, `docs/networkx-validation.md` | **none** |
| `worktree-Folium` | none (0 commits ahead) | **none** |
| `docs/remaining-work-assessment` | `docs/remaining_work.md` | **none** |

This is not luck. The instrumentation work confined itself to
`src/flight_planner/pathfinding/`, its tests, its own experiment directory, and
the two doc files that describe the extension point it changed.

### The one live hazard: `docs/index.md`

`worktree-NetworkX` edits it. It is the single file in `docs/` that every new
document wants to touch, so it is where parallel doc work collides. Two
documents added in parallel both append to the same list, and git sees one
region changed twice.

This is why [evaluation-search-instrumentation.md](evaluation-search-instrumentation.md)
and this document are **not** linked from `docs/index.md`. `project_plan.md` is
not either, so project-management docs already sit outside that list. Whoever
lands last can add all the index entries in one edit, as one hunk, with no
conflict.

### The remaining T8 work splits cleanly

The deck is one 483-line file, but the evaluation-stage work lands in four
sections that are 15+ lines apart, which git's three-way merge handles as
independent hunks:

| Task | `slides/index.html` section | Other files | Conflicts with |
|---|---|---|---|
| Fill the comparison table | 323–337 | — | nothing |
| Big-O write-up | 339–353 | `docs/report.md` | nothing |
| Embed the runtime plot | 355–361 | — (the PNG is already committed) | nothing |
| Route map | 363–369 | new renderer, `docs/images/` | nothing |

Those are exact `<section>`…`</section>` boundaries, each a self-contained
slide. The narrowest gap between two of them is one line, which is close enough
that two people editing *adjacent* sections may see git ask for a merge — so if
two of these run at once, prefer the non-adjacent pairs (table + runtime plot,
or Big-O + route map).

Two rules make that hold:

1. **One owner per slide section.** Different sections of one HTML file merge
   fine; the same section does not.
2. **No global edits to the deck while parallel work is in flight.** A CSS
   change, a reflow, or a reformat rewrites every line and conflicts with all
   four tasks at once. Anyone needing one should land it alone, first.

### Two things to know before branching

- **`main` is one commit ahead of `origin/main`.** The from-scratch min-heap
  (`4b101fe`) is local only. Anyone branching from `origin/main` gets a tree
  where Dijkstra has no heap to run on. Push `main` first, or branch from local
  `main`.
- **Squash only commits unique to your branch, and never rewrite anything at or
  below the fork point.** This rule was learned expensively in this repository:
  squashing past a shared ancestor once made `git merge-base` fall back to a
  much older commit, and git then saw both sides as having independently written
  the same 1,093-line file. Rebase onto the primary tip regularly rather than
  once at the end, and squash at the moment of landing.

The full roadmap, critical path and per-person lane are in
`docs/remaining_work.md` on the `docs/remaining-work-assessment` branch (699
lines, §7 for the critical path). This section covers only merge mechanics.

## 10. Self-review record

Seven discrepancies were found by checking the plan against the repository
rather than against memory. Recorded so they are not re-introduced:

1. **The module split was not free.** `tests/flight_planner/test_dijkstra.py`
   imported `flight_planner.pathfinding.algorithms` by module path, so deleting
   that file broke it. An earlier draft claimed the move commit was a literal
   no-op — it would have gone red. Fixed by re-pointing the test at the whole
   subpackage with `pkgutil.iter_modules`, which is also a stronger test: it
   catches `heapq` reappearing in any algorithm module, including ones that do
   not exist yet.
2. **`adt/min_heap.py`'s docstring** named the same module path in prose, and
   went stale at the split.
3. **Early-return semantics were unspecified** ([§4](#4-the-api-as-built)). The
   unreachable case must keep its real counters.
4. **`cost` is not one unit** across the three algorithms.
5. **`on_push` has no natural priority in BFS** (D5).
6. **The lint gate reaches the experiment directory.** `ruff` excludes only
   `notebooks`, so `experiments/search-cost/plots.py` needs Google-style
   docstrings like any `src/` module.
7. **The size axis had to be V+E, not airports** ([§6](#6-experiment-design)) —
   found by measuring the narrowings rather than assuming they scaled together.
