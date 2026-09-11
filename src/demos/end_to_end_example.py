"""Example: one network, every algorithm and both distance formulas.

The largest of the demos. Builds a six-airport international network and runs
Dijkstra, BFS and A* over it, then swaps A*'s heuristic from Haversine to
Vincenty to show that changing the DistanceFormula changes only the
heuristic's precision, not any interface.

Run from anywhere:
    uv run python src/demos/end_to_end_example.py
"""

from flight_planner import Airport, FlightPlanner, Route
from flight_planner.geo import Vincenty
from flight_planner.pathfinding import AStar, BFS

if __name__ == "__main__":
    planner = FlightPlanner()

    # Define Airports (with real approximate coordinates, for the A* heuristic)
    jfk = Airport("JFK", name="John F. Kennedy Intl", city="New York", country="USA",
                  latitude=40.6413, longitude=-73.7781)
    lhr = Airport("LHR", name="Heathrow", city="London", country="UK",
                  latitude=51.4700, longitude=-0.4543)
    cdg = Airport("CDG", name="Charles de Gaulle", city="Paris", country="France",
                  latitude=49.0097, longitude=2.5479)
    dxb = Airport("DXB", name="Dubai Intl", city="Dubai", country="UAE",
                  latitude=25.2532, longitude=55.3657)
    hnd = Airport("HND", name="Haneda", city="Tokyo", country="Japan",
                  latitude=35.5494, longitude=139.7798)
    sin = Airport("SIN", name="Changi", city="Singapore", country="Singapore",
                  latitude=1.3644, longitude=103.9915)

    # Define Direct Routes
    planner.add_edge(Route(jfk, lhr, distance_km=5540.0, airline="British Airways", flight_number="BA178"))
    planner.add_edge(Route(lhr, dxb, distance_km=5470.0, airline="Emirates", flight_number="EK002"))
    planner.add_edge(Route(dxb, hnd, distance_km=7935.0, airline="Emirates", flight_number="EK318"))
    planner.add_edge(Route(jfk, cdg, distance_km=5835.0, airline="Air France", flight_number="AF007"))
    planner.add_edge(Route(cdg, sin, distance_km=10730.0, airline="Singapore Airlines", flight_number="SQ335"))
    planner.add_edge(Route(sin, hnd, distance_km=5300.0, airline="Singapore Airlines", flight_number="SQ638"))
    planner.add_edge(Route(jfk, hnd, distance_km=10860.0, airline="Japan Airlines", flight_number="JL003"))

    print("--- Flight Network Summary ---")
    print(f"Total Airports: {len(planner.vertices)}")
    print(f"Total Flight Routes: {len(planner.edges)}")

    def print_legs(legs):
        """Print each leg of an itinerary.

        Args:
            legs: Routes making up the itinerary, in order.
        """
        for leg in legs:
            print(f"  • {leg.flight_number} ({leg.airline}): {leg.origin.iata_code} -> {leg.destination.iata_code} ({leg.distance_km:.1f} km)")

    print("\n--- Dijkstra (default): Shortest Path (JFK -> HND) ---")
    dist, itinerary = planner.find_shortest_route("JFK", "HND")
    print(f"Optimal Distance: {dist:.1f} km")
    print("Flight Legs:")
    print_legs(itinerary)

    print("\n--- Dijkstra (default): Multi-Stop Path (LHR -> HND) ---")
    dist_lhr_hnd, legs_lhr_hnd = planner.find_shortest_route("LHR", "HND")
    print(f"Optimal Distance: {dist_lhr_hnd:.1f} km")
    print_legs(legs_lhr_hnd)

    print("\n--- BFS: Fewest-Hops Path (JFK -> HND) ---")
    hops, bfs_legs = planner.find_shortest_route("JFK", "HND", algorithm=BFS())
    bfs_distance = sum(leg.distance_km for leg in bfs_legs)
    print(f"Hop Count: {int(hops)} (real distance: {bfs_distance:.1f} km)")
    print("NOTE: BFS optimizes for fewest flight legs, not total distance — "
          "this may differ from Dijkstra's result above.")
    print_legs(bfs_legs)

    print("\n--- A* (Haversine heuristic, default): Shortest Path (JFK -> HND) ---")
    astar_haversine = AStar(heuristic=lambda a, b: a.distance_to(b))
    dist_astar, astar_legs = planner.find_shortest_route("JFK", "HND", algorithm=astar_haversine)
    print(f"Optimal Distance: {dist_astar:.1f} km (matches Dijkstra: {dist_astar == dist})")
    print_legs(astar_legs)

    print("\n--- A* (Vincenty heuristic): Shortest Path (JFK -> HND) ---")
    astar_vincenty = AStar(heuristic=lambda a, b: a.distance_to(b, Vincenty()))
    dist_astar_v, astar_legs_v = planner.find_shortest_route("JFK", "HND", algorithm=astar_vincenty)
    print(f"Optimal Distance: {dist_astar_v:.1f} km (matches Dijkstra: {dist_astar_v == dist})")
    print("NOTE: swapping the DistanceFormula (Haversine -> Vincenty) changes "
          "only the heuristic's precision, not AStar's or Point's interface.")
