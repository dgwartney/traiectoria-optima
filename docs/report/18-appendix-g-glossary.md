# Appendix G. Glossary

Aviation and graph terms as this report uses them. Where a term has a looser
everyday meaning, the definition here is the one the numbers were measured
against.

The A–Z index this list used to carry has been dropped: it was a navigation aid
for the documentation site, and in a PDF it is 26 links to the same page.

## Aviation

**Codeshare.** One aircraft sold under more than one airline's code. 11,982 of
the surviving route rows carry the flag, which is why §2.4 reads parallel edges
as a multigraph of *marketing* rather than as 66,332 distinct aircraft
movements.

**Connecting flight.** Requires a change of planes, and a layover at the stop.
In graph terms a path of two or more edges.

**Direct flight.** Makes a stop but keeps the same flight number, and often the
same aircraft. *Not* the opposite of non-stop — a direct flight can have stops.
Eleven surviving rows have `stops > 0` (§2.4), so a handful of this dataset's
"routes" are direct rather than non-stop.

**Hub-and-spoke.** A network shape in which most traffic routes through a few
large airports. It is what produces the heavy-tailed degree distribution in
§2.5: a median out-degree of 4 against ATL's 915.

**IATA code.** The three-letter airport identifier assigned by the
International Air Transport Association (`SFO`, `BOS`, `LHR`) — the one on a
boarding pass. **This project uses it as an airport's identity**; see
[Appendix B](13-appendix-b-data-structures.md#airport-a-vertex-that-is-also-a-point).
An airport without exactly three characters of it is not usable (§2.3).

**ICAO code.** The four-letter airport identifier assigned by the International
Civil Aviation Organization (`KSFO`, `KBOS`, `EGLL`), used mainly in operations
and air-traffic control. Carried in the dataset for cross-referencing, but not
used as identity.

**Non-stop flight.** Goes from origin to destination with no intermediate stop.
One edge.

**Route.** In this dataset, **a marketed airline service rather than a distinct
flight** — the distinction §2.4 exists to make. One row of OpenFlights
`routes.dat`.

## Graphs and search

**Adjacency list.** A graph representation storing, per vertex, only the edges
that exist. The alternative is an adjacency matrix, which stores a cell per
ordered pair. At 0.32% density (§2.5) a matrix would spend over 99.6% of
itself recording the absence of a route, which is the argument in §3.

**Admissible heuristic.** One that never overestimates the true remaining cost:
`h(v) <= d(v, goal)` for every vertex. Enough to make A\* optimal *if* it can
reopen a closed vertex. This project's A\* cannot, so admissibility alone is
not enough — see *consistent*.

**Consistent (monotone) heuristic.** One that never drops faster than an edge
costs: `h(u) <= w(u, v) + h(v)` for every edge. This is the condition A\*
actually needs when it closes a vertex permanently on first expansion, which is
the subject of §4.3 and [Appendix E](16-appendix-e-astar-consistency.md).

**Frontier.** The set of discovered but not yet expanded vertices — the heap in
Dijkstra and A\*, the queue in BFS. `peak_frontier` is its largest observed
size, sampled after each push so lazy deletion's memory cost is measured rather
than hidden.

**Great-circle distance.** The shortest distance between two points along the
surface of a sphere. Every edge weight in this project is one, computed by
`flight_planner.geo.Haversine` at a 6371.0 km radius.

**Haversine formula.** A great-circle distance formula, numerically stable at
small separations. Both this project's edge weights and its A\* heuristic use
it, at the same radius — which is the pipeline invariant §4.3's admissibility
argument rests on. See [Appendix C](14-appendix-c-distance-formulas.md).

**Lazy deletion.** The strategy this project's Dijkstra uses instead of
`decrease_key`: on finding a shorter path it pushes a second entry for the same
vertex rather than updating the first, and a `settled` set discards the
superseded one when it surfaces. The project's `MinHeap` exposes only
`push`/`pop`/`peek`, so this is a consequence of the data structure rather than
a tuning choice. `nodes_pushed - nodes_expanded` is the work it throws away.

**Multigraph.** A graph permitting more than one edge between the same ordered
pair of vertices. This network is one: 29,615 of 66,332 routes run parallel to
another (§2.5), and §5 records that a simple `DiGraph` mirror silently discards
exactly those.

**Nodes expanded.** The count of vertices a search removed from its frontier
and processed. It is the cost measure §7 compares, and BFS keeps a separate
counter for it because BFS marks `visited` at *enqueue* time, so
`len(visited)` would mean something different there than in the other two
algorithms.

**Out-degree / in-degree.** The number of edges leaving / entering a vertex —
here, departures and arrivals. §2.5 reports both, and their near-symmetry at
every hub is a check on the cleaning rather than a finding.

**Snapshot.** An immutable, content-addressed copy of the cleaned dataset, plus
a manifest recording each file's SHA-256, byte count, row count, the narrowing
criteria that produced it, and the commit that wrote it. Opening one re-hashes
every file and refuses to proceed on a mismatch. Every figure in this report
names one. See [Appendix F](17-appendix-f-reproducibility.md).

**Strongly connected component.** A maximal set of vertices in which every one
is reachable from every other *following edge direction*. 3,318 airports (98.0%)
form one, which is what makes §7's arbitrary long-haul queries meaningful.

**Weakly connected component.** The same, ignoring edge direction. The network
has 8, one holding 99.2% of the airports.
