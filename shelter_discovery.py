"""
Smart Flood Evacuation & Rescue System - Dynamic Shelter Discovery Engine
========================================================================

Discovers potential emergency shelter candidates (schools, community halls,
colleges, stadiums, civic centres) near any geographic coordinates globally
using OpenStreetMap (Overpass API and Nominatim fallback).

Operational Safety Invariants:
-------------------------------
1. All discovered civic structures are marked 'is_verified = False' (unverified).
2. Capacity is set to None / unverified until an authorized official conducts
   a physical structural and safety inspection.
3. Unverified candidates are never assigned to evacuees automatically.
4. Admins can review candidates, inspect distance, and verify/register them
   with operational capacity into the system database.
5. Fails gracefully if external APIs are unreachable or offline.
"""

import math
import logging
from typing import Dict, Any, List, Optional
import requests

from algorithms.merge_sort import merge_sort_by_key

logger = logging.getLogger("SmartFloodShelterDiscovery")

# Default Overpass interpreter mirrors
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SmartFloodRescueSystem/2.0 (Disaster-Response-Evacuation-Coordination)"


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS points in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _query_overpass(lat: float, lon: float, radius_meters: int, timeout_sec: int = 4) -> Optional[List[Dict[str, Any]]]:
    """Queries OpenStreetMap Overpass API for civic facilities within radius."""
    query = f"""[out:json][timeout:{timeout_sec}];
(
  node["amenity"~"school|community_centre|college|university|place_of_worship|social_facility|townhall"](around:{radius_meters}, {lat}, {lon});
  way["amenity"~"school|community_centre|college|university|place_of_worship|social_facility|townhall"](around:{radius_meters}, {lat}, {lon});
);
out center 20;"""

    for mirror in OVERPASS_MIRRORS:
        try:
            resp = requests.post(
                mirror,
                data={"data": query},
                headers={"User-Agent": USER_AGENT},
                timeout=timeout_sec + 2
            )
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])
                candidates = []
                for el in elements:
                    tags = el.get("tags", {})
                    name = tags.get("name")
                    if not name:
                        continue  # Skip unnamed nodes

                    amenity = tags.get("amenity", "civic_building")
                    c_lat = el.get("lat") or el.get("center", {}).get("lat")
                    c_lon = el.get("lon") or el.get("center", {}).get("lon")
                    if c_lat is None or c_lon is None:
                        continue

                    dist = haversine_distance(lat, lon, float(c_lat), float(c_lon))
                    address_parts = [
                        tags.get("addr:street"),
                        tags.get("addr:suburb"),
                        tags.get("addr:city")
                    ]
                    clean_address = ", ".join(p for p in address_parts if p) or f"Near {round(c_lat, 4)}, {round(c_lon, 4)}"

                    candidates.append({
                        "name": name.strip(),
                        "amenity_type": amenity.replace("_", " ").title(),
                        "latitude": round(float(c_lat), 5),
                        "longitude": round(float(c_lon), 5),
                        "distance_km": round(dist, 2),
                        "address": clean_address,
                        "is_verified": False,
                        "status": "Potential Candidate (Unverified)",
                        "capacity": None,
                        "contact_phone": tags.get("phone") or tags.get("contact:phone") or None,
                        "source": "OpenStreetMap Overpass",
                        "confidence": "High (Named Civic Structure)"
                    })
                return candidates
        except Exception as e:
            logger.debug("Overpass mirror %s failed: %s", mirror, e)
            continue
    return None


