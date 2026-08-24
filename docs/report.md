---
title: "A1: Flight Route Planner"
subtitle: "Final Report"
author: "Aastha Sharma-Flores, Jake Lu, David Gwartney"
date: 2026-08-23
---

# A1: Flight Route Planner — Final Report

## 1. Introduction
- Problem statement: finding cheapest / shortest / fewest-stop routes between airports
- Motivation and goals
- Summary of approach (BFS, Dijkstra, A*)

## 2. Dataset
- Data sources (OpenFlights airports/routes, OurAirports)
- Scope (U.S. large/medium airports and connecting routes)
- Cleaning and preparation steps
- Basic dataset statistics (airport count, route count, degree distribution, disconnected airports)

## 3. Graph Construction
- Adjacency-list representation
- Haversine edge-weight computation
- Handling of missing/invalid data (nulls, duplicates, self-loops)

## 4. Algorithms

### 4.1 BFS (Fewest Stops)
- Description and implementation notes

### 4.2 Dijkstra's Algorithm
- From-scratch binary min-heap implementation
- Dijkstra implementation using the custom heap
- Validation against NetworkX

### 4.3 A* Search (Stretch Concept)
- Haversine admissible heuristic
- A* implementation using the custom heap
- Admissibility argument/proof

### 4.4 Secondary Features
- Fewest-stops vs. cheapest-distance mode switch
- Nearest-airports-to-a-point lookup

## 5. Correctness Testing
- Unit test strategy (empty, single-node, disconnected, cyclic/duplicate cases)
- Known-route validation
- Library cross-validation results (NetworkX)

## 6. Complexity Analysis
- Big-O analysis of graph construction
- Big-O analysis of BFS
- Big-O analysis of Dijkstra (with custom heap)
- Big-O analysis of A*

## 7. Empirical Evaluation
- Benchmark methodology (query set, hardware/environment)
- Runtime comparison: BFS vs. Dijkstra vs. A*
- Nodes-expanded comparison: informed vs. uninformed search
- Runtime plot(s): time vs. input/graph size
- Discussion of results (does A* expand fewer nodes while returning the same answer?)

## 8. Visualization
- Rendered route map (Folium/ipyleaflet)
- Other supporting visualizations (graph stats, degree distribution)

## 9. Challenges and Lessons Learned
- Data quality issues encountered
- Algorithmic/implementation challenges
- What we would do differently

## 10. Conclusion
- Summary of findings
- Future work / extensions

## 11. References
- Course textbook and papers (Goodrich et al.; Hart, Nilsson & Raphael; CLRS)
- Dataset sources
- Libraries used (and how, per the "validation/plotting only" rule)

## Appendix
- Team contributions
- Repository/notebook links
