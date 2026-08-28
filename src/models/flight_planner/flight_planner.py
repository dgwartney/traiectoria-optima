"""
Flight Network Graph & Dijkstra Pathfinding Module.

Provides FlightPlanner, a specialized flight network graph built on the
Graph/Vertex/Edge abstractions that uses Dijkstra's algorithm to compute
shortest paths between airports.
"""

from __future__ import annotations
import heapq
from typing import Dict, List, Optional, Tuple, Union

from graph import Graph
from airport import Airport
from route import Route


class FlightPlanner(Graph[Airport, Route]):
    """Specialized flight network graph providing Dijkstra-based pathfinding."""

    def __init__(self) -> None:
        super().__init__()
        self._iata_lookup: Dict[str, Airport] = {}

    @property
    def iata_lookup(self) -> Dict[str, Airport]:
        """Provides a read-only dictionary mapping IATA codes to Airport instances."""
        return dict(self._iata_lookup)

    def add_vertex(self, vertex: Airport) -> None:
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
    ) -> Tuple[float, List[Route]]:
        """
        Uses Dijkstra's algorithm to compute the shortest path between two airports.

        Args:
            origin: Starting Airport instance or 3-letter IATA code.
            destination: Target Airport instance or 3-letter IATA code.

        Returns:
            Tuple[float, List[Route]]: (total_distance_km, list_of_routes)
            Returns (float('inf'), []) if no route is found.
        """
        start_airport = self._resolve_airport(origin)
        end_airport = self._resolve_airport(destination)

        if start_airport == end_airport:
            return 0.0, []

        # Priority queue entries: (cumulative_distance, tie_breaker_counter, current_airport)
        counter = 0
        pq: List[Tuple[float, int, Airport]] = [(0.0, counter, start_airport)]

        distances: Dict[Airport, float] = {start_airport: 0.0}
        predecessors: Dict[Airport, Route] = {}

        while pq:
            current_dist, _, current_airport = heapq.heappop(pq)

            if current_airport == end_airport:
                break

            if current_dist > distances.get(current_airport, float("inf")):
                continue

            for route in self.get_outgoing_edges(current_airport):
                neighbor = route.destination
                distance_to_neighbor = current_dist + route.distance_km

                if distance_to_neighbor < distances.get(neighbor, float("inf")):
                    distances[neighbor] = distance_to_neighbor
                    predecessors[neighbor] = route
                    counter += 1
                    heapq.heappush(pq, (distance_to_neighbor, counter, neighbor))

        # Destination unreachable
        if end_airport not in predecessors and start_airport != end_airport:
            return float("inf"), []

        # Backtrack path reconstruction
        path: List[Route] = []
        curr = end_airport
        while curr in predecessors:
            incoming_route = predecessors[curr]
            path.append(incoming_route)
            curr = incoming_route.origin

        path.reverse()
        return distances[end_airport], path
