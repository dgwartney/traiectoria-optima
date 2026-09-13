"""Re-derive the numbers report §2.5 states as fact.

`graph-stats` was the only committed experiment nothing re-verified, and it is
the one the report leans on hardest: §2.5 quotes roughly twenty of its figures
-- size, density, the degree table, the reachability counts, the component
structure -- and §3.4 builds the adjacency-list argument on its density. A
drift in the snapshot or the measurement code would have left every one of
those stale with a green suite.

The cheap figures are recomputed from the pinned snapshot and compared against
the record. The two expensive ones -- the strongly connected core, and
reachability, which the experiment measures by turning `BFS` into a probe --
are asserted for internal consistency instead, since re-running a full
traversal per airport does not belong in the default suite.

It also pins the **pair-counting convention**, which is the one place two
committed experiments look like they disagree: `graph-stats` counts *directed*
pairs and `route-map` counts *undirected* ones. Neither said so, and 36,717
against 18,814 reads as a contradiction until one does.
"""

import json
from collections import Counter

import pytest

from flight_planner.experiments import Experiment

SLUG = "graph-stats"
SNAPSHOT_ID = "2026-09-11-bb90a8"


@pytest.fixture(scope="module")
def experiment(repo_root):
    """Open the committed experiment, verifying its snapshot on the way."""
    return Experiment.open(repo_root / "experiments" / SLUG)


@pytest.fixture(scope="module")
def recorded(repo_root):
    """Return the committed `results.json` payload."""
    path = repo_root / "experiments" / SLUG / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))["results"]


@pytest.fixture(scope="module")
def network(experiment):
    """Return `(airports, routes)` from the pinned snapshot."""
    catalog = experiment.snapshot.catalog()
    return catalog.airports, catalog.routes


def test_it_pins_the_world_snapshot(experiment):
    assert experiment.snapshot.snapshot_id == SNAPSHOT_ID


class TestSize:
    """The four numbers §2.5 opens with, and §3.4 reuses."""

    def test_airports_and_routes(self, network, recorded):
        airports, routes = network

        assert len(airports) == recorded["size"]["airports"] == 3387
        assert len(routes) == recorded["size"]["routes"] == 66332

    def test_distinct_pairs_and_the_parallel_remainder(self, network, recorded):
        """36,717 + 29,615 = 66,332, exactly. The identity §2.4 rests on."""
        _, routes = network
        pairs = {(r.origin.iata_code, r.destination.iata_code) for r in routes}

        size = recorded["size"]
        assert len(pairs) == size["airport_pairs"] == 36717
        assert len(routes) - len(pairs) == size["parallel_routes"] == 29615
        assert size["airport_pairs"] + size["parallel_routes"] == size["routes"]

    def test_density_is_the_figure_the_adjacency_list_argument_uses(self, recorded):
        """0.32%, and the 11,468,382 cells a matrix would have allocated."""
        size = recorded["size"]

        assert size["possible_pairs"] == 3387 * 3386 == 11468382
        assert size["density"] == pytest.approx(
            size["airport_pairs"] / size["possible_pairs"]
        )
        assert round(size["density"] * 100, 2) == 0.32
        # What §3.4 actually claims: a matrix spends over 99.6% of itself
        # recording that a route is absent.
        assert 1 - size["density"] > 0.996


class TestDegree:
    """The table §2.5 prints, recomputed rather than trusted."""

    def test_out_degree(self, network, recorded):
        airports, routes = network
        counts = Counter(r.origin.iata_code for r in routes)
        degrees = [counts.get(a.iata_code, 0) for a in airports]

        out = recorded["degree"]["out"]
        assert min(degrees) == out["min"] == 0
        assert max(degrees) == out["max"] == 915
        assert sum(degrees) / len(degrees) == pytest.approx(out["mean"])
        assert counts.most_common(1)[0][0] == out["busiest"] == "ATL"

    def test_in_degree(self, network, recorded):
        airports, routes = network
        counts = Counter(r.destination.iata_code for r in routes)
        degrees = [counts.get(a.iata_code, 0) for a in airports]

        incoming = recorded["degree"]["in"]
        assert max(degrees) == incoming["max"] == 911
        assert counts.most_common(1)[0][0] == incoming["busiest"] == "ATL"

    def test_the_means_agree_because_every_edge_has_two_ends(self, recorded):
        """A check on the measurement, not on the network.

        Mean out-degree and mean in-degree must be identical -- both are
        E/V -- so a difference would mean the two were counted differently.
        """
        degree = recorded["degree"]
        assert degree["out"]["mean"] == degree["in"]["mean"]
        assert degree["out"]["mean"] == pytest.approx(66332 / 3387)

    def test_the_mean_and_median_gap_is_the_heavy_tail(self, recorded):
        """§2.5 calls this the most important fact about the graph's shape."""
        out = recorded["degree"]["out"]
        assert out["median"] == 4
        assert out["mean"] / out["median"] > 4

    def test_the_distribution_sums_to_every_airport(self, recorded):
        """A histogram that has lost a bucket would otherwise go unnoticed."""
        total = sum(count for _, count in recorded["degree_distribution"]["out"])
        assert total == recorded["size"]["airports"]


