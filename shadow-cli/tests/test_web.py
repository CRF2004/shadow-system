"""
Shadow CLI - Phase 5: Web Server Tests
Tests for the web API endpoints.
"""

import json
import threading
import unittest
import urllib.request
import urllib.parse
import urllib.error
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

    def _get_status(self, path):
        """GET and return (status, parsed_json), tolerating HTTP errors."""
        url = self.base + path
        try:
            with urllib.request.urlopen(url) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

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

    # ── Skills ───────────────────────────────────────────────────────

    def test_skills_endpoint_empty(self):
        """Skills endpoint returns empty list for new player."""
        reset_player()
        data = self._get("/api/skills")
        self.assertIn("skills", data)
        self.assertIsInstance(data["skills"], list)
        self.assertEqual(len(data["skills"]), 0)

    def test_skills_endpoint_with_config(self):
        """Skills endpoint returns configured skills."""
        reset_player()
        # Configure skills via onboarding save
        skills = [
            {"id": "guitar", "name": "吉他", "category": "音乐", "unit": "分钟", "icon": "🎸",
             "exp_formula": "linear", "exp_per_unit": 2, "daily_cap": 120, "daily_target": 30},
        ]
        self._post("/api/onboard/save", {"skills": skills, "template_used": "test"})
        data = self._get("/api/skills")
        self.assertEqual(len(data["skills"]), 1)
        self.assertEqual(data["skills"][0]["id"], "guitar")
        self.assertEqual(data["skills"][0]["icon"], "🎸")

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

    # ── Activities ───────────────────────────────────────────────────

    def test_activities_single(self):
        """Activities endpoint accepts a single activity."""
        reset_player()
        data = self._post("/api/activities", {"type": "commit", "quantity": 1, "source": "git_hook"})
        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 1)
        self.assertGreater(data["total_exp"], 0)
        self.assertEqual(data["results"][0]["action_type"], "commit")

    def test_activities_batch(self):
        """Activities endpoint accepts a batch of activities."""
        reset_player()
        data = self._post("/api/activities", {
            "activities": [
                {"type": "commit", "quantity": 1},
                {"type": "coding_line", "quantity": 100},
            ],
        })
        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["results"]), 2)
        self.assertGreater(data["total_exp"], 0)

    def test_activities_invalid_payload(self):
        """Activities endpoint rejects empty payloads."""
        data = self._post("/api/activities", {})
        self.assertFalse(data["success"])
        self.assertIn("message", data)

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

    # ── Analytics API ───────────────────────────────────────────────

    def test_analytics_weekly(self):
        """Weekly report endpoint."""
        reset_player()
        from analytics import log_daily_activity
        from state import load_player
        player = load_player()
        from datetime import date, timedelta
        monday = date.today() - timedelta(days=date.today().weekday())
        log_daily_activity(player, monday.isoformat(), "commit", 3, 150, 10)
        log_daily_activity(player, monday.isoformat(), "coding", 500, 50, 0)
        save_player(player)
        data = self._get("/api/analytics/weekly")
        self.assertIn("week_start", data)
        self.assertIn("days_active", data)
        self.assertIn("total_exp", data)
        self.assertIn("daily_data", data)
        self.assertIn("trend", data)
        self.assertGreater(data["total_exp"], 0)

    def test_analytics_monthly(self):
        """Monthly report endpoint."""
        data = self._get("/api/analytics/monthly")
        self.assertIn("month", data)
        self.assertIn("days_active", data)
        self.assertIn("total_exp", data)

    def test_analytics_insights(self):
        """Insights endpoint."""
        data = self._get("/api/analytics/insights")
        self.assertIn("insights", data)
        self.assertIsInstance(data["insights"], list)

    def test_analytics_streak(self):
        """Streak history endpoint."""
        data = self._get("/api/analytics/streak")
        self.assertIn("current_streak", data)
        self.assertIn("best_streak", data)
        self.assertIn("active_days", data)
        self.assertIn("completion_rate", data)

    def test_analytics_reminders(self):
        """Smart reminders endpoint."""
        data = self._get("/api/analytics/reminders")
        self.assertIn("reminders", data)
        self.assertIsInstance(data["reminders"], list)

    def test_analytics_breakdown(self):
        """Type breakdown endpoint."""
        data = self._get("/api/analytics/breakdown")
        self.assertIn("types", data)
        self.assertIn("most_active_type", data)
        self.assertIsInstance(data["types"], list)

    # ── Static file serving ──────────────────────────────────────────

    def test_serves_index_html(self):
        """Root URL serves index.html."""
        url = self.base + "/"
        with urllib.request.urlopen(url) as r:
            content = r.read().decode()
            self.assertIn("Shadow CLI", content)
            self.assertIn("暗影君主", content)
            self.assertIn("tab-dashboard", content)

    def test_mobile_viewport_meta_present(self):
        """Served index.html includes viewport meta so mobile browsers scale correctly."""
        url = self.base + "/"
        with urllib.request.urlopen(url) as r:
            content = r.read().decode()
        self.assertIn(
            'name="viewport"',
            content,
            "index.html must include a <meta name=viewport> tag for mobile rendering",
        )
        self.assertIn("width=device-width", content)

    def test_mobile_responsive_css_media_queries(self):
        """layout.css ships responsive breakpoints (768px tablet / 480px phone)."""
        with urllib.request.urlopen(self.base + "/css/layout.css") as r:
            css = r.read().decode()
        self.assertIn("@media(max-width:768px)", css, "layout.css must stack layout on tablets")
        self.assertIn("@media(max-width:480px)", css, "layout.css must adapt layout on phones")
        # Mobile sidebar becomes a horizontal nav bar (flex row), not a fixed column.
        self.assertIn("flex-direction:column", css, "mobile app shell must switch to column layout")

    def test_cors_headers(self):
        """API responses include CORS headers."""
        url = self.base + "/api/status"
        with urllib.request.urlopen(url) as r:
            self.assertIn("Access-Control-Allow-Origin", r.headers)

    # ── Malformed-input robustness (bad numeric fields / bad chat bodies) ──

    def test_record_bad_quantity_returns_400(self):
        """/api/record with non-numeric quantity returns clean 400, not a crash."""
        reset_player()
        data = self._post("/api/record", {"type": "commit", "quantity": "abc"})
        self.assertFalse(data["success"])

    def test_record_bad_quantity_null_returns_400(self):
        """/api/record with null quantity returns clean 400, not a crash."""
        reset_player()
        data = self._post("/api/record", {"type": "commit", "quantity": None})
        self.assertFalse(data["success"])

    def test_health_bad_numbers_returns_400(self):
        """/api/health with non-numeric steps returns clean 400, not a crash."""
        reset_player()
        data = self._post("/api/health", {"steps": "many", "exercise_min": 30, "sleep_hours": 8})
        self.assertFalse(data["success"])

    def test_health_infinite_sleep_returns_400_not_disconnect(self):
        """A JSON `1e999` sleep parses to inf; must 400, not drop the link.

        float("1e999") overflows to inf without raising (and JSON's Infinity
        literal loads as inf), so _coerce_float returned inf; int(inf) then
        raised OverflowError inside the health EXP calculation and the
        connection was dropped with no response (RemoteDisconnected).
        """
        import http.client
        reset_player()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(
            "POST",
            "/api/health",
            body=b'{"steps":5000,"exercise":30,"sleep":1e999}',
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        self.assertEqual(resp.status, 400)
        self.assertFalse(data.get("success"))

    def test_health_nan_sleep_returns_400_not_disconnect(self):
        """A JSON NaN sleep is rejected with a clean 400, not a dropped link."""
        import http.client
        reset_player()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(
            "POST",
            "/api/health",
            body=b'{"steps":5000,"sleep":NaN}',
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        self.assertEqual(resp.status, 400)
        self.assertFalse(data.get("success"))

    def test_health_valid_sleep_still_works(self):
        """A finite numeric sleep value keeps working after hardening."""
        reset_player()
        data = self._post("/api/health", {"steps": 5000, "exercise": 30, "sleep": 8})
        self.assertTrue(data["success"])

    def test_reading_bad_numbers_returns_400(self):
        """/api/reading with non-numeric minutes returns clean 400, not a crash."""
        reset_player()
        data = self._post("/api/reading", {"minutes": "lots", "pages": 10})
        self.assertFalse(data["success"])

    def test_browser_bad_numbers_returns_400(self):
        """/api/browser with non-numeric minutes returns clean 400, not a crash."""
        reset_player()
        data = self._post("/api/browser", {"site": "leetcode.com", "minutes": "many"})
        self.assertFalse(data["success"])

    def test_allocate_stat_bad_amount_returns_400(self):
        """/api/allocate-stat with non-numeric amount returns clean 400, not a crash."""
        reset_player()
        player = load_player()
        player["statPoints"] = 5
        save_player(player)
        data = self._post("/api/allocate-stat", {"stat": "str", "amount": "xx"})
        self.assertFalse(data["success"])

    def test_chat_malformed_messages_return_400(self):
        """Chat endpoint rejects non-list / non-dict messages with clean 400s."""
        reset_player()
        for bad_messages in ("hi", {"role": "user", "content": "hi"}, [1, 2, 3], "nope"):
            data = self._post("/v1/chat/completions", {"messages": bad_messages})
            self.assertIn("error", data)

    def test_chat_non_string_content_returns_400(self):
        """Chat endpoint ignores non-string message content (no crash)."""
        reset_player()
        data = self._post("/v1/chat/completions", {"messages": [{"role": "user", "content": 123}]})
        self.assertIn("error", data)

    # ── Malformed GET query params (days / offset) ────────────────────────

    def test_summary_bad_days_query_returns_400(self):
        """Summary GET endpoints reject non-numeric ?days= with a clean 400."""
        reset_player()
        for path in ("/api/health-summary?days=abc",
                     "/api/reading-summary?days=abc",
                     "/api/browser-summary?days=abc"):
            status, data = self._get_status(path)
            self.assertEqual(status, 400, path)
            self.assertFalse(data["success"], path)

    def test_analytics_bad_query_params_return_400(self):
        """Analytics GET endpoints reject non-numeric ?offset=/?days= with 400."""
        reset_player()
        for path in ("/api/analytics/weekly?offset=abc",
                     "/api/analytics/monthly?offset=abc",
                     "/api/analytics/breakdown?days=abc"):
            status, data = self._get_status(path)
            self.assertEqual(status, 400, path)
            self.assertFalse(data["success"], path)

    def test_valid_numeric_query_params_still_work(self):
        """Well-formed ?days=/?offset= keep working after hardening."""
        reset_player()
        for path in ("/api/health-summary?days=3",
                     "/api/reading-summary?days=3",
                     "/api/browser-summary?days=3",
                     "/api/analytics/weekly?offset=0",
                     "/api/analytics/monthly?offset=0",
                     "/api/analytics/breakdown?days=7"):
            status, data = self._get_status(path)
            self.assertEqual(status, 200, path)

    def test_malformed_content_length_does_not_crash(self):
        """A non-numeric Content-Length header must not drop the connection."""
        import http.client
        reset_player()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.putrequest("POST", "/api/record")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", "abc")
        conn.endheaders()
        resp = conn.getresponse()
        self.assertIn(resp.status, (200, 400))
        resp.read()
        conn.close()

    def test_activities_infinite_quantity_returns_400(self):
        """A JSON `1e999` quantity parses to inf; must 400, not drop the link.

        `int(float("inf"))` raises OverflowError, which the previous inline
        try/except (TypeError, ValueError) did not catch, so the exception
        escaped and the connection was dropped. Mirrors _coerce_int hardening.
        """
        import http.client
        reset_player()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(
            "POST",
            "/api/activities",
            body=b'{"activities":[{"type":"coding","quantity":1e999}]}',
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        self.assertEqual(resp.status, 400)
        self.assertFalse(data.get("success"))
        self.assertTrue(data.get("errors"))

    def test_activities_valid_quantity_still_works(self):
        """A normal numeric activity list keeps working after hardening."""
        reset_player()
        data = self._post("/api/activities", {"activities": [{"type": "commit", "quantity": 2}]})
        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["quantity"], 2)

    # ── Non-object JSON bodies on POST endpoints ──────────────────────────

    def test_non_object_json_body_returns_400_not_disconnect(self):
        """POST endpoints must 400 on a JSON array body, not drop the socket.

        ``body.get(...)`` on a list/string/number raises AttributeError, which
        escaped the handler and dropped the connection with no HTTP response
        (RemoteDisconnected). Every object-body endpoint must instead reply 400.
        """
        import http.client
        reset_player()
        endpoints = [
            "/api/summon", "/api/legion", "/api/buy", "/api/sell",
            "/api/enter-dungeon", "/api/scan-git", "/api/scan-files",
            "/api/integrations/enable", "/api/integrations/disable",
            "/api/auth/login", "/api/auth/register",
            "/api/guilds/create", "/api/guilds/disband", "/api/guilds/join",
            "/api/guilds/leave", "/api/guilds/info", "/api/guilds/transfer",
            "/api/guilds/kick", "/api/guilds/promote", "/api/guilds/start-task",
            "/api/guilds/contribute", "/api/guilds/start-battle",
            "/api/guilds/deal-damage",
            "/api/onboard/configure", "/api/onboard/save",
        ]
        for ep in endpoints:
            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            try:
                conn.request("POST", ep, body=b'[]',
                             headers={"Content-Type": "application/json"})
                resp = conn.getresponse()
                data = json.loads(resp.read().decode())
            except http.client.RemoteDisconnected:
                self.fail(f"{ep} dropped the connection on a non-object JSON body")
            finally:
                conn.close()
            self.assertEqual(resp.status, 400, ep)
            self.assertFalse(data.get("success"), ep)
            self.assertIn("JSON", data.get("message", ""), ep)

    def test_object_json_body_still_works_after_guard(self):
        """Well-formed JSON object bodies keep their normal behavior."""
        reset_player()
        status, data = self._post_status("/api/auth/login",
                                         {"username": "no_such_user", "password": "x"})
        self.assertEqual(status, 401)
        self.assertFalse(data.get("success"))

        status, data = self._post_status("/api/guilds/info", {"guildId": "no-such-guild"})
        self.assertEqual(status, 404)
        self.assertFalse(data.get("success"))

    def _post_status(self, path, body):
        """POST a JSON object and return (status, parsed_json)."""
        url = self.base + path
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    # ── Non-string credentials on auth endpoints ──────────────────────────

    def test_non_string_credentials_do_not_drop_connection(self):
        """Non-string username/password must 400/401, not drop the socket.

        ``username.lower()`` raises AttributeError for a JSON number/list/null and
        ``len(password)`` raises TypeError for a number, so these bodies escaped
        the handler and the connection was closed with no HTTP response
        (RemoteDisconnected). Measured pre-fix: 4 of the 6 bodies below dropped.
        """
        import http.client
        reset_player()
        cases = [
            ("/api/auth/register", {"username": 123, "password": "abcd"}, 400),
            ("/api/auth/register", {"username": "newuser", "password": 1234}, 400),
            ("/api/auth/register", {"username": ["a", "b"], "password": "abcd"}, 400),
            ("/api/auth/register", {"username": None, "password": "abcd"}, 400),
            ("/api/auth/login", {"username": 123, "password": "abcd"}, 401),
            ("/api/auth/login", {"username": "x", "password": 1234}, 401),
        ]
        for path, body, expected in cases:
            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            try:
                conn.request("POST", path, body=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
                resp = conn.getresponse()
                data = json.loads(resp.read().decode())
            except http.client.RemoteDisconnected:
                self.fail(f"{path} {body} dropped the connection")
            finally:
                conn.close()
            self.assertEqual(resp.status, expected, f"{path} {body}")
            self.assertFalse(data.get("success"), f"{path} {body}")

    def test_chat_valid_request_returns_completion(self):
        """Chat endpoint still returns a valid completion for well-formed input."""
        reset_player()
        data = self._post("/v1/chat/completions", {
            "messages": [{"role": "user", "content": "我的状态"}],
        })
        self.assertEqual(data["object"], "chat.completion")
        self.assertIn("暗影君主", data["choices"][0]["message"]["content"])


if __name__ == "__main__":
    unittest.main()
