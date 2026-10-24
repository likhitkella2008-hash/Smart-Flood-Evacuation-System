from flask import Flask, render_template, request, jsonify, session
import sqlite3
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "SMART_FLOOD_SECRET_2026"

DATABASE = "smart_flood_final.db"


# =========================================================
# DATABASE
# =========================================================

def db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_database():

    conn = db()
    cur = conn.cursor()

    # -----------------------------------------------------
    # CITIZENS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # RESCUE TEAMS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # SHELTERS
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS shelters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            occupied INTEGER NOT NULL DEFAULT 0
        )
    """)

    # -----------------------------------------------------
    # EMERGENCY REQUESTS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # NOTIFICATIONS
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            citizen_id INTEGER NOT NULL,

            message TEXT NOT NULL,

            is_read INTEGER NOT NULL DEFAULT 0,

            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # -----------------------------------------------------
    # DEFAULT ADMIN
    # -----------------------------------------------------

    cur.execute("""
        SELECT id
        FROM admins
        WHERE username = 'admin'
    """)

    if cur.fetchone() is None:

        cur.execute("""
            INSERT INTO admins
            (username, password)
            VALUES (?, ?)
        """, (
            "admin",
            "admin123"
        ))

    # -----------------------------------------------------
    # DEFAULT RESCUE TEAMS
    # -----------------------------------------------------

    teams = [
        (
            "Alpha Rescue Team",
            "alpha",
            "alpha123",
            "Gandhipuram"
        ),
        (
            "Bravo Rescue Team",
            "bravo",
            "bravo123",
            "RS Puram"
        ),
        (
            "Charlie Rescue Team",
            "charlie",
            "charlie123",
            "Ukkadam"
        )
    ]

    for team in teams:

        cur.execute("""
            SELECT id
            FROM rescue_teams
            WHERE username = ?
        """, (team[1],))

        if cur.fetchone() is None:

            cur.execute("""
                INSERT INTO rescue_teams
                (
                    team_name,
                    username,
                    password,
                    location,
                    status
                )
                VALUES (?, ?, ?, ?, 'Available')
            """, team)

    # -----------------------------------------------------
    # DEFAULT SHELTERS
    # -----------------------------------------------------

    shelters = [
        (
            "Government Higher Secondary School",
            "Gandhipuram",
            500
        ),
        (
            "Corporation Community Hall",
            "RS Puram",
            300
        ),
        (
            "Government School Shelter",
            "Ukkadam",
            350
        ),
        (
            "Amrita Emergency Shelter",
            "Coimbatore",
            400
        )
    ]

    for shelter in shelters:

        cur.execute("""
            SELECT id
            FROM shelters
            WHERE name = ?
        """, (shelter[0],))

        if cur.fetchone() is None:

            cur.execute("""
                INSERT INTO shelters
                (
                    name,
                    location,
                    capacity,
                    occupied
                )
                VALUES (?, ?, ?, 0)
            """, shelter)

    conn.commit()
    conn.close()


# =========================================================
# HELPERS
# =========================================================

def priority(flood_level, people):

    if flood_level >= 5 or people >= 10:
        return "Critical"

    if flood_level >= 4 or people >= 5:
        return "High"

    if flood_level >= 3:
        return "Medium"

    return "Low"


def add_notification(citizen_id, message):

    conn = db()

    conn.execute("""
        INSERT INTO notifications
        (
            citizen_id,
            message,
            created_at
        )
        VALUES (?, ?, ?)
    """, (
        citizen_id,
        message,
        now()
    ))

    conn.commit()
    conn.close()


def send_sms(phone, message):

    print()
    print("=" * 60)
    print("SMS NOTIFICATION")
    print("=" * 60)
    print("PHONE :", phone)
    print("TEXT  :", message)
    print("=" * 60)
    print()


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


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")
# =========================================================
# LIVE WEATHER REPORT
# =========================================================

@app.route("/api/weather")
def live_weather():
    city = request.args.get("city", "Coimbatore").strip()

    if not city:
        return jsonify({
            "success": False,
            "message": "Please enter a city name."
        }), 400

    try:
        # Find the city's coordinates
        geo_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json"
            },
            timeout=10
        )
        geo_response.raise_for_status()

        locations = geo_response.json().get("results", [])

        if not locations:
            return jsonify({
                "success": False,
                "message": "Location not found."
            }), 404

        location = locations[0]

        # Fetch current weather
        weather_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "precipitation,"
                    "rain,"
                    "wind_speed_10m,"
                    "weather_code"
                ),
                "hourly": "precipitation",
                "forecast_days": 1,
                "timezone": "auto"
            },
            timeout=10
        )
        weather_response.raise_for_status()

        data = weather_response.json()
        current = data.get("current", {})

        return jsonify({
            "success": True,
            "location": location.get("name", city),
            "region": location.get("admin1", ""),
            "country": location.get("country", ""),
            "temperature_c": current.get("temperature_2m"),
            "humidity_percent": current.get(
                "relative_humidity_2m"
            ),
            "precipitation_mm": current.get("precipitation"),
            "rain_mm": current.get("rain"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
            "weather_time": current.get("time"),
            "hourly_forecast": data.get("hourly", {})
        })

    except requests.RequestException:
        return jsonify({
            "success": False,
            "message": "Unable to retrieve weather data. "
                       "Check your internet connection."
        }), 502


# =========================================================
# SESSION
# =========================================================

@app.route("/session")
def get_session():

    if not session.get("logged_in"):

        return jsonify({
            "logged_in": False
        })

    return jsonify({
        "logged_in": True,
        "role": session.get("role"),
        "name": session.get("name"),
        "username": session.get("username"),
        "phone": session.get("phone"),
        "team_name": session.get("team_name")
    })


# =========================================================
# CITIZEN REGISTRATION
# =========================================================

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json() or {}

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

    conn = db()

    try:

        conn.execute("""
            INSERT INTO citizens
            (
                name,
                username,
                password,
                phone,
                location,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            username,
            password,
            phone,
            location,
            now()
        ))

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


