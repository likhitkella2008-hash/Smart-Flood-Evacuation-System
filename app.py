import os
import re
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Union, Dict, Any, List, Tuple
import requests
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

# Modular Domain Engines
from prioritization import calculate_priority
from flood_risk import assess_flood_risk
from routing import plan_evacuation_route
from notifications import notification_service
from migrate import migrate_database
from shelter_discovery import discover_potential_shelters, haversine_distance

# Genuine ADSA Implementations
from algorithms.merge_sort import merge_sort_requests, merge_sort_by_key, compare_emergency_requests
from algorithms.binary_search import binary_search_request_by_id, binary_search_ids
from algorithms.priority_queue import EmergencyPriorityQueue, BinaryHeap, MinHeap
from algorithms.dijkstra import AdjacencyListGraph, dijkstra_shortest_path
from algorithms.graph_traversal import bfs_traversal, dfs_traversal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SmartFlood")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "SMART_FLOOD_SECRET_PROD_2026_SECURE")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

DATABASE = "smart_flood_final.db"


def get_json_data():
    """Safely extracts JSON payload without throwing 400 on empty/missing body."""
    return request.get_json(silent=True) or {}


def geocode_location(query: str, count: int = 5):
    """
    Geocodes text address/city queries using Open-Meteo Geocoding API.
    Returns list of matching location dicts with latitude, longitude, and names.
    """
    if not query or len(query.strip()) < 2:
        return []
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": query.strip(),
                "count": max(1, min(count, 10)),
                "language": "en",
                "format": "json"
            },
            timeout=8.0
        )
        if resp.status_code == 200:
            return resp.json().get("results", []) or []
        elif resp.status_code == 429:
            logger.warning("Open-Meteo geocoding rate limited for query '%s'", query)
    except Exception as ex:
        logger.warning("Geocoding lookup failed for '%s': %s", query, ex)
    return []


# =========================================================
# DATABASE HELPERS & INITIALIZATION
# =========================================================

