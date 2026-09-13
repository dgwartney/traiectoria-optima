# Traiectoria Optima

Documentation site for the Traiectoria Optima project.

## Start here

- [Where we are](status.md) — a dated picture of the code, the documentation
  and what is left: which branch holds what, what has been verified, and the
  seven remaining items measured against the requirements. Read this first if
  you have been away from the repository.
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

## Deliverables

- [Final report](report/README.md) — one file per chapter, assembled into a
  PDF by `make report`. §1, §2, §6 and §7 are written; the rest are
  outlines.
- [Report and deck crosswalk](report-deck-crosswalk.md) — the report and the
  presentation are two renderings of one body of committed evidence. This says
  which chapter each slide derives from, what is transcription rather than
  research, and the nine places the deck disagreed with the code. Read it
  before writing any chapter or any slide.

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
- [Visualization](visualization.md) — the design behind `flight_planner.viz`, the
  class-based mapping layer that lets every experiment draw its answer the same
  way: measured Folium costs on both the 7,005-route and 66,332-route snapshots,
  the geodesic and antimeridian problems with the pictures to prove them, a
  comparison against the alternatives, and what building it taught that designing
  it had not. Demonstrated by `experiments/route-map/`.
- [Search instrumentation: design](design-search-instrumentation.md) — why
  `find_path` became `search` returning a `SearchResult`, the eight decisions
  behind the counters and `SearchObserver`, what was deliberately left out,
  and the seven discrepancies found by checking the plan against the code.
- [Search instrumentation: evaluation](evaluation-search-instrumentation.md) —
  how to re-run every number in the comparison table and the runtime plot,
  what may legitimately differ between machines, and what would be a real
  failure.
- [Distance Formulas](distance_formulas.md) — haversine, Vincenty, and the
  trade-offs between them.
- [Graph Algorithm Notes](graph-algorithms-notes.md) — Dijkstra, BFS and A\*.
- [Validating against NetworkX](networkx-validation.md) — seven ways to check
  the hand-written algorithms against an independent implementation, from a
  single oracle class to a second engine behind the Strategy interface, and
  the A\* heuristic-consistency gap that randomized testing surfaced.
- [Validation against NetworkX: results](results-networkx-parity.md) — what
  `experiments/networkx-parity` found: 200 long-haul queries over the world
  network, three algorithms, zero disagreements, and why NetworkX's timings
  are not a fair race. Written for the final report.
- [A\* and heuristic consistency: results](results-astar-consistency.md) —
  what `experiments/astar-consistency` found: A\* is optimal only for
  *consistent* heuristics, the four-vertex graph that shows it, and the
  658,470 checks proving it cannot bite this project. Written for the final
  report.
- [Glossary](glossary.md) — aviation and graph terms used throughout.
