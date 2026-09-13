"""A* without a closed set, optimal for any admissible heuristic.

`flight_planner.AStar` adds a vertex to `visited` when it is popped and skips
it forever after. That is correct for a *consistent* heuristic — one where
`h(u) <= w(u, v) + h(v)` for every edge — but its docstring promises only
*admissibility*, which is weaker. Under a heuristic that is admissible but not
consistent, a cheaper route to an already-closed vertex updates
`predecessors` while the improved cost never propagates onward, and the search
returns a cost that does not describe the path it hands back.

This class is the fix, kept outside `flight_planner` so the defect and the
remedy can be measured against each other before either is adopted. Two
details are forced by the code it replaces:

- **`MinHeap.pop()` returns the item without its priority.** A stale entry
  therefore cannot be recognised the usual way, by comparing the popped `f`
  against `g + h`. (NetworkX can do it that way: it keeps
  `enqueued[v] = (cost, h)` beside its heap.) Comparing `g` against the
  g-score the vertex carried at its last expansion does the same job, and also
  permits a genuine re-expansion, which is the whole point.
- **`AStar` reports `nodes_expanded` as `len(visited)`.** Dropping the closed
  set deletes the set that counter counts, so expansions are counted
  explicitly here — as `BFS` already does, and for the same reason.

On this project's data the great-circle heuristic *is* consistent, so the two
implementations agree exactly and no committed result depends on the
difference. The relevance is to the report's admissibility argument: either
this becomes the implementation, or `astar.py` must say *consistent* where it
currently says *admissible*.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, Optional, TypeVar

from flight_planner.adt.min_heap import MinHeap
from flight_planner.core.edge import Edge
from flight_planner.core.graph import Graph
from flight_planner.core.vertex import Vertex
from flight_planner.pathfinding.observers import SearchObserver
from flight_planner.pathfinding.result import SearchResult
from flight_planner.pathfinding.strategy import PathfindingAlgorithm, _reconstruct_path

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)

_NULL_OBSERVER: SearchObserver = SearchObserver()


class ReopeningAStar(PathfindingAlgorithm[V, E]):
    """A* that re-expands a vertex when a cheaper route to it appears.

    A drop-in replacement for `AStar`: same constructor, same Strategy, same
    `SearchResult`. The only behavioral difference is on heuristics that are
    admissible without being consistent, where this returns the optimal cost
    and `AStar` may not.

    Attributes are private; the heuristic is fixed at construction so one
    instance can serve many queries, exactly as `AStar` does.
    """

    def __init__(self, heuristic: Callable[[V, V], float]) -> None:
        """Configure the search with the heuristic that guides it.

        Args:
            heuristic: Callable estimating the remaining cost from a vertex to
                the goal. Must be admissible — never overestimating the true
                remaining cost. Unlike `AStar`, it need not be consistent, and
                must be a *function*: an estimator that returns a different
                value each time it is asked about the same vertex is not a
                heuristic and breaks every guarantee here.
        """
        self._heuristic = heuristic

    def search(
        self,
        graph: Graph[V, E],
        start: V,
        goal: V,
        observer: Optional[SearchObserver] = None,
    ) -> SearchResult[E]:
        """Find the lowest-total-weight path, guided by the heuristic.

        Args:
            graph: Graph to search, used only through `get_outgoing_edges`.
            start: Vertex to search from.
            goal: Vertex to search for.
            observer: Optional `SearchObserver` notified on each push and
                expansion. A re-expansion fires `on_expand` again, so a trace
                records the search's real shape rather than a deduplicated
                one, and `len(trace.expansions)` still equals
                `result.nodes_expanded`.

        Returns:
            A `SearchResult` whose `cost` is the total weight and is optimal
            for any admissible heuristic. `nodes_expanded` counts
            re-expansions, so it can exceed the number of distinct vertices
            reached. `(inf, [])` for an unreachable goal, `(0.0, [])` and zero
            counters when `start == goal`.
        """
        if start == goal:
            return SearchResult(0.0, [])

        watcher = observer if observer is not None else _NULL_OBSERVER

        open_set: MinHeap[V] = MinHeap()
        start_f = self._heuristic(start, goal)
        open_set.push(start, start_f)
        watcher.on_push(start, start_f)
        pushed = 1
        peak = 1
        expanded = 0

        g_score: Dict[V, float] = {start: 0.0}
        predecessors: Dict[V, E] = {}
        # The g-score each vertex carried the last time it was expanded. This
        # replaces `AStar`'s closed set, and the comparison below is the whole
        # difference between the two implementations.
        expanded_at: Dict[V, float] = {}

        while open_set:
            current = open_set.pop()

            if current == goal:
                break
            # A pop whose g is no better than the one this vertex carried when
            # it was last expanded is a superseded queue entry -- the lazy
            # deletion `Dijkstra` also relies on. A pop whose g *is* better is
            # a route found after the vertex was closed, which is precisely
            # the case `AStar`'s `visited` set discards.
            if g_score[current] >= expanded_at.get(current, math.inf):
                continue
            expanded_at[current] = g_score[current]
            expanded += 1
            watcher.on_expand(current, g_score[current])

            for edge in graph.get_outgoing_edges(current):
                neighbor = edge.target
                tentative_g = g_score[current] + edge.weight

                if tentative_g < g_score.get(neighbor, math.inf):
                    g_score[neighbor] = tentative_g
                    predecessors[neighbor] = edge
                    f_score = tentative_g + self._heuristic(neighbor, goal)
                    open_set.push(neighbor, f_score)
                    watcher.on_push(neighbor, f_score)
                    pushed += 1
                    peak = max(peak, len(open_set))

        counters = {
            "nodes_expanded": expanded,
            "nodes_pushed": pushed,
            "peak_frontier": peak,
        }
        if goal not in predecessors:
            return SearchResult(math.inf, [], **counters)

        return SearchResult(
            g_score[goal], _reconstruct_path(predecessors, goal), **counters
        )