def _query_nominatim(lat: float, lon: float, radius_km: float, max_results: int = 15) -> List[Dict[str, Any]]:
    """Queries OpenStreetMap Nominatim for civic amenities in a bounding box."""
    # Rough degree delta: 1 deg lat ~ 111 km
    delta_deg = max(0.015, radius_km / 111.0)
    viewbox = f"{lon - delta_deg},{lat + delta_deg},{lon + delta_deg},{lat - delta_deg}"

    amenity_queries = ["school", "community centre", "college", "hall"]
    candidates = []
    seen_coords = set()

    for q in amenity_queries:
        if len(candidates) >= max_results:
            break
        try:
            params = {
                "q": q,
                "format": "json",
                "bounded": 1,
                "viewbox": viewbox,
                "limit": 6
            }
            resp = requests.get(
                NOMINATIM_SEARCH_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=4.0
            )
            if resp.status_code == 200:
                results = resp.json()
                for item in results:
                    c_lat = float(item.get("lat", 0))
                    c_lon = float(item.get("lon", 0))
                    coord_key = (round(c_lat, 3), round(c_lon, 3))
                    if coord_key in seen_coords:
                        continue
                    seen_coords.add(coord_key)

                    dist = haversine_distance(lat, lon, c_lat, c_lon)
                    if dist > radius_km * 1.5:
                        continue

                    raw_name = item.get("name") or item.get("display_name", "").split(",")[0]
                    candidates.append({
                        "name": raw_name.strip(),
                        "amenity_type": item.get("type", "Civic Facility").replace("_", " ").title(),
                        "latitude": round(c_lat, 5),
                        "longitude": round(c_lon, 5),
                        "distance_km": round(dist, 2),
                        "address": item.get("display_name", "")[:90],
                        "is_verified": False,
                        "status": "Potential Candidate (Unverified)",
                        "capacity": None,
                        "contact_phone": None,
                        "source": "OpenStreetMap Nominatim",
                        "confidence": "Medium (Civic Structure)"
                    })
        except Exception as e:
            logger.debug("Nominatim query '%s' failed: %s", q, e)
            continue

    return candidates


def discover_potential_shelters(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    max_results: int = 15,
    existing_shelters: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Discovers civic buildings near coordinates that can serve as potential emergency shelters.

    Returns structured dict with candidates sorted by distance, with verification flags.
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
        radius_km = max(0.5, min(float(radius_km), 25.0))
    except (ValueError, TypeError):
        return {
            "success": False,
            "message": "Valid latitude and longitude coordinates required for shelter discovery.",
            "candidates": []
        }

    radius_meters = int(radius_km * 1000)
    candidates: List[Dict[str, Any]] = []
    source_used = "OpenStreetMap"

    # Step 1: Attempt Overpass
    overpass_candidates = _query_overpass(lat, lon, radius_meters, timeout_sec=4)
    if overpass_candidates is not None:
        candidates = overpass_candidates
        source_used = "OpenStreetMap Overpass API"
    else:
        # Step 2: Fallback to Nominatim bounded search
        logger.info("Overpass timed out or unreachable. Falling back to Nominatim amenity search.")
        candidates = _query_nominatim(lat, lon, radius_km, max_results=max_results)
        source_used = "OpenStreetMap Nominatim Engine"

    # Deduplicate against existing official shelters in the database
    existing_coords = set()
    if existing_shelters:
        for s in existing_shelters:
            s_lat = s.get("latitude")
            s_lon = s.get("longitude")
            if s_lat is not None and s_lon is not None:
                existing_coords.add((round(float(s_lat), 3), round(float(s_lon), 3)))

    filtered_candidates = []
    seen_names = set()
    for c in candidates:
        coord_key = (round(c["latitude"], 3), round(c["longitude"], 3))
        name_key = c["name"].lower()
        if coord_key in existing_coords:
            continue  # Already a registered shelter
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        filtered_candidates.append(c)

    # Sort by distance using manual Merge Sort (replaces built-in list.sort())
    filtered_candidates = merge_sort_by_key(filtered_candidates, key="distance_km")
    filtered_candidates = filtered_candidates[:max_results]

    status_note = (
        f"Discovered {len(filtered_candidates)} potential candidate structures within {radius_km} km. "
        "These buildings require field verification and capacity assignment before deployment."
    ) if filtered_candidates else f"No unverified civic facilities found within {radius_km} km via {source_used}."

    return {
        "success": True,
        "search_center": {"latitude": lat, "longitude": lon},
        "radius_km": radius_km,
        "count": len(filtered_candidates),
        "source": source_used,
        "message": status_note,
        "candidates": filtered_candidates,
        "disclaimer": (
            "SAFETY NOTICE: OpenStreetMap candidate facilities are unverified public structures. "
            "They are NOT confirmed emergency shelters and possess NO pre-allocated occupancy. "
            "Response coordinators must verify safety, access, and facilities before assigning evacuees."
        )
    }
