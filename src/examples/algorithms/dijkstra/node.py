class Node:
    """Represents a single vertex in the graph."""

    def __init__(self, name: str):
        self.name: str = name
        # Maps neighboring Node objects to the edge weight (cost)
        self.neighbors: Dict[Node, float] = {}

    def add_neighbor(self, neighbor: "Node", weight: float) -> None:
        """Adds a directed edge from this node to another with a weight."""
        self.neighbors[neighbor] = weight

    def __str__(self) -> str:
        return self.name

    # These dunder methods allow the Node to be used cleanly in sets/dicts
    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.name == other.name
