"""Example: build a planner from the processed CSV files and route across it.

Unlike the other demos, which hand-build a small graph inline, this one loads
the real network from `data/processed/{airports,routes}.csv` and reports how
many rows each loader skipped.

Run from anywhere:
    uv run python src/demos/loader_example.py
"""

from typing import Sequence

from flight_planner import FlightPlanner, Route
from flight_planner.loaders import AirportLoader, RouteLoader
from flight_planner.pathfinding import BFS


def print_legs(legs: Sequence[Route]) -> None:
    """Print each leg of an itinerary.

    Args:
        legs: Routes making up the itinerary, in order.
    """
    for leg in legs:
        print(
            f"  • {leg.airline} {leg.origin.iata_code} -> "
            f"{leg.destination.iata_code} ({leg.distance_km:.1f} km)"
        )


if __name__ == "__main__":
    airport_loader = AirportLoader()
    airport_map = airport_loader.load_by_iata()
    route_loader = RouteLoader(airport_map)
    routes = route_loader.load()

    network = FlightPlanner()
    for loaded_airport in airport_map.values():
        network.add_vertex(loaded_airport)
    for loaded_route in routes:
        network.add_edge(loaded_route)

    DEPARTURE="OMA"
    ARRIVAL="SJC"

    print("--- Loaded Flight Network ---")
    print(f"Airports file: {airport_loader.path}")
    print(f"Routes file:   {route_loader.path}")
    print(f"Total Airports: {len(network.vertices)} (skipped {len(airport_loader.skipped)})")
    print(f"Total Routes:   {len(network.edges)} (skipped {len(route_loader.skipped)})")

    print(f"\n--- Dijkstra (default): Shortest Path ({DEPARTURE} -> {ARRIVAL}) ---")
    total_km, itinerary = network.find_shortest_route(DEPARTURE, ARRIVAL)
    print(f"Optimal Distance: {total_km:.1f} km")
    print_legs(itinerary)

    print(f"\n--- BFS: Fewest-Hops Path ({DEPARTURE} -> {DEPARTURE}) ---")
    hop_count, bfs_legs = network.find_shortest_route(DEPARTURE, ARRIVAL, algorithm=BFS())
    print(
        f"Hop Count: {int(hop_count)} "
        f"(real distance: {sum(leg.distance_km for leg in bfs_legs):.1f} km)"
    )
    print_legs(bfs_legs)
