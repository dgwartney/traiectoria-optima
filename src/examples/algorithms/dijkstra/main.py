from dijkstra import dijkstra

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    # Task 1 Graph Example:
    # A graph mapped as a dictionary of dictionaries
    example_graph = {
        "A": {"B": 4, "C": 2},
        "B": {"C": 1, "D": 5},
        "C": {"B": 1, "D": 8, "E": 10},
        "D": {"E": 2},
        "E": {},
    }

    shortest_path, total_cost = dijkstra(example_graph, start="A", target="E")

    print(f"Shortest Path: {shortest_path}")
    print(f"Total Cost: {total_cost}")
