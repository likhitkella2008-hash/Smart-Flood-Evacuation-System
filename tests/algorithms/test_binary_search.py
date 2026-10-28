"""
Unit tests for Manual Iterative Binary Search (algorithms/binary_search.py)
"""

import unittest
from algorithms.binary_search import (
    binary_search_request_by_id,
    binary_search_ids,
    is_sorted_by_id
)


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
        """Finds target located inside the array and collects trace."""
        found, steps, trace = binary_search_request_by_id(self.sample_requests, 45, collect_trace=True)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], 45)
        self.assertTrue(len(trace) > 0)
        self.assertEqual(trace[-1]["status"], "MATCH_FOUND")

    def test_target_not_present_smaller_than_min(self):
        """Target smaller than minimum element returns None."""
        found, steps, trace = binary_search_request_by_id(self.sample_requests, 1)
        self.assertIsNone(found)

    def test_target_not_present_larger_than_max(self):
        """Target larger than maximum element returns None."""
        found, steps, trace = binary_search_request_by_id(self.sample_requests, 999)
        self.assertIsNone(found)

    def test_target_in_gap(self):
        """Target between elements returns None."""
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

    def test_generic_binary_search_ids(self):
        """Verifies binary_search_ids helper."""
        idx, steps = binary_search_ids(self.sample_ids, 79)
        self.assertEqual(idx, 8)

        missing_idx, _ = binary_search_ids(self.sample_ids, 80)
        self.assertEqual(missing_idx, -1)


if __name__ == "__main__":
    unittest.main()