# =========================================================
# CITIZEN LOGIN
# =========================================================

@app.route("/citizen-login", methods=["POST"])
def citizen_login():

    data = request.get_json() or {}

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = db()

    citizen = conn.execute("""
        SELECT *
        FROM citizens
        WHERE username = ?
        AND password = ?
    """, (
        username,
        password
    )).fetchone()

    conn.close()

    if citizen is None:

        return jsonify({
            "success": False,
            "message": "Invalid citizen username or password."
        })

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


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/admin-login", methods=["POST"])
def admin_login():

    data = request.get_json() or {}

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = db()

    admin = conn.execute("""
        SELECT *
        FROM admins
        WHERE username = ?
        AND password = ?
    """, (
        username,
        password
    )).fetchone()

    conn.close()

    if admin is None:

        return jsonify({
            "success": False,
            "message": "Invalid admin username or password."
        })

    session.clear()

    session["logged_in"] = True
    session["role"] = "admin"
    session["name"] = "Administrator"
    session["username"] = username

    return jsonify({
        "success": True,
        "role": "admin"
    })


# =========================================================
# RESCUE LOGIN
# =========================================================

@app.route("/rescue-login", methods=["POST"])
def rescue_login():

    data = request.get_json() or {}

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = db()

    team = conn.execute("""
        SELECT *
        FROM rescue_teams
        WHERE username = ?
        AND password = ?
    """, (
        username,
        password
    )).fetchone()

    conn.close()

    if team is None:

        return jsonify({
            "success": False,
            "message": "Invalid rescue team username or password."
        })

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


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "success": True
    })


# =========================================================
# CREATE EMERGENCY REQUEST
# =========================================================