class TestHubs:
    """The ten busiest airports, and the symmetry that validates the cleaning."""

    def test_top_hubs_are_ordered_and_complete(self, recorded):
        hubs = recorded["top_hubs"]
        assert len(hubs) == 10
        assert [h["out_degree"] for h in hubs] == sorted(
            (h["out_degree"] for h in hubs), reverse=True
        )
        assert hubs[0]["iata_code"] == "ATL"

    def test_arrivals_and_departures_track_each_other_at_every_hub(self, recorded):
        """§2.5 uses this as a sanity check on the cleaning rather than a finding.

        Aircraft that arrive must leave, so a large gap at a major airport
        would point at dropped rows.
        """
        for hub in recorded["top_hubs"]:
            ratio = hub["in_degree"] / hub["out_degree"]
            assert 0.95 < ratio < 1.05, f"{hub['iata_code']} is lopsided: {hub}"

    def test_the_ten_busiest_carry_the_share_the_report_quotes(self, recorded):
        """8.1% of all routes."""
        departures = sum(h["out_degree"] for h in recorded["top_hubs"])
        assert round(100 * departures / recorded["size"]["routes"], 1) == 8.1


class TestReachabilityAndComponents:
    """Asserted for consistency rather than re-run.

    The experiment measures these by aiming `BFS` at a sentinel airport that
    is not in the graph, so the search never terminates early and becomes a
    reachability probe. Repeating that per airport is minutes of work, which
    does not belong in the default suite.
    """

    def test_dead_ends_match_the_degree_distribution(self, recorded):
        """16 airports with no departures -- the same 16 the histogram shows.

        Two independent measurements in the same file, so a disagreement
        means one of them is wrong.
        """
        zero_bucket = dict(recorded["degree_distribution"]["out"])["0"]
        assert recorded["reachability"]["no_departures"] == zero_bucket == 16

    def test_no_airport_is_isolated(self, recorded):
        """Every vertex appears in at least one route, so all 3,387 are real."""
        assert recorded["reachability"]["isolated"] == 0

    def test_the_weak_components_account_for_every_airport(self, recorded):
        components = recorded["components"]
        assert components["weak_count"] == len(components["weak_sizes"]) == 8
        assert sum(components["weak_sizes"]) == recorded["size"]["airports"]
        assert components["largest_weak"] == max(components["weak_sizes"]) == 3359

    def test_the_strong_core_is_bounded_by_what_reaches_the_seed(self, recorded):
        """The core is the intersection of two reachable sets, so it cannot
        exceed either. A recorded core larger than one of them would be a bug
        in the measurement rather than a property of the network."""
        components = recorded["components"]
        assert components["strong_core"] <= components["reachable_from_seed"]
        assert components["strong_core"] <= components["can_reach_seed"]
        assert components["strong_core"] == 3318

    def test_the_percentages_the_report_quotes(self, recorded):
        airports = recorded["size"]["airports"]
        components = recorded["components"]
        assert round(100 * components["largest_weak"] / airports, 1) == 99.2
        assert round(100 * components["strong_core"] / airports, 1) == 98.0


class TestThePairCountingConvention:
    """Why 36,717 and 18,814 are not a contradiction.

    `graph-stats` counts **directed** pairs; `route-map` counts **undirected**
    ones. Neither artifact said so, and the two numbers read as a disagreement
    until one does. Pinning the arithmetic here means the convention cannot be
    silently reinterpreted later.
    """

    def test_graph_stats_counts_directed_pairs(self, network, recorded):
        _, routes = network
        directed = {(r.origin.iata_code, r.destination.iata_code) for r in routes}

        assert len(directed) == recorded["size"]["airport_pairs"]

    def test_route_map_counts_undirected_pairs(self, network, repo_root):
        _, routes = network
        undirected = {
            frozenset((r.origin.iata_code, r.destination.iata_code)) for r in routes
        }
        route_map = json.loads(
            (repo_root / "experiments" / "route-map" / "results.json").read_text(
                encoding="utf-8"
            )
        )["results"]["network"]

        assert len(undirected) == route_map["distinct_pairs"] == 18814

    def test_the_difference_is_911_one_directional_pairs(self, network):
        """The finding the two conventions produce when reconciled.

        Every undirected pair is one or two directed pairs, so
        `2 x undirected - directed` counts the ones served in a single
        direction only.
        """
        _, routes = network
        directed = {(r.origin.iata_code, r.destination.iata_code) for r in routes}
        undirected = {frozenset(pair) for pair in directed}

        one_way = 2 * len(undirected) - len(directed)
        assert one_way == 911

        # And the complement: pairs flown both ways.
        both_ways = len(directed) - len(undirected)
        assert both_ways == len(undirected) - one_way == 17903

    def test_the_parallel_share_is_the_45_percent_the_report_quotes(self, recorded):
        size = recorded["size"]
        assert round(100 * size["parallel_routes"] / size["routes"], 1) == 44.6