def db():
    turso_url = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("LIBSQL_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN") or os.environ.get("LIBSQL_AUTH_TOKEN")

    if turso_url:
        import turso_db
        return turso_db.connect(turso_url, auth_token=turso_token)

    # Local SQLite with Vercel serverless /tmp fallback protection
    db_path = DATABASE
    if os.environ.get("VERCEL") == "1" and not os.path.isabs(db_path):
        db_path = os.path.join("/tmp", os.path.basename(DATABASE))

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_database():
    """Initializes tables and executes safe migrations."""
    conn = db()
    cur = conn.cursor()

    # 1. Citizens
    cur.execute("""
        CREATE TABLE IF NOT EXISTS citizens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # 2. Admins
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # 3. Rescue Teams
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rescue_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available'
        )
    """)

    # 4. Shelters
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shelters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            occupied INTEGER NOT NULL DEFAULT 0
        )
    """)

    # 5. Emergency Requests
    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citizen_id INTEGER NOT NULL,
            citizen_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT NOT NULL,
            people INTEGER NOT NULL,
            flood_level INTEGER NOT NULL,
            details TEXT,
            priority TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            assigned_team_id INTEGER,
            assigned_team TEXT,
            shelter_id INTEGER,
            shelter TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # 6. Notifications
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            citizen_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # 7. Road Hazards (for routing hazard-avoidance)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS road_hazards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            severity TEXT NOT NULL,
            description TEXT,
            reported_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    conn.commit()

    # Default Admin
    cur.execute("SELECT id, password FROM admins WHERE username = 'admin'")
    row = cur.fetchone()
    if row is None:
        cur.execute("""
            INSERT INTO admins (username, password)
            VALUES (?, ?)
        """, ("admin", generate_password_hash("admin123")))
    conn.commit()

    # Default Rescue Teams
    teams = [
        ("Alpha Rescue Team", "alpha", "alpha123", "Gandhipuram", 11.0185, 76.9730, "+91 9443011221"),
        ("Bravo Rescue Team", "bravo", "bravo123", "RS Puram", 11.0095, 76.9495, "+91 9443011222"),
        ("Charlie Rescue Team", "charlie", "charlie123", "Ukkadam", 10.9910, 76.9610, "+91 9443011223")
    ]

    for team in teams:
        cur.execute("SELECT id FROM rescue_teams WHERE username = ?", (team[1],))
        if cur.fetchone() is None:
            cur.execute("""
                INSERT INTO rescue_teams (team_name, username, password, location, status, latitude, longitude, phone)
                VALUES (?, ?, ?, ?, 'Available', ?, ?, ?)
            """, (team[0], team[1], generate_password_hash(team[2]), team[3], team[4], team[5], team[6]))
    conn.commit()

    # Default Shelters
    shelters = [
        ("Government Higher Secondary School", "Gandhipuram", 500, 11.0180, 76.9720, "+91 422 2521101"),
        ("Corporation Community Hall", "RS Puram", 300, 11.0085, 76.9485, "+91 422 2548822"),
        ("Government School Shelter", "Ukkadam", 350, 10.9900, 76.9600, "+91 422 2390014"),
        ("Amrita Emergency Shelter", "Coimbatore", 400, 10.9020, 76.9030, "+91 422 2685000")
    ]

    for shelter in shelters:
        cur.execute("SELECT id FROM shelters WHERE name = ?", (shelter[0],))
        if cur.fetchone() is None:
            cur.execute("""
                INSERT INTO shelters (name, location, capacity, occupied, latitude, longitude, contact_phone)
                VALUES (?, ?, ?, 0, ?, ?, ?)
            """, (shelter[0], shelter[1], shelter[2], shelter[3], shelter[4], shelter[5]))
    conn.commit()

    # Sample road hazard for demonstration of detour planner
    cur.execute("SELECT id FROM road_hazards WHERE name = 'Sungam Bypass Submersion'")
    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO road_hazards (name, location, latitude, longitude, severity, description, reported_at, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            "Sungam Bypass Submersion",
            "Sungam Bypass",
            10.9970,
            76.9780,
            "Flooded",
            "Water level 3.5 ft over road culvert. Impassable for light vehicles.",
            now()
        ))
    conn.commit()
    conn.close()

    # Run safe schema migration for columns
    migrate_database(DATABASE)


# =========================================================
# AUTHORIZATION GUARDS & HELPERS
# =========================================================

def verify_and_migrate_password(stored_pw: str, input_pw: str, table_name: str, record_id: int) -> bool:
    """
    Checks password securely. If stored as legacy plain text, transparently
    hashes and updates the record in SQLite without breaking user logins.
    """
    if not stored_pw or not input_pw:
        return False

    # 1. Try checking as hashed password
    try:
        if check_password_hash(stored_pw, input_pw):
            return True
    except Exception:
        pass

    # 2. Backward compatibility: match legacy plain text
    if stored_pw == input_pw:
        # Migrate immediately to secure hash
        try:
            new_hash = generate_password_hash(input_pw)
            conn = db()
            conn.execute(f"UPDATE {table_name} SET password = ? WHERE id = ?", (new_hash, record_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
        return True

    return False


def citizen_only():
    if session.get("role") != "citizen":
        return jsonify({
            "success": False,
            "message": "Citizen login required."
        }), 401
    return None


def admin_only():
    if session.get("role") != "admin":
        return jsonify({
            "success": False,
            "message": "Admin login required."
        }), 401
    return None


def rescue_only():
    if session.get("role") != "rescue":
        return jsonify({
            "success": False,
            "message": "Rescue team login required."
        }), 401
    return None


def add_notification(citizen_id, message):
    """Backwards-compatible helper wrapping NotificationService."""
    conn = db()
    notification_service.notify(conn, citizen_id, "", message, event_type="in_app")
    conn.commit()
    conn.close()


def send_sms(phone, message):
    """Backwards-compatible helper wrapping NotificationService."""
    notification_service.send_sms(phone, message)


# =========================================================
# ROUTES: HOME & LIVE WEATHER
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/location/search")
def location_search():
    """
    Search endpoint leveraging Open-Meteo Geocoding API for dynamic
    locality, district, and city searches with coordinates.
    """
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"success": True, "results": []})

    results = geocode_location(q, count=6)
    formatted = []
    for r in results:
        admin = r.get("admin1", "")
        country = r.get("country", "")
        name = r.get("name", "")
        display = f"{name}, {admin} ({country})" if admin else f"{name}, {country}"
        formatted.append({
            "name": name,
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
            "admin1": admin,
            "country": country,
            "display_name": display
        })
    return jsonify({"success": True, "query": q, "results": formatted})


# =========================================================
# WMO WEATHER CODES & METEOROLOGICAL UTILITIES
# =========================================================

WMO_WEATHER_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "⛈️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "⛈️"),
    71: ("Slight snow fall", "🌨️"),
    73: ("Moderate snow fall", "🌨️"),
    75: ("Heavy snow fall", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌧️"),
    82: ("Violent rain showers", "⛈️"),
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⚡"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️")
}

def parse_coordinates(val: str) -> Optional[Tuple[float, float]]:
    """
    Parses a string formatted as 'lat, lon' or 'lat,lon' into (latitude, longitude) float tuple.
    Returns None if not a valid coordinate string.
    """
    if not val or not isinstance(val, str):
        return None
    m = re.match(r"^\s*([-+]?\d{1,3}(?:\.\d+)?)\s*,\s*([-+]?\d{1,3}(?:\.\d+)?)\s*$", val.strip())
    if m:
        try:
            lat = float(m.group(1))
            lon = float(m.group(2))
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return lat, lon
        except (ValueError, TypeError):
            pass
    return None

def degrees_to_cardinal(d: Optional[Union[int, float]]) -> str:
    """Converts wind direction in degrees (0-360) to a 16-point cardinal direction string."""
    if d is None:
        return ""
    try:
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        ix = round(float(d) / (360.0 / len(dirs))) % len(dirs)
        return dirs[ix]
    except Exception:
        return ""


@app.route("/api/weather")
def live_weather():
    """
    Live Meteorological Telemetry endpoint querying official Open-Meteo API.
    Retrieves real-time temperature, humidity, wind velocity, precipitation,
    and forward-looking hourly precipitation forecasts. Never returns fake zeros.
    """
    raw_lat = request.args.get("latitude") or request.args.get("lat")
    raw_lon = request.args.get("longitude") or request.args.get("lon")
    city = request.args.get("city", "").strip()

    lat = None
    lon = None
    loc_name = ""
    region_name = ""
    country_name = ""

    # 1. Parse coordinate string in city parameter (e.g. "11.0168, 76.9558")
    if city and not (raw_lat and raw_lon):
        parsed = parse_coordinates(city)
        if parsed:
            raw_lat, raw_lon = parsed

    # 2. Process direct numerical coordinates
    if raw_lat is not None and raw_lon is not None and str(raw_lat).strip() and str(raw_lon).strip():
        try:
            parsed_lat = float(raw_lat)
            parsed_lon = float(raw_lon)
            if not (-90.0 <= parsed_lat <= 90.0 and -180.0 <= parsed_lon <= 180.0):
                return jsonify({
                    "success": False,
                    "error_type": "INVALID_COORDINATES",
                    "message": f"Coordinates out of bounds (-90 to 90, -180 to 180): ({parsed_lat}, {parsed_lon})."
                }), 400
            lat = parsed_lat
            lon = parsed_lon
            lat_dir = "N" if lat >= 0 else "S"
            lon_dir = "E" if lon >= 0 else "W"
            loc_name = city if (city and not parse_coordinates(city)) else f"Coordinates ({abs(round(lat, 4))}° {lat_dir}, {abs(round(lon, 4))}° {lon_dir})"
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error_type": "INVALID_COORDINATES",
                "message": "Invalid numeric format for latitude or longitude."
            }), 400

    # 3. Geocode text location if coordinates not provided
    if lat is None or lon is None:
        target_city = city if city else "Coimbatore"
        try:
            locations = geocode_location(target_city, count=1)
        except requests.exceptions.Timeout:
            return jsonify({
                "success": False,
                "error_type": "TIMEOUT",
                "message": f"Geocoding lookup for '{target_city}' timed out. Please check your internet connection."
            }), 504
        except requests.exceptions.RequestException:
            return jsonify({
                "success": False,
                "error_type": "NETWORK_ERROR",
                "message": "Unable to reach geocoding service. Please check your internet connection."
            }), 502

        if not locations:
            return jsonify({
                "success": False,
                "error_type": "LOCATION_NOT_FOUND",
                "message": f"Location '{target_city}' could not be resolved. Please verify the spelling or specify latitude, longitude."
            }), 404

        location = locations[0]
        lat = location["latitude"]
        lon = location["longitude"]
        loc_name = location.get("name", target_city)
        region_name = location.get("admin1", "")
        country_name = location.get("country", "")

    # 4. Fetch Live Meteorological Telemetry from Open-Meteo
    try:
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "precipitation,"
                "rain,"
                "wind_speed_10m,"
                "wind_direction_10m,"
                "weather_code,"
                "apparent_temperature,"
                "precipitation_probability"
            ),
            "hourly": "precipitation,temperature_2m,weather_code,precipitation_probability",
            "wind_speed_unit": "kmh",
            "forecast_days": 2,
            "timezone": "auto"
        }
        logger.info(f"Querying Open-Meteo API for coordinates ({lat}, {lon}) [{loc_name}]")
        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=weather_params,
            timeout=10
        )
        if weather_response.status_code == 429:
            return jsonify({
                "success": False,
                "error_type": "RATE_LIMIT",
                "message": "Open-Meteo API rate limit reached. Please wait a few seconds and retry."
            }), 429

        weather_response.raise_for_status()
        data = weather_response.json()

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error_type": "TIMEOUT",
            "message": "Weather service request timed out while connecting to Open-Meteo. Please check your internet connection and retry."
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "error_type": "CONNECTION_ERROR",
            "message": "Unable to reach Open-Meteo weather service. Please verify your internet connection."
        }), 502
    except requests.exceptions.HTTPError:
        status = weather_response.status_code if 'weather_response' in locals() else 502
        return jsonify({
            "success": False,
            "error_type": "HTTP_ERROR",
            "message": f"Open-Meteo service returned error: HTTP {status}."
        }), status
    except Exception as ex:
        return jsonify({
            "success": False,
            "error_type": "SERVER_ERROR",
            "message": f"Failed to retrieve meteorological telemetry: {str(ex)}"
        }), 500

    # 5. Extract & Validate Measurements
    current = data.get("current", {})
    hourly = data.get("hourly", {})
    units = data.get("current_units", {})

    temp_c = current.get("temperature_2m")
    apparent_temp_c = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    precip_raw = current.get("precipitation")
    precip_prob_raw = current.get("precipitation_probability")
    rain_raw = current.get("rain")
    wind_raw = current.get("wind_speed_10m")
    wind_dir = current.get("wind_direction_10m")
    wmo_code = current.get("weather_code")
    interval_sec = current.get("interval", 900)
    interval_mins = max(1, round(interval_sec / 60))

    # Convert wind speed to km/h if API returned m/s
    wind_unit = units.get("wind_speed_10m", "km/h")
    if wind_raw is not None:
        try:
            wind_kmh = round(float(wind_raw) * 3.6, 1) if "m/s" in wind_unit else round(float(wind_raw), 1)
        except (ValueError, TypeError):
            wind_kmh = None
    else:
        wind_kmh = None

    cond_desc, cond_icon = WMO_WEATHER_CODES.get(wmo_code, ("Not specified", "🌡️"))
    wind_compass = degrees_to_cardinal(wind_dir)

    logger.info(
        f"Open-Meteo received for ({lat}, {lon}) [{loc_name}]: "
        f"time={current.get('time')}, temp={temp_c}C (feels {apparent_temp_c}C), "
        f"humidity={humidity}%, wind={wind_kmh}km/h {wind_compass} ({wind_dir} deg), "
        f"precip={precip_raw}mm (prob {precip_prob_raw}%), wmo={wmo_code} ({cond_desc})"
    )

    # 6. Build Next 12-Hour Forward-Looking Forecast from current observation time
    cur_time_str = current.get("time", "")
    cur_hour_prefix = cur_time_str[:13] if cur_time_str else datetime.now().strftime("%Y-%m-%dT%H")

    hourly_times = hourly.get("time", [])
    hourly_precip = hourly.get("precipitation", [])
    hourly_prob = hourly.get("precipitation_probability", [])
    hourly_temp = hourly.get("temperature_2m", [])
    hourly_codes = hourly.get("weather_code", [])

    start_idx = 0
    for idx, t in enumerate(hourly_times):
        if t.startswith(cur_hour_prefix):
            start_idx = idx
            break

    next_12_hours = []
    for i in range(start_idx, min(start_idx + 12, len(hourly_times))):
        c_val = hourly_codes[i] if i < len(hourly_codes) else None
        h_desc, h_icon = WMO_WEATHER_CODES.get(c_val, ("Unknown", "🌡️"))
        p_val = hourly_precip[i] if i < len(hourly_precip) else 0.0
        prob_val = hourly_prob[i] if i < len(hourly_prob) else None
        t_val = hourly_temp[i] if i < len(hourly_temp) else None
        next_12_hours.append({
            "time": hourly_times[i],
            "precipitation_mm": round(float(p_val), 2) if p_val is not None else 0.0,
            "precipitation_probability_percent": int(prob_val) if prob_val is not None else 0,
            "temperature_c": round(float(t_val), 1) if t_val is not None else None,
            "weather_code": c_val,
            "condition": h_desc,
            "icon": h_icon
        })

    # Forward 24-Hour Cumulative Precipitation
    next_24_precip = hourly_precip[start_idx : start_idx + 24]
    precip_24h_sum = round(sum(next_24_precip), 2) if next_24_precip else 0.0

    formatted_loc = f"{loc_name}, {region_name} ({country_name})" if region_name and country_name else f"{loc_name}, {country_name}" if country_name else loc_name

    resp_payload = {
        "success": True,
        "location": loc_name,
        "region": region_name,
        "country": country_name,
        "formatted_location": formatted_loc,
        "latitude": round(lat, 5),
        "longitude": round(lon, 5),
        "timezone": data.get("timezone", "auto"),
        "timezone_abbreviation": data.get("timezone_abbreviation", ""),
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "observation_time": cur_time_str,
        "temperature_c": round(float(temp_c), 1) if temp_c is not None else None,
        "apparent_temperature_c": round(float(apparent_temp_c), 1) if apparent_temp_c is not None else None,
        "humidity_percent": round(float(humidity), 1) if humidity is not None else None,
        "precipitation_mm": round(float(precip_raw), 2) if precip_raw is not None else 0.0,
        "precipitation_probability_percent": int(precip_prob_raw) if precip_prob_raw is not None else 0,
        "precipitation_interval_mins": interval_mins,
        "rain_mm": round(float(rain_raw), 2) if rain_raw is not None else 0.0,
        "wind_speed_kmh": wind_kmh,
        "wind_direction_deg": wind_dir,
        "wind_direction_compass": wind_compass,
        "weather_code": wmo_code,
        "condition": cond_desc,
        "condition_icon": cond_icon,
        "next_12_hours": next_12_hours,
        "hourly_forecast": hourly,
        "precipitation_24h_sum_mm": precip_24h_sum,
        "data_source": "Open-Meteo Weather Forecast API",
        "source_type": "Numerical Weather Prediction (NWP) model assimilation"
    }

    # Safe diagnostic mode: exposes raw API metrics without credentials or secrets
    if request.args.get("diagnostic") in ("1", "true", "yes") or request.args.get("debug") in ("1", "true", "yes"):
        resp_payload["diagnostic"] = {
            "requested_endpoint": "https://api.open-meteo.com/v1/forecast",
            "evaluated_coordinates": {"latitude": round(lat, 5), "longitude": round(lon, 5)},
            "resolved_name": loc_name,
            "raw_units": units,
            "raw_current_snapshot": current,
            "hourly_available_fields": list(hourly.keys()),
            "hourly_data_points_count": len(hourly_times),
            "start_forecast_index": start_idx,
            "forecast_start_time": hourly_times[start_idx] if start_idx < len(hourly_times) else None,
            "timezone_info": {
                "timezone": data.get("timezone"),
                "timezone_abbreviation": data.get("timezone_abbreviation"),
                "utc_offset_seconds": data.get("utc_offset_seconds")
            }
        }

    resp = jsonify(resp_payload)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# =========================================================
# SESSION MANAGEMENT & AUTHENTICATION
# =========================================================

@app.route("/session")
def get_session():
    if not session.get("logged_in"):
        return jsonify({"logged_in": False})

    return jsonify({
        "logged_in": True,
        "role": session.get("role"),
        "name": session.get("name"),
        "username": session.get("username"),
        "phone": session.get("phone"),
        "team_name": session.get("team_name"),
        "citizen_id": session.get("citizen_id"),
        "team_id": session.get("team_id")
    })


@app.route("/register", methods=["POST"])
def register():
    data = get_json_data()
    name = data.get("name", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    phone = data.get("phone", "").strip()
    location = data.get("location", "").strip()

    if not all([name, username, password, phone]):
        return jsonify({
            "success": False,
            "message": "Please fill all required fields."
        })

    if len(password) < 6:
        return jsonify({
            "success": False,
            "message": "Password must be at least 6 characters long."
        })

    conn = db()
    try:
        pw_hash = generate_password_hash(password)
        conn.execute("""
            INSERT INTO citizens (name, username, password, phone, location, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, username, pw_hash, phone, location, now()))
        conn.commit()
        conn.close()
        return jsonify({
            "success": True,
            "message": "Citizen account created successfully."
        })
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "success": False,
            "message": "Username already exists."
        })


