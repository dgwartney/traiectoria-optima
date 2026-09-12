# Traiectoria Optima

Documentation site for the Traiectoria Optima project.

## Start here

- [Tutorial](tutorial.md) — build one experiment end to end, in half an hour:
  freeze a slice of the data, ask a question of it, and record the answer next
  to the data that produced it. Start here if you would rather learn by doing.
- [Setup](setup.md) — installing `uv`, getting the dev environment running,
  running the notebooks, and using the package from
  [Google Colab](setup.md#6-google-colab).
- [Experiments](experiments.md) — the model this project uses to keep results
  reproducible: immutable snapshots, the `Catalog` narrowing vocabulary, and
  experiment directories that record what produced each number.
- [Demos](demos.md) — the runnable example scripts in `src/demos/`, what each
  one shows, and the conventions they follow.

## Reference

- [Package design](../src/flight_planner/README.md) — how `flight_planner` is
  layered, why it composes rather than inherits, and where to hook in a new
  algorithm, distance formula or edge weight. It ships inside the wheel, so it
  describes the installed package rather than this repository.
- [Flight Planner](flight_planner.md) — the guided tour of `Airport`, `Route`
  and `FlightPlanner`, the `Vertex`/`Edge`/`Graph` classes they derive from,
  and how to extend them. Start here if you want to use the library directly
  rather than run an experiment.
- [Data](data.md) — the raw OpenFlights and OurAirports schemas, the Wikipedia
  international-airports scrape, and the processed dataset the pipeline builds.
- [Makefile](makefile.md) — every target (`make test`, `make flight_network`,
  `make snapshot`, `make experiment`, ...) and how the dependency tracking
  works.
- [Documentation Standard](documentation-standard.md) — how code in this
  project is documented.
- [Distance Formulas](distance_formulas.md) — haversine, Vincenty, and the
  trade-offs between them.
- [Graph Algorithm Notes](graph-algorithms-notes.md) — Dijkstra, BFS and A\*.
- [Validating against NetworkX](networkx-validation.md) — six ways to check
  the hand-written algorithms against an independent implementation, from a
  twenty-line adapter to a second engine behind the Strategy interface, and
  the A\* heuristic-consistency gap that randomized testing surfaced.
- [Glossary](glossary.md) — aviation and graph terms used throughout.
