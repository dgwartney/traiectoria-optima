import heapq


def dijkstra(graph, start, target):
    # --- TASK 1: Define the Graph Structure ---
    # (Passed into the function as a dictionary adjacency list: {node: {neighbor: weight}})

    # --- TASK 2: Initialize State Trackers ---
    # Initialize all distances to infinity
    distances = {node: float("inf") for node in graph}
    distances[start] = 0  # Start node distance is 0

    # Track parent pointers to reconstruct the path later
    parents = {node: None for node in graph}

    # Set to keep track of fully processed nodes
    visited = set()

    # --- TASK 3: Initialize the Priority Queue ---
    # Heap stores tuples: (distance, vertex)
    priority_queue = [(0, start)]

    # --- TASK 4: Implement the Main Processing Loop ---
    while priority_queue:
        # Extract the node with the minimum distance
        current_distance, current_node = heapq.heappop(priority_queue)

        # Skip the node if it has already been processed
        if current_node in visited:
            continue

        # Mark node as visited once we extract it
        visited.add(current_node)

        # Early exit if we reached our destination
        if current_node == target:
            break

        # --- TASK 5: Implement Edge Relaxation ---
        for neighbor, weight in graph[current_node].items():
            if neighbor in visited:
                continue

            # Calculate total distance to neighbor through current node
            new_distance = current_distance + weight

            # Update if the new path is shorter
            if new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                parents[neighbor] = current_node
                # Push the updated distance to the priority queue
                heapq.heappush(priority_queue, (new_distance, neighbor))

    # --- TASK 6: Reconstruct the Shortest Path ---
    path = []
    current = target

    # Check if a path actually exists
    if distances[target] == float("inf"):
        return None, float("inf")

    # Backtrack through parent pointers
    while current is not None:
        path.append(current)
        current = parents[current]

    # Reverse the sequence to get start-to-finish order
    path.reverse()

    return path, distances[target]


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
