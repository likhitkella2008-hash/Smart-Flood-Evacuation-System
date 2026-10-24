"""
Turso LibSQL Database Synchronization Utility
=============================================
Uploads and synchronizes data from the local SQLite database (smart_flood_final.db)
to your remote Turso cloud database.

Usage:
    py turso_sync.py
    (or set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in environment / .env)
"""

import os
import sqlite3
import sys
import turso_db

LOCAL_DB_FILE = "smart_flood_final.db"


def load_env_file():
    """Simple parser for .env file if present."""
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k not in os.environ:
                        os.environ[k] = v


def sync_local_to_turso():
    load_env_file()
    turso_url = os.environ.get("TURSO_DATABASE_URL") or os.environ.get("LIBSQL_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN") or os.environ.get("LIBSQL_AUTH_TOKEN")

    print("=" * 65)
    print("   SMART FLOOD SYSTEM - TURSO CLOUD DATABASE SYNC UTILITY")
    print("=" * 65)

    if not turso_url:
        print("\n❌ Error: TURSO_DATABASE_URL environment variable is not set.")
        print("\nPlease set it via command line or in your .env file:")
        print("  set TURSO_DATABASE_URL=https://<your-db>-<org>.turso.io")
        print("  set TURSO_AUTH_TOKEN=<your-turso-token>")
        print("\nOr pass them interactively:")
        try:
            turso_url = input("Enter Turso Database URL: ").strip()
            turso_token = input("Enter Turso Auth Token: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)

        if not turso_url:
            print("❌ Turso Database URL required. Exiting.")
            sys.exit(1)

    if not os.path.exists(LOCAL_DB_FILE):
        print(f"\n❌ Local database '{LOCAL_DB_FILE}' not found.")
        sys.exit(1)

    print(f"\n1. Connecting to local database '{LOCAL_DB_FILE}'...")
    local_conn = sqlite3.connect(LOCAL_DB_FILE)
    local_conn.row_factory = sqlite3.Row

    print(f"2. Connecting to remote Turso database ({turso_url})...")
    remote_conn = turso_db.connect(turso_url, auth_token=turso_token)

    # Initialize schema on remote
    print("3. Initializing remote tables and schema...")
    from app import init_database
    # Temporarily point db() to remote
    old_db_func = sys.modules["app"].db
    sys.modules["app"].db = lambda: remote_conn
    try:
        init_database()
        print("   ✓ Remote tables verified.")
    finally:
        sys.modules["app"].db = old_db_func

    # Tables to migrate
    tables = ["citizens", "admins", "rescue_teams", "shelters", "requests", "road_hazards"]

    print("\n4. Synchronizing records from local database to Turso...")
    for table in tables:
        try:
            rows = local_conn.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                print(f"   - {table}: 0 local records to sync.")
                continue

            cols = rows[0].keys()
            placeholders = ", ".join(["?"] * len(cols))
            cols_str = ", ".join(cols)
            insert_sql = f"INSERT OR REPLACE INTO {table} ({cols_str}) VALUES ({placeholders})"

            count = 0
            for r in rows:
                vals = [r[c] for c in cols]
                remote_conn.execute(insert_sql, vals)
                count += 1
            print(f"   ✓ {table}: Synchronized {count} records.")
        except Exception as e:
            print(f"   ⚠️ Warning while syncing {table}: {e}")

    print("\n" + "=" * 65)
    print("🎉 Turso database synchronization completed successfully!")
    print("Your cloud database is now loaded with all local data.")
    print("=" * 65)


if __name__ == "__main__":
    sync_local_to_turso()
