# Experiments

An experiment is a question asked of a fixed dataset, with the answer recorded
next to the identity of the data that produced it. This document describes the
model, the three classes that implement it, and how to create and run one.

The short version:

```python
from pathlib import Path
from flight_planner.experiments import Experiment

experiment = Experiment.open(Path.cwd())      # reads experiment.toml
catalog    = experiment.catalog()             # verifies every checksum
planner    = catalog.airline('UA').planner()  # narrow, then materialize

distance_km, legs = planner.find_shortest_route('SFO', 'BOS')
experiment.record({'shortest_km': distance_km}, catalog=catalog)
```

Three of the [demos](demos.md) cover the same ground end to end, against this
repository's own snapshots:

```bash
uv run python src/demos/snapshot_example.py     # frozen data, and the checksum guarantee
uv run python src/demos/catalog_example.py      # lookup, narrowing, endpoint modes
uv run python src/demos/experiment_example.py   # reading, running and recording one
```

## 1. The problem this solves

`data/processed/airports.csv` and `data/processed/routes.csv` are *build
output*. `make flight_network` rewrites them from the raw sources whenever the
pipeline changes. A notebook that reads them directly has two problems:

- **Re-running it later can produce a different answer**, with nothing to
  indicate that the data moved rather than the code.
- **A number in a report cannot be traced to the bytes behind it.** "4,341 km"
  is not a result; "4,341 km, from snapshot `2026-09-11-bb90a8`, United's large
  US airports" is.

The fix is to separate the *dataset that keeps changing* from the *dataset an
experiment was run against*, and to make the second one provably immutable.

## 2. Three pieces

| Class | What it is | Knows about |
|---|---|---|
| `Snapshot` | Frozen CSV files plus a manifest of SHA-256 checksums | A manifest *format*; it is handed a directory |
| `Catalog` | The scope an experiment works in: lookup and narrowing | Airports and routes as domain objects |
| `Experiment` | A directory binding notebooks to one snapshot, and its results | An `experiment.toml` format |

All three live in `flight_planner.experiments` and ship in the wheel. None of
them knows where this repository keeps its data — every one takes a directory
from its caller. That is deliberate, and it is what lets the same code run from
a source checkout, an installed wheel, or a clone in a Colab session.

The other half — *creating* snapshots and experiments — knows the repository
layout intimately, so it lives in `scripts/` and is not shipped.

```
scripts/new_snapshot.py    ->  data/snapshots/<id>/     ->  Snapshot  ->  Catalog
scripts/new_experiment.py  ->  experiments/<slug>/      ->  Experiment
```

## 3. Snapshot: data that cannot change quietly

A snapshot is a directory:

```
data/snapshots/2026-09-11-bb90a8/
    airports.csv     3,387 rows
    routes.csv      66,332 rows
    manifest.json
```

The manifest records the id, when it was frozen, the git commit it came from,
the tool that wrote it, the narrowing that produced it, and a SHA-256, byte
count and row count for every file:

```json
{
  "snapshot_id": "2026-09-11-bb90a8",
  "created": "2026-09-11T17:02:13+00:00",
  "source_commit": "610936de75b2d3c45e0e84daea687b32daf35aa3",
  "generator": "scripts/new_snapshot.py",
  "criteria": {},
  "files": {
    "routes.csv": { "sha256": "3450e7a4...", "bytes": 2991700, "rows": 66332 }
  }
}
```

`Snapshot.open()` re-hashes every file and raises `SnapshotIntegrityError` if
one has moved by a single byte. This is not a formality — flipping one bit in
the 3 MB `routes.csv` is detected.

```python
from flight_planner.experiments import Snapshot

snapshot = Snapshot.open('data/snapshots/2026-09-11-bb90a8')
snapshot.snapshot_id        # '2026-09-11-bb90a8'
snapshot.criteria           # {} -- the whole network
snapshot.source_commit      # the commit the data was generated from
snapshot.path('routes.csv') # only files the manifest vouches for
```

