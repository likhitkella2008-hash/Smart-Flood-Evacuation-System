"""
Unit tests for Depth-First Search (algorithms/dfs.py).
"""

import unittest
from algorithms.dijkstra import AdjacencyListGraph
from algorithms.dfs import ManualStack, dfs_traversal, find_connected_components


class TestDFS(unittest.TestCase):
    """Test suite for manual DFS, ManualStack, and connected components."""

    def setUp(self):
        self.graph = AdjacencyListGraph()
        self.graph.add_edge("1", "2", 1.0)
        self.graph.add_edge("2", "3", 1.0)
        self.graph.add_edge("3", "4", 1.0)
        # Separate island component
        self.graph.add_edge("5", "6", 1.0)
        # Isolated single node
        self.graph.add_node("7")

    def test_stack_operations(self):
        s = ManualStack()
        self.assertTrue(s.is_empty())
        self.assertEqual(len(s), 0)
        self.assertIsNone(s.peek())

        s.push("alpha")
        s.push("beta")
        self.assertEqual(len(s), 2)
        self.assertEqual(s.peek(), "beta")
        self.assertEqual(s.pop(), "beta")
        self.assertEqual(s.pop(), "alpha")
        self.assertTrue(s.is_empty())

        with self.assertRaises(IndexError):
            s.pop()

    def test_dfs_traversal(self):
        res = dfs_traversal(self.graph, "1", collect_trace=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["start_node"], "1")
        self.assertEqual(set(res["reachable_nodes"]), {"1", "2", "3", "4"})
        self.assertNotIn("5", res["reachable_nodes"])
        self.assertNotIn("7", res["reachable_nodes"])
        self.assertGreater(len(res["trace"]), 0)

    def test_dfs_target_path(self):
        res = dfs_traversal(self.graph, "1", target_node="4")
        self.assertTrue(res["target_found"])
        self.assertEqual(res["path_to_target"], ["1", "2", "3", "4"])

    def test_dfs_unreachable_target(self):
        res = dfs_traversal(self.graph, "1", target_node="5")
        self.assertFalse(res["target_found"])
        self.assertIsNone(res["path_to_target"])

    def test_find_connected_components(self):
        components = find_connected_components(self.graph)
        self.assertEqual(len(components), 3)
        sizes = sorted([len(c) for c in components])
        self.assertEqual(sizes, [1, 2, 4])


if __name__ == "__main__":
    unittest.main()
