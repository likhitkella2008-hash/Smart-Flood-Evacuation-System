"""
Smart Flood Evacuation & Rescue System - Safe Evacuation Route Planner
======================================================================

Route planning engine for emergency evacuation and rescue dispatch.
Combines NetworkX road network graph Dijkstra algorithm with hazard avoidance
penalties, alongside fallback to OpenStreetMap / OSRM public routing.

Safety Invariants:
------------------
- Never assumes a road is completely safe.
- Marks all paths as "Unverified suggested route".
- Incorporates dynamic penalties for confirmed flooded or closed road segments.
- If road segments are confirmed impassable, calculates safe detours.
- Provides fallback waypoint corridors if routing telemetry is offline.
"""

import math
import requests
from typing import Dict, Any, List, Optional, Tuple
import networkx as nx

# Regional Road Transit Nodes for Greater Coimbatore Emergency Network
COIMBATORE_ROAD_NODES = {
    "gandhipuram_hub": {"lat": 11.0183, "lon": 76.9725, "name": "Gandhipuram Hub"},
    "cross_cut_rd": {"lat": 11.0210, "lon": 76.9680, "name": "Cross Cut Road Jn"},
    "rs_puram_east": {"lat": 11.0089, "lon": 76.9550, "name": "RS Puram East"},
    "db_road_center": {"lat": 11.0085, "lon": 76.9485, "name": "DB Road RS Puram"},
    "town_hall": {"lat": 10.9980, "lon": 76.9610, "name": "Town Hall Junction"},
    "ukkadam_stand": {"lat": 10.9904, "lon": 76.9602, "name": "Ukkadam Bus Terminal"},
    "sungam_bypass": {"lat": 10.9970, "lon": 76.9780, "name": "Sungam Bypass Jn"},
    "trichy_rd_ramanathapuram": {"lat": 10.9950, "lon": 76.9930, "name": "Trichy Road Ramanathapuram"},
    "singanallur_hub": {"lat": 10.9990, "lon": 77.0220, "name": "Singanallur Junction"},
    "avinashi_rd_peelamedu": {"lat": 11.0280, "lon": 77.0010, "name": "Avinashi Rd Peelamedu"},
    "coimbatore_junction": {"lat": 10.9985, "lon": 76.9675, "name": "Coimbatore Main Railway Station"},
    "sundarapuram_nh": {"lat": 10.9490, "lon": 76.9710, "name": "Sundarapuram NH"},
    "palakkad_rd_kuniyamuthur": {"lat": 10.9630, "lon": 76.9450, "name": "Kuniyamuthur Palakkad Rd"},
    "ettimadai_amrita_gate": {"lat": 10.9020, "lon": 76.9030, "name": "Amrita Ettimadai Emergency Hub"}
}

