"""
Smart Flood Rescue System - Binary Search Algorithm Implementation
===================================================================

Manual iterative Binary Search implementation for emergency request ID lookup.
Precondition: Input list must be sorted in ascending order by the search key ('id').

Time Complexity:
    Best Case:    O(1)        (Target located at initial midpoint)
    Average Case: O(log N)
    Worst Case:   O(log N)    (Target at extremes or absent)
Space Complexity: O(1)        (Iterative implementation, in-place index pointers)
"""

from typing import Any, Dict, List, Optional, Tuple


def is_sorted_by_id(requests: List[Dict[str, Any]]) -> bool:
    """Verifies whether the list of requests is strictly sorted in ascending order of ID."""
    for i in range(len(requests) - 1):
        id_curr = requests[i].get("id", 0)
        id_next = requests[i + 1].get("id", 0)
        if id_curr > id_next:
            return False
    return True


def binary_search_request_by_id(
    sorted_requests: List[Dict[str, Any]],
    target_id: int,
    collect_trace: bool = False
) -> Tuple[Optional[Dict[str, Any]], int, List[Dict[str, Any]]]:
    """
    Searches for a specific emergency rescue request by its unique integer ID.

    Args:
        sorted_requests: List of request dictionaries sorted ascending by 'id'.
        target_id: The integer ID of the emergency request being retrieved.
        collect_trace: If True, records each step for interactive UI visualization.

    Returns:
        (found_request, comparison_steps, trace_history)
        - found_request is None if the target ID is not in the list.
    """
    trace: List[Dict[str, Any]] = []
    steps = 0

    if not sorted_requests:
        return None, steps, trace

    try:
        target = int(target_id)
    except (ValueError, TypeError):
        return None, steps, trace

    low = 0
    high = len(sorted_requests) - 1

    while low <= high:
        steps += 1
        mid = (low + high) // 2
        mid_item = sorted_requests[mid]
        mid_id = mid_item.get("id")

        if mid_id is None:
            # Skip invalid item if ID is absent
            break

        step_info = {
            "step": steps,
            "low": low,
            "high": high,
            "mid": mid,
            "mid_id": mid_id,
            "target_id": target,
        }

        if mid_id == target:
            step_info["status"] = "MATCH_FOUND"
            step_info["action"] = f"Target ID {target} located at index {mid}."
            if collect_trace:
                trace.append(step_info)
            return mid_item, steps, trace

        elif mid_id < target:
            step_info["status"] = "SEARCH_RIGHT"
            step_info["action"] = f"Mid ID {mid_id} < Target {target}; shifting low pointer to {mid + 1}."
            if collect_trace:
                trace.append(step_info)
            low = mid + 1

        else:
            step_info["status"] = "SEARCH_LEFT"
            step_info["action"] = f"Mid ID {mid_id} > Target {target}; shifting high pointer to {mid - 1}."
            if collect_trace:
                trace.append(step_info)
            high = mid - 1

    if collect_trace:
        trace.append({
            "step": steps + 1,
            "low": low,
            "high": high,
            "status": "NOT_FOUND",
            "action": f"Search interval exhausted. Request ID {target} does not exist."
        })

    return None, steps, trace


def binary_search_ids(
    sorted_ids: List[int],
    target_id: int
) -> Tuple[int, int]:
    """
    Generic iterative binary search on a sorted integer list.

    Returns:
        (found_index, steps_taken)
        - found_index is -1 if target is not found.
    """
    if not sorted_ids:
        return -1, 0

    low = 0
    high = len(sorted_ids) - 1
    steps = 0

    while low <= high:
        steps += 1
        mid = (low + high) // 2
        mid_val = sorted_ids[mid]

        if mid_val == target_id:
            return mid, steps
        elif mid_val < target_id:
            low = mid + 1
        else:
            high = mid - 1

    return -1, steps
