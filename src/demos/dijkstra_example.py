"""Example: default weighted-shortest-path search using Dijkstra.

Run from anywhere:
    uv run python src/demos/dijkstra_example.py
"""


from flight_planner import Airport, FlightPlanner, Route
from flight_planner.pathfinding import Dijkstra

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
