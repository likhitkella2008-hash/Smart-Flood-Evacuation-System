"""
Smart Flood Rescue System - Dijkstra Shortest Path Implementation
==================================================================

Manual Dijkstra Algorithm implementation using an adjacency list graph
and a manual Binary Min-Heap priority queue (no external graph libraries).

Mathematical Invariant:
----------------------
Maintains tentative distances d[v] for all vertices v.
At each step, extracts vertex u with minimum d[u], and relaxes all outgoing edges (u, v):
    if d[u] + weight(u, v) < d[v]:
        d[v] = d[u] + weight(u, v)
        prev[v] = u

Precondition:
-------------
All edge weights must be strictly non-negative (weight >= 0).
Raises ValueError if negative weights are detected.
"""

from typing import Any, Dict, List, Optional, Set, Tuple


class AdjacencyListGraph:
    """
    Graph data structure represented as an adjacency list.
    Supports directed and undirected edges with arbitrary attributes (weight, hazards, etc.).
    """

    def __init__(self, directed: bool = False):
        self.directed = directed
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.adj: Dict[str, List[Dict[str, Any]]] = {}

    def add_node(self, node_id: str, **attrs: Any) -> None:
        """Adds a vertex to the graph with optional attributes (e.g. lat, lon, name)."""
        node_id = str(node_id)
        if node_id not in self.nodes:
            self.nodes[node_id] = attrs
            self.adj[node_id] = []
        else:
            self.nodes[node_id].update(attrs)

    def add_edge(
        self,
        u: str,
        v: str,
        weight: float,
        base_distance: Optional[float] = None,
        hazard_note: Optional[str] = None,
        **attrs: Any
    ) -> None:
        """
        Adds an edge between nodes u and v.
        Validates that weight >= 0.
        """
        if weight < 0:
            raise ValueError(f"Dijkstra requires non-negative edge weights; got {weight} for edge ({u}, {v})")

        u = str(u)
        v = str(v)

        if u not in self.nodes:
            self.add_node(u)
        if v not in self.nodes:
            self.add_node(v)

        edge_data = {
            "to": v,
            "weight": float(weight),
            "base_distance": float(base_distance if base_distance is not None else weight),
            "hazard_note": hazard_note,
            **attrs
        }
        self.adj[u].append(edge_data)

        if not self.directed:
            reverse_edge = {
                "to": u,
                "weight": float(weight),
                "base_distance": float(base_distance if base_distance is not None else weight),
                "hazard_note": hazard_note,
                **attrs
            }
            self.adj[v].append(reverse_edge)

    def neighbors(self, u: str) -> List[Dict[str, Any]]:
        """Returns all outgoing edges from node u."""
        return self.adj.get(str(u), [])

    @classmethod
    def from_networkx(cls, nx_graph: Any) -> "AdjacencyListGraph":
        """Constructs an AdjacencyListGraph directly from a NetworkX Graph instance."""
        graph = cls(directed=getattr(nx_graph, "is_directed", lambda: False)())
        for node, data in nx_graph.nodes(data=True):
            graph.add_node(node, **data)
        for u, v, data in nx_graph.edges(data=True):
            w = data.get("weight", 1.0)
            base_dist = data.get("base_distance", w)
            note = data.get("hazard_note")
            graph.add_edge(u, v, weight=w, base_distance=base_dist, hazard_note=note)
        return graph


