# Appendix D. Validation against NetworkX

Full results for the cross-validation §5 summarises. Every number below is read
from
[`experiments/networkx-parity/results.json`](../../experiments/networkx-parity/results.json),
which the experiment wrote; nothing here is hand-copied from a console session.
Regenerate with `uv run python experiments/networkx-parity/run.py`.

## The question

The three pathfinding algorithms are this project's deliverable, so they
cannot be replaced by a library — the assignment's rules say libraries are
"allowed only for loading, plotting, and **validating** your own results".
That leaves the question of how anyone knows they are right.

1,050 unit tests say the code behaves as designed. They cannot say the design is
correct, because the same person wrote both. For that, the same questions have
to be put to an implementation that shares no code, no data structures and no
author with ours. [NetworkX](https://networkx.org) is that implementation: a
BSD-licensed, independently maintained graph library whose shortest-path
routines are exercised by a large user base. Where the two disagree, one of
them has a bug.

## Method

**The data.** Snapshot `2026-09-11-bb90a8` — the whole world, 3,387 airports
and 66,332 routes, with no narrowing criteria at all. The project catalogue
asks for long-haul queries, and only the world graph contains long hauls;
narrowing to the US slice first would make "agrees with NetworkX" a claim about
a network nobody flies. Source commit `610936de`, re-verified by checksum on
every run.

**The comparison runs through our own interface, not around it.** NetworkX is
not called directly. It is wrapped as three engines implementing
`PathfindingAlgorithm` — `NetworkXDijkstra`, `NetworkXBFS`, `NetworkXAStar`
(`src/validation/engines.py`) — and handed to the same
`planner.find_shortest_route(origin, destination, engine)` every other
experiment uses:

```python
for name, ours, theirs in (
    ("Dijkstra", Dijkstra(), NetworkXDijkstra()),
    ("BFS", BFS(), NetworkXBFS()),
    ("A*", AStar(heuristic), NetworkXAStar(heuristic)),
):
    parity[name] = compare(planner, sample, ours, theirs, tolerance)
```

This matters more than convenience. Because the engine is a *parameter*, both
sides return the same kind of object — a `SearchResult` carrying `Route` legs
with airlines and flight numbers, not a list of node keys. What is validated is
therefore the whole answer, not just a number: if NetworkX's result could not
be expressed in our types, that would itself be a finding.

**The query set.** All-pairs over 3,387 airports is 11.5 million queries. The
experiment samples 200 ordered pairs instead, drawn with seed `20260913` from
the largest strongly connected component so that every pair is reachable by
construction and the sweep measures search rather than the cost of discovering
"no route". Unreachable pairs are checked separately, since agreeing that a
route exists is only half the contract.

**Comparing floats.** Both libraries sum the same `float64` kilometres in a
different order, so exact equality is the wrong test. Costs are compared with
a relative tolerance of `1e-9`.

## Result: the two libraries agree

| Algorithm | Pairs | Cost mismatches | Largest divergence | Identical paths | Identical flight numbers |
|---|---|---|---|---|---|
| Dijkstra | 200 | **0** | 3.6 × 10⁻¹² km | 200 / 200 | 200 / 200 |
| BFS | 200 | **0** | 0 km | 142 / 200 | 142 / 200 |
| A\* | 200 | **0** | 3.6 × 10⁻¹² km | 200 / 200 | 200 / 200 |

Zero disagreements on cost, for all three algorithms. The largest divergence
anywhere in the sweep is 3.6 × 10⁻¹² km — about four picometres, which is
float64 addition order and not a difference in answer.

Both libraries also agreed on all 4 unreachable pairs found in the first 400
ordered pairs: no route exists, and both say so.

### The named long-haul pairs

These five are `experiments/search-cost`'s pairs, so the two experiments can
be read side by side. Distances in kilometres; BFS reports legs, not distance.

| Pair | Dijkstra | NetworkX Dijkstra | A\* | NetworkX A\* | BFS legs | NetworkX BFS legs |
|---|---|---|---|---|---|---|
| SFO–BOS | 4341.022 | 4341.022 | 4341.022 | 4341.022 | 1 | 1 |
| LAX–JFK | 3974.164 | 3974.164 | 3974.164 | 3974.164 | 1 | 1 |
| SEA–MIA | 4379.358 | 4379.358 | 4379.358 | 4379.358 | 1 | 1 |
| HNL–BOS | 8192.794 | 8192.794 | 8192.794 | 8192.794 | 2 | 2 |
| ANC–MIA | 6459.622 | 6459.622 | 6459.622 | 6459.622 | 2 | 2 |

Four independent weighted implementations — two of ours, two of NetworkX's —
agree to three decimal places on every pair.

### Why BFS matches on 142 paths and not 200

This is not a defect, and reading it as one would be the easiest mistake to
make with this table.

BFS minimises *legs*, and on a network with 66,332 routes over 36,717 distinct
airport pairs, minimum-leg routes tie constantly: dozens of two-leg itineraries
may all be equally short. Nothing in the problem statement prefers one over
another, so the two libraries break those ties differently — ours by the order
`get_outgoing_edges` returns, NetworkX's by its own traversal order. Both
answers are correct.

The durable contract is therefore **cost parity**, which holds 200/200. Path
identity is reported as a secondary, non-blocking observation. The weighted
algorithms happen to agree on all 200 paths as well, because distance ties are
far rarer than leg-count ties.

## The graph-type decision, measured

A `MultiDiGraph` is used for the mirror rather than the simpler `DiGraph`, and
the experiment records the reason as a number rather than leaving it as a
comment:

| | Count |
|---|---|
| Routes in the snapshot | 66,332 |
| Distinct ordered airport pairs | 36,717 |
| **Routes a `DiGraph` would discard** | **29,615** |

A `DiGraph` keeps one edge per node pair. Mirroring 66,332 routes into one
would silently drop 29,615 of them — nearly half the network — and then every
table above would still read "0 mismatches", because both libraries would be
searching the same wrongly-built graph. The experiment asserts
`mirror.size == len(planner.edges)` before comparing anything, so this failure
mode cannot pass unnoticed.

This is the single most important design decision in the validation code, and
it is invisible in the results if you do not look for it.

## Runtime, honestly framed

Median of 5 runs of the whole 200-query sweep, on an Apple M2 Pro (10 cores,
macOS 26.6.2, Python 3.12.12). A node count reproduces on any machine; a
millisecond does not, which is why the machine is recorded alongside.

| Engine | 200 queries | Per query |
|---|---|---|
| `flight_planner` A\* | 862 ms | 4.3 ms |
| `flight_planner` BFS | 1,694 ms | 8.5 ms |
| `flight_planner` Dijkstra | 3,958 ms | 19.8 ms |
| NetworkX A\* | 475 ms | 2.4 ms |
| NetworkX BFS | 14 ms | 0.07 ms |
| NetworkX Dijkstra | 2,357 ms | 11.8 ms |

**This is not a leaderboard, and the reasons are load-bearing.**

**Two of the three NetworkX rows are not running the same algorithm as ours.**
This was checked in the NetworkX source rather than assumed, and it is the
caveat that matters most:

| Our call | What NetworkX actually runs |
|---|---|
| `nx.shortest_path(G, o, d)` — used by `NetworkXBFS` | `bidirectional_shortest_path` |
| `nx.shortest_path(G, o, d, weight=...)` — used by `NetworkXDijkstra` | `bidirectional_dijkstra` |
| `nx.astar_path(G, o, d, heuristic=...)` — used by `NetworkXAStar` | unidirectional A\* |

A bidirectional search grows a frontier from both ends and meets in the
middle, which on a graph of this diameter explores dramatically less. Ours are
the textbook single-source versions the assignment asks for. So the BFS row's
120× gap and the Dijkstra row's 1.7× gap both measure *a different algorithm
choice*, not a worse implementation of the same choice. Only the A\* row
compares like with like — and there the gap is 1.8×.

This does not affect any parity result above: bidirectional Dijkstra returns
the same optimal cost as the unidirectional kind, which is why the costs
agree exactly. It affects only what the timings may be used to claim.

**The systems are not comparable either.** NetworkX walks dicts of dicts keyed
by short strings. `flight_planner` walks `Airport` and `Route` objects and
allocates a `Route` list for every answer. Some of the remaining gap is data
structures, not algorithms.

**And our Dijkstra carries the from-scratch heap.** `MinHeap` is pure Python
and is the graded stretch concept; NetworkX uses the C-implemented `heapq`.

The conclusion worth stating in the report is therefore the modest one: **our
implementations are in the same performance class as an established library —
within a factor of two on the one comparison that runs the same algorithm —
and A\* is roughly 4.6× faster than our own Dijkstra on the same queries.**
That last figure is the informed-versus-uninformed result the project set out
to demonstrate, and it is a comparison between two of our own engines, so no
cross-library caveat applies to it.

## What this does and does not establish

**Establishes.** On 200 real long-haul queries over the full world network,
all three hand-written algorithms return the same costs as an independent
implementation, to within float64 noise; their results are expressible in our
own domain types without loss; and both libraries agree about unreachability.
This satisfies the assignment's Stage 2 milestone — "validated against a
library reference" — for all three algorithms rather than only the weighted
pair.

**Does not establish.** Three limits, stated so the report does not overclaim:

- **Expansion counts are not validated.** NetworkX does not expose how many
  nodes it expanded, so the engines report `nodes_expanded = 0` deliberately
  rather than inventing a plausible number that would sit in the same column
  as a measured one. The informed-versus-uninformed comparison rests on our
  own instrumentation, checked against an independent count in
  `tests/flight_planner/test_observers.py`.
- **200 pairs is a sample, not a proof.** It is drawn reproducibly from a
  seed, but a 0.002% sample of the 11.5 million possible pairs cannot rule out
  a defect that appears only on a rare graph shape. That gap is what
  [`experiments/astar-consistency`](16-appendix-e-astar-consistency.md) exists to
  close from the other direction, with randomized graphs designed to produce
  shapes flight data never does.
- **A recorded result goes stale silently.** "Zero mismatches" keeps reading
  as zero long after the code stops agreeing, so
  `tests/experiments/test_validation_experiments.py` re-derives the collapse
  figure, the five named pairs through four engines, and the sample seed from
  the snapshot on every test run rather than trusting the file.

## Reproducing it

```
uv run python experiments/networkx-parity/run.py
```

The script exits non-zero if the two libraries disagree, so a disagreement is
a failure rather than a line of output someone has to notice. Recorded
2026-09-12 against NetworkX 3.6.1.

## See also

- [Validating against NetworkX](../networkx-validation.md) — the design document
  this experiment implements (Options B and C), and the five other options
  considered.
- [A\* and heuristic consistency](16-appendix-e-astar-consistency.md) — the
  companion experiment, and the defect it found.
- [Experiments](../experiments.md) — snapshots, the `Catalog` vocabulary, and the
  experiment model.
- [Final report](README.md) — [§5](05-correctness-testing.md) is where this section lands.
