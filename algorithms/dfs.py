"""
Smart Flood Rescue System - Depth-First Search (DFS) Module
===========================================================

Manual implementation of Depth-First Search (DFS) for disaster road network
branch analysis, isolated road segment detection, and corridor verification.

Data Structure:
- ManualStack: Pure manual Last-In, First-Out (LIFO) stack operating without
  external libraries.

Time Complexity:  O(V + E)
Space Complexity: O(V)
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from algorithms.dijkstra import AdjacencyListGraph


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
        """Returns True if the stack has no items."""
        return len(self._items) == 0

    def peek(self) -> Optional[Any]:
        """Returns the topmost item without removing it."""
        if self.is_empty():
            return None
        return self._items[-1]

    def __len__(self) -> int:
        return len(self._items)


def dfs_traversal(
    graph: AdjacencyListGraph,
    start_node: str,
    target_node: Optional[str] = None,
    collect_trace: bool = False
) -> Dict[str, Any]:
    """
    Performs Depth-First Search (DFS) using an explicit LIFO stack.

    Practical Application in Flood Rescue:
        - Deep corridor reachability analysis: Determines if a path exists between
          an isolated village or zone and a major arterial road.
        - Topological loop and detour inspection.

    Args:
        graph: AdjacencyListGraph representing the road/shelter network.
        start_node: Origin vertex ID.
        target_node: Optional destination vertex ID. If reached, traversal stops early.
        collect_trace: If True, records chronological exploration steps for UI display.

    Returns:
        {
            "success": bool,
            "start_node": str,
            "target_node": Optional[str],
            "target_found": bool,
            "visited_order": List[str],        # Order in which nodes were popped and processed
            "reachable_nodes": List[str],      # All discovered nodes in this connected component
            "parent_map": Dict[str, str],      # DFS spanning forest predecessors
            "path_to_target": Optional[List[str]], # Reconstructed path if target was specified and found
            "trace": List[Dict[str, Any]]
        }
    """
    start = str(start_node)
    target = str(target_node) if target_node is not None else None

    if start not in graph.nodes:
        raise KeyError(f"Start node '{start}' does not exist in graph.")
    if target is not None and target not in graph.nodes:
        return {
            "success": False,
            "start_node": start,
            "target_node": target,
            "target_found": False,
            "visited_order": [],
            "reachable_nodes": [],
            "parent_map": {},
            "path_to_target": None,
            "trace": [{"action": f"Target node '{target}' does not exist in graph."}]
        }

    visited: Set[str] = set()
    stack = ManualStack()
    stack.push(start)

    visited_order: List[str] = []
    parent_map: Dict[str, Optional[str]] = {start: None}
    trace: List[Dict[str, Any]] = []
    target_found = False

    step = 0
    if collect_trace:
        trace.append({
            "step": step,
            "current_node": start,
            "stack_size": len(stack),
            "action": f"Pushed origin node '{start}' onto DFS stack."
        })

    while not stack.is_empty():
        curr = stack.pop()

        if curr in visited:
            continue

        visited.add(curr)
        visited_order.append(curr)

        step += 1
        if collect_trace:
            trace.append({
                "step": step,
                "current_node": curr,
                "stack_size": len(stack),
                "action": f"Popped and visited node '{curr}'."
            })

        if target is not None and curr == target:
            target_found = True
            break

        # Push neighbors onto stack (reverse order preserves natural left-to-right branch order)
        neighbors = graph.neighbors(curr)
        for edge in reversed(neighbors):
            neighbor = edge["to"]
            if neighbor not in visited:
                if neighbor not in parent_map:
                    parent_map[neighbor] = curr
                stack.push(neighbor)

    # Reconstruct path to target if target requested and reached
    path_to_target: Optional[List[str]] = None
    if target_found and target is not None:
        path: List[str] = []
        curr_back: Optional[str] = target
        while curr_back is not None:
            path.append(curr_back)
            curr_back = parent_map.get(curr_back)
        path.reverse()
        path_to_target = path

    return {
        "success": True,
        "start_node": start,
        "target_node": target,
        "target_found": target_found,
        "visited_order": visited_order,
        "reachable_nodes": list(visited),
        "parent_map": parent_map,
        "path_to_target": path_to_target,
        "trace": trace
    }


def find_connected_components(graph: AdjacencyListGraph) -> List[List[str]]:
    """
    Finds all isolated connected components in the graph using DFS.
    
    In a major flood disaster, arterial bridges and underpasses may wash away,
    partitioning the city into isolated geographic 'islands'. This function identifies
    all disconnected sub-graphs so rescue helicopters and boats can be dispatched.
    
    Returns:
        List of node lists, each representing a distinct connected component.
    """
    visited: Set[str] = set()
    components: List[List[str]] = []

    for node in sorted(graph.nodes.keys()):
        if node not in visited:
            res = dfs_traversal(graph, start_node=node, target_node=None, collect_trace=False)
            component = res["reachable_nodes"]
            for n in component:
                visited.add(n)
            components.append(component)

    return components
