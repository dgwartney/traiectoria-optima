"""Unit tests for `validation.oracle`."""

import math

import networkx as nx
import pytest

from flight_planner.core import Edge, Graph, Vertex
from validation.oracle import NetworkXMirror, NetworkXView


class TestNetworkXMirror:
    """The generic mirror: does it carry the graph across without loss?"""

    def test_order_and_size_match_the_source_graph(self, diamond):
        graph, *_ = diamond
        mirror = NetworkXMirror(graph)

        assert mirror.order == len(graph.vertices)
        assert mirror.size == len(graph.edges)

    def test_parallel_edges_all_survive(self, parallel_edges):
        # The decision the whole document turns on. A DiGraph would report 1.
        graph, _, _ = parallel_edges
        mirror = NetworkXMirror(graph)

        assert len(graph.edges) == 3
        assert mirror.size == 3
        assert isinstance(mirror.graph, nx.MultiDiGraph)

    def test_a_digraph_would_have_collapsed_them(self, parallel_edges):
        # Stated as a test so the reason for MultiDiGraph is executable rather
        # than a comment someone can delete.
        graph, _, _ = parallel_edges
        collapsed = nx.DiGraph()
        for edge in graph.edges:
            collapsed.add_edge(edge.source.key, edge.target.key, weight=edge.weight)

        assert collapsed.number_of_edges() == 1
        assert NetworkXMirror(graph).size == 3

    def test_the_cheapest_parallel_edge_sets_the_distance(self, parallel_edges):
        graph, start, goal = parallel_edges

        assert NetworkXMirror(graph).distance(start.key, goal.key) == pytest.approx(1.0)

    def test_an_empty_graph_mirrors_to_an_empty_graph(self):
        mirror = NetworkXMirror(Graph())

        assert mirror.order == 0
        assert mirror.size == 0

    def test_a_single_vertex_has_no_edges_and_no_distance_to_itself(self):
        graph: Graph[Vertex, Edge] = Graph()
        only = Vertex("A")
        graph.add_vertex(only)
        mirror = NetworkXMirror(graph)

        assert mirror.order == 1
        assert mirror.size == 0
        assert mirror.distance("A", "A") == pytest.approx(0.0)

    def test_an_unreachable_goal_gives_infinity_rather_than_raising(
        self, disconnected
    ):
        graph, inside, outside = disconnected
        mirror = NetworkXMirror(graph)

        assert math.isinf(mirror.distance(inside.key, outside.key))
        assert math.isinf(mirror.hops(inside.key, outside.key))

    def test_an_unknown_key_gives_infinity_rather_than_raising(self, diamond):
        graph, *_ = diamond
        mirror = NetworkXMirror(graph)

        assert math.isinf(mirror.distance("S", "nowhere"))

    def test_a_cycle_and_a_self_loop_do_not_break_it(self, cyclic):
        graph, a, b, c = cyclic
        mirror = NetworkXMirror(graph)

        assert mirror.order == 3
        assert mirror.size == len(graph.edges)
        # A -> B -> C, and the zero-weight parallel B -> C is the cheaper one.
        assert mirror.distance(a.key, c.key) == pytest.approx(1.0)

    def test_hops_ignores_weight(self, diamond):
        graph, start, _, _, goal = diamond
        mirror = NetworkXMirror(graph)

        # Cheapest by distance is three legs; fewest legs is two.
        assert mirror.distance(start.key, goal.key) == pytest.approx(2.5)
        assert mirror.hops(start.key, goal.key) == 2

    def test_vertex_maps_a_node_key_back_to_the_vertex_object(self, diamond):
        graph, start, a, _, _ = diamond
        mirror = NetworkXMirror(graph)

        assert mirror.vertex("S") is start
        assert mirror.vertex("A") is a

    def test_vertex_raises_for_a_key_it_never_saw(self, diamond):
        graph, *_ = diamond

        with pytest.raises(KeyError):
            NetworkXMirror(graph).vertex("nope")

    def test_mirrors_reports_identity_not_equality(self, diamond):
        graph, *_ = diamond
        twin: Graph[Vertex, Edge] = Graph()
        for edge in graph.edges:
            twin.add_edge(edge)
        mirror = NetworkXMirror(graph)

        assert mirror.mirrors(graph)
        assert not mirror.mirrors(twin)

    def test_edge_keys_and_node_attributes_are_carried_when_supplied(self, diamond):
        graph, *_ = diamond
        mirror = NetworkXMirror(
            graph,
            edge_key=lambda edge: f"{edge.source.key}{edge.target.key}",
            node_attributes=lambda vertex: {"label": vertex.key.lower()},
        )

        assert mirror.graph.nodes["S"]["label"] == "s"
        assert "SA" in mirror.graph["S"]["A"]

    def test_a_falsy_edge_key_lets_networkx_assign_one(self, diamond):
        # An empty flight number must not become the string key "", which
        # would make every unnumbered parallel route collapse onto one entry.
        # Passing None instead makes NetworkX assign successive integers.
        graph, *_ = diamond
        mirror = NetworkXMirror(graph, edge_key=lambda edge: "")

        assert list(mirror.graph["S"]["A"]) == [0]

    def test_unkeyed_parallel_edges_stay_distinct(self, parallel_edges):
        graph, start, goal = parallel_edges
        mirror = NetworkXMirror(graph, edge_key=lambda edge: "")

        assert sorted(mirror.graph[start.key][goal.key]) == [0, 1, 2]

    def test_all_distances_agrees_with_the_per_pair_query(self, diamond):
        graph, start, _, _, goal = diamond
        mirror = NetworkXMirror(graph)

        assert mirror.all_distances()[start.key][goal.key] == pytest.approx(
            mirror.distance(start.key, goal.key)
        )

    def test_all_hop_counts_omits_unreachable_pairs(self, disconnected):
        graph, inside, outside = disconnected
        mirror = NetworkXMirror(graph)

        assert outside.key not in mirror.all_hop_counts()[inside.key]

    def test_strongly_connected_components_come_back_largest_first(self, cyclic):
        graph, *_ = cyclic
        components = NetworkXMirror(graph).strongly_connected_components()

        assert [len(component) for component in components] == sorted(
            (len(component) for component in components), reverse=True
        )
        assert len(components[0]) == 3

    def test_path_raises_when_there_is_no_path(self, disconnected):
        graph, inside, outside = disconnected

        with pytest.raises(nx.NetworkXNoPath):
            NetworkXMirror(graph).path(inside.key, outside.key)

    def test_repr_names_the_shape(self, diamond):
        graph, *_ = diamond

        assert repr(NetworkXMirror(graph)) == "NetworkXMirror(order=4, size=4)"