@app.route("/create-request", methods=["POST"])
def create_request():

    check = citizen_only()

    if check:
        return check

    data = request.get_json() or {}

    location = data.get("location", "").strip()
    phone = data.get("phone", "").strip()
    details = data.get("details", "").strip()

    try:

        people = int(data.get("people", 1))
        flood_level = int(data.get("flood_level", 1))

    except (ValueError, TypeError):

        return jsonify({
            "success": False,
            "message": "Invalid people or flood level."
        })

    if not location:

        return jsonify({
            "success": False,
            "message": "Location is required."
        })

    if not phone:

        return jsonify({
            "success": False,
            "message": "Emergency phone is required."
        })

    if people < 1:

        return jsonify({
            "success": False,
            "message": "Number of people must be at least 1."
        })

    if flood_level < 1 or flood_level > 5:

        return jsonify({
            "success": False,
            "message": "Flood level must be between 1 and 5."
        })

    citizen_id = session["citizen_id"]
    citizen_name = session["name"]

    request_priority = priority(
        flood_level,
        people
    )

    conn = db()

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO requests
        (
            citizen_id,
            citizen_name,
            phone,
            location,
            people,
            flood_level,
            details,
            priority,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
    """, (
        citizen_id,
        citizen_name,
        phone,
        location,
        people,
        flood_level,
        details,
        request_priority,
        now(),
        now()
    ))

    request_id = cur.lastrowid

    conn.commit()
    conn.close()

    add_notification(
        citizen_id,
        f"Emergency request #{request_id} submitted successfully. "
        f"Waiting for administrator approval."
    )

    send_sms(
        phone,
        f"Smart Flood: Request #{request_id} received. "
        f"Status: Pending. Administrator will review your request."
    )

    return jsonify({
        "success": True,
        "request_id": request_id,
        "message": "Emergency request submitted successfully."
    })


# =========================================================
# CITIZEN REQUESTS
# =========================================================

@app.route("/my-requests")
def my_requests():

    check = citizen_only()

    if check:
        return check

    citizen_id = session["citizen_id"]

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM requests
        WHERE citizen_id = ?
        ORDER BY id DESC
    """, (
        citizen_id,
    )).fetchall()

    conn.close()

    result = []

    for row in rows:

        result.append(dict(row))

    return jsonify({
        "success": True,
        "requests": result
    })


# =========================================================
# CITIZEN NOTIFICATIONS
# =========================================================

@app.route("/notifications")
def notifications():

    check = citizen_only()

    if check:
        return check

    citizen_id = session["citizen_id"]

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM notifications
        WHERE citizen_id = ?
        ORDER BY id DESC
        LIMIT 20
    """, (
        citizen_id,
    )).fetchall()

    conn.close()

    result = []

    for row in rows:

        result.append(dict(row))

    return jsonify({
        "success": True,
        "notifications": result
    })


# =========================================================
# ADMIN STATISTICS
# =========================================================

@app.route("/admin/stats")
def admin_stats():

    check = admin_only()

    if check:
        return check

    conn = db()

    total = conn.execute("""
        SELECT COUNT(*)
        FROM requests
    """).fetchone()[0]

    pending = conn.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE status = 'Pending'
    """).fetchone()[0]

    assigned = conn.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE status = 'Assigned'
    """).fetchone()[0]

    progress = conn.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE status = 'In Progress'
    """).fetchone()[0]

    rescued = conn.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE status = 'Rescued'
    """).fetchone()[0]

    teams = conn.execute("""
        SELECT COUNT(*)
        FROM rescue_teams
        WHERE status = 'Available'
    """).fetchone()[0]

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


# =========================================================
# ADMIN ALL REQUESTS
# =========================================================

@app.route("/admin/requests")
def admin_requests():

    check = admin_only()

    if check:
        return check

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM requests
        ORDER BY
            CASE priority
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                ELSE 4
            END,
            id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "requests": [dict(row) for row in rows]
    })


# =========================================================
# ADMIN RESCUE TEAMS
# =========================================================

@app.route("/admin/teams")
def admin_teams():

    check = admin_only()

    if check:
        return check

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM rescue_teams
        ORDER BY id
    """).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "teams": [dict(row) for row in rows]
    })


# =========================================================
# ADMIN SHELTERS
# =========================================================

