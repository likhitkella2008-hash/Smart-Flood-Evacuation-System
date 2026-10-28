"""
Unit tests for Manual Binary Heap Priority Queue (algorithms/priority_queue.py)
"""

import unittest
from algorithms.priority_queue import (
    EmergencyPriorityQueue,
    BinaryHeap,
    MinHeap
)


class TestPriorityQueue(unittest.TestCase):
    """Verifies manual Binary Heap and Emergency Priority Queue implementation."""

    def test_heap_indices_math(self):
        """Verifies tree-to-array index mathematical invariants."""
        self.assertEqual(EmergencyPriorityQueue.parent_index(1), 0)
        self.assertEqual(EmergencyPriorityQueue.parent_index(2), 0)
        self.assertEqual(EmergencyPriorityQueue.parent_index(3), 1)
        self.assertEqual(EmergencyPriorityQueue.parent_index(4), 1)
        self.assertEqual(EmergencyPriorityQueue.left_child_index(0), 1)
        self.assertEqual(EmergencyPriorityQueue.right_child_index(0), 2)
        self.assertEqual(EmergencyPriorityQueue.left_child_index(1), 3)
        self.assertEqual(EmergencyPriorityQueue.right_child_index(1), 4)

    def test_priority_queue_push_and_peek(self):
        """Peek previews highest priority without popping."""
        pq = EmergencyPriorityQueue()
        self.assertTrue(pq.is_empty())
        self.assertIsNone(pq.peek())

        pq.push({"id": 1, "priority": "Medium", "priority_score": 30.0})
        self.assertEqual(pq.peek()["id"], 1)

        pq.push({"id": 2, "priority": "Critical", "priority_score": 85.0})
        # Root must immediately become the Critical request via heapify_up
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

    def test_bottom_up_build_heap(self):
        """Verifies O(N) bottom-up heapification produces valid max-heap order."""
        cases = [
            {"id": 1, "priority": "Low", "priority_score": 10.0},
            {"id": 2, "priority": "Critical", "priority_score": 75.0},
            {"id": 3, "priority": "High", "priority_score": 60.0},
            {"id": 4, "priority": "Critical", "priority_score": 92.0},
        ]
        pq = EmergencyPriorityQueue(initial_items=cases)
        self.assertEqual(len(pq), 4)
        self.assertEqual(pq.peek()["id"], 4)
        top = pq.pop()
        self.assertEqual(top["id"], 4)

    def test_equal_priority_tie_breaking(self):
        """Equal category and score broken by earlier created_at / lower ID."""
        pq = EmergencyPriorityQueue()
        # Same category and score; req 10 has earlier timestamp
        pq.push({"id": 20, "priority": "High", "priority_score": 50.0, "created_at": "2026-10-28 10:30:00"})
        pq.push({"id": 10, "priority": "High", "priority_score": 50.0, "created_at": "2026-10-28 10:00:00"})

        # Earlier created_at should come out first
        first = pq.pop()
        self.assertEqual(first["id"], 10)
        second = pq.pop()
        self.assertEqual(second["id"], 20)

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


if __name__ == "__main__":
    unittest.main()