Two design points worth knowing:

- **The id is `<date>-<content hash>`.** Identical data always lands on the same
  directory name, so re-freezing the same slice is a no-op rather than a
  duplicate. Different data always lands on a different name, so a changed
  dataset cannot silently occupy an old id.
- **Verification can be skipped** with `Snapshot.open(directory, verify=False)`,
  which exists because hashing a large snapshot on every open costs real time.
  Skipping it means nothing detects a changed file, so it should be a deliberate
  act, not a default.

### Snapshots in this repository

| Id | Contents | Criteria |
|---|---|---|
| `2026-09-11-bb90a8` | 66,332 routes / 3,387 airports | none — the whole network |
| `2026-09-11-1528c4` | 861 routes / 88 airports | `airline=UA`, `airport_type=large_airport`, `country=US` |

The second predates the pipeline going global and is kept pinned rather than
re-frozen. It is also a working demonstration of forward compatibility: it was
cut before the `is_international` column existed, and it still loads — absent
columns read as their default instead of raising.

## 4. Catalog: narrowing, and being told what it cost

A catalog is the set of airports and routes an experiment is working with. It
does two jobs: looking things up, and narrowing the scope.

### Lookup

```python
catalog = snapshot.catalog()

catalog.airport('BOS')                 # -> Airport
catalog.flight('UA1876')               # -> Route
catalog.route('SFO', 'BOS', airline='UA')
catalog.routes_between('SFO', 'BOS')   # -> every carrier's leg
catalog.routes_from('SFO')             # -> outgoing only; routes are directed
```

**The flight number is the only unique handle on a route.** SFO to BOS is flown
by three carriers over the identical 4,341.022 km:

```
B60346   UA1876   VX0047
```

So `route('SFO', 'BOS')` cannot answer, and does not guess — it raises and names
the candidates. Pass `airline=`, or use `flight()`.

### Narrowing

Four axes, each returning a new catalog:

```python
catalog.airline('UA')                  # by operating carrier
catalog.airport_type('large')          # by OurAirports size classification
catalog.country('US')                  # by ISO country
catalog.international()                # by the Wikipedia international list
```

Narrowings compose, and every one records what it did:

```python
narrowed = catalog.airline('UA').airport_type('large').country('US')
narrowed.summary()
# {'chain':    [{'operation': 'airline', 'arguments': ['UA'], ...}, ...],
#  'routes':   [66332, 2170, 1661, 861],
#  'airports': [3387, 427, 256, 88],
#  'dangling': 0}
```

That chain is the point. It goes into the snapshot manifest when you freeze a
slice, and into `results.json` when you record a result, so a number always
carries its own derivation.

### The three endpoint modes

A route has two ends. When you narrow by a property of *airports*, you have to
say what happens to a route with one qualifying end and one that does not.
All three answers are available; none is forbidden.

| `endpoints` | A route is kept when | Consequence |
|---|---|---|
| `"both"` (default) | both ends match | Closed. Order never matters. Nothing dangles. |
| `"either"` | at least one end matches | Keeps hub-to-regional legs; the airport set then contains airports that did not themselves match. |
| `"airports"` | always — routes are untouched | Narrows lookups only. Order matters, and routes can point outside the scope. |

Measured on the full snapshot, starting from `airline('UA')` (2,170 routes /
427 airports) and narrowing to large airports:

| Mode | Routes | Airports | Dangling |
|---|---|---|---|
| `both` | 1,661 | 256 | 0 |
| `either` | 2,144 | 425 | 0 |
| `airports` | 2,170 | 257 | **509** |

`"both"` is the default because it is the only mode that commutes.
`.airline('UA').airport_type('large')` and `.airport_type('large').airline('UA')`
both yield exactly 1,661 routes and 256 airports — the same objects in the same
order — because pruning routes so that both ends qualify and then re-deriving
the airports from what survives makes the order irrelevant.

