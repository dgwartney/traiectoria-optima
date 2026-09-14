"""Example: a textbook flight network, run through all three algorithms.

The seven-airport graph is transcribed by hand from the flight-network example
in Goodrich, Tamassia and Goldwasser, *Data Structures and Algorithms in
Python* (Wiley), distances and all, so the paths this prints can be checked
against the worked example in the book.

The network is built by `build_network()` rather than inline, so that
`tests/demos/test_book_example.py` can assert the answers instead of leaving
them to be read off a console. Report §5.1 is the claim those assertions back.

Run from anywhere:
    uv run python src/demos/book_example.py
"""


from flight_planner import Airport, FlightPlanner, Route
from flight_planner.pathfinding import Dijkstra
from flight_planner.geo import haversine_heuristic
from flight_planner.pathfinding import AStar, BFS

#: The query the book works through: Boston to Los Angeles.
DEPARTURE = "BOS"
ARRIVAL = "LAX"


def build_network() -> FlightPlanner:
    """Build the seven-airport network from the textbook.

    Returns:
        A `FlightPlanner` holding the book's seven airports and eleven
        flights. No coordinates are given, because the book's figure has
        none -- see `test_book_example.py` for what that does to A-star.
    """
    planner = FlightPlanner()

    BOS = Airport("BOS", city="Boston")
    DFW = Airport("DFW", city="Dallas/Fort Worth")
    JFK = Airport("JFK", city="New York")
    LAX = Airport("LAX", city="Los Angeles")
    MIA = Airport("MIA", city="Miami")
    ORD = Airport("ORD", city="Chicago")
    SFO = Airport("SFO", city="SanFrancisco")

    planner.add_edge(Route(BOS, JFK, distance_km=301.0, flight_number="NW45"))
    planner.add_edge(Route(BOS, MIA, distance_km=2028.0, flight_number="DL247"))

    planner.add_edge(Route(DFW, ORD, distance_km=1291.0, flight_number="DL335"))
    planner.add_edge(Route(DFW, LAX, distance_km=1987.0, flight_number="DL335"))

    planner.add_edge(Route(JFK, DFW, distance_km=2238.0, flight_number="AA1387"))
    planner.add_edge(Route(JFK, MIA, distance_km=1760.0, flight_number="AA390"))
    planner.add_edge(Route(JFK, SFO, distance_km=4153.0, flight_number="SW45"))

    planner.add_edge(Route(LAX, ORD, distance_km=2803.0, flight_number="UA120"))

    planner.add_edge(Route(MIA, DFW, distance_km=1805.0, flight_number="AA523"))
    planner.add_edge(Route(MIA, LAX, distance_km=3763.0, flight_number="AA523"))

    planner.add_edge(Route(ORD, DFW, distance_km=1291.0, flight_number="UA877"))

    return planner


def _print_legs(legs) -> None:
    for leg in legs:
        print(
            f"  • {leg.flight_number}: {leg.origin.iata_code} -> "
            f"{leg.destination.iata_code} ({leg.distance_km:.1f} km)"
        )


if __name__ == "__main__":
    planner = build_network()

    dijkstra_distance, legs = planner.find_shortest_route(
        DEPARTURE, ARRIVAL, algorithm=Dijkstra()
    )
    print(f"Dijkstra (weighted-shortest): {dijkstra_distance:.1f} km")
    _print_legs(legs)
    print("")

    hops, bfs_legs = planner.find_shortest_route(DEPARTURE, ARRIVAL, algorithm=BFS())
    bfs_distance = sum(leg.distance_km for leg in bfs_legs)
    print(
        f"BFS (fewest-hops): {int(hops)} leg(s), "
        f"{bfs_distance:.1f} km -- {bfs_distance - dijkstra_distance:+.1f} km "
        "against the shortest route"
    )
    _print_legs(bfs_legs)
    print("")

    astar = AStar(haversine_heuristic())
    astar_distance, astar_legs = planner.find_shortest_route(
        DEPARTURE, ARRIVAL, algorithm=astar
    )
    print(
        f"A* optimal distance:       {astar_distance:.1f} km "
        f"(matches: {astar_distance == dijkstra_distance})"
    )
    _print_legs(astar_legs)
