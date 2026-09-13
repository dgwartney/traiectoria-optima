# Traiectoria-optima

Class project for San Jose University graduate course CMPE-180A

## About the name

_Traiectoria-optima_ is a Latin phrase that translates directly to "optimal trajectory" or "best path."

It combines two classical Latin roots:

- **Traiectoria** (from traiicere): A crossing, passage, or path described by a moving object.

- **Optima** (feminine form of optimus): Best, most favorable, or ideal.

## Term Project (CMPE 180A, Fall 2026)

This repo implements **A1: Flight Route Planner** — a from-scratch graph
search over the OpenFlights airline network (BFS, a hand-rolled binary
min-heap + Dijkstra, and A* with an admissible haversine heuristic).

- [`docs/project_plan.md`](docs/project_plan.md) — project description, task
  breakdown by implementation stage, and team roles/responsibilities.
- [`docs/report/`](docs/report/README.md) — the final report, one file per chapter.
  `make report` assembles them into `build/pdf/report.pdf`.
- [`docs/data.md`](docs/data.md) — OpenFlights airport/route data schemas.
- [`docs/airlines.md`](docs/airlines.md) — background on U.S. carriers and hubs.
- [`docs/visualization.md`](docs/visualization.md) — the design of the
  mapping layer: measured Folium costs, the geodesic and antimeridian
  problems, and why the alternatives were not used.

## Development Environment Setup with `uv`

This project uses [uv](https://docs.astral.sh/uv/) to manage the Python
interpreter, the virtual environment, and the locked dependency set
(`pyproject.toml` + `uv.lock`). See
[`docs/setup.md`](docs/setup.md) for the full walkthrough: installing `uv`,
`uv sync`, running commands with `uv run`, managing dependencies, running
tests, and troubleshooting. Quick start:

```bash
uv sync
uv run pytest
```

`uv sync` installs the runtime dependency and the `dev` group. JupyterLab and
the mapping stack are in the `notebooks` group, so running the notebooks needs
`uv sync --group notebooks` (or `--all-groups`).

## Using the package elsewhere

`flight_planner` is an installable package whose only third-party dependency
is `pandas`, so it can be used outside this checkout — from Google Colab, for
example — without pulling in the development environment:

```bash
pip install git+https://github.com/dgwartney/traiectoria-optima.git
```

The processed CSV files are data rather than package contents, and the loaders
take their paths from the caller, so a clone is still needed to supply them.
See [Google Colab](docs/setup.md#6-google-colab) for the two-cell recipe and
the pitfalls that are easy to hit there.

## Makefile

Common `uv run` commands are wrapped in the top-level `Makefile`. Run
`make help` for the full list of targets, or see
[`docs/makefile.md`](docs/makefile.md) for how its dependency tracking
works.

## Data Sets

- [Open Flights](https://openflights.org/data.php)

- [Our Airports](https://ourairports.com/data/)

Raw files for both sources live under `data/raw/`. `src/data/flight_data.py`
(`FlightDataToDB`) loads the OpenFlights airports/routes and OurAirports
airports data into a SQLite database at `data/processed/flight_data.db`. It
takes every input and output path as an argument, so build it through make,
which passes them:

```bash
make flight_data
```

`src/sql/flight_data.sql` derives the United Airlines tables from that database
and spools them out as `data/processed/{airports,routes}.csv` — `make
united_airlines_csv`. See [`docs/data.md`](docs/data.md) for the full column
schemas of the raw OpenFlights files, and for how international airport
coordinates are resolved.