@app.route("/citizen-login", methods=["POST"])
def citizen_login():
    data = get_json_data()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = db()
    citizen = conn.execute("SELECT * FROM citizens WHERE username = ?", (username,)).fetchone()
    conn.close()

    if citizen is None or not verify_and_migrate_password(citizen["password"], password, "citizens", citizen["id"]):
        return jsonify({
            "success": False,
            "message": "Invalid citizen username or password."
        }), 401

    session.clear()
    session["logged_in"] = True
    session["role"] = "citizen"
    session["citizen_id"] = citizen["id"]
    session["name"] = citizen["name"]
    session["username"] = citizen["username"]
    session["phone"] = citizen["phone"]

    return jsonify({
        "success": True,
        "role": "citizen",
        "name": citizen["name"]
    })


@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = get_json_data()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = db()
    admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    conn.close()

    if admin is None or not verify_and_migrate_password(admin["password"], password, "admins", admin["id"]):
        return jsonify({
            "success": False,
            "message": "Invalid admin username or password."
        }), 401

    session.clear()
    session["logged_in"] = True
    session["role"] = "admin"
    session["name"] = "Administrator"
    session["username"] = username

    return jsonify({
        "success": True,
        "role": "admin"
    })


@app.route("/rescue-login", methods=["POST"])
def rescue_login():
    data = get_json_data()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = db()
    team = conn.execute("SELECT * FROM rescue_teams WHERE username = ?", (username,)).fetchone()
    conn.close()

    if team is None or not verify_and_migrate_password(team["password"], password, "rescue_teams", team["id"]):
        return jsonify({
            "success": False,
            "message": "Invalid rescue team username or password."
        }), 401

    session.clear()
    session["logged_in"] = True
    session["role"] = "rescue"
    session["team_id"] = team["id"]
    session["team_name"] = team["team_name"]
    session["name"] = team["team_name"]
    session["username"] = team["username"]

    return jsonify({
        "success": True,
        "role": "rescue",
        "team_name": team["team_name"]
    })


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


# =========================================================
# CITIZEN EMERGENCY REQUEST SUBMISSION & TRACKING
# =========================================================

@app.route("/create-request", methods=["POST"])
def create_request():
    check = citizen_only()
    if check:
        return check

    data = get_json_data()
    location = data.get("location", "").strip()
    phone = data.get("phone", "").strip()
    details = data.get("details", "").strip()

    # Vulnerability & GPS fields
    try:
        people = int(data.get("people", 1))
        flood_level = int(data.get("flood_level", 1))
        elderly_count = max(0, int(data.get("elderly_count", 0)))
        children_count = max(0, int(data.get("children_count", 0)))
        disability_count = max(0, int(data.get("disability_count", 0)))
        medical_urgent = 1 if data.get("medical_urgent") in [True, 1, "1", "true"] else 0
        assistance_notes = data.get("assistance_notes", "").strip()
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid numeric input in form."
        }), 400

    # GPS coordinates validation
    latitude = None
    longitude = None
    location_accuracy = None
    raw_lat = data.get("latitude")
    raw_lon = data.get("longitude")
    raw_acc = data.get("location_accuracy")

    if raw_lat is not None and raw_lon is not None and str(raw_lat).strip() != "" and str(raw_lon).strip() != "":
        try:
            parsed_lat = float(raw_lat)
            parsed_lon = float(raw_lon)
            if -90.0 <= parsed_lat <= 90.0 and -180.0 <= parsed_lon <= 180.0:
                latitude = parsed_lat
                longitude = parsed_lon
                if raw_acc is not None and str(raw_acc).strip() != "" and str(raw_acc).lower() != "manual":
                    try:
                        acc_val = float(raw_acc)
                        location_accuracy = max(0.0, acc_val)
                        # Reject excessively imprecise coordinates (e.g. > 15 km network/ISP radius)
                        if location_accuracy > 15000.0:
                            logger.warning("Discarded imprecise coordinates (%s, %s) with accuracy ±%sm", latitude, longitude, location_accuracy)
                            latitude = None
                            longitude = None
                            location_accuracy = None
                    except (ValueError, TypeError):
                        location_accuracy = None
            else:
                return jsonify({
                    "success": False,
                    "message": "GPS coordinates out of valid geographical bounds (-90 to 90, -180 to 180)."
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Invalid GPS coordinate format."
            }), 400

    if not location:
        return jsonify({"success": False, "message": "Location is required."}), 400
    if not phone:
        return jsonify({"success": False, "message": "Emergency phone is required."}), 400
    if people < 1:
        return jsonify({"success": False, "message": "Number of people must be at least 1."}), 400
    if flood_level < 1 or flood_level > 5:
        return jsonify({"success": False, "message": "Flood level must be between 1 and 5."}), 400

    # Dynamic Geocoding fallback: if citizen did not submit device GPS coordinates,
    # attempt resolving the location text via Open-Meteo Geocoding
    if latitude is None or longitude is None:
        geo_matches = geocode_location(location, count=1)
        if geo_matches:
            latitude = geo_matches[0]["latitude"]
            longitude = geo_matches[0]["longitude"]
            location_accuracy = 1000.0
            logger.info("Auto-geocoded incident address '%s' to (%s, %s)", location, latitude, longitude)

    citizen_id = session["citizen_id"]
    citizen_name = session["name"]

    # Calculate enhanced prioritization score and reasons
    score, priority_category, reasons = calculate_priority(
        flood_level=flood_level,
        people=people,
        medical_urgent=bool(medical_urgent),
        elderly_count=elderly_count,
        children_count=children_count,
        disability_count=disability_count
    )
    reasons_str = "; ".join(reasons)

    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO requests (
            citizen_id, citizen_name, phone, location, people, flood_level, details,
            priority, status, created_at, updated_at, latitude, longitude,
            location_accuracy, priority_score, priority_reasons, elderly_count,
            children_count, disability_count, medical_urgent, assistance_notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        citizen_id, citizen_name, phone, location, people, flood_level, details,
        priority_category, now(), now(), latitude, longitude,
        location_accuracy, score, reasons_str, elderly_count,
        children_count, disability_count, medical_urgent, assistance_notes
    ))
    request_id = cur.lastrowid
    conn.commit()

    # Synchronized Notification Service
    notif_msg = (
        f"Smart Flood: Emergency request #{request_id} received. "
        f"Triage: {priority_category} (Score: {score:.0f}). "
        f"Administrator is reviewing your case."
    )
    notification_service.notify(conn, citizen_id, phone, notif_msg, event_type="request_submitted")
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "request_id": request_id,
        "priority": priority_category,
        "priority_score": score,
        "reasons": reasons,
        "message": f"Emergency request #{request_id} submitted successfully with priority {priority_category}."
    })


