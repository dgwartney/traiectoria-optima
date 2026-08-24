class Graph:
    """Represents the network structure containing all nodes."""

    def __init__(self):
        # Maps string names to actual Node objects
        self.nodes: Dict[str, Node] = {}

    def get_or_create_node(self, name: str) -> Node:
        """Retrieves an existing node or creates a new one if it doesn't exist."""
        if name not in self.nodes:
            self.nodes[name] = Node(name)
        return self.nodes[name]

    def add_edge(self, from_node_name: str, to_node_name: str, weight: float) -> None:
        """Connects two nodes together with a weighted edge."""
        from_node = self.get_or_create_node(from_node_name)
        to_node = self.get_or_create_node(to_node_name)
        from_node.add_neighbor(to_node, weight)

    def get_all_nodes(self) -> List[Node]:
        """Returns a list of all Node objects in the graph."""
        return list(self.nodes.values())