@app.route("/admin/shelters")
def admin_shelters():

    check = admin_only()

    if check:
        return check

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM shelters
        ORDER BY id
    """).fetchall()

    conn.close()

    shelters = []

    for row in rows:

        item = dict(row)

        item["available"] = (
            row["capacity"] -
            row["occupied"]
        )

        shelters.append(item)

    return jsonify({
        "success": True,
        "shelters": shelters
    })


# =========================================================
# ADMIN ACCEPT + ASSIGN NEAREST TEAM
# =========================================================

@app.route(
    "/admin/assign-team/<int:request_id>",
    methods=["POST"]
)
def admin_assign_team(request_id):

    check = admin_only()

    if check:
        return check

    conn = db()

    emergency = conn.execute("""
        SELECT *
        FROM requests
        WHERE id = ?
    """, (
        request_id,
    )).fetchone()

    if emergency is None:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Emergency case not found."
        })

    if emergency["status"] != "Pending":

        conn.close()

        return jsonify({
            "success": False,
            "message": "This case has already been processed."
        })

    # -----------------------------------------------------
    # FIRST TRY LOCATION MATCH
    # -----------------------------------------------------

    team = conn.execute("""
        SELECT *
        FROM rescue_teams
        WHERE status = 'Available'
        AND LOWER(location) = LOWER(?)
        LIMIT 1
    """, (
        emergency["location"],
    )).fetchone()

    # -----------------------------------------------------
    # OTHERWISE FIRST AVAILABLE TEAM
    # -----------------------------------------------------

    if team is None:

        team = conn.execute("""
            SELECT *
            FROM rescue_teams
            WHERE status = 'Available'
            ORDER BY id
            LIMIT 1
        """).fetchone()

    if team is None:

        conn.close()

        return jsonify({
            "success": False,
            "message": "No rescue team is currently available."
        })

    # -----------------------------------------------------
    # ASSIGN
    # -----------------------------------------------------

    conn.execute("""
        UPDATE requests
        SET
            status = 'Assigned',
            assigned_team_id = ?,
            assigned_team = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        team["id"],
        team["team_name"],
        now(),
        request_id
    ))

    conn.execute("""
        UPDATE rescue_teams
        SET status = 'Busy'
        WHERE id = ?
    """, (
        team["id"],
    ))

    conn.commit()
    conn.close()

    # -----------------------------------------------------
    # CITIZEN NOTIFICATION
    # -----------------------------------------------------

    message = (
        f"Your emergency request #{request_id} "
        f"has been accepted by the administrator. "
        f"{team['team_name']} has been assigned to your rescue."
    )

    add_notification(
        emergency["citizen_id"],
        message
    )

    send_sms(
        emergency["phone"],
        message
    )

    return jsonify({
        "success": True,
        "message": "Rescue team assigned successfully.",
        "team": team["team_name"]
    })


# =========================================================
# ADMIN ASSIGN SHELTER
# =========================================================

