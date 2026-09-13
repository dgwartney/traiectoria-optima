---
title: |
  Flight Route Planner\
  Remaining Work Assessment
subtitle: |
  SJSU CMPE 180A\
  Fall 2026 — Prof. Sanja Damjanovic
author: "David Gwartney"
date: 2026-09-12
---

# Remaining Work Assessment

This document assesses what is left to complete on the term project, and who
owns it, measured against four sources:

| Source | What it is | Authority |
|---|---|---|
| `term-project-info.pdf` | The instructor's Week 5 term-project intro — A1 catalog entry, the four stages, the required outputs, and the library rules | **Governs.** This is the rubric. |
| `project_plan.md.pdf` | The plan actually submitted to the instructor (Google Doc export, 37 tasks) | The commitment of record |
| `docs/project_plan.md` (= `project_plan.pdf`) | A later in-repo revision with a T1–T9 deliverable table and named owners, written 2026-08-23, never submitted | The team's working plan |
| GitHub project board #2 | 37 issues mirroring the *submitted* plan | Now reassigned from the T1–T9 table (see §5) |

Where they conflict, the instructor's document wins. The three planning
documents are not the same, and the differences matter — see §2.

The assessment of *state* is based on the code and documents in the repository
at commit `fd475e1` (`main`, clean tree), plus the Google Slides deck exported
as `traiectoria-optima (2).pdf`, which lives outside the repository.

---

## 1. Summary

**The library is substantially built; the graded outputs are not.**

The `flight_planner` package is real, layered, documented, and covered by a
green test suite — 311 tests pass, `ruff check` is clean. BFS, Dijkstra, and A\*
all work. The snapshot/catalog/experiment framework goes well beyond anything
the rubric asks for.

What is missing is the stretch concept, the rubric's named test cases, all of
Stage 4, and the write-up. Stage 1 is close but not finished; Stage 2 is
complete except for library validation.

**Eight findings drive the remaining work:**

1. **The from-scratch min-heap does not exist, and that is the graded stretch
   concept.** `src/flight_planner/adt/min_heap.py:47` calls `heapq.heappush`;
   its own docstring admits it. `Dijkstra` and `AStar` also call `heapq`
   directly (`pathfinding/algorithms.py:75`, `:182`). The instructor's catalog
   is explicit — A1's stretch concept is "Dijkstra with **your own min-heap**"
   — and states that the stretch concept is "where most of the learning (**and
   grading weight**) sits." Nothing else on this list costs as many points.

2. **Nothing counts nodes expanded.** The problem statement the instructor
   wrote is "show how informed search (A\*) expands fewer nodes than uninformed
   search (BFS/Dijkstra) while returning the same answer." No algorithm is
   instrumented to report expansions, so the project's central claim cannot be
   produced today. A required Outcome — the BFS-vs-Dijkstra-vs-A\* comparison
   table — depends on it.

3. **NetworkX validation has never been started.** There is not one reference
   to `networkx` anywhere in the repository. This is not merely a team
   preference: "validated against a library reference" is the instructor's
   Stage 2 milestone, and the A1 entry names NetworkX specifically.

4. **No empirical runtime study and no visualization.** The rubric requires "at
   least one plot of time vs. input size" and "one visualization" / "a rendered
   route map." Neither exists as a committed artifact.

5. **The four test cases the rubric names are not tested.** The instructor
   requires "unit tests on small inputs with known answers (including empty,
   single-element, cyclic/duplicate, and disconnected cases)." None of the four
   is tested against the graph: `tests/flight_planner/test_graph.py` covers
   add-vertex, add-edge, outgoing edges and delegation, and nothing else.
   (`test_min_heap.py` has empty and duplicate cases, but that is the heap.)
   311 passing tests made this easy to miss. See §5.4.

6. **The final report is an empty outline.** `docs/report.md` is 83 lines of
   headings and bullet placeholders — no prose, no numbers, no figures.

7. **The presentation exists but asserts things the code does not do.** The
   Google Slides deck (20 slides) is polished and well ahead of the in-repo
   reveal.js deck, but its Min-Heap slide describes an array-backed heap with
   sift-up/sift-down and decrease-key, and its Dijkstra slide says "driven by
   our own from-scratch priority queue." Neither is true of `main` today. Its
   Core API slide shows `fewest_stops()` / `shortest_distance()` / `astar()`,
   which is not the real API (`find_shortest_route(origin, destination,
   algorithm=...)`), and carries a literal "TODO: confirm signatures against
   `src/`." See §6.

