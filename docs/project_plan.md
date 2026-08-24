---
title: "A1: Flight Route Planner"
subtitle: "Project Plan"
author: "Aastha Sharma-Flores, Jake Lu, David Gwartney"
date: 2026-08-23
---

# A1: Flight Route Planner — Project Plan

**Course:** SJSU CMPE 180A, Fall 2026 — Prof. Sanja Damjanovic

**Team:** Aastha Sharma-Flores (ASF) · Jake Lu (JL) · David Gwartney (DG)

**Group / DSA area:** Group A — Graphs & Traversal

**Stretch concept (self-learn):** Dijkstra with a from-scratch binary min-heap, and A*
search with an admissible haversine heuristic

**Presentation:** 9/15/2026

## Problem

As stated in the project catalog:

> Given the world airline network, find the cheapest / shortest / fewest-stop route
> between two airports, and show how informed search (A*) expands fewer nodes than
> uninformed search (BFS/Dijkstra) while returning the same answer.

**How we define cost.** OpenFlights carries no fare data, and the catalog's Outcomes for
A1 call for "a `RoutePlanner` supporting hops/distance queries." We therefore read
*cheapest* in the graph sense — lowest total edge cost — with edge cost equal to
great-circle (haversine) distance. This gives three query modes:

| Query | Metric | Edge weight | Algorithm |
|-------|--------|-------------|-----------|
| Fewest stops | Layovers | Uniform (1 per hop) | BFS |
| Cheapest / shortest | Total great-circle distance | Haversine | Dijkstra |
| Cheapest / shortest, accelerated | Total great-circle distance | Haversine + heuristic | A* |

A* returns the same route as Dijkstra while expanding fewer nodes — the result the project
asks us to demonstrate.

The graph, BFS, Dijkstra, the min-heap, and A* are built from scratch using Python dicts,
sets, lists, and `deque`; `heapq` is not used, since our own min-heap is the stretch
concept. `pandas`, `sqlite3`, `NetworkX`, `matplotlib`, and `folium` are used only for
loading, validating our results, and plotting — never as a substitute for a required
algorithm.

**To confirm at office hours:**

1. Whether distance-as-cost satisfies "cheapest," or a separate cost model is wanted;
2. Whether scoping the graph to large/medium U.S. airports is acceptable, given the catalog says "world airline network" and asks for long-haul
queries.

## Deliverables

| # | Deliverable | Slides | Owner |
|---|-------------|--------|-------|
| T1 | Cleaned OpenFlights airport/route dataset in SQLite, exported as node and edge tables, with dataset statistics and EDA charts | 7, 13 | DG |
| T2 | `RoutePlanner` graph core: adjacency list, haversine edge weights, public API, and reported graph statistics | 8, 10, 11, 14, 15 | ASF |
| T3 | From-scratch array-backed binary min-heap (no `heapq`) | 9, 16 | DG |
| T4 | Test suite: hand-built mini-graph plus the required empty, single-element, cyclic/duplicate, and disconnected cases | new slide | JL |
| T5 | BFS fewest-stops search with path reconstruction, reachability validated against NetworkX | 5, 17 | JL |
| T6 | Dijkstra shortest-distance search running on our own min-heap, validated against NetworkX | 5, 18 | ASF |
| T7 | A* search with the haversine heuristic, plus the written admissibility argument | 5, 19 | ASF |
| T8 | Evaluation: BFS/Dijkstra/A* comparison table (nodes expanded and runtime) on long-haul queries, runtime-vs-input-size plot, Big-O write-up, and one rendered route map | 6, 12, 20 | JL |
| T9 | Runnable notebook/CLI and live demo, assembled slide deck, and final report | 1, 2, 3, 4, 21, 22 | DG |

Owners above are for *building* each deliverable, and are a proposed starting point to be
confirmed by the team.

**Sequencing.** T1 → T2 unblocks all search work. T3 must land before T6 (Dijkstra
consumes the heap); the heap interface is agreed up front so both proceed in parallel.
T5, T6 and T7 must all work before T8 can benchmark. T9 closes.

**Cross-cutting.** Agree the `RoutePlanner` API before T5–T7 start; `pytest` (already set
up) and `ruff` for all code; PR review before merging to `main`. Deck fixes: add a
testing/validation slide, state on slide 6 that "cost" means great-circle distance, and
drop the Stack/DFS panel from slide 9.

## Presenting

All three members deliver a portion of the presentation. Each speaks to the work they
built, so preparation doubles as rehearsal.

| Presenter | Slides | Covering |
|-----------|--------|----------|
| DG | 1–4, 7, 9, 13, 16 | Opening and motivation, dataset and pipeline, min-heap, live demo |
| ASF | 8, 10, 11, 14, 15, 18, 19 | Distance formulas, system design, adjacency list, core API, Dijkstra, A* |
| JL | 5, 6, 12, 17, 20, 21, testing slide | Query modes, network analysis, BFS, testing/validation, evaluation, visualization, references |
| All | 22 | Q&A |

## Required outputs checklist

- From-scratch structure + required algorithms 
- Stretch concept (own min-heap Dijkstra + A*) implemented and explained 
- Unit tests on small known inputs 
- Big-O analysis + empirical runtime study
- Data loading/validation + one visualization
- Jupyter notebook + slides + demo + final report
- Every team member delivers a portion of the presentation.