def dijkstra_shortest_path(
    graph: AdjacencyListGraph,
    start: str,
    target: str,
    collect_trace: bool = False
) -> Dict[str, Any]:
    """
    Computes single-pair shortest path using manual Dijkstra's algorithm.

    Time Complexity:  O((V + E) log V) with manual binary min-heap
    Space Complexity: O(V) for distances and predecessor tracking

    Args:
        graph: AdjacencyListGraph instance.
        start: Start node ID.
        target: Target/Destination node ID.
        collect_trace: If True, tracks intermediate steps for UI animation/inspection.

    Returns:
        {
            "success": bool,
            "path": List[str],             # Sequence of node IDs
            "distance": float,             # Total edge weight (including penalties)
            "base_distance": float,        # Physical geographical distance in km
            "hazard_alerts": List[str],    # Hazard warnings along selected route
            "visited_order": List[str],    # Execution trace of popped nodes
            "trace": List[Dict[str, Any]]  # Step-by-step trace
        }
    """
    start = str(start)
    target = str(target)

    if start not in graph.nodes:
        raise KeyError(f"Start node '{start}' does not exist in graph.")
    if target not in graph.nodes:
        raise KeyError(f"Target node '{target}' does not exist in graph.")

    # Edge Case: Start equals target
    if start == target:
        return {
            "success": True,
            "path": [start],
            "distance": 0.0,
            "base_distance": 0.0,
            "hazard_alerts": [],
            "visited_order": [start],
            "trace": [{"step": 1, "action": f"Start '{start}' is identical to target.", "current": start}]
        }

    # Initialize data structures
    distances: Dict[str, float] = {node: float("inf") for node in graph.nodes}
    base_distances: Dict[str, float] = {node: float("inf") for node in graph.nodes}
    predecessors: Dict[str, Optional[str]] = {node: None for node in graph.nodes}
    edge_notes: Dict[str, Optional[str]] = {node: None for node in graph.nodes}
    edge_base_weights: Dict[str, float] = {node: 0.0 for node in graph.nodes}

    distances[start] = 0.0
    base_distances[start] = 0.0

    # Manual Min-Heap: storing (tentative_distance, node_id)
    # Binary heap implemented directly inside to guarantee zero external dependency
    heap: List[Tuple[float, str]] = [(0.0, start)]

    def _heap_push(item: Tuple[float, str]) -> None:
        heap.append(item)
        idx = len(heap) - 1
        while idx > 0:
            parent = (idx - 1) // 2
            if heap[idx][0] < heap[parent][0]:
                heap[idx], heap[parent] = heap[parent], heap[idx]
                idx = parent
            else:
                break

    def _heap_pop() -> Tuple[float, str]:
        root = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            idx = 0
            n = len(heap)
            while True:
                smallest = idx
                left = 2 * idx + 1
                right = 2 * idx + 2
                if left < n and heap[left][0] < heap[smallest][0]:
                    smallest = left
                if right < n and heap[right][0] < heap[smallest][0]:
                    smallest = right
                if smallest != idx:
                    heap[idx], heap[smallest] = heap[smallest], heap[idx]
                    idx = smallest
                else:
                    break
        return root

    visited_order: List[str] = []
    settled_nodes: Set[str] = set()
    trace: List[Dict[str, Any]] = []
    step_num = 0

    while heap:
        curr_dist, u = _heap_pop()

        if u in settled_nodes:
            continue
        settled_nodes.add(u)
        visited_order.append(u)

        step_num += 1
        if collect_trace:
            trace.append({
                "step": step_num,
                "current_node": u,
                "current_distance": round(curr_dist, 3),
                "action": f"Settled node '{u}' with minimum distance {curr_dist:.2f}"
            })

        # Early termination when destination is settled
        if u == target:
            break

        # Edge relaxation for each outgoing neighbor
        for edge in graph.neighbors(u):
            v = edge["to"]
            weight = edge["weight"]
            base_dist = edge.get("base_distance", weight)
            note = edge.get("hazard_note")

            if weight < 0:
                raise ValueError(f"Encountered negative edge weight {weight} between {u} and {v}")

            new_dist = curr_dist + weight

            if new_dist < distances[v]:
                distances[v] = new_dist
                base_distances[v] = base_distances[u] + base_dist
                predecessors[v] = u
                edge_notes[v] = note
                edge_base_weights[v] = base_dist
                _heap_push((new_dist, v))

                if collect_trace:
                    trace.append({
                        "step": step_num,
                        "action": f"Relaxed edge ({u} -> {v}): updated distance to {new_dist:.2f}",
                        "relaxed_node": v,
                        "new_distance": round(new_dist, 3)
                    })

    # Check if target is unreachable
    if distances[target] == float("inf"):
        return {
            "success": False,
            "path": [],
            "distance": float("inf"),
            "base_distance": float("inf"),
            "hazard_alerts": [],
            "visited_order": visited_order,
            "trace": trace
        }

    # Reconstruct optimal path from target backwards to start
    path: List[str] = []
    curr: Optional[str] = target
    hazard_alerts: List[str] = []

    while curr is not None:
        path.append(curr)
        if edge_notes.get(curr):
            hazard_alerts.append(edge_notes[curr])
        curr = predecessors.get(curr)

    # Reverse to obtain chronological start -> target sequence
    path.reverse()
    hazard_alerts.reverse()

    return {
        "success": True,
        "path": path,
        "distance": round(distances[target], 3),
        "base_distance": round(base_distances[target], 3),
        "hazard_alerts": hazard_alerts,
        "visited_order": visited_order,
        "trace": trace
    }
