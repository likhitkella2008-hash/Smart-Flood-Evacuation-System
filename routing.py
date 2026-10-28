"""
Smart Flood Evacuation & Rescue System - Safe Evacuation Route Planner
======================================================================

Multi-location, hazard-aware route planning engine for emergency evacuation
and rescue dispatch across any geographical coordinates.

Combines:
1. Public OpenStreetMap / OSRM live road network geometry.
2. Active road hazard spatial collision detection and automated detour routing.
3. Offline NetworkX Dijkstra topological graphs (with regional Coimbatore transit
   nodes and dynamic waypoint networks for all other global regions).

Safety Invariants:
------------------
- Never assumes any road is completely safe.
- Marks all paths as 'Unverified suggested route'.
- Dynamically penalizes edges near active flood hazard reports.
- Dispatches detours around confirmed closed/flooded road segments.
- Transparently alerts user if unrecorded hazard risk is present.
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple
import networkx as nx
import requests

from algorithms.dijkstra import AdjacencyListGraph, dijkstra_shortest_path

logger = logging.getLogger("SmartFloodRouting")

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
    """Calculates great-circle distance in kilometers between two GPS points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def is_in_coimbatore_region(lat: float, lon: float) -> bool:
    """Checks whether coordinates fall within Greater Coimbatore metropolitan area."""
    return 10.75 <= lat <= 11.25 and 76.75 <= lon <= 77.25


def find_nearest_node(lat: float, lon: float, node_dict: Optional[Dict[str, Dict[str, Any]]] = None) -> Tuple[str, float]:
    """Finds the closest road network node to a given coordinate."""
    nodes = node_dict or COIMBATORE_ROAD_NODES
    best_node = None
    min_dist = float("inf")
    for node_id, data in nodes.items():
        d = haversine_distance(lat, lon, data["lat"], data["lon"])
        if d < min_dist:
            min_dist = d
            best_node = node_id
    return best_node, min_dist


