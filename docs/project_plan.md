# A1: Flight Route Planner

**Course:** SJSU CMPE 180A, Fall 2026 — Prof. Sanja Damjanovic
**Group / DSA area:** Group A — Graphs & Traversal
**Stretch concept (self-learn):** Dijkstra's algorithm with a from-scratch min-heap, and A* search with an admissible haversine heuristic

## Group Members

- Astha Sharma-Flores
- Jake Lu
- David Gwartney

## Project Plan

Given the worldwide airline network (airports + routes), find the cheapest / shortest / fewest-stop route between two airports, and show that informed search (A*) expands fewer nodes than uninformed search (BFS/Dijkstra) while returning the same answer.

We build a `RoutePlanner` on top of the OpenFlights airports + routes dataset (~3,300 airports, ~67,000 routes), scoped to U.S. airports and their domestic/international routes for this project. The core graph, BFS, Dijkstra (with a hand-rolled binary min-heap), and A* (with a haversine distance heuristic) are all implemented from scratch using Python dictionaries, sets, lists, and `deque`. Libraries (`pandas`, `sqlite3`, `NetworkX`, `matplotlib`/`folium`) are used only for data loading, validating our results, and visualization — never as a substitute for the required algorithms.

Data collection and cleaning is already underway: `airports.dat` and `routes.dat` (OpenFlights) and `airports.csv` (OurAirports) have been loaded into a SQLite database (`data/processed/flight_data.db`) via `src/data/flight_data.py`, and a query for large/medium U.S. airports exists in `src/sql/airports.sql`. This gives the team a head start on Stage 1.

### Tasks

Organized by the four required implementation stages (see `general references` in the course intro doc for per-stage rubric).

**Stage 1 — Foundation (data loader + core graph + stats + tests)**

1. Finalize the U.S. airport subset (large/medium airports, valid IATA codes, no null coordinates) and the routes that connect them; export a clean `nodes` (airports) and `edges` (routes) table from `flight_data.db`.
2. Compute great-circle edge weights between connected airports using the haversine formula.
3. Build the `RoutePlanner` graph as an adjacency list (`dict[airport] -> list[(neighbor, weight)]`) loaded from the cleaned data.
4. Report basic graph statistics (airport count, route count, average degree, disconnected airports, min/max edge distance).
5. Write unit tests on a small hand-built mini-graph (including empty, single-airport, disconnected, and duplicate-route cases).
6. Draft and submit the one-page project proposal for instructor approval.

**Stage 2 — Core algorithm (primary algorithm + tests + library validation)**

7. Implement BFS for fewest-stop (unweighted) routing.
8. Implement a from-scratch binary min-heap (no `heapq`).
9. Implement Dijkstra's algorithm using the custom heap for cheapest/shortest-distance routing.
10. Validate BFS and Dijkstra results against `NetworkX` on the same graph.
11. Write unit tests covering known routes, unreachable airports, and ties.

**Stage 3 — Stretch + features (self-learn concept + secondary features)**

12. Implement the haversine admissible heuristic for A*.
13. Implement A* search using the custom heap and heuristic.
14. Add secondary query features: fewest-stops vs. cheapest-distance mode switch, and a nearest-airports-to-a-point lookup.
15. Argue/verify admissibility of the haversine heuristic (heuristic never overestimates true distance).

**Stage 4 — Evaluation (runtime study + complexity + visualization + report + demo)**

16. Build a benchmark suite comparing nodes expanded and runtime for BFS vs. Dijkstra vs. A* across a set of long-haul queries.
17. Produce an empirical runtime plot (time vs. input/graph size) and a nodes-expanded comparison table.
18. Render one route on a map (Folium/ipyleaflet) for the visualization deliverable.
19. Write the Big-O complexity analysis for the graph build, BFS, Dijkstra, and A*.
20. Assemble the final Jupyter notebook (consolidate code, results, and plots into a single runnable notebook).
21. Write the final report.
22. Prepare the presentation slides.
23. Prepare and rehearse the live demo.

**Cross-cutting / supporting tasks**

24. ~~Set up `pytest` (or equivalent) test runner and CI-style `uv run` test command so unit tests from Stages 1–3 run consistently.~~ Done: `pytest` added as a dev dependency, `tests/` mirrors `src/`, and `[tool.pytest.ini_options]` in `pyproject.toml` wires up `testpaths`/`pythonpath`. Run with `uv run pytest`.
25. Set up `ruff` lint/format checks on all new source code (dependency already present).
26. Design the `RoutePlanner` public API/class interface (method signatures, inputs/outputs) before implementation so Stage 1–3 work integrates cleanly.
27. Decide on and document airport/route edge cases to handle: multi-airport cities, codeshare duplicate routes, self-loops, and islands/Hawaii/Alaska connectivity.
28. Update `docs/data.md` with the final cleaned schema used by `RoutePlanner` (post Stage-1 transformations), distinct from the raw OpenFlights/OurAirports schemas already documented.
29. Track project risks/blockers (e.g., data gaps, scope creep) and revisit scope if the full worldwide graph proves too large for runtime experiments.
30. Set up a shared task tracker (e.g., GitHub Issues/Projects) mirroring this task list, with owners and due dates once assigned.
31. Establish a regular team check-in cadence and a shared meeting-notes doc.
32. Define and agree on a git workflow (branch naming, PR review before merging to `main`).
33. Build a small CLI or notebook widget for interactively querying routes (origin, destination, mode) to support the live demo.
34. Do a peer code review pass across all three algorithm implementations (BFS, Dijkstra, A*) before Stage 4 evaluation begins.
35. Dry-run the full notebook end-to-end (fresh environment, `uv sync`) to confirm reproducibility before submission.
36. Prepare Q&A talking points / anticipated questions for the demo and presentation.
37. Confirm all deliverables against the syllabus/rubric checklist (proposal, tests, complexity write-up, runtime study, visualization, notebook, slides, demo, report) before final submission.

### Roles and Responsibilities

- Astha Sharma-Flores
    * TBD

- Jake Lu
    * TBD

- David Gwartney
    * TBD
