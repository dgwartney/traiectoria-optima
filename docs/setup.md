# Development Environment Setup with `uv`

This project uses [uv](https://docs.astral.sh/uv/) to manage the Python
interpreter, the virtual environment, and the locked dependency set
(`pyproject.toml` + `uv.lock`). Python 3.12 or newer is required; `uv` will
download a suitable interpreter for you, so a pre-installed Python is not
needed.

## 1. Install `uv`

**macOS**

```bash
# Recommended: standalone installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv
```

Restart your shell (or `source ~/.zshrc`) so `uv` is on your `PATH`.

**Windows**

```powershell
# Recommended: standalone installer (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with winget
winget install --id=astral-sh.uv -e
```

Open a new PowerShell window afterwards so the updated `PATH` takes effect.

Verify the install on either platform:

```bash
uv --version
```

## 2. Clone the repository

```bash
git clone https://github.com/dgwartney/traiectoria-optima.git
cd traiectoria-optima
```

## 3. Create the environment and install dependencies

```bash
uv sync
```

This creates a `.venv` in the project root, installs the pinned Python
version, and installs the runtime dependency plus the `dev` group exactly as
recorded in `uv.lock`. Re-run `uv sync` any time you pull changes that touch
`pyproject.toml` or `uv.lock`.

Dependencies are split three ways, so that installing the `flight_planner`
package never drags in the whole working environment:

| Where | Contains | Installed by |
| --- | --- | --- |
| `[project.dependencies]` | `pandas` — the only third-party import in the package | always; the only entry published in the wheel |
| `dev` group | pytest, ruff, matplotlib, numpy, scipy, playwright | `uv sync` (default) |
| `notebooks` group | JupyterLab, ipykernel, folium, pyproj, ipyleaflet | `uv sync --group notebooks` |

Only the first is published in the wheel metadata, which is what lets the
package install into an existing environment without upgrading it. To get
everything at once:

```bash
uv sync --all-groups
```

## 4. Run things in the environment

The idiomatic approach is to prefix commands with `uv run` — no manual
activation required, and `uv` keeps the environment in sync automatically:

```bash
uv run python src/demos/end_to_end_example.py
uv run jupyter lab
```

If you prefer an activated shell:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (cmd.exe)
.venv\Scripts\activate.bat
```

Deactivate with `deactivate`.

## 5. Jupyter notebooks

JupyterLab lives in the `notebooks` dependency group, so install that group
before the first launch — a plain `uv sync` does not provide it:

```bash
uv sync --group notebooks
```

Then launch JupyterLab through `uv` so the kernel resolves to the project
environment:

```bash
uv run jupyter lab
```

Notebooks live in `notebooks/`. If a notebook does not see the project
packages, select the kernel that points at `.venv` (registered by the
`ipykernel` dependency), or register it explicitly:

```bash
uv run python -m ipykernel install --user --name traiectoria-optima
```

## 6. Google Colab

The package installs straight from the public repository, so a Colab notebook
needs no checkout of its own and no credentials. The clone is still required:
the CSV files are data, not package contents, and the loaders take their paths
from the caller.

Setup cell:

```python
!rm -rf /content/traiectoria-optima
!git clone --depth 1 https://github.com/dgwartney/traiectoria-optima.git /content/traiectoria-optima
!pip3 install -q /content/traiectoria-optima
```

Then the package is importable in the same session:

```python
from flight_planner import Dijkstra
from flight_planner.experiments import Snapshot

REPO = '/content/traiectoria-optima'
snapshot = Snapshot.open(f'{REPO}/data/snapshots/2026-09-11-bb90a8')
planner = snapshot.load_planner()      # every checksum verified here

distance, legs = planner.find_shortest_route('SFO', 'BOS', Dijkstra())
```

**Read a snapshot, not `data/processed/`.** The processed CSVs are build
output — `make flight_network` rewrites them — so a notebook that reads them
can produce a different answer on a later run with nothing to say the data
moved. A snapshot is frozen and checksummed: opening one proves you are reading
the bytes you think you are. See [Experiments](experiments.md).

Better still, if the work is a question worth recording, put it in an
experiment, which pins its own snapshot and records results next to the data's
identity:

```python
from flight_planner.experiments import Experiment

experiment = Experiment.open(f'{REPO}/experiments/sfo-bos-dijkstra')
planner = experiment.snapshot.load_planner()
experiment.record({'shortest_km': 4341.0, 'legs': 1})
```

To version a notebook written in Colab, commit from the clone — an experiment
directory is a normal part of the repository.

Four details make the difference between this working and not:

- **`!pip3` in a shell cell, `%pip` inside a notebook that installs for
  itself.** `!pip3 install` runs the shell's pip, which is what the setup cell
  above does. `%pip install` is IPython's magic: it installs into the kernel
  actually running the notebook, which is the safer form when the notebook is
  bootstrapping its own dependencies — and it is what the scaffolded experiment
  notebooks use. There is no `%pip3`; the magic picks the interpreter for you.

- **Do not use `pip3 install -e`.** An editable install works through a `.pth`
  file, and `.pth` files are executed only when the interpreter starts. The
  install reports success, then `import flight_planner` raises
  `ModuleNotFoundError` until the runtime is restarted. A plain install lands
  in `site-packages`, which is already on `sys.path`, and is importable
  immediately. Use `-e` only if you intend to edit the clone, and then restart
  the runtime (Runtime → Restart session) after every install.
- **`git clone` is not idempotent.** Re-running the cell without the `rm -rf`
  fails with `destination path ... already exists`, and because a `!` cell does
  not stop on error the install then runs against the stale tree. A
  `ModuleNotFoundError` in the import cell is usually this: check the setup
  cell's output for `fatal:`.
- **Nothing is upgraded.** The floors in `[project.dependencies]` are the
  oldest versions the test suite passes on, not the newest available, so the
  install leaves Colab's preinstalled pandas, numpy and matplotlib untouched
  and no runtime restart is needed.

As a fallback that skips installation altogether — the package imports only
pandas, which Colab already provides:

```python
import sys
sys.path.insert(0, '/content/traiectoria-optima/src')
```

## 7. Managing dependencies

```bash
uv add <package>                     # add a runtime dependency
uv add --dev <package>               # add to the dev group
uv add --group notebooks <package>   # add to the notebooks group
uv remove <package>                  # drop a dependency
uv lock --upgrade                    # refresh the lock to newest allowed versions
```

`uv add`/`uv remove` update both `pyproject.toml` and `uv.lock`; commit both
files together.

Add to `[project.dependencies]` only what the `flight_planner` package itself
imports — everything published there becomes a requirement for anyone
installing the wheel. Tooling, notebook and analysis packages belong in a
group.

## 8. Running tests

Tests are written with `pytest` (a dev dependency) and live under `tests/`,
mirroring the layout of `src/`:

```
tests/
├── conftest.py                  # matplotlib backend, data-path and snapshot fixtures
├── data/
│   ├── test_flight_data.py      # FlightDataToDB: paths, loaders, SQLite writes
│   ├── test_flight_network.py   # the pandas transform: numbering, resolution, output
│   └── test_international_airports.py
├── exercises/
│   ├── algorithms/
│   │   └── test_exercise_dijkstra.py
│   └── graphs/
│       └── test_adjency_list.py
├── flight_planner/              # the graph core, pathfinding, distances, CSV loader
│   ├── test_vertex.py
│   ├── test_edge.py
│   ├── test_graph.py
│   ├── test_point.py
│   ├── test_airport.py
│   ├── test_route.py
│   ├── test_flight_planner.py
│   ├── test_haversine.py
│   ├── test_vincenty.py
│   ├── test_memoized.py
│   ├── test_dijkstra.py
│   ├── test_bfs.py
│   ├── test_astar.py
│   ├── test_loader.py
│   └── experiments/             # Snapshot, Catalog, Experiment
│       ├── test_snapshot.py
│       ├── test_catalog.py
│       └── test_experiment.py
├── scripts/                     # the snapshot and experiment generators
│   ├── test_new_snapshot.py
│   └── test_new_experiment.py
├── experiments/
│   └── test_committed.py        # the committed snapshots and experiments still work
└── models/
    └── flight/                  # aircraft performance and the gate-to-gate simulator
        ├── test_atmosphere.py
        ├── test_aircraft.py
        ├── test_wind.py
        ├── test_simulator.py
        └── test_payload_range.py
```

Run the full suite with:

```bash
uv run pytest
```

`testpaths` and `pythonpath` are configured in `[tool.pytest.ini_options]` in
`pyproject.toml`. `pythonpath` is needed because the modules under
`src/models/flight/`, `src/data/` and `src/exercises/` still import each other
with bare (non-package) imports, so those directories are added to `sys.path`
for test discovery.

`src/flight_planner/` is **not** among them. It is a real package with an
`__init__.py`, installed into the environment by `uv sync` (see the
`[build-system]` and `[tool.hatch.build.targets.wheel]` blocks in
`pyproject.toml`), so `import flight_planner` resolves from any working
directory without a `sys.path` entry. That is also why the demo scripts in
`src/demos/` need no path manipulation to run.

Because the remaining `sys.path` entries are import roots, no two of them may
contain a directory of the same name — the first one found wins and shadows the
rest. This once broke test collection, when two roots each held a directory
called `examples/`; they were renamed to `src/exercises/` and `src/demos/` to
retire the name.

## Troubleshooting

- **`uv: command not found` / not recognized** — reopen the terminal so the
  installer's `PATH` change applies.
- **PowerShell blocks the install script** — run it in the form shown above,
  which sets `-ExecutionPolicy ByPass` for that single invocation only.
- **Environment feels stale or broken** — delete `.venv` and run `uv sync`
  again; the lock file makes this cheap and reproducible.

## Makefile

The most common `uv run` commands are wrapped in the top-level `Makefile` —
run `make help` for the full list, or see [Makefile](makefile.md) for how it
works.
