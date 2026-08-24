"""Example of Dijkstra's algorithm."""

import heapq
from collections import defaultdict
from typing import Dict, List


class Solution(object):
    """Solution to Dijkstra's algorithm."""

    @staticmethod
    def shortest_path(number_of_vertices: int, edges: List[List[int]], source_vertex: int) -> Dict[int, int]:
        """Args:
            n:
            edges:
            source_vertext:

        Returns: Dict[int, int]

        """  # noqa: D205, D415
        adj: Dict[int, List[List[int]]] = defaultdict(list)
        for i in range(number_of_vertices):
            adj[i] = []

        for vertex, distance, weight in edges:
            adj[vertex].append([distance, weight])

        shortest = {}  # Map vertex -> distance of shortest path
        min_heap = [[0, source_vertex]]
        while min_heap:
            w1, n1 = heapq.heappop(min_heap)
            if n1 in shortest:
                continue
            shortest[n1] = w1

            for n2, w2 in adj[n1]:
                if n2 not in shortest:
                    heapq.heappush(min_heap, [w1 + w2, n2])

        for i in range(n):
            if i not in shortest:
                shortest[i] = -1

        return shortest

edges: List[List[int]] = [
    [1, 10]
]

