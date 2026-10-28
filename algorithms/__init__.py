"""
Smart Flood Rescue System - Data Structures and Algorithms (DSA) Package
========================================================================

Genuine, from-scratch Python implementations of core ADSA algorithms:
- Merge Sort (Emergency Triage Sorting)
- Binary Search (Request ID Lookup)
- Priority Queue / Binary Heap (Triage Emergency Dispatch)
- Heap Sort (In-Place Tree-Array Sorting)
- Dijkstra's Algorithm (Disaster Road Shortest Path Routing)
- Breadth-First Search (Reachability & Evacuation Wave)
- Depth-First Search (Corridor & Isolation Analysis)
- Nearest Resource Selection (Single-Pass Linear Selection)
"""

from algorithms.merge_sort import (
    merge_sort,
    merge_sort_requests,
    merge_sort_by_key,
    compare_emergency_requests,
    get_priority_rank
)

from algorithms.binary_search import (
    binary_search,
    binary_search_request_by_id,
    binary_search_ids,
    is_sorted_by_id
)

from algorithms.priority_queue import (
    BinaryHeap,
    EmergencyPriorityQueue,
    MinHeap
)

from algorithms.heap_sort import (
    heapify,
    heapify_min,
    heap_sort,
    heap_sort_requests
)

from algorithms.dijkstra import (
    AdjacencyListGraph,
    dijkstra_shortest_path
)

from algorithms.bfs import (
    ManualQueue,
    bfs_traversal
)

from algorithms.dfs import (
    ManualStack,
    dfs_traversal,
    find_connected_components
)

from algorithms.nearest_resource import (
    find_nearest_available_team,
    find_nearest_suitable_shelter,
    find_nearest_resource
)

__all__ = [
    "merge_sort",
    "merge_sort_requests",
    "merge_sort_by_key",
    "compare_emergency_requests",
    "get_priority_rank",
    "binary_search",
    "binary_search_request_by_id",
    "binary_search_ids",
    "is_sorted_by_id",
    "BinaryHeap",
    "EmergencyPriorityQueue",
    "MinHeap",
    "heapify",
    "heapify_min",
    "heap_sort",
    "heap_sort_requests",
    "AdjacencyListGraph",
    "dijkstra_shortest_path",
    "ManualQueue",
    "bfs_traversal",
    "ManualStack",
    "dfs_traversal",
    "find_connected_components",
    "find_nearest_available_team",
    "find_nearest_suitable_shelter",
    "find_nearest_resource",
]
