import sqlite3
import os

DATABASES = ["smart_flood_final.db", "smart_flood.db"]

COIMBATORE_SHELTER_COORDS = {
    "Government Higher Secondary School": (11.0180, 76.9720, "+91 422 2521101"),
    "Corporation Community Hall": (11.0085, 76.9485, "+91 422 2548822"),
    "Government School Shelter": (10.9900, 76.9600, "+91 422 2390014"),
    "Amrita Emergency Shelter": (10.9020, 76.9030, "+91 422 2685000")
}

COIMBATORE_TEAM_COORDS = {
    "alpha": (11.0185, 76.9730, "+91 9443011221"),
    "bravo": (11.0095, 76.9495, "+91 9443011222"),
    "charlie": (10.9910, 76.9610, "+91 9443011223")
}

def migrate_database(db_path):
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist, skipping.")
        return

    print(f"Running safe migration on: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Requests table additions
    cur.execute("PRAGMA table_info(requests)")
    req_cols = [r["name"] for r in cur.fetchall()]

    new_req_cols = [
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("location_accuracy", "REAL"),
        ("priority_score", "REAL DEFAULT 0"),
        ("priority_reasons", "TEXT"),
        ("elderly_count", "INTEGER DEFAULT 0"),
        ("children_count", "INTEGER DEFAULT 0"),
        ("disability_count", "INTEGER DEFAULT 0"),
        ("medical_urgent", "INTEGER DEFAULT 0"),
        ("assistance_notes", "TEXT"),
        ("completion_notes", "TEXT")
    ]

    for col_name, col_type in new_req_cols:
        if col_name not in req_cols:
            print(f"  Adding column {col_name} ({col_type}) to requests")
            cur.execute(f"ALTER TABLE requests ADD COLUMN {col_name} {col_type}")

    # 2. Rescue teams table additions
    cur.execute("PRAGMA table_info(rescue_teams)")
    team_cols = [r["name"] for r in cur.fetchall()]

    new_team_cols = [
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("last_location_update", "TEXT"),
        ("phone", "TEXT"),
        ("location_type", "TEXT DEFAULT 'base_station'")
    ]

    for col_name, col_type in new_team_cols:
        if col_name not in team_cols:
            print(f"  Adding column {col_name} ({col_type}) to rescue_teams")
            cur.execute(f"ALTER TABLE rescue_teams ADD COLUMN {col_name} {col_type}")

    # 3. Shelters table additions
    cur.execute("PRAGMA table_info(shelters)")
    shelter_cols = [r["name"] for r in cur.fetchall()]

    new_shelter_cols = [
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("contact_phone", "TEXT"),
        ("is_verified", "INTEGER DEFAULT 1"),
        ("source", "TEXT DEFAULT 'verified_db'"),
        ("amenity_type", "TEXT DEFAULT 'shelter'")
    ]

    for col_name, col_type in new_shelter_cols:
        if col_name not in shelter_cols:
            print(f"  Adding column {col_name} ({col_type}) to shelters")
            cur.execute(f"ALTER TABLE shelters ADD COLUMN {col_name} {col_type}")

    # 4. Road Hazards table for Evacuation Routing
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

    # Populate known coordinates for shelters if null
    for name, (lat, lon, phone) in COIMBATORE_SHELTER_COORDS.items():
        cur.execute("""
            UPDATE shelters
            SET latitude = ?, longitude = ?, contact_phone = COALESCE(contact_phone, ?)
            WHERE name = ? AND latitude IS NULL
        """, (lat, lon, phone, name))

    # Populate known coordinates for rescue teams if null
    for username, (lat, lon, phone) in COIMBATORE_TEAM_COORDS.items():
        cur.execute("""
            UPDATE rescue_teams
            SET latitude = ?, longitude = ?, phone = COALESCE(phone, ?)
            WHERE username = ? AND latitude IS NULL
        """, (lat, lon, phone, username))

    # Calculate initial priority_score for existing requests if null or 0
    cur.execute("SELECT id, flood_level, people FROM requests WHERE priority_score IS NULL OR priority_score = 0")
    old_requests = cur.fetchall()
    for req in old_requests:
        # Base scoring calculation
        fl = req["flood_level"] or 1
        ppl = req["people"] or 1
        score = (fl * 7) + min(ppl * 3, 30)
        reasons = f"Reported flood level {fl}/5; {ppl} people affected"
        cur.execute("UPDATE requests SET priority_score = ?, priority_reasons = ? WHERE id = ?", (score, reasons, req["id"]))

    conn.commit()
    conn.close()
    print(f"Migration completed successfully for {db_path}!")

if __name__ == "__main__":
    for db in DATABASES:
        migrate_database(db)
