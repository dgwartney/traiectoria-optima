# Copyright (c) Dec 22, 2014 CareerMonk Publications and others.
# E-Mail           		: info@careermonk.com
# Creation Date    		: 2014-01-10 06:15:46
# Last modification		: 2008-10-31
#               by		: Narasimha Karumanchi
# Book Title			: Data Structures And Algorithmic Thinking With Python
# Warranty         		: This software is provided "as is" without any
# 				   warranty; without even the implied warranty of
# 				    merchantability or fitness for a particular purpose.

import math
import collections.abc

class Vertex:
    """
    Represents a vertex in the graph
    """
    def __init__(self, vertex_id: int, label: str ="") -> None:
        self._id: int = vertex_id
        self._adjacent: dict[int, float] = {}
        self._label: str = label

        # Set distance to infinity for all nodes
        self._distance: float = math.inf

        # Mark all nodes unvisited
        self._visited: bool = False

        # Predecessor
        self._previous: Vertex | None = None

    def add_adjacent(self, adjacent_vertex: int, weight: float=0):
        """
        Add an adjacent vertex to this vertex
        """
        self._adjacent[adjacent_vertex] = weight

    def get_adjacent(self):
        """
        Returns the adjacent vertices for this vertex
        """
        return self._adjacent.keys()

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, vertex_id: int):
        self._id = vertex_id

    def get_weight(self, adjacent_vertext: int) -> float:
        return self._adjacent[adjacent_vertext]

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, distance: float):
        self._distance = distance
    @property
    def previous(self):
        return self._previous

    @previous.setter
    def previous(self, previous):
        self._previous = previous

    @property
    def visited(self):
        return self._visited

    @visited.setter
    def visited(self, visited: bool):
        self._visited = visited

    def __str__(self):
        return str(self.id) + ' adjacent: ' + str([x.id for x in self._adjacent])

class Graph:
    def __init__(self):
        self._vertices = {}
        self._numVertices:int = 0

    def __iter__(self) -> collections.abc.Iterator[Vertex]:
        return iter(self._vertices.values())

    def add_vertex(self, node) -> Vertex:
        vertex = Vertex(node)
        self._vertices[node] = vertex
        self._numVertices += 1
        return vertex

    def __setitem__(self, node, _value) -> None:
        self.add_vertex(node)

    def __len__(self):
        return len(self._vertices)

    def __getitem__(self, node) -> Vertex | None:
        return self._vertices.get(node)

    def add_edge(self, frm, to, cost=0):
        if frm not in self._vertices:
            self.add_vertex(frm)
        if to not in self._vertices:
            self.add_vertex(to)

        self._vertices[frm].add_adjacent(self._vertices[to], cost)
        # For directed graph do not add this
        self._vertices[to].add_adjacent(self._vertices[frm], cost)

    def get_vertices(self):
        return self._vertices.keys()

    def setPrevious(self, current):
        self.previous = current

    def getPrevious(self, current):
        return self.previous

    def getEdges(self):
        edges = []
        for v in self:
            for w in v.get_adjacent():
                edges.append((v.id, w.id, v.get_weight(w)))
        return edges

if __name__ == '__main__':

    G = Graph()
    G['a'] = 'a'
    G.add_vertex('b')
    G.add_vertex('c')
    G.add_vertex('d')
    G.add_vertex('e')
    G.add_edge('a', 'b', 4)
    G.add_edge('a', 'c', 1)
    G.add_edge('c', 'b', 2)
    G.add_edge('b', 'e', 4)
    G.add_edge('c', 'd', 4)
    G.add_edge('d', 'e', 4)

    print('Graph data:')
    print(G.getEdges())
