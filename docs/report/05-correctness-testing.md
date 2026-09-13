# 5. Correctness Testing
- Unit test strategy (empty, single-node, disconnected, cyclic/duplicate cases)
- Known-route validation
- Library cross-validation results (NetworkX)
  — drop in [results-networkx-parity.md](15-appendix-d-networkx-parity.md);
  200 long-haul queries over the world network, three algorithms, 0 cost
  mismatches, recorded in `experiments/networkx-parity/results.json`
- Randomized differential testing
  — [results-astar-consistency.md](16-appendix-e-astar-consistency.md);
  10,866 queries on random graphs, which found a real defect in A*
