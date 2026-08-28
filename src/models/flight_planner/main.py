"""Example: build a small flight network and find shortest routes."""

from airport import Airport
from route import Route
from flight_planner import FlightPlanner

if __name__ == "__main__":
    planner = FlightPlanner()

    # Define Airports
    jfk = Airport("JFK", name="John F. Kennedy Intl", city="New York", country="USA")
    lhr = Airport("LHR", name="Heathrow", city="London", country="UK")
    cdg = Airport("CDG", name="Charles de Gaulle", city="Paris", country="France")
    dxb = Airport("DXB", name="Dubai Intl", city="Dubai", country="UAE")
    hnd = Airport("HND", name="Haneda", city="Tokyo", country="Japan")
    sin = Airport("SIN", name="Changi", city="Singapore", country="Singapore")

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

    print("\n--- Finding Shortest Path (JFK -> HND) ---")
    dist, itinerary = planner.find_shortest_route("JFK", "HND")
    print(f"Optimal Distance: {dist:.1f} km")
    print("Flight Legs:")
    for leg in itinerary:
        print(f"  • {leg.flight_number} ({leg.airline}): {leg.origin.iata_code} -> {leg.destination.iata_code} ({leg.distance_km:.1f} km)")

    print("\n--- Finding Multi-Stop Path (LHR -> HND) ---")
    dist_lhr_hnd, legs_lhr_hnd = planner.find_shortest_route("LHR", "HND")
    print(f"Optimal Distance: {dist_lhr_hnd:.1f} km")
    for leg in legs_lhr_hnd:
        print(f"  • {leg.flight_number} ({leg.airline}): {leg.origin.iata_code} -> {leg.destination.iata_code} ({leg.distance_km:.1f} km)")
