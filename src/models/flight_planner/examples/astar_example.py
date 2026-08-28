"""Example: A* guided by a great-circle-distance heuristic on Point.

Run from the flight_planner directory:
    python -m examples.astar_example
"""

from airport import Airport
from route import Route
from flight_planner import FlightPlanner
from pathfinding import AStar

if __name__ == "__main__":
    planner = FlightPlanner()

    jfk = Airport("JFK", city="New York", latitude=40.6413, longitude=-73.7781)
    ord_ = Airport("ORD", city="Chicago", latitude=41.9742, longitude=-87.9073)
    lax = Airport("LAX", city="Los Angeles", latitude=33.9416, longitude=-118.4085)

    planner.add_edge(Route(jfk, lax, distance_km=3980.0, flight_number="DIRECT1"))
    planner.add_edge(Route(jfk, ord_, distance_km=1150.0, flight_number="LEG1"))
    planner.add_edge(Route(ord_, lax, distance_km=2800.0, flight_number="LEG2"))

    # The heuristic is any Callable[[Airport, Airport], float]. Point.distance_to
    # (defaulting to the Haversine DistanceFormula) is admissible here because
    # real flight distance is always >= straight-line great-circle distance.
    astar = AStar(heuristic=lambda a, b: a.distance_to(b))

    dijkstra_distance, _ = planner.find_shortest_route("JFK", "LAX")
    astar_distance, astar_legs = planner.find_shortest_route("JFK", "LAX", algorithm=astar)

    print(f"Dijkstra optimal distance: {dijkstra_distance:.1f} km")
    print(f"A* optimal distance:       {astar_distance:.1f} km (matches: {astar_distance == dijkstra_distance})")
    for leg in astar_legs:
        print(f"  • {leg.flight_number}: {leg.origin.iata_code} -> {leg.destination.iata_code} ({leg.distance_km:.1f} km)")
