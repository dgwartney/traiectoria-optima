# Demos

`src/demos/` holds runnable example scripts — one idea each, printed to stdout.
They are not part of the package: the wheel contains `flight_planner` and
nothing else, so a demo is something you run from a clone of this repository,
not something `pip install` gives you.

That separation is deliberate. Each demo imports `flight_planner` exactly the
way an outside consumer would, with no path manipulation and no knowledge of
the package's internals, so the set of them doubles as a check that the
re-exports in `__init__.py` are right and that the package really is usable
from outside its own source tree.

Run any of them from anywhere:

```bash
uv run python src/demos/dijkstra_example.py
```

## The catalogue

| File | Demonstrates |
|---|---|
| `dijkstra_example.py` | Default weighted-shortest-path search |
| `bfs_example.py` | Fewest-hops search, contrasted with Dijkstra |
| `astar_example.py` | A\* guided by `haversine_heuristic()`, the package's one admissible heuristic |
| `custom_distance_formula_example.py` | Adding a new `DistanceFormula` (`Equirectangular`) without touching `Point`/`Haversine`/`Vincenty` |
| `custom_edge_weight_example.py` | Adding a new `Edge` subclass weighted by duration instead of distance |
| `end_to_end_example.py` | All three algorithms over one six-airport network, and the measurement showing that swapping `DistanceFormula` changes admissibility rather than merely precision |
| `book_example.py` | The seven-airport flight network from Goodrich, Tamassia & Goldwasser, *Data Structures and Algorithms in Python*, hand-built and run through all three algorithms |
| `loader_example.py` | Building a planner from the processed CSV files instead of by hand |
| `snapshot_example.py` | Opening a frozen snapshot, and the checksum guarantee it carries |
| `catalog_example.py` | Narrowing a snapshot to a scope, and what each narrowing cost |
| `route_query_example.py` | The whole route-lookup surface on real data: airports, routes, the three query modes, and how a failed lookup reports itself |
| `experiment_example.py` | Reading, running and recording an experiment against pinned data |
| `script_experiment_example.py` | An experiment written as a `.py` script rather than a notebook, and why it must locate itself |
| `search_instrumentation_example.py` | What a search cost — `SearchResult` counters, `ExpansionTrace`, and writing your own `SearchObserver` |

## 1. Hand-built networks

The first group builds a small graph inline, with distances written into the
source. Nothing is loaded, so what each algorithm does is visible in one
screen.

- **`dijkstra_example.py`** — three airports where the direct JFK–LAX leg is
  longer than the two-hop route through Chicago, which is the smallest network
  that makes "shortest" mean something other than "fewest".
- **`bfs_example.py`** — the same shape, asked the other question.
- **`astar_example.py`** — A\* over that network with a Haversine heuristic
  wrapped in `Memoized`, and a check that it agrees with Dijkstra.
- **`end_to_end_example.py`** — six international airports with real
  coordinates, run through all three algorithms, then A\*'s heuristic swapped
  from Haversine to Vincenty to show that changing the `DistanceFormula`
  changes only the heuristic's precision, not any interface.
- **`book_example.py`** — the seven-airport flight network transcribed by hand
  from Goodrich, Tamassia and Goldwasser, *Data Structures and Algorithms in
  Python*, distances and all, so its output can be checked against the worked
  example in the book.

## 2. Extending the package

Both of these add a class from outside the package and hand it to unmodified
library code — the point being that neither requires touching `Graph`, `Point`,
or any existing algorithm.

- **`custom_distance_formula_example.py`** — implements `Equirectangular` and
  passes it wherever `Haversine` or `Vincenty` would go.
- **`custom_edge_weight_example.py`** — subclasses `Edge` so that `weight`
  means flight duration rather than distance. Every `PathfindingAlgorithm`
  works with it unchanged, because they only ever read `edge.weight`.
