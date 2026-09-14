# 11. References

## 11.1 Texts and papers

Goodrich, M. T., Tamassia, R., & Goldwasser, M. H. (2013). *Data Structures and
Algorithms in Python*. Wiley.
: The course textbook. Chapter 9 is the heap this project's `MinHeap`
  implements as an array-backed complete binary tree (§4.2); chapter 14 is the
  graph and traversal material behind §3 and §4. Its worked flight-network
  example is the seven-airport graph §5.1 tests against.

Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022).
*Introduction to Algorithms* (4th ed.). MIT Press.
: Consulted for the complexity derivations in §6, in particular the
  distinction between the `decrease_key` formulation of Dijkstra and the
  lazy-deletion variant this project uses because its heap exposes only
  `push`/`pop`/`peek` (§4.2, §6.3).

Dijkstra, E. W. (1959). A note on two problems in connexion with graphs.
*Numerische Mathematik*, 1, 269–271.
: The original algorithm.

Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the
heuristic determination of minimum cost paths. *IEEE Transactions on Systems
Science and Cybernetics*, 4(2), 100–107.
: A\*, and the admissibility condition §4.3 examines.

Hart, P. E., Nilsson, N. J., & Raphael, B. (1972). Correction to "A formal
basis for the heuristic determination of minimum cost paths". *SIGART
Bulletin*, 37.
: **Directly relevant to this project's central argument.** The correction
  addresses monotonicity — what §4.3 calls consistency — which is the
  condition an A\* that never reopens a closed vertex actually requires. Our
  implementation is that A\*, and its docstring cited the 1968 condition.

Pearl, J. (1984). *Heuristics: Intelligent Search Strategies for Computer
Problem Solving*. Addison-Wesley.
: The treatment of consistent (monotone) heuristics used in §4.3 and
  [Appendix E](16-appendix-e-astar-consistency.md).

Sinnott, R. W. (1984). Virtues of the haversine. *Sky & Telescope*, 68(2), 159.
: The haversine formulation used for every edge weight and for the A\*
  heuristic ([Appendix C](14-appendix-c-distance-formulas.md)).

Vincenty, T. (1975). Direct and inverse solutions of geodesics on the ellipsoid
with application of nested equations. *Survey Review*, 23(176), 88–93.
: The ellipsoidal comparison formula. §9.4's corollary — that the *more
  accurate* formula makes a *less correct* heuristic — is measured against
  this one.

Karney, C. F. F. (2013). Algorithms for geodesics. *Journal of Geodesy*, 87(1),
43–55.
: Resolves Vincenty's convergence failures for near-antipodal points.
  Discussed in Appendix C as the method `pyproj` implements; not used as an
  edge weight or heuristic.

## 11.2 Data sources

