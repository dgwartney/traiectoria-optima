"""Flight network graph module.

Provides FlightPlanner, a specialized flight network graph built on the
Graph/Vertex/Edge abstractions that finds routes between airports using a
pluggable PathfindingAlgorithm strategy (Dijkstra by default).
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union

from ..core.graph import Graph
from .airport import Airport
from .route import Route
from ..pathfinding import (
    Dijkstra,
    PathfindingAlgorithm,
    SearchObserver,
    SearchResult,
)


class FlightPlanner(Graph[Airport, Route]):
    """Specialized flight network graph providing pathfinding between airports."""

    def __init__(self) -> None:
        """Create an empty flight network with no airports or routes."""
        super().__init__()
        self._iata_lookup: Dict[str, Airport] = {}

    @property
    def iata_lookup(self) -> Dict[str, Airport]:
        """Provides a read-only dictionary mapping IATA codes to Airport instances."""
        return dict(self._iata_lookup)

    def add_vertex(self, vertex: Airport) -> None:
        """Add an airport to the network and index it by IATA code.

        Args:
            vertex: Airport to add. A later airport reusing an existing code
                replaces that code's entry in the lookup.
        """
        super().add_vertex(vertex)
        self._iata_lookup[vertex.iata_code] = vertex

    def find_airport(self, iata_code: str) -> Optional[Airport]:
        """Look up an Airport instance by its IATA code."""
        return self._iata_lookup.get(iata_code.strip().upper())

    def _resolve_airport(self, airport_or_code: Union[Airport, str]) -> Airport:
        """Helper to resolve an Airport instance from an object or IATA string."""
        if isinstance(airport_or_code, Airport):
            if airport_or_code not in self._adjacency:
                raise ValueError(f"Airport '{airport_or_code.iata_code}' is not in the graph.")
            return airport_or_code
        elif isinstance(airport_or_code, str):
            airport = self.find_airport(airport_or_code)
            if not airport:
                raise ValueError(f"Airport with IATA code '{airport_or_code}' not found in the graph.")
            return airport
        raise TypeError("Expected Airport instance or IATA code string.")

    def find_shortest_route(
        self,
        origin: Union[Airport, str],
        destination: Union[Airport, str],
        algorithm: Optional[PathfindingAlgorithm[Airport, Route]] = None,
    ) -> Tuple[float, List[Route]]:
        """Compute a route between two airports.

        Uses the given pathfinding Strategy, defaulting to Dijkstra's algorithm
        for weighted-shortest-distance behavior.

        Args:
            origin: Starting Airport instance or 3-letter IATA code.
            destination: Target Airport instance or 3-letter IATA code.
            algorithm: PathfindingAlgorithm strategy (Dijkstra/BFS/AStar/custom).
                Defaults to Dijkstra() if omitted.

        Returns:
            Tuple[float, List[Route]]: (total_cost, list_of_routes)
            Returns (float('inf'), []) if no route is found.
            Returns (0.0, []) if origin == destination.
        """
        result = self.search_route(origin, destination, algorithm)
        return result.cost, result.path

    def search_route(
        self,
        origin: Union[Airport, str],
        destination: Union[Airport, str],
        algorithm: Optional[PathfindingAlgorithm[Airport, Route]] = None,
        observer: Optional[SearchObserver] = None,
    ) -> SearchResult[Route]:
        """Compute a route, keeping what the search itself cost.

        The same query as `find_shortest_route`, reporting the search's own
        counters — nodes expanded, nodes queued, peak frontier — alongside the
        itinerary.

        Args:
            origin: Starting Airport instance or 3-letter IATA code.
            destination: Target Airport instance or 3-letter IATA code.
            algorithm: PathfindingAlgorithm strategy (Dijkstra/BFS/AStar/custom).
                Defaults to Dijkstra() if omitted.
            observer: Optional `SearchObserver` notified as the search runs.

        Returns:
            A `SearchResult` over `Route` legs. An origin equal to the
            destination reports zero cost and zero counters, since no search
            runs; an unreachable destination reports an infinite cost but the
            real counters.
        """
        start_airport = self._resolve_airport(origin)
        end_airport = self._resolve_airport(destination)

        if start_airport == end_airport:
            return SearchResult(0.0, [])

        chosen_algorithm = algorithm if algorithm is not None else Dijkstra()
        return self.search(start_airport, end_airport, chosen_algorithm, observer)
