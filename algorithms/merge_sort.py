"""
Smart Flood Rescue System - Merge Sort Algorithm Implementation
================================================================

Manual recursive Merge Sort implementation for emergency rescue requests.
No built-in sorted(), list.sort(), or SQL ORDER BY used for algorithmic ordering.

Priority Ordering Hierarchy:
1. Priority Category: Critical (Rank 1) > High (Rank 2) > Medium (Rank 3) > Low (Rank 4)
2. Priority Score: Higher numerical score (0 - 100) first within the same category
3. Tie-breaker: Earlier submission time (created_at) or lower request ID first
"""

from typing import Any, Callable, Dict, List, Optional


# Canonical category priority rank mapping (lower numerical rank = higher urgency)
PRIORITY_CATEGORY_RANKS: Dict[str, int] = {
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4,
}


def get_priority_rank(category: Optional[str]) -> int:
    """Returns numerical rank for a priority category (1=Critical ... 4=Low)."""
    if not category:
        return 99
    return PRIORITY_CATEGORY_RANKS.get(str(category).strip().upper(), 99)


def compare_emergency_requests(req_a: Dict[str, Any], req_b: Dict[str, Any]) -> int:
    """
    Compares two emergency request dictionaries for priority ordering.

    Returns:
        -1 if req_a has HIGHER priority than req_b (a should come before b)
        +1 if req_b has HIGHER priority than req_a (b should come before a)
         0 if req_a and req_b are exactly tied in priority
    """
    # 1. Compare Category Rank (Critical=1 < High=2 < Medium=3 < Low=4)
    rank_a = get_priority_rank(req_a.get("priority"))
    rank_b = get_priority_rank(req_b.get("priority"))
    if rank_a < rank_b:
        return -1
    elif rank_a > rank_b:
        return 1

    # 2. Compare Numerical Priority Score (higher score first -> descending)
    try:
        score_a = float(req_a.get("priority_score", 0.0) or 0.0)
    except (ValueError, TypeError):
        score_a = 0.0

    try:
        score_b = float(req_b.get("priority_score", 0.0) or 0.0)
    except (ValueError, TypeError):
        score_b = 0.0

    if score_a > score_b:
        return -1
    elif score_a < score_b:
        return 1

    # 3. Tie-breaker: Earlier submission timestamp (created_at ascending)
    created_a = str(req_a.get("created_at") or "")
    created_b = str(req_b.get("created_at") or "")
    if created_a and created_b and created_a != created_b:
        return -1 if created_a < created_b else 1

    # 4. Tie-breaker: Lower request ID (first submitted / FIFO in tie)
    try:
        id_a = int(req_a.get("id", 0) or 0)
    except (ValueError, TypeError):
        id_a = 0

    try:
        id_b = int(req_b.get("id", 0) or 0)
    except (ValueError, TypeError):
        id_b = 0

    if id_a < id_b:
        return -1
    elif id_a > id_b:
        return 1

    return 0


def _merge_emergency_lists(
    left: List[Dict[str, Any]], right: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Merges two sorted lists of emergency requests into a single sorted list."""
    merged: List[Dict[str, Any]] = []
    i = 0
    j = 0

    # Two-pointer linear merge step: O(len(left) + len(right))
    while i < len(left) and j < len(right):
        cmp = compare_emergency_requests(left[i], right[j])
        if cmp <= 0:
            # left[i] has higher or equal priority -> preserve stability
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    # Append remaining elements from either half
    while i < len(left):
        merged.append(left[i])
        i += 1

    while j < len(right):
        merged.append(right[j])
        j += 1

    return merged


def merge_sort_requests(requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Performs recursive divide-and-conquer Merge Sort on emergency rescue requests.

    Time Complexity:
        Best Case:    O(N log N)
        Average Case: O(N log N)
        Worst Case:   O(N log N)
    Space Complexity: O(N) auxiliary space

    Args:
        requests: List of emergency request dictionaries.

    Returns:
        A new list containing all requests sorted by triage urgency.
    """
    if len(requests) <= 1:
        return list(requests)

    mid = len(requests) // 2
    left_sorted = merge_sort_requests(requests[:mid])
    right_sorted = merge_sort_requests(requests[mid:])

    return _merge_emergency_lists(left_sorted, right_sorted)


def merge_sort_by_key(
    items: List[Dict[str, Any]],
    key: str = "id",
    reverse: bool = False
) -> List[Dict[str, Any]]:
    """
    Generic manual Merge Sort for dictionaries by a specific dictionary key.
    Used to sort requests by ID for Binary Search without using built-ins.
    """
    if len(items) <= 1:
        return list(items)

    mid = len(items) // 2
    left = merge_sort_by_key(items[:mid], key=key, reverse=reverse)
    right = merge_sort_by_key(items[mid:], key=key, reverse=reverse)

    merged: List[Dict[str, Any]] = []
    i = j = 0

    while i < len(left) and j < len(right):
        val_left = left[i].get(key)
        val_right = right[j].get(key)

        # Handle None comparisons safely
        if val_left is None and val_right is not None:
            take_left = False
        elif val_right is None and val_left is not None:
            take_left = True
        elif val_left is None and val_right is None:
            take_left = True
        else:
            if not reverse:
                take_left = val_left <= val_right
            else:
                take_left = val_left >= val_right

        if take_left:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    while i < len(left):
        merged.append(left[i])
        i += 1
    while j < len(right):
        merged.append(right[j])
        j += 1

    return merged
