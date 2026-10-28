"""
Smart Flood Rescue System - Heap Sort Implementation
=====================================================

Textbook educational implementation of the Heap Sort algorithm.
Follows the structured Python format with explicit index calculations,
conditions, temporary variable swaps, and recursive heapify operations.

Mathematical Array-to-Binary-Tree Invariants:
---------------------------------------------
For a node located at index i in a 0-indexed array:
  - Parent index:       (i - 1) // 2
  - Left child index:   2 * i + 1
  - Right child index:  2 * i + 2

Time Complexity:
  - Best Case:    O(N log N)
  - Average Case: O(N log N)
  - Worst Case:   O(N log N)
Space Complexity: O(1) auxiliary (in-place sorting)
Stability: Not stable
"""

from typing import Any, Callable, Dict, List, Optional, Tuple


def heapify(arr: List[Any], n: int, i: int) -> None:
    """
    Maintains the Max-Heap property for a subtree rooted at index i.
    Uses explicit temporary variables and recursive calls.
    
    Args:
        arr: The list of elements being sorted in-place.
        n: Total number of active elements in the heap portion.
        i: Root index of the current subtree.
    """
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2

    # Check if left child exists and is greater than current largest
    if left < n and arr[left] > arr[largest]:
        largest = left

    # Check if right child exists and is greater than current largest
    if right < n and arr[right] > arr[largest]:
        largest = right

    # If the largest is not the root, perform manual swap and recurse
    if largest != i:
        temp = arr[i]
        arr[i] = arr[largest]
        arr[largest] = temp

        # Recursively heapify the affected subtree
        heapify(arr, n, largest)


def heapify_min(arr: List[Any], n: int, i: int) -> None:
    """
    Maintains the Min-Heap property (matching the reference educational style).
    Swapping root to end sorts the array in descending order.
    """
    smallest = i
    left = 2 * i + 1
    right = 2 * i + 2

    if left < n and arr[left] < arr[smallest]:
        smallest = left

    if right < n and arr[right] < arr[smallest]:
        smallest = right

    if smallest != i:
        temp = arr[i]
        arr[i] = arr[smallest]
        arr[smallest] = temp

        heapify_min(arr, n, smallest)


def heap_sort(arr: List[Any], ascending: bool = True) -> List[Any]:
    """
    Sorts an array in-place using the Heap Sort algorithm.
    
    Step 1: Build a Max-Heap from the unsorted array (O(N)).
    Step 2: Repeatedly extract the root (maximum element), place it at the end
            of the array, and restore heap property for the remaining sub-array (O(N log N)).
            
    Args:
        arr: List of comparable elements.
        ascending: True for non-decreasing order, False for non-increasing order.
        
    Returns:
        The sorted list (modified in-place and returned for convenience).
    """
    n = len(arr)
    if n <= 1:
        return arr

    if ascending:
        # Step 1: Build Max-Heap from the bottom-most internal nodes up to root
        # Last non-leaf node is at index (n // 2) - 1
        for i in range(n // 2 - 1, -1, -1):
            heapify(arr, n, i)

        # Step 2: One by one extract elements from the heap
        for i in range(n - 1, 0, -1):
            # Move current maximum root to the end
            temp = arr[0]
            arr[0] = arr[i]
            arr[i] = temp

            # Call heapify on the reduced heap
            heapify(arr, i, 0)
    else:
        # Step 1: Build Min-Heap
        for i in range(n // 2 - 1, -1, -1):
            heapify_min(arr, n, i)

        # Step 2: Extract elements
        for i in range(n - 1, 0, -1):
            temp = arr[0]
            arr[0] = arr[i]
            arr[i] = temp

            heapify_min(arr, i, 0)

    return arr


def heap_sort_requests(
    requests: List[Dict[str, Any]],
    key: str = "priority_score",
    reverse: bool = True,
    collect_trace: bool = False
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Sorts emergency requests or resource dictionaries using Heap Sort.
    
    Args:
        requests: List of request dictionaries.
        key: Dictionary attribute to sort by (e.g. 'priority_score', 'id').
        reverse: If True, higher values appear first (e.g. highest priority first).
        collect_trace: If True, captures intermediate steps for the DSA Lab UI.
        
    Returns:
        (sorted_requests, trace_steps)
    """
    if not requests:
        return [], []

    # Make a shallow copy of dictionaries to avoid mutating original list order outside
    arr = list(requests)
    n = len(arr)
    trace: List[Dict[str, Any]] = []

    if collect_trace:
        trace.append({
            "step": 0,
            "action": f"Initial array before Heap Sort ({n} items)",
            "state": [r.get(key, 0) for r in arr]
        })

    def get_val(item: Dict[str, Any]) -> Any:
        return item.get(key, 0)

    def is_greater(item_a: Dict[str, Any], item_b: Dict[str, Any]) -> bool:
        val_a = get_val(item_a)
        val_b = get_val(item_b)
        # If reverse is True (descending), build min-heap so root moves to end producing descending
        if reverse:
            return val_a < val_b
        return val_a > val_b

    def sift_down(arr_ref: List[Dict[str, Any]], heap_size: int, root_idx: int) -> None:
        idx = root_idx
        while True:
            candidate = idx
            left = 2 * idx + 1
            right = 2 * idx + 2

            if left < heap_size and is_greater(arr_ref[left], arr_ref[candidate]):
                candidate = left

            if right < heap_size and is_greater(arr_ref[right], arr_ref[candidate]):
                candidate = right

            if candidate != idx:
                temp = arr_ref[idx]
                arr_ref[idx] = arr_ref[candidate]
                arr_ref[candidate] = temp
                idx = candidate
            else:
                break

    # Build heap phase
    for i in range(n // 2 - 1, -1, -1):
        sift_down(arr, n, i)

    if collect_trace:
        trace.append({
            "step": 1,
            "action": "Heap construction phase complete (Heapified array)",
            "state": [r.get(key, 0) for r in arr]
        })

    # Extraction phase
    step_num = 2
    for i in range(n - 1, 0, -1):
        temp = arr[0]
        arr[0] = arr[i]
        arr[i] = temp

        sift_down(arr, i, 0)

        if collect_trace and (step_num <= 10 or i == 1):
            trace.append({
                "step": step_num,
                "action": f"Extracted element to index {i}, restored heap on {i} elements",
                "state": [r.get(key, 0) for r in arr]
            })
            step_num += 1

    return arr, trace
