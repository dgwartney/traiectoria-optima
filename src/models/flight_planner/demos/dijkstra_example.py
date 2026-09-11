"""Example: default weighted-shortest-path search using Dijkstra.

Run from the repository root:
    uv run python src/models/flight_planner/demos/dijkstra_example.py

Or as a module, from src/models/flight_planner/:
    python -m demos.dijkstra_example
"""

# Runnable from anywhere: the sibling modules (airport, route, ...) live one
# directory up and are imported by bare name, so that directory has to be on
# sys.path. Python only adds this script's own directory automatically.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from airport import Airport
from route import Route
from flight_planner import FlightPlanner
from pathfinding import Dijkstra

if __name__ == "__main__":
    planner = FlightPlanner()

    jfk = Airport("JFK", city="New York")
    ord_ = Airport("ORD", city="Chicago")
    lax = Airport("LAX", city="Los Angeles")

    # A direct route is longer than the two-hop route through Chicago.
    planner.add_edge(Route(jfk, lax, distance_km=3980.0, flight_number="DIRECT1"))
    planner.add_edge(Route(jfk, ord_, distance_km=1150.0, flight_number="LEG1"))
    planner.add_edge(Route(ord_, lax, distance_km=2800.0, flight_number="LEG2"))

    # Passing algorithm=Dijkstra() explicitly is equivalent to omitting it —
    # Dijkstra is FlightPlanner's default PathfindingAlgorithm.
    distance, legs = planner.find_shortest_route("JFK", "LAX", algorithm=Dijkstra())

    print(f"Cheapest total distance JFK -> LAX: {distance:.1f} km")
    for leg in legs:
        print(f"  • {leg.flight_number}: {leg.origin.iata_code} -> {leg.destination.iata_code} ({leg.distance_km:.1f} km)")
