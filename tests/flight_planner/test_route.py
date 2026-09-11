from flight_planner.flights import Airport
from flight_planner.flights import Route


class TestRoute:
    def test_origin_destination_distance(self):
        jfk, lax = Airport("JFK"), Airport("LAX")
        route = Route(jfk, lax, distance_km=3980.0, airline="Delta", flight_number="DL1")

        assert route.origin == jfk
        assert route.destination == lax
        assert route.distance_km == 3980.0
        assert route.airline == "Delta"
        assert route.flight_number == "DL1"

    def test_maps_onto_edge_interface(self):
        jfk, lax = Airport("JFK"), Airport("LAX")
        route = Route(jfk, lax, distance_km=3980.0)

        assert route.source == jfk
        assert route.target == lax
        assert route.weight == 3980.0
