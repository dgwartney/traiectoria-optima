"""Example: A* guided by a great-circle-distance heuristic on Point.

Run from anywhere:
    uv run python src/demos/astar_example.py
"""


from flight_planner import Airport, FlightPlanner, Route
from flight_planner.geo import haversine_heuristic
from flight_planner.pathfinding import AStar

if __name__ == "__main__":
    planner = FlightPlanner()

    jfk = Airport("JFK", city="New York", latitude=40.6413, longitude=-73.7781)
    ord_ = Airport("ORD", city="Chicago", latitude=41.9742, longitude=-87.9073)
    lax = Airport("LAX", city="Los Angeles", latitude=33.9416, longitude=-118.4085)

    planner.add_edge(Route(jfk, lax, distance_km=3980.0, flight_number="DIRECT1"))
    planner.add_edge(Route(jfk, ord_, distance_km=1150.0, flight_number="LEG1"))
    planner.add_edge(Route(ord_, lax, distance_km=2800.0, flight_number="LEG2"))

    # The heuristic is any Callable[[Airport, Airport], float]. Haversine
    # (wrapped in Memoized to avoid recomputing it for nodes A* relaxes more
    # than once) is admissible here because real flight distance is always
    # >= straight-line great-circle distance.
    astar = AStar(haversine_heuristic())

    dijkstra_distance, _ = planner.find_shortest_route("JFK", "LAX")
    astar_distance, astar_legs = planner.find_shortest_route("JFK", "LAX", algorithm=astar)

    print(f"Dijkstra optimal distance: {dijkstra_distance:.1f} km")
    print(f"A* optimal distance:       {astar_distance:.1f} km (matches: {astar_distance == dijkstra_distance})")
    for leg in astar_legs:
        print(f"  • {leg.flight_number}: {leg.origin.iata_code} -> {leg.destination.iata_code} ({leg.distance_km:.1f} km)")
