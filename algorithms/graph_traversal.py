"""
Smart Flood Rescue System - Graph Traversals (BFS & DFS) Integration Module
===========================================================================

Re-exports manual Breadth-First Search (BFS) and Depth-First Search (DFS)
implementations from `algorithms.bfs` and `algorithms.dfs` for backward
compatibility with existing system imports.

Data Structures:
- ManualQueue (algorithms.bfs)
- ManualStack (algorithms.dfs)
"""

from algorithms.bfs import ManualQueue, bfs_traversal
from algorithms.dfs import ManualStack, dfs_traversal, find_connected_components

__all__ = [
    "ManualQueue",
    "ManualStack",
    "bfs_traversal",
    "dfs_traversal",
    "find_connected_components",
]
