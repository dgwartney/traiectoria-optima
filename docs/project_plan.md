# A1: Flight Route Planner

**Course:** SJSU CMPE 180A, Fall 2026 — Prof. Sanja Damjanovic
**Group / DSA area:** Group A — Graphs & Traversal
**Stretch concept (self-learn):** Dijkstra's algorithm with a from-scratch min-heap, and A* search with an admissible haversine heuristic

## Group Members

- Astha Sharma-Flores => ASF
- Jake Lu => JL
- David Gwartney => DG

## Project Plan

Given the worldwide airline network (airports + routes), find the cheapest / shortest / fewest-stop route between two airports, and show that informed search (A*) expands fewer nodes than uninformed search (BFS/Dijkstra) while returning the same answer.

We build a `RoutePlanner` on top of the OpenFlights airports + routes dataset (~3,300 airports, ~67,000 routes), scoped to U.S. airports and their domestic/international routes for this project. The core graph, BFS, Dijkstra (with a hand-rolled binary min-heap), and A* (with a haversine distance heuristic) are all implemented from scratch using Python dictionaries, sets, lists, and `deque`. Libraries (`pandas`, `sqlite3`, `NetworkX`, `matplotlib`/`folium`) are used only for data loading, validating our results, and visualization — never as a substitute for the required algorithms.

Data collection and cleaning is already underway: `airports.dat` and `routes.dat` (OpenFlights) and `airports.csv` (OurAirports) have been loaded into a SQLite database (`data/processed/flight_data.db`) via `src/data/flight_data.py`, and a query for large/medium U.S. airports exists in `src/sql/airports.sql`. This gives the team a head start on Stage 1.

### Tasks

Organized by the four required implementation stages (see `general references` in the course intro doc for per-stage rubric).