The other modes are order-dependent, and that is not a defect to be prevented.
The principle here is that the experimenter is **informed, not restricted**: any
narrowing in any order is permitted, and the catalog tells you what it did.

### Dangling edges

Under `"airports"`, routes survive that point at airports outside the scope.
`Catalog.dangling` lists them, and `planner()` builds the graph anyway while
warning:

```
509 route(s) reach 170 airport(s) outside this catalog (ABE, ACV, ACY, AEX,
AIA, ...); they are included as vertices. Narrow with endpoints='both' to
avoid this.
```

It builds rather than refuses because there are legitimate reasons to want
exactly that graph. It warns because the alternative is a graph whose vertices
arrived by accident.

### Materializing

```python
planner = narrowed.planner()          # everything in scope
planner = catalog.subgraph(['UA1876', 'UA0005'])   # only the named legs
```

`subgraph()` is for hand-assembling a small network out of real entities — a
three-flight example with real coordinates, rather than a whole slice.

## 5. Experiment: the directory and its record

```
experiments/sfo-bos-dijkstra/
    experiment.toml     what it runs against, and with
    explore.ipynb       the notebook(s)
    results.json        what came out
```

### `experiment.toml`

```toml
slug = "sfo-bos-dijkstra"
description = "Does narrowing the network to one airline change the route?"
notebooks = ["explore.ipynb"]
snapshot = "../../data/snapshots/2026-09-11-bb90a8"

[parameters]
origin = "SFO"
destination = "BOS"
airline = "UA"
```

**The snapshot path is relative to the toml file and resolved against that
file's own location** — never against the working directory, and never by
walking up from `__file__`. This is what lets the repository be cloned anywhere
and the experiment still find its data. An absolute path is also accepted.

`[parameters]` holds whatever the notebook needs that is not the data itself:
an origin, a heuristic, a cutoff. It is recorded alongside the results, so a run
states its inputs as well as its outputs.

### `results.json`

`record()` will not write a result that does not say where it came from. It
opens the snapshot — which verifies every checksum — and then embeds the
snapshot's identity, the parameters, and the narrowing chain:

```json
{
  "experiment": "sfo-bos-dijkstra",
  "recorded": "2026-09-11T17:03:30+00:00",
  "snapshot": {
    "id": "2026-09-11-bb90a8",
    "reference": "../../data/snapshots/2026-09-11-bb90a8",
    "criteria": {},
    "source_commit": "610936de75b2d3c45e0e84daea687b32daf35aa3"
  },
  "parameters": { "origin": "SFO", "destination": "BOS", "airline": "UA" },
  "results":    { "narrowed_km": 4341.022084519025, "narrowed_flights": ["UA1876"] },
  "catalog":    { "chain": [...], "routes": [66332, 2170, 1661, 861], "dangling": 0 }
}
```

Recording against tampered data raises instead of writing. A previous run is
replaced rather than appended to — git holds the history, so the file holds the
current answer.

Notebooks are committed **without stored outputs**. Outputs are re-derivable,
they make diffs unreadable, and `results.json` is the recorded answer. A test
enforces this.

## 6. Creating one

```bash
# Freeze the whole processed network.
make snapshot

# Freeze a slice. Narrowings are the catalog's, so they mean the same thing
# here as in a notebook.
make snapshot SNAPSHOT_FILTERS="--airline UA --airport-type large --country US"

# Scaffold an experiment against the most recent snapshot.
make experiment SLUG=astar-heuristics

# ... or against a named one.
make experiment SLUG=astar-heuristics SNAPSHOT=2026-09-11-bb90a8
```

`make snapshot` prints what each narrowing cost:

```
processed: 66332 routes / 3387 airports
  airline(UA) -> 2170 routes / 427 airports
  airport_type(large_airport) -> 1661 routes / 256 airports
  country(US) -> 861 routes / 88 airports
snapshot: data/snapshots/2026-09-11-35038d
  861 routes / 88 airports
```

