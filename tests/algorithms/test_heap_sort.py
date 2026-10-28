"""
Unit tests for Heap Sort algorithm (algorithms/heap_sort.py).
"""

import unittest
from algorithms.heap_sort import heapify, heapify_min, heap_sort, heap_sort_requests


class TestHeapSort(unittest.TestCase):
    """Test suite covering Heap Sort correctness and edge cases."""

    def test_empty_list(self):
        arr = []
        result = heap_sort(arr)
        self.assertEqual(result, [])

    def test_single_element(self):
        arr = [42]
        result = heap_sort(arr)
        self.assertEqual(result, [42])

    def test_already_sorted_ascending(self):
        arr = [1, 2, 3, 4, 5, 6, 7]
        result = heap_sort(arr, ascending=True)
        self.assertEqual(result, [1, 2, 3, 4, 5, 6, 7])

    def test_reverse_sorted(self):
        arr = [9, 8, 7, 6, 5, 4, 3, 2, 1]
        result = heap_sort(arr, ascending=True)
        self.assertEqual(result, [1, 2, 3, 4, 5, 6, 7, 8, 9])

    def test_descending_sort(self):
        arr = [3, 1, 4, 1, 5, 9, 2, 6, 5]
        result = heap_sort(arr, ascending=False)
        self.assertEqual(result, [9, 6, 5, 5, 4, 3, 2, 1, 1])

    def test_duplicate_elements(self):
        arr = [5, 2, 5, 1, 2, 5, 5, 1]
        result = heap_sort(arr, ascending=True)
        self.assertEqual(result, [1, 1, 2, 2, 5, 5, 5, 5])

    def test_all_identical_elements(self):
        arr = [7, 7, 7, 7, 7]
        result = heap_sort(arr, ascending=True)
        self.assertEqual(result, [7, 7, 7, 7, 7])

    def test_negative_and_floating_numbers(self):
        arr = [-3.5, 10.2, 0.0, -12.1, 4.8, -1.0]
        result = heap_sort(arr, ascending=True)
        self.assertEqual(result, [-12.1, -3.5, -1.0, 0.0, 4.8, 10.2])

    def test_heapify_isolated(self):
        # Array where subtrees are heaps but root violates max-heap
        arr = [1, 10, 9, 7, 8, 3, 5]
        heapify(arr, len(arr), 0)
        # Root must now be max of {1, 10, 9} -> 10
        self.assertEqual(arr[0], 10)

    def test_heap_sort_requests(self):
        requests = [
            {"id": 1, "priority_score": 45, "name": "Req A"},
            {"id": 2, "priority_score": 95, "name": "Req B"},
            {"id": 3, "priority_score": 70, "name": "Req C"},
            {"id": 4, "priority_score": 95, "name": "Req D"},
            {"id": 5, "priority_score": 20, "name": "Req E"}
        ]
        sorted_reqs, trace = heap_sort_requests(requests, key="priority_score", reverse=True, collect_trace=True)
        scores = [r["priority_score"] for r in sorted_reqs]
        self.assertEqual(scores, [95, 95, 70, 45, 20])
        self.assertGreater(len(trace), 0)


if __name__ == "__main__":
    unittest.main()