@app.route("/my-requests")
def my_requests():
    check = citizen_only()
    if check:
        return check

    citizen_id = session["citizen_id"]
    conn = db()
    rows = conn.execute("""
        SELECT * FROM requests
        WHERE citizen_id = ?
        ORDER BY id DESC
    """, (citizen_id,)).fetchall()
    conn.close()

    return jsonify({
        "success": True,
        "requests": [dict(row) for row in rows]
    })


@app.route("/notifications")
def notifications():
    check = citizen_only()
    if check:
        return check

    citizen_id = session["citizen_id"]
    conn = db()
    rows = conn.execute("""
        SELECT * FROM notifications
        WHERE citizen_id = ?
        ORDER BY id DESC
        LIMIT 30
    """, (citizen_id,)).fetchall()
    conn.close()

    return jsonify({
        "success": True,
        "notifications": [dict(row) for row in rows]
    })


@app.route("/notifications/mark-read", methods=["POST"])
def mark_notifications_read():
    check = citizen_only()
    if check:
        return check

    citizen_id = session["citizen_id"]
    conn = db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE citizen_id = ?", (citizen_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# =========================================================
# ADMIN ENDPOINTS: STATS, TEAMS, SHELTERS, REQUESTS
# =========================================================

@app.route("/admin/stats")
def admin_stats():
    check = admin_only()
    if check:
        return check

    conn = db()
    total = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'Pending'").fetchone()[0]
    assigned = conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'Assigned'").fetchone()[0]
    progress = conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'In Progress'").fetchone()[0]
    rescued = conn.execute("SELECT COUNT(*) FROM requests WHERE status = 'Rescued'").fetchone()[0]
    teams = conn.execute("SELECT COUNT(*) FROM rescue_teams WHERE status = 'Available'").fetchone()[0]
    conn.close()

    return jsonify({
        "success": True,
        "total": total,
        "pending": pending,
        "assigned": assigned,
        "progress": progress,
        "rescued": rescued,
        "available_teams": teams
    })


@app.route("/admin/requests")
def admin_requests():
    check = admin_only()
    if check:
        return check

    conn = db()
    # Fetch raw requests from database without SQL ORDER BY
    # Ordering is computed purely in Python via manual Recursive Merge Sort
    rows = conn.execute("SELECT * FROM requests").fetchall()
    conn.close()

    raw_requests = [dict(row) for row in rows]
    # Pure Python recursive divide-and-conquer Merge Sort (Critical > High > Medium > Low, descending score)
    sorted_requests = merge_sort_requests(raw_requests)

    return jsonify({
        "success": True,
        "requests": sorted_requests,
        "sorting_engine": "Manual Recursive Merge Sort (O(N log N))",
        "total": len(sorted_requests)
    })


@app.route("/admin/teams")
def admin_teams():
    check = admin_only()
    if check:
        return check

    conn = db()
    rows = conn.execute("SELECT * FROM rescue_teams ORDER BY id").fetchall()
    conn.close()

    teams = []
    for row in rows:
        t = dict(row)
        is_live = (t.get("location_type") == "live_gps" and t.get("last_location_update") is not None)
        t["is_live_gps"] = is_live
        t["location_label"] = "Live GPS Beacon" if is_live else "Base Station (Predefined)"
        teams.append(t)

    return jsonify({
        "success": True,
        "teams": teams
    })


@app.route("/admin/shelters")
def admin_shelters():
    check = admin_only()
    if check:
        return check

    conn = db()
    rows = conn.execute("SELECT * FROM shelters ORDER BY id").fetchall()
    conn.close()

    shelters = []
    for row in rows:
        item = dict(row)
        item["available"] = max(0, row["capacity"] - row["occupied"])
        item["occupancy_pct"] = round((row["occupied"] / max(1, row["capacity"])) * 100.0, 1)
        item["is_verified"] = bool(item.get("is_verified", 1))
        item["source"] = item.get("source") or "verified_db"
        shelters.append(item)

    return jsonify({
        "success": True,
        "shelters": shelters
    })


# =========================================================
# ADMIN OPERATIONS: TEAM ASSIGNMENT, SHELTER, CANCELLATION
# =========================================================

@app.route("/admin/assign-team/<int:request_id>", methods=["POST"])
def admin_assign_team(request_id):
    check = admin_only()
    if check:
        return check

    data = get_json_data()
    specified_team_id = data.get("team_id")
    admin_user = session.get("username", "admin")

    logger.info("Admin '%s' requested rescue team deployment for emergency case #%s", admin_user, request_id)

    conn = db()
    try:
        emergency = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        if emergency is None:
            conn.close()
            logger.warning("Case #%s not found for team assignment", request_id)
            return jsonify({"success": False, "message": f"Emergency case #{request_id} not found."}), 404

        if emergency["status"] != "Pending":
            conn.close()
            logger.warning("Case #%s cannot be assigned because its status is '%s'", request_id, emergency["status"])
            return jsonify({
                "success": False,
                "message": f"Case #{request_id} is already in '{emergency['status']}' status."
            }), 400

        # Select team: specified, nearest GPS coordinate proximity, matching location, or first available
        team = None
        if specified_team_id:
            team = conn.execute(
                "SELECT * FROM rescue_teams WHERE id = ? AND status = 'Available'",
                (specified_team_id,)
            ).fetchone()

        # Spatial Proximity: Find nearest available rescue team
        if team is None and emergency["latitude"] is not None and emergency["longitude"] is not None:
            available_teams = conn.execute(
                "SELECT * FROM rescue_teams WHERE status = 'Available' AND latitude IS NOT NULL AND longitude IS NOT NULL"
            ).fetchall()
            if available_teams:
                e_lat = float(emergency["latitude"])
                e_lon = float(emergency["longitude"])
                sorted_teams = sorted(
                    available_teams,
                    key=lambda t: haversine_distance(e_lat, e_lon, float(t["latitude"]), float(t["longitude"]))
                )
                team = sorted_teams[0]

        if team is None:
            team = conn.execute("""
                SELECT * FROM rescue_teams
                WHERE status = 'Available' AND LOWER(location) = LOWER(?)
                LIMIT 1
            """, (emergency["location"],)).fetchone()

        if team is None:
            team = conn.execute("""
                SELECT * FROM rescue_teams
                WHERE status = 'Available'
                ORDER BY id LIMIT 1
            """).fetchone()

        if team is None:
            conn.close()
            logger.warning("No available rescue teams to assign to case #%s", request_id)
            return jsonify({
                "success": False,
                "message": "No rescue team is currently available. All units are busy."
            }), 400

        with conn:
            conn.execute("""
                UPDATE requests
                SET status = 'Assigned', assigned_team_id = ?, assigned_team = ?, updated_at = ?
                WHERE id = ?
            """, (team["id"], team["team_name"], now(), request_id))

            conn.execute("UPDATE rescue_teams SET status = 'Busy' WHERE id = ?", (team["id"],))

        # Send synchronized citizen notification and SMS
        message = (
            f"Your emergency request #{request_id} has been accepted by dispatch. "
            f"{team['team_name']} has been deployed to your location."
        )
        notification_service.notify(conn, emergency["citizen_id"], emergency["phone"], message, event_type="team_assigned")
        conn.commit()
        conn.close()

        logger.info("Successfully assigned %s (ID %s) to emergency case #%s", team["team_name"], team["id"], request_id)

        return jsonify({
            "success": True,
            "message": f"Rescue team {team['team_name']} deployed successfully.",
            "team": team["team_name"],
            "team_id": team["id"]
        })

    except Exception as ex:
        conn.close()
        logger.error("Exception during team assignment for case #%s: %s", request_id, str(ex), exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Database or server error assigning rescue team: {str(ex)}"
        }), 500


