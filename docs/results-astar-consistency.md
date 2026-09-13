---
title: "A* and heuristic consistency"
subtitle: "Results from `experiments/astar-consistency`"
---

# A\* and heuristic consistency

> **For the final report.** This section is written for
> [`docs/report/04-algorithms.md`](report/04-algorithms.md) §4.3,
> *A\* Search (Stretch Concept)* → "Haversine
> admissible heuristic / Admissibility argument", and §5, *Correctness
> Testing*. Every number below is read from
> [`experiments/astar-consistency/results.json`](../experiments/astar-consistency/results.json),
> which the experiment wrote. Regenerate with
> `uv run python experiments/astar-consistency/run.py`.

## The question, and why it is not the obvious one

Textbooks state A\*'s guarantee in two different strengths, and the difference
is easy to miss:

- **Admissible** — `h(v)` never overestimates the true remaining cost to the
  goal. Enough for A\* to be optimal *if it is allowed to reconsider a vertex
  it has already expanded*.
- **Consistent** (also called monotone) — `h(u) <= w(u, v) + h(v)` for every
  edge `u → v`. Stronger. Required if A\* closes each vertex permanently on
  first expansion, which is the common textbook formulation and the one this
  project implements.

`AStar`'s docstring promises optimality for an *admissible* heuristic. Its
implementation adds each vertex to a `visited` set when popped and skips it
forever after (`src/flight_planner/pathfinding/astar.py:84`), which needs
*consistency*. The two claims are not the same, and this experiment measures
the gap between them.

**Why this could not be found with flight data.** Great-circle distance is
consistent as a matter of spherical geometry — the estimate from `u` to the
goal cannot exceed the flown distance `u → v` plus the estimate from `v`,
because that is the triangle inequality. So no quantity of real routes reaches
the case. The experiment therefore has two halves that ask different questions
of different data.

## Half one: the defect, on four vertices

An aggregate over ten thousand queries proves a defect exists; it does not let
a reader *see* it. This is the smallest graph that does:

```
S --2.0--> A --1.0--> G
 \                    ^
  1.0--> B --0.5--> A/
```

The optimum is `S → B → A → G` at **2.5**. The direct `S → A → G` costs 3.0.
The heuristic:

| Vertex | `h(v)` | True remaining cost |
|---|---|---|
| S | 0.0 | 2.5 |
| B | 1.5 | 1.5 |
| A | 0.0 | 1.0 |
| G | 0.0 | 0.0 |

No estimate exceeds the truth, so it is **admissible**. But `h(S) = 0` while
`h(B) = 1.5` across an edge of weight 1.0, so `h(S) <= w(S,B) + h(B)` — it is
**not consistent**.

What the three engines return:

| Engine | Reported cost | Route returned | Legs sum to | Expansions |
|---|---|---|---|---|
| `Dijkstra` | 2.5 | `S→B→A→G` | 2.5 | 3 |
| `AStar` | **3.0** | `S→B→A→G` | **2.5** | 3 |
| `ReopeningAStar` | 2.5 | `S→B→A→G` | 2.5 | 4 |

**There are two defects in that middle row, and the second is worse than the
first.** A\* returns 3.0 where the optimum is 2.5 — suboptimal, which is bad.
But the itinerary it hands back is `S→B→A→G`, whose legs sum to 2.5. **The
cost it reports does not describe the route it returns.** A user handed a
three-leg itinerary and told it costs 3.0 when those three legs cost 2.5 has
been given two answers that contradict each other.

The mechanism: A\* pops `A` early, carrying the 2.0 route via `S→A`, and closes
it. The cheaper route `S→B→A` is found afterwards, so `predecessors[A]` is
updated — which is why the *path* is right — but `A` is never re-expanded, so
the improvement never propagates to `G`, and `g_score[G]` keeps the stale
3.0 that is then reported as the cost.

## Half two: the sweep, on random graphs

Fifty random weighted digraphs (2–25 vertices, up to 3× as many edges, with
zero weights, ties, self-loops, parallel edges and disconnected components on
purpose), every ordered pair, with a fresh admissible-but-inconsistent
heuristic per goal. **NetworkX is the oracle** — its A\* reopens nodes, and so
is optimal for any admissible heuristic. Verified, not assumed: it was wrong
on none of the 10,866 queries.

| | Count |
|---|---|
| Graphs | 50 |
| Queries | 10,866 |
| Goals scored | 681 |
| …of which the heuristic was genuinely inconsistent | 304 (45%) |
| **`AStar` suboptimal** | **27** |
| …of those, where the reported cost contradicts its own path | **25** |
| `ReopeningAStar` suboptimal | **0** |
| NetworkX A\* suboptimal | **0** |

First failure, so one case is reproducible rather than only countable: seed 6,
`n3 → n12`, where `AStar` reports 7.764 against an optimum of 7.0.

Only 304 of 681 heuristics turn out inconsistent, and the reason is worth
stating: where a goal is unreachable from most vertices, every score is 0.0,
and a zero heuristic is trivially consistent. The 27 failures all come from the
304 that are not.

### The fix, and what it costs

The remedy is to drop the closed set and skip superseded queue entries
instead — the standard formulation, and the one NetworkX itself uses.
`ReopeningAStar` (`src/validation/reopening.py`) does that. Two details are
forced by the existing code:

