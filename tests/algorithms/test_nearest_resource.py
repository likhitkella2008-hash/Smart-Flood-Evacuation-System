"""
Unit tests for Single-Pass Nearest-Resource Selection (algorithms/nearest_resource.py)
"""

import unittest
from algorithms.nearest_resource import (
    find_nearest_available_team,
    find_nearest_suitable_shelter,
    find_nearest_resource,
    haversine_distance
)


class TestNearestResource(unittest.TestCase):
    """Verifies manual single-pass O(N) selection algorithm."""

    def setUp(self):
        # Emergency incident at Gandhipuram (11.0183, 76.9725)
        self.emergency = {
            "id": 101,
            "latitude": 11.0183,
            "longitude": 76.9725,
            "people": 4
        }

        # Candidate rescue teams
        self.teams = [
            {"id": 1, "team_name": "Far Team", "status": "Available", "latitude": 10.9020, "longitude": 76.9030}, # ~15 km
            {"id": 2, "team_name": "Closest Team", "status": "Available", "latitude": 11.0210, "longitude": 76.9680}, # ~0.6 km
            {"id": 3, "team_name": "Mid Team", "status": "Available", "latitude": 10.9980, "longitude": 76.9610}, # ~2.5 km
            {"id": 4, "team_name": "Super Close But Busy", "status": "Busy", "latitude": 11.0185, "longitude": 76.9726}, # 0.02 km but BUSY
        ]

        # Candidate shelters
        self.shelters = [
            {
                "id": 10,
                "shelter_name": "Unverified Near Hall",
                "is_verified": 0,
                "capacity": 100,
                "occupied": 10,
                "latitude": 11.0190,
                "longitude": 76.9720
            },
            {
                "id": 20,
                "shelter_name": "Full Verified Hall",
                "is_verified": 1,
                "capacity": 50,
                "occupied": 50, # 0 capacity remaining
                "latitude": 11.0200,
                "longitude": 76.9710
            },
            {
                "id": 30,
                "shelter_name": "Verified Closest Available",
                "is_verified": 1,
                "capacity": 100,
                "occupied": 20, # 80 capacity remaining (needs 4)
                "latitude": 11.0089,
                "longitude": 76.9550
            },
            {
                "id": 40,
                "shelter_name": "Verified Far Available",
                "is_verified": 1,
                "capacity": 200,
                "occupied": 0,
                "latitude": 10.9490,
                "longitude": 76.9710
            }
        ]

    def test_find_nearest_available_team_success(self):
        """Finds closest team that is strictly Available."""
        team = find_nearest_available_team(self.emergency, self.teams)
        self.assertIsNotNone(team)
        self.assertEqual(team["id"], 2)
        self.assertEqual(team["team_name"], "Closest Team")

    def test_find_nearest_available_team_ignores_busy_units(self):
        """Even if a Busy unit is 20 meters away, it is ignored in favor of an Available unit."""
        team = find_nearest_available_team(self.emergency, self.teams)
        self.assertNotEqual(team["id"], 4)

    def test_find_nearest_available_team_all_busy_returns_none(self):
        """Returns None if every candidate team is Busy."""
        busy_teams = [{"id": 1, "status": "Busy", "latitude": 11.0, "longitude": 76.9}]
        self.assertIsNone(find_nearest_available_team(self.emergency, busy_teams))

    def test_find_nearest_available_team_missing_gps_returns_none(self):
        """Emergency without GPS coordinates returns None."""
        no_gps_req = {"id": 102, "latitude": None, "longitude": None}
        self.assertIsNone(find_nearest_available_team(no_gps_req, self.teams))

    def test_find_nearest_suitable_shelter_success(self):
        """Finds closest shelter that is verified AND has sufficient remaining capacity."""
        shelter = find_nearest_suitable_shelter(self.emergency, self.shelters)
        self.assertIsNotNone(shelter)
        self.assertEqual(shelter["id"], 30)
        self.assertEqual(shelter["shelter_name"], "Verified Closest Available")

    def test_find_nearest_suitable_shelter_capacity_constraint(self):
        """Rejects shelters that lack sufficient remaining capacity for the group."""
        large_group = {"id": 103, "latitude": 11.0183, "longitude": 76.9725, "people": 150}
        # Shelter 30 only has 80 capacity remaining (100 - 20) -> should skip to Shelter 40 (200 capacity)
        shelter = find_nearest_suitable_shelter(large_group, self.shelters)
        self.assertIsNotNone(shelter)
        self.assertEqual(shelter["id"], 40)

    def test_find_nearest_suitable_shelter_exhausted_capacity_returns_none(self):
        """Returns None when no shelter has enough space for a massive group."""
        huge_group = {"id": 104, "latitude": 11.0183, "longitude": 76.9725, "people": 500}
        shelter = find_nearest_suitable_shelter(huge_group, self.shelters)
        self.assertIsNone(shelter)


if __name__ == "__main__":
    unittest.main()
