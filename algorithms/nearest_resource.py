"""
Smart Flood Rescue System - Single-Pass Nearest-Resource Selection
===================================================================

Manual single-pass selection algorithm to identify the closest eligible rescue team
or evacuation shelter to an emergency location.

Replaces unnecessary full-array sorting (e.g. sorted() running in O(N log N))
with a linear scan tracking the minimum distance candidate.

Time Complexity:  O(N) single-pass scan
Space Complexity: O(1) auxiliary space (excluding candidate list)
"""

import math
from typing import Any, Callable, Dict, List, Optional, Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def find_nearest_available_team(
    emergency: Dict[str, Any],
    teams: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Finds the nearest available rescue team to an emergency location using single-pass O(N) scan.

    Preserves:
    - Status verification ('Available')
    - Coordinate presence and validation
    - Returns None if emergency lacks GPS or if no eligible teams exist.

    Args:
        emergency: Dictionary/Row representing the emergency request (with 'latitude', 'longitude').
        teams: List of rescue team dictionaries/Rows.

    Returns:
        The nearest eligible team dict/Row, or None if none eligible.
    """
    if not emergency:
        return None

    try:
        e_lat = float(emergency.get("latitude"))
        e_lon = float(emergency.get("longitude"))
    except (ValueError, TypeError):
        return None

    best_team: Optional[Dict[str, Any]] = None
    min_distance = float("inf")

    # Single-pass linear selection: O(N) time, O(1) space
    for t in teams:
        # 1. Eligibility Check: Status must be Available
        status = str(t.get("status", "")).strip().capitalize()
        if status != "Available":
            continue

        # 2. Coordinate Validation
        try:
            t_lat = float(t.get("latitude"))
            t_lon = float(t.get("longitude"))
        except (ValueError, TypeError):
            continue

        # 3. Calculate spatial distance
        dist = haversine_distance(e_lat, e_lon, t_lat, t_lon)

        # 4. Invariant: Maintain pointer to minimum distance candidate
        if dist < min_distance:
            min_distance = dist
            best_team = t

    return best_team


def find_nearest_suitable_shelter(
    emergency: Dict[str, Any],
    shelters: List[Dict[str, Any]],
    required_capacity: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Finds the nearest verified evacuation shelter with sufficient remaining capacity using O(N) scan.

    Preserves:
    - is_verified == 1 requirement
    - Strict capacity check: (capacity - occupied) >= required_capacity
    - Coordinate presence and validation
    - Returns None if no eligible shelter is found.

    Args:
        emergency: Dictionary/Row with 'latitude', 'longitude', and optional 'people'.
        shelters: List of shelter dictionaries/Rows.
        required_capacity: Explicit number of occupants needed. If None, derived from emergency['people'].

    Returns:
        The nearest eligible shelter dict/Row, or None if none eligible.
    """
    if not emergency:
        return None

    try:
        e_lat = float(emergency.get("latitude"))
        e_lon = float(emergency.get("longitude"))
    except (ValueError, TypeError):
        return None

    if required_capacity is not None:
        needed = max(1, int(required_capacity))
    else:
        try:
            needed = max(1, int(emergency.get("people", 1) or 1))
        except (ValueError, TypeError):
            needed = 1

    best_shelter: Optional[Dict[str, Any]] = None
    min_distance = float("inf")

    # Single-pass linear selection: O(N) time, O(1) space
    for s in shelters:
        # 1. Eligibility Check: Must be verified by emergency management
        is_verified = s.get("is_verified")
        if not is_verified:
            continue

        # 2. Capacity Check: Non-exceedance invariant
        try:
            cap = int(s.get("capacity", 0) or 0)
            occ = int(s.get("occupied", 0) or 0)
        except (ValueError, TypeError):
            continue

        if (cap - occ) < needed:
            continue

        # 3. Coordinate Validation
        try:
            s_lat = float(s.get("latitude"))
            s_lon = float(s.get("longitude"))
        except (ValueError, TypeError):
            continue

        # 4. Calculate spatial distance
        dist = haversine_distance(e_lat, e_lon, s_lat, s_lon)

        # 5. Invariant: Maintain minimum distance candidate
        if dist < min_distance:
            min_distance = dist
            best_shelter = s

    return best_shelter


def find_nearest_resource(
    origin_lat: float,
    origin_lon: float,
    candidates: List[Dict[str, Any]],
    filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None
) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Generic single-pass selection algorithm to find the closest candidate to a GPS point.

    Returns:
        (nearest_candidate, distance_km) or (None, float('inf'))
    """
    best_candidate: Optional[Dict[str, Any]] = None
    min_dist = float("inf")

    for c in candidates:
        if filter_func and not filter_func(c):
            continue

        try:
            c_lat = float(c.get("latitude"))
            c_lon = float(c.get("longitude"))
        except (ValueError, TypeError):
            continue

        dist = haversine_distance(origin_lat, origin_lon, c_lat, c_lon)
        if dist < min_dist:
            min_dist = dist
            best_candidate = c

    return best_candidate, min_dist
