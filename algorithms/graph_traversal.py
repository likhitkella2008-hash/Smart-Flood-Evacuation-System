"""
Smart Flood Rescue System - Graph Traversals (BFS & DFS) Implementation
=======================================================================

Manual implementations of Breadth-First Search (BFS) and Depth-First Search (DFS)
for disaster road network analysis, reachability assessment, and flood wave propagation.

Data Structures Implemented:
- ManualQueue: Pure manual First-In, First-Out (FIFO) queue for level-by-level exploration.
- ManualStack: Pure manual Last-In, First-Out (LIFO) stack for deep branch exploration.
- Visited Set: Hash set ensuring O(1) membership testing and preventing infinite loops in cyclic road networks.

Time Complexity:  O(V + E)
Space Complexity: O(V)
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from algorithms.dijkstra import AdjacencyListGraph


class ManualQueue:
    """
    Pure manual First-In, First-Out (FIFO) queue implementation.
    Operates without collections.deque or external queue libraries.
    """

    def __init__(self):
        self._items: List[Any] = []
        self._head: int = 0

    def enqueue(self, item: Any) -> None:
        """Appends an element to the back of the queue in O(1)."""
        self._items.append(item)

    def dequeue(self) -> Any:
        """Removes and returns the front element from the queue in O(1) amortized."""
        if self.is_empty():
            raise IndexError("dequeue from an empty ManualQueue")
        item = self._items[self._head]
        self._head += 1
        # Amortized list compaction to reclaim unused head space
        if self._head > 500 and self._head > len(self._items) // 2:
            self._items = self._items[self._head:]
            self._head = 0
        return item

    def is_empty(self) -> bool:
        """Returns True if the queue has no elements pending."""
        return self._head >= len(self._items)

    def __len__(self) -> int:
        return len(self._items) - self._head


class ManualStack:
    """
    Pure manual Last-In, First-Out (LIFO) stack implementation.
    """

    def __init__(self):
        self._items: List[Any] = []

    def push(self, item: Any) -> None:
        """Pushes an element onto the top of the stack in O(1)."""
        self._items.append(item)

    def pop(self) -> Any:
        """Pops and returns the topmost element from the stack in O(1)."""
        if self.is_empty():
            raise IndexError("pop from an empty ManualStack")
        return self._items.pop()

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def peek(self) -> Optional[Any]:
        if self.is_empty():
            return None
        return self._items[-1]

    def __len__(self) -> int:
        return len(self._items)


def bfs_traversal(
    graph: AdjacencyListGraph,
    start_node: str,
    max_hops: Optional[int] = None,
    collect_trace: bool = False
) -> Dict[str, Any]:
    """
    Performs level-order Breadth-First Search from a specified origin node.

    Practical Application in Flood Rescue:
        - "Flood Evacuation Wave": Identifies all road junctions, relief centers,
          and shelters reachable within `max_hops` network segments.
        - Unweighted shortest hop distance calculation.

    Args:
        graph: AdjacencyListGraph representing the road/shelter network.
        start_node: Origin vertex ID.
        max_hops: Optional maximum number of road segments to explore outward.
        collect_trace: If True, records chronological exploration steps for UI display.

    Returns:
        {
            "success": bool,
            "start_node": str,
            "visited_order": List[str],        # Order in which nodes were discovered
            "hop_distances": Dict[str, int],   # Minimum number of hops from start
            "reachable_nodes": List[str],      # All connected vertices
            "parent_map": Dict[str, str],      # BFS spanning tree predecessors
            "trace": List[Dict[str, Any]]
        }
    """
    start = str(start_node)
    if start not in graph.nodes:
        raise KeyError(f"Start node '{start}' does not exist in graph.")

    visited: Set[str] = {start}
    queue = ManualQueue()
    queue.enqueue((start, 0))  # (node_id, hop_level)

    visited_order: List[str] = [start]
    hop_distances: Dict[str, int] = {start: 0}
    parent_map: Dict[str, Optional[str]] = {start: None}
    trace: List[Dict[str, Any]] = []

    step = 0
    if collect_trace:
        trace.append({
            "step": step,
            "current_node": start,
            "hop_level": 0,
            "action": f"Initialized BFS queue at origin node '{start}'."
        })

    while not queue.is_empty():
        curr, hops = queue.dequeue()

        if max_hops is not None and hops >= max_hops:
            continue

        for edge in graph.neighbors(curr):
            neighbor = edge["to"]
            if neighbor not in visited:
                visited.add(neighbor)
                visited_order.append(neighbor)
                hop_distances[neighbor] = hops + 1
                parent_map[neighbor] = curr
                queue.enqueue((neighbor, hops + 1))

                step += 1
                if collect_trace:
                    trace.append({
                        "step": step,
                        "current_node": neighbor,
                        "hop_level": hops + 1,
                        "parent": curr,
                        "action": f"Discovered node '{neighbor}' via edge from '{curr}' at hop {hops + 1}."
                    })

    return {
        "success": True,
        "start_node": start,
        "visited_order": visited_order,
        "hop_distances": hop_distances,
        "reachable_nodes": list(visited),
        "parent_map": parent_map,
        "trace": trace
    }


def dfs_traversal(
    graph: AdjacencyListGraph,
    start_node: str,
    target_node: Optional[str] = None,
    collect_trace: bool = False
) -> Dict[str, Any]:
    """
    Performs iterative Depth-First Search using an explicit manual LIFO stack.

    Practical Application in Flood Rescue:
        - "Deep Corridor Exploration": Explores alternative evacuation corridors
          deep into highland safe zones.
        - Cycle detection and connected component exploration.

    Args:
        graph: AdjacencyListGraph representing the road network.
        start_node: Origin vertex ID.
        target_node: Optional destination to stop exploration early when reached.
        collect_trace: If True, records exploration decisions.

    Returns:
        {
            "success": bool,
            "start_node": str,
            "target_node": Optional[str],
            "visited_order": List[str],
            "reachable_nodes": List[str],
            "target_found": bool,
            "path_to_target": Optional[List[str]],
            "trace": List[Dict[str, Any]]
        }
    """
    start = str(start_node)
    if start not in graph.nodes:
        raise KeyError(f"Start node '{start}' does not exist in graph.")

    target = str(target_node) if target_node else None
    if target and target not in graph.nodes:
        raise KeyError(f"Target node '{target}' does not exist in graph.")

    visited: Set[str] = set()
    stack = ManualStack()
    stack.push((start, [start]))  # (node_id, path_so_far)
    visited_order: List[str] = []
    path_to_target: Optional[List[str]] = None
    target_found = False
    trace: List[Dict[str, Any]] = []
    step = 0

    while not stack.is_empty():
        curr, path = stack.pop()

        if curr not in visited:
            visited.add(curr)
            visited_order.append(curr)

            step += 1
            if collect_trace:
                trace.append({
                    "step": step,
                    "current_node": curr,
                    "depth": len(path) - 1,
                    "action": f"Visited node '{curr}' (Depth {len(path) - 1})."
                })

            if target and curr == target:
                target_found = True
                path_to_target = list(path)
                if collect_trace:
                    trace.append({
                        "step": step + 1,
                        "action": f"Destination node '{target}' reached by DFS path."
                    })
                break

            # Add unvisited neighbors to stack (reverse for intuitive exploration order)
            for edge in reversed(graph.neighbors(curr)):
                neighbor = edge["to"]
                if neighbor not in visited:
                    stack.push((neighbor, path + [neighbor]))

    return {
        "success": True,
        "start_node": start,
        "target_node": target,
        "visited_order": visited_order,
        "reachable_nodes": list(visited),
        "target_found": target_found,
        "path_to_target": path_to_target,
        "trace": trace
    }


def find_connected_components(graph: AdjacencyListGraph) -> List[List[str]]:
    """
    Identifies all disconnected road components in the graph (e.g. isolated flood islands).
    Uses BFS iteratively across all unvisited vertices.
    """
    visited: Set[str] = set()
    components: List[List[str]] = []

    for node in graph.nodes:
        if node not in visited:
            # Run BFS from this unvisited node
            bfs_res = bfs_traversal(graph, node)
            comp = bfs_res["reachable_nodes"]
            for c_node in comp:
                visited.add(c_node)
            components.append(comp)

    return components
