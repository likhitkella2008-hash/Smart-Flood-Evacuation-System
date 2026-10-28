"""
Smart Flood Rescue System - Breadth-First Search (BFS) Module
=============================================================

Manual implementation of Breadth-First Search (BFS) for disaster road network
reachability assessment, flood wave propagation, and evacuation zone analysis.

Data Structure:
- ManualQueue: Pure manual First-In, First-Out (FIFO) queue operating without
  collections.deque or external libraries.

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

    def peek(self) -> Optional[Any]:
        """Returns the item at the front of the queue without removing it."""
        if self.is_empty():
            return None
        return self._items[self._head]

    def __len__(self) -> int:
        return len(self._items) - self._head


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
            "queue_size": len(queue),
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
                        "current_node": curr,
                        "discovered_neighbor": neighbor,
                        "hop_level": hops + 1,
                        "queue_size": len(queue),
                        "action": f"Discovered node '{neighbor}' from '{curr}' at hop {hops + 1}."
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
