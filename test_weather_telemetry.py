"""
Smart Flood Rescue System - Weather Telemetry Verification Suite
================================================================
Tests the real Open-Meteo Meteorological Telemetry integration:
1. Live weather retrieval for Coimbatore.
2. Dynamic location lookup for alternate cities (Chennai, Bengaluru).
3. Coordinate parsing support (lat, lon).
4. Validation and error handling for non-existent locations (no fake zeros).
5. Numerical coordinate bounds validation (-90 to 90, -180 to 180).
6. Units and measurement interval verification (°C, %, km/h, mm, 15-min interval).
7. Forward-looking 12-hour hourly precipitation forecast verification.
"""

import unittest
from app import app, parse_coordinates, degrees_to_cardinal, WMO_WEATHER_CODES


class TestWeatherTelemetry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def test_01_coordinate_parser_helper(self):
        """Verifies robust parsing of latitude and longitude strings."""
        self.assertEqual(parse_coordinates("11.0168, 76.9558"), (11.0168, 76.9558))
        self.assertEqual(parse_coordinates("13.0827,80.2707"), (13.0827, 80.2707))
        self.assertEqual(parse_coordinates("-33.8688, 151.2093"), (-33.8688, 151.2093))
        self.assertIsNone(parse_coordinates("Coimbatore"))
        self.assertIsNone(parse_coordinates("95.0, 200.0"))  # Out of bounds
        self.assertIsNone(parse_coordinates(""))
        self.assertIsNone(parse_coordinates(None))

    def test_02_cardinal_direction_helper(self):
        """Verifies wind direction degree to 16-point compass conversion."""
        self.assertEqual(degrees_to_cardinal(0), "N")
        self.assertEqual(degrees_to_cardinal(90), "E")
        self.assertEqual(degrees_to_cardinal(180), "S")
        self.assertEqual(degrees_to_cardinal(270), "W")
        self.assertEqual(degrees_to_cardinal(207), "SSW")
        self.assertEqual(degrees_to_cardinal(None), "")

    def test_03_coimbatore_weather_retrieval(self):
        """Verifies real Open-Meteo telemetry retrieval for Coimbatore."""
        resp = self.client.get("/api/weather?city=Coimbatore")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["location"], "Coimbatore")
        self.assertAlmostEqual(data["latitude"], 11.0, delta=0.5)
        self.assertAlmostEqual(data["longitude"], 76.96, delta=0.5)

        # Check required meteorological metrics
        self.assertIsNotNone(data["temperature_c"])
        self.assertIsInstance(data["temperature_c"], (int, float))
        self.assertIsNotNone(data["humidity_percent"])
        self.assertIsInstance(data["humidity_percent"], (int, float))
        self.assertIsNotNone(data["wind_speed_kmh"])
        self.assertIsInstance(data["wind_speed_kmh"], (int, float))
        self.assertIsNotNone(data["precipitation_mm"])
        self.assertIsInstance(data["precipitation_mm"], (int, float))
        self.assertEqual(data["precipitation_interval_mins"], 15)

        # Verify forward-looking next 12 hours forecast
        next_12 = data.get("next_12_hours", [])
        self.assertEqual(len(next_12), 12)
        for h in next_12:
            self.assertIn("time", h)
            self.assertIn("precipitation_mm", h)
            self.assertIn("temperature_c", h)
            self.assertIn("condition", h)
            self.assertIn("icon", h)

        # Verify timestamps
        self.assertIn("observation_time", data)
        self.assertIn("retrieved_at", data)
        self.assertIn("timezone", data)

    def test_04_alternate_location_chennai(self):
        """Verifies changing location to Chennai dynamically updates coordinates and weather."""
        resp = self.client.get("/api/weather?city=Chennai")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["location"], "Chennai")
        self.assertAlmostEqual(data["latitude"], 13.08, delta=0.5)
        self.assertAlmostEqual(data["longitude"], 80.28, delta=0.5)
        self.assertIn("Tamil Nadu", data["formatted_location"])

    def test_05_alternate_location_bengaluru(self):
        """Verifies changing location to Bengaluru dynamically updates coordinates and weather."""
        resp = self.client.get("/api/weather?city=Bengaluru")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["location"], "Bengaluru")
        self.assertAlmostEqual(data["latitude"], 12.97, delta=0.5)
        self.assertAlmostEqual(data["longitude"], 77.59, delta=0.5)
        self.assertIn("Karnataka", data["formatted_location"])

    def test_06_direct_coordinates_lookup(self):
        """Verifies weather retrieval using direct numerical coordinates in city or lat/lon params."""
        resp = self.client.get("/api/weather?lat=13.0827&lon=80.2707")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertAlmostEqual(data["latitude"], 13.0827, delta=0.001)
        self.assertAlmostEqual(data["longitude"], 80.2707, delta=0.001)

        # Coordinate string in city param
        resp2 = self.client.get("/api/weather?city=11.0168,%2076.9558")
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertTrue(data2["success"])
        self.assertAlmostEqual(data2["latitude"], 11.0168, delta=0.001)
        self.assertAlmostEqual(data2["longitude"], 76.9558, delta=0.001)

    def test_07_invalid_city_returns_404_not_fake_zeros(self):
        """Verifies non-existent locations return HTTP 404 with error message instead of fake zero data."""
        resp = self.client.get("/api/weather?city=NonExistentXYZPlace123456789")
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error_type"], "LOCATION_NOT_FOUND")
        self.assertIn("could not be resolved", data["message"])
        # Ensure no fake meteorological numbers are returned
        self.assertNotIn("temperature_c", data)
        self.assertNotIn("humidity_percent", data)

    def test_08_out_of_bounds_coordinates_return_400(self):
        """Verifies out-of-bounds coordinates return HTTP 400."""
        resp = self.client.get("/api/weather?lat=95.0&lon=200.0")
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error_type"], "INVALID_COORDINATES")
        self.assertIn("out of bounds", data["message"])

    def test_09_cache_control_headers_present(self):
        """Verifies no-cache headers prevent browser from serving stale telemetry."""
        resp = self.client.get("/api/weather?city=Coimbatore")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("no-cache", resp.headers.get("Cache-Control", ""))


if __name__ == "__main__":
    unittest.main()
