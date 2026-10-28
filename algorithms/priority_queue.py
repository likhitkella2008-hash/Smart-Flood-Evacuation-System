"""
Smart Flood Rescue System - Priority Queue (Binary Heap) Implementation
========================================================================

Manual array-based Binary Heap implementation.
Explicitly avoids Python's built-in `heapq` module.

Mathematical Tree-to-Array Invariants:
-------------------------------------
For node at 0-indexed position i:
  - Parent index:       (i - 1) // 2
  - Left child index:   2 * i + 1
  - Right child index:  2 * i + 2

Time Complexity:
  - push:     O(log N)    (Sift-up from leaf to root)
  - pop:      O(log N)    (Sift-down from root to leaf)
  - peek:     O(1)        (Root inspection)
  - is_empty: O(1)
  - size:     O(1)
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
from algorithms.merge_sort import compare_emergency_requests


class BinaryHeap:
    """
    Generic manual array-based Binary Heap.
    
    Accepts a comparator function `is_higher_priority(item_a, item_b) -> bool`.
    Returns True if item_a should be positioned closer to the root than item_b.
    """

    def __init__(self, is_higher_priority: Callable[[Any, Any], bool]):
        self._heap: List[Any] = []
        self._is_higher = is_higher_priority

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    @staticmethod
    def parent_index(i: int) -> int:
        return (i - 1) // 2

    @staticmethod
    def left_child_index(i: int) -> int:
        return 2 * i + 1

    @staticmethod
    def right_child_index(i: int) -> int:
        return 2 * i + 2

    def push(self, item: Any) -> None:
        """Appends item to the end of the array and sifts it up to restore heap invariant."""
        self._heap.append(item)
        self._heapify_up(len(self._heap) - 1)

    def pop(self) -> Any:
        """Removes and returns the root (highest priority item) of the heap."""
        if self.is_empty():
            raise IndexError("pop from an empty Priority Queue")

        root = self._heap[0]
        last_item = self._heap.pop()

        if not self.is_empty():
            self._heap[0] = last_item
            self._heapify_down(0)

        return root

    def peek(self) -> Optional[Any]:
        """Returns the root item without removing it. Returns None if empty."""
        if self.is_empty():
            return None
        return self._heap[0]

    def _heapify_up(self, index: int) -> None:
        """Restores heap invariant upward from the given index to the root."""
        current = index
        while current > 0:
            parent = self.parent_index(current)
            # If current item has higher priority than its parent, swap them
            if self._is_higher(self._heap[current], self._heap[parent]):
                self._heap[current], self._heap[parent] = self._heap[parent], self._heap[current]
                current = parent
            else:
                break

    def _heapify_down(self, index: int) -> None:
        """Restores heap invariant downward from the given index toward the leaves."""
        current = index
        n = len(self._heap)

        while True:
            highest_priority_idx = current
            left = self.left_child_index(current)
            right = self.right_child_index(current)

            # Check if left child has higher priority than current candidate
            if left < n and self._is_higher(self._heap[left], self._heap[highest_priority_idx]):
                highest_priority_idx = left

            # Check if right child has higher priority than current candidate
            if right < n and self._is_higher(self._heap[right], self._heap[highest_priority_idx]):
                highest_priority_idx = right

            if highest_priority_idx != current:
                self._heap[current], self._heap[highest_priority_idx] = (
                    self._heap[highest_priority_idx],
                    self._heap[current],
                )
                current = highest_priority_idx
            else:
                break

    def heapify_up(self, index: int) -> None:
        """Public alias for heapify_up."""
        self._heapify_up(index)

    def heapify_down(self, index: int) -> None:
        """Public alias for heapify_down."""
        self._heapify_down(index)

    def to_list(self) -> List[Any]:
        """Returns a shallow copy of the underlying heap array representation."""
        return list(self._heap)


class EmergencyPriorityQueue:
    """
    Triage Emergency Priority Queue backed by a manual Binary Max-Heap.

    Orders requests such that Critical > High > Medium > Low,
    followed by numerical priority score (descending), and earlier submission/ID.

    Mathematical Tree-to-Array Invariants:
      - Parent index:       (i - 1) // 2
      - Left child index:   2 * i + 1
      - Right child index:  2 * i + 2
    """

    def __init__(self, initial_items: Optional[List[Dict[str, Any]]] = None):
        self._heap: List[Dict[str, Any]] = []
        if initial_items:
            self.build_heap(initial_items)

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    @staticmethod
    def parent_index(i: int) -> int:
        return (i - 1) // 2

    @staticmethod
    def left_child_index(i: int) -> int:
        return 2 * i + 1

    @staticmethod
    def right_child_index(i: int) -> int:
        return 2 * i + 2

    def is_higher_priority(self, req_a: Dict[str, Any], req_b: Dict[str, Any]) -> bool:
        """Returns True if req_a has higher triage urgency than req_b."""
        return compare_emergency_requests(req_a, req_b) < 0

    def push(self, request: Dict[str, Any]) -> None:
        """Enqueues an emergency rescue request with O(log N) heap adjustment."""
        self._heap.append(request)
        self.heapify_up(len(self._heap) - 1)

    def pop(self) -> Dict[str, Any]:
        """Dequeues and returns the highest-urgency emergency request ready for dispatch."""
        if self.is_empty():
            raise IndexError("pop from an empty EmergencyPriorityQueue")

        root = self._heap[0]
        last_item = self._heap.pop()

        if not self.is_empty():
            self._heap[0] = last_item
            self.heapify_down(0)

        return root

    def peek(self) -> Optional[Dict[str, Any]]:
        """Previews the highest-urgency pending emergency request without removing it."""
        if self.is_empty():
            return None
        return self._heap[0]

    def heapify_up(self, index: int) -> None:
        """Restores max-heap invariant upward from the given index to the root in O(log N)."""
        current = index
        while current > 0:
            parent = self.parent_index(current)
            if self.is_higher_priority(self._heap[current], self._heap[parent]):
                self._heap[current], self._heap[parent] = self._heap[parent], self._heap[current]
                current = parent
            else:
                break

    def heapify_down(self, index: int) -> None:
        """Restores max-heap invariant downward from index toward the leaves in O(log N)."""
        current = index
        n = len(self._heap)

        while True:
            highest_priority_idx = current
            left = self.left_child_index(current)
            right = self.right_child_index(current)

            if left < n and self.is_higher_priority(self._heap[left], self._heap[highest_priority_idx]):
                highest_priority_idx = left

            if right < n and self.is_higher_priority(self._heap[right], self._heap[highest_priority_idx]):
                highest_priority_idx = right

            if highest_priority_idx != current:
                self._heap[current], self._heap[highest_priority_idx] = (
                    self._heap[highest_priority_idx],
                    self._heap[current],
                )
                current = highest_priority_idx
            else:
                break

    def build_heap(self, items: List[Dict[str, Any]]) -> None:
        """
        Constructs binary max-heap from an arbitrary list using bottom-up heapification.
        Time Complexity: O(N) linear time (more efficient than N * log N successive pushes).
        """
        self._heap = list(items)
        # Start at the last non-leaf node: (n // 2) - 1 down to 0
        for i in range((len(self._heap) // 2) - 1, -1, -1):
            self.heapify_down(i)

    def to_list(self) -> List[Dict[str, Any]]:
        """Returns a copy of the internal heap array representation."""
        return list(self._heap)


class MinHeap:
    """
    Dedicated Binary Min-Heap storing (key, value) pairs.
    Used for Dijkstra's shortest path algorithm where smaller key (distance) = higher priority.
    """

    def __init__(self):
        def _is_smaller(a: Tuple[float, Any], b: Tuple[float, Any]) -> bool:
            return a[0] < b[0]

        self._heap = BinaryHeap(is_higher_priority=_is_smaller)

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return self._heap.is_empty()

    def push(self, priority: float, item: Any) -> None:
        """Pushes (priority, item) tuple into min-heap."""
        self._heap.push((priority, item))

    def pop(self) -> Tuple[float, Any]:
        """Pops and returns (min_priority, item)."""
        return self._heap.pop()

    def peek(self) -> Optional[Tuple[float, Any]]:
        """Returns min without removing."""
        return self._heap.peek()