class TestNetworkXView:
    """The flights view: coordinates, flight numbers, and the heuristic."""

    def test_order_and_size_match_the_planner(self, mini_planner):
        view = NetworkXView(mini_planner)

        assert view.order == len(mini_planner.vertices)
        assert view.size == len(mini_planner.edges)

    def test_parallel_routes_are_keyed_by_flight_number(self, mini_planner):
        view = NetworkXView(mini_planner)

        assert sorted(view.graph["SFO"]["DEN"]) == ["UA0001", "WN0002"]

    def test_coordinates_are_carried_as_node_attributes(self, mini_planner):
        view = NetworkXView(mini_planner)

        assert view.graph.nodes["SFO"]["lat"] == pytest.approx(37.6189)
        assert view.graph.nodes["SFO"]["lon"] == pytest.approx(-122.375)
        assert view.graph.nodes["SFO"]["name"] == "San Francisco"

    def test_the_heuristic_takes_iata_codes_not_vertices(self, mini_planner):
        # The bridge this class exists for: NetworkX passes keys.
        view = NetworkXView(mini_planner)
        sfo = mini_planner.iata_lookup["SFO"]
        bos = mini_planner.iata_lookup["BOS"]

        assert view.heuristic("SFO", "BOS") == pytest.approx(sfo.distance_to(bos))

    def test_the_heuristic_is_zero_from_an_airport_to_itself(self, mini_planner):
        assert NetworkXView(mini_planner).heuristic("SFO", "SFO") == pytest.approx(0.0)

    def test_the_heuristic_never_exceeds_the_cheapest_route(self, mini_planner):
        # Admissibility, on the fixture rather than in the abstract.
        view = NetworkXView(mini_planner)
        for origin, destination in view.ordered_pairs():
            estimate = view.heuristic(origin, destination)
            true_cost = view.distance(origin, destination)
            assert estimate <= true_cost + 1e-9, f"{origin}->{destination}"

    def test_astar_and_dijkstra_agree_through_the_view(self, mini_planner):
        view = NetworkXView(mini_planner)
        for origin, destination in view.ordered_pairs():
            if math.isinf(view.distance(origin, destination)):
                continue
            assert view.astar_distance(origin, destination) == pytest.approx(
                view.distance(origin, destination)
            )

    def test_the_cheapest_of_two_parallel_routes_wins(self, mini_planner):
        # SFO->DEN is carried twice, the WN leg 2 km dearer than the UA one.
        view = NetworkXView(mini_planner)
        legs = [
            data["weight"] for data in view.graph["SFO"]["DEN"].values()
        ]

        assert len(legs) == 2
        assert view.distance("SFO", "DEN") == pytest.approx(min(legs))

    def test_ordered_pairs_is_sorted_and_omits_self_pairs(self, mini_planner):
        pairs = NetworkXView(mini_planner).ordered_pairs()

        assert pairs == sorted(pairs)
        assert all(origin != destination for origin, destination in pairs)
        assert len(pairs) == 4 * 3

    def test_ordered_pairs_is_stable_across_views(self, mini_planner):
        # A recorded experiment samples a prefix of this list, so the prefix
        # has to mean the same thing on a later run.
        assert (
            NetworkXView(mini_planner).ordered_pairs()
            == NetworkXView(mini_planner).ordered_pairs()
        )

    def test_reachable_pairs_are_drawn_from_one_component(self, mini_planner):
        # mini_planner is a DAG, so its largest strongly connected component
        # is a single airport and no pair can be drawn.
        with pytest.raises(ValueError, match="two or more airports"):
            NetworkXView(mini_planner).reachable_pairs(5, seed=1)

    def test_reachable_pairs_are_reproducible_from_the_seed(self, mini_planner):
        # Give the planner a cycle so a component exists to draw from.
        from flight_planner.flights import Route

        mini_planner.add_edge(
            Route(
                mini_planner.iata_lookup["BOS"],
                mini_planner.iata_lookup["SFO"],
                5000.0,
                "DL",
                "DL0006",
            )
        )
        view = NetworkXView(mini_planner)

        first = view.reachable_pairs(6, seed=42)
        assert first == view.reachable_pairs(6, seed=42)
        assert first != view.reachable_pairs(6, seed=43)
        assert len(first) == 6
        for origin, destination in first:
            assert not math.isinf(view.distance(origin, destination))

    def test_repr_names_the_shape(self, mini_planner):
        assert repr(NetworkXView(mini_planner)) == "NetworkXView(order=4, size=5)"