@app.route(
    "/admin/assign-shelter/<int:request_id>",
    methods=["POST"]
)
def admin_assign_shelter(request_id):

    check = admin_only()

    if check:
        return check

    conn = db()

    emergency = conn.execute("""
        SELECT *
        FROM requests
        WHERE id = ?
    """, (
        request_id,
    )).fetchone()

    if emergency is None:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Emergency case not found."
        })

    # Find nearest/suitable shelter.
    # Since this demo does not use GPS coordinates,
    # location is matched first.

    shelter = conn.execute("""
        SELECT *
        FROM shelters
        WHERE
            LOWER(location) = LOWER(?)
            AND (capacity - occupied) >= ?
        LIMIT 1
    """, (
        emergency["location"],
        emergency["people"]
    )).fetchone()

    if shelter is None:

        shelter = conn.execute("""
            SELECT *
            FROM shelters
            WHERE
                (capacity - occupied) >= ?
            ORDER BY
                (capacity - occupied) ASC
            LIMIT 1
        """, (
            emergency["people"],
        )).fetchone()

    if shelter is None:

        conn.close()

        return jsonify({
            "success": False,
            "message": "No shelter has enough available capacity."
        })

    # -----------------------------------------------------
    # ASSIGN SHELTER
    # -----------------------------------------------------

    conn.execute("""
        UPDATE requests
        SET
            shelter_id = ?,
            shelter = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        shelter["id"],
        shelter["name"],
        now(),
        request_id
    ))

    conn.execute("""
        UPDATE shelters
        SET occupied = occupied + ?
        WHERE id = ?
    """, (
        emergency["people"],
        shelter["id"]
    ))

    conn.commit()
    conn.close()

    message = (
        f"Safe shelter assigned for emergency request "
        f"#{request_id}: {shelter['name']}."
    )

    add_notification(
        emergency["citizen_id"],
        message
    )

    send_sms(
        emergency["phone"],
        message
    )

    return jsonify({
        "success": True,
        "message": "Shelter assigned successfully.",
        "shelter": shelter["name"]
    })


# =========================================================
# ADMIN CANCEL REQUEST
# =========================================================

@app.route(
    "/admin/cancel/<int:request_id>",
    methods=["POST"]
)
def admin_cancel(request_id):

    check = admin_only()

    if check:
        return check

    conn = db()

    emergency = conn.execute("""
        SELECT *
        FROM requests
        WHERE id = ?
    """, (
        request_id,
    )).fetchone()

    if emergency is None:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Emergency case not found."
        })

    # Release rescue team.

    if emergency["assigned_team_id"]:

        conn.execute("""
            UPDATE rescue_teams
            SET status = 'Available'
            WHERE id = ?
        """, (
            emergency["assigned_team_id"],
        ))

    # Release shelter capacity.

    if emergency["shelter_id"]:

        conn.execute("""
            UPDATE shelters
            SET occupied =
                MAX(0, occupied - ?)
            WHERE id = ?
        """, (
            emergency["people"],
            emergency["shelter_id"]
        ))

    conn.execute("""
        UPDATE requests
        SET
            status = 'Cancelled',
            updated_at = ?
        WHERE id = ?
    """, (
        now(),
        request_id
    ))

    conn.commit()
    conn.close()

    message = (
        f"Emergency request #{request_id} "
        f"has been cancelled by the administrator."
    )

    add_notification(
        emergency["citizen_id"],
        message
    )

    send_sms(
        emergency["phone"],
        message
    )

    return jsonify({
        "success": True,
        "message": "Emergency request cancelled."
    })


# =========================================================
# RESCUE TEAM REQUESTS
# =========================================================

@app.route("/rescue/requests")
def rescue_requests():

    check = rescue_only()

    if check:
        return check

    team_id = session["team_id"]

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM requests
        WHERE assigned_team_id = ?
        AND status IN ('Assigned', 'In Progress')
        ORDER BY id DESC
    """, (
        team_id,
    )).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "requests": [dict(row) for row in rows]
    })


# =========================================================
# RESCUE START / COMPLETE
# =========================================================

@app.route(
    "/rescue/update/<int:request_id>",
    methods=["POST"]
)
def rescue_update(request_id):

    check = rescue_only()

    if check:
        return check

    data = request.get_json() or {}

    status = data.get("status")

    if status not in [
        "In Progress",
        "Rescued"
    ]:

        return jsonify({
            "success": False,
            "message": "Invalid status."
        })

    team_id = session["team_id"]

    conn = db()

    emergency = conn.execute("""
        SELECT *
        FROM requests
        WHERE id = ?
        AND assigned_team_id = ?
    """, (
        request_id,
        team_id
    )).fetchone()

    if emergency is None:

        conn.close()

        return jsonify({
            "success": False,
            "message": "This case is not assigned to your team."
        })

    conn.execute("""
        UPDATE requests
        SET
            status = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        status,
        now(),
        request_id
    ))

    # When rescue is completed,
    # release the team.

    if status == "Rescued":

        conn.execute("""
            UPDATE rescue_teams
            SET status = 'Available'
            WHERE id = ?
        """, (
            team_id,
        ))

    conn.commit()
    conn.close()

    if status == "In Progress":

        message = (
            f"Rescue team has started responding "
            f"to emergency request #{request_id}."
        )

    else:

        message = (
            f"Rescue completed successfully "
            f"for emergency request #{request_id}."
        )

    add_notification(
        emergency["citizen_id"],
        message
    )

    send_sms(
        emergency["phone"],
        message
    )

    return jsonify({
        "success": True,
        "message": message
    })


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    init_database()

    print()
    print("=" * 65)
    print("       SMART FLOOD EVACUATION & RESCUE SYSTEM")
    print("=" * 65)
    print()
    print("SERVER")
    print("http://127.0.0.1:5000/")
    print()
    print("ADMIN")
    print("Username : admin")
    print("Password : admin123")
    print()
    print("RESCUE TEAMS")
    print("Alpha   : alpha / alpha123")
    print("Bravo   : bravo / bravo123")
    print("Charlie : charlie / charlie123")
    print()
    print("CITIZEN")
    print("Register through the website.")
    print()
    print("=" * 65)
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )