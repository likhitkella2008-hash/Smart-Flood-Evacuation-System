"""
Smart Flood Rescue System - ADSA Algorithms & Data Structures Unit Test Suite
=============================================================================

Comprehensive test suite verifying correctness, edge cases, invariants, and integration
for all 5 core DSA algorithms:
1. Merge Sort (Recursive divide-and-conquer triage ranking)
2. Binary Search (Iterative logarithmic ID lookup)
3. Priority Queue (Array-based binary heap triage dispatch)
4. Dijkstra's Algorithm (Adjacency list shortest path with hazard penalties)
5. Graph Traversals (BFS level-order & DFS deep-corridor exploration)
"""

import unittest
from typing import Dict, Any, List

from algorithms.merge_sort import (
    merge_sort_requests,
    merge_sort_by_key,
    compare_emergency_requests,
    get_priority_rank
)
from algorithms.binary_search import (
    binary_search_request_by_id,
    binary_search_ids,
    is_sorted_by_id
)
from algorithms.priority_queue import (
    BinaryHeap,
    EmergencyPriorityQueue,
    MinHeap
)
from algorithms.dijkstra import (
    AdjacencyListGraph,
    dijkstra_shortest_path
)
from algorithms.graph_traversal import (
    bfs_traversal,
    dfs_traversal,
    find_connected_components
)
import routing
from app import app


class TestMergeSort(unittest.TestCase):
    """Verifies manual recursive Merge Sort implementation."""

    def test_empty_list(self):
        """Empty input returns empty list without error."""
        self.assertEqual(merge_sort_requests([]), [])

    def test_single_element(self):
        """Single element list returns identical element."""
        req = [{"id": 1, "priority": "Critical", "priority_score": 90.0}]
        self.assertEqual(merge_sort_requests(req), req)

    def test_category_priority_ordering(self):
        """Ensures Critical > High > Medium > Low hierarchy."""
        raw = [
            {"id": 1, "priority": "Low", "priority_score": 10.0},
            {"id": 2, "priority": "Critical", "priority_score": 75.0},
            {"id": 3, "priority": "Medium", "priority_score": 30.0},
            {"id": 4, "priority": "High", "priority_score": 50.0},
        ]
        sorted_reqs = merge_sort_requests(raw)
        priorities = [r["priority"] for r in sorted_reqs]
        self.assertEqual(priorities, ["Critical", "High", "Medium", "Low"])

    def test_score_tie_breaking_within_category(self):
        """Within identical category, higher score must come first."""
        raw = [
            {"id": 1, "priority": "Critical", "priority_score": 75.0},
            {"id": 2, "priority": "Critical", "priority_score": 95.0},
            {"id": 3, "priority": "Critical", "priority_score": 82.0},
        ]
        sorted_reqs = merge_sort_requests(raw)
        scores = [r["priority_score"] for r in sorted_reqs]
        self.assertEqual(scores, [95.0, 82.0, 75.0])

    def test_timestamp_and_id_tie_breaking(self):
        """Identical category and score broken by earlier created_at or lower id."""
        raw = [
            {"id": 20, "priority": "High", "priority_score": 60.0, "created_at": "2026-10-28 12:00:00"},
            {"id": 10, "priority": "High", "priority_score": 60.0, "created_at": "2026-10-28 11:00:00"},
        ]
        sorted_reqs = merge_sort_requests(raw)
        self.assertEqual(sorted_reqs[0]["id"], 10)

    def test_merge_sort_by_key_ascending(self):
        """Generic merge sort by key sorts integers ascending for binary search."""
        items = [{"id": 40}, {"id": 10}, {"id": 99}, {"id": 5}, {"id": 25}]
        res = merge_sort_by_key(items, key="id")
        ids = [x["id"] for x in res]
        self.assertEqual(ids, [5, 10, 25, 40, 99])


class TestBinarySearch(unittest.TestCase):
    """Verifies manual iterative Binary Search implementation."""

    def setUp(self):
        self.sample_ids = [5, 12, 19, 27, 34, 45, 58, 62, 79, 88, 93, 101]
        self.sample_requests = [{"id": i, "name": f"Victim #{i}"} for i in self.sample_ids]

    def test_empty_search(self):
        """Binary search on empty list returns None and 0 steps."""
        found, steps, trace = binary_search_request_by_id([], 50)
        self.assertIsNone(found)
        self.assertEqual(steps, 0)

    def test_first_element_left_boundary(self):
        """Finds target located at left extreme."""
        found, steps, trace = binary_search_request_by_id(self.sample_requests, 5)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], 5)
        self.assertLessEqual(steps, 5)

    def test_last_element_right_boundary(self):
        """Finds target located at right extreme."""
        found, steps, trace = binary_search_request_by_id(self.sample_requests, 101)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], 101)
        self.assertLessEqual(steps, 5)

    def test_midpoint_search(self):
        """Finds target located inside the array."""
        found, steps, trace = binary_search_request_by_id(self.sample_requests, 45, collect_trace=True)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], 45)
        self.assertTrue(len(trace) > 0)

    def test_target_not_present(self):
        """Correctly identifies missing element."""
        found, steps, trace = binary_search_request_by_id(self.sample_requests, 50)
        self.assertIsNone(found)
        self.assertLessEqual(steps, 5)

    def test_single_element_found_and_not_found(self):
        """Single element array edge case."""
        single = [{"id": 42}]
        found, steps, _ = binary_search_request_by_id(single, 42)
        self.assertIsNotNone(found)
        self.assertEqual(steps, 1)

        found_missing, steps_m, _ = binary_search_request_by_id(single, 99)
        self.assertIsNone(found_missing)
        self.assertEqual(steps_m, 1)


