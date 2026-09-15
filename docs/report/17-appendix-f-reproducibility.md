# Appendix F. Reproducibility: Snapshots and Experiments

Every figure in this report names a frozen dataset and a committed answer. This
appendix describes the machinery that makes that possible. It is a condensation:
[`docs/experiments.md`](../experiments.md) is the full reference, with the
worked examples, the Colab recipe, and the complete narrowing vocabulary.

## F.1 The problem

The processed tables everything reads — `data/processed/airports.csv` and
`routes.csv` — are build output. `make flight_network` regenerates them from
the raw sources and overwrites whatever was there, and the filenames do not
change when it does. A notebook reading them directly therefore has two
problems:

- **Re-running it later can produce a different answer**, with nothing to
  indicate that the data moved rather than the code.
- **A number cannot be traced to the data it came from.** "4,341 km" is not a
  result. "4,341 km, from the frozen copy `2026-09-11-bb90a8`, looking only at
  United's large US airports" is.

That second sentence is the standard this report holds itself to, and §2.2's
insistence that "3,387 airports" names a specific hashed set of rows rather
than whatever the last build produced is this appendix's rule applied to a
chapter.

## F.2 Three pieces

| Class | What it is | Used to |
|---|---|---|
| `Catalog` | A working set of airports and routes | Explore: look things up, narrow to a slice, see how much is left |
| `Snapshot` | An immutable, checksummed copy of one such set | Pin the data a result was computed from |
| `Experiment` | A directory holding a snapshot reference, its parameters, and its recorded answer | Publish a number with its derivation attached |

**A snapshot is content-addressed.** Its id is `<date>-<hash of contents>`, so
changing the data changes the id: a snapshot cannot be edited in place, only
superseded. `Snapshot.open()` re-hashes every file against the manifest before
returning a row and raises on a mismatch, which costs 0.01 s on the 66,332-route
network — cheap enough that a live demo can afford to verify its own data.

**The manifest records provenance, not just content.** Per file: SHA-256, byte
count and row count. Per snapshot: the criteria that produced it, the commit of
the code that wrote it, and — for slices cut in more than one step — the
narrowing chain, operation by operation, with the row and airport counts before
and after each. So a slice states how it was cut, not merely what it contains.

**Narrowing has to say what it does with a half-qualifying route.** A route has
two ends; narrowing on a property of *airports* must decide the case where one
end qualifies and the other does not. The default is `endpoints="both"`, because
it is the only mode under which two narrowings commute — narrowing by airline
then by country gives the same set as the reverse. Edges left dangling by a
narrowing are reported rather than quietly retained, since a graph whose
vertices arrived by accident is not the graph anyone asked for.

<div class="deck-slide" id="snapshots">

### Why every number in this deck names a snapshot

<div class="cards">

<div class="card">

<span class="pill warn">The problem</span>

### `data/processed/` is build output

`make flight_network` overwrites it and the filenames do not change, so a
notebook reading it directly can produce a different answer later with nothing
to say the *data* moved rather than the code.

**"4,341 km" is not a result.** "4,341 km, from the frozen copy
`2026-09-11-bb90a8`" is.

</div>

<div class="card">

<span class="pill">Three pieces</span>

### Catalog · Snapshot · Experiment

A `Catalog` explores and narrows. A `Snapshot` freezes one working set,
**content-addressed** — its id is a hash of its contents, so it can be
superseded but never edited.

`Snapshot.open()` re-hashes every file against the manifest before returning a
row. **0.01 s** on 66,332 routes — cheap enough for a live demo to verify its
own data.

</div>

<div class="card">

<span class="pill astar">Ten committed experiments</span>

### The answer travels with its derivation

Each is a directory: an `experiment.toml` naming its snapshot **by relative
path**, the notebook or script, and a committed `results.json`.

The manifest records provenance, not just content — the narrowing chain
operation by operation, with counts before and after each, plus the commit that
wrote it. `tests/experiments/` re-derives them on every run.

</div>

</div>

</div>

## F.3 The snapshots

| Id | Contents | Criteria | Used by |
|---|---|---|---|
| `2026-09-11-bb90a8` | 66,332 routes / 3,387 airports | none — the whole network | §2.5, §5, §7, and the route maps in §8 |
| `2026-09-12-3e4f9d` | 7,005 routes / 94 airports | `airport_type=large_airport`, `country=US` | `shortest-vs-fewest`, and the second half of §4.3's consistency sweep |
| `2026-09-11-1528c4` | 861 routes / 88 airports | `airline=UA`, `airport_type=large_airport`, `country=US` | the loader tests |

The last predates the pipeline going global and is kept pinned rather than
re-frozen. It is also a working demonstration of forward compatibility: it was
cut before the `is_international` column existed and it still loads, because
absent columns read as their default rather than raising.

## F.4 The experiments