Rows are carried across verbatim: every column is read as text and written back
untouched, so a snapshot's bytes are the processed file's bytes for the rows
that survived. No re-formatted floats, no drift.

`make experiment` writes a starter notebook that runs end to end as written —
it opens the experiment, verifies the data, finds a route and records the
result. `--force` regenerates the config the script owns and **never** touches a
notebook, which is the experimenter's work.

Full options: `uv run python scripts/new_snapshot.py --help`.

## 7. Running in Colab

See [Setup §6](setup.md#6-google-colab) for the install cell. Once the package
is installed and the repository cloned, an experiment is three lines:

```python
from flight_planner.experiments import Experiment

experiment = Experiment.open('/content/traiectoria-optima/experiments/sfo-bos-dijkstra')
planner    = experiment.snapshot.load_planner()   # checksums verified here
experiment.record({'shortest_km': 4341.0, 'legs': 1})
```

This was verified end to end from a clean clone, running under the installed
wheel from an unrelated working directory, with Colab's pinned pandas 2.2.3 and
numpy 2.1.3 left untouched.

To version a notebook written in Colab, commit from the clone — the experiment
directory is a normal part of the repository.

## 8. Things to know before you rely on this

**Flight numbers are assigned, not real.** `UA1876` is not a published United
flight. The numbers are generated by the pipeline as `{airline}{n:04d}`, ordered
by `(source, destination)`, so that every route has a stable unique handle.
`(airline, source, destination)` is unique across all 67,663 raw routes, so the
assignment is collision-free. Do not present them as real schedules.

**Numbering leaves gaps, deliberately.** Numbers are assigned to the *raw* route
set, before endpoint resolution. United is numbered `UA0001`–`UA2180` but ships
2,170 rows, because 10 of its routes reference airports with no usable IATA code
or coordinates. The alternative — numbering after resolution — would renumber
every downstream route the moment an entry was added to
`data/reference/iata_code_overrides.csv`. Stability was judged worth the gaps.

**1,331 of 67,663 raw routes are dropped** (98.0% resolve), referencing airports
that no longer exist or have been renamed (TXL, SXF, TSE). The pipeline reports
them rather than dropping them silently.

**`Airport` hashes on IATA code alone, and `Graph.add_vertex` is first-wins.**
Mixing a bare `Airport('BOS')` with a catalog-sourced BOS keeps whichever was
added first and silently discards the other's coordinates — which would make
A\*'s Haversine heuristic measure from (0, 0). Entities that come from a catalog
are safe by construction. This is documented and tested rather than fixed,
because changing it would change core graph semantics.

**`international` is not a synonym for `large`.** The flag comes from
Wikipedia's list of international airports and is independent of the OurAirports
size classification: 116 large airports are absent from that list, and 364
medium ones appear on it.

## 9. Reference: the full network

From `data/snapshots/2026-09-11-bb90a8`:

| | |
|---|---|
| Routes | 66,332 (of 67,663 raw; 98.0% resolve) |
| Airports | 3,387 — only those a route touches, from 9,053 with a usable IATA code |
| Airlines | 564 (568 raw) |
| Countries | 230 |
| Continents | 6 |

Airports by `type`:

| Type | Count |
|---|---|
| `medium_airport` | 1,736 |
| `large_airport` | 1,066 |
| `small_airport` | 518 |
| `heliport` | 34 |
| `seaplane_base` | 33 |

Note there are **five** classifications, not three — `airport_type('large')`,
`('medium')` and `('small')` are shorthand for the `_airport` forms, but
heliports and seaplane bases must be named in full.

Busiest carriers by resolved routes: `FR` 2,384 · `AA` 2,346 · `UA` 2,170.

1,329 of the 3,387 airports are listed as international.

## See also

- [Setup](setup.md) — installing, and the Colab install cell
- [Data](data.md) — where the raw data comes from and what the pipeline makes of it
- [Makefile](makefile.md) — every target, including `snapshot` and `experiment`