class TestPriorityQueue(unittest.TestCase):
    """Verifies manual Binary Heap and Emergency Priority Queue implementation."""

    def test_heap_indices_math(self):
        """Verifies tree-to-array index mathematical invariants."""
        self.assertEqual(BinaryHeap.parent_index(1), 0)
        self.assertEqual(BinaryHeap.parent_index(2), 0)
        self.assertEqual(BinaryHeap.parent_index(3), 1)
        self.assertEqual(BinaryHeap.parent_index(4), 1)
        self.assertEqual(BinaryHeap.left_child_index(0), 1)
        self.assertEqual(BinaryHeap.right_child_index(0), 2)
        self.assertEqual(BinaryHeap.left_child_index(1), 3)
        self.assertEqual(BinaryHeap.right_child_index(1), 4)

    def test_priority_queue_push_and_peek(self):
        """Peek previews highest priority without popping."""
        pq = EmergencyPriorityQueue()
        self.assertTrue(pq.is_empty())
        self.assertIsNone(pq.peek())

        pq.push({"id": 1, "priority": "Medium", "priority_score": 30.0})
        self.assertEqual(pq.peek()["id"], 1)

        pq.push({"id": 2, "priority": "Critical", "priority_score": 85.0})
        # Root must become the Critical request
        self.assertEqual(pq.peek()["id"], 2)

    def test_sequential_priority_pops(self):
        """Pop extracts elements in strict descending urgency."""
        pq = EmergencyPriorityQueue()
        cases = [
            {"id": 1, "priority": "Low", "priority_score": 10.0},
            {"id": 2, "priority": "Critical", "priority_score": 75.0},
            {"id": 3, "priority": "High", "priority_score": 60.0},
            {"id": 4, "priority": "Critical", "priority_score": 92.0},
            {"id": 5, "priority": "Medium", "priority_score": 35.0},
        ]
        for c in cases:
            pq.push(c)

        self.assertEqual(len(pq), 5)
        # Expected pop order: ID 4 (Crit 92), ID 2 (Crit 75), ID 3 (High 60), ID 5 (Med 35), ID 1 (Low 10)
        popped_ids = [pq.pop()["id"] for _ in range(5)]
        self.assertEqual(popped_ids, [4, 2, 3, 5, 1])
        self.assertTrue(pq.is_empty())

    def test_pop_empty_queue_raises_error(self):
        """Popping empty heap raises IndexError."""
        pq = EmergencyPriorityQueue()
        with self.assertRaises(IndexError):
            pq.pop()

    def test_min_heap_for_dijkstra(self):
        """MinHeap extracts smallest distance first."""
        mh = MinHeap()
        mh.push(10.5, "Node_A")
        mh.push(2.1, "Node_B")
        mh.push(7.4, "Node_C")
        mh.push(1.2, "Node_D")

        popped = [mh.pop()[1] for _ in range(4)]
        self.assertEqual(popped, ["Node_D", "Node_B", "Node_C", "Node_A"])


