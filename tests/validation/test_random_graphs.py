"""Unit tests for `validation.random_graphs`.

A randomized harness is only as trustworthy as its generator. If the two
graphs differ, or the heuristic is not admissible, or a run is not
reproducible, then every conclusion drawn from a sweep is worthless — and
worthless in a way that looks like a finding. These tests are the guard.
"""

import math

import networkx as nx
import pytest

from flight_planner.pathfinding import BFS, Dijkstra
from validation.random_graphs import (
    WEIGHTS,
    InconsistentHeuristic,
    RandomGraphPair,
)

SEEDS = range(12)


class TestRandomGraphPair:
    """One graph, built twice, from one seed."""

    @pytest.mark.parametrize("seed", SEEDS)
    def test_both_graphs_have_the_same_vertices(self, seed):
        pair = RandomGraphPair(seed)

        assert {vertex.key for vertex in pair.ours.vertices} == set(pair.theirs.nodes)
        assert pair.order == pair.theirs.number_of_nodes()

    @pytest.mark.parametrize("seed", SEEDS)
    def test_both_graphs_have_the_same_edge_endpoints(self, seed):
        pair = RandomGraphPair(seed)
        ours = {(edge.source.key, edge.target.key) for edge in pair.ours.edges}

        assert ours == set(pair.theirs.edges)

    @pytest.mark.parametrize("seed", SEEDS)
    def test_the_digraph_keeps_the_cheapest_of_any_parallel_pair(self, seed):
        # The subtle way to build a parity suite that compares two different
        # graphs. A shortest path never takes the dearer of two parallel
        # edges, so keeping the cheapest makes the oracle answer *our*
        # question.
        pair = RandomGraphPair(seed)
        cheapest: dict = {}
        for edge in pair.ours.edges:
            key = (edge.source.key, edge.target.key)
            cheapest[key] = min(cheapest.get(key, math.inf), edge.weight)

        for (origin, destination), weight in cheapest.items():
            assert pair.theirs[origin][destination]["weight"] == pytest.approx(weight)

    def test_the_same_seed_gives_the_same_graph(self):
        first, second = RandomGraphPair(7), RandomGraphPair(7)

        assert [vertex.key for vertex in first.vertices] == [
            vertex.key for vertex in second.vertices
        ]
        assert sorted(
            (edge.source.key, edge.target.key, edge.weight) for edge in first.ours.edges
        ) == sorted(
            (edge.source.key, edge.target.key, edge.weight)
            for edge in second.ours.edges
        )

    def test_different_seeds_give_different_graphs(self):
        shapes = {
            (RandomGraphPair(seed).order, RandomGraphPair(seed).theirs.number_of_edges())
            for seed in SEEDS
        }

        assert len(shapes) > 1

    @pytest.mark.parametrize("seed", SEEDS)
    def test_no_weight_is_negative(self, seed):
        # Dijkstra's contract. A negative weight would make the oracle and our
        # algorithm both wrong, which proves nothing.
        pair = RandomGraphPair(seed)

        assert all(edge.weight >= 0.0 for edge in pair.ours.edges)

    def test_zero_weights_and_ties_actually_occur(self):
        # The cases the generator exists to produce. If the draw stopped
        # producing them the sweep would quietly get weaker.
        weights = [
            edge.weight for seed in range(40) for edge in RandomGraphPair(seed).ours.edges
        ]

        assert 0.0 in WEIGHTS
        assert any(weight == 0.0 for weight in weights)
        assert sum(1 for weight in weights if weight == 1.0) > 1

    def test_disconnected_pairs_actually_occur(self):
        # Unreachability is the common case here, not an edge case, and it is
        # the branch a naive harness forgets.
        unreachable = 0
        for seed in range(20):
            pair = RandomGraphPair(seed)
            for start, goal in pair.ordered_pairs():
                if math.isinf(pair.distance(start, goal)):
                    unreachable += 1

        assert unreachable > 0

    def test_order_respects_max_order(self):
        assert all(2 <= RandomGraphPair(seed, max_order=5).order <= 5 for seed in SEEDS)

    def test_density_zero_gives_an_edgeless_graph(self):
        pair = RandomGraphPair(3, density=0)

        assert pair.ours.edges == []
        assert pair.theirs.number_of_edges() == 0
        assert pair.order >= 2

    @pytest.mark.parametrize("seed", SEEDS)
    def test_distance_matches_a_direct_networkx_query(self, seed):
        pair = RandomGraphPair(seed)
        for start, goal in pair.ordered_pairs()[:20]:
            try:
                expected = nx.shortest_path_length(
                    pair.theirs, start.key, goal.key, weight="weight"
                )
            except nx.NetworkXNoPath:
                expected = math.inf
            assert pair.distance(start, goal) == pytest.approx(expected) or (
                math.isinf(expected) and math.isinf(pair.distance(start, goal))
            )

    @pytest.mark.parametrize("seed", SEEDS)
    def test_hops_ignores_weight(self, seed):
        pair = RandomGraphPair(seed)
        for start, goal in pair.ordered_pairs()[:20]:
            hops = pair.hops(start, goal)
            if not math.isinf(hops):
                assert hops == int(hops)

    @pytest.mark.parametrize("seed", SEEDS)
    def test_remaining_costs_omits_vertices_that_cannot_reach_the_goal(self, seed):
        pair = RandomGraphPair(seed)
        goal = pair.vertices[0]
        remaining = pair.remaining_costs(goal)

        for vertex in pair.vertices:
            if math.isinf(pair.distance(vertex, goal)) and vertex != goal:
                assert vertex.key not in remaining

    def test_ordered_pairs_omits_self_pairs_and_is_complete(self):
        pair = RandomGraphPair(5)
        pairs = pair.ordered_pairs()

        assert len(pairs) == pair.order * (pair.order - 1)
        assert all(start != goal for start, goal in pairs)

    def test_repr_names_the_seed_and_the_shape(self):
        assert repr(RandomGraphPair(3)) == "RandomGraphPair(seed=3, order=9, size=17)"


