"""The two validation experiments must keep producing what they recorded.

Following `test_committed.py`: a recorded result is only worth citing if it
still follows from the data. These tests re-derive the cheap parts of each
result from the snapshot and compare, and check the expensive parts for
internal consistency rather than re-running a sweep that takes minutes.

The distinction that matters here: a parity experiment's *headline* is a
zero. "No disagreements" is exactly the claim that rots silently, because a
result file keeps saying zero long after the code stopped agreeing.
"""

import math

import networkx as nx
import pytest

from flight_planner import AStar, Dijkstra
from flight_planner.experiments import Experiment
from flight_planner.geo import Haversine, Memoized
from validation import (
    NetworkXAStar,
    NetworkXDijkstra,
    NetworkXView,
    ReopeningAStar,
)

PARITY_SLUG = "networkx-parity"
CONSISTENCY_SLUG = "astar-consistency"


@pytest.fixture(scope="module")
def parity(repo_root):
    return Experiment.open(repo_root / "experiments" / PARITY_SLUG)


@pytest.fixture(scope="module")
def consistency(repo_root):
    return Experiment.open(repo_root / "experiments" / CONSISTENCY_SLUG)


@pytest.fixture(scope="module")
def heuristic():
    formula = Memoized(Haversine())
    return lambda origin, goal: origin.distance_to(goal, formula=formula)


class TestTheParityExperiment:
    """`experiments/networkx-parity`."""

    def test_it_recorded_a_result(self, parity):
        assert parity.results() is not None

    def test_the_snapshot_still_verifies(self, parity):
        # Opening it re-hashes every file against the manifest.
        assert parity.snapshot.snapshot_id == "2026-09-11-bb90a8"

    def test_it_pins_the_whole_world_not_a_slice(self, parity):
        # A parity claim about long-haul queries needs a graph with long hauls.
        assert parity.snapshot.criteria == {}

    def test_the_recorded_graph_size_is_still_the_snapshot_size(self, parity):
        recorded = parity.results()["results"]["graph"]
        planner = parity.catalog().planner()

        assert recorded["routes"] == len(planner.edges)
        assert recorded["airport_pairs"] < recorded["routes"]

    def test_the_digraph_collapse_figure_is_still_true(self, parity):
        # The number that justifies MultiDiGraph everywhere in the design.
        recorded = parity.results()["results"]["graph"]
        planner = parity.catalog().planner()
        pairs = {
            (route.origin.iata_code, route.destination.iata_code)
            for route in planner.edges
        }

        assert recorded["routes_a_digraph_would_discard"] == len(
            planner.edges
        ) - len(pairs)

    def test_the_mirror_still_loses_nothing(self, parity):
        planner = parity.catalog().planner()
        view = NetworkXView(planner)

        assert view.order == len(planner.vertices)
        assert view.size == len(planner.edges)

    def test_the_headline_zero_is_still_zero(self, parity):
        assert parity.results()["results"]["total_cost_mismatches"] == 0

    @pytest.mark.parametrize("algorithm", ["Dijkstra", "BFS", "A*"])
    def test_every_algorithm_recorded_no_cost_mismatches(self, parity, algorithm):
        recorded = parity.results()["results"]["parity"][algorithm]

        assert recorded["cost_mismatches"] == 0
        assert recorded["mismatches"] == []

    @pytest.mark.parametrize("algorithm", ["Dijkstra", "BFS", "A*"])
    def test_the_divergence_is_float_noise_not_a_difference(self, parity, algorithm):
        # 3.6e-12 km is four picometres. Anything larger would be a real
        # disagreement wearing a small number's clothes.
        recorded = parity.results()["results"]["parity"][algorithm]

        assert recorded["largest_absolute_divergence_km"] < 1e-6

    def test_the_recorded_named_pairs_still_produce_the_recorded_costs(
        self, parity, heuristic
    ):
        # Re-derived, not trusted. Five pairs is cheap; the 200-pair sweep is
        # not, and is covered by its internal consistency above.
        planner = parity.catalog().planner()
        engines = {
            "Dijkstra": Dijkstra(),
            "A*": AStar(heuristic),
            "nx Dijkstra": NetworkXDijkstra(),
            "nx A*": NetworkXAStar(heuristic),
        }

        for row in parity.results()["results"]["named_pairs"]:
            origin, destination = row["pair"].split("-")
            for name, engine in engines.items():
                cost, _ = planner.find_shortest_route(origin, destination, engine)
                assert cost == pytest.approx(row["cost"][name]), (
                    f"{row['pair']} {name}"
                )

    def test_all_four_weighted_engines_agree_on_every_named_pair(self, parity):
        # The point of the experiment, read straight off the record.
        for row in parity.results()["results"]["named_pairs"]:
            weighted = [
                row["cost"][name]
                for name in ("Dijkstra", "A*", "nx Dijkstra", "nx A*")
            ]
            assert weighted[0] == pytest.approx(weighted[1])
            assert weighted[0] == pytest.approx(weighted[2])
            assert weighted[0] == pytest.approx(weighted[3])

    def test_bfs_answers_a_different_question_and_says_so(self, parity):
        # BFS's cost is a hop count, so it must not be compared with the
        # kilometres beside it. Both BFS engines must still agree though.
        for row in parity.results()["results"]["named_pairs"]:
            assert row["cost"]["BFS"] == pytest.approx(row["cost"]["nx BFS"])
            assert row["cost"]["BFS"] < 100  # legs, not kilometres

    def test_astar_expanded_fewer_nodes_than_dijkstra_on_every_named_pair(
        self, parity
    ):
        for row in parity.results()["results"]["named_pairs"]:
            assert row["expanded"]["A*"] < row["expanded"]["Dijkstra"], row["pair"]

    def test_no_networkx_engine_reports_an_expansion_count(self, parity):
        # Zero counters are deliberate; a column of them in a comparison table
        # would invite being read as a measurement, so they are omitted here.
        for row in parity.results()["results"]["named_pairs"]:
            assert set(row["expanded"]) == {"Dijkstra", "BFS", "A*"}

    def test_both_libraries_agree_that_an_unreachable_pair_has_no_route(
        self, parity
    ):
        recorded = parity.results()["results"]["unreachable"]

        assert recorded["pairs_tested"] > 0
        assert recorded["both_agree_no_route"] == recorded["pairs_tested"]

    def test_the_timing_records_the_machine_it_ran_on(self, parity):
        # A node count reproduces anywhere; a millisecond does not.
        environment = parity.results()["results"]["environment"]

        assert set(environment) == {"cpu", "cores", "platform", "python", "colab"}
        assert parity.results()["results"]["sweep_ms"]

    def test_it_records_which_oracle_version_answered(self, parity):
        # A recorded result goes stale when the oracle moves; a test fails
        # loudly, but the record has to say what it was measured against.
        assert parity.results()["results"]["oracle"].startswith("networkx ")

    def test_the_sample_is_reproducible_from_the_recorded_seed(self, parity):
        planner = parity.catalog().planner()
        view = NetworkXView(planner)
        parameters = parity.results()["parameters"]

        first = view.reachable_pairs(
            parameters["sample_pairs"], seed=parameters["sample_seed"]
        )
        second = view.reachable_pairs(
            parameters["sample_pairs"], seed=parameters["sample_seed"]
        )

        assert first == second
        assert len(first) == parameters["sample_pairs"]


