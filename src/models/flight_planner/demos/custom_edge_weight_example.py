"""Example: a custom Edge subclass with different weight semantics.

DistanceFormula (see custom_distance_formula_example.py) governs the A*
heuristic's straight-line ESTIMATE between Points. It has nothing to do with
Edge.weight, which is the REAL cost an algorithm accumulates along a path.
Here, weight represents flight duration in hours instead of distance —
Dijkstra/BFS/AStar work with it unchanged, since they only ever read
edge.weight generically.

Run from the flight_planner directory:
    python -m demos.custom_edge_weight_example
"""

from edge import Edge
from airport import Airport
from graph import Graph
from pathfinding import Dijkstra


class TimedRoute(Edge[Airport]):
    """A flight route weighted by duration (hours) instead of distance."""

    def __init__(self, origin: Airport, destination: Airport, duration_hours: float, flight_number: str = "") -> None:
        super().__init__(source=origin, target=destination, weight=duration_hours)
        self._flight_number = flight_number

    @property
    def duration_hours(self) -> float:
        return self.weight

    @property
    def flight_number(self) -> str:
        return self._flight_number


if __name__ == "__main__":
    graph: Graph[Airport, TimedRoute] = Graph()

    jfk = Airport("JFK", city="New York")
    ord_ = Airport("ORD", city="Chicago")
    lax = Airport("LAX", city="Los Angeles")

    # The direct flight is longer in distance but here we're optimizing time,
    # and a fast direct flight beats two shorter-distance connecting legs.
    graph.add_edge(TimedRoute(jfk, lax, duration_hours=5.5, flight_number="DIRECT1"))
    graph.add_edge(TimedRoute(jfk, ord_, duration_hours=2.5, flight_number="LEG1"))
    graph.add_edge(TimedRoute(ord_, lax, duration_hours=4.0, flight_number="LEG2"))

    total_hours, legs = graph.shortest_path(jfk, lax, Dijkstra())

    print(f"Fastest total duration JFK -> LAX: {total_hours:.1f} hours")
    for leg in legs:
        print(f"  • {leg.flight_number}: {leg.source.iata_code} -> {leg.target.iata_code} ({leg.duration_hours:.1f} h)")