def check_route_hazards(
    coordinates: List[List[float]],
    hazards: Optional[List[Dict[str, Any]]],
    threshold_km: float = 0.8
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Checks if a polyline trajectory intersects or approaches active road hazards.
    Returns list of textual alert warnings and list of interfering hazard dicts.
    """
    if not coordinates or not hazards:
        return [], []

    alerts: List[str] = []
    conflicts: List[Dict[str, Any]] = []

    for h in hazards:
        h_lat = h.get("latitude")
        h_lon = h.get("longitude")
        if h_lat is None or h_lon is None:
            continue

        try:
            hl = float(h_lat)
            hn = float(h_lon)
        except (ValueError, TypeError):
            continue

        min_d = min(haversine_distance(pt[0], pt[1], hl, hn) for pt in coordinates)
        if min_d <= threshold_km:
            sev = str(h.get("severity", "Caution")).strip()
            name = h.get("name", "Reported Road Obstruction")
            desc = h.get("description", "")
            alerts.append(f"Hazard Alert: Route passes within {min_d:.2f} km of {sev} segment: '{name}' ({desc})")
            conflicts.append({
                "hazard": h,
                "distance_km": round(min_d, 2),
                "severity": sev,
                "latitude": hl,
                "longitude": hn
            })

    return alerts, conflicts


def build_disaster_graph(active_hazards: Optional[List[Dict[str, Any]]] = None) -> nx.Graph:
    """
    Constructs Coimbatore regional NetworkX graph with hazard penalties applied to edges.
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

        for h in hazards:
            h_lat = h.get("latitude")
            h_lon = h.get("longitude")
            if h_lat is not None and h_lon is not None:
                d_hazard = haversine_distance(mid_lat, mid_lon, float(h_lat), float(h_lon))
                if d_hazard <= 1.5:
                    sev = str(h.get("severity", "")).lower()
                    if "closed" in sev or "flooded" in sev:
                        weight *= 100.0
                        hazard_note = f"Segment {u} - {v} near reported flooding ({h.get('name', 'Hazard')})"
                    elif "caution" in sev:
                        weight *= 3.0
                        hazard_note = f"Segment {u} - {v} under caution ({h.get('name', 'Hazard')})"

        G.add_edge(u, v, weight=weight, base_distance=base_dist, hazard_note=hazard_note)

    return G


def build_manual_disaster_graph(active_hazards: Optional[List[Dict[str, Any]]] = None) -> AdjacencyListGraph:
    """
    Constructs Coimbatore regional AdjacencyListGraph with hazard penalties applied to edges.
    Powers manual Dijkstra algorithm without external graph library dependencies.
    """
    graph = AdjacencyListGraph(directed=False)

    for node_id, data in COIMBATORE_ROAD_NODES.items():
        graph.add_node(node_id, **data)

    hazards = active_hazards or []

    for u, v, base_dist in COIMBATORE_ROAD_EDGES:
        u_data = COIMBATORE_ROAD_NODES[u]
        v_data = COIMBATORE_ROAD_NODES[v]
        mid_lat = (u_data["lat"] + v_data["lat"]) / 2.0
        mid_lon = (u_data["lon"] + v_data["lon"]) / 2.0

        weight = base_dist
        hazard_note = None

        for h in hazards:
            h_lat = h.get("latitude")
            h_lon = h.get("longitude")
            if h_lat is not None and h_lon is not None:
                d_hazard = haversine_distance(mid_lat, mid_lon, float(h_lat), float(h_lon))
                if d_hazard <= 1.5:
                    sev = str(h.get("severity", "")).lower()
                    if "closed" in sev or "flooded" in sev:
                        weight *= 100.0
                        hazard_note = f"Segment {u} - {v} near reported flooding ({h.get('name', 'Hazard')})"
                    elif "caution" in sev:
                        weight *= 3.0
                        hazard_note = f"Segment {u} - {v} under caution ({h.get('name', 'Hazard')})"

        graph.add_edge(u, v, weight=weight, base_distance=base_dist, hazard_note=hazard_note)

    return graph


def build_dynamic_corridor_graph(
    start_lat: float,
    start_lon: float,
    dest_lat: float,
    dest_lon: float,
    active_hazards: Optional[List[Dict[str, Any]]] = None
) -> Tuple[nx.Graph, List[str]]:
    """
    Constructs a location-agnostic dynamic waypoint network between any two GPS points.
    Generates direct corridor nodes plus lateral detour nodes to allow Dijkstra
    to route around active road hazards anywhere globally.
    """
    G = nx.Graph()
    hazards = active_hazards or []

    # Number of steps along the vector
    steps = 4
    d_lat = (dest_lat - start_lat) / float(steps)
    d_lon = (dest_lon - start_lon) / float(steps)

    # Perpendicular lateral offset vector (~1.2 km offset)
    ortho_lat = -d_lon * 0.4
    ortho_lon = d_lat * 0.4

    # 1. Add Start & Destination
    G.add_node("start", lat=start_lat, lon=start_lon, name="Start")
    G.add_node("dest", lat=dest_lat, lon=dest_lon, name="Destination")

    prev_layer = ["start"]

    for i in range(1, steps):
        base_lat = start_lat + (d_lat * i)
        base_lon = start_lon + (d_lon * i)

        c_node = f"w_center_{i}"
        l_node = f"w_left_{i}"
        r_node = f"w_right_{i}"

        G.add_node(c_node, lat=base_lat, lon=base_lon, name=f"Corridor Node {i}")
        G.add_node(l_node, lat=base_lat + ortho_lat, lon=base_lon + ortho_lon, name=f"Detour North/West {i}")
        G.add_node(r_node, lat=base_lat - ortho_lat, lon=base_lon - ortho_lon, name=f"Detour South/East {i}")

        curr_layer = [c_node, l_node, r_node]

        # Connect prev layer to current layer
        for u in prev_layer:
            u_lat = G.nodes[u]["lat"]
            u_lon = G.nodes[u]["lon"]
            for v in curr_layer:
                v_lat = G.nodes[v]["lat"]
                v_lon = G.nodes[v]["lon"]

                dist = haversine_distance(u_lat, u_lon, v_lat, v_lon)
                mid_lat = (u_lat + v_lat) / 2.0
                mid_lon = (u_lon + v_lon) / 2.0

                weight = dist
                note = None

                # Apply hazard penalties
                for h in hazards:
                    h_lat = h.get("latitude")
                    h_lon = h.get("longitude")
                    if h_lat is not None and h_lon is not None:
                        d_h = haversine_distance(mid_lat, mid_lon, float(h_lat), float(h_lon))
                        if d_h <= 1.2:
                            sev = str(h.get("severity", "")).lower()
                            if "closed" in sev or "flooded" in sev:
                                weight *= 80.0
                                note = f"Detour around flooded area: {h.get('name', 'Road Submersion')}"
                            else:
                                weight *= 4.0
                                note = f"Caution near road hazard: {h.get('name', 'Hazard')}"

                G.add_edge(u, v, weight=weight, base_distance=dist, hazard_note=note)

        prev_layer = curr_layer

    # Connect last layer to dest
    dest_lat = G.nodes["dest"]["lat"]
    dest_lon = G.nodes["dest"]["lon"]
    for u in prev_layer:
        u_lat = G.nodes[u]["lat"]
        u_lon = G.nodes[u]["lon"]
        dist = haversine_distance(u_lat, u_lon, dest_lat, dest_lon)
        G.add_edge(u, "dest", weight=dist, base_distance=dist, hazard_note=None)

    # Solve shortest path
    try:
        path = nx.dijkstra_path(G, "start", "dest", weight="weight")
        return G, path
    except Exception:
        return G, ["start", "dest"]


def try_osrm_routing(
    start_lat: float,
    start_lon: float,
    dest_lat: float,
    dest_lon: float,
    via_lat: Optional[float] = None,
    via_lon: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Attempts to fetch real-world driving geometry from OpenStreetMap OSRM API.
    Supports optional intermediate waypoint for detour planning.
    """
    try:
        if via_lat is not None and via_lon is not None:
            coord_str = f"{start_lon},{start_lat};{via_lon},{via_lat};{dest_lon},{dest_lat}"
        else:
            coord_str = f"{start_lon},{start_lat};{dest_lon},{dest_lat}"

        url = f"https://router.project-osrm.org/route/v1/driving/{coord_str}?overview=full&geometries=geojson"
        resp = requests.get(url, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            routes = data.get("routes", [])
            if routes:
                route = routes[0]
                geometry = route.get("geometry", {}).get("coordinates", [])
                leaflet_coords = [[pt[1], pt[0]] for pt in geometry]
                distance_km = route.get("distance", 0) / 1000.0
                duration_min = route.get("duration", 0) / 60.0

                return {
                    "coordinates": leaflet_coords,
                    "distance_km": round(distance_km, 2),
                    "duration_min": round(duration_min, 1),
                    "engine": "OpenStreetMap / OSRM Live Road Network"
                }
    except Exception as e:
        logger.debug("OSRM routing request failed: %s", e)
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
    Calculates the safest evacuation path between any origin and shelter.

    Applies:
    1. Real-world road geometry (OSRM).
    2. Hazard collision detection and automated detour re-routing.
    3. Seamless offline Dijkstra emergency graph fallback for any location worldwide.
    """
    warnings: List[str] = [
        "Unverified suggested route. Conditions may change rapidly during floods.",
        "Never attempt to drive or walk through moving floodwaters."
    ]

    try:
        s_lat = float(start_lat)
        s_lon = float(start_lon)
        d_lat = float(shelter_lat)
        d_lon = float(shelter_lon)
    except (ValueError, TypeError):
        return {
            "success": False,
            "message": "Invalid or missing coordinates for route planning."
        }

    direct_dist = haversine_distance(s_lat, s_lon, d_lat, d_lon)
    hazards = active_hazards or []

    # -------------------------------------------------------------
    # 1. Primary Attempt: Query OSRM
    # -------------------------------------------------------------
    osrm_result = try_osrm_routing(s_lat, s_lon, d_lat, d_lon)
    is_detour_active = False

    if osrm_result and osrm_result.get("coordinates"):
        initial_coords = osrm_result["coordinates"]
        alerts, conflicts = check_route_hazards(initial_coords, hazards, threshold_km=0.8)

        # Check if any conflict is severe (closed or flooded)
        severe_conflicts = [c for c in conflicts if any(w in c["severity"].lower() for w in ["closed", "flooded", "submerged"])]

        if severe_conflicts:
            # Attempt automated detour via orthogonal waypoint away from hazard
            conflict = severe_conflicts[0]
            hz_lat = conflict["latitude"]
            hz_lon = conflict["longitude"]

            # Compute detour waypoint offset
            mid_lat = (s_lat + d_lat) / 2.0
            mid_lon = (s_lon + d_lon) / 2.0
            vec_lat = hz_lat - mid_lat
            vec_lon = hz_lon - mid_lon

            # Shift in the opposite direction of the hazard by ~1.5 km
            norm = math.sqrt(vec_lat**2 + vec_lon**2) or 0.01
            detour_lat = mid_lat - (vec_lat / norm) * 0.015
            detour_lon = mid_lon - (vec_lon / norm) * 0.015

            detour_osrm = try_osrm_routing(s_lat, s_lon, d_lat, d_lon, via_lat=detour_lat, via_lon=detour_lon)
            if detour_osrm and detour_osrm.get("coordinates"):
                d_alerts, d_conflicts = check_route_hazards(detour_osrm["coordinates"], hazards, threshold_km=0.6)
                d_severe = [c for c in d_conflicts if any(w in c["severity"].lower() for w in ["closed", "flooded"])]
                if not d_severe:
                    # Detour successfully bypassed the severe hazard
                    osrm_result = detour_osrm
                    is_detour_active = True
                    warnings.append(
                        f"Detour Route Active: Primary path approached flooded hazard '{conflict['hazard'].get('name', 'Hazard')}'. "
                        "Calculated safe diversion route."
                    )
                    alerts = d_alerts

        for a in alerts:
            warnings.append(a)

        if not alerts and not is_detour_active:
            warnings.append("No known road hazards detected along this corridor based on current emergency dispatch telemetry.")

        return {
            "success": True,
            "shelter_name": shelter_name,
            "start": [s_lat, s_lon],
            "destination": [d_lat, d_lon],
            "route_coordinates": osrm_result["coordinates"],
            "distance_km": osrm_result["distance_km"],
            "estimated_duration_min": osrm_result["duration_min"],
            "engine": f"{osrm_result['engine']} (Detour Safe)" if is_detour_active else osrm_result["engine"],
            "warnings": warnings,
            "hazard_alerts": alerts,
            "detour_active": is_detour_active
        }

    # -------------------------------------------------------------
    # 2. Fallback Attempt: Offline Dijkstra Graph Routing (Manual Engine)
    # -------------------------------------------------------------
    logger.info("OSRM unreachable or offline. Using Offline Dijkstra Routing Engine.")

    if is_in_coimbatore_region(s_lat, s_lon) and is_in_coimbatore_region(d_lat, d_lon):
        # Predefined Coimbatore high-resolution arterial transit network
        start_node, d_start = find_nearest_node(s_lat, s_lon)
        end_node, d_end = find_nearest_node(d_lat, d_lon)

        graph_coords: List[List[float]] = [[s_lat, s_lon]]
        total_km = d_start
        hazard_alerts: List[str] = []

        try:
            # Primary: Manual Dijkstra Shortest Path using AdjacencyListGraph & Binary Min-Heap
            manual_G = build_manual_disaster_graph(hazards)
            dijkstra_res = dijkstra_shortest_path(manual_G, start_node, end_node)

            if dijkstra_res.get("success") and dijkstra_res.get("path"):
                path = dijkstra_res["path"]
                for i in range(len(path) - 1):
                    u, v = path[i], path[i+1]
                    for edge in manual_G.neighbors(u):
                        if edge["to"] == v:
                            total_km += edge.get("base_distance", 1.0)
                            if edge.get("hazard_note"):
                                hazard_alerts.append(edge["hazard_note"])
                            break

                for node_id in path:
                    nd = COIMBATORE_ROAD_NODES[node_id]
                    graph_coords.append([nd["lat"], nd["lon"]])

                graph_coords.append([d_lat, d_lon])
                total_km += d_end
                engine_name = "Manual Binary Min-Heap Dijkstra Engine (Disaster Safe)"
            else:
                raise nx.NetworkXNoPath("No path found via manual Dijkstra")

        except Exception as e:
            # Fallback to NetworkX if manual search encounters an unexpected issue
            logger.warning(f"Manual Dijkstra fallback to NetworkX: {e}")
            G = build_disaster_graph(hazards)
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

                graph_coords.append([d_lat, d_lon])
                total_km += d_end
                engine_name = "NetworkX Coimbatore Arterial Dijkstra Engine (Offline Safe)"

            except nx.NetworkXNoPath:
                graph_coords = [[s_lat, s_lon], [d_lat, d_lon]]
                total_km = direct_dist
                warnings.append("No viable path on regional road network. Corridor line displayed.")
                engine_name = "NetworkX Coimbatore Arterial Dijkstra Engine (Offline Safe)"

    else:
        # Dynamic location-agnostic waypoint corridor (Chennai, Bengaluru, Mumbai, etc.)
        G, path = build_dynamic_corridor_graph(s_lat, s_lon, d_lat, d_lon, hazards)
        graph_coords = []
        total_km = 0.0
        hazard_alerts = []

        for i in range(len(path)):
            node_id = path[i]
            nd = G.nodes[node_id]
            graph_coords.append([nd["lat"], nd["lon"]])
            if i > 0:
                prev_id = path[i-1]
                edge = G[prev_id][node_id]
                total_km += edge.get("base_distance", 1.0)
                if edge.get("hazard_note"):
                    hazard_alerts.append(edge["hazard_note"])

        engine_name = "NetworkX Dynamic Corridor Dijkstra Engine (Global Offline)"

    for ha in hazard_alerts:
        warnings.append(f"Hazard Alert: {ha}")

    if not hazard_alerts:
        warnings.append("No known road hazards detected along this corridor based on current emergency dispatch telemetry.")

    # In wet flood conditions, assume average vehicle/evacuation speed of 25 km/h
    duration_min = round((total_km / 25.0) * 60.0, 1)

    return {
        "success": True,
        "shelter_name": shelter_name,
        "start": [s_lat, s_lon],
        "destination": [d_lat, d_lon],
        "route_coordinates": graph_coords,
        "distance_km": round(total_km, 2),
        "estimated_duration_min": duration_min,
        "engine": engine_name,
        "warnings": warnings,
        "hazard_alerts": hazard_alerts,
        "detour_active": bool(hazard_alerts)
    }
