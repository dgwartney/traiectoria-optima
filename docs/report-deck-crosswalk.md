---
title: |
  Flight Route Planner\
  Report and Deck Crosswalk
subtitle: |
  One body of evidence, two renderings — what gets written once
  and ported, and what must never be written twice
author: David Gwartney
date: 2026-09-13
---

# Report and deck crosswalk

**Read this before writing any chapter or any slide.** The final report and the
presentation deck are two of the six outputs the rubric names, and they are not
two bodies of work. They are two renderings of one body of evidence that is
already committed: six experiments' `results.json`, six figures in
`slides/images/`, and three result documents. Report §1, §2.1, §6 and §7 are
already written prose over that evidence.

Everything still open in both artifacts is **transcription, not research** —
with one exception, the A\* admissibility argument (§4.3), which is the only
remaining writing task carrying real graded weight.

This document exists because the board previously tracked the report and the
deck as independent lanes, across 28 open issues. That structure invited the
same paragraph to be written twice, and in the places where it was written
twice, the two copies disagreed — see [§3](#3-where-the-two-artifacts-diverged).

## Contents

1. [The rule](#1-the-rule)
2. [The crosswalk](#2-the-crosswalk)
3. [Where the two artifacts diverged](#3-where-the-two-artifacts-diverged)
4. [Which deck is the deliverable](#4-which-deck-is-the-deliverable)
5. [Order of work](#5-order-of-work)

## 1. The rule

**The report chapter is the source. The slide is a derivative.**

Write the chapter from the committed `results.json`, then port that chapter's
headline numbers to its slide in the same sitting, before moving on. Two
consequences, and they are the whole point of this document:

- **No slide task is ever "find the real number."** By the time a slide is
  ported, the number is in the chapter, and the chapter cites the
  `experiments/` directory it came from. A slide that needs a figure the
  chapter does not have means the *chapter* is unfinished.
- **No chapter and its slide are ever assigned to different sittings.** The
  cost of the second rendering is minutes. The cost of splitting them is that
  the two copies drift, which is exactly what happened before.

Every number in either artifact traces to a committed `results.json`. Neither
artifact is allowed to carry a figure that does not.

## 2. The crosswalk

One content unit per row. The deck column is a checklist item on the report
issue, not an issue of its own.

| Content unit | Report | Deck | Evidence already committed | Real work |
|---|---|---|---|---|
| Dataset | #42 (§2 intro; §2.1 written) | #53 | `graph-stats/results.json`, `degree-distribution.png`, `top-hubs.png` | Prose for sources and cleaning; the slide is transcription |
| Graph construction + API | #43 | #54, #55 | — | One pipeline and API description, written once |
| Algorithms + A\* argument | #44, **#15** | #56 | `results-astar-consistency.md` — 658,470 checks, 0 violations, plus a four-vertex counterexample | **The one genuine writing task.** Highest graded weight open |
| Correctness testing | #45 | #61 | `results-networkx-parity.md`, `astar-consistency` | Blocked on #5 — see [§5](#5-order-of-work) |
| Complexity + runtime | §6, §7 written | #58 | `search-cost/results.json`, `runtime.png`, `nodes-expanded.png` | Transcription only |
| Visualization | #46 | #57, #60 | `route-map/`, `route-map-syd-jfk.png`, `route-map-hnl-bdl.png` | Short prose, then insert an existing figure |
| Lessons learned | #47 | #62 | §1.1's two findings, `status.md` §8 | Written once, split two ways |
| Conclusion | #48 | — | §1.1 executive summary | Small |
| References | #49 | Deck slide is complete | The deck's References slide already matches §11's outline | **Copy the slide into the chapter.** No research |
| Appendix / links | #50 | Questions slide carries the repo link | — | Minutes |
| Demo | #20, #23 | #52 | `src/demos/route_query_example.py`, `search-cost/results.json` | **One** notebook drives the slide, the demo and the rehearsal |

**Slide tasks that survive as their own issues**, because they have no report
counterpart: #51 (the agenda numbers five items "05"), #64 (accuracy sweep),
#22 (assemble and export). Everything else in the #51–#64 range folds into the
row above that names it.

## 3. Where the two artifacts diverged

Nine claims where the deck and the code disagreed as of the 12 September deck
export. They are one defect, not nine: **the deck predates the measurements.**
Fix them after the chapters are written, so the deck copies finished prose
rather than being independently corrected.

| Claim on the deck | What the code and the report say |
|---|---|
| "Mathematical Guarantee: Both approaches are guaranteed to return the exact same optimal route" | §1.1 and §7.5: BFS answers a *different question*. On some queries it expands more nodes and returns a worse route. BFS's cost is a hop count; Dijkstra's and A\*'s are kilometres. The guarantee holds for A\* against Dijkstra, and only there. |
| "Cheapest Route: minimizing overall flight cost"; "Flat-rate pricing values per carrier segment" | §1.2: OpenFlights carries **no fare data**. "Cheapest" is defined as lowest total great-circle distance. |
| "Standardized Flight Physics", cruise velocities, headwind equations | `src/models/flight/` exists, and the route planner never touches it. Nothing in the deliverable models physics. |
| "2. SQLite Structuring" in the pipeline | The pipeline has been pandas since `39875ac`. SQLite survives only in legacy `src/data/`. |
| "ipyleaflet Widgets… bidirectional communication" | `ipyleaflet` appears nowhere in `src/`. `flight_planner.viz` is Folium and pyproj. Ch. 8's outline repeats the same error. |
| "Decrease-Key Optimizations… resolving the standard [TODO]" | `MinHeap` exposes `push`, `pop` and `peek` and has **no `decrease_key`**. Dijkstra uses lazy superseded entries — see `test_superseded_entry_does_not_corrupt_the_distance`. The claim is false, and the lazy-deletion design is the better slide. |
| Core API: `fewest_stops` / `shortest_distance` / `astar`, plus "TODO: confirm signatures" | The API is `FlightPlanner`, and `search()` returning a `SearchResult`. |
| Empirical Runtime: complexity classes only; "optimal baseline for dense graph processing" | Density is **0.32%** — the graph is sparse, and that sparsity is §2.1's and §3's argument for the adjacency list. Measured growth exponents are in `search-cost/results.json`. |
| "~3,300 airports / ~67,000 routes", plus a TODO | Measured: **3,387 airports and 66,332 routes**, of which 29,615 run parallel to another on the same pair (§2.1). |

The A\* row travels with #39: the consistency correction has to land in
`AStar`'s docstring, in Ch. 4 and on the A\* slide together, or the three
disagree again.

Two things the rubric names as A1 outcomes are **missing from the deck and
already rendered in the repository** — the BFS-vs-Dijkstra-vs-A\* comparison
table and a rendered route map. `slides/images/nodes-expanded.png`,
`route-map-syd-jfk.png` and `route-map-hnl-bdl.png` are committed. Those are
insertions, not production.

## 4. Which deck is the deliverable

**The Google Slides deck.** The in-repo reveal.js deck is retired (#38).

It contributes no finished content — 36 `TODO` markers across 31 sections — but
its *section list* is a better outline than the Google deck's current one, and
it is where the board's #59–#63 came from. So the outline is harvested and the
HTML goes. `slides/images/` stays: `docs/` links those figures, and the report
builds against them.

The rubric's rule that "a web UI is never required or rewarded" does not
penalise presentation tooling. It does not reward it either, and the deck is
the deliverable that is behind.

## 5. Order of work

1. **#5 — the four rubric-named tests** (empty, single-element,
   cyclic/duplicate, disconnected) plus the hand-built mini-graph. p. 5 names
   them; `test_graph.py` has five tests, all about construction, and none of
   the four. Ch. 5's first bullet and the deck's Testing slide both promise
   this coverage, so until it lands **both artifacts would describe tests that
   do not exist.** Small, independent, startable now, and on the critical path
   rather than optional.
2. **#39, #15 and Ch. 4** — highest graded weight open, and the evidence is
   already measured.
3. **Ch. 2 intro, Ch. 3, Ch. 5, Ch. 8, Ch. 9, Ch. 10, Ch. 11, Appendix** —
   prose, each followed immediately by its slide port ([§1](#1-the-rule)).
4. **The demo notebook (#20)** — reading its numbers from
   `experiments/search-cost/results.json` rather than recomputing them, so
   nothing on stage waits for a timing loop.
5. **`make report` (#21), deck export (#22), rehearsal (#23), accuracy sweep
   (#64).**

## See also

- [Final report](report/README.md) — one file per chapter; §1, §2.1, §6 and §7
  are written, the rest is the work
- [Where we are](status.md) — the dated snapshot this document's evidence
  column is drawn from
- [Experiments](experiments.md) — why every number here names a `results.json`
- `term-project-info.pdf` — the requirements, at the repository root