class TestDijkstra(unittest.TestCase):
    """Verifies manual Dijkstra algorithm implementation."""

    def test_simple_triangle_graph(self):
        """Solves shortest path on small 3-node graph."""
        g = AdjacencyListGraph()
        g.add_edge("A", "B", 1.0)
        g.add_edge("B", "C", 2.0)
        g.add_edge("A", "C", 5.0)

        res = dijkstra_shortest_path(g, "A", "C")
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["A", "B", "C"])
        self.assertEqual(res["distance"], 3.0)

    def test_start_equals_target(self):
        """Start node identical to destination returns distance 0."""
        g = AdjacencyListGraph()
        g.add_node("Amrita_Ettimadai")
        res = dijkstra_shortest_path(g, "Amrita_Ettimadai", "Amrita_Ettimadai")
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["Amrita_Ettimadai"])
        self.assertEqual(res["distance"], 0.0)

    def test_negative_weight_rejection(self):
        """Raises ValueError when negative weight is introduced."""
        g = AdjacencyListGraph()
        with self.assertRaises(ValueError):
            g.add_edge("X", "Y", -3.5)

    def test_disconnected_graph_target_unreachable(self):
        """Unreachable target returns success=False and infinite distance."""
        g = AdjacencyListGraph()
        g.add_edge("Island_A", "Island_B", 2.0)
        g.add_node("Mainland_C")

        res = dijkstra_shortest_path(g, "Island_A", "Mainland_C")
        self.assertFalse(res["success"])
        self.assertEqual(res["path"], [])
        self.assertEqual(res["distance"], float("inf"))

    def test_coimbatore_arterial_route_with_hazard_detour(self):
        """Verifies Coimbatore road network routing and flood hazard penalty diversion."""
        # Unpenalized graph
        clean_g = routing.build_manual_disaster_graph(active_hazards=[])
        clean_res = dijkstra_shortest_path(clean_g, "gandhipuram_hub", "singanallur_hub")
        self.assertTrue(clean_res["success"])
        self.assertGreater(clean_res["distance"], 0.0)

        # Penalize primary corridor via flooded hazard on Sungam bypass
        flooded_hazard = [{
            "name": "Sungam Bypass Flooding",
            "latitude": 10.9970,
            "longitude": 76.9780,
            "severity": "Flooded / Closed"
        }]
        hazard_g = routing.build_manual_disaster_graph(active_hazards=flooded_hazard)
        hazard_res = dijkstra_shortest_path(hazard_g, "gandhipuram_hub", "singanallur_hub")
        self.assertTrue(hazard_res["success"])
        # Should divert or apply substantial penalty (reroutes via Avinashi Rd Peelamedu)
        self.assertNotEqual(clean_res["path"], hazard_res["path"])
        self.assertEqual(hazard_res["path"], ["gandhipuram_hub", "avinashi_rd_peelamedu", "singanallur_hub"])
        self.assertNotEqual(clean_res["distance"], hazard_res["distance"])


class TestGraphTraversals(unittest.TestCase):
    """Verifies BFS level-order and DFS deep exploration implementations."""

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
        # Should only visit A, B, C
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


class TestAppEndpointsIntegration(unittest.TestCase):
    """Verifies that Flask endpoints correctly serve DSA features."""

    def setUp(self):
        self.client = app.test_client()
        # Authenticate admin session
        self.client.post("/admin-login", json={"username": "admin", "password": "admin123"})

    def test_admin_requests_uses_merge_sort(self):
        """Verifies /admin/requests returns Merge Sort metadata and sorted items."""
        resp = self.client.get("/admin/requests")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("Merge Sort", data.get("sorting_engine", ""))
        reqs = data.get("requests", [])
        self.assertIsInstance(reqs, list)

    def test_admin_binary_search_endpoint(self):
        """Verifies /api/admin/requests/search-id executes Binary Search."""
        resp = self.client.get("/api/admin/requests/search-id?id=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("Binary Search", data.get("algorithm", ""))
        self.assertIn("steps_taken", data)

    def test_admin_priority_queue_endpoint(self):
        """Verifies /api/admin/dispatch/triage-queue inspects Binary Heap."""
        resp = self.client.get("/api/admin/dispatch/triage-queue")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("Binary Max-Heap", data.get("data_structure", ""))

    def test_dsa_demo_api_and_page(self):
        """Verifies /api/dsa/demo and /dsa are accessible and valid."""
        demo_resp = self.client.get("/api/dsa/demo")
        self.assertEqual(demo_resp.status_code, 200)
        demo_data = demo_resp.get_json()
        self.assertTrue(demo_data.get("success"))
        self.assertIn("merge_sort", demo_data.get("algorithms", {}))
        self.assertIn("dijkstra", demo_data.get("algorithms", {}))

        page_resp = self.client.get("/dsa")
        self.assertEqual(page_resp.status_code, 200)
        self.assertIn(b"ADSA Algorithms Laboratory", page_resp.data)

    def test_dsa_source_code_api(self):
        """Verifies /api/dsa/source-code returns genuine Python files for all algorithms."""
        resp = self.client.get("/api/dsa/source-code")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        sources = data.get("sources", {})
        required_algos = ["merge_sort", "binary_search", "priority_queue", "heap_sort", "dijkstra", "bfs", "dfs", "nearest_resource"]
        for algo in required_algos:
            self.assertIn(algo, sources)
            self.assertTrue(len(sources[algo]) > 50)

        # Single algorithm lookup
        single_resp = self.client.get("/api/dsa/source-code/heap_sort")
        self.assertEqual(single_resp.status_code, 200)
        single_data = single_resp.get_json()
        self.assertTrue(single_data.get("success"))
        self.assertIn("def heap_sort", single_data.get("code", ""))


if __name__ == "__main__":
    unittest.main()