@app.route("/admin/assign-shelter/<int:request_id>", methods=["POST"])
def admin_assign_shelter(request_id):
    """
    Assigns an evacuation shelter with strict capacity verification,
    atomic transaction handling, and prevents duplicate allocations.
    """
    check = admin_only()
    if check:
        return check

    data = get_json_data()
    specified_shelter_id = data.get("shelter_id")
    admin_user = session.get("username", "admin")

    logger.info("Admin '%s' requested shelter assignment for emergency case #%s", admin_user, request_id)

    conn = db()
    try:
        emergency = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        if emergency is None:
            conn.close()
            logger.warning("Case #%s not found for shelter assignment", request_id)
            return jsonify({"success": False, "message": f"Emergency case #{request_id} not found."}), 404

        people_count = emergency["people"]
        prev_shelter_id = emergency["shelter_id"]

        # If a specific shelter was requested
        shelter = None
        if specified_shelter_id:
            shelter = conn.execute("""
                SELECT * FROM shelters
                WHERE id = ? AND (capacity - occupied) >= ? AND is_verified = 1
            """, (specified_shelter_id, people_count)).fetchone()

        # Spatial Proximity: Find closest verified shelter with sufficient capacity
        if shelter is None and emergency["latitude"] is not None and emergency["longitude"] is not None:
            candidate_shelters = conn.execute("""
                SELECT * FROM shelters
                WHERE is_verified = 1 AND (capacity - occupied) >= ? AND latitude IS NOT NULL AND longitude IS NOT NULL
            """, (people_count,)).fetchall()
            if candidate_shelters:
                e_lat = float(emergency["latitude"])
                e_lon = float(emergency["longitude"])
                sorted_shelters = sorted(
                    candidate_shelters,
                    key=lambda s: haversine_distance(e_lat, e_lon, float(s["latitude"]), float(s["longitude"]))
                )
                shelter = sorted_shelters[0]

        # Otherwise find matching location or lowest occupancy with capacity
        if shelter is None:
            shelter = conn.execute("""
                SELECT * FROM shelters
                WHERE is_verified = 1 AND LOWER(location) = LOWER(?) AND (capacity - occupied) >= ?
                LIMIT 1
            """, (emergency["location"], people_count)).fetchone()

        if shelter is None:
            shelter = conn.execute("""
                SELECT * FROM shelters
                WHERE is_verified = 1 AND (capacity - occupied) >= ?
                ORDER BY (capacity - occupied) ASC
                LIMIT 1
            """, (people_count,)).fetchone()

        if shelter is None:
            conn.close()
            logger.warning("No shelter has capacity for %s people in case #%s", people_count, request_id)
            return jsonify({
                "success": False,
                "message": f"No shelter has sufficient available capacity for {people_count} person(s)."
            }), 400

        with conn:
            # If reassigning from a previous shelter, release previous allocation first!
            if prev_shelter_id and prev_shelter_id != shelter["id"]:
                conn.execute("""
                    UPDATE shelters
                    SET occupied = MAX(0, occupied - ?)
                    WHERE id = ?
                """, (people_count, prev_shelter_id))

            # If not already occupying this exact shelter
            if prev_shelter_id != shelter["id"]:
                conn.execute("""
                    UPDATE shelters
                    SET occupied = occupied + ?
                    WHERE id = ?
                """, (people_count, shelter["id"]))

            conn.execute("""
                UPDATE requests
                SET shelter_id = ?, shelter = ?, updated_at = ?
                WHERE id = ?
            """, (shelter["id"], shelter["name"], now(), request_id))

        # Send notification
        message = (
            f"Evacuation Shelter Assigned for emergency #{request_id}: "
            f"{shelter['name']} ({shelter['location']}). "
            f"Contact: {shelter['contact_phone'] if 'contact_phone' in shelter.keys() else 'Emergency Hotline 112'}."
        )
        notification_service.notify(conn, emergency["citizen_id"], emergency["phone"], message, event_type="shelter_assigned")
        conn.commit()
        conn.close()

        logger.info("Successfully assigned shelter '%s' (ID %s) to case #%s", shelter["name"], shelter["id"], request_id)

        return jsonify({
            "success": True,
            "message": f"Shelter {shelter['name']} assigned successfully.",
            "shelter": shelter["name"],
            "shelter_id": shelter["id"]
        })

    except Exception as ex:
        conn.close()
        logger.error("Exception during shelter assignment for case #%s: %s", request_id, str(ex), exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Database or server error assigning shelter: {str(ex)}"
        }), 500


@app.route("/admin/cancel/<int:request_id>", methods=["POST"])
def admin_cancel(request_id):
    check = admin_only()
    if check:
        return check

    data = get_json_data()
    admin_user = session.get("username", "admin")
    logger.info("Admin '%s' requested cancellation of case #%s", admin_user, request_id)

    conn = db()
    try:
        emergency = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        if emergency is None:
            conn.close()
            return jsonify({"success": False, "message": f"Emergency case #{request_id} not found."}), 404

        if emergency["status"] == "Cancelled":
            conn.close()
            return jsonify({"success": False, "message": f"Emergency case #{request_id} is already cancelled."}), 400

        with conn:
            # Release rescue team
            if emergency["assigned_team_id"]:
                conn.execute("UPDATE rescue_teams SET status = 'Available' WHERE id = ?", (emergency["assigned_team_id"],))

            # Release shelter allocation
            if emergency["shelter_id"]:
                conn.execute("""
                    UPDATE shelters
                    SET occupied = MAX(0, occupied - ?)
                    WHERE id = ?
                """, (emergency["people"], emergency["shelter_id"]))

            conn.execute("UPDATE requests SET status = 'Cancelled', updated_at = ? WHERE id = ?", (now(), request_id))

        message = f"Emergency request #{request_id} has been cancelled by the administrator."
        notification_service.notify(conn, emergency["citizen_id"], emergency["phone"], message, event_type="request_cancelled")
        conn.commit()
        conn.close()

        logger.info("Successfully cancelled case #%s and released resources", request_id)

        return jsonify({
            "success": True,
            "message": f"Emergency request #{request_id} has been cancelled and resources released."
        })
    except Exception as ex:
        conn.close()
        logger.error("Error cancelling case #%s: %s", request_id, str(ex), exc_info=True)
        return jsonify({"success": False, "message": f"Error cancelling case: {str(ex)}"}), 500


# =========================================================
# RESCUE OPERATIONS ENDPOINTS
# =========================================================

@app.route("/rescue/requests")
def rescue_requests():
    check = rescue_only()
    if check:
        return check

    team_id = session["team_id"]
    conn = db()
    rows = conn.execute("""
        SELECT * FROM requests
        WHERE assigned_team_id = ?
        AND status IN ('Assigned', 'In Progress')
        ORDER BY id DESC
    """, (team_id,)).fetchall()
    conn.close()

    return jsonify({
        "success": True,
        "requests": [dict(row) for row in rows]
    })


@app.route("/rescue/update/<int:request_id>", methods=["POST"])
def rescue_update(request_id):
    check = rescue_only()
    if check:
        return check

    data = get_json_data()
    status = data.get("status")
    notes = data.get("completion_notes", "").strip()

    if status not in ["In Progress", "Rescued"]:
        return jsonify({"success": False, "message": "Invalid status."}), 400

    team_id = session["team_id"]
    conn = db()

    try:
        emergency = conn.execute("""
            SELECT * FROM requests
            WHERE id = ? AND assigned_team_id = ?
        """, (request_id, team_id)).fetchone()

        if emergency is None:
            conn.close()
            return jsonify({"success": False, "message": "This case is not assigned to your team."}), 403

        with conn:
            conn.execute("""
                UPDATE requests
                SET status = ?, completion_notes = COALESCE(?, completion_notes), updated_at = ?
                WHERE id = ?
            """, (status, notes if notes else None, now(), request_id))

            if status == "Rescued":
                conn.execute("UPDATE rescue_teams SET status = 'Available' WHERE id = ?", (team_id,))

        if status == "In Progress":
            message = f"Rescue team has initiated transit and active response to request #{request_id}."
        else:
            message = f"Rescue completed successfully for request #{request_id}. Evacuees secured."

        notification_service.notify(conn, emergency["citizen_id"], emergency["phone"], message, event_type="rescue_status_updated")
        conn.commit()
        conn.close()

        logger.info("Rescue team %s updated case #%s to status '%s'", team_id, request_id, status)

        return jsonify({"success": True, "message": message})
    except Exception as ex:
        conn.close()
        logger.error("Error in rescue_update for case #%s: %s", request_id, str(ex), exc_info=True)
        return jsonify({"success": False, "message": f"Error updating rescue status: {str(ex)}"}), 500