- **`search_instrumentation_example.py`** — subclasses `SearchObserver` to
  narrate a search as it runs. It also shows the two built-in ways to see what
  a search cost: the `SearchResult` counters every algorithm returns, and
  `ExpansionTrace`, which records the order vertices were reached in.

  Its eight-airport network is a corridor from SFO east to BOS plus a spur
  running the wrong way, out over the Pacific. That geometry is the whole
  point: the spur is *near the start* and *far from the goal*, so Dijkstra
  expands OGG and HNL while A\* never looks at them — the same effect that
  takes A\* from 92 expansions to 1 on the real SFO→BOS query.

## 3. Real data

- **`loader_example.py`** — builds a planner from `data/processed/` through
  `AirportLoader` and `RouteLoader`, and reports how many rows each loader
  skipped. This reads *build output*, which `make flight_network` rewrites —
  which is the problem the experiment machinery exists to solve.

## 4. Experiments

These three cover [the experiment model](experiments.md) end to end, against
this repository's own snapshots. Read them in order; each one picks up where
the last left off.

- **`snapshot_example.py`** — lists the available snapshots, opens the full
  network with verification on, and reports what the manifest records about
  it: the id, the commit it was generated from, the criteria that produced it.
  It then copies the snapshot to a temporary directory, appends a single byte
  to `routes.csv`, and shows the reopen failing with `SnapshotIntegrityError`.
  The checksum guarantee is the whole point of a snapshot, so the demo
  exercises it rather than describing it.
- **`catalog_example.py`** — the lookup vocabulary (`airport`, `flight`,
  `route`, `routes_between`, `routes_from`), including `route('SFO', 'BOS')`
  refusing to guess between the three carriers that fly it. Then the narrowing
  chain `airline('UA').airport_type('large').country('US')` with the counts it
  reports at each step, a measured comparison of the three endpoint modes, a
  demonstration that the default mode commutes, and the `UserWarning` raised
  when a scope's routes reach outside it.
- **`route_query_example.py`** — the demo to read if you want to *use* the
  package rather than understand it. Opens the world snapshot, looks an airport
  up and prints its descriptive fields, asks for its departures and arrivals
  (`routes_from` / `routes_to`) and the carriers on one pair, then runs all
  three query modes over SFO–BOS and prints each cost **with the unit it is
  measured in** — BFS's is a hop count, the others' kilometres — alongside the
  nodes each search expanded. It closes by showing the three ways a lookup can
  fail, all catchable as one `FlightPlannerError`, and repeating the query on a
  narrowed network. Its functions are written to be imported as readily as run,
  so a notebook cell can call `open_catalog()` and `compare_modes()` directly.
- **`experiment_example.py`** — reads the committed
  `experiments/sfo-bos-dijkstra` *without running it*, to show what
  `experiment.toml` declares and what its `results.json` recorded. It then
  scaffolds a second experiment in a temporary directory, narrows the snapshot
  exactly as that experiment's parameters declare, compares the fewest-hops
  and shortest-distance itineraries, and records the result — so the write
  path is demonstrated without overwriting a committed run.

- **`script_experiment_example.py`** — the same machinery with no notebook in
  sight. `notebooks` in `experiment.toml` is a list of filenames and nothing
  checks the extension, so this builds a throwaway experiment whose code is a
  `run.py` sitting beside the config, then runs that script *as its own
  process from an unrelated working directory* — proof that
  `Experiment.open(Path(__file__).resolve().parent)` finds the experiment when
  the cwd cannot. It finishes by running the same script with `Path.cwd()`
  substituted in, so the resulting `FileNotFoundError` is shown rather than
  described. See [Experiments
  §6](experiments.md#it-does-not-have-to-be-a-notebook).

## Conventions

A demo that follows these can be read as a worked example rather than as a
script with local habits:

- **A module docstring saying what it demonstrates**, ending with the
  `uv run python src/demos/<name>.py` line that runs it.
- **No cwd assumptions.** A demo that needs repository data locates it
  relative to `__file__`, because the package itself takes directories from its
  caller and a demo should not undercut that.
- **Everything under `if __name__ == "__main__":`**, so importing a demo does
  not run it.
- **Read-only against committed state.** A demo that needs to write — or to
  corrupt something, as `snapshot_example.py` does — works on a copy in a
  temporary directory.
