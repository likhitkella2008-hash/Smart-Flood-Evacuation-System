"""
Unit tests for Manual Recursive Merge Sort (algorithms/merge_sort.py)
"""

import unittest
from algorithms.merge_sort import (
    merge_sort,
    merge_sort_requests,
    merge_sort_by_key,
    compare_emergency_requests,
    get_priority_rank
)


class TestMergeSort(unittest.TestCase):
    """Verifies manual recursive Merge Sort implementation."""

    def test_generic_merge_sort_empty_and_single(self):
        """Standard merge_sort handles empty and single-element lists."""
        self.assertEqual(merge_sort([]), [])
        self.assertEqual(merge_sort([42]), [42])

    def test_generic_merge_sort_already_sorted_and_reversed(self):
        """Standard merge_sort correctly sorts already-sorted and reverse-sorted lists."""
        already_sorted = [1, 2, 3, 4, 5, 6]
        self.assertEqual(merge_sort(already_sorted), [1, 2, 3, 4, 5, 6])

        reversed_list = [6, 5, 4, 3, 2, 1]
        self.assertEqual(merge_sort(reversed_list), [1, 2, 3, 4, 5, 6])

    def test_generic_merge_sort_with_duplicates(self):
        """Standard merge_sort sorts arrays with multiple duplicate values."""
        raw = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
        self.assertEqual(merge_sort(raw), [1, 1, 2, 3, 3, 4, 5, 5, 5, 6, 9])

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
        """Within identical category, higher numerical score must come first."""
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

    def test_stability_on_duplicates(self):
        """Duplicate records preserve their relative input order (stable sort)."""
        raw = [
            {"id": 5, "priority": "Medium", "priority_score": 40.0, "tag": "first"},
            {"id": 5, "priority": "Medium", "priority_score": 40.0, "tag": "second"},
        ]
        sorted_reqs = merge_sort_requests(raw)
        self.assertEqual(sorted_reqs[0]["tag"], "first")
        self.assertEqual(sorted_reqs[1]["tag"], "second")

    def test_merge_sort_by_key_ascending_and_descending(self):
        """Generic merge sort by key sorts values ascending and descending."""
        items = [{"id": 40}, {"id": 10}, {"id": 99}, {"id": 5}, {"id": 25}]
        asc = merge_sort_by_key(items, key="id")
        self.assertEqual([x["id"] for x in asc], [5, 10, 25, 40, 99])

        desc = merge_sort_by_key(items, key="id", reverse=True)
        self.assertEqual([x["id"] for x in desc], [99, 40, 25, 10, 5])


if __name__ == "__main__":
    unittest.main()
