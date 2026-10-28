"""
Unit tests for Manual BFS & DFS Traversals (algorithms/graph_traversal.py)
"""

import unittest
from algorithms.dijkstra import AdjacencyListGraph
from algorithms.graph_traversal import (
    bfs_traversal,
    dfs_traversal,
    find_connected_components,
    ManualQueue,
    ManualStack
)


class TestGraphTraversals(unittest.TestCase):
    """Verifies BFS level-order and DFS deep exploration implementations."""

    def test_manual_queue_fifo(self):
        """Verifies FIFO behavior of ManualQueue."""
        q = ManualQueue()
        self.assertTrue(q.is_empty())
        q.enqueue(10)
        q.enqueue(20)
        q.enqueue(30)
        self.assertEqual(len(q), 3)
        self.assertEqual(q.dequeue(), 10)
        self.assertEqual(q.dequeue(), 20)
        self.assertEqual(q.dequeue(), 30)
        self.assertTrue(q.is_empty())

    def test_manual_stack_lifo(self):
        """Verifies LIFO behavior of ManualStack."""
        s = ManualStack()
        self.assertTrue(s.is_empty())
        s.push("first")
        s.push("second")
        self.assertEqual(s.peek(), "second")
        self.assertEqual(s.pop(), "second")
        self.assertEqual(s.pop(), "first")
        self.assertTrue(s.is_empty())

    def setUp(self):
        self.g = AdjacencyListGraph()
        # Connect: A-B, A-C, B-D, C-E, D-F
        self.g.add_edge("A", "B", 1.0)
        self.g.add_edge("A", "C", 1.0)
        self.g.add_edge("B", "D", 1.0)
        self.g.add_edge("C", "E", 1.0)
        self.g.add_edge("D", "F", 1.0)

    def test_bfs_hop_distances(self):
        """BFS correctly records minimum hops from start node."""
        res = bfs_traversal(self.g, "A")
        self.assertTrue(res["success"])
        hops = res["hop_distances"]
        self.assertEqual(hops["A"], 0)
        self.assertEqual(hops["B"], 1)
        self.assertEqual(hops["C"], 1)
        self.assertEqual(hops["D"], 2)
        self.assertEqual(hops["E"], 2)
        self.assertEqual(hops["F"], 3)

    def test_bfs_max_hops_constraint(self):
        """BFS respects max_hops cutoff."""
        res = bfs_traversal(self.g, "A", max_hops=1)
        self.assertIn("A", res["reachable_nodes"])
        self.assertIn("B", res["reachable_nodes"])
        self.assertIn("C", res["reachable_nodes"])
        self.assertNotIn("F", res["hop_distances"])

    def test_dfs_path_to_target(self):
        """DFS identifies a path to destination."""
        res = dfs_traversal(self.g, "A", target_node="F")
        self.assertTrue(res["success"])
        self.assertTrue(res["target_found"])
        self.assertEqual(res["path_to_target"][0], "A")
        self.assertEqual(res["path_to_target"][-1], "F")

    def test_cycle_safety(self):
        """Visited set prevents infinite loops in cyclic graphs."""
        cyclic_g = AdjacencyListGraph()
        cyclic_g.add_edge("1", "2", 1.0)
        cyclic_g.add_edge("2", "3", 1.0)
        cyclic_g.add_edge("3", "1", 1.0)  # Cycle 1-2-3-1

        bfs_res = bfs_traversal(cyclic_g, "1")
        self.assertEqual(len(bfs_res["visited_order"]), 3)

        dfs_res = dfs_traversal(cyclic_g, "1")
        self.assertEqual(len(dfs_res["visited_order"]), 3)

    def test_connected_components(self):
        """Identifies separate disconnected components."""
        g = AdjacencyListGraph()
        g.add_edge("Subnet1_A", "Subnet1_B", 1.0)
        g.add_edge("Subnet2_C", "Subnet2_D", 1.0)
        comps = find_connected_components(g)
        self.assertEqual(len(comps), 2)


if __name__ == "__main__":
    unittest.main()