@app.route("/rescue/update-location", methods=["POST"])
def rescue_update_location():
    """Allows rescue teams to update their current GPS coordinates and broadcast live beacon."""
    check = rescue_only()
    if check:
        return check

    data = get_json_data()
    try:
        lat = float(data.get("latitude"))
        lon = float(data.get("longitude"))
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return jsonify({"success": False, "message": "Coordinates out of bounds."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Valid latitude and longitude required."}), 400

    team_id = session["team_id"]
    conn = db()
    conn.execute("""
        UPDATE rescue_teams
        SET latitude = ?, longitude = ?, location_type = 'live_gps', last_location_update = ?
        WHERE id = ?
    """, (lat, lon, now(), team_id))
    conn.commit()
    conn.close()

    logger.info("Rescue team %s updated live GPS coordinates to (%s, %s)", team_id, lat, lon)

    return jsonify({
        "success": True,
        "message": "Rescue team GPS position updated successfully (Live GPS Beacon active).",
        "latitude": lat,
        "longitude": lon,
        "location_type": "live_gps"
    })


# =========================================================
# FEATURE 1: INTERACTIVE MAP DATA API
# =========================================================

@app.route("/api/map/emergency-data")
def map_emergency_data():
    """
    Returns verified coordinates for emergency requests, rescue teams,
    shelters, and hazards. Does not invent coordinates.
    Masks citizen names for unauthorized roles.
    """
    is_authorized = session.get("role") in ["admin", "rescue"]
    current_citizen_id = session.get("citizen_id")

    conn = db()

    # 1. Requests
    requests_rows = conn.execute("SELECT * FROM requests ORDER BY id DESC").fetchall()
    mapped_requests = []
    unmapped_requests = []

    for r in requests_rows:
        row_dict = dict(r)
        # Privacy guard: mask names if not authorized and not own request
        if not is_authorized and row_dict.get("citizen_id") != current_citizen_id:
            row_dict["citizen_name"] = f"Citizen #{row_dict['id']}"
            row_dict["phone"] = "***-****"

        if row_dict.get("latitude") is not None and row_dict.get("longitude") is not None:
            mapped_requests.append(row_dict)
        else:
            unmapped_requests.append(row_dict)

    # 2. Rescue Teams: Distinguish Live GPS Beacons from Base Stations
    teams_rows = conn.execute("SELECT * FROM rescue_teams WHERE latitude IS NOT NULL").fetchall()
    mapped_teams = []
    for t in teams_rows:
        td = dict(t)
        is_live = (td.get("location_type") == "live_gps" and td.get("last_location_update") is not None)
        td["is_live_gps"] = is_live
        td["location_type"] = td.get("location_type") or "base_station"
        td["location_label"] = "Live GPS Beacon" if is_live else "Base Station (Predefined)"
        mapped_teams.append(td)

    # 3. Shelters: Differentiate verified operational shelters from unverified
    shelters_rows = conn.execute("SELECT * FROM shelters WHERE latitude IS NOT NULL").fetchall()
    mapped_shelters = []
    for s in shelters_rows:
        sd = dict(s)
        sd["available"] = max(0, sd["capacity"] - sd["occupied"])
        sd["occupancy_pct"] = round((sd["occupied"] / max(1, sd["capacity"])) * 100.0, 1)
        sd["is_verified"] = bool(sd.get("is_verified", 1))
        sd["source"] = sd.get("source") or "verified_db"
        mapped_shelters.append(sd)

    # 4. Hazards
    hazards_rows = conn.execute("SELECT * FROM road_hazards WHERE active = 1").fetchall()
    mapped_hazards = [dict(h) for h in hazards_rows]

    conn.close()

    return jsonify({
        "success": True,
        "mapped_requests": mapped_requests,
        "unmapped_requests": unmapped_requests,
        "rescue_teams": mapped_teams,
        "shelters": mapped_shelters,
        "road_hazards": mapped_hazards
    })


@app.route("/api/shelters/map")
def shelters_map():
    conn = db()
    rows = conn.execute("SELECT * FROM shelters ORDER BY id").fetchall()
    conn.close()

    shelters = []
    for r in rows:
        sd = dict(r)
        sd["available"] = max(0, sd["capacity"] - sd["occupied"])
        sd["occupancy_pct"] = round((sd["occupied"] / max(1, sd["capacity"])) * 100.0, 1)
        sd["is_verified"] = bool(sd.get("is_verified", 1))
        sd["source"] = sd.get("source") or "verified_db"
        shelters.append(sd)

    return jsonify({"success": True, "shelters": shelters})


@app.route("/api/shelters/discover", methods=["GET", "POST"])
def shelters_discover():
    """
    Discovers potential emergency shelters dynamically from OpenStreetMap
    near any provided GPS coordinates.
    All candidates are returned as unverified without allocated capacity.
    """
    if request.method == "POST":
        data = get_json_data()
        raw_lat = data.get("latitude") or data.get("lat")
        raw_lon = data.get("longitude") or data.get("lon")
        radius_km = data.get("radius_km", 5.0)
    else:
        raw_lat = request.args.get("latitude") or request.args.get("lat")
        raw_lon = request.args.get("longitude") or request.args.get("lon")
        radius_km = request.args.get("radius_km", 5.0)

    try:
        lat = float(raw_lat)
        lon = float(raw_lon)
        radius = float(radius_km)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Valid latitude and longitude required to discover shelters."
        }), 400

    conn = db()
    existing_shelters = [dict(s) for s in conn.execute("SELECT latitude, longitude FROM shelters").fetchall()]
    conn.close()

    discovery_result = discover_potential_shelters(
        latitude=lat,
        longitude=lon,
        radius_km=radius,
        existing_shelters=existing_shelters
    )

    return jsonify(discovery_result)


