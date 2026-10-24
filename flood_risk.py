"""
Smart Flood Evacuation & Rescue System - Flood Risk Assessment Engine
=====================================================================

Configurable weighted rule-based scoring model for environmental flood risk.
This model calculates a heuristic risk index (0 to 100) based on real-time
meteorological telemetry from Open-Meteo, citizen-reported field observations,
and topographical vulnerability factors.

Mathematical Model:
-------------------
Risk Score = (w1 * Current_Rain_Score)
           + (w2 * Forecast_Rain_Score)
           + (w3 * Citizen_Reports_Score)
           + (w4 * Terrain_Vulnerability_Score)

Default Weights (Sum = 1.0):
  w1 (Current Rain):       0.25
  w2 (Forecast Rain 24h):  0.35
  w3 (Citizen Reports):    0.25
  w4 (Low-Lying / Terrain):0.15

Score Ranges & Categories:
  0  - 29 : Low Risk      (Normal drainage, monitoring conditions)
  30 - 59 : Moderate Risk (Localized waterlogging, caution advised)
  60 - 79 : High Risk     (Substantial water accumulation, rescue teams alerted)
  80 - 100: Severe Risk   (Critical flood hazard, active evacuation recommended)

Disclaimer:
  This engine is a deterministic heuristic triage index for coordination.
  It does not claim to be a 2D hydrodynamic flood simulation or an ML model.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List


# Known flood-prone / low-lying zones across major metropolitan corridors
KNOWN_VULNERABLE_AREAS = {
    # Coimbatore Metropolitan Area
    "ukkadam": 85.0,        # Lake proximity, low elevation basin
    "singanallur": 75.0,    # Lake overflow vulnerability
    "ramanathapuram": 65.0, # Water stagnation corridor
    "gandhipuram": 50.0,    # Commercial hub, moderate storm-drain runoff
    "rs puram": 40.0,       # Higher ground, better stormwater drainage
    "peelamedu": 45.0,      # Airport corridor, moderate
    "coimbatore": 55.0,     # General metropolitan default

    # Chennai Metropolitan Area (Adyar / Cooum / low-lying basins)
    "velachery": 85.0,      # Marshland proximity, chronic inundation zone
    "mudichur": 85.0,       # Adyar river basin overflow
    "tambaram": 75.0,       # Lake basin runoff
    "saidapet": 75.0,       # Cooum river corridor
    "t nagar": 70.0,        # Low stormwater runoff gradient
    "marina": 60.0,         # Coastal stormwater discharge threshold
    "chennai": 65.0,        # Coastal metropolitan default

    # Bengaluru Urban (Valley systems / lake chain corridors)
    "bellandur": 80.0,      # Bellandur lake catchment basin
    "koramangala": 75.0,    # Primary valley stormwater overflow
    "hebbal": 65.0,         # Hebbal lake basin
    "whitefield": 60.0,     # Moderate drainage
    "bengaluru": 55.0,      # Urban plateau default

    # Mumbai Metropolitan Area
    "kurla": 85.0,          # Mithi river floodplain
    "hindmata": 85.0,       # Low-lying saucer basin
    "dadar": 75.0,          # Low stormwater drainage gradient
    "mumbai": 70.0          # Coastal high-tide rainfall interaction
}


def assess_flood_risk(
    current_precipitation_mm: Optional[float],
    forecast_rain_24h_mm: Optional[float],
    citizen_flood_levels: Optional[List[int]] = None,
    location_name: str = "Coimbatore",
    weights: Optional[Dict[str, float]] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluates environmental flood risk using live weather and field data.

    Returns structured dictionary with:
    - risk_score: float (0.0 - 100.0)
    - risk_category: str ('Low', 'Moderate', 'High', 'Severe')
    - factors: Dict of input breakdowns and weighted contributions
    - timestamp: ISO 8601 string
    - data_completeness: str ('Complete', 'Partial - Forecast Missing', etc.)
    - warnings: List[str]
    """
    w = weights or {
        "current_rain": 0.25,
        "forecast_rain": 0.35,
        "citizen_reports": 0.25,
        "terrain_area": 0.15
    }

    warnings: List[str] = []
    missing_elements: List[str] = []

    # 1. Current Rain Component (0 - 100)
    # Rainfall intensity reference (WMO/IMD):
    # > 15 mm/hr is heavy rain; > 30 mm/hr is very heavy / violent downpour.
    if current_precipitation_mm is not None:
        try:
            curr_val = max(0.0, float(current_precipitation_mm))
            # Linear scale: 0 mm = 0 pts; 25 mm/h = 100 pts
            curr_score = min(100.0, (curr_val / 25.0) * 100.0)
            curr_status = f"{curr_val:.1f} mm/hr"
        except (ValueError, TypeError):
            curr_score = 0.0
            curr_status = "Invalid data"
            missing_elements.append("current rain telemetry")
    else:
        curr_score = 0.0
        curr_status = "Unavailable"
        missing_elements.append("current rain telemetry")

    # 2. Forecast Rain (24h accumulation) Component (0 - 100)
    # Accumulated 24h rainfall:
    # 0-20mm: normal; 20-60mm: moderate; 60-120mm: heavy; >120mm: severe flood alert
    if forecast_rain_24h_mm is not None:
        try:
            fc_val = max(0.0, float(forecast_rain_24h_mm))
            fc_score = min(100.0, (fc_val / 100.0) * 100.0)
            fc_status = f"{fc_val:.1f} mm expected next 24h"
        except (ValueError, TypeError):
            fc_score = 0.0
            fc_status = "Invalid data"
            missing_elements.append("24h forecast data")
    else:
        fc_score = 0.0
        fc_status = "Unavailable"
        missing_elements.append("24h forecast data")

    # 3. Citizen Field Reports Component (0 - 100)
    if citizen_flood_levels and len(citizen_flood_levels) > 0:
        valid_levels = [lvl for lvl in citizen_flood_levels if 1 <= lvl <= 5]
        if valid_levels:
            avg_level = sum(valid_levels) / len(valid_levels)
            max_level = max(valid_levels)
            # Weighted average: 60% average, 40% worst-case peak
            blended_level = (0.6 * avg_level) + (0.4 * max_level)
            # Map 1-5 scale to 0-100: Level 1 = 15, Level 5 = 100
            field_score = min(100.0, ((blended_level - 1.0) / 4.0) * 85.0 + 15.0)
            field_status = f"{len(valid_levels)} active field reports (avg Level {avg_level:.1f}, peak Level {max_level})"
        else:
            field_score = 0.0
            field_status = "No active severity reports"
    else:
        field_score = 0.0
        field_status = "No active field reports"

    # 4. Topographical / Known Area Vulnerability (0 - 100)
    loc_key = (location_name or "Coimbatore").strip().lower()
    matched_terrain = None
    for k, v in KNOWN_VULNERABLE_AREAS.items():
        if k in loc_key:
            matched_terrain = v
            terrain_status = f"Specific terrain vulnerability match for '{k}' in '{location_name}': {v:.0f}/100"
            break

    if matched_terrain is not None:
        terrain_score = matched_terrain
    else:
        terrain_score = 50.0
        terrain_status = f"Standard regional baseline index (50/100) applied for '{location_name}'. No specific high-risk topographic basin override recorded."

    # Assess data completeness
    if not missing_elements:
        data_completeness = "Complete (Telemetry + Forecast + Field Reports)"
    else:
        data_completeness = f"Partial ({', '.join(missing_elements)} missing)"
        warnings.append("Assessment is operating with partial telemetry. Confidence is adjusted.")

    # Compute weighted total
    risk_score = (
        (w["current_rain"] * curr_score) +
        (w["forecast_rain"] * fc_score) +
        (w["citizen_reports"] * field_score) +
        (w["terrain_area"] * terrain_score)
    )

    final_risk_score = min(100.0, max(0.0, round(risk_score, 1)))

    if final_risk_score >= 80.0:
        category = "Severe"
        recommendation = "Severe flood risk detected. Coordinate immediate low-lying evacuations."
    elif final_risk_score >= 60.0:
        category = "High"
        recommendation = "High water accumulation probable. Place rescue teams on active standby."
    elif final_risk_score >= 30.0:
        category = "Moderate"
        recommendation = "Moderate localized runoff. Monitor vulnerable drainage corridors."
    else:
        category = "Low"
        recommendation = "Low environmental risk under current and forecast weather telemetry."

    return {
        "risk_score": final_risk_score,
        "risk_category": category,
        "recommendation": recommendation,
        "location": location_name,
        "latitude": latitude,
        "longitude": longitude,
        "assessment_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_completeness": data_completeness,
        "warnings": warnings,
        "factors": {
            "current_rain": {
                "score": round(curr_score, 1),
                "weight": w["current_rain"],
                "weighted_pts": round(w["current_rain"] * curr_score, 1),
                "detail": curr_status
            },
            "forecast_rain": {
                "score": round(fc_score, 1),
                "weight": w["forecast_rain"],
                "weighted_pts": round(w["forecast_rain"] * fc_score, 1),
                "detail": fc_status
            },
            "citizen_reports": {
                "score": round(field_score, 1),
                "weight": w["citizen_reports"],
                "weighted_pts": round(w["citizen_reports"] * field_score, 1),
                "detail": field_status
            },
            "terrain_area": {
                "score": round(terrain_score, 1),
                "weight": w["terrain_area"],
                "weighted_pts": round(w["terrain_area"] * terrain_score, 1),
                "detail": terrain_status
            }
        }
    }