8. **Three planning documents disagree with each other.** The submitted plan
   has no deliverable table, no owners beyond Aastha Sharma-Flores, a *Goals*
   section consisting of one malformed bullet ("To understand and implement the
   Dykstra algorithms" — misspelled, and omitting BFS and A\*), and a *Roles and
   Responsibilities* section reading "Jake Lu — TBD / David Gwartney — TBD". The
   richer T1–T9 plan was written three days after submission and never sent. See §2.

**One concern is smaller than the plans suggest.** Both plans flag "is scoping
to U.S. airports acceptable?" as an open question against the catalog's "world
airline network." In fact `data/processed/airports.csv` holds 3,387 airports
across 200+ countries (US 613, CA 208, CN 178, BR 126, RU 114) and
`routes.csv` holds 66,332 routes — that is the full world dataset, matching the
catalog's "~3,300 airports, ~67,000 routes" almost exactly. The U.S. narrowing
happens only at *snapshot* time. The world graph is available whenever a
long-haul query set needs it, so this is a presentation choice, not a gap.

**One finding sits underneath all of the above.** Of 58 commits, **54 are David
Gwartney's, 4 are Aastha Sharma-Flores's, and none are Jake Lu's**. `git blame`
across every tracked source and document file returns 22,088 lines with a single
author: DG. Every deliverable nominally owned by someone else — the graph core,
BFS, Dijkstra, A\*, the entire test suite — was written by him. See §9.

**The board has been rebuilt to match reality.** It previously had 22 of 37
issues unassigned, Jake Lu on a single shared task, every item in `Backlog`,
and nothing ever closed. Now: all 37 assigned from the T1–T9 owner table, and
**eight verified complete, credited to their actual author, and closed** — all
eight to DG (§5.3). Four more that looked done do not survive a strict reading
and were left open with the gap recorded on the issue (§5.4).

| | Open | Closed |
|---|---|---|
| David Gwartney | 16 | **8** |
| Jake Lu | 10 | 0 |
| Aastha Sharma-Flores | 9 | 0 |
| Unassigned | 0 | — |

**Immediate actions, in order:**

1. Write the real min-heap and switch `Dijkstra`/`AStar` onto it (#8) — DG.
2. Add an expansion counter to all three algorithms (#16) — JL.
3. Add NetworkX cross-validation (#10) — JL.
4. Correct the Min-Heap, Dijkstra and Core API slides so the deck stops
   claiming what the code does not do (#22) — DG.
5. Write the four rubric-named edge-case tests (#5) — JL. Small, graded, and
   currently invisible behind 311 passing tests.

Steps 1–3 are the whole gate: every Stage 4 item waits on them, and steps 1
and 2 together are roughly a day of work. Step 5 is independent of all of them
and can start immediately.

---

## 2. The three planning documents

| | Submitted (`project_plan.md.pdf`) | In-repo (`docs/project_plan.md`) |
|---|---|---|
| Date | Submitted to instructor | 2026-08-23, three days later |
| Structure | 37 flat tasks in four stages | 9 deliverables T1–T9, mapped to slides |
| Owners | ASF on 12 tasks; everything else "TBD" | Every deliverable owned by DG, ASF or JL |
| Goals | One bullet: "To understand and implement the Dykstra algorithms" | Full problem statement, cost model, query-mode table |
| Roles | "Jake Lu — TBD", "David Gwartney — TBD" | Presenting split across all three, by slide |
| Sequencing | None | T1→T2 unblocks search; T3 before T6; T5–T7 before T8 |
| Cost model | Not defined | "Cheapest" defined as lowest total haversine distance |
| `heapq` | Not mentioned | Explicitly banned |

The git history shows the sequence plainly: commits through 2026-08-20 shaped
the submitted version, the 37 issues were created from it on 2026-08-21, and
`docs/project_plan.md` was rewritten into the T1–T9 form on 2026-08-23.

**Consequences.** The instructor holds a plan in which two of three team members
have no stated role and the stated goal misspells the algorithm. Everything that
makes the project look well-organized — the deliverable table, the ownership,
the sequencing, the cost-model reasoning — is invisible to them.

**Recommendation.** Do not leave two plans in circulation. Either resubmit or
append the T1–T9 version (fixing *Goals* and filling in *Roles*), or fold its
content into the final report's team-contributions appendix so the reasoning
lands somewhere graded. At minimum, fix the "Dykstra" typo before it is read.

---

## 3. Compliance with the instructor's required outputs

From `term-project-info.pdf`, §"Term project outputs" and the A1 catalog entry.

| Required output | State | Owner |
|---|---|---|
| Correct from-scratch structure + required algorithms | ⚠️ BFS, Dijkstra, A\* all correct and tested. The from-scratch **structure** — the min-heap — is not built. | DG (#8) |
| Stretch concept implemented and clearly explained | ❌ Not implemented. This carries the most grading weight of any single item. | DG (#8) |
| Unit tests + correctness on known small inputs, including **empty, single-element, cyclic/duplicate, disconnected** | ❌ **Audited: none of the four are tested against the graph.** 311 tests pass across 33 files, but `test_graph.py` covers only add-vertex, add-edge, outgoing edges and delegation. Also no known-route test and no route-level tie test. | JL (#5, #11) |
| Complexity analysis of **your own code** | ❌ The deck shows textbook complexity classes; nothing is derived from this implementation. | JL (#19) |
| Empirical runtime study — **at least one plot of time vs. input size** | ❌ No timing harness, no plot. | JL (#16, #17) |
| Data loading/validation + one visualization | ⚠️ Loading is solid. No visualization committed; `notebooks/view_routes.ipynb` and `folium-groups.ipynb` are the starting point. | JL (#18) |
| Jupyter notebook + slides + demo/presentation | ⚠️ Deck exists (§6); no assembled final notebook; no demo entry point. | DG (#20, #22, #33, #23) |
| Libraries restricted to I/O, plotting, validation | ✅ Honoured — `pandas`, `sqlite3`, `folium`, `matplotlib` are used only for those roles. | — |
| Stage 2: validated against a library reference (NetworkX) | ❌ Not started. | JL (#10) |
| Stage 1: one-page proposal **approved** | ❓ Submitted; approval unconfirmed. | DG (#6) |
| Stage 1: the U.S. subset finalized | ⚠️ The processed set is worldwide; the U.S. narrowing exists only as a snapshot, and that snapshot is `large_airport` while the task says large/medium. | DG (#1) |
| A1 Outcome: `RoutePlanner` supporting hops/distance queries | ✅ `FlightPlanner.find_shortest_route` with a pluggable algorithm Strategy. | — |
| A1 Outcome: BFS-vs-Dijkstra-vs-A\* comparison table | ❌ Blocked on expansion counters. | JL (#16, #17) |
| A1 Outcome: rendered route map | ❌ | JL (#18) |
| A1 Outcome: tests | ✅ | JL |

**One rule worth reading carefully.** The instructor's library rule permits
"dictionaries, sets, lists, deque, and (where noted) `heapq`" — so `heapq` is
not banned course-wide. But for A1 the stretch concept *is* the heap, so the
heap itself must be from scratch and Dijkstra must run on it. The team's own
plan went further and banned `heapq` outright. Either way, the current code
fails the requirement that matters.

**A note on effort allocation.** The rubric says "A Jupyter notebook
implementation is sufficient. (Alternatively, a command-line interface is
sufficient; **a web UI is never required or rewarded**.)" The reveal.js deck in
`slides/` is presentation tooling rather than a web UI, so it is not penalised —
but it is also not rewarded, and the Google Slides deck has already overtaken
it. Consider retiring `slides/index.html` rather than maintaining two decks.

---

## 4. Deliverable-by-deliverable assessment (T1–T9)

The T1–T9 numbering is from `docs/project_plan.md` and is internal to the team;
the instructor's structure is the four stages in §3.

| # | Deliverable | Owner | State | What is left |
|---|---|---|---|---|
| T1 | Cleaned dataset in SQLite, node/edge exports, stats + EDA charts | DG | **Partial** | `data/processed/airports.csv` (3,387), `routes.csv` (66,332), `flight_data.db`, three frozen snapshots. Missing: a pinned large+medium U.S. subset (the processed set is worldwide), the published dataset-statistics table, and EDA charts for slides 7/13. |
| T2 | `RoutePlanner` core: adjacency list, haversine weights, public API, graph statistics | ASF | **Mostly done** | `FlightPlanner`, `Graph`, `Vertex`, `Edge`, `Haversine`/`Vincenty`, `CsvLoader` implemented and documented. Missing: **reported graph statistics** — `core/graph.py` has no degree/density/component methods, so slides 14/15 have no numbers. |
| T3 | From-scratch array-backed binary min-heap (no `heapq`) | DG | **Not done** | `MinHeap` is a `heapq` wrapper with a tie-break counter. Needs real array-backed `_sift_up`/`_sift_down`; then `Dijkstra` and `AStar` switch onto it and `heapq` leaves `flight_planner`. |
| T4 | Test suite: mini-graph plus empty, single-element, cyclic/duplicate, disconnected | JL | **Partial — audited** | 311 tests pass and the package is well covered, but **none of the four rubric-named cases are tested against the graph**, there is no known-route test, and route-level ties are untested. Then the testing/validation slide. |
| T5 | BFS fewest-stops with reconstruction, validated against NetworkX | JL | **Half done** | BFS works (`algorithms.py:94`) with predecessor-map reconstruction, and is tested. NetworkX cross-validation not started. |
| T6 | Dijkstra on our own min-heap, validated against NetworkX | ASF | **Half done** | Dijkstra works and is tested, but runs on `heapq` — so it does not satisfy the deliverable as written. NetworkX validation not started. |
| T7 | A\* with haversine heuristic + written admissibility argument | ASF | **Mostly done** | A\* works (`algorithms.py:142`), tested, demonstrated in `src/demos/astar_example.py`. Admissibility is asserted in docstrings and `docs/graph-algorithms-notes.md`; the written argument for slide 19 and report §4.3 is unwritten. Also must move off `heapq`. |
| T8 | Evaluation: comparison table (nodes expanded + runtime), runtime-vs-size plot, Big-O write-up, rendered route map | JL | **Not started** | Everything. The experiments framework is the right vehicle — `experiments/shortest-vs-fewest/` already compares Dijkstra against BFS over three pairs and records to `results.json`. A three-way benchmark experiment is the natural shape. |
| T9 | Runnable notebook/CLI + live demo, assembled deck, final report | DG | **Partially started** | Google Slides deck is real but substantively incomplete and partly inaccurate (§6). Report is an outline. No interactive query entry point — `argparse` appears only in `scripts/new_snapshot.py` and `scripts/new_experiment.py`, which are authoring tools. No assembled final notebook. |

---

## 5. GitHub board: assignment and status

### 5.1 What changed

The board previously reflected the *submitted* plan, where 22 of 37 issues had
no owner and Jake Lu was named on exactly one shared task. All 37 issues have
now been reassigned from the T1–T9 owner table in `docs/project_plan.md`.

| Assignee | Open | Closed | Open issues |
|---|---|---|---|
| David Gwartney (`dgwartney`) | 16 | **8** | 1, 6, 8, 20, 21, 22, 23\*, 29, 30, 31, 32, 33, 34\*, 35, 36\*, 37 |
| Jake Lu (`jakelyu`) | 10 | 0 | 5, 10, 11, 16, 17, 18, 19, 23\*, 34\*, 36\* |
| Aastha Sharma-Flores (`aastha-csf`) | 9 | 0 | 4, 9, 13, 14, 15, 23\*, 27, 34\*, 36\* |
| Unassigned | 0 | — | — |

DG's eight closures are the eight tasks in §5.3; six of them were reassigned to
him from ASF or JL on the evidence of `git blame` before closing.

\* shared across all three: #23 live demo, #34 peer code review, #36 Q&A prep.

Five issues changed hands so the board matches the plan:

| Issue | Was | Now | Why |
|---|---|---|---|
| #7 Implement BFS | ASF | JL | T5 is JL's |
| #11 Tests for known routes / unreachable / ties | DG | JL | T4 is JL's |
| #19 Big-O complexity analysis | ASF | JL | Part of T8 |
| #20 Assemble the final notebook | ASF | DG | Part of T9 |
| #33 CLI / notebook query widget | ASF | DG | Part of T9 |

The lanes now read cleanly: **ASF owns the graph core and the search
algorithms, JL owns testing and the entire evaluation, DG owns the data, the
min-heap, and everything that ships.**

### 5.2 Status fields are still stale

Eight issues are now closed (§5.3), but the board's *Status* single-select was
never maintained: every remaining item reads `Backlog` except #33
(`In progress`, though no work on it exists in `main`). Closing state and
Status now disagree. Either set Status from the issue state or stop using the
field — two sources of truth is worse than one.

### 5.3 Issues closed, and who actually completed them

Eight issues have been verified complete against the *exact wording* of each
task, reassigned to the person `git blame` shows did the work, and closed. In
all eight that person is **David Gwartney** — 100% of the surviving lines in
every cited file are his (§9).

| # | Task | Was assigned | Evidence |
|---|---|---|---|
| 2 | Haversine edge weights | ASF | `geo/haversine.py` (39/39 DG), `Route` weights, distances in `csv_loader.py`; `test_haversine.py`, `test_loader.py`. Commits `be3eb98`, `4313de0`, `ba6aca5` |
| 3 | `RoutePlanner` adjacency list | ASF | `core/graph.py` (98/98), `flights/planner.py` (86/86), `csv_loader.py` (374/374); `test_graph.py`, `test_flight_planner.py`. Commits `be3eb98`, `4313de0` |
| 7 | BFS fewest-stop routing | JL | `algorithms.py:94` — queue, visited set, predecessor map, reconstruction; `test_bfs.py`. Commit `4313de0` |
| 12 | Haversine admissible heuristic | ASF | `geo/haversine.py` + `Point.distance_to` + `geo/memoized.py`, consumed at `algorithms.py:142`; `test_astar.py`, `test_memoized.py`. Commits `4313de0`, `e7dd78a` |
| 24 | pytest runner + CI-style command | JL | `pytest` dev dependency, `tests/` mirrors `src/`, `[tool.pytest.ini_options]` sets `testpaths`/`pythonpath`; 311 passed. Issue body already recorded Status: Done |
| 25 | ruff lint/format checks | DG | `[tool.ruff]` + lint rules + pydocstyle + per-file ignores; `ruff check .` clean |
| 26 | `RoutePlanner` public API design | ASF | `find_shortest_route(origin, destination, algorithm=...)` with pluggable Strategy, documented in `docs/flight_planner.md` and the package README |
| 28 | `docs/data.md` final cleaned schema | DG | §5 "The processed dataset" — transform description, `airports.csv`/`routes.csv` column tables, "What gets dropped", kept distinct from the raw schemas in §1–2 |

### 5.4 Four that look done but are not

An earlier draft of this document listed these as closeable. On a strict reading
of each task's own wording they are not, and they have been left open with the
gap recorded on the issue:

| # | Task | What is actually missing |
|---|---|---|
| 1 | Finalize U.S. airport subset, export nodes/edges | `airports.csv` is the **world** set (3,387 airports, 200+ countries); the U.S. narrowing happens only at snapshot time, and that snapshot is `large_airport` only while the task asks for **large/medium**. The build also moved from `flight_data.db` export to pandas (`39875ac`), changing the stated mechanism |
| 5 | Unit tests on a hand-built mini-graph | **None of the four rubric-named cases are tested against the graph** — no empty graph, no single-vertex graph, no cyclic/duplicate edge, no disconnected graph. `test_min_heap.py` has empty/duplicate cases, but that is the heap |
| 11 | Tests for known routes, unreachable airports, ties | Unreachable is covered in all three algorithms. **Known routes** are not — the tests use a synthetic A/B/C/D graph, and the textbook network lives in `src/demos/book_example.py`, a demo rather than a test. **Ties** are covered only in the heap, not at the route level |
| 30 | Shared task tracker | The board exists, mirrors all 37 tasks, and now has owners — but the task also asks for **due dates**, and none are set |

Note that #5 and #11 are not bookkeeping quibbles: the four edge cases in #5 are
named explicitly in the instructor's required-outputs list (§3), so they are
graded.

### 5.5 Full task table

| # | Task | Owner | Board status | Actual state |
|---|---|---|---|---|
| 1 | Finalize U.S. airport subset, export nodes/edges | DG | Backlog | **Partial** — processed set is worldwide; snapshot is large-only (§5.4) |
| 2 | Compute haversine edge weights | DG | **Closed** | **Done** — `geo/haversine.py`, `Route` weights |
| 3 | Build `RoutePlanner` as adjacency list | DG | **Closed** | **Done** — `core/graph.py`, `flights/planner.py` |
| 4 | Report basic graph statistics | ASF | Backlog | **Done** — `experiments/graph-stats/`; size, density, degree, reachability and components recorded in its `results.json` and written up in report §2.5. No stats API was added: the notebook measures reachability with the package's own `BFS` through the observer seam |
| 5 | Unit tests on a hand-built mini-graph | JL | Backlog | **Not done** — none of the four rubric cases tested on the graph (§5.4) |
| 6 | Draft and submit the one-page proposal | DG | Backlog | **Submitted; approval unconfirmed** |
| 7 | Implement BFS | DG | **Closed** | **Done** — `algorithms.py:94` |
| 8 | From-scratch binary min-heap | DG | Backlog | **Not done** — wraps `heapq` |
| 9 | Dijkstra using the custom heap | ASF | Backlog | **Partial** — Dijkstra done, uses `heapq` |
| 10 | Validate BFS/Dijkstra against NetworkX | JL | Backlog | **Not started** — no `networkx` anywhere |
| 11 | Tests for known routes, unreachable, ties | JL | Backlog | **Partial** — unreachable only; no known-route or route-tie test (§5.4) |
| 12 | Haversine admissible heuristic | DG | **Closed** | **Done** — `Point.distance_to`, `Memoized` |
| 13 | A\* using custom heap + heuristic | ASF | Backlog | **Partial** — A\* done, uses `heapq` |
| 14 | Secondary queries (mode switch, nearest-airports) | ASF | Backlog | **Partial** — mode switch exists via the algorithm Strategy; no nearest-airports lookup |
| 15 | Argue/verify admissibility | ASF | Backlog | **Not done** — asserted, never argued |
| 16 | Benchmark BFS vs Dijkstra vs A\* | JL | Backlog | **Not started** |
| 17 | Runtime plot + nodes-expanded table | JL | Backlog | **Not started** — blocked on #16 |
| 18 | Render one route on a map | JL | Backlog | **Not started for the deliverable** |
| 19 | Big-O complexity analysis | JL | Backlog | **Not done** — deck shows textbook values only |
| 20 | Assemble the final Jupyter notebook | DG | Backlog | **Not started** |
| 21 | Write the final report | DG | Backlog | **Outline only** |
| 22 | Prepare presentation slides | DG | Backlog | **Partial and partly inaccurate** — §6 |
| 23 | Prepare and rehearse the live demo | all | Backlog | **Blocked** on #33 |
| 24 | pytest runner + CI-style command | DG | **Closed** | **Done** — every clause of the task text satisfied |
| 25 | ruff lint/format checks | DG | **Closed** | **Done** — configured, `make lint` clean |
| 26 | Design the `RoutePlanner` public API | DG | **Closed** | **Done** — `docs/flight_planner.md`, package README |
| 27 | Document airport/route edge cases | ASF | Backlog | **Partial** — data cases in `docs/data.md`; algorithmic cases unwritten |
| 28 | Update `docs/data.md` with final schema | DG | **Closed** | **Done** — `docs/data.md` §5 |
| 29 | Track project risks/blockers | DG | Backlog | **Not started** |
| 30 | Set up a shared task tracker | DG | Backlog | **Partial** — no due dates (§5.4) |
| 31 | Regular team check-in cadence | DG | Backlog | **Unknown** |
| 32 | Define and agree a git workflow | DG | Backlog | **Partial in practice**, nothing written down |
| 33 | CLI / notebook query widget | DG | In progress | **Not started in `main`** |
| 34 | Peer code review pass | all | Backlog | **Not started** — no PR has ever been opened |
| 35 | Dry-run the notebook end-to-end | DG | Backlog | **Not started** — depends on #20 |
| 36 | Q&A talking points | all | Backlog | **Not started** |
| 37 | Confirm deliverables against the rubric | DG | Backlog | **Not started** — §3 is a starting point |

---

## 6. The presentation

The deck was built in Google Slides outside the repository
(`traiectoria-optima (2).pdf`, 20 slides). It is substantially better designed
than the in-repo reveal.js deck and should be treated as the real one.

**What is strong.** The traveler's-dilemma framing with a concrete persona; the
explicit "Network Abstractions & Simplifications" slide, which pre-empts the
obvious question about why real fares and weather are absent; the three-mode
query table; the worked SJC→JFK walkthroughs for BFS, Dijkstra and A\* on the
same four-node network, which lets the audience see the three algorithms make
different choices on identical data; a correct references slide.

**What must be fixed — accuracy.** These slides assert capabilities the code
does not have, and a reader of the repository will notice:

- **Min-Heap From Scratch** describes array representation, iterative sift-up
  and sift-down, and "Decrease-Key Optimizations... resolving the standard
  [TODO] requirement." None of that exists — `MinHeap` wraps `heapq`.
- **Dijkstra** claims it is "driven by our own from-scratch priority queue."
  It is driven by `heapq`.
- **System Design** says the graph is "built entirely from scratch utilizing a
  high-performance adjacency list" — this one is true — but the same panel
  attributes the min-heap to Dijkstra, inheriting the same problem.
- **Core API** shows `fewest_stops(src, dst)`, `shortest_distance(src, dst)`,
  `astar(src, dst)`. The real API is
  `find_shortest_route(origin, destination, algorithm=...)` with the algorithm
  as a pluggable Strategy — a better design than the slide, and worth showing
  accurately. The slide still carries "# TODO: confirm signatures against src/".

  The fastest fix for all four is to do the work (#8) rather than soften the
  slides; the deck is describing the right design, just ahead of the code.

**What is missing — substance.**

- **Empirical Runtime Study** has three complexity-class descriptions and no
  measured data. The rubric requires a plot of time vs. input size.
- **No BFS-vs-Dijkstra-vs-A\* comparison table** anywhere in the deck — a named
  A1 Outcome, and the project's headline claim.
- **No rendered route map.** There is a slide about Folium and ipyleaflet as
  technologies, but no actual route on an actual map. Another named Outcome.
- **No testing/validation slide**, which the team's own plan calls for as a
  "new slide" and which the rubric's four required test cases deserve.
- **Dataset** carries "[TODO — visual] TODO: dataset snapshot — row counts,
  columns used, node/edge after cleaning" — those numbers exist today (3,387
  airports, 66,332 routes) and can be filled in immediately.
- **No "What We Learned" content** and no deliverables checklist, though the
  agenda promises the former.
- The **agenda numbering is broken** — four items are labelled "05".
- **References** cite NetworkX "(validation and visualization only)", which is
  not yet true of any code.

**Two decks now exist.** `slides/index.html` (39 reveal.js sections, six `TODO`
placeholders) and the Google Slides deck cover the same ground. Maintaining both
is waste, and only one gets presented. Recommend retiring the reveal.js deck.

---

## 7. The critical path

Ordered so nothing waits on anything that is not already moving.

**Step 1 — Build the real min-heap (#8, DG).**
Rewrite `MinHeap` with a real array and explicit `_sift_up`/`_sift_down`,
keeping the existing `push`/`pop`/`peek`/`__len__` interface so
`tests/flight_planner/test_min_heap.py` still applies. Then switch `Dijkstra`
and `AStar` onto it and delete the `heapq` import from `flight_planner`. The
existing algorithm tests are the safety net. *This is the highest-weight item
on the rubric and it is currently the deck's biggest factual exposure.*

**Step 2 — Instrument expansions (#16, JL).**
Have each algorithm report how many vertices it expanded — a third tuple
element or a small result object. One change; unblocks the entire evaluation.

**Step 3 — NetworkX cross-validation (#10, JL).**
Add `networkx` as a dev dependency, sample N airport pairs from a snapshot,
compare hop counts (BFS) and distances (Dijkstra), and report agreements and
disagreements. Naturally an experiment directory, so the numbers land in a
`results.json` next to the snapshot that produced them.

**Step 4 — The benchmark experiment (#16, #17, #19, JL).**
With steps 1–3 done, one experiment produces the comparison table, the runtime
measurements, and the runtime-vs-input-size series in a single recorded run.
Follow the shape of `experiments/shortest-vs-fewest/`. Run it on the **world**
graph for the long-haul queries the catalog asks about, not just the U.S.
snapshot.

**Step 5 — The rubric's edge-case tests (#5, #11, JL).**
Independent of steps 1–4 and startable today: empty graph, single-vertex graph,
cyclic/duplicate edge, and disconnected graph, tested against `Graph` by name;
plus a known-route test (the textbook network already exists in
`src/demos/book_example.py` and can be lifted into a test) and a route-level
tie test. Small, and explicitly graded.

**Step 6 — Visualization and graph statistics (#4 ASF, #18 JL).**
Render one route to a map image for the deck. The graph-statistics half is
**done**: `experiments/graph-stats/` measures size, density, degree,
reachability and components on the world snapshot, and report §2.5 is written
from its `results.json`. Slides 14/15 still need the numbers ported across; the
two figures are already rendered for a dark surface in `slides/images/`.

**Step 7 — Demo surface (#33, DG).**
Build the interactive query entry point — origin, destination, mode. A CLI is
explicitly sufficient per the rubric.

**Step 8 — Write-up (#15 ASF; #20, #21, #22, #35, #37 DG; #23, #36 all).**
Fill the chapters in `docs/report/` with the numbers from steps 2–6, correct and complete the
deck, assemble the final notebook, dry-run it in a fresh environment, then
rehearse.

### Polish items, found in passing

Not board tasks and not blocking anything. Recorded here so they are not
rediscovered late, and so the report-polish pass in step 8 has a list to work
from.

| Item | Found | What to do |
|---|---|---|
| **Report figures float away from their references.** In the assembled PDF, figures land at the next available LaTeX float slot rather than near the prose that introduces them. Chapter 2 runs pages 4–7 with its degree prose on 4–5 and both figures on 6 and 7; Chapter 7's two behave the same way. | 2026-09-13, reviewing §2.5 | Either add `\usepackage{float}` to `docs/templates/doc-header.tex` and set `H` placement, which pins every chapter's figures where they are written, or move the references so the prose flows into each float. Whole-document typesetting, so it belongs to a pass over the assembled report rather than to one chapter. Verify with `make report` and check which page each figure lands on relative to its reference. |

---

## 8. David Gwartney's lane

**8 closed, 16 open.** The closures are all of §5.3 — every one verified
against the task's own wording and credited on the evidence of `git blame`.

### Unblocked and urgent — one item

**`#8`, the from-scratch min-heap.** This is your critical-path item and the
project's. It is the highest-weight thing on the rubric, it is what four slides
already claim exists (§6), and it gates T3, T6 and T7. Commit `af42a64` already
landed the finished interface and 115 lines of passing tests, so what remains is
replacing four `heapq` calls with `_sift_up`/`_sift_down` over `self._entries`.
Nothing else you own should start before it.

### Startable today — eight items, none hard

| # | Task | Note |
|---|---|---|
| 1 | Finalize the U.S. subset | Pin a large+medium U.S. snapshot; the machinery already exists, it is a `Catalog` narrowing and a `make snapshot` |
| 22 | Slides | The Dataset slide's TODO can be filled from `data/processed/` today (3,387 airports, 66,332 routes). The factual corrections wait on #8 |
| 21 | Final report | Sections 1–3, 5 and 9–11 need no benchmark data |
| 33 | CLI query widget | Start after #8; it is the demo's spine, and a CLI is explicitly sufficient per the rubric |
| 29 | Risk log | A short markdown file — §10 is a starting draft |
| 31 | Check-in cadence | A short markdown file |
| 32 | Git workflow | A short markdown file; also see #34 — no PR has ever been opened |
| 30 | Task tracker | Only due dates are missing |
| 6 | Proposal approval | An email |

### Blocked on Jake Lu's Stage 4 — five items

`#20` notebook · `#21` report (the data-bearing half) · `#22` slides (the
evaluation half) · `#35` dry-run · `#37` rubric check. All five need the numbers
from steps 2–4 and 6. Build the structure of each now so only numbers are
missing later.

### Shared, late — three items

`#23` demo rehearsal · `#34` peer review pass · `#36` Q&A prep.

### Suggested order

**#8** → the deck's factual gaps and Dataset slide (#22) → #1 snapshot → #33 CLI
→ the data-free report sections (#21) → the process files (#29, #31, #32, #30)
while waiting on Stage 4 → #20, #35, #37 last.

**The honest read on schedule.** Fourteen of your sixteen open issues are
either small or waiting on someone else. The project's exposure is not your
workload — it is that Stage 4 sits entirely with a teammate who has never
committed to this repository (§9). Plan #20, #21, #22 and #37 on the assumption
that you may have to produce the benchmark numbers yourself.

---

## 9. Contribution analysis: what has actually landed, and from whom

The sections above assess *what exists*. This one assesses *who built it*,
from `git log` and `git blame` across the 58 commits between 2026-08-14 and
2026-09-12.

### 9.1 The headline

**David Gwartney has written essentially all of the committed project.**

| Measure | DG | ASF | JL |
|---|---|---|---|
| Commits | **54** | 4 | **0** |
| Surviving lines, all tracked `.py`/`.md`/`.toml`/`.html`/`.sql`/`Makefile` | **22,088 (100%)** | 0 | 0 |
| Surviving lines including notebooks | **27,979 (100%)** | 0 | 0 |
| Files with any surviving authorship | **all** | none | none |

`git blame` over every tracked source and document file returns a single
author. There is no file in this repository, of any kind, with a line that
anyone other than David Gwartney wrote and that still survives.

### 9.2 The other two contributors, precisely

**Aastha Sharma-Flores — 4 commits, 0 surviving lines.** All four touched
`docs/project_plan.md` and nothing else:

| Commit | Date | Effect |
|---|---|---|
| `e73d2cc` | 2026-08-20 | "Added my name next to tasks I'm interested in" — 13 lines changed |
| `2cb8f4b` | 2026-08-20 | merge commit, no content |
| `1973655` | 2026-08-20 | "Added my name next to tasks" — +58 lines |
| `483c5c2` | 2026-08-20 | "Revert 'Added my name next to tasks'" — −58 lines |

The third commit was reverted by the fourth. The first was superseded when the
plan was rewritten into its T1–T9 form on 2026-08-23 (`6a239eb`, `21bd5fa`).
`git blame docs/project_plan.md` today returns 105 lines, all DG.

The lasting contribution of those commits is nonetheless real and should be
credited: **the task-interest markings are the origin of every "ASF" in the
plan's owner table**, and therefore of the assignment structure this document
uses. It is a planning contribution, not a code one.

**Jake Lu — 0 commits.** No commits on `main`, none on
`feature-in-process-work-nodata`, no branches, no PRs. There is no git record of
any contribution.

### 9.3 Ownership on paper vs. authorship in fact

Every deliverable nominally owned by someone else was written by DG:

| Deliverable | Plan owner | Who wrote it | Evidence |
|---|---|---|---|
| T2 `RoutePlanner` graph core | ASF | DG | `core/graph.py` 98/98, `flights/planner.py` 86/86, `geo/haversine.py` 39/39 — commits `be3eb98`, `4313de0` |
| T4 Test suite | JL | DG | `tests/` 3,196 lines, 100% DG — commits `de2fc61`, `658b525`, and tests in every feature commit |
| T5 BFS | JL | DG | `pathfinding/algorithms.py` 216/216, `test_bfs.py` 34/34 — commit `4313de0` |
| T6 Dijkstra | ASF | DG | same file; `test_dijkstra.py` 34/34 |
| T7 A\* + heuristic | ASF | DG | same file; `test_astar.py` 40/40; `geo/memoized.py` — commits `4313de0`, `e7dd78a` |
| T1 Dataset | DG | DG | `src/data/` 1,319 lines — commits `6798c68`, `1c15924`, `0a1cfb5`, `e080749`, `d3244be`, `ba6aca5` |
| T3 Min-heap | DG | DG | `adt/min_heap.py` 101/101 + `test_min_heap.py` 115/115 — commit `af42a64` |
| T9 Notebook/deck/report | DG | DG | `docs/` 5,685 lines, `slides/index.html` 483/483, `docs/report.md` 83/83 |
| T8 Evaluation | JL | — | nothing exists |

### 9.4 Where DG's 27,979 lines went

| Area | Lines | Deliverable |
|---|---|---|
| `notebooks/` | 10,608 | T1 EDA, T8 visualization groundwork |
| `docs/` | 5,685 | T9, plus the tutorial and experiment model |
| `tests/` | 3,196 | **T4 — JL's deliverable** |
| `src/flight_planner/` | 3,062 | **T2, T3, T5, T6, T7** |
| `src/data/` | 1,319 | T1 |
| `src/demos/` | 994 | T9 |
| `scripts/` | 710 | tooling (unplanned) |
| `experiments/` | 646 | tooling (unplanned) |
| `slides/` | 547 | T9 |
| `src/models/`, `src/exercises/`, `src/sql/`, other | 1,212 | background/exploratory |

Roughly **7,900 lines of the package, tests and data pipeline** are the graded
implementation; the rest is documentation, notebooks and exploratory work.

### 9.5 On #8, the min-heap

DG's own critical-path item is further along than §4 implies. Commit `af42a64`
("Add a stubbed `MinHeap` ADT... Implement `MinHeap` and cover it with tests")
landed a complete, documented, generic priority queue with insertion-order
tie-breaking and 115 lines of tests — the *interface* is finished and the test
suite that will validate the real implementation already exists and passes.
What is missing is only the internals: replacing four `heapq` calls with
`_sift_up`/`_sift_down` over `self._entries`. The docstring says so explicitly.
This is a smaller job than starting from nothing, and the tests are the
safety net.

### 9.6 Caveats

This analysis measures **committed work in this repository**, which is not the
same as total effort:

- The Google Slides deck (§6) was built outside git, and its PDF metadata names
  no author. Whoever built it did substantial design work that this analysis
  cannot see or credit.
- The submitted project plan was written in Google Docs; the same applies.
- Review, discussion, debugging help and planning conversations leave no commit.
- `git blame` credits surviving lines. Work that was written, superseded and
  replaced disappears from it — which is how ASF's plan edits net to zero
  despite having genuinely shaped the plan.

What the analysis does establish firmly is that **all code, all tests, all
documentation and both in-repo decks were authored by DG**, and that no
algorithm, test or data-pipeline work has ever been committed by anyone else.

### 9.7 What to do with this

Three practical consequences:

1. **The report's team-contributions appendix (`docs/report/12-appendix.md`) has
   to be written honestly.** The instructor requires that every member presents,
   and the appendix is where contribution is declared. Write it from the record.
2. **The reassignment in §5 is a forecast, not a description.** It assigns JL 12
   issues and ASF 13 on the strength of a plan neither has committed against.
   Confirm it with both directly before the Stage 4 critical path depends on it.
   If it cannot be confirmed, DG should re-plan on the assumption of building
   Stage 4 alone — which is feasible but changes the schedule materially.
3. **Presenting is a separate risk.** The rubric requires every member to
   deliver a portion. ASF and JL are slated for slides covering work they did
   not write. That needs rehearsal time, not just assignment.

---

## 10. Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| The deck claims a from-scratch heap the code lacks | This is a *correctness* exposure in front of the instructor, on the item carrying the most grading weight | Step 1 (#8) — fix the code, not the slide |
| Stage 4 is one person's critical path | JL owns #16–#19; nothing in the report, notebook or deck can finish without them, and he has been effectively unassigned until today | Confirm the reassignment with him directly before relying on it |
| Two plans in circulation, and the submitted one is the weaker | The instructor's copy has "Dykstra" as the stated goal and "TBD" as two-thirds of the roles | §2 — resubmit, append, or fold into the report |
| NetworkX validation absent | Explicitly required by the rubric's Stage 2, not optional | Step 3 (#10) |
| 311 passing tests concealed a graded gap | The four rubric-named edge cases are untested, and a green suite made that invisible until audited. Other "done" claims in this project deserve the same scrutiny | Step 5 (#5, #11); §5.4 shows the audit method |
| No PRs, no code review (#34) | The plan commits to "PR review before merging to `main`"; every commit so far went straight to `main` | Route steps 1–5 through PRs |
| Board *Status* field now contradicts issue state | Eight issues are closed but still read `Backlog`; #33 reads `In progress` with no work in `main` | §5.2 — drive Status from issue state, or drop the field |
| Two decks maintained in parallel | Duplicated effort on the one deliverable that is already behind | Retire `slides/index.html` |
| `feature-in-process-work-nodata` has diverged far from `main` | 149 files changed, including large deletions | Decide whether it is live; delete if abandoned |
| Office-hours question 1 still open | Whether distance-as-cost satisfies "cheapest" is still unconfirmed and is baked into every number | Confirm, or state the assumption explicitly in the report |

Office-hours question 2 (U.S. scoping) can be closed by the team: the world
dataset is already processed and loadable, so the long-haul benchmark can run
on it.

---

## 11. What was verified, and how

Everything above is anchored to commit `fd475e1` and the four source documents:

- `uv run pytest -q` → **311 passed**
- `uv run ruff check .` → **All checks passed**
- `grep -rn "heapq" src/flight_planner` → `adt/min_heap.py:17,47`,
  `pathfinding/algorithms.py:75,182`
- `grep -rn "networkx"` across `*.py`, `*.toml`, `*.md`, `*.ipynb` → **no matches**
- `data/processed/airports.csv` → 3,387 rows, 200+ countries (US 613, CA 208,
  CN 178, BR 126, RU 114); `routes.csv` → 66,332 rows
- `wc -l docs/report.md` → 83 lines, headings and bullets only
- `grep -c "<section" slides/index.html` → 39, six stubbed with `TODO`
- `pdftotext` on `traiectoria-optima (2).pdf` → 20 slides; §6 quotes it directly
- `pdftotext` on `project_plan.md.pdf` and `project_plan.pdf` → §2 compares them
- `pdftotext` on `term-project-info.pdf` → §3 quotes the A1 catalog entry,
  the four stages, and the required-outputs list
- `gh issue list` → 37 issues, **0 closed**; after reassignment, **0 unassigned**
  (DG 16 open / 8 closed, JL 10 open, ASF 9 open)
- `ls .github` → does not exist (no CI)
- `gh issue close` → 8 issues verified clause-by-clause, reassigned to their
  actual author and closed: #2, #3, #7, #12, #24, #25, #26, #28
- `grep -rn "def test_"` over `tests/flight_planner/` → no empty-graph,
  single-vertex, cyclic/duplicate-edge or disconnected-graph test exists; the
  only `empty`/`duplicate` cases are in `test_min_heap.py`

---

*This assessment reflects the repository at `fd475e1` and the GitHub board as of
2026-09-12. The board was modified in the course of writing it: all 37 issues
assigned, and eight closed. Re-run the commands in this section to refresh.*
- `git log --format='%an' | sort | uniq -c` → DG 54, ASF 4, JL 0 (58 commits,
  2026-08-14 → 2026-09-12)
- `git blame --line-porcelain` over all tracked `.py`/`.md`/`.toml`/`.html`/
  `.sql`/`Makefile` → 22,088 lines, **one author**; including notebooks, 27,979
- `git blame docs/project_plan.md` → 105/105 DG; ASF's `1973655` was reverted by
  `483c5c2`, and `e73d2cc` was superseded by the 2026-08-23 rewrite