| # | Stage | Task | Assigned To | Status |
|---|-------|------|-------------|--------|
| 1 | Stage 1 — Foundation | Finalize the U.S. airport subset (large/medium airports, valid IATA codes, no null coordinates) and the routes that connect them; export a clean `nodes` (airports) and `edges` (routes) table from `flight_data.db`. | TBD | Not Started |
| 2 | Stage 1 — Foundation | Compute great-circle edge weights between connected airports using the haversine formula. | TBD | Not Started |
| 3 | Stage 1 — Foundation | Build the `RoutePlanner` graph as an adjacency list (`dict[airport] -> list[(neighbor, weight)]`) loaded from the cleaned data. | TBD | Not Started |
| 4 | Stage 1 — Foundation | Report basic graph statistics (airport count, route count, average degree, disconnected airports, min/max edge distance). | TBD | Not Started |
| 5 | Stage 1 — Foundation | Write unit tests on a small hand-built mini-graph (including empty, single-airport, disconnected, and duplicate-route cases). | TBD | Not Started |
| 6 | Stage 1 — Foundation | Draft and submit the one-page project proposal for instructor approval. | TBD | Not Started |
| 7 | Stage 2 — Core algorithm | Implement BFS for fewest-stop (unweighted) routing. | TBD | Not Started |
| 8 | Stage 2 — Core algorithm | Implement a from-scratch binary min-heap (no `heapq`). | TBD | Not Started |
| 9 | Stage 2 — Core algorithm | Implement Dijkstra's algorithm using the custom heap for cheapest/shortest-distance routing. | TBD | Not Started |
| 10 | Stage 2 — Core algorithm | Validate BFS and Dijkstra results against `NetworkX` on the same graph. | TBD | Not Started |
| 11 | Stage 2 — Core algorithm | Write unit tests covering known routes, unreachable airports, and ties. | TBD | Not Started |
| 12 | Stage 3 — Stretch + features | Implement the haversine admissible heuristic for A*. | TBD | Not Started |
| 13 | Stage 3 — Stretch + features | Implement A* search using the custom heap and heuristic. | TBD | Not Started |
| 14 | Stage 3 — Stretch + features | Add secondary query features: fewest-stops vs. cheapest-distance mode switch, and a nearest-airports-to-a-point lookup. | TBD | Not Started |
| 15 | Stage 3 — Stretch + features | Argue/verify admissibility of the haversine heuristic (heuristic never overestimates true distance). | TBD | Not Started |
| 16 | Stage 4 — Evaluation | Build a benchmark suite comparing nodes expanded and runtime for BFS vs. Dijkstra vs. A* across a set of long-haul queries. | TBD | Not Started |
| 17 | Stage 4 — Evaluation | Produce an empirical runtime plot (time vs. input/graph size) and a nodes-expanded comparison table. | TBD | Not Started |
| 18 | Stage 4 — Evaluation | Render one route on a map (Folium/ipyleaflet) for the visualization deliverable. | TBD | Not Started |
| 19 | Stage 4 — Evaluation | Write the Big-O complexity analysis for the graph build, BFS, Dijkstra, and A*. | TBD | Not Started |
| 20 | Stage 4 — Evaluation | Assemble the final Jupyter notebook (consolidate code, results, and plots into a single runnable notebook). | TBD | Not Started |
| 21 | Stage 4 — Evaluation | Write the final report. | TBD | Not Started |
| 22 | Stage 4 — Evaluation | Prepare the presentation slides. | TBD | Not Started |
| 23 | Stage 4 — Evaluation | Prepare and rehearse the live demo. | TBD | Not Started |
| 24 | Cross-cutting | Set up `pytest` (or equivalent) test runner and CI-style `uv run` test command so unit tests from Stages 1–3 run consistently. `pytest` added as a dev dependency, `tests/` mirrors `src/`, and `[tool.pytest.ini_options]` in `pyproject.toml` wires up `testpaths`/`pythonpath`. Run with `uv run pytest`. | TBD | Done |
| 25 | Cross-cutting | Set up `ruff` lint/format checks on all new source code (dependency already present). | TBD | Not Started |
| 26 | Cross-cutting | Design the `RoutePlanner` public API/class interface (method signatures, inputs/outputs) before implementation so Stage 1–3 work integrates cleanly. | TBD | Not Started |
| 27 | Cross-cutting | Decide on and document airport/route edge cases to handle: multi-airport cities, codeshare duplicate routes, self-loops, and islands/Hawaii/Alaska connectivity. | TBD | Not Started |
| 28 | Cross-cutting | Update `docs/data.md` with the final cleaned schema used by `RoutePlanner` (post Stage-1 transformations), distinct from the raw OpenFlights/OurAirports schemas already documented. | TBD | Not Started |
| 29 | Cross-cutting | Track project risks/blockers (e.g., data gaps, scope creep) and revisit scope if the full worldwide graph proves too large for runtime experiments. | TBD | Not Started |
| 30 | Cross-cutting | Set up a shared task tracker (e.g., GitHub Issues/Projects) mirroring this task list, with owners and due dates once assigned. | TBD | Not Started |
| 31 | Cross-cutting | Establish a regular team check-in cadence and a shared meeting-notes doc. | TBD | Not Started |
| 32 | Cross-cutting | Define and agree on a git workflow (branch naming, PR review before merging to `main`). | TBD | Not Started |
| 33 | Cross-cutting | Build a small CLI or notebook widget for interactively querying routes (origin, destination, mode) to support the live demo. | TBD | Not Started |
| 34 | Cross-cutting | Do a peer code review pass across all three algorithm implementations (BFS, Dijkstra, A*) before Stage 4 evaluation begins. | TBD | Not Started |
| 35 | Cross-cutting | Dry-run the full notebook end-to-end (fresh environment, `uv sync`) to confirm reproducibility before submission. | TBD | Not Started |
| 36 | Cross-cutting | Prepare Q&A talking points / anticipated questions for the demo and presentation. | TBD | Not Started |
| 37 | Cross-cutting | Confirm all deliverables against the syllabus/rubric checklist (proposal, tests, complexity write-up, runtime study, visualization, notebook, slides, demo, report) before final submission. | TBD | Not Started |

### Roles and Responsibilities

- Astha Sharma-Flores
    * TBD

- Jake Lu
    * TBD

- David Gwartney
    * TBD
