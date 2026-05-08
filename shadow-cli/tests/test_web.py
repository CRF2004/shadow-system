"""
Shadow CLI - Phase 5: Web Server Tests
Tests for the web API endpoints.
"""

import json
import threading
import unittest
import urllib.request
import urllib.parse
from http.server import HTTPServer

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import load_player, reset_player, save_player


class TestWebAPI(unittest.TestCase):
    """Test web API endpoints."""

    @classmethod
    def setUpClass(cls):
        """Start web server on a test port."""
        cls.port = 18999  # Use non-standard port for testing
        reset_player()

        # Import after reset
        from web_server import ShadowAPIHandler
        cls.server = HTTPServer(("127.0.0.1", cls.port), ShadowAPIHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _get(self, path):
        """Make a GET request and return parsed JSON."""
        url = self.base + path
        with urllib.request.urlopen(url) as r:
            return json.loads(r.read().decode())

    def _post(self, path, body=None):
        """Make a POST request and return parsed JSON."""
        url = self.base + path
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode())

    # ── Status ───────────────────────────────────────────────────────

    def test_status_returns_player_data(self):
        """Status endpoint returns valid player data."""
        data = self._get("/api/status")
        self.assertIn("level", data)
        self.assertIn("exp", data)
        self.assertIn("hp", data)
        self.assertIn("mp", data)
        self.assertIn("title", data)
        self.assertIn("gold", data)
        self.assertIn("power", data)
        self.assertIn("stats", data)
        self.assertIsInstance(data["stats"], dict)

    def test_status_has_version(self):
        """Status includes version."""
        data = self._get("/api/status")
        self.assertIn("version", data)

    def test_status_has_progress(self):
        """Status includes progress tracking fields."""
        data = self._get("/api/status")
        self.assertIn("expPct", data)
        self.assertIn("streak", data)
        self.assertIn("combo", data)
        self.assertIn("totalExp", data)
        self.assertIn("soldierCount", data)
        self.assertIn("achievementCount", data)

    # ── Tasks ────────────────────────────────────────────────────────

    def test_tasks_returns_daily_tasks(self):
        """Tasks endpoint returns daily tasks."""
        data = self._get("/api/tasks")
        self.assertIn("tasks", data)
        self.assertIn("date", data)
        self.assertIsInstance(data["tasks"], list)
        self.assertGreater(len(data["tasks"]), 0)

    # ── Record ───────────────────────────────────────────────────────

    def test_record_commit(self):
        """Record commit grants EXP."""
        reset_player()
        data = self._post("/api/record", {"type": "commit", "quantity": 1})
        self.assertTrue(data["success"])
        self.assertGreater(data["exp"], 0)

    def test_record_coding(self):
        """Record coding grants EXP."""
        reset_player()
        data = self._post("/api/record", {"type": "coding_line", "quantity": 100})
        self.assertTrue(data["success"])
        self.assertGreater(data["exp"], 0)

    def test_record_unknown_type(self):
        """Record unknown type returns error."""
        data = self._post("/api/record", {"type": "unknown_action"})
        self.assertFalse(data["success"])

    def test_record_updates_status(self):
        """Recording updates player status."""
        reset_player()
        status_before = self._get("/api/status")
        self._post("/api/record", {"type": "commit", "quantity": 1})
        status_after = self._get("/api/status")
        self.assertGreater(status_after["totalExp"], status_before["totalExp"])

    # ── Summon ───────────────────────────────────────────────────────

    def test_summon_random(self):
        """Summon random soldier."""
        reset_player()
        data = self._post("/api/summon", {})
        self.assertTrue(data["success"])

    def test_summon_specific_type(self):
        """Summon specific soldier type."""
        reset_player()
        data = self._post("/api/summon", {"type": "dev"})
        self.assertTrue(data["success"])

    def test_summon_insufficient_mp(self):
        """Summon with insufficient MP fails."""
        reset_player()
        # Set MP to 0
        player = load_player()
        player["mp"] = 0
        save_player(player)
        data = self._post("/api/summon", {})
        self.assertFalse(data["success"])

    # ── Legion ───────────────────────────────────────────────────────

    def test_legion_small(self):
        """Summon small legion."""
        reset_player()
        data = self._post("/api/legion", {"scale": "small"})
        self.assertTrue(data["success"])

    # ── Army ─────────────────────────────────────────────────────────

    def test_army_empty(self):
        """Army is empty for new player."""
        reset_player()
        data = self._get("/api/army")
        self.assertEqual(data["count"], 0)

    def test_army_after_summon(self):
        """Army shows soldiers after summon."""
        reset_player()
        # Summon until we get a soldier (low chance but test the endpoint)
        self._post("/api/legion", {"scale": "full"})
        data = self._get("/api/army")
        self.assertIn("soldiers", data)
        self.assertIn("count", data)

    # ── Achievements ─────────────────────────────────────────────────

    def test_achievements_endpoint(self):
        """Achievements endpoint returns list."""
        data = self._get("/api/achievements")
        self.assertIn("achievements", data)
        self.assertIsInstance(data["achievements"], list)

    # ── Dungeons ─────────────────────────────────────────────────────

    def test_dungeons_available(self):
        """Dungeons endpoint returns available dungeons."""
        reset_player()
        data = self._get("/api/dungeons")
        self.assertIn("dungeons", data)
        self.assertIsInstance(data["dungeons"], list)
        # Level 1 should have daily dungeons
        self.assertGreater(len(data["dungeons"]), 0)

    def test_enter_dungeon(self):
        """Enter a dungeon instance."""
        reset_player()
        data = self._post("/api/enter-dungeon", {"id": "code_dungeon"})
        self.assertTrue(data["success"])
        self.assertIn("instance", data)

    def test_enter_invalid_dungeon(self):
        """Enter invalid dungeon returns error."""
        data = self._post("/api/enter-dungeon", {"id": "nonexistent"})
        self.assertFalse(data["success"])

    # ── Bosses ───────────────────────────────────────────────────────

    def test_bosses_endpoint(self):
        """Bosses endpoint returns boss list."""
        reset_player()
        data = self._get("/api/bosses")
        self.assertIn("bosses", data)

    # ── Shop ─────────────────────────────────────────────────────────

    def test_shop_endpoint(self):
        """Shop endpoint returns items."""
        data = self._get("/api/shop")
        self.assertIn("items", data)
        self.assertIn("gold", data)
        self.assertIsInstance(data["items"], list)

    def test_shop_filter_by_category(self):
        """Shop filters by category."""
        data = self._get("/api/shop?category=consumable")
        self.assertTrue(all(i["category"] == "consumable" for i in data["items"]))

    # ── Buy / Sell ───────────────────────────────────────────────────

    def test_buy_insufficient_gold(self):
        """Buy with insufficient gold fails."""
        reset_player()
        data = self._post("/api/buy", {"id": "hp_potion"})
        self.assertFalse(data["success"])

    def test_buy_with_gold(self):
        """Buy item with enough gold."""
        reset_player()
        player = load_player()
        player["gold"] = 1000
        save_player(player)
        data = self._post("/api/buy", {"id": "hp_potion"})
        self.assertTrue(data["success"])

    def test_buy_unknown_item(self):
        """Buy unknown item fails."""
        data = self._post("/api/buy", {"id": "nonexistent"})
        self.assertFalse(data["success"])

    def test_inventory_after_buy(self):
        """Inventory shows purchased items."""
        reset_player()
        player = load_player()
        player["gold"] = 1000
        save_player(player)
        self._post("/api/buy", {"id": "hp_potion"})
        data = self._get("/api/inventory")
        self.assertGreater(data["count"], 0)

    # ── Inventory ────────────────────────────────────────────────────

    def test_inventory_endpoint(self):
        """Inventory endpoint returns list."""
        data = self._get("/api/inventory")
        self.assertIn("items", data)
        self.assertIn("count", data)

    # ── Integrations ─────────────────────────────────────────────────

    def test_integrations_endpoint(self):
        """Integrations endpoint returns status."""
        data = self._get("/api/integrations")
        self.assertIn("healthEnabled", data)
        self.assertIn("readingEnabled", data)
        self.assertIn("browserEnabled", data)
        self.assertIn("totalImports", data)

    def test_integration_enable_disable(self):
        """Toggle integration settings."""
        reset_player()
        data = self._post("/api/integrations/enable", {"target": "health"})
        self.assertTrue(data["success"])
        status = self._get("/api/integrations")
        self.assertTrue(status["healthEnabled"])

        data = self._post("/api/integrations/disable", {"target": "health"})
        self.assertTrue(data["success"])
        status = self._get("/api/integrations")
        self.assertFalse(status["healthEnabled"])

    def test_integration_unknown_target(self):
        """Toggle unknown integration type fails."""
        data = self._post("/api/integrations/enable", {"target": "xyz"})
        self.assertFalse(data["success"])

    # ── Health recording ─────────────────────────────────────────────

    def test_health_manual(self):
        """Record health data via API."""
        reset_player()
        data = self._post("/api/health", {
            "steps": 5000,
            "exercise_min": 30,
            "sleep_hours": 8,
        })
        self.assertTrue(data["success"])
        self.assertGreater(data["total_exp"], 0)

    def test_health_summary(self):
        """Get health summary."""
        data = self._get("/api/health-summary")
        self.assertIn("total_steps", data)
        self.assertIn("total_exp", data)

    # ── Reading recording ────────────────────────────────────────────

    def test_reading_manual(self):
        """Record reading data via API."""
        reset_player()
        data = self._post("/api/reading", {
            "minutes": 45,
            "pages": 20,
            "book": "Python编程",
        })
        self.assertTrue(data["success"])
        self.assertGreater(data["total_exp"], 0)

    def test_reading_summary(self):
        """Get reading summary."""
        data = self._get("/api/reading-summary")
        self.assertIn("total_minutes", data)
        self.assertIn("total_exp", data)

    # ── Browser recording ────────────────────────────────────────────

    def test_browser_manual(self):
        """Record browser activity via API."""
        reset_player()
        data = self._post("/api/browser", {"site": "leetcode.com", "minutes": 60})
        self.assertTrue(data["success"])
        self.assertGreater(data["total_exp"], 0)

    def test_browser_any_site(self):
        """Browser records any site (no site filtering)."""
        data = self._post("/api/browser", {"site": "youtube.com", "minutes": 30})
        self.assertTrue(data["success"])

    def test_browser_summary(self):
        """Get browser summary."""
        data = self._get("/api/browser-summary")
        self.assertIn("total_minutes", data)
        self.assertIn("total_exp", data)

    # ── Allocate stat ────────────────────────────────────────────────

    def test_allocate_stat(self):
        """Allocate stat points."""
        reset_player()
        player = load_player()
        player["statPoints"] = 5
        save_player(player)
        data = self._post("/api/allocate-stat", {"stat": "str", "amount": 2})
        self.assertTrue(data["success"])
        self.assertEqual(data["stats"]["strength"], 12)

    def test_allocate_insufficient_points(self):
        """Allocate with insufficient points fails."""
        reset_player()
        player = load_player()
        player["statPoints"] = 0
        save_player(player)
        data = self._post("/api/allocate-stat", {"stat": "str", "amount": 1})
        self.assertFalse(data["success"])

    # ── Static file serving ──────────────────────────────────────────

    def test_serves_index_html(self):
        """Root URL serves index.html."""
        url = self.base + "/"
        with urllib.request.urlopen(url) as r:
            content = r.read().decode()
            self.assertIn("Shadow CLI", content)
            self.assertIn("暗影君主", content)
            self.assertIn("tab-dashboard", content)

    def test_cors_headers(self):
        """API responses include CORS headers."""
        url = self.base + "/api/status"
        with urllib.request.urlopen(url) as r:
            self.assertIn("Access-Control-Allow-Origin", r.headers)


if __name__ == "__main__":
    unittest.main()