class TestTheAStarConsistencyExperiment:
    """`experiments/astar-consistency`."""

    def test_it_recorded_a_result(self, consistency):
        assert consistency.results() is not None

    def test_the_snapshot_still_verifies(self, consistency):
        assert consistency.snapshot.snapshot_id == "2026-09-12-3e4f9d"

    def test_the_minimal_case_still_reproduces(self, consistency):
        # Four vertices, re-derived from scratch. If this ever stops failing,
        # `astar.py` was patched and the experiment's conclusion has changed.
        from flight_planner.core import Edge, Graph, Vertex

        recorded = consistency.results()["results"]["minimal_case"]
        graph = Graph()
        start, a, b, goal = Vertex("S"), Vertex("A"), Vertex("B"), Vertex("G")
        for edge in (
            Edge(start, a, 2.0),
            Edge(start, b, 1.0),
            Edge(b, a, 0.5),
            Edge(a, goal, 1.0),
        ):
            graph.add_edge(edge)
        scores = recorded["heuristic"]

        def heuristic(vertex, _goal):
            return scores[vertex.key]

        assert Dijkstra().search(graph, start, goal).cost == pytest.approx(
            recorded["Dijkstra"]["cost"]
        )
        assert AStar(heuristic).search(graph, start, goal).cost == pytest.approx(
            recorded["AStar"]["cost"]
        )
        assert ReopeningAStar(heuristic).search(
            graph, start, goal
        ).cost == pytest.approx(recorded["ReopeningAStar"]["cost"])

    def test_the_recorded_minimal_case_shows_both_halves_of_the_defect(
        self, consistency
    ):
        recorded = consistency.results()["results"]["minimal_case"]

        # Suboptimal...
        assert recorded["AStar"]["cost"] > recorded["optimum"]
        # ...and the cost does not describe the path it returned.
        assert recorded["AStar"]["legs_sum_to"] != pytest.approx(
            recorded["AStar"]["cost"]
        )
        # Both of which the patch fixes.
        assert recorded["ReopeningAStar"]["cost"] == pytest.approx(
            recorded["optimum"]
        )
        assert recorded["ReopeningAStar"]["legs_sum_to"] == pytest.approx(
            recorded["ReopeningAStar"]["cost"]
        )

    def test_the_sweep_found_the_shipped_astar_suboptimal(self, consistency):
        recorded = consistency.results()["results"]["randomized"]

        assert recorded["queries"] > 10_000
        assert recorded["astar_suboptimal"] > 0

    def test_the_patch_and_the_oracle_were_both_clean(self, consistency):
        recorded = consistency.results()["results"]["randomized"]

        assert recorded["reopening_astar_suboptimal"] == 0
        assert recorded["networkx_astar_suboptimal"] == 0

    def test_the_sweep_actually_produced_inconsistent_heuristics(self, consistency):
        # A sweep of consistent heuristics would find nothing and prove
        # nothing, while looking exactly like a clean run.
        recorded = consistency.results()["results"]["randomized"]

        assert recorded["inconsistent_goals"] > recorded["goals"] * 0.3

    def test_the_fix_is_nearly_free_in_expansions(self, consistency):
        recorded = consistency.results()["results"]["randomized"]

        assert 0 < recorded["reopening_expansion_overhead"] < 0.05

    def test_the_projects_own_heuristic_is_still_consistent(self, consistency):
        # The reason no committed result depends on any of the above.
        recorded = consistency.results()["results"]["snapshot_heuristic_consistency"]

        assert recorded["checks"] > 100_000
        assert recorded["violations"] == 0

    def test_consistency_is_re_derived_on_a_sample_of_the_snapshot(
        self, consistency
    ):
        # The full sweep is 658,470 checks; a sample keeps the suite fast
        # while still failing if the geometry or the data changed.
        planner = consistency.catalog().planner()
        formula = Memoized(Haversine())
        goals = sorted(planner.vertices, key=lambda airport: airport.iata_code)[:5]

        for goal in goals:
            for route in planner.edges[:500]:
                direct = route.origin.distance_to(goal, formula=formula)
                through = route.distance_km + route.destination.distance_to(
                    goal, formula=formula
                )
                assert direct <= through + 1e-9

    def test_astar_still_agrees_with_dijkstra_on_the_snapshot(self, consistency):
        recorded = consistency.results()["results"]["snapshot_agreement"]

        assert recorded["pairs_checked"] > 8_000
        assert recorded["mismatches"] == []

    def test_taking_the_patch_would_not_move_a_recorded_number(self, consistency):
        # The question the search-cost experiment raised: its comparison table
        # publishes A*'s expansion counts, and test_committed.py pins them.
        recorded = consistency.results()["results"]["snapshot_agreement"]

        assert recorded["patch_changes_expansions"] is False
        assert (
            recorded["nodes_expanded"]["ReopeningAStar"]
            == recorded["nodes_expanded"]["AStar"]
        )

    def test_astar_expanded_far_fewer_nodes_than_dijkstra_overall(self, consistency):
        recorded = consistency.results()["results"]["snapshot_agreement"][
            "nodes_expanded"
        ]

        assert recorded["AStar"] < recorded["Dijkstra"]

    def test_a_sample_of_pairs_still_agrees_when_re_run(self, consistency, heuristic):
        planner = consistency.catalog().planner()
        codes = sorted(airport.iata_code for airport in planner.vertices)[:12]

        for origin in codes:
            for destination in codes:
                if origin == destination:
                    continue
                dijkstra, _ = planner.find_shortest_route(
                    origin, destination, Dijkstra()
                )
                astar, _ = planner.find_shortest_route(
                    origin, destination, AStar(heuristic)
                )
                assert astar == pytest.approx(dijkstra) or (
                    math.isinf(astar) and math.isinf(dijkstra)
                )

    def test_it_records_which_oracle_version_answered(self, consistency):
        assert consistency.results()["results"]["oracle"] == (
            f"networkx {nx.__version__}"
        )
