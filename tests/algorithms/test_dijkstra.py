"""
Unit tests for Manual Dijkstra Shortest Path (algorithms/dijkstra.py)
"""

import unittest
from algorithms.dijkstra import (
    AdjacencyListGraph,
    dijkstra_shortest_path
)
import routing


class TestDijkstra(unittest.TestCase):
    """Verifies manual Dijkstra algorithm implementation."""

    def test_simple_triangle_graph(self):
        """Solves shortest path on small 3-node graph."""
        g = AdjacencyListGraph()
        g.add_edge("A", "B", 1.0)
        g.add_edge("B", "C", 2.0)
        g.add_edge("A", "C", 5.0)

        res = dijkstra_shortest_path(g, "A", "C")
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["A", "B", "C"])
        self.assertEqual(res["distance"], 3.0)

    def test_multiple_paths_chooses_minimum(self):
        """Correctly selects path with strictly smaller cumulative distance."""
        g = AdjacencyListGraph()
        # Path 1: S -> X -> D (cost: 3 + 4 = 7)
        # Path 2: S -> Y -> D (cost: 2 + 3 = 5)
        # Path 3: S -> Z -> D (cost: 6 + 1 = 7)
        g.add_edge("S", "X", 3.0)
        g.add_edge("X", "D", 4.0)
        g.add_edge("S", "Y", 2.0)
        g.add_edge("Y", "D", 3.0)
        g.add_edge("S", "Z", 6.0)
        g.add_edge("Z", "D", 1.0)

        res = dijkstra_shortest_path(g, "S", "D")
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["S", "Y", "D"])
        self.assertEqual(res["distance"], 5.0)

    def test_start_equals_target(self):
        """Start node identical to destination returns distance 0."""
        g = AdjacencyListGraph()
        g.add_node("Amrita_Ettimadai")
        res = dijkstra_shortest_path(g, "Amrita_Ettimadai", "Amrita_Ettimadai")
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["Amrita_Ettimadai"])
        self.assertEqual(res["distance"], 0.0)

    def test_negative_weight_rejection(self):
        """Raises ValueError when negative weight is introduced."""
        g = AdjacencyListGraph()
        with self.assertRaises(ValueError):
            g.add_edge("X", "Y", -3.5)

    def test_missing_node_raises_key_error(self):
        """Missing start or target node raises KeyError."""
        g = AdjacencyListGraph()
        g.add_edge("A", "B", 2.0)
        with self.assertRaises(KeyError):
            dijkstra_shortest_path(g, "A", "NonExistent")

    def test_disconnected_graph_target_unreachable(self):
        """Unreachable target returns success=False and infinite distance."""
        g = AdjacencyListGraph()
        g.add_edge("Island_A", "Island_B", 2.0)
        g.add_node("Mainland_C")

        res = dijkstra_shortest_path(g, "Island_A", "Mainland_C")
        self.assertFalse(res["success"])
        self.assertEqual(res["path"], [])
        self.assertEqual(res["distance"], float("inf"))

    def test_coimbatore_arterial_route_with_hazard_detour(self):
        """Verifies Coimbatore road network routing and flood hazard penalty diversion."""
        # Unpenalized graph
        clean_g = routing.build_manual_disaster_graph(active_hazards=[])
        clean_res = dijkstra_shortest_path(clean_g, "gandhipuram_hub", "singanallur_hub")
        self.assertTrue(clean_res["success"])
        self.assertEqual(clean_res["path"], ["gandhipuram_hub", "sungam_bypass", "trichy_rd_ramanathapuram", "singanallur_hub"])
        self.assertEqual(clean_res["distance"], 7.5)

        # Flood hazard on Sungam bypass forces detour via Avinashi Rd Peelamedu
        flooded_hazard = [{
            "name": "Sungam Bypass Flooding",
            "latitude": 10.9970,
            "longitude": 76.9780,
            "severity": "Flooded / Closed"
        }]
        hazard_g = routing.build_manual_disaster_graph(active_hazards=flooded_hazard)
        hazard_res = dijkstra_shortest_path(hazard_g, "gandhipuram_hub", "singanallur_hub")
        self.assertTrue(hazard_res["success"])
        self.assertEqual(hazard_res["path"], ["gandhipuram_hub", "avinashi_rd_peelamedu", "singanallur_hub"])
        self.assertEqual(hazard_res["distance"], 7.6)


if __name__ == "__main__":
    unittest.main()
