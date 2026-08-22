import math

class Node():

    __slots__ = ["airport_id"]


    def __init__(self, airport_id)-> None:
        self.airport_id



class Edge():

    __slots__ = ["dist", "src", "dest"]

    def __init__(self, src: GraphNode, dest: GraphNode, dist: float = math.inf)-> None:
        self.dist = dist
        self.src = src
        self.dest = dest


a1 = Node("SFO");
a2 = Node("LAX");

e1 = Edge(a1, a2)


class GraphBuilder()


    @static
    def build(filePath: Path):