# Road segments (bidirectional edges) with baseline distances in km
COIMBATORE_ROAD_EDGES = [
    ("gandhipuram_hub", "cross_cut_rd", 0.6),
    ("cross_cut_rd", "rs_puram_east", 1.8),
    ("rs_puram_east", "db_road_center", 0.8),
    ("gandhipuram_hub", "town_hall", 2.4),
    ("town_hall", "coimbatore_junction", 0.9),
    ("town_hall", "ukkadam_stand", 1.2),
    ("town_hall", "sungam_bypass", 2.0),
    ("gandhipuram_hub", "sungam_bypass", 2.5),
    ("sungam_bypass", "trichy_rd_ramanathapuram", 1.8),
    ("trichy_rd_ramanathapuram", "singanallur_hub", 3.2),
    ("gandhipuram_hub", "avinashi_rd_peelamedu", 3.5),
    ("avinashi_rd_peelamedu", "singanallur_hub", 4.1),
    ("ukkadam_stand", "palakkad_rd_kuniyamuthur", 3.8),
    ("palakkad_rd_kuniyamuthur", "ettimadai_amrita_gate", 9.2),
    ("ukkadam_stand", "sundarapuram_nh", 5.2),
    ("sundarapuram_nh", "ettimadai_amrita_gate", 11.0),
    ("rs_puram_east", "town_hall", 1.5),
    ("db_road_center", "palakkad_rd_kuniyamuthur", 5.6)
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in kilometers."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_node(lat: float, lon: float) -> Tuple[str, float]:
    """Finds the closest road network node to a given coordinate."""
    best_node = None
    min_dist = float("inf")
    for node_id, data in COIMBATORE_ROAD_NODES.items():
        d = haversine_distance(lat, lon, data["lat"], data["lon"])
        if d < min_dist:
            min_dist = d
            best_node = node_id
    return best_node, min_dist


def build_disaster_graph(active_hazards: Optional[List[Dict[str, Any]]] = None) -> nx.Graph:
    """
    Constructs a NetworkX graph with hazard penalties applied to edges.
    """
    G = nx.Graph()

    for node_id, data in COIMBATORE_ROAD_NODES.items():
        G.add_node(node_id, **data)

    hazards = active_hazards or []

    for u, v, base_dist in COIMBATORE_ROAD_EDGES:
        u_data = COIMBATORE_ROAD_NODES[u]
        v_data = COIMBATORE_ROAD_NODES[v]
        mid_lat = (u_data["lat"] + v_data["lat"]) / 2.0
        mid_lon = (u_data["lon"] + v_data["lon"]) / 2.0

        weight = base_dist
        hazard_note = None
        impassable = False

        for h in hazards:
            h_lat = h.get("latitude")
            h_lon = h.get("longitude")
            if h_lat is not None and h_lon is not None:
                d_hazard = haversine_distance(mid_lat, mid_lon, float(h_lat), float(h_lon))
                # Hazard within 1.5 km of road segment midpoint
                if d_hazard <= 1.5:
                    sev = str(h.get("severity", "")).lower()
                    if "closed" in sev or "flooded" in sev:
                        # Heavy penalty (100x distance) to avoid unless no other option
                        weight *= 100.0
                        hazard_note = f"Segment {u} - {v} near reported flooding ({h.get('name', 'Hazard')})"
                    elif "caution" in sev:
                        weight *= 3.0
                        hazard_note = f"Segment {u} - {v} under caution ({h.get('name', 'Hazard')})"

        G.add_edge(u, v, weight=weight, base_distance=base_dist, hazard_note=hazard_note)

    return G


def try_osrm_routing(start_lat: float, start_lon: float, dest_lat: float, dest_lon: float) -> Optional[Dict[str, Any]]:
    """
    Attempts to fetch real-world driving geometry from the public OpenStreetMap OSRM API.
    Fails safely if internet/OSRM is unreachable.
    """
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{start_lon},{start_lat};{dest_lon},{dest_lat}"
            f"?overview=full&geometries=geojson"
        )
        resp = requests.get(url, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("routes") and len(data["routes"]) > 0:
                route = data["routes"][0]
                geometry = route.get("geometry", {}).get("coordinates", [])
                # Convert [lon, lat] pairs to [lat, lon] for Leaflet
                leaflet_coords = [[pt[1], pt[0]] for pt in geometry]
                distance_km = route.get("distance", 0) / 1000.0
                duration_min = route.get("duration", 0) / 60.0
                return {
                    "coordinates": leaflet_coords,
                    "distance_km": round(distance_km, 2),
                    "duration_min": round(duration_min, 1),
                    "engine": "OpenStreetMap / OSRM Live Road Network"
                }
    except Exception:
        pass
    return None


def plan_evacuation_route(
    start_lat: float,
    start_lon: float,
    shelter_lat: float,
    shelter_lon: float,
    shelter_name: str,
    active_hazards: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Calculates the safest evacuation path from citizen to shelter.
    Applies Dijkstra graph routing with hazard penalties and falls back gracefully.
    """
    warnings: List[str] = [
        "Unverified suggested route. Conditions may change rapidly during floods.",
        "Never attempt to drive or walk through moving floodwaters."
    ]

    try:
        start_lat = float(start_lat)
        start_lon = float(start_lon)
        shelter_lat = float(shelter_lat)
        shelter_lon = float(shelter_lon)
    except (ValueError, TypeError):
        return {
            "success": False,
            "message": "Invalid or missing coordinates for route planning."
        }

    # First attempt: Try real-world OSRM route
    osrm_result = try_osrm_routing(start_lat, start_lon, shelter_lat, shelter_lon)

    # Second: Calculate with NetworkX emergency graph for hazard analysis
    G = build_disaster_graph(active_hazards)
    start_node, d_start = find_nearest_node(start_lat, start_lon)
    end_node, d_end = find_nearest_node(shelter_lat, shelter_lon)

    graph_coords: List[List[float]] = [[start_lat, start_lon]]
    total_km = d_start
    hazard_alerts: List[str] = []

    try:
        path = nx.dijkstra_path(G, start_node, end_node, weight="weight")
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            edge_data = G[u][v]
            total_km += edge_data.get("base_distance", 1.0)
            if edge_data.get("hazard_note"):
                hazard_alerts.append(edge_data["hazard_note"])

        for node_id in path:
            nd = COIMBATORE_ROAD_NODES[node_id]
            graph_coords.append([nd["lat"], nd["lon"]])

        graph_coords.append([shelter_lat, shelter_lon])
        total_km += d_end

    except nx.NetworkXNoPath:
        # If no path in graph, fallback to straight corridor
        graph_coords = [[start_lat, start_lon], [shelter_lat, shelter_lon]]
        total_km = haversine_distance(start_lat, start_lon, shelter_lat, shelter_lon)
        warnings.append("No viable path on regional road network. Corridor line displayed.")

    if hazard_alerts:
        for alert in hazard_alerts:
            warnings.append(f"Hazard Alert: {alert}")

    # Determine final route geometry
    if osrm_result and not hazard_alerts:
        # Use high-resolution OSRM road geometry when safe
        final_coords = osrm_result["coordinates"]
        final_distance = osrm_result["distance_km"]
        final_duration = osrm_result["duration_min"]
        engine_label = osrm_result["engine"]
    else:
        # Use graph Dijkstra route avoiding hazards
        final_coords = graph_coords
        final_distance = round(total_km, 2)
        # Wet flood conditions: average 25 km/h
        final_duration = round((total_km / 25.0) * 60.0, 1)
        engine_label = "NetworkX Hazard-Aware Dijkstra Emergency Engine"

    return {
        "success": True,
        "shelter_name": shelter_name,
        "start": [start_lat, start_lon],
        "destination": [shelter_lat, shelter_lon],
        "route_coordinates": final_coords,
        "distance_km": final_distance,
        "estimated_duration_min": final_duration,
        "engine": engine_label,
        "warnings": warnings,
        "hazard_alerts": hazard_alerts
    }
