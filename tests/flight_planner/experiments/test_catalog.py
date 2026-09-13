import warnings

import pytest

from flight_planner.experiments import Catalog, Snapshot
from flight_planner.flights.airport import Airport
from flight_planner.flights.route import Route


# A hand-built network small enough to reason about exactly, exercising every
# axis the catalog narrows on: airline, airport type, country, and the
# international flag. Distances are nominal -- nothing here tests geography.
HUB = Airport("HUB", name="Hub", country="US", type="large_airport", is_international=True)
BIG = Airport("BIG", name="Big", country="US", type="large_airport", is_international=True)
MED = Airport("MED", name="Med", country="US", type="medium_airport", is_international=False)
FOR = Airport("FOR", name="Foreign", country="CA", type="large_airport", is_international=True)


def route(number, airline, origin, destination, distance_km=100.0):
    return Route(
        origin=origin,
        destination=destination,
        distance_km=distance_km,
        airline=airline,
        flight_number=number,
    )


@pytest.fixture
def catalog():
    routes = [
        route("UA0001", "UA", HUB, BIG),
        route("UA0002", "UA", BIG, HUB),
        route("UA0003", "UA", HUB, MED),
        route("UA0004", "UA", HUB, FOR),
        route("AA0001", "AA", HUB, BIG),
    ]
    return Catalog([HUB, BIG, MED, FOR], routes)


class TestLookup:
    def test_airport_by_iata(self, catalog):
        assert catalog.airport("HUB") is HUB

    def test_airport_code_is_normalized(self, catalog):
        assert catalog.airport(" hub ") is HUB

    def test_unknown_airport_raises(self, catalog):
        with pytest.raises(KeyError, match="XXX"):
            catalog.airport("XXX")

    def test_flight_returns_exactly_one_route(self, catalog):
        leg = catalog.flight("UA0001")
        assert (leg.origin, leg.destination, leg.airline) == (HUB, BIG, "UA")

    def test_unknown_flight_raises(self, catalog):
        with pytest.raises(KeyError, match="UA9999"):
            catalog.flight("UA9999")

    def test_route_respects_direction(self, catalog):
        assert catalog.route("HUB", "FOR").flight_number == "UA0004"
        with pytest.raises(LookupError, match="FOR -> HUB"):
            catalog.route("FOR", "HUB")

    def test_ambiguous_route_names_the_candidates(self, catalog):
        # HUB -> BIG is flown by both UA and AA, so the endpoint pair does not
        # identify a route. The error has to say which flights to pick from.
        with pytest.raises(LookupError) as error:
            catalog.route("HUB", "BIG")
        assert "UA0001" in str(error.value)
        assert "AA0001" in str(error.value)

    def test_ambiguous_route_resolved_by_airline(self, catalog):
        assert catalog.route("HUB", "BIG", airline="AA").flight_number == "AA0001"

    def test_routes_between_returns_every_carrier(self, catalog):
        numbers = {leg.flight_number for leg in catalog.routes_between("HUB", "BIG")}
        assert numbers == {"UA0001", "AA0001"}

    def test_routes_from_is_outgoing_only(self, catalog):
        numbers = {leg.flight_number for leg in catalog.routes_from("HUB")}
        assert numbers == {"UA0001", "UA0003", "UA0004", "AA0001"}

    def test_routes_to_is_incoming_only(self, catalog):
        numbers = {leg.flight_number for leg in catalog.routes_to("HUB")}
        assert numbers == {"UA0002"}

    def test_routes_to_code_is_normalized(self, catalog):
        assert catalog.routes_to(" hub ") == catalog.routes_to("HUB")

    def test_routes_to_and_from_partition_a_pair(self, catalog):
        # Routes are directed, so the two questions genuinely differ: MED has
        # an arrival and no departures.
        assert {leg.flight_number for leg in catalog.routes_to("MED")} == {"UA0003"}
        assert catalog.routes_from("MED") == ()

    def test_routes_to_unknown_airport_is_empty(self, catalog):
        assert catalog.routes_to("ZZZ") == ()


