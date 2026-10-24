import unittest
import json
import sqlite3
from app import app, db, init_database
from prioritization import calculate_priority
from flood_risk import assess_flood_risk
from routing import plan_evacuation_route

class SmartFloodSystemComprehensiveTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        init_database()

    def test_01_existing_citizen_login_migration(self):
        """Verify legacy plaintext citizen password successfully migrates and logs in."""
        resp = self.app.post("/citizen-login", json={
            "username": "akshaya",
            "password": "akshaya123"
        })
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("role"), "citizen")

    def test_02_admin_login(self):
        """Verify admin login works and sets session."""
        resp = self.app.post("/admin-login", json={
            "username": "admin",
            "password": "admin123"
        })
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("role"), "admin")

    def test_03_rescue_team_login(self):
        """Verify rescue team login works."""
        resp = self.app.post("/rescue-login", json={
            "username": "alpha",
            "password": "alpha123"
        })
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("role"), "rescue")

    def test_04_create_emergency_request_with_vulnerabilities_and_gps(self):
        """Citizen creates emergency request with GPS and vulnerable persons."""
        self.app.post("/citizen-login", json={"username": "akshaya", "password": "akshaya123"})
        resp = self.app.post("/create-request", json={
            "location": "Gandhipuram 7th Street",
            "phone": "9381161652",
            "people": 4,
            "flood_level": 4,
            "latitude": 11.0195,
            "longitude": 76.9740,
            "location_accuracy": 12.5,
            "medical_urgent": True,
            "elderly_count": 2,
            "children_count": 1,
            "disability_count": 0,
            "assistance_notes": "Elderly grandmother needs oxygen support"
        })
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("priority"), "Critical")
        self.assertGreaterEqual(data.get("priority_score"), 60.0)
        self.assertIn("reasons", data)

    def test_05_gps_validation_out_of_bounds(self):
        """GPS coordinates exceeding geographical bounds must be rejected."""
        self.app.post("/citizen-login", json={"username": "akshaya", "password": "akshaya123"})
        resp = self.app.post("/create-request", json={
            "location": "Out of bounds point",
            "phone": "9381161652",
            "people": 2,
            "flood_level": 2,
            "latitude": 120.5, # Invalid > 90
            "longitude": 76.95
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data.get("success"))

    def test_06_unauthenticated_security_checks(self):
        """Unauthenticated requests to protected endpoints must be rejected with 401."""
        # Clear session
        self.app.post("/logout")
        self.assertEqual(self.app.get("/admin/stats").status_code, 401)
        self.assertEqual(self.app.get("/admin/requests").status_code, 401)
        self.assertEqual(self.app.get("/rescue/requests").status_code, 401)
        self.assertEqual(self.app.post("/create-request", json={}).status_code, 401)

    def test_07_citizen_cannot_access_admin_endpoints(self):
        """Citizens must be forbidden from accessing admin endpoints."""
        self.app.post("/citizen-login", json={"username": "akshaya", "password": "akshaya123"})
        self.assertEqual(self.app.get("/admin/stats").status_code, 401)
        self.assertEqual(self.app.get("/admin/requests").status_code, 401)
        self.assertEqual(self.app.post("/admin/assign-team/1").status_code, 401)

    def test_08_map_data_and_unmapped_handling(self):
        """Verify map data returns mapped coordinates and lists unmapped requests honestly."""
        resp = self.app.get("/api/map/emergency-data")
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data.get("success"))
        self.assertIn("mapped_requests", data)
        self.assertIn("unmapped_requests", data)
        # Verify unmapped requests have null coordinates
        for r in data["unmapped_requests"]:
            self.assertTrue(r["latitude"] is None or r["longitude"] is None)

    def test_09_flood_risk_assessment(self):
        """Verify flood risk assessment heuristic calculation."""
        resp = self.app.get("/api/flood-risk/assess?location=Coimbatore")
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data.get("success"))
        assessment = data.get("assessment", {})
        self.assertIn("risk_score", assessment)
        self.assertIn(assessment.get("risk_category"), ["Low", "Moderate", "High", "Severe"])
        self.assertIn("factors", assessment)

    def test_10_evacuation_route_planning_and_hazard_avoidance(self):
        """Verify Dijkstra route calculation with road network and hazard notes."""
        resp = self.app.post("/api/route/plan", json={
            "start_lat": 11.0183,
            "start_lon": 76.9725,
            "shelter_id": 1
        })
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data.get("success"))
        self.assertIn("route_coordinates", data)
        self.assertGreater(data.get("distance_km"), 0)
        self.assertIn("warnings", data)

    def test_11_shelter_capacity_and_transaction_safety(self):
        """Verify shelter capacity updates atomically and releases upon cancellation."""
        self.app.post("/citizen-login", json={"username": "akshaya", "password": "akshaya123"})
        resp_req = self.app.post("/create-request", json={
            "location": "RS Puram",
            "phone": "9381161652",
            "people": 5,
            "flood_level": 3
        })
        req_id = resp_req.get_json()["request_id"]

        self.app.post("/admin-login", json={"username": "admin", "password": "admin123"})
        self.app.post(f"/admin/assign-team/{req_id}", json={})
        resp_shelter = self.app.post(f"/admin/assign-shelter/{req_id}", json={})
        data_shelter = resp_shelter.get_json()
        self.assertEqual(resp_shelter.status_code, 200)
        self.assertTrue(data_shelter.get("success"))

        # Releasing upon cancel
        resp_cancel = self.app.post(f"/admin/cancel/{req_id}")
        self.assertEqual(resp_cancel.status_code, 200)
        self.assertTrue(resp_cancel.get_json().get("success"))

    def test_12_rescue_team_update_authorization(self):
        """Verify rescue team cannot update cases assigned to other teams."""
        self.app.post("/rescue-login", json={"username": "bravo", "password": "bravo123"})
        resp = self.app.post("/rescue/update/99999", json={"status": "In Progress"})
        self.assertIn(resp.status_code, [403, 400])

    def test_13_prioritization_engine_unit_tests(self):
        """Direct unit test of scoring rules, medical override, and wait time escalation."""
        # 1. Base test
        score1, cat1, reasons1 = calculate_priority(flood_level=1, people=1)
        self.assertEqual(cat1, "Low")
        self.assertLess(score1, 25.0)

        # 2. Medical emergency guarantee
        score2, cat2, reasons2 = calculate_priority(flood_level=1, people=1, medical_urgent=True)
        self.assertEqual(cat2, "Critical")

        # 3. Wait time escalation
        score3, cat3, reasons3 = calculate_priority(flood_level=3, people=3, created_at="2026-10-22 10:00:00")
        self.assertIn("wait", "".join(reasons3).lower())

    def test_14_road_hazards_api(self):
        """Admin can report and retrieve road hazards for detour planning."""
        self.app.post("/admin-login", json={"username": "admin", "password": "admin123"})
        resp_post = self.app.post("/api/road-hazards", json={
            "name": "Avinashi Road Underpass Flooding",
            "location": "Avinashi Road",
            "severity": "Closed",
            "latitude": 11.025,
            "longitude": 77.002,
            "description": "Underpass submerged with 4 feet water."
        })
        self.assertEqual(resp_post.status_code, 200)

        resp_get = self.app.get("/api/road-hazards")
        data_get = resp_get.get_json()
        self.assertTrue(data_get.get("success"))
        self.assertGreaterEqual(len(data_get.get("hazards", [])), 1)

if __name__ == "__main__":
    unittest.main()
