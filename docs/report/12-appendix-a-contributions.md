# Appendix A. Contributions and Code Inventory

## A.1 Contributions

[`docs/project_plan.md`](../project_plan.md) proposed a three-way split of the
nine deliverables T1–T9 across DG, ASF and JL, with each member presenting the
work they built. That allocation did not survive contact with the term. The
repository record is unambiguous and is reproduced here rather than summarised,
because a contributions statement that disagrees with `git log` is worse than
none:

| | Commits | Blamed lines on the delivered tree |
|---|---|---|
| David Gwartney | 78 | 32,622 |
| ASF | 4 | 0 |
| JL | 0 | 0 |

```sh
git shortlog -sne                                    # the commit counts
git ls-files '*.py' '*.md' | while read -r f; do \
  git blame --line-porcelain -- "$f"; done | grep '^author ' | sort | uniq -c
```

ASF's four commits are early and their content has since been rewritten, which
is why the blamed-line count is zero rather than small. **Every deliverable in
this report was built by one author**, including the six T1–T9 items the plan
assigned elsewhere: the graph core and public API (T2), the test suite and its
edge cases (T4), BFS (T5), Dijkstra (T6), A\* and the admissibility argument
(T7), and the evaluation (T8).

Two consequences are worth stating plainly rather than leaving a reader to
infer them. The project plan's presentation split across three speakers cannot
be delivered as written. And the plan's "PR review before merging to `main`"
control never operated, which is the gap the automated checks were built to
cover: an independent NetworkX oracle (§5), randomized differential testing,
and the rule that every published figure names a checksummed snapshot. Those
were not chosen for elegance. They are what stands in for a second reader.

## A.2 What was built

The report argues about roughly a sixth of the code. This section accounts for
the rest, because a reader who has just finished §7 has no way to tell whether
the thing measured is 500 lines or 18,000.

**18,465 lines of Python** across `src/`, `scripts/` and `tests/`, of which the
installable `flight_planner` package is 5,181.

| Layer | Lines | What it is |
|---|---|---|
| `core/` + `adt/` + `pathfinding/` + `geo/` | **1,548** | **The graded from-scratch work — 30% of the package.** Adjacency-list digraph; array-backed binary min-heap with sequence tie-breaking and no `decrease_key`; three searches behind one Strategy interface; an Observer layer; two geodesic formulas and a memoizing decorator. `heapq`, `networkx` and `scipy` appear nowhere in it |
| `flights/` | 450 | Domain composition — `Airport`, `Route`, `FlightPlanner`, and the one multiple-inheritance decision in the project (§3) |
| `loaders/` + `experiments/` + `viz/` + package root | **3,183** | Infrastructure, and not boilerplate: `experiments/catalog.py` alone is 694 lines of narrowing, query and provenance logic |
| `src/validation/` | 1,336 | The NetworkX oracle, randomized differential testing, and the reopening detector. **The best-covered subsystem in the repository by ratio** — 1,349 test lines and 256 collected tests against 1,336 source lines. It is what found the A\* defect §4.3 reports |
| `src/data/` | 1,324 | The four-stage cleaning pipeline behind §2.3 |
| `src/demos/` | 1,415 | 14 runnable scripts, deliberately outside the wheel so they exercise the package's public re-exports rather than its internals |
| `scripts/` | 1,037 | Snapshot and experiment scaffolders, and the deck build. These know the repository's layout, which is why they are not package code |
| `tests/` | 7,171 | **644 test functions, 883 collected** with parametrization, across 49 files |

Two directories are in the tree and are **not** part of the delivered system:

- **`src/models/flight/` (504 lines)** — aircraft performance, an ISA
  atmosphere model, wind and payload-range. It has its own tests and nothing
  imports it. §10 treats it as the natural next step, and it is excluded from
  the system description in §3 for that reason.
- **`src/exercises/` (497 lines)** — coursework study code from the textbook,
  kept for reference. No part of the deliverable imports it.

## A.3 Reproducing the report

Everything in this document is built from the repository:

```sh
uv sync                            # the environment
uv run pytest                      # 883 tests
make report                        # this PDF
make vendor-reveal && make deck    # the presentation, from these same chapters
```

The seven committed experiments under `experiments/` each hold an
`experiment.toml` naming the snapshot they ran against and a `results.json`
holding their answer. [Appendix F](17-appendix-f-reproducibility.md) describes
that machinery and lists the snapshots. `tests/experiments/` re-derives the
committed answers, so a figure in this report that has drifted from the data
fails the test suite rather than going unnoticed.

| Artifact | Where |
|---|---|
| Repository | `github.com/dgwartney/traiectoria-optima` |
| The package | `src/flight_planner/`, and [Appendix B](13-appendix-b-data-structures.md) |
| Experiments and their recorded answers | `experiments/<slug>/results.json` |
| Snapshots | `data/snapshots/<id>/`, each with a checksum manifest |
| Figures | `docs/images/` (report) and `slides/images/` (deck), both written by experiment code |
