"""What a search found, and what finding it cost.

`find_path` answers only "which route?". The project's central claim is about
the *other* half — that A* reaches the same answer while expanding far fewer
nodes than Dijkstra — and that half was previously discarded the moment a
search returned. `SearchResult` keeps it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, List, TypeVar

from ..core.edge import Edge

E = TypeVar("E", bound=Edge)

#: `cost` counts edges. BFS reports this; the number is a hop count.
COST_HOPS = "hops"

#: `cost` sums `edge.weight`. Dijkstra and A* report this. The *physical* unit
#: is the graph's to define -- kilometres for this project's flight networks --
#: which is why the marker says "weight" rather than "km": `pathfinding` is
#: generic over any `Graph[V, E]` and cannot know what a weight measures.
COST_WEIGHT = "weight"


@dataclass(frozen=True)
class SearchResult(Generic[E]):
    """The outcome of one search, with the work it took to get there.

    Attributes:
        cost: Total cost of the path. **The unit depends on the algorithm** —
            `Dijkstra` and `AStar` return the summed `edge.weight` (kilometres,
            for this project's graphs), while `BFS` returns a hop count.
            `float("inf")` if the goal was unreachable, `0.0` if start == goal.
        path: Edges forming the route, in order; empty if there is no route.
        nodes_expanded: Vertices whose outgoing edges were requested. The goal
            is never counted: every algorithm here breaks on reaching it,
            before expanding it.
        nodes_pushed: Vertices placed on the frontier, counting repeats. Both
            weighted algorithms re-queue a vertex rather than repositioning its
            existing entry, so `nodes_pushed - nodes_expanded` is the work the
            lazy-deletion design throws away.
        peak_frontier: Largest the frontier ever got — the measured space cost,
            against the O(V) bound the complexity write-up claims.
        unit: What `cost` counts — `COST_HOPS` or `COST_WEIGHT`. Set by the
            algorithm that produced the result, so a caller holding only a
            `SearchResult` can still label or guard the number. Empty string
            for a hand-constructed result that did not say.
    """

    cost: float
    path: List[E] = field(default_factory=list)
    nodes_expanded: int = 0
    nodes_pushed: int = 0
    peak_frontier: int = 0
    unit: str = ""

    @property
    def found(self) -> bool:
        """Report whether a route was found.

        Returns:
            `True` unless the goal was unreachable. Note that a search from a
            vertex to itself counts as found, with an empty path.
        """
        return self.cost != float("inf")
