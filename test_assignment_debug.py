from app import app, db
import unittest

class AssignmentWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_unauthenticated_blocked(self):
        """Unauthenticated user must be blocked with 401 and valid JSON."""
        res = self.client.post('/admin/assign-team/1', headers={'Content-Type': 'application/json'})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertIsNotNone(data)
        self.assertFalse(data['success'])
        self.assertIn("Admin login required", data['message'])

    def test_02_assign_team_empty_body_and_json_body(self):
        """Assign team must work with empty body, missing body, or JSON body."""
        # Login as admin
        log_res = self.client.post('/admin-login', json={'username':'admin', 'password':'admin123'})
        self.assertEqual(log_res.status_code, 200)

        # Create a pending request
        conn = db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO requests (citizen_id, citizen_name, phone, location, people, flood_level, priority, status, created_at, updated_at)
            VALUES (1, 'Test Citizen', '9876543210', 'Gandhipuram', 2, 2, 'Medium', 'Pending', '2026-10-22 12:00:00', '2026-10-22 12:00:00')
        """)
        req_id = cur.lastrowid
        cur.execute("UPDATE rescue_teams SET status = 'Available' WHERE id = 1")
        conn.commit()
        conn.close()

        # Call with headers ONLY (the exact bug reproduction condition!)
        res = self.client.post(f'/admin/assign-team/{req_id}', headers={'Content-Type': 'application/json'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsNotNone(data)
        self.assertTrue(data['success'])
        self.assertIn("Alpha Rescue Team", data['team'])

        # Double assignment check (should be prevented)
        res_double = self.client.post(f'/admin/assign-team/{req_id}', json={})
        self.assertEqual(res_double.status_code, 400)
        data_double = res_double.get_json()
        self.assertFalse(data_double['success'])
        self.assertIn("already in", data_double['message'])

        # Verify DB updates
        conn = db()
        r = conn.execute("SELECT status, assigned_team, assigned_team_id FROM requests WHERE id = ?", (req_id,)).fetchone()
        t = conn.execute("SELECT status FROM rescue_teams WHERE id = ?", (data['team_id'],)).fetchone()
        conn.close()
        self.assertEqual(r['status'], 'Assigned')
        self.assertEqual(t['status'], 'Busy')

    def test_03_no_teams_available_handling(self):
        """When all teams are busy, assignment returns clean 400 JSON error."""
        self.client.post('/admin-login', json={'username':'admin', 'password':'admin123'})

        conn = db()
        cur = conn.cursor()
        # Mark all teams busy
        cur.execute("UPDATE rescue_teams SET status = 'Busy'")
        # Create a pending request
        cur.execute("""
            INSERT INTO requests (citizen_id, citizen_name, phone, location, people, flood_level, priority, status, created_at, updated_at)
            VALUES (1, 'Test Citizen 2', '9876543210', 'Ukkadam', 1, 1, 'Low', 'Pending', '2026-10-22 12:00:00', '2026-10-22 12:00:00')
        """)
        req_id = cur.lastrowid
        conn.commit()
        conn.close()

        res = self.client.post(f'/admin/assign-team/{req_id}', json={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data['success'])
        self.assertIn("No rescue team is currently available", data['message'])

        # Reset teams to Available for normal operations
        conn = db()
        conn.execute("UPDATE rescue_teams SET status = 'Available'")
        conn.commit()
        conn.close()

    def test_04_assign_shelter_empty_body_and_json(self):
        """Assign shelter works without throwing 400 HTML error."""
        self.client.post('/admin-login', json={'username':'admin', 'password':'admin123'})

        conn = db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO requests (citizen_id, citizen_name, phone, location, people, flood_level, priority, status, created_at, updated_at)
            VALUES (1, 'Shelter Test Citizen', '9876543210', 'RS Puram', 3, 2, 'Medium', 'Pending', '2026-10-22 12:00:00', '2026-10-22 12:00:00')
        """)
        req_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Call with headers ONLY
        res = self.client.post(f'/admin/assign-shelter/{req_id}', headers={'Content-Type': 'application/json'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn("shelter", data)

if __name__ == '__main__':
    unittest.main()
