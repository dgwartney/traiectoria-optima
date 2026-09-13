"""Pathfinding Strategy interface, and the path reconstruction all of it shares.

The interface operates purely on the generic Graph/Vertex/Edge contract
(`get_outgoing_edges`, `edge.source`/`target`/`weight`) and knows nothing about
any specific domain (e.g. Airport/Route) — it works on any `Graph[V, E]`.

Each concrete algorithm lives in its own module beside this one (`dijkstra.py`,
`bfs.py`, `astar.py`), mirroring how `geo/` keeps `DistanceFormula` in
`formula.py` and each formula in its own file.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Generic, List, Optional, Tuple, TypeVar, TYPE_CHECKING

from ..core.vertex import Vertex
from ..core.edge import Edge
from .observers import SearchObserver
from .result import COST_WEIGHT, SearchResult

if TYPE_CHECKING:
    from ..core.graph import Graph

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)


class PathfindingAlgorithm(ABC, Generic[V, E]):
    """Strategy interface: compute a path between two vertices of a Graph.

    Implementations provide `search`, which reports both the route and what
    finding it cost. `find_path` is the older two-value view, kept because the
    demos, notebooks and committed experiments are written against it.

    Attributes:
        unit: What this algorithm's `cost` counts — `COST_HOPS` or
            `COST_WEIGHT`. Declared here so `SearchResult.unit` can be filled
            in without every algorithm restating it, and so a caller holding
            only the algorithm can ask before running it.
    """

    unit: ClassVar[str] = COST_WEIGHT

    @abstractmethod
    def search(
        self,
        graph: "Graph[V, E]",
        start: V,
        goal: V,
        observer: Optional[SearchObserver] = None,
    ) -> SearchResult[E]:
        """Find a path from `start` to `goal`, reporting the cost of the search.

        Args:
            graph: Graph to search, used only through `get_outgoing_edges`.
            start: Vertex to search from.
            goal: Vertex to search for.
            observer: Optional `SearchObserver` notified as the search runs.
                Observation never changes the result.

        Returns:
            A `SearchResult` carrying the route and the search's own counters.
            An unreachable goal gives an infinite cost and an empty path, but
            keeps the real counters — the search did the work.
        """
        raise NotImplementedError

    def find_path(self, graph: "Graph[V, E]", start: V, goal: V) -> Tuple[float, List[E]]:
        """Find a path from `start` to `goal`.

        The route alone, for callers that do not care what the search cost.
        Equivalent to reading `cost` and `path` off `search`.

        Args:
            graph: Graph to search, used only through `get_outgoing_edges`.
            start: Vertex to search from.
            goal: Vertex to search for.

        Returns:
            Tuple of `(total_cost, ordered_edges_forming_the_path)`.
            `(float("inf"), [])` if `goal` is unreachable from `start`, and
            `(0.0, [])` if `start == goal`.
        """
        result = self.search(graph, start, goal)
        return result.cost, result.path


def _reconstruct_path(predecessors: Dict[V, E], goal: V) -> List[E]:
    """Walk the predecessor chain back from the goal and return it forwards.

    Args:
        predecessors: For each reached vertex, the edge it was reached by.
        goal: Vertex to walk back from.

    Returns:
        The edges from the start to `goal`, in travel order. Empty if `goal`
        was never reached.

    Raises:
        ValueError: If the predecessor chain revisits a vertex. All three
            algorithms build an acyclic chain when their preconditions hold,
            so this cannot happen on this project's data -- every edge weight
            is a haversine distance and therefore non-negative. It is checked
            because the failure mode without the check is an infinite loop
            rather than an error: a graph with a negative cycle
            (`A->B` 5, `B->C` 1, `C->B` -3, `C->D` 1) makes a naive walk spin
            forever, and a search that hangs is far harder to diagnose than
            one that raises.
    """
    path: List[E] = []
    seen = {goal}
    current = goal
    while current in predecessors:
        edge = predecessors[current]
        path.append(edge)
        current = edge.source
        if current in seen:
            raise ValueError(
                f"predecessor chain revisits {current!r}: the graph has a "
                "negative cycle, which violates the non-negative edge weight "
                "precondition of Dijkstra and A*"
            )
        seen.add(current)
    path.reverse()
    return path
