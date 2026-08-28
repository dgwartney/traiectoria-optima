"""Example: fewest-hops search using BFS, contrasted with Dijkstra.

Run from the flight_planner directory:
    python -m examples.bfs_example
"""

from airport import Airport
from route import Route
from flight_planner import FlightPlanner
from pathfinding import BFS

if __name__ == "__main__":
    planner = FlightPlanner()

    jfk = Airport("JFK", city="New York")
    ord_ = Airport("ORD", city="Chicago")
    lax = Airport("LAX", city="Los Angeles")

    # A direct route is longer than the two-hop route through Chicago.
    planner.add_edge(Route(jfk, lax, distance_km=3980.0, flight_number="DIRECT1"))
    planner.add_edge(Route(jfk, ord_, distance_km=1150.0, flight_number="LEG1"))
    planner.add_edge(Route(ord_, lax, distance_km=2800.0, flight_number="LEG2"))

    dijkstra_distance, dijkstra_legs = planner.find_shortest_route("JFK", "LAX")
    hops, bfs_legs = planner.find_shortest_route("JFK", "LAX", algorithm=BFS())

    print(f"Dijkstra (weighted-shortest): {dijkstra_distance:.1f} km via "
          f"{len(dijkstra_legs)} leg(s)")
    print(f"BFS (fewest-hops): {int(hops)} leg(s) via the direct route")
    print("These diverge on purpose: BFS ignores edge.weight entirely and "
          "picks the direct 1-hop flight, even though it's the longer one.")
    for leg in bfs_legs:
        print(f"  • {leg.flight_number}: {leg.origin.iata_code} -> {leg.destination.iata_code} ({leg.distance_km:.1f} km)")