class TestOurAlgorithmsOnRandomGraphs:
    """The generator is only useful if the uninformed pair survive it.

    Dijkstra and BFS have no heuristic to get wrong, so a disagreement here
    would be a defect in them or in the generator — and either way has to be
    settled before the A* sweep means anything.
    """

    @pytest.mark.parametrize("seed", SEEDS)
    def test_dijkstra_matches_networkx_on_every_pair(self, seed):
        pair = RandomGraphPair(seed)
        for start, goal in pair.ordered_pairs():
            cost, _ = Dijkstra().find_path(pair.ours, start, goal)
            theirs = pair.distance(start, goal)
            assert cost == pytest.approx(theirs) or (
                math.isinf(cost) and math.isinf(theirs)
            ), f"seed={seed} {start.key}->{goal.key}"

    @pytest.mark.parametrize("seed", SEEDS)
    def test_bfs_matches_unweighted_networkx_on_every_pair(self, seed):
        pair = RandomGraphPair(seed)
        for start, goal in pair.ordered_pairs():
            hops, _ = BFS().find_path(pair.ours, start, goal)
            assert hops == pair.hops(start, goal), (
                f"seed={seed} {start.key}->{goal.key}"
            )


class TestInconsistentHeuristic:
    """Admissible by construction, inconsistent on purpose, and a function."""

    @pytest.mark.parametrize("seed", SEEDS)
    def test_it_is_admissible(self, seed):
        # Everything the sweep concludes rests on this.
        pair = RandomGraphPair(seed)
        for goal in pair.vertices:
            heuristic = InconsistentHeuristic(pair, goal, seed ^ 0xA5)
            assert heuristic.is_admissible(pair), f"seed={seed} goal={goal.key}"

    @pytest.mark.parametrize("seed", SEEDS)
    def test_it_is_a_function_of_the_vertex(self, seed):
        # The bug in the first draft: an estimator calling rng.random() inside
        # the body answers differently every time and is not a heuristic.
        pair = RandomGraphPair(seed)
        goal = pair.vertices[0]
        heuristic = InconsistentHeuristic(pair, goal, seed ^ 0xA5)

        for vertex in pair.vertices:
            first = heuristic(vertex, goal)
            assert all(heuristic(vertex, goal) == first for _ in range(5))

    def test_the_same_seed_gives_the_same_scores(self):
        pair = RandomGraphPair(9)
        goal = pair.vertices[0]

        first = InconsistentHeuristic(pair, goal, 4)
        second = InconsistentHeuristic(pair, goal, 4)

        assert all(
            first(vertex, goal) == second(vertex, goal) for vertex in pair.vertices
        )

    def test_a_large_share_of_cases_are_genuinely_inconsistent(self):
        # Not all of them, and the reason is worth knowing: where the goal is
        # unreachable from most vertices, every score is 0.0 and a
        # zero heuristic is trivially consistent. Measured over seeds 0-19,
        # 120 of 256 goals (47%) give an inconsistent heuristic -- which is
        # what makes the sweep worth running. The floor below is a guard
        # against the generator silently drifting to all-consistent, not a
        # claim about the exact rate.
        inconsistent = 0
        total = 0
        for seed in range(20):
            pair = RandomGraphPair(seed)
            for goal in pair.vertices:
                heuristic = InconsistentHeuristic(pair, goal, seed ^ 0xA5)
                total += 1
                if not heuristic.is_consistent(pair):
                    inconsistent += 1

        assert (total, inconsistent) == (256, 120)
        assert inconsistent / total > 0.3

    @pytest.mark.parametrize("seed", SEEDS)
    def test_over_keys_agrees_with_the_vertex_form(self, seed):
        # NetworkX passes node keys; the two views must score identically or
        # the comparison is between two different heuristics.
        pair = RandomGraphPair(seed)
        goal = pair.vertices[0]
        heuristic = InconsistentHeuristic(pair, goal, seed ^ 0xA5)

        for vertex in pair.vertices:
            assert heuristic.over_keys(vertex.key, goal.key) == pytest.approx(
                heuristic(vertex, goal)
            )

    def test_a_vertex_that_cannot_reach_the_goal_scores_zero(self):
        pair = RandomGraphPair(3, density=0)
        goal = pair.vertices[0]
        heuristic = InconsistentHeuristic(pair, goal, 1)

        assert all(
            heuristic(vertex, goal) == pytest.approx(0.0) for vertex in pair.vertices
        )

    def test_it_raises_for_a_vertex_it_never_scored(self):
        from flight_planner.core import Vertex

        pair = RandomGraphPair(3)
        goal = pair.vertices[0]
        heuristic = InconsistentHeuristic(pair, goal, 1)

        with pytest.raises(KeyError):
            heuristic(Vertex("stranger"), goal)

    def test_repr_names_the_goal_and_the_count(self):
        pair = RandomGraphPair(3)
        goal = pair.vertices[0]

        assert repr(InconsistentHeuristic(pair, goal, 1)) == (
            "InconsistentHeuristic(goal='n0', scored=9)"
        )