@app.route("/api/shelters/verify-and-add", methods=["POST"])
def shelter_verify_and_add():
    """
    Admin-only endpoint to inspect, verify, and officially activate a candidate shelter.
    Explicitly assigns verified operational capacity, emergency phone, and persists to DB.
    """
    check = admin_only()
    if check:
        return check

    data = get_json_data()
    name = data.get("name", "").strip()
    location = data.get("location", "").strip()
    raw_lat = data.get("latitude")
    raw_lon = data.get("longitude")
    contact_phone = data.get("contact_phone", "").strip() or "Emergency Control"
    amenity_type = data.get("amenity_type", "Civic Shelter").strip()

    try:
        capacity = int(data.get("capacity", 0))
        lat = float(raw_lat)
        lon = float(raw_lon)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Valid capacity (integer) and GPS coordinates (float) are required."
        }), 400

    if not name:
        return jsonify({"success": False, "message": "Shelter facility name is required."}), 400
    if not location:
        location = f"{name} Campus"
    if capacity < 1:
        return jsonify({"success": False, "message": "Verified operational capacity must be at least 1 person."}), 400

    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shelters (name, location, capacity, occupied, latitude, longitude, contact_phone, is_verified, source, amenity_type)
        VALUES (?, ?, ?, 0, ?, ?, ?, 1, 'verified_osm', ?)
    """, (name, location, capacity, lat, lon, contact_phone, amenity_type))
    shelter_id = cur.lastrowid
    conn.commit()
    conn.close()

    logger.info("Admin '%s' verified and activated shelter '%s' (ID %s, capacity %s) at (%s, %s)",
                session.get("username", "admin"), name, shelter_id, capacity, lat, lon)

    return jsonify({
        "success": True,
        "message": f"Shelter '{name}' verified and activated with operational capacity of {capacity} spaces.",
        "shelter": {
            "id": shelter_id,
            "name": name,
            "location": location,
            "capacity": capacity,
            "occupied": 0,
            "latitude": lat,
            "longitude": lon,
            "contact_phone": contact_phone,
            "is_verified": 1,
            "source": "verified_osm"
        }
    })


# =========================================================
# FEATURE 3: FLOOD RISK ASSESSMENT API
# =========================================================

@app.route("/api/flood-risk/assess")
def flood_risk_assessment():
    raw_lat = request.args.get("latitude") or request.args.get("lat")
    raw_lon = request.args.get("longitude") or request.args.get("lon")
    location = request.args.get("location", "").strip()

    lat = None
    lon = None
    target_loc = location or "Coimbatore"

    if raw_lat and raw_lon:
        try:
            lat = float(raw_lat)
            lon = float(raw_lon)
        except (ValueError, TypeError):
            pass

    # Retrieve live rainfall from Open-Meteo
    current_rain = None
    forecast_rain_24h = None

    try:
        if lat is None or lon is None:
            results = geocode_location(target_loc, count=1)
            if results:
                lat = results[0]["latitude"]
                lon = results[0]["longitude"]
                target_loc = results[0].get("name", target_loc)

        if lat is not None and lon is not None:
            w_res = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "precipitation,rain",
                    "hourly": "precipitation",
                    "forecast_days": 1,
                    "timezone": "auto"
                },
                timeout=6
            )
            if w_res.status_code == 200:
                w_data = w_res.json()
                current_rain = w_data.get("current", {}).get("precipitation", 0.0)
                hourly_p = w_data.get("hourly", {}).get("precipitation", [])
                forecast_rain_24h = sum(hourly_p[:24]) if hourly_p else 0.0
    except Exception as ex:
        logger.debug("Weather telemetry fetch failed for flood risk: %s", ex)

    # Retrieve recent active citizen-reported flood levels
    conn = db()
    rows = conn.execute("""
        SELECT flood_level FROM requests
        WHERE status != 'Cancelled'
        ORDER BY id DESC LIMIT 50
    """).fetchall()
    conn.close()
    citizen_levels = [r["flood_level"] for r in rows if r["flood_level"] is not None]

    assessment = assess_flood_risk(
        current_precipitation_mm=current_rain,
        forecast_rain_24h_mm=forecast_rain_24h,
        citizen_flood_levels=citizen_levels,
        location_name=target_loc,
        latitude=lat,
        longitude=lon
    )

    return jsonify({"success": True, "assessment": assessment})


# =========================================================
# FEATURE 5: SAFE EVACUATION ROUTE PLANNER API
# =========================================================

@app.route("/api/route/plan", methods=["POST"])
def plan_route():
    """
    Plans safest evacuation route from citizen/team coordinates to a designated shelter.
    Applies NetworkX Dijkstra routing with road hazard avoidance and OSRM fallback.
    """
    data = get_json_data()
    start_lat = data.get("start_lat")
    start_lon = data.get("start_lon")
    shelter_id = data.get("shelter_id")
    request_id = data.get("request_id")

    conn = db()

    # If request_id is supplied, lookup starting coordinates from request
    if request_id:
        req = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        if req and req["latitude"] is not None and req["longitude"] is not None:
            start_lat = req["latitude"]
            start_lon = req["longitude"]
        elif req:
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Emergency case #{request_id} does not have verified GPS coordinates."
            }), 400

    if start_lat is None or start_lon is None:
        conn.close()
        return jsonify({"success": False, "message": "Starting GPS coordinates are required."}), 400

    s_lat = float(start_lat)
    s_lon = float(start_lon)

    # Retrieve shelter coordinates: specific shelter, or closest verified operational shelter with capacity
    if shelter_id:
        shelter = conn.execute("SELECT * FROM shelters WHERE id = ? AND is_verified = 1", (shelter_id,)).fetchone()
    else:
        candidate_shelters = conn.execute("""
            SELECT * FROM shelters
            WHERE is_verified = 1 AND (capacity - occupied) > 0 AND latitude IS NOT NULL AND longitude IS NOT NULL
        """).fetchall()

        if candidate_shelters:
            sorted_candidates = sorted(
                candidate_shelters,
                key=lambda s: haversine_distance(s_lat, s_lon, float(s["latitude"]), float(s["longitude"]))
            )
            shelter = sorted_candidates[0]
        else:
            shelter = conn.execute("""
                SELECT * FROM shelters
                WHERE is_verified = 1 AND (capacity - occupied) > 0
                ORDER BY id LIMIT 1
            """).fetchone()

    if shelter is None or shelter["latitude"] is None or shelter["longitude"] is None:
        conn.close()
        return jsonify({"success": False, "message": "No verified target shelter found with available capacity."}), 404

    # Fetch active road hazards for avoidance
    hazards_rows = conn.execute("SELECT * FROM road_hazards WHERE active = 1").fetchall()
    hazards = [dict(h) for h in hazards_rows]
    conn.close()

    result = plan_evacuation_route(
        start_lat=s_lat,
        start_lon=s_lon,
        shelter_lat=float(shelter["latitude"]),
        shelter_lon=float(shelter["longitude"]),
        shelter_name=shelter["name"],
        active_hazards=hazards
    )

    if result.get("success"):
        result["shelter_id"] = shelter["id"]
        result["shelter_capacity"] = shelter["capacity"]
        result["shelter_available"] = max(0, shelter["capacity"] - shelter["occupied"])
        result["shelter_contact"] = shelter["contact_phone"] if "contact_phone" in shelter.keys() else None

    return jsonify(result)


# =========================================================
# FEATURE 6: ADVANCED ANALYTICS DASHBOARD API
# =========================================================

@app.route("/api/analytics/dashboard")
def analytics_dashboard():
    """
    Returns authentic database analytics for Chart.js dashboards:
    Priority breakdown, status breakdown, shelter capacity vs occupancy,
    and emergency requests timeline. No fabricated data.
    """
    conn = db()

    # 1. Cases by Priority
    priorities = ["Critical", "High", "Medium", "Low"]
    priority_counts = {}
    for p in priorities:
        count = conn.execute("SELECT COUNT(*) FROM requests WHERE priority = ?", (p,)).fetchone()[0]
        priority_counts[p] = count

    # 2. Cases by Status
    statuses = ["Pending", "Assigned", "In Progress", "Rescued", "Cancelled"]
    status_counts = {}
    for s in statuses:
        count = conn.execute("SELECT COUNT(*) FROM requests WHERE status = ?", (s,)).fetchone()[0]
        status_counts[s] = count

    # 3. Shelter Capacity vs Occupied
    shelter_rows = conn.execute("SELECT name, capacity, occupied FROM shelters ORDER BY id").fetchall()
    shelters_data = [
        {
            "name": r["name"],
            "capacity": r["capacity"],
            "occupied": r["occupied"],
            "available": max(0, r["capacity"] - r["occupied"])
        }
        for r in shelter_rows
    ]

    # 4. Emergency Requests Timeline (from created_at dates)
    timeline_rows = conn.execute("""
        SELECT SUBSTR(created_at, 1, 10) as day, COUNT(*) as cnt
        FROM requests
        GROUP BY day
        ORDER BY day ASC
    """).fetchall()
    timeline = [{"date": r["day"], "count": r["cnt"]} for r in timeline_rows]

    # 5. Vulnerability Totals
    vuln_totals = conn.execute("""
        SELECT
            SUM(elderly_count) as total_elderly,
            SUM(children_count) as total_children,
            SUM(disability_count) as total_disabled,
            SUM(medical_urgent) as total_medical_urgent
        FROM requests
    """).fetchone()

    conn.close()

    return jsonify({
        "success": True,
        "priority_distribution": priority_counts,
        "status_distribution": status_counts,
        "shelter_analytics": shelters_data,
        "requests_timeline": timeline,
        "vulnerability_summary": {
            "elderly": vuln_totals["total_elderly"] or 0,
            "children": vuln_totals["total_children"] or 0,
            "disabled": vuln_totals["total_disabled"] or 0,
            "medical_urgent": vuln_totals["total_medical_urgent"] or 0
        }
    })


# =========================================================
# ROAD HAZARDS MANAGEMENT API
# =========================================================

@app.route("/api/road-hazards", methods=["GET", "POST"])
def manage_road_hazards():
    conn = db()
    if request.method == "POST":
        check = admin_only()
        if check:
            conn.close()
            return check

        data = get_json_data()
        name = data.get("name", "").strip()
        location = data.get("location", "").strip()
        severity = data.get("severity", "Flooded").strip()
        description = data.get("description", "").strip()
        lat = data.get("latitude")
        lon = data.get("longitude")

        if not name or not location:
            conn.close()
            return jsonify({"success": False, "message": "Hazard name and location are required."}), 400

        conn.execute("""
            INSERT INTO road_hazards (name, location, latitude, longitude, severity, description, reported_at, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """, (name, location, lat, lon, severity, description, now()))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Hazard '{name}' reported successfully."})

    rows = conn.execute("SELECT * FROM road_hazards WHERE active = 1 ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"success": True, "hazards": [dict(r) for r in rows]})


# =========================================================
# ADSA ALGORITHM ENDPOINTS & INTERACTIVE DEMONSTRATION
# =========================================================

@app.route("/api/admin/requests/search-id", methods=["GET", "POST"])
def admin_search_request_by_id():
    """
    Searches for an emergency request using manual iterative Binary Search on sorted IDs.
    O(log N) runtime with step-by-step trace.
    """
    check = admin_only()
    if check:
        return check

    data = get_json_data() if request.method == "POST" else request.args
    target_id_raw = data.get("id")

    if target_id_raw is None or str(target_id_raw).strip() == "":
        return jsonify({"success": False, "message": "Target request ID is required."}), 400

    try:
        target_id = int(target_id_raw)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Request ID must be an integer."}), 400

    conn = db()
    rows = conn.execute("SELECT * FROM requests").fetchall()
    conn.close()

    raw_requests = [dict(r) for r in rows]
    # Binary Search requires ascending sorted order by key
    sorted_by_id = merge_sort_by_key(raw_requests, key="id")

    found_request, steps, trace = binary_search_request_by_id(
        sorted_by_id, target_id, collect_trace=True
    )

    return jsonify({
        "success": True,
        "target_id": target_id,
        "found": found_request is not None,
        "request": found_request,
        "steps_taken": steps,
        "total_records": len(sorted_by_id),
        "trace": trace,
        "algorithm": "Manual Iterative Binary Search (O(log N))"
    })


@app.route("/api/admin/dispatch/triage-queue")
def admin_dispatch_triage_queue():
    """
    Inspects active emergency dispatch queue using manual Binary Heap Priority Queue.
    Enqueues all pending requests and returns root peek and queue structure.
    """
    check = admin_only()
    if check:
        return check

    conn = db()
    rows = conn.execute("SELECT * FROM requests WHERE status = 'Pending'").fetchall()
    conn.close()

    pending_requests = [dict(r) for r in rows]
    pq = EmergencyPriorityQueue()
    for req in pending_requests:
        pq.push(req)

    peek_item = pq.peek()
    heap_list = pq.to_list()

    return jsonify({
        "success": True,
        "total_pending": len(pending_requests),
        "queue_size": len(pq),
        "next_for_dispatch": peek_item,
        "heap_array_preview": heap_list[:10],
        "data_structure": "Manual Array-Based Binary Max-Heap (O(1) peek, O(log N) push/pop)"
    })


@app.route("/api/admin/dispatch/pop-next", methods=["POST"])
def admin_dispatch_pop_next():
    """
    Pops the single highest-urgency emergency request from the Priority Queue
    for immediate rescue assignment.
    """
    check = admin_only()
    if check:
        return check

    conn = db()
    rows = conn.execute("SELECT * FROM requests WHERE status = 'Pending'").fetchall()
    conn.close()

    pending_requests = [dict(r) for r in rows]
    if not pending_requests:
        return jsonify({
            "success": False,
            "message": "No pending emergency requests in the triage queue."
        }), 404

    pq = EmergencyPriorityQueue()
    for req in pending_requests:
        pq.push(req)

    top_request = pq.pop()

    return jsonify({
        "success": True,
        "message": f"Dequeued highest-priority Request #{top_request.get('id')} ({top_request.get('priority')})",
        "popped_request": top_request,
        "remaining_queue_size": len(pq),
        "algorithm": "EmergencyPriorityQueue.pop() with Sift-Down (O(log N))"
    })


@app.route("/api/dsa/demo")
def api_dsa_demo():
    """
    Comprehensive Demonstration Endpoint: executes all 5 ADSA algorithms
    with deterministic, verifiable inputs and outputs.
    """
    # 1. Merge Sort Demonstration
    sample_cases = [
        {"id": 101, "name": "Ravi", "priority": "Medium", "priority_score": 38.0, "created_at": "2026-10-28 10:00:00"},
        {"id": 102, "name": "Meena", "priority": "Critical", "priority_score": 85.0, "created_at": "2026-10-28 10:05:00"},
        {"id": 103, "name": "Suresh", "priority": "Low", "priority_score": 18.0, "created_at": "2026-10-28 09:50:00"},
        {"id": 104, "name": "Kavitha", "priority": "High", "priority_score": 58.0, "created_at": "2026-10-28 10:12:00"},
        {"id": 105, "name": "Deepak", "priority": "Critical", "priority_score": 92.0, "created_at": "2026-10-28 10:15:00"},
        {"id": 106, "name": "Ananya", "priority": "Critical", "priority_score": 85.0, "created_at": "2026-10-28 10:01:00"}
    ]
    sorted_cases = merge_sort_requests(sample_cases)

    # 2. Binary Search Demonstration
    demo_ids = [10, 22, 35, 47, 53, 68, 74, 89, 91, 105, 120]
    sorted_reqs_for_bs = [{"id": x, "label": f"Incident #{x}"} for x in demo_ids]
    bs_target = 68
    bs_found, bs_steps, bs_trace = binary_search_request_by_id(sorted_reqs_for_bs, bs_target, collect_trace=True)

    # 3. Priority Queue Demonstration
    pq_demo = EmergencyPriorityQueue()
    for case in sample_cases:
        pq_demo.push(case)
    pq_root = pq_demo.peek()
    pq_heap_before = pq_demo.to_list()
    pq_popped = pq_demo.pop()
    pq_heap_after = pq_demo.to_list()

    # 4. Dijkstra Shortest Path Demonstration (Disaster Safe Routing)
    from routing import build_manual_disaster_graph
    demo_hazards = [{
        "name": "Town Hall Underpass Flooding",
        "latitude": 10.9980,
        "longitude": 76.9610,
        "severity": "Flooded / Closed"
    }]
    clean_graph = build_manual_disaster_graph(active_hazards=[])
    dijkstra_clean = dijkstra_shortest_path(clean_graph, "gandhipuram_hub", "singanallur_hub", collect_trace=True)

    hazard_graph = build_manual_disaster_graph(active_hazards=demo_hazards)
    dijkstra_hazards = dijkstra_shortest_path(hazard_graph, "gandhipuram_hub", "singanallur_hub", collect_trace=True)

    # 5. Graph Traversals: BFS & DFS
    bfs_result = bfs_traversal(clean_graph, "gandhipuram_hub", max_hops=3, collect_trace=True)
    dfs_result = dfs_traversal(clean_graph, "gandhipuram_hub", target_node="singanallur_hub", collect_trace=True)

    return jsonify({
        "success": True,
        "algorithms": {
            "merge_sort": {
                "name": "Recursive Merge Sort",
                "time_complexity": "O(N log N)",
                "space_complexity": "O(N)",
                "input_count": len(sample_cases),
                "input_sample": sample_cases,
                "sorted_output": sorted_cases
            },
            "binary_search": {
                "name": "Iterative Binary Search",
                "time_complexity": "O(log N)",
                "space_complexity": "O(1)",
                "search_space": demo_ids,
                "target_id": bs_target,
                "found": bs_found is not None,
                "steps_taken": bs_steps,
                "trace": bs_trace
            },
            "priority_queue": {
                "name": "Array-Based Binary Max-Heap (Priority Queue)",
                "time_complexity": "O(1) peek, O(log N) push/pop",
                "root_peek": pq_root,
                "popped_highest_priority": pq_popped,
                "heap_array_length_before": len(pq_heap_before),
                "heap_array_length_after": len(pq_heap_after)
            },
            "dijkstra": {
                "name": "Dijkstra Shortest Path with Binary Min-Heap",
                "time_complexity": "O((V + E) log V)",
                "space_complexity": "O(V)",
                "start": "gandhipuram_hub",
                "destination": "singanallur_hub",
                "unpenalized_route": {
                    "path": dijkstra_clean["path"],
                    "distance_km": dijkstra_clean["distance"]
                },
                "hazard_penalized_route": {
                    "path": dijkstra_hazards["path"],
                    "distance_km": dijkstra_hazards["distance"],
                    "hazard_alerts": dijkstra_hazards["hazard_alerts"]
                }
            },
            "graph_traversals": {
                "name": "BFS Level-Order & DFS Depth-First Exploration",
                "time_complexity": "O(V + E)",
                "space_complexity": "O(V)",
                "start_node": "gandhipuram_hub",
                "bfs_wave_order": bfs_result["visited_order"],
                "bfs_hop_distances": bfs_result["hop_distances"],
                "dfs_order": dfs_result["visited_order"],
                "dfs_path_to_singanallur": dfs_result["path_to_target"]
            }
        }
    })


@app.route("/dsa")
def dsa_presentation_page():
    """
    Dedicated ADSA algorithms presentation & interactive lab page.
    Renders live execution controls, math explanations, and algorithm visualizations.
    """
    return render_template("dsa_lab.html")


# =========================================================
# SERVER RUN ENTRY POINT
# =========================================================

# Auto-initialize database on application boot (crucial for Vercel serverless)
try:
    with app.app_context():
        init_database()
except Exception as _boot_err:
    logger.warning("Database boot auto-initialization notice: %s", _boot_err)

if __name__ == "__main__":

    print()
    print("=" * 68)
    print("       SMART FLOOD EVACUATION & RESCUE SYSTEM - ADVANCED EDITION")
    print("=" * 68)
    print()
    print("SERVER : http://127.0.0.1:5000/")
    print()
    print("ADMIN CREDENTIALS")
    print("Username : admin")
    print("Password : admin123")
    print()
    print("RESCUE TEAM CREDENTIALS")
    print("Alpha Team   : alpha / alpha123   (Gandhipuram)")
    print("Bravo Team   : bravo / bravo123   (RS Puram)")
    print("Charlie Team : charlie / charlie123 (Ukkadam)")
    print()
    print("CITIZEN PORTAL")
    print("Register online or login with existing accounts.")
    print("=" * 68)
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
