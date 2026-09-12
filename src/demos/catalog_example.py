"""Example: narrowing a snapshot to the scope an experiment works in.

A `Catalog` sits between frozen data and a `FlightPlanner`. It looks airports
and routes up, narrows the scope along four axes, and records what each
narrowing cost — so a result can state exactly how its graph was derived.

This demo shows the lookups, the narrowing chain, what the three endpoint
modes do differently, and the two ways to materialize a planner.

Run from anywhere:
    uv run python src/demos/catalog_example.py
"""

import warnings
from pathlib import Path

from flight_planner.experiments import Snapshot

SNAPSHOTS_DIR = Path(__file__).resolve().parents[2] / "data" / "snapshots"
SNAPSHOT_ID = "2026-09-11-bb90a8"

DEPARTURE = "SFO"
ARRIVAL = "BOS"

if __name__ == "__main__":
    snapshot = Snapshot.open(SNAPSHOTS_DIR / SNAPSHOT_ID)
    catalog = snapshot.catalog()
    print(f"--- {snapshot.snapshot_id} ---")
    print(f"{len(catalog.routes)} routes / {len(catalog.airports)} airports")

    print("\n--- Lookup ---")
    airport = catalog.airport(ARRIVAL)
    print(
        f"airport({ARRIVAL!r}): {airport.name}, {airport.city} "
        f"({airport.type}, international={airport.is_international})"
    )
    numbers = [route.flight_number for route in catalog.routes_between(DEPARTURE, ARRIVAL)]
    print(f"routes_between({DEPARTURE!r}, {ARRIVAL!r}): {', '.join(numbers)}")

    # The endpoint pair does not identify a leg — several carriers fly it over
    # the identical distance — so route() raises rather than guessing.
    try:
        catalog.route(DEPARTURE, ARRIVAL)
    except LookupError as error:
        print(f"route({DEPARTURE!r}, {ARRIVAL!r}): {error}")
    print(f"route(..., airline='UA'): {catalog.route(DEPARTURE, ARRIVAL, airline='UA')}")

    # The flight number is the only unique handle on a route.
    flight = catalog.flight("UA1876")
    print(f"flight('UA1876'): {flight.origin.iata_code} -> {flight.destination.iata_code}")

    print("\n--- Narrowing, and what each step cost ---")
    narrowed = catalog.airline("UA").airport_type("large").country("US")
    summary = narrowed.summary()
    for step in summary["chain"]:
        arguments = ", ".join(str(value) for value in step["arguments"])
        print(
            f"  {step['operation']}({arguments}) -> "
            f"{step['routes'][1]} routes / {step['airports'][1]} airports"
        )
    print(f"routes:   {summary['routes']}")
    print(f"airports: {summary['airports']}")
    print(f"dangling: {summary['dangling']}")

    # `summary()` is what goes into results.json, so a recorded number always
    # carries the derivation of the graph it came from.

    print("\n--- The three endpoint modes ---")
    print("Narrowing United's network to large airports:")
    print(f"{'mode':<10}{'routes':>8}{'airports':>10}{'dangling':>10}")
    united = catalog.airline("UA")
    for mode in ("both", "either", "airports"):
        scope = united.airport_type("large", endpoints=mode)
        print(
            f"{mode:<10}{len(scope.routes):>8}{len(scope.airports):>10}"
            f"{len(scope.dangling):>10}"
        )

    # "both" is the default because it is the only mode that commutes: pruning
    # routes so that both ends qualify and re-deriving the airports from what
    # survives makes the order of two narrowings irrelevant.
    forwards = catalog.airline("UA").airport_type("large")
    backwards = catalog.airport_type("large").airline("UA")
    print(
        "airline then airport_type == airport_type then airline: "
        f"{forwards.routes == backwards.routes}"
    )

    print("\n--- Dangling edges are reported, not forbidden ---")
    # Under "airports" the routes are untouched, so some point at airports
    # outside the scope. planner() builds that graph as asked, and warns.
    loose = united.airport_type("large", endpoints="airports")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        loose_planner = loose.planner()
    for warning in caught:
        print(f"  UserWarning: {warning.message}")
    print(f"  built anyway: {len(loose_planner.vertices)} airports / {len(loose_planner.edges)} routes")

    print("\n--- Materializing ---")
    planner = narrowed.planner()
    total_km, legs = planner.find_shortest_route(DEPARTURE, ARRIVAL)
    print(f"planner():  {DEPARTURE} -> {ARRIVAL} is {total_km:.1f} km over {len(legs)} leg(s)")

    # subgraph() hand-assembles a small network out of real entities — three
    # flights with real coordinates, rather than a whole slice.
    hand_built = catalog.subgraph(["UA1875", "UA1876"])
    print(
        f"subgraph(['UA1875', 'UA1876']): {len(hand_built.vertices)} airports / "
        f"{len(hand_built.edges)} routes"
    )
    for route in hand_built.edges:
        print(
            f"  • {route.flight_number}: {route.origin.iata_code} -> "
            f"{route.destination.iata_code} ({route.distance_km:.1f} km)"
        )
