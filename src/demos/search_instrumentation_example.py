"""Example: what a search cost, not just what it found.

Every other demo asks "which route?". This one asks "what did finding it
take?" — the question the project exists to answer, since A* earns its place
by reaching Dijkstra's answer while expanding far fewer nodes.

Two ways to see it:

- `search()` returns a `SearchResult` carrying the route *and* the counters:
  nodes expanded, nodes queued, peak frontier size.
- a `SearchObserver` watches the search as it runs, so `ExpansionTrace` can
  record the order vertices were reached in — the shape of the search rather
  than its size.

The network is eight airports on one line of longitude, chosen so the numbers
are checkable by eye: a corridor from SFO east to BOS, plus a spur running the
wrong way. The spur is close to the start and far from the goal, which is
exactly the situation a heuristic exists to notice.

Run from anywhere:
    uv run python src/demos/search_instrumentation_example.py
"""

from flight_planner import (
    Airport,
    AStar,
    BFS,
    Dijkstra,
    ExpansionTrace,
    FlightPlanner,
    Route,
    SearchObserver,
)

# Roughly-real coordinates on a west-to-east corridor, plus a spur heading
# back out over the Pacific. Latitude is held constant so the geometry stays
# legible: distance is then purely east-west.
LATITUDE = 40.0
AIRPORTS = {
    "HNL": -157.9,  # the spur: far west, the wrong way entirely
    "OGG": -156.4,
    "SFO": -122.4,  # origin
    "SLC": -111.9,
    "DEN": -104.7,
    "ORD": -87.9,
    "CLE": -81.8,
    "BOS": -71.0,  # destination
}

CORRIDOR = ["SFO", "SLC", "DEN", "ORD", "CLE", "BOS"]
SPUR = ["SFO", "OGG", "HNL"]


def build_network() -> FlightPlanner:
    """Build the eight-airport corridor and its westward spur.

    Returns:
        A `FlightPlanner` with legs along the corridor and out to the spur,
        each weighted by great-circle distance.
    """
    planner = FlightPlanner()
    airports = {
        code: Airport(code, latitude=LATITUDE, longitude=longitude)
        for code, longitude in AIRPORTS.items()
    }
    for chain in (CORRIDOR, SPUR):
        for origin, destination in zip(chain, chain[1:]):
            start, end = airports[origin], airports[destination]
            planner.add_edge(
                Route(start, end, distance_km=start.distance_to(end))
            )
    return planner


class NarratingObserver(SearchObserver):
    """An observer that says what it sees, to show the hooks firing.

    Attributes:
        label: Name of the algorithm being watched, used in the output.
    """

    def __init__(self, label: str) -> None:
        """Name the search this observer is watching.

        Args:
            label: Algorithm name to print alongside each expansion.
        """
        self.label = label

    def on_expand(self, vertex, cost_so_far) -> None:
        """Print each expansion as it happens.

        Args:
            vertex: The airport being expanded.
            cost_so_far: Distance of the best known route to it.
        """
        print(f"      {self.label} expands {vertex.iata_code} at {cost_so_far:,.0f} km")


def main() -> None:
    """Run all three algorithms over the corridor and report what each cost."""
    planner = build_network()
    heuristic = lambda origin, goal: origin.distance_to(goal)  # noqa: E731

    print(__doc__.split("Run from anywhere:")[0].strip())
    print(f"\nNetwork: {len(planner.vertices)} airports, {len(planner.edges)} legs")
    print(f"Query:   SFO -> BOS\n")

    # ------------------------------------------------------------------
    # 1. The counters
    # ------------------------------------------------------------------
    print("1. What each search cost")
    print(f"   {'algorithm':<12}{'expanded':>9}{'pushed':>8}{'peak':>6}{'cost':>12}  route")
    results = {}
    for name, algorithm in [
        ("BFS", BFS()),
        ("Dijkstra", Dijkstra()),
        ("A*", AStar(heuristic)),
    ]:
        result = planner.search_route("SFO", "BOS", algorithm)
        results[name] = result
        route = "->".join(["SFO"] + [leg.destination.iata_code for leg in result.path])
        # BFS measures hops, the other two measure kilometres -- never put
        # them in one column and call it "cost".
        unit = "hops" if name == "BFS" else "km"
        print(
            f"   {name:<12}{result.nodes_expanded:>9}{result.nodes_pushed:>8}"
            f"{result.peak_frontier:>6}{result.cost:>9,.0f} {unit:<3} {route}"
        )

    print(
        f"\n   Dijkstra and A* agree on the route and the distance, but A* got"
        f"\n   there on {results['A*'].nodes_expanded} expansion(s) against"
        f" {results['Dijkstra'].nodes_expanded}. That is the whole claim."
    )

    # ------------------------------------------------------------------
    # 2. The shape of the search
    # ------------------------------------------------------------------
    print("\n2. Where each search looked, in order")
    for name, algorithm in [("Dijkstra", Dijkstra()), ("A*", AStar(heuristic))]:
        trace = ExpansionTrace()
        planner.search_route("SFO", "BOS", algorithm, observer=trace)
        looked = " ".join(airport.iata_code for airport in trace.order)
        print(f"   {name:<10} {looked}")
    print(
        "\n   Dijkstra walks out to OGG and HNL because they are *near SFO*."
        "\n   A* never does: they are near the start but far from the goal,"
        "\n   and only a heuristic can tell the difference."
    )

    # ------------------------------------------------------------------
    # 3. Writing your own observer
    # ------------------------------------------------------------------
    print("\n3. A custom observer -- override only the hook you want")
    planner.search_route("SFO", "BOS", Dijkstra(), observer=NarratingObserver("Dijkstra"))

    # ------------------------------------------------------------------
    # 4. The old contract still holds
    # ------------------------------------------------------------------
    print("\n4. find_path() is unchanged, for callers that do not care")
    cost, legs = planner.find_shortest_route("SFO", "BOS")
    print(f"   find_shortest_route -> ({cost:,.0f} km, {len(legs)} legs)")
    print("   ...which is exactly the cost and path off the SearchResult above.")


if __name__ == "__main__":
    main()
