## Agenda {#agenda}

<div class="cards">

<div class="card">

<span class="pill mute">1 · The problem</span>

### One question, three right answers

Cheapest, shortest and fewest-stops are **not the same query**, and their costs
are not even in the same units.

</div>

<div class="card">

<span class="pill">2 · The data</span>

### Two sources, and what cleaning threw away

Where 66,332 routes came from, the 1,331 that were dropped and why, and how
every figure in this deck is pinned to a checksummed snapshot.

</div>

<div class="card">

<span class="pill bfs">3 · The design</span>

### A graph that has never heard of an airport

The four-layer split, the adjacency list and the density argument for it, and
the API the algorithms actually see.

</div>

<div class="card">

<span class="pill dijkstra">4 · The algorithms</span>

### BFS, a hand-rolled heap, Dijkstra, A\*

All three from scratch behind one interface — and the argument that A\* needs a
**consistent** heuristic, not merely an admissible one.

</div>

<div class="card">

<span class="pill astar">5 · The evidence</span>

### Correctness, complexity, and cost

Every answer checked against **NetworkX**, an implementation nobody here
wrote, plus 10,866 randomized queries. Every complexity bound checked against
a measurement. **130×–784× fewer expansions** for the same answer.

</div>

<div class="card">

<span class="pill warn">6 · Seeing it</span>

### The map, the demo, the lessons

Where a table stops explaining and a picture starts — then the live demo, and
what the project got wrong on the way.

</div>

</div>