| Source | File used | What it supplies |
|---|---|---|
| [OpenFlights](https://openflights.org/data.html) | `routes.dat` (67,663 rows) | Every edge: airline, origin, destination, codeshare flag, stops, equipment |
| [OurAirports](https://ourairports.com/data/) | `airports.csv` (85,884 rows) | Airport identity, coordinates and the descriptive columns |
| Wikipedia, *List of international airports by country* | scraped to `airports_raw.json` | The `is_international` flag on 1,329 airports |
| IATA airport code registry | consulted by hand | Adjudicating the ten codes where Wikipedia and OurAirports disagree (§9.1) |

Both bulk sources are vendored under `data/raw/` and recorded with a SHA-256 in
every experiment that reads them. §2.1 explains why the airports come from
OurAirports rather than OpenFlights' own `airports.dat`: the edges and the
vertices come from different projects on purpose, because the route table is
the only open source of the edges and the OurAirports table is the better
source of the vertices.

Coordinates were once resolved through AirportsAPI.com. That dependency was
removed once it became clear the service was serving OurAirports data back over
the network and was wrong on the three rows where it differed (§9.1).

## 11.3 Libraries, and what each one is allowed to do

The assignment permits libraries "only for loading, plotting, and **validating**
your own results". The table states, per library, which of those three it does
and where it is enforced.

**The published wheel depends on `pandas` and nothing else.** Everything below
`pandas` is a `dev`- or `notebooks`-group dependency, not part of the package's
runtime contract.

| Library | Version | Role | Why this is not the deliverable |
|---|---|---|---|
| `pandas` | 3.0.5 | **Loading.** The only third-party import in `flight_planner` | Reads CSV and runs the cleaning transform (§2.3). No graph, no search, no distance |
| `networkx` | 3.6.1 | **Validating, only.** | The independent oracle in §5.4. Wrapped behind our own `PathfindingAlgorithm` interface so it is a *parameter* of an experiment, never a substitute for the algorithms. It reports its expansion counters as literal zero, because it cannot measure them and a fabricated number in a comparison column would be worse than an obviously absent one (§5.4) |
| `matplotlib` | 3.11.1 | **Plotting.** | §2.5's and §7's charts |
| `numpy` | 2.5.2 | Plotting support | Array handling underneath matplotlib, and the trilinear interpolation in §10.4's wind model — which is why removing `scipy` cost nothing |
| `folium` | 0.20.0 | **Plotting.** | The route maps in §8. Imported lazily, inside the method that needs it |
| `pyproj` | 3.7.2 | **Plotting.** | Great-circle interpolation for drawing only (§8.2). **Not** used for any distance this report reports — those come from our own `geo.Haversine` |
| `playwright` | — | **Plotting.** | Screenshots a Leaflet map to PNG so a static PDF can cite it (§8.6), and exports the deck |
| `pytest`, `ruff` | 9.1.1, 0.16.4 | Tooling | The 1,118-test suite (1,041 without the `notebooks` extras) and the lint gate |

The two claims worth verifying rather than accepting:

```sh
grep -rn "import heapq"   src/flight_planner/     # prints nothing
grep -rn "import networkx" src/flight_planner/    # prints nothing
```

The heap, the graph, the three searches and both distance formulas are built on
Python's built-in types. [Appendix A](12-appendix-a-code-inventory.md) accounts
for every line.

## 11.4 Tools used to produce this report

| Tool | Version | Use |
|---|---|---|
| Python | 3.12.12 | Everything |
| [pandoc](https://pandoc.org) | 3.11 | Markdown → PDF via XeLaTeX, and markdown → reveal.js |
| [reveal.js](https://revealjs.com) | 5.1.0 | The presentation, **built from these chapters** rather than maintained beside them (Appendix F) |
| Mermaid CLI, `rsvg-convert` | — | Diagrams, rasterized for the PDF |
| `uv` | — | Dependency resolution and the locked environment |

The deck is generated from the same chapter files as this report by a pandoc
Lua filter, so the two cannot disagree about a number. That is a direct
response to the previous deck, which was maintained by hand and had drifted
from the code in nine documented places.

<div class="deck-slide" id="references">

### References

<div class="cards">

<div class="card">

<span class="pill">Texts and papers</span>

Goodrich, Tamassia & Goldwasser, *Data Structures and Algorithms in Python*
(Wiley, 2013) — ch. 9 heap, ch. 14 graphs.

Hart, Nilsson & Raphael (1968), *A Formal Basis…* — and the **1972
correction**, which is the monotonicity condition our A\* actually needs.

Dijkstra (1959) · Pearl (1984) · CLRS 4th ed.

Sinnott (1984) haversine · Vincenty (1975) · Karney (2013).

</div>

<div class="card">

<span class="pill dijkstra">Data</span>

**OpenFlights** `routes.dat` — 67,663 route rows.

**OurAirports** `airports.csv` — 85,884 airport rows.

Wikipedia international-airport list; IATA registry for the ten disputed
codes.

Both bulk sources vendored and **SHA-256'd in every result file**.

</div>

<div class="card">

<span class="pill astar">Libraries — loading, plotting, validating</span>

`pandas` is the **only** dependency of the published wheel.

`networkx` **validates only**, wrapped behind our own interface.
`matplotlib`, `folium`, `pyproj`, `playwright` draw.

```sh
grep -rn "import heapq" src/flight_planner/
# prints nothing
```

</div>

</div>

<p class="footnote">Appendix A accounts for every line of code; Appendix F for how every figure is pinned to a checksummed snapshot.</p>

</div>
