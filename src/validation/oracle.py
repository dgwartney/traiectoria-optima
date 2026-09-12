"""The same graph, as NetworkX sees it, and the questions it can answer.

Two classes, because there are two jobs. `NetworkXMirror` converts any
`Graph[V, E]` — it knows about `vertex.key` and `edge.weight` and nothing
else, which keeps the reference engines in `engines.py` usable against a
four-vertex test fixture. `NetworkXView` composes a mirror with a
`FlightPlanner` to add what only the flights layer has: airport coordinates,
flight numbers, and a great-circle heuristic in the signature NetworkX's A*
expects.

Composition rather than inheritance, following the package it validates:
`NetworkXView` *has* a mirror and *has* a planner. Nothing about a flight
network is a special case of a generic mirror — it simply knows more.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Dict, Generic, List, Optional, Tuple, TypeVar

import networkx as nx

from flight_planner.core.edge import Edge
from flight_planner.core.graph import Graph
from flight_planner.core.vertex import Vertex
from flight_planner.flights.planner import FlightPlanner
from flight_planner.geo.formula import DistanceFormula
from flight_planner.geo.haversine import Haversine
from flight_planner.geo.memoized import Memoized

V = TypeVar("V", bound=Vertex)
E = TypeVar("E", bound=Edge)


class NetworkXMirror(Generic[V, E]):
    """A `Graph[V, E]` mirrored into NetworkX, losing nothing.

    A `MultiDiGraph`, not a `DiGraph`, and that is not a style preference: the
    project's data carries up to 20 parallel routes between one airport pair,
    and a `DiGraph` keeps only the last edge added between any two nodes. On
    the world snapshot that silently discards 29,615 of 66,332 routes, after
    which every parity test passes while comparing a graph nobody built.
    `size` against `len(graph.edges)` is the assertion that catches it.

    Nodes are `vertex.key`, so the mirror assumes keys are unique and
    hashable — which `Graph` already requires, since it indexes vertices by
    identity.

    Attributes:
        graph: The `nx.MultiDiGraph` mirror.
    """

    def __init__(
        self,
        graph: Graph[V, E],
        edge_key: Optional[Callable[[E], object]] = None,
        node_attributes: Optional[Callable[[V], Dict[str, object]]] = None,
    ) -> None:
        """Mirror a graph.

        Args:
            graph: Graph to mirror. Read once, so a graph mutated afterwards
                leaves the mirror stale; the reference engines guard against
                that by identity.
            edge_key: Optional callable naming each edge, used as the
                `MultiDiGraph` key. Parallel edges are preserved either way;
                a key only makes them addressable. Falsy results become
                `None`, since NetworkX then assigns an integer.
            node_attributes: Optional callable returning attributes to attach
                to each node.
        """
        self._source_graph = graph
        self._vertices: Dict[object, V] = {
            vertex.key: vertex for vertex in graph.vertices
        }
        self.graph = self._build(graph, edge_key, node_attributes)

    @staticmethod
    def _build(
        graph: Graph[V, E],
        edge_key: Optional[Callable[[E], object]],
        node_attributes: Optional[Callable[[V], Dict[str, object]]],
    ) -> nx.MultiDiGraph:
        mirror = nx.MultiDiGraph()
        for vertex in graph.vertices:
            attributes = node_attributes(vertex) if node_attributes else {}
            mirror.add_node(vertex.key, **attributes)
        for edge in graph.edges:
            key = edge_key(edge) if edge_key else None
            mirror.add_edge(
                edge.source.key,
                edge.target.key,
                key=key or None,
                weight=edge.weight,
            )
        return mirror

    @property
    def order(self) -> int:
        """Return the node count.

        Returns:
            Number of nodes, which must equal `len(graph.vertices)`.
        """
        return self.graph.number_of_nodes()

    @property
    def size(self) -> int:
        """Return the edge count, parallel edges included.

        Returns:
            Number of edges, which must equal `len(graph.edges)`. A collapsed
            mirror shows up here and nowhere else.
        """
        return self.graph.number_of_edges()

    def vertex(self, key: object) -> V:
        """Return the vertex a node key came from.

        The bridge that makes NetworkX results expressible in our own types,
        and the reason this is a class: NetworkX answers in keys, every
        caller needs vertices, and the mapping should exist once.

        Args:
            key: Node key, as it appears in `graph`.

        Returns:
            The originating vertex.

        Raises:
            KeyError: If the key is not in the mirrored graph.
        """
        return self._vertices[key]

    def mirrors(self, graph: Graph[V, E]) -> bool:
        """Report whether this mirror was built from `graph`.

        Identity, not equality: a mirror of a mutated graph is stale, and the
        reference engines cache one per graph.

        Args:
            graph: Graph to compare against.

        Returns:
            `True` if `graph` is the graph this mirror was built from.
        """
        return graph is self._source_graph

    def distance(self, origin: object, destination: object) -> float:
        """Return the weighted shortest-path length — Dijkstra's question.

        Args:
            origin: Node key to start from.
            destination: Node key to reach.

        Returns:
            Total weight of the cheapest path, or `inf` if none exists. An
            origin equal to the destination gives `0.0`, matching
            `PathfindingAlgorithm`'s contract.
        """
        try:
            return nx.shortest_path_length(
                self.graph, origin, destination, weight="weight"
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return math.inf

    def hops(self, origin: object, destination: object) -> float:
        """Return the unweighted shortest-path length — BFS's question.

        Args:
            origin: Node key to start from.
            destination: Node key to reach.

        Returns:
            Number of edges in the shortest path, or `inf` if none exists.
        """
        try:
            return float(nx.shortest_path_length(self.graph, origin, destination))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return math.inf

    def astar_distance(
        self, origin: object, destination: object, heuristic: Callable
    ) -> float:
        """Return NetworkX's A* length under a heuristic.

        NetworkX's A* *reopens* nodes — it compares an entry's queued cost
        rather than skipping closed nodes outright — so it stays optimal for
        any admissible heuristic. That makes it a legitimate oracle for the
        inconsistent-heuristic case, which `flight_planner.AStar` gets wrong.

        Args:
            origin: Node key to start from.
            destination: Node key to reach.
            heuristic: Callable over *node keys*, not vertices.

        Returns:
            Total weight of the path A* found, or `inf` if none exists.
        """
        try:
            return nx.astar_path_length(
                self.graph,
                origin,
                destination,
                heuristic=heuristic,
                weight="weight",
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return math.inf

    def path(self, origin: object, destination: object) -> List[object]:
        """Return the node sequence of a weighted shortest path.

        Args:
            origin: Node key to start from.
            destination: Node key to reach.

        Returns:
            Node keys in order, starting with `origin`.

        Raises:
            networkx.NetworkXNoPath: If no path exists.
            networkx.NodeNotFound: If a key is not in the graph.
        """
        return nx.shortest_path(self.graph, origin, destination, weight="weight")

    def hop_path(self, origin: object, destination: object) -> List[object]:
        """Return the node sequence of an unweighted shortest path.

        Args:
            origin: Node key to start from.
            destination: Node key to reach.

        Returns:
            Node keys in order, starting with `origin`.

        Raises:
            networkx.NetworkXNoPath: If no path exists.
            networkx.NodeNotFound: If a key is not in the graph.
        """
        return nx.shortest_path(self.graph, origin, destination)

    def all_distances(self) -> Dict[object, Dict[object, float]]:
        """Return every weighted shortest-path length, keyed origin then goal.

        One all-pairs sweep, because a per-pair query over thousands of pairs
        rebuilds the same search tree thousands of times.

        Returns:
            Nested mapping; a missing inner key means unreachable.
        """
        return dict(nx.all_pairs_dijkstra_path_length(self.graph, weight="weight"))

    def all_hop_counts(self) -> Dict[object, Dict[object, int]]:
        """Return every unweighted shortest-path length.

        Returns:
            Nested mapping; a missing inner key means unreachable.
        """
        return dict(nx.all_pairs_shortest_path_length(self.graph))

    def strongly_connected_components(self) -> List[frozenset]:
        """Return the strongly connected components, largest first.

        Structure `flight_planner` has no vocabulary for, and the honest way
        to pick a benchmark query set: a pair drawn from one component is
        reachable by construction.

        Returns:
            Components as frozensets of node keys, in descending size order.
        """
        components = nx.strongly_connected_components(self.graph)
        return sorted(
            (frozenset(component) for component in components),
            key=len,
            reverse=True,
        )

    def __repr__(self) -> str:
        """Return a debugging representation.

        Returns:
            String of the form `NetworkXMirror(order=94, size=7005)`.
        """
        return f"{type(self).__name__}(order={self.order}, size={self.size})"


class NetworkXView:
    """A `FlightPlanner` mirrored into NetworkX, with the flights extras.

    Composes a `NetworkXMirror` and adds the three things only this layer
    has: airport coordinates as node attributes, flight numbers as edge keys,
    and `heuristic`, which is the great-circle distance in the signature
    NetworkX's `astar_path_length` expects.

    That last one is the reason this is a class rather than a conversion
    function. NetworkX hands a heuristic *node keys* where `flight_planner`
    hands it *vertices*, so every A* comparison needs the planner's
    `iata_lookup` — and a bare function would leave each caller re-deriving
    it. Here it exists once.

    Attributes:
        mirror: The underlying `NetworkXMirror`.
        graph: The `nx.MultiDiGraph`, for direct NetworkX calls.
    """

    def __init__(
        self, planner: FlightPlanner, formula: Optional[DistanceFormula] = None
    ) -> None:
        """Mirror a planner.

        Args:
            planner: Flight network to mirror. Read once; a planner mutated
                afterwards leaves the view stale.
            formula: Distance formula for `heuristic`, memoized `Haversine`
                by default since the oracle asks about the same airport pairs
                repeatedly.
        """
        self._planner = planner
        self._lookup = planner.iata_lookup
        self._formula = formula if formula is not None else Memoized(Haversine())
        self.mirror: NetworkXMirror = NetworkXMirror(
            planner,
            edge_key=lambda route: route.flight_number,
            node_attributes=lambda airport: {
                "lat": airport.latitude,
                "lon": airport.longitude,
                "name": airport.name,
            },
        )
        self.graph = self.mirror.graph

    @property
    def order(self) -> int:
        """Return the airport count."""
        return self.mirror.order

    @property
    def size(self) -> int:
        """Return the route count, parallel routes included."""
        return self.mirror.size

    def heuristic(self, origin_code: str, destination_code: str) -> float:
        """Return the great-circle distance between two IATA codes.

        Args:
            origin_code: IATA code of the node being scored.
            destination_code: IATA code of the goal.

        Returns:
            Great-circle distance in kilometres. Admissible as long as no
            route is shorter than the great circle it flies, which is the
            argument the report has to make.
        """
        return self._lookup[origin_code].distance_to(
            self._lookup[destination_code], formula=self._formula
        )

    def distance(self, origin: str, destination: str) -> float:
        """Return NetworkX's shortest flying distance in kilometres."""
        return self.mirror.distance(origin, destination)

    def hops(self, origin: str, destination: str) -> float:
        """Return NetworkX's fewest number of legs."""
        return self.mirror.hops(origin, destination)

    def astar_distance(self, origin: str, destination: str) -> float:
        """Return NetworkX's A* distance under the great-circle heuristic."""
        return self.mirror.astar_distance(origin, destination, self.heuristic)

    def path(self, origin: str, destination: str) -> List[object]:
        """Return the IATA codes of a shortest-distance route."""
        return self.mirror.path(origin, destination)

    def all_distances(self) -> Dict[object, Dict[object, float]]:
        """Return every shortest flying distance, keyed origin then goal."""
        return self.mirror.all_distances()

    def all_hop_counts(self) -> Dict[object, Dict[object, int]]:
        """Return every fewest-legs count, keyed origin then goal."""
        return self.mirror.all_hop_counts()

    def ordered_pairs(self) -> List[Tuple[str, str]]:
        """Return every ordered pair of distinct airports, sorted.

        Sorted so a sampled prefix is the same set on every run, which a
        recorded experiment needs and a random sample would not give.

        Returns:
            `(origin, destination)` IATA-code pairs, origin-major.
        """
        codes = sorted(airport.iata_code for airport in self._planner.vertices)
        return [
            (origin, destination)
            for origin in codes
            for destination in codes
            if origin != destination
        ]

    def reachable_pairs(self, count: int, seed: int) -> List[Tuple[str, str]]:
        """Return pairs drawn from the largest strongly connected component.

        Every pair is reachable by construction, so a benchmark over them
        measures search rather than the cost of discovering "no route".

        Args:
            count: How many pairs to return.
            seed: Seed for the draw, so a recorded run is reproducible.

        Returns:
            `count` ordered pairs of distinct, mutually reachable airports.

        Raises:
            ValueError: If the largest component has fewer than two airports.
        """
        components = self.mirror.strongly_connected_components()
        largest = sorted(components[0]) if components else []
        if len(largest) < 2:
            raise ValueError(
                "no strongly connected component with two or more airports"
            )

        rng = random.Random(seed)
        pairs: List[Tuple[str, str]] = []
        while len(pairs) < count:
            origin, destination = rng.choice(largest), rng.choice(largest)
            if origin != destination:
                pairs.append((str(origin), str(destination)))
        return pairs

    def __repr__(self) -> str:
        """Return a debugging representation.

        Returns:
            String of the form `NetworkXView(order=94, size=7005)`.
        """
        return f"NetworkXView(order={self.order}, size={self.size})"
