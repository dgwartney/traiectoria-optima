# Existing software

This project wrote its own snapshots, experiment records, catalog and data
loaders. Every one of those is a solved problem somewhere on PyPI, and a
reader who has met MLflow or DVC is entitled to ask why none of them is in
`pyproject.toml`. This document is the answer: what was built, what exists,
what each package would add, and what it would cost.

**What this is not.** None of the packages below has been installed, run or
benchmarked against this repository. This is a desk survey of their published
documentation, done in September 2026. Claims about *this* repository are
measured from the files in it; claims about the packages are what their
documentation says they do. The distinction matters if you are deciding to
adopt one — read the docs, not this page.

## 1. What was built

Four modules, 1,630 lines including docstrings:

| Piece | File | Lines | Job |
|---|---|---|---|
| `Snapshot` | [`experiments/snapshot.py`](../src/flight_planner/experiments/snapshot.py) | 236 | A directory of frozen CSVs plus `manifest.json`; opening it re-hashes every file against a recorded SHA-256 |
| `Catalog` | [`experiments/catalog.py`](../src/flight_planner/experiments/catalog.py) | 694 | Look up and narrow airports and routes, record each narrowing, materialize a `FlightPlanner` |
| `Experiment` | [`experiments/experiment.py`](../src/flight_planner/experiments/experiment.py) | 295 | `experiment.toml` in, `results.json` out, with the snapshot's identity recorded next to the numbers |
| `AirportLoader`, `RouteLoader` | [`loaders/csv_loader.py`](../src/flight_planner/loaders/csv_loader.py) | 405 | CSV rows to domain objects |

Two facts about them shape everything below.

The whole `experiments` subpackage imports **nothing outside the standard
library** — `hashlib`, `json`, `tomllib`, `pathlib`, `datetime`, `warnings`.
pandas arrives only underneath, through the loaders. The published wheel
declares exactly one runtime dependency, `pandas>=2.2,<4`.