class TestNarrowing:
    def test_airline_keeps_only_that_carrier(self, catalog):
        united = catalog.airline("UA")
        assert len(united.routes) == 4
        assert {leg.airline for leg in united.routes} == {"UA"}

    def test_airline_rederives_the_airports(self, catalog):
        # AA only flies HUB -> BIG, so narrowing to it drops MED and FOR.
        american = catalog.airline("AA")
        assert set(american.iata_codes) == {"HUB", "BIG"}

    def test_airport_type_both_endpoints_by_default(self, catalog):
        large = catalog.airport_type("large_airport")
        assert {leg.flight_number for leg in large.routes} == {
            "UA0001",
            "UA0002",
            "UA0004",
            "AA0001",
        }
        assert set(large.iata_codes) == {"HUB", "BIG", "FOR"}

    def test_airport_type_accepts_the_short_name(self, catalog):
        assert catalog.airport_type("large").routes == catalog.airport_type(
            "large_airport"
        ).routes

    def test_airport_type_either_endpoint(self, catalog):
        either = catalog.airport_type("large", endpoints="either")
        assert "UA0003" in {leg.flight_number for leg in either.routes}
        # MED is kept because it is an endpoint of a route that qualified,
        # even though MED itself is not a large airport.
        assert "MED" in either.iata_codes

    def test_airport_type_airports_only_leaves_routes_alone(self, catalog):
        scoped = catalog.airport_type("large", endpoints="airports")
        assert len(scoped.routes) == 5
        assert set(scoped.iata_codes) == {"HUB", "BIG", "FOR"}
        assert {leg.flight_number for leg in scoped.dangling} == {"UA0003"}

    def test_country_narrows_to_domestic(self, catalog):
        domestic = catalog.country("us")
        assert "UA0004" not in {leg.flight_number for leg in domestic.routes}
        assert "FOR" not in domestic.iata_codes

    def test_international_flag(self, catalog):
        assert set(catalog.international().iata_codes) == {"HUB", "BIG", "FOR"}

    def test_international_can_be_inverted(self, catalog):
        # Under "both" no route has two domestic-only endpoints, so asking for
        # the airports themselves is the useful form of the question.
        scoped = catalog.international(False, endpoints="airports")
        assert scoped.iata_codes == ("MED",)

    def test_unknown_endpoint_mode_is_rejected(self, catalog):
        with pytest.raises(ValueError, match="sideways"):
            catalog.airport_type("large", endpoints="sideways")

    def test_narrowing_does_not_mutate_the_source(self, catalog):
        catalog.airline("AA")
        assert len(catalog.routes) == 5

    def test_both_commutes(self, catalog):
        forward = catalog.airline("UA").airport_type("large")
        backward = catalog.airport_type("large").airline("UA")
        assert forward.routes == backward.routes
        assert forward.iata_codes == backward.iata_codes

    def test_airports_mode_does_not_commute(self, catalog):
        # Documented, not prevented: "airports" narrows lookups without
        # touching routes, so it depends on what ran before it.
        forward = catalog.airport_type("large", endpoints="airports").country("US")
        backward = catalog.country("US").airport_type("large", endpoints="airports")
        assert len(forward.routes) != len(backward.routes)


class TestSummary:
    def test_records_the_chain(self, catalog):
        summary = catalog.airline("UA").airport_type("large").summary()
        assert [step["operation"] for step in summary["chain"]] == [
            "airline",
            "airport_type",
        ]
        assert summary["routes"] == [5, 4, 3]
        assert summary["airports"] == [4, 4, 3]
        assert summary["dangling"] == 0

    def test_empty_chain_still_reports_counts(self, catalog):
        assert catalog.summary() == {
            "chain": [],
            "routes": [5],
            "airports": [4],
            "dangling": 0,
        }

    def test_records_the_arguments(self, catalog):
        step = catalog.country("US", "CA").summary()["chain"][0]
        assert step["arguments"] == ["US", "CA"]
        assert step["endpoints"] == "both"


class TestMaterializing:
    def test_planner_holds_the_narrowed_scope(self, catalog):
        planner = catalog.airline("AA").planner()
        assert len(planner.vertices) == 2
        assert len(planner.edges) == 1

    def test_planner_shares_airport_identity(self, catalog):
        assert catalog.planner().find_airport("HUB") is HUB

    def test_planner_warns_about_dangling_edges(self, catalog):
        scoped = catalog.airport_type("large", endpoints="airports")
        with pytest.warns(UserWarning, match="1 route"):
            scoped.planner()

    def test_planner_is_quiet_when_nothing_dangles(self, catalog):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            catalog.airport_type("large").planner()

    def test_subgraph_holds_only_the_named_legs(self, catalog):
        planner = catalog.subgraph(["UA0001", "UA0004"])
        assert len(planner.edges) == 2
        assert {airport.iata_code for airport in planner.vertices} == {
            "HUB",
            "BIG",
            "FOR",
        }

    def test_subgraph_accepts_route_objects(self, catalog):
        planner = catalog.subgraph([catalog.flight("UA0002")])
        assert len(planner.edges) == 1


@pytest.fixture(scope="module")
def legacy(legacy_snapshot_dir):
    return Snapshot.open(legacy_snapshot_dir).catalog()


class TestAgainstTheLegacySnapshot:
    """The catalog against real, immutable data rather than a fixture."""

    def test_loads_the_whole_snapshot(self, legacy):
        assert len(legacy.routes) == 861
        assert len(legacy.airports) == 88

    def test_narrowing_to_its_own_criteria_changes_nothing(self, legacy):
        # The snapshot was frozen as UA / large_airport / US, so re-applying
        # those narrowings has to be a no-op.
        narrowed = legacy.airline("UA").airport_type("large_airport").country("US")
        assert len(narrowed.routes) == 861
        assert len(narrowed.airports) == 88
        assert narrowed.summary()["dangling"] == 0

    def test_flight_number_is_the_unique_handle(self, legacy):
        leg = legacy.flight("UA0005")
        assert (leg.origin.iata_code, leg.destination.iata_code) == ("ABQ", "DEN")

    def test_planner_matches_the_snapshot_loader(self, legacy, legacy_snapshot_dir):
        planner = legacy.planner()
        loaded = Snapshot.open(legacy_snapshot_dir).load_planner()
        assert len(planner.vertices) == len(loaded.vertices)
        assert len(planner.edges) == len(loaded.edges)
