# Traiectoria Optima

Documentation site for the Traiectoria Optima project.

## Start here

- [Setup](setup.md) — installing `uv`, getting the dev environment running,
  running the notebooks, and using the package from
  [Google Colab](setup.md#6-google-colab).
- [Experiments](experiments.md) — the model this project uses to keep results
  reproducible: immutable snapshots, the `Catalog` narrowing vocabulary, and
  experiment directories that record what produced each number.

## Reference

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
- [Glossary](glossary.md) — aviation and graph terms used throughout.