And every artifact is a **plain file committed to git**. A snapshot is two CSVs
and a manifest; an experiment is a TOML file, a script and a JSON file. Nothing
is in a database, a cache directory or a server. That is what lets
[Experiments §8](experiments.md#8-running-in-colab) reduce a Colab run to three
lines: clone the repository and the data is already there, verified on open.

## 2. The landscape, by concern

### Snapshot — checksummed, pinned data

[**Pooch**](https://github.com/fatiando/pooch) is the closest single-purpose
match in the language. It keeps a registry mapping filename to SHA-256 (and
optionally a URL), downloads into a local cache, and re-checks the hash on
every fetch — the same contract as `Snapshot.open(verify=True)`, minus the
having-to-write-it. Pure Python, minimal dependencies, and its
[stated purpose](https://www.fatiando.org/pooch/latest/sample-data.html) is
"a package needs to ship sample data." It would add remote hosting, so
snapshots would not have to live in the repository.

What it does not have is the manifest as a *committed artifact*. Pooch's
registry is a hash list; this project's `manifest.json` also records
`snapshot_id`, `created`, `source_commit`, the `criteria` that produced the
slice, and per-file `rows`. That provenance block is the thing `results.json`
quotes back.

[**DVC**](https://dvc.org) is the heavyweight answer: pointer files in git,
content-addressed storage in S3/GCS/local, plus pipelines (`dvc repro`) and
metric diffs. Real capability — remote storage, lineage, cached
re-execution — at the price of a CLI, a cache and a configured remote.
lakeFS's comparison pages report that DVC now sits under the same ownership as
lakeFS.

[**lakeFS**](https://lakefs.io) and **Quilt** version data by git-like commits
over object storage, each commit an immutable snapshot. Both are sized for data
lakes. This project's largest snapshot is 66,332 routes.

### Experiment — configuration in, results out

[**Hydra**](https://hydra.cc) is the direct upgrade over `experiment.toml`:
composable configuration, per-run output directories, and multirun sweeps. The
sweep parameters already sitting in `experiments/astar-consistency/experiment.toml`
— `seeds = 50`, `max_order = 25`, `density = 3` — are exactly what Hydra's
multirun exists for, and `run.py` would stop looping over them by hand.

[**MLflow**](https://mlflow.org) logs parameters, metrics and artifacts per run,
records the git commit, and gives you a UI to compare runs. The trade-off is
architectural and appears in every comparison of the two: MLflow centralizes run
metadata in a tracking store, where DVC distributes it across git commits.
Centralizing is the opposite of this project's arrangement, in which the result
*is* a file next to the code that produced it.

[**Sacred**](https://github.com/IDSIA/sacred) is the older library closest in
spirit — a decorator that captures configuration and provenance per run.

[**benchlog**](https://github.com/williamtbarker/benchlog) turned up in the
search as an almost line-for-line match for what is here: a local tracker with
atomic manifests, artifact SHA-256 and byte size, and git commit, branch and
dirty state. Small and unproven, but the same idea arrived at independently,
which is at least evidence the idea is not eccentric.

### Catalog — a named, filtered view

[**Kedro**](https://kedro.org)'s Data Catalog is the named equivalent: a
declarative dataset registry over local and cloud filesystems, wrapped in a
project template with pipelines and Kedro-Viz. It is hosted by LF AI & Data and
has roughly 10,800 GitHub stars.

It replaces the *registry* half of `Catalog` and none of the rest.
`Catalog`'s distinguishing behaviour — the three
[endpoint modes](experiments.md#the-three-endpoint-modes), the
[narrowing chain](experiments.md#narrowing) that `summary()` hands back, the
[dangling-edge warning](experiments.md#dangling-edges) — is about routes and
airports. No framework knows what a dangling edge is.

### Orchestration — not currently a concern

Nothing here re-executes on a dependency graph; `make` and a `run.py` per
experiment do the job. If that changes, the field is
[Snakemake](https://snakemake.github.io),
[Ploomber](https://ploomber.io) and
[pytask](https://pytask-dev.readthedocs.io), and
[awesome-pipeline](https://github.com/pditommaso/awesome-pipeline) is the
catalogue.

## 3. Summary

| Concern | Closest package | Adds | Costs |
|---|---|---|---|
| Snapshot | Pooch | Remote hosting, cache management, a tested hash path | Manifest provenance moves out of the registry |
| Snapshot (large) | DVC, lakeFS | Object-store versioning, lineage, pipeline caching | A CLI, a cache, a configured remote |
| Experiment config | Hydra | Composition, sweeps, per-run output dirs | A new configuration model to learn |
| Experiment record | MLflow, Sacred | Run comparison, a UI, metric history | Results leave git for a tracking store |
| Catalog | Kedro | A cloud-aware dataset registry, pipelines, Viz | A project layout; no domain narrowing |

No single package covers all four. The realistic substitution is **Pooch +
Hydra**, or **DVC + MLflow** for the full stack. The comparisons cited above
make the same point from the other side: teams running these tools in 2026
typically run two or three of them together. That is the honest measure of what
"just use the standard tool" would cost here.

## 4. What this project would give up

Each of these is a property the current arrangement has and the alternatives
weaken:

- **One runtime dependency.** The wheel installs into an existing Colab or
  cluster environment without forcing an upgrade, because it asks for pandas
  and nothing else. DVC, MLflow and Kedro each bring a substantial tree.
- **`git clone` is the whole setup.** No remote to configure, no cache to warm,
  no tracking server to reach. That is why
  [running an experiment in Colab](experiments.md#8-running-in-colab) is three
  lines of Python.
- **The result is a readable file.** `results.json` can be diffed in a pull
  request, and the review sees the numbers change. A tracking store cannot be
  reviewed this way.
- **It is the subject matter.** This is a project *about* how to make a result
  reproducible. Machinery that a reader can read in an afternoon teaches the
  idea; an adopted framework teaches the framework.

## 5. What would change the answer

Written down so the decision can be revisited on evidence rather than taste:

- **Snapshots outgrow git.** The full network snapshot is a few megabytes
  today. At hundreds, the CSVs stop belonging in the repository and Pooch or
  DVC becomes the obvious answer rather than the heavier one.
- **Sweeps outgrow hand-written loops.** `astar-consistency` already loops over
  50 seeds inside `run.py`. A second or third experiment doing the same is the
  argument for Hydra multirun.
- **Runs need comparing across time.** `results.json` records one run. The
  moment the question becomes "how has this number moved over twenty runs,"
  MLflow's premise starts to pay.
- **Someone else has to reproduce this at scale.** For one reader with a
  laptop, files in git win. For a team with a cluster, they do not.

Until then the machinery stays, and this page is the record of the alternatives
that were considered and why they were not adopted.

## See also

- [Experiments](experiments.md) — the full reference for the machinery this
  page compares against
- [Setup](setup.md) — the dependency groups, and what the wheel actually
  declares
- [Validating against NetworkX](networkx-validation.md) — the one place the
  project *did* adopt an outside package, and the reasoning that justified it
