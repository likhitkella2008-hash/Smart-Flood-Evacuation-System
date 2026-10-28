"""
Unit tests for Breadth-First Search (algorithms/bfs.py).
"""

import unittest
from algorithms.dijkstra import AdjacencyListGraph
from algorithms.bfs import ManualQueue, bfs_traversal


class TestBFS(unittest.TestCase):
    """Test suite for manual BFS and ManualQueue."""

    def setUp(self):
        self.graph = AdjacencyListGraph()
        self.graph.add_edge("A", "B", 1.0)
        self.graph.add_edge("A", "C", 2.0)
        self.graph.add_edge("B", "D", 1.5)
        self.graph.add_edge("C", "D", 2.5)
        self.graph.add_edge("D", "E", 3.0)
        self.graph.add_node("Isolated")

    def test_queue_operations(self):
        q = ManualQueue()
        self.assertTrue(q.is_empty())
        self.assertEqual(len(q), 0)
        self.assertIsNone(q.peek())

        q.enqueue(10)
        q.enqueue(20)
        self.assertFalse(q.is_empty())
        self.assertEqual(len(q), 2)
        self.assertEqual(q.peek(), 10)

        self.assertEqual(q.dequeue(), 10)
        self.assertEqual(q.dequeue(), 20)
        self.assertTrue(q.is_empty())

        with self.assertRaises(IndexError):
            q.dequeue()

    def test_bfs_traversal(self):
        res = bfs_traversal(self.graph, "A", collect_trace=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["start_node"], "A")
        self.assertEqual(res["visited_order"][0], "A")
        # Level 1 should be B and C
        self.assertIn("B", res["visited_order"][1:3])
        self.assertIn("C", res["visited_order"][1:3])
        self.assertEqual(res["hop_distances"]["A"], 0)
        self.assertEqual(res["hop_distances"]["B"], 1)
        self.assertEqual(res["hop_distances"]["C"], 1)
        self.assertEqual(res["hop_distances"]["D"], 2)
        self.assertEqual(res["hop_distances"]["E"], 3)
        self.assertNotIn("Isolated", res["reachable_nodes"])
        self.assertGreater(len(res["trace"]), 0)

    def test_bfs_max_hops(self):
        res = bfs_traversal(self.graph, "A", max_hops=1)
        self.assertTrue(res["success"])
        self.assertIn("B", res["visited_order"])
        self.assertIn("C", res["visited_order"])
        self.assertNotIn("D", res["visited_order"])
        self.assertNotIn("E", res["visited_order"])

    def test_bfs_missing_start_node(self):
        with self.assertRaises(KeyError):
            bfs_traversal(self.graph, "NonExistent")


if __name__ == "__main__":
    unittest.main()
