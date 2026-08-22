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
- [`docs/report.md`](docs/report.md) — outline for the final report.
- [`docs/data.md`](docs/data.md) — OpenFlights airport/route data schemas.
- [`docs/airlines.md`](docs/airlines.md) — background on U.S. carriers and hubs.
- [`docs/software.md`](docs/software.md) — mapping/visualization libraries under consideration.

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
airports data into a SQLite database at `data/processed/flight_data.db`; run
it directly with:

```bash
uv run python src/data/flight_data.py
```

`src/sql/airports.sql` contains a starter query for filtering to U.S.
large/medium airports. See [`docs/data.md`](docs/data.md) for the full column
schemas of the raw OpenFlights files.
