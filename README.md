# Traiectoria Optima

A from-scratch graph search over the OpenFlights airline network — BFS, a
hand-rolled binary min-heap with Dijkstra, and A* with an admissible haversine
heuristic — built as the term project (**A1: Flight Route Planner**) for San
José State University's CMPE 180A, Fall 2026.

_Traiectoria optima_ is Latin for "the best path": *traiectoria* (from
*traiicere*), the path traced by something crossing over; *optima*, best.

## Start here

**[`docs/index.md`](docs/index.md)** is the documentation home — the
project's data model, the experiment/snapshot machinery, the final report and
deck, and everything else lives off that page. In particular:

- [Where we are](docs/status.md) — a dated picture of what exists, what is
  verified, and what is left. Read this first if you're new to the repo.
- [Tutorial](docs/tutorial.md) — build one experiment end to end in about
  half an hour.
- [Setup](docs/setup.md) — installing `uv`, running the dev environment, and
  using the package from Google Colab.

## Quick start

```bash
uv sync
uv run pytest
```

See [`docs/setup.md`](docs/setup.md) for the full walkthrough, and
[`docs/makefile.md`](docs/makefile.md) (or `make help`) for the `make`
targets that wrap common commands.

## Using the package elsewhere

`flight_planner` is an installable package with one third-party dependency,
`pandas`, so it runs outside this checkout — from Google Colab, for example —
without the development environment:

```bash
pip install git+https://github.com/dgwartney/traiectoria-optima.git
```

See [Google Colab](docs/setup.md#6-google-colab) for the two-cell recipe.

## Data

Raw [OpenFlights](https://openflights.org/data.php) and
[Our Airports](https://ourairports.com/data/) files live under `data/raw/`;
`make flight_data` and `make flight_network` build the processed dataset from
them. See [`docs/data.md`](docs/data.md) for the schemas and how international
airport coordinates are resolved.