Ten are committed. Each is a directory holding an `experiment.toml` that names
its snapshot **as a path relative to itself** — so the experiment travels with
the repository, and works the same from a clone, a source checkout or a Colab
session — a notebook or script, and a `results.json` holding the answer.

| Slug | Question | Snapshot | Consumed by |
|---|---|---|---|
| `graph-stats` | What does the network look like as a graph? Size, degree, reachability. | world | §2.5, §3 |
| `search-cost` | How much cheaper is informed search? | world | §7 |
| `networkx-parity` | Do our algorithms agree with an independent implementation? | world | §5, [App. D](15-appendix-d-networkx-parity.md) |
| `astar-consistency` | Is A\* optimal for an admissible heuristic, or only a consistent one? | US large | §4.3, §5, [App. E](16-appendix-e-astar-consistency.md) |
| `heuristic-admissibility` | Is the heuristic admissible *here*, and would a more accurate formula break it? | world | §4.3, §9 |
| `manhattan-heuristic` | What does a badly inadmissible heuristic buy, and what does it cost? | world | No chapter yet. Cited by `flight_planner.geo.heuristic`'s docstring as the counterexample to §4.3's argument, and listed here so that absence is deliberate rather than an oversight |
| `data-cleaning` | What did cleaning discard, and is the snapshot what the pipeline produces? | world | §2.3, §9 |
| `route-map` | What does an answer look like, drawn rather than printed? | world | §8, §9 |
| `shortest-vs-fewest` | What does skipping a stop cost? | US large | §9 |
| `sfo-bos-dijkstra` | Does narrowing to one airline change the shortest SFO–BOS route? | world | The framework's worked example, and the fixture the [Tutorial](../tutorial.md) builds against. No chapter cites it, and it is listed here so that absence is deliberate rather than an oversight |

Three of them are worth singling out for what they had to solve:

- **`search-cost` measures time**, so it records the machine — CPU model, core
  count, platform, Python version, and whether it was a Colab runtime —
  alongside the numbers. Growth exponents and node counts are portable;
  milliseconds are not, which is why §7.4 leans on the ratios between series
  rather than on the absolute figures.
- **`astar-consistency` needed data the snapshot cannot supply.** A heuristic
  that is admissible but inconsistent does not occur in this dataset, so its
  first half runs on random graphs; its second half uses the snapshot to ask
  whether the defect is reachable *here*. That is what earns it a pin rather
  than making it a unit test.
- **`route-map`'s output is a picture**, so it is the only experiment whose
  result cannot be a number. It writes each figure twice, dark for the deck and
  light for this report, and `tests/experiments/test_committed.py` asserts both
  exist.
- **`heuristic-admissibility` measures an invariant rather than a result.**
  §4.3's guarantee is not a fact about geometry — it holds because
  `src/data/flight_network.py` and `flight_planner.geo.heuristic` use the same
  formula at the same earth radius, which is a property of the build. An
  invariant nobody checks is a coincidence, so the experiment exits non-zero
  if it breaks and `tests/experiments/test_heuristic_admissibility.py`
  re-derives it over all 66,332 edges rather than reading the recorded
  answer.

## F.5 What this does not protect against

Stated here rather than left for a reader to discover:

**Flight numbers are assigned, not real.** `UA1876` is not a published United
flight. The pipeline generates `{airline}{n:04d}` ordered by
`(source, destination)` so every route has a stable handle;
`(airline, source, destination)` is unique across all 67,663 raw rows, so the
assignment is collision-free. They must not be presented as schedules.

**The numbering leaves gaps, deliberately.** Numbers are assigned to the *raw*
route set, before endpoint resolution, so United is numbered `UA0001`–`UA2180`
but ships 2,170 rows. Numbering after resolution would renumber every
downstream route the moment an entry was added to
`data/reference/iata_code_overrides.csv`; stability was judged worth the gaps.

**`Airport` hashes on IATA code alone, and `Graph.add_vertex` is first-wins.**
Mixing a bare `Airport('BOS')` with a catalog-sourced BOS (Boston) keeps whichever
arrived first and silently discards the other's coordinates — which would leave
A\*'s heuristic measuring from (0, 0). Entities that come from a catalog are
safe by construction. This is documented and tested rather than fixed, because
the alternative is making `Airport` unhashable without coordinates, which would
break the hand-built graphs §5's edge-case tests rely on.

**A snapshot verifies its contents, not its correctness.** The checksum proves
the rows have not changed since they were frozen. It says nothing about whether
the cleaning that produced them was *right*.

That gap is narrower than it was. `experiments/data-cleaning` re-runs the
pipeline over the committed raw files and compares the result against the
frozen snapshot, code for code — so "this snapshot is what the cleaning
produces" is now a measurement rather than an assumption, and the experiment
exits non-zero if the two part company. What remains unverifiable by any
amount of checksumming is whether the cleaning *rules* are the right rules,
which is an argument (§2.3) rather than a test.
