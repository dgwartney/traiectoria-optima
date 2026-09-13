"""Example: looking up airports, routes and itineraries from a script.

This is the route-query surface, exercised end to end on real data. Every
other demo shows one piece of it: `catalog_example.py` looks things up but
routes with only the default algorithm, and `search_instrumentation_example.py`
compares all three algorithms but on an eight-airport network built by hand.
This one does both, on the frozen world snapshot.

There is no CLI and no widget, because none is needed. The functions below are
the whole query surface, and they are written to be imported as readily as run:

    >>> from route_query_example import open_catalog, compare_modes
    >>> catalog = open_catalog()
    >>> for name, result in compare_modes(catalog.planner(), "SFO", "BOS").items():
    ...     print(name, result.cost, result.unit)

Four things worth noticing, because each was a rough edge before:

- **The heuristic comes from `haversine_heuristic()`.** Do not hand-roll one:
  which formula you pick decides whether A*'s answer is guaranteed optimal.
- **Every result says what its cost counts.** `result.unit` is `COST_HOPS` for
  BFS and `COST_WEIGHT` for the other two, so nothing has to infer the unit
  from the algorithm's name and no column silently mixes hops with kilometres.
- **Every failed lookup raises `FlightPlannerError`.** One `except` covers an
  unknown airport, an unknown flight number and an ambiguous airport pair.
- **Opening a snapshot re-hashes it.** The numbers below came from data that
  was verified against its manifest on the way in.

Run from anywhere:
    uv run python src/demos/route_query_example.py
"""

from pathlib import Path
from typing import Dict

from flight_planner import (
    COST_HOPS,
    AStar,
    BFS,
    Dijkstra,
    FlightPlanner,
    SearchResult,
    haversine_heuristic,
)
from flight_planner.errors import FlightPlannerError
from flight_planner.experiments import Catalog, Snapshot

# The package takes directories from its caller, so the demo locates the
# repository's snapshots relative to this file rather than the process's cwd.
SNAPSHOTS_DIR = Path(__file__).resolve().parents[2] / "data" / "snapshots"
SNAPSHOT_ID = "2026-09-11-bb90a8"

DEPARTURE = "SFO"
ARRIVAL = "BOS"


def open_catalog(snapshot_id: str = SNAPSHOT_ID) -> Catalog:
    """Open a frozen snapshot and return its catalog.

    Args:
        snapshot_id: Directory name under `data/snapshots`.

    Returns:
        A `Catalog` over the whole snapshot, unnarrowed. Narrow it with
        `.airline(...)`, `.country(...)` or `.airport_type(...)` before calling
        `.planner()` to query a smaller network.
    """
    return Snapshot.open(SNAPSHOTS_DIR / snapshot_id).catalog()


def compare_modes(
    planner: FlightPlanner, origin: str, destination: str
) -> Dict[str, SearchResult]:
    """Run all three query modes over one airport pair.

    The project's central claim in one call: A* returns the same route as
    Dijkstra while expanding far fewer nodes, and BFS answers a different
    question entirely.

    Args:
        planner: Network to query, from `Catalog.planner()`.
        origin: Departure IATA code.
        destination: Arrival IATA code.

    Returns:
        Mapping of mode name to its `SearchResult`. Each result carries the
        route, the cost, the `unit` that cost is measured in, and the search's
        own counters.

    Raises:
        AirportNotFoundError: If either code is not in the network.
    """
    modes = {
        "fewest stops": BFS(),
        "shortest distance": Dijkstra(),
        "shortest distance (A*)": AStar(haversine_heuristic()),
    }
    return {
        name: planner.search_route(origin, destination, algorithm)
        for name, algorithm in modes.items()
    }


def format_result(origin: str, result: SearchResult) -> str:
    """Render one search result as a single line.

    Args:
        origin: Departure IATA code, needed because a result holds only legs.
        result: What `compare_modes` returned for one mode.

    Returns:
        A line carrying the cost with its unit, the nodes expanded, and the
        itinerary. Unreachable pairs render as `no route`.
    """
    if not result.found:
        return f"{'no route':>26}  expanded {result.nodes_expanded:>5}"
    unit = "hops" if result.unit == COST_HOPS else "km"
    route = " -> ".join(
        [origin] + [leg.destination.iata_code for leg in result.path]
    )
    return (
        f"{result.cost:>20,.1f} {unit:<5} expanded {result.nodes_expanded:>5}"
        f"  {route}"
    )


def main() -> None:
    """Look an airport up, inspect its routes, then query three ways."""
    catalog = open_catalog()
    print(f"--- snapshot {SNAPSHOT_ID} ---")
    print(f"{len(catalog.airports):,} airports / {len(catalog.routes):,} routes")

    print("\n--- Looking an airport up ---")
    airport = catalog.airport(ARRIVAL)
    print(f"{airport.iata_code}: {airport.name}")
    print(
        f"    {airport.city}, {airport.country} — {airport.type}, "
        f"international={airport.is_international}"
    )
    print(f"    {airport.latitude:.4f}, {airport.longitude:.4f}")

    print("\n--- Looking its routes up ---")
    departures = catalog.routes_from(ARRIVAL)
    arrivals = catalog.routes_to(ARRIVAL)
    print(f"routes_from({ARRIVAL!r}): {len(departures):,} departures")
    print(f"routes_to({ARRIVAL!r}):   {len(arrivals):,} arrivals")
    carriers = sorted({route.airline for route in arrivals})
    print(f"    carriers arriving: {', '.join(carriers[:12])}, ...")
    on_the_pair = catalog.routes_between(DEPARTURE, ARRIVAL)
    numbers = ", ".join(route.flight_number for route in on_the_pair)
    print(f"routes_between({DEPARTURE!r}, {ARRIVAL!r}): {numbers}")

    print("\n--- When a lookup does not resolve ---")
    # One exception type covers all three, so a script or notebook needs one
    # `except` rather than guessing between KeyError, LookupError and
    # ValueError -- and the message prints without stray quotes around it.
    for description, ask in (
        ("unknown airport", lambda: catalog.airport("ZZZ")),
        ("unknown flight", lambda: catalog.flight("ZZ9999")),
        ("ambiguous pair", lambda: catalog.route(DEPARTURE, ARRIVAL)),
    ):
        try:
            ask()
        except FlightPlannerError as error:
            print(f"{description:<17} {type(error).__name__}: {error}")

    print("\n--- Querying three ways ---")
    planner = catalog.planner()
    print(f"{DEPARTURE} -> {ARRIVAL}\n")
    print(f"{'mode':<24}{'cost':>20} {'unit':<5} {'expanded':>14}  route")
    for name, result in compare_modes(planner, DEPARTURE, ARRIVAL).items():
        print(f"{name:<24}{format_result(DEPARTURE, result)}")

    print(
        "\nBFS answers a different question — its cost is a hop count, not a\n"
        "distance, which is why the unit column is not decoration. Dijkstra and\n"
        "A* agree on the route and the distance; A* reaches it having expanded\n"
        "far fewer airports, which is the result this project exists to show."
    )

    print("\n--- The same query on a narrowed network ---")
    # Narrowing records what it did, so a result can state how its graph was
    # derived rather than leaving the reader to guess.
    narrowed = catalog.airline("UA").country("US")
    print(f"{narrowed!r}")
    for name, result in compare_modes(
        narrowed.planner(), DEPARTURE, ARRIVAL
    ).items():
        print(f"{name:<24}{format_result(DEPARTURE, result)}")


if __name__ == "__main__":
    main()