- **`MinHeap.pop()` returns the item without its priority**, so a stale entry
  cannot be recognised the usual way, by comparing the popped `f` against
  `g + h`. (NetworkX can: it keeps `enqueued[v] = (cost, h)` beside its heap.)
  Comparing `g` against the g-score the vertex carried at its last expansion
  does the same job, and also permits a genuine re-expansion — which is the
  whole point.
- **`AStar` derives `nodes_expanded` from `len(visited)`.** Dropping the closed
  set deletes the set that counter counts, so the fix must carry an explicit
  counter, exactly as `bfs.py` already does for the same reason.

The price is re-expansions:

| | Total expansions over the sweep |
|---|---|
| `AStar` | 40,580 |
| `ReopeningAStar` | 40,792 |
| **Overhead** | **+0.52%** |

Half a percent, and only where the heuristic is inconsistent.

## Half three: does any of this matter here?

Having established the defect, the question that actually matters to this
project is whether it is reachable on the project's own data. That is a
question only the real data answers — and answering it is what makes this an
experiment rather than a unit test.

Snapshot `2026-09-12-3e4f9d` — US large airports, 94 airports and 7,005
routes, the same slice the tutorial uses.

**Is the great-circle heuristic consistent on this data?** Checked directly,
for every edge against every possible goal:

| | Value |
|---|---|
| Checks (`94 goals × 7,005 routes`) | **658,470** |
| Violations | **0** |
| Worst violation | 0.000000 km |

Consistency is a property of the *data*, not only of geometry: it would fail if
any route in the dataset were recorded as shorter than the great circle it
spans. None is.

**So do A\* and Dijkstra agree?** On every ordered pair of the snapshot:

| | Value |
|---|---|
| Pairs checked | **8,742** |
| Cost mismatches | **0** |
| `Dijkstra` expansions | 410,874 |
| `AStar` expansions | **24,424** |
| `ReopeningAStar` expansions | **24,424** |

Two conclusions, and both are needed in the report.

**First: no committed result in this project is wrong.** The heuristic is
consistent here, so `AStar`'s closed set costs nothing, and it agrees with
Dijkstra on all 8,742 pairs. The defect is real but unreachable from this
data.

**Second — and this is the one the report should highlight — taking the fix
would not change a single published number.** `ReopeningAStar` expands
*exactly* the same 24,424 nodes as `AStar`, because a consistent heuristic
never triggers a re-expansion. That matters because
[`experiments/search-cost`](../experiments/search-cost) publishes A\*'s
per-pair expansion counts and `tests/experiments/test_committed.py` pins every
one of them; the obvious worry about adopting the patch — that it would
invalidate the project's headline comparison table — is measurably unfounded.

The same figures also restate the project's central claim on real data:
**A\* expands 24,424 nodes where Dijkstra expands 410,874 — 16.8× fewer, for
identical answers on all 8,742 pairs.**

## Recommendation

Take the patch. The case for it:

- It is about a dozen lines.
- It costs 0.52% more expansions, and only on inconsistent heuristics.
- It moves no committed number (measured above, not assumed).
- It removes a state in which the reported cost contradicts the returned
  itinerary — far harder to defend in a report than a re-expansion is.
- It makes the docstring true as written.

If the patch is **not** taken, then all three places `astar.py` says
*admissible* — lines 25, 35 and 61 — must be changed to say *consistent*, and
the report's admissibility argument must make the stronger claim. Which the
project's own heuristic does satisfy, as the 658,470 checks above show. What
is not defensible is leaving the docstring promising one condition while the
code requires another.

One existing test needs a note either way:
`tests/flight_planner/test_observers.py::TestReportedCountsAreTrue::test_no_vertex_is_expanded_twice`
asserts no vertex is ever expanded twice. The patch keeps it green, because its
fixture's heuristic is consistent — but that test does encode "no
re-expansion" as a requirement, so it needs a comment explaining *why* it
holds, or it will later look as though the patch violated it.

## What this does and does not establish

**Establishes.** A\* as implemented is optimal only for consistent heuristics,
not merely admissible ones; the gap is reachable in a second on random graphs
and produces both suboptimal costs and self-contradictory results; the
standard fix is nearly free; and none of it affects this project, whose
heuristic is consistent across 658,470 checks.

**Does not establish.** The randomized sweep covers graphs of 2–25 vertices
with non-negative weights. It says nothing about negative weights (outside
Dijkstra's contract, deliberately never generated), about graphs orders of
magnitude larger, or about heuristics that are *inadmissible* — which would
break optimality for any A\* formulation, including NetworkX's, and so cannot
be checked against this oracle.

## Reproducing it

```
uv run python experiments/astar-consistency/run.py
```

The script exits non-zero only if the *snapshot* half finds a problem — an
inconsistent real heuristic, or A\* disagreeing with Dijkstra on real data.
The randomized half is *expected* to find the shipped A\* suboptimal; that is
the finding, not a failure. Recorded 2026-09-12 against NetworkX 3.6.1 on an
Apple M2 Pro, Python 3.12.12.

## See also

- [Validation against NetworkX](results-networkx-parity.md) — the companion
  experiment: do our answers match NetworkX's on real long-haul queries?
- [Validating against NetworkX](networkx-validation.md) — the design document
  this experiment implements (Option E), and the six other options considered.
- [Graph Algorithm Notes](graph-algorithms-notes.md) — Dijkstra, BFS and A\*.
- [Final report](report/README.md) — [§4.3](report/04-algorithms.md) and
  [§5](report/05-correctness-testing.md) are where this section lands.
