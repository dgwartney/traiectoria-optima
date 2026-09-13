---
title: |
  Flight Route Planner\
  Where We Are
subtitle: |
  A point-in-time picture of the code, the documentation,
  and what is left — 12 September 2026
author: David Gwartney
---

# Where we are

**Read this first if you have been away from the repository.** It is a dated
snapshot, not a plan: it says what exists today, which branch it is on, whether
it has been verified, and what is left. The roadmap lives in
[`remaining_work.md`](remaining_work.md), now in `docs/`; the requirements live
in `term-project-info.pdf` at the repository root.

Everything below was measured on 12 September 2026 by running the commands in
[§9](#9-verifying-any-of-this-yourself), not recalled. Where a number is a
property of this machine rather than of the code, it says so.

## Contents

1. [The short version](#1-the-short-version)
2. [What is public right now](#2-what-is-public-right-now)
3. [What landed, and in which commit](#3-what-landed-and-in-which-commit)
4. [Where to start reading](#4-where-to-start-reading)
5. [What the code does today](#5-what-the-code-does-today)
6. [Three findings worth knowing before you read the code](#6-three-findings-worth-knowing-before-you-read-the-code)
7. [What is left, against the requirements PDF](#7-what-is-left-against-the-requirements-pdf)
8. [What the merge turned up](#8-what-the-merge-turned-up)
9. [Verifying any of this yourself](#9-verifying-any-of-this-yourself)

## 1. The short version

The library is done and the graded outputs are most of the way there. Today
produced 29 commits across five branches, and the three items that were the
whole gate two days ago — the from-scratch min-heap, expansion counting, and
NetworkX validation — are all closed.

| Instructor's stage | State |
|---|---|
| Stage 1 — Foundation | **Complete**, proposal submitted and graded. Graph statistics are now measured and written up — `experiments/graph-stats/`, report §2.5. |
| Stage 2 — Core algorithm | **Complete.** BFS, Dijkstra and A\* all work, are tested, and now agree with NetworkX on real queries. |
| Stage 3 — Stretch + features | **Code complete.** The min-heap is from scratch, `heapq` is gone from the package, A\* runs on our heap. The *written* admissibility argument is not done. |
| Stage 4 — Evaluation | **Mostly done.** Comparison table, runtime-vs-size plot, complexity write-up and route map all exist. The report's other sections and the deck do not. |

What is genuinely left is writing, not building: the report's prose sections,
the deck, the four rubric-named edge-case tests, and one
assembled demo. See [§7](#7-what-is-left-against-the-requirements-pdf).

**Everything described below is on `main`.** Five branches and four untracked
documents landed on 12 September in nine commits; the two largest were squashed
to one commit each. `main` is green: **768 tests pass** with the `notebooks`
dependency group installed, 697 pass and 4 skip without it, and `ruff check .`
is clean.

## 2. What is public right now

Everything in this document is on `main`, and `main` is pushed. Every link
below is live:

| Document | Read it for |
|---|---|
| [`docs/index.md`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/index.md) | The index — every document, grouped |
| [`docs/tutorial.md`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/tutorial.md) | Build one experiment end to end, in half an hour |
| [`docs/setup.md`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/setup.md) | Getting `uv run pytest` to pass, and the Colab lane |
| [`docs/flight_planner.md`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/flight_planner.md) | The package, layer by layer |
| [`docs/experiments.md`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/experiments.md) | Snapshots, catalogs, and reproducible results |
| [`docs/demos.md`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/demos.md) | Thirteen runnable scripts, one idea each |
| [`docs/report/`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/report/README.md) | The final report, one file per chapter — §1, §2, §6 and §7 written, plus appendices A–G; §3–§5 and §8–§11 outlined |
| [`docs/visualization.md`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/visualization.md) | The mapping layer's design record |
| [`docs/networkx-validation.md`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/networkx-validation.md) | How the algorithms are checked against NetworkX |
| [`docs/results-astar-consistency.md`](https://github.com/dgwartney/traiectoria-optima/blob/main/docs/results-astar-consistency.md) | The consistency finding, in full |

**One correction worth knowing if you read the docs before today.** Earlier
copies of `flight_planner.md` told you to implement `find_path` when writing a
new search algorithm. You now implement **`search`**, returning a
`SearchResult`; `find_path` is inherited. The published copy is current.

**There is still no rendered documentation site.** `make docs` builds mkdocs
locally; GitHub Pages is not configured, so documentation means GitHub links.

## 3. What landed, and in which commit

Nine commits, oldest first. Each is a fast-forward on the one before it, so the
history reads in order.

| Commit | What it holds |
|---|---|
| `75fc1e0` | `pathfinding/algorithms.py` split into one module per algorithm |
| `cd498c9` | `SearchResult` — what a search cost, not just what it found |
| `24c8676` | The instrumentation exported, documented and demonstrated |
| `f40ee82` | The `search-cost` experiment on the world network |
| `c48f86f` | How construction and search scale, and on what |
| `b12c081` | The committed experiments made findable; the `plots.py` pattern |
| `5d3f54b` | Report section 6 (complexity) and section 7 (empirical evaluation) |
| `e914b3b` | `flight_planner.viz`, the `route-map` experiment, `visualization.md` |
| `0e44b33` | `src/validation/`, two comparison experiments, three result documents |

The last two were each squashed from a worktree branch — four commits and seven
respectively — with the pre-squash history preserved under the
`backup/pre-squash-20260912-1704-*` tags, following the convention this
repository already uses.

**One environment gap surfaced by merging them**, and it is worth knowing
because it will bite anyone who clones and runs the suite: `flight_planner.viz`
needs `folium` and `pyproj`, which live in the `notebooks` dependency group, not
`dev`. A plain `uv sync` therefore cannot exercise the mapping layer. The viz
tests now skip rather than fail in that case, which is why a dev-only run
reports 697 passed and 4 skipped. To run everything:

```bash
uv sync --group notebooks && uv run pytest -q     # 768 passed
```

## 4. Where to start reading

If you have not touched the repository in a week, this order works:

1. **[`setup.md`](setup.md)** — get `uv run pytest` passing. Nothing else
   matters until that works.
2. **[`tutorial.md`](tutorial.md)** — seven steps from raw CSVs to a recorded
   experiment, with a Colab lane if you do not want a local checkout. This is
   the single best use of an hour, and it is current and public.
3. **[`flight_planner.md`](report/13-appendix-b-data-structures.md)** — the package, layer by layer.
   Read the local copy, not the public one ([§2](#2-what-is-public-right-now)).
4. **[`experiments.md`](experiments.md)** — snapshots, catalogs, experiments,
   and why a result records the data that produced it.
5. **[`demos.md`](demos.md)** — thirteen runnable scripts, one idea each. The
   fastest way to see any single feature work.

Then, depending on what you are picking up:

| If you are working on | Read |
|---|---|
| Anything touching the algorithms | [`design-search-instrumentation.md`](design-search-instrumentation.md) — why `search` replaced `find_path`, the eight decisions, and the seven discrepancies found in self-review |
| The evaluation, the plots, or §6/§7 of the report | [`evaluation-search-instrumentation.md`](evaluation-search-instrumentation.md) — how to re-run every number and what may legitimately differ |
| Correctness or the report's §5 | `results-networkx-parity.md` and `networkx-validation.md` (1,532 lines: seven options considered, one chosen) |
| A\*, admissibility, or the report's §4.3 | `results-astar-consistency.md` — start at [§6](#6-three-findings-worth-knowing-before-you-read-the-code) below |
| Maps or figures | `visualization.md` (1,606 lines) — four module-location options, the antimeridian problem, and what the prototype measured |
| Planning, ownership, or the board | [`remaining_work.md`](remaining_work.md) §7 for the critical path, §8 for lanes |

## 5. What the code does today

```
src/flight_planner/
  adt/min_heap.py        from-scratch array-backed binary heap; no heapq anywhere
  core/                  generic Vertex, Edge, Graph[V, E]
  geo/                   Point, Haversine, Vincenty
  pathfinding/           strategy.py, bfs.py, dijkstra.py, astar.py,
                         result.py, observers.py
  flights/               Airport, Route, FlightPlanner
  loaders/               CsvLoader
  experiments/           Snapshot, Catalog, Experiment
  viz/                   route maps, great circles, palettes   [Folium branch]
src/validation/          NetworkX oracle, behind our own Strategy   [NetworkX branch]
```

`grep -rn "import heapq" src/flight_planner/` returns nothing. That is the
stretch concept's hard requirement, and it holds.

**Six experiments exist**, each pinned to one of three frozen snapshots
(`2026-09-11-1528c4`, `2026-09-11-bb90a8`, `2026-09-12-3e4f9d`):

| Experiment | Asks | Branch |
|---|---|---|
| `sfo-bos-dijkstra` | Does narrowing to one airline change the route? | `main` |
| `shortest-vs-fewest` | What does skipping a stop cost? | `main` |
| `search-cost` | How much cheaper is informed search? | instrumentation |
| `networkx-parity` | Do we agree with NetworkX? | NetworkX |
| `astar-consistency` | Is the heuristic consistent, not just admissible? | NetworkX |
| `route-map` | One rendered route on a map | Folium |

Opening a snapshot re-hashes every file against its manifest. Cost on the world
network: 0.01 s to verify, 0.35 s to build the catalog, 0.04 s to build the
planner — so a live demo can afford it.

## 6. Three findings worth knowing before you read the code

**1. A\* needs a *consistent* heuristic, not merely an admissible one — and
nothing we have committed is wrong.** `AStar`'s docstring promises optimality
for an admissible heuristic, but the implementation closes each vertex on first
expansion, which requires the stronger *consistent* property
(`h(u) <= w(u,v) + h(v)` on every edge). The `astar-consistency` experiment
constructs a four-vertex counterexample where the shipped A\* returns a
suboptimal cost, and finds the same class of failure in seconds on random
graphs. It then checks the real heuristic across **658,470** checks on the
snapshot and finds it consistent, so every committed result stands. **This is
the strongest material available for the report's §4.3 admissibility argument** —
it is the graded claim, and we can now make it with a measured counterexample
rather than a textbook assertion.

**2. BFS is not uniformly cheaper than Dijkstra.** It answers a different
question — fewest hops, not shortest distance — and on some queries it expands
*more* nodes while returning a longer route. The simple "uninformed is
expensive" story does not survive contact with the numbers, and the write-up
should say so. Relatedly, `cost` is not one unit across the three algorithms:
BFS counts hops, the other two count kilometres. They are never summed.

**3. The extension point moved.** To add a search algorithm you now write
`search`, returning a `SearchResult`; `find_path` is inherited. Twenty-odd call
sites relied on the old `(cost, path)` tuple contract, which is why the split
commit was not the no-op it looked like. If you have local work against
`pathfinding/algorithms.py`, that file no longer exists — see the mapping table
in `networkx-validation.md`.

## 7. What is left, against the requirements PDF

Checked line by line against `term-project-info.pdf` — the "Term project
outputs" list on p. 4, the rules on p. 5, and the A1 entry on p. 6 — rather than
against our own internal plan, which asks for more than the rubric does.

| # | Item | Why it is required | Size |
|---|---|---|---|
| 1 | **The A\* admissibility argument, written out** | A1's stretch concept is "Dijkstra with your own min-heap **and** A\* with an admissible haversine heuristic", and outputs require it be "clearly **explained**". Highest graded weight of anything open. | Half a day. The evidence is already measured ([§6](#6-three-findings-worth-knowing-before-you-read-the-code)). |
| 2 | **The four rubric-named tests** | p. 5 names them: empty, single-element, cyclic/duplicate, disconnected. None is tested against `Graph` today — `test_graph.py` has five tests, all about construction. A1 also asks for a hand-built mini-graph test; there is none. | Small, independent, startable now |
| 3 | **Report prose** | §1, §2, §6 and §7 are written, and appendices A–G are in place. §3–§5 and §8–§11 are still bullet outlines. §8 and §5's NetworkX paragraph can be assembled from the appendices, which is where the result documents now live. | The long pole |
| 4 | ~~**Graph statistics**~~ | **Closed.** `experiments/graph-stats/` measures size, density, degree, reachability and components on the world snapshot; report §2.5 is written from its `results.json`. `core/graph.py` still has no stats method and does not need one — reachability is measured with the package's own `BFS` and a `SearchObserver`. | — |
| 5 | **One assembled demo** | p. 5: "A Jupyter notebook implementation is sufficient. (Alternatively, a command-line interface is sufficient; a web UI is never required or rewarded.)" Four experiment notebooks exist; none is a five-minute walkthrough of the three queries. | Small — see below |
| 6 | **The deck** | Required output. **Superseded: the deck is now built from the report chapters** by `make deck` — a reveal.js deck whose content is the `deck-slide` blocks inside the chapters, so it cannot drift from the prose the way the Google deck did. The first in-repo deck (`slides/index.html`) was deleted at `b0bb9cf` and is recoverable from `7d42b04`; `slides/images/` was kept because the experiments write those figures and the suite asserts them. What is left is authoring each slide as its chapter is written. | Moves with the chapters, not after them |
| 7 | **`docs/index.md` entries** | Every new document is unlinked, deliberately, to keep parallel branches from colliding on one file. Whoever lands last adds them all in one hunk. | Minutes |

**Not required, despite appearing in our internal plan:** a pinned large+medium
U.S. subset. The U.S. narrowing is our own choice against a catalog that says
"world airline network". The degree-distribution figure was also on this list —
the PDF asks for "basic statistics" and one visualization, and degree
distribution is project A4's requirement rather than ours — but it was built
anyway, in `experiments/graph-stats/`, because a table of degree counts does not
show a reader what heavy-tailed means and one chart does.

**Two open decisions, both cheap to make and expensive to defer:**

- ~~**Which deck is the deliverable?**~~ **Decided: the Google Slides deck.**
  The in-repo reveal.js deck is retired — see `slides/README.md` for what was
  removed and how to read it again. Its 36 TODOs evaporated with it, and item
  6 is now "port the measured numbers into Google Slides". The nine places the
  Google deck disagrees with the code are tracked once, together, in
  `report-deck-crosswalk.md` §3.
- **How is the demo built?** The experiment framework is the natural home — it
  already solves snapshot paths that resolve from a fresh clone or Colab, and
  `make experiment SLUG=...` scaffolds it. It should *not* be the `search-cost`
  notebook, which is a 25-cell measurement artifact; the demo should exercise
  the public API and read its numbers from
  `experiments/search-cost/results.json` rather than recompute them, so nothing
  on stage waits for a timing loop.

## 8. What the merge turned up

Two conflicts, both resolved by keeping material rather than choosing between
versions:

- **`tests/experiments/test_committed.py`** — the mapping branch and the
  instrumentation branch each registered a new experiment in the same test file.
  Purely additive; both class blocks kept.
- **`docs/report.md`** (since split into `docs/report/`) — the NetworkX branch had added a caveat to section 7's
  *outline* while section 7 was being written in prose elsewhere. Taking either
  side alone would have dropped something, so the written section was kept and
  the caveat carried into 7.6: NetworkX's `shortest_path` runs a *bidirectional*
  search, so of the three algorithms only the A\* row compares like with like.

Two rules made this cheap, and both were learned expensively in this repository:
**squash only commits unique to your branch, and never rewrite anything at or
below the fork point.** Squashing past a shared ancestor once made
`git merge-base` fall back to a much older commit, and git then saw both sides
as having independently written the same 1,093-line file.

## 9. Verifying any of this yourself

Nothing here needs to be taken on trust.

```bash
# The suite and the lint gate, from any branch
uv run pytest -q
uv run ruff check .

# The stretch concept's hard requirement
grep -rn "import heapq" src/flight_planner/     # must print nothing

# What is actually published
git ls-remote --heads origin

# Whether a branch would merge cleanly
git merge-tree --write-tree main <branch>

# Re-run the evaluation and compare against the committed results
uv run jupyter nbconvert --execute --to notebook --inplace \
  experiments/search-cost/explore.ipynb
git diff --stat experiments/search-cost/results.json
```

On that last one: node counts, growth exponents and graph sizes are
deterministic and must not move. Absolute milliseconds are a property of the
machine and will. `evaluation-search-instrumentation.md` §8 has the full table
of what may legitimately differ and what is a real failure.

## See also

- [`remaining_work.md`](remaining_work.md) — the roadmap this document
  summarises: compliance table, T1–T9 detail, critical path, per-person lanes
- [Tutorial](tutorial.md) — the end-to-end lane for a new reader
- [Final report](report/README.md) — one file per chapter, plus appendices A–G; §1, §2, §6 and §7 are written, the rest is the work
- `term-project-info.pdf` — the requirements, at the repository root
