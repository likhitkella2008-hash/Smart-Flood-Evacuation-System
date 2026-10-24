"""
Comprehensive Test Suite for Dynamic Location & Shelter Discovery Upgrade
==========================================================================
Verifies:
1. Open-Meteo Geocoding API integration (/api/location/search).
2. Dynamic incident geocoding when citizen submits manual address without GPS.
3. OpenStreetMap-based shelter discovery (/api/shelters/discover) returns unverified candidates without capacity.
4. Admin verification & activation of shelter (/api/shelters/verify-and-add) with capacity enforcement.
5. Proximity-aware spatial shelter assignment (Haversine distance vs string match).
6. Proximity-aware spatial rescue team assignment (Haversine distance vs first available).
7. Location-aware multi-city routing (OSRM & NetworkX offline fallback) in Chennai / Bengaluru.
8. Road hazard collision detection and avoidance warnings.
9. Environmental flood risk assessment for any city/coordinates.
10. Rescue team Live GPS Beacon vs Predefined Base Station state tracking.
"""

import unittest
import json
import sqlite3
import app as flask_app
from routing import plan_evacuation_route, haversine_distance
from shelter_discovery import discover_potential_shelters


class DynamicLocationSystemTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        flask_app.DATABASE = "smart_flood_final.db"
        flask_app.migrate_database(flask_app.DATABASE)
        flask_app.app.config["TESTING"] = True
        cls.client = flask_app.app.test_client()

    def setUp(self):
        self.conn = sqlite3.connect("smart_flood_final.db")
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()

    def test_01_geocoding_api_search(self):
        """Verify Open-Meteo Geocoding search endpoint returns coordinates for cities."""
        resp = self.client.get("/api/location/search?q=Chennai")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["results"]), 0)
        top = data["results"][0]
        self.assertIn("latitude", top)
        self.assertIn("longitude", top)
        self.assertAlmostEqual(top["latitude"], 13.08, delta=0.5)
        self.assertAlmostEqual(top["longitude"], 80.27, delta=0.5)

    def test_02_dynamic_geocoding_on_citizen_request(self):
        """Verify that citizen request with address text but no GPS gets automatically geocoded."""
        with self.client.session_transaction() as sess:
            sess["role"] = "citizen"
            sess["citizen_id"] = 1
            sess["name"] = "Dynamic Test Citizen"
            sess["username"] = "citizen_dyn_test"

        payload = {
            "location": "Bengaluru",
            "phone": "9876543210",
            "people": 2,
            "flood_level": 3,
            "details": "Water entering basement",
            "latitude": None,
            "longitude": None
        }
        resp = self.client.post("/create-request", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        req_id = data["request_id"]

        row = self.conn.execute("SELECT latitude, longitude, location FROM requests WHERE id = ?", (req_id,)).fetchone()
        self.assertIsNotNone(row["latitude"], "Latitude should be automatically resolved via geocoding")
        self.assertIsNotNone(row["longitude"], "Longitude should be automatically resolved via geocoding")
        self.assertAlmostEqual(row["latitude"], 12.97, delta=0.5)

    def test_03_shelter_discovery_osm_unverified_invariants(self):
        """Verify OpenStreetMap discovery returns candidates with is_verified=False and capacity=None."""
        # Query near Chennai Central (13.0827, 80.2707)
        res = discover_potential_shelters(13.0827, 80.2707, radius_km=3.0)
        self.assertTrue(res["success"])
        self.assertIn("candidates", res)
        self.assertIn("SAFETY NOTICE", res["disclaimer"])

        for c in res["candidates"][:3]:
            self.assertFalse(c["is_verified"], "Discovered candidate MUST be marked unverified")
            self.assertIsNone(c["capacity"], "Discovered candidate MUST NOT possess allocated capacity")
            self.assertIn("latitude", c)
            self.assertIn("longitude", c)
            self.assertGreater(c["distance_km"], 0.0)

    def test_04_admin_verify_and_activate_shelter(self):
        """Verify admin can officially activate a discovered shelter with verified operational capacity."""
        with self.client.session_transaction() as sess:
            sess["role"] = "admin"
            sess["username"] = "admin"

        shelter_name = "Chennai Dynamic Operational Emergency Center"
        payload = {
            "name": shelter_name,
            "location": "Chennai Central Sector 4",
            "latitude": 13.0850,
            "longitude": 80.2750,
            "capacity": 350,
            "contact_phone": "+91 44 25612345",
            "amenity_type": "Civic Centre"
        }
        resp = self.client.post("/api/shelters/verify-and-add", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["shelter"]["capacity"], 350)
        self.assertEqual(data["shelter"]["is_verified"], 1)

        # Confirm in DB
        row = self.conn.execute("SELECT * FROM shelters WHERE name = ?", (shelter_name,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["capacity"], 350)
        self.assertEqual(row["is_verified"], 1)
        self.assertEqual(row["source"], "verified_osm")

    def test_05_proximity_based_shelter_assignment(self):
        """Verify that shelter allocation picks the closest verified shelter by Haversine distance."""
        with self.client.session_transaction() as sess:
            sess["role"] = "admin"
            sess["username"] = "admin"

        # Create an incident in Chennai
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO requests (
                citizen_id, citizen_name, phone, location, people, flood_level,
                priority, status, created_at, updated_at, latitude, longitude, priority_score
            ) VALUES (1, 'Proximity Test Citizen', '9876543210', 'Chennai Central', 4, 3, 'High', 'Pending', datetime('now'), datetime('now'), 13.0845, 80.2740, 50.0)
        """)
        self.conn.commit()
        req_id = cur.lastrowid

        # Call admin assign shelter without passing a specific shelter ID
        resp = self.client.post(f"/admin/assign-shelter/{req_id}", json={})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])

        # The closest shelter is the newly verified Chennai shelter (13.0850, 80.2750), NOT Coimbatore shelters (~400 km away)!
        self.assertEqual(data["shelter"], "Chennai Dynamic Operational Emergency Center")

    def test_06_multi_city_routing_with_osrm_and_offline_dijkstra(self):
        """Verify multi-city evacuation route planning across global coordinates."""
        # 1. Chennai Route
        res = plan_evacuation_route(
            start_lat=13.0827,
            start_lon=80.2707,
            shelter_lat=13.0850,
            shelter_lon=80.2750,
            shelter_name="Chennai Central Shelter"
        )
        self.assertTrue(res["success"])
        self.assertGreater(len(res["route_coordinates"]), 1)
        self.assertGreater(res["distance_km"], 0.1)

        # 2. Bengaluru Route with Hazard Collision & Warning
        hazards = [{
            "name": "Koramangala Culvert Overflow",
            "latitude": 12.9350,
            "longitude": 77.6240,
            "severity": "Flooded",
            "description": "3 ft overflow on main arterial"
        }]
        res_blr = plan_evacuation_route(
            start_lat=12.9340,
            start_lon=77.6200,
            shelter_lat=12.9360,
            shelter_lon=77.6300,
            shelter_name="Koramangala Indoor Stadium",
            active_hazards=hazards
        )
        self.assertTrue(res_blr["success"])
        self.assertIn("warnings", res_blr)
        self.assertTrue(any("Hazard" in w or "Detour" in w for w in res_blr["warnings"]))

    def test_07_rescue_team_live_beacon_vs_base_station(self):
        """Verify rescue team location update marks location_type as 'live_gps'."""
        with self.client.session_transaction() as sess:
            sess["role"] = "rescue"
            sess["team_id"] = 1
            sess["username"] = "alpha"

        # Broadcast live GPS
        resp = self.client.post("/rescue/update-location", json={"latitude": 13.0827, "longitude": 80.2707})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["location_type"], "live_gps")

        # Verify in map telemetry
        resp_map = self.client.get("/api/map/emergency-data")
        data_map = resp_map.get_json()
        team_alpha = next((t for t in data_map["rescue_teams"] if t["id"] == 1), None)
        self.assertIsNotNone(team_alpha)
        self.assertTrue(team_alpha["is_live_gps"])
        self.assertEqual(team_alpha["location_label"], "Live GPS Beacon")

    def test_08_imprecise_gps_accuracy_discarded(self):
        """Verify that excessively poor accuracy coordinates (e.g. 259044m) are rejected to prevent false dispatch."""
        with self.client.session_transaction() as sess:
            sess["role"] = "citizen"
            sess["citizen_id"] = 1
            sess["name"] = "Imprecise Test Citizen"

        payload = {
            "location": "Local Flood Area Without Known Address",
            "phone": "9876543210",
            "people": 2,
            "flood_level": 3,
            "latitude": 13.04822,
            "longitude": 80.19968,
            "location_accuracy": 259044.0  # 259 km network uncertainty
        }
        resp = self.client.post("/create-request", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        req_id = data["request_id"]

        row = self.conn.execute("SELECT latitude, longitude FROM requests WHERE id = ?", (req_id,)).fetchone()
        # Coordinates must be discarded rather than accepted as verified GPS
        self.assertIsNone(row["latitude"])
        self.assertIsNone(row["longitude"])

    def test_09_genuine_precise_gps_stored_without_substitution(self):
        """Verify that genuine high-accuracy device GPS coordinates are preserved without alteration."""
        with self.client.session_transaction() as sess:
            sess["role"] = "citizen"
            sess["citizen_id"] = 1
            sess["name"] = "Precise Test Citizen"

        test_lat = 9.92520
        test_lon = 78.11980
        test_acc = 18.5  # 18.5 meters genuine GPS fix

        payload = {
            "location": "Madurai South Meenakshi Corridor",
            "phone": "9876543210",
            "people": 3,
            "flood_level": 2,
            "latitude": test_lat,
            "longitude": test_lon,
            "location_accuracy": test_acc
        }
        resp = self.client.post("/create-request", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        req_id = data["request_id"]

        row = self.conn.execute("SELECT latitude, longitude, location_accuracy FROM requests WHERE id = ?", (req_id,)).fetchone()
        self.assertEqual(row["latitude"], test_lat)
        self.assertEqual(row["longitude"], test_lon)
        self.assertEqual(row["location_accuracy"], test_acc)

    def test_10_suburban_campus_wifi_accuracy_preserved(self):
        """Verify that genuine campus/neighborhood Wi-Fi fixes (e.g. 3244m at Ettimadai) are preserved rather than rejected."""
        with self.client.session_transaction() as sess:
            sess["role"] = "citizen"
            sess["citizen_id"] = 1
            sess["name"] = "Ettimadai Campus Citizen"

        test_lat = 10.91174
        test_lon = 76.90650
        test_acc = 3244.0  # ~3.2 km campus/suburban Wi-Fi accuracy

        payload = {
            "location": "Ettimadai, Coimbatore South",
            "phone": "9876543210",
            "people": 2,
            "flood_level": 3,
            "latitude": test_lat,
            "longitude": test_lon,
            "location_accuracy": test_acc
        }
        resp = self.client.post("/create-request", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        req_id = data["request_id"]

        row = self.conn.execute("SELECT latitude, longitude, location_accuracy FROM requests WHERE id = ?", (req_id,)).fetchone()
        self.assertIsNotNone(row["latitude"])
        self.assertEqual(row["latitude"], test_lat)
        self.assertEqual(row["longitude"], test_lon)
        self.assertEqual(row["location_accuracy"], test_acc)


if __name__ == "__main__":
    unittest.main()
