"""
Phase 4 Tests - External Integrations (Health, Reading, Browser)
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from state import create_default_player
from integrations.health import (
    import_health_json,
    import_health_csv,
    import_health_export,
    record_health_manual,
    get_health_summary,
)
from integrations.reading import (
    import_reading_json,
    import_reading_csv,
    record_reading_manual,
    get_reading_summary,
)
from integrations.browser_bridge import (
    import_browser_data,
    record_browser_manual,
    get_browser_summary,
)


# ── Health Integration Tests ───────────────────────────────────────────────

class TestHealthImportJSON(unittest.TestCase):
    """Test health data JSON import."""

    def setUp(self):
        self.player = create_default_player()
        self.temp_dir = tempfile.mkdtemp()

    def _write_json(self, data: dict) -> str:
        path = Path(self.temp_dir) / "health.json"
        with open(path, "w") as f:
            json.dump(data, f)
        return str(path)

    def test_import_health_basic(self):
        """Basic health JSON import should grant EXP."""
        data = {"data": [
            {"date": "2026-05-01", "steps": 5000, "exerciseMinutes": 30, "sleepHours": 8}
        ]}
        result = import_health_json(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertGreater(result["total_exp"], 0)
        self.assertEqual(result["entries_processed"], 1)

    def test_import_health_grants_exp(self):
        """Health import should grant EXP to player."""
        exp_before = self.player.get("totalExp", 0)
        data = {"data": [
            {"date": "2026-05-01", "steps": 10000, "exerciseMinutes": 0, "sleepHours": 0}
        ]}
        import_health_json(self.player, self._write_json(data))
        self.assertGreater(self.player.get("totalExp", 0), exp_before)

    def test_import_health_stored_in_state(self):
        """Health data should be stored in player state."""
        data = {"data": [
            {"date": "2026-05-01", "steps": 8000, "exerciseMinutes": 20, "sleepHours": 7}
        ]}
        import_health_json(self.player, self._write_json(data))
        self.assertIn("2026-05-01", self.player.get("healthData", {}))
        stored = self.player["healthData"]["2026-05-01"]
        self.assertEqual(stored["steps"], 8000)
        self.assertEqual(stored["exerciseMin"], 20)
        self.assertEqual(stored["sleepHours"], 7)

    def test_import_health_import_history(self):
        """Import should be recorded in importHistory."""
        data = {"data": [
            {"date": "2026-05-01", "steps": 5000, "exerciseMinutes": 0, "sleepHours": 0}
        ]}
        import_health_json(self.player, self._write_json(data))
        history = self.player.get("importHistory", [])
        health_imports = [h for h in history if h.get("source") == "health"]
        self.assertGreater(len(health_imports), 0)

    def test_import_health_grants_gold(self):
        """Import should grant gold (10% of EXP)."""
        data = {"data": [
            {"date": "2026-05-01", "steps": 5000, "exerciseMinutes": 0, "sleepHours": 0}
        ]}
        gold_before = self.player.get("gold", 0)
        import_health_json(self.player, self._write_json(data))
        self.assertGreater(self.player.get("gold", 0), gold_before)

    def test_import_health_daily_cap(self):
        """Health EXP should be capped at daily_health_cap."""
        # Max possible: steps=5000 (50) + exercise=50min (100) + sleep=10h (50) = 200
        data = {"data": [
            {"date": "2026-05-01", "steps": 50000, "exerciseMinutes": 500, "sleepHours": 24}
        ]}
        result = import_health_json(self.player, self._write_json(data))
        self.assertLessEqual(result["total_exp"], 200)

    def test_import_health_multiple_entries(self):
        """Import multiple days of health data."""
        data = {"data": [
            {"date": "2026-05-01", "steps": 5000, "exerciseMinutes": 0, "sleepHours": 0},
            {"date": "2026-05-02", "steps": 8000, "exerciseMinutes": 20, "sleepHours": 0},
        ]}
        result = import_health_json(self.player, self._write_json(data))
        self.assertEqual(result["entries_processed"], 2)

    def test_import_health_invalid_file(self):
        """Invalid file path should return error."""
        result = import_health_json(self.player, "/nonexistent/path.json")
        self.assertFalse(result["success"])

    def test_import_health_empty_data(self):
        """Empty data array should process 0 entries."""
        data = {"data": []}
        result = import_health_json(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertEqual(result["entries_processed"], 0)

    def test_import_health_malformed_numeric_skipped(self):
        """Malformed numeric fields skip that entry instead of crashing the import."""
        data = {"data": [
            {"date": "2026-05-01", "steps": "abc", "exerciseMinutes": 10},
            {"date": "2026-05-02", "steps": None},
            {"date": "2026-05-03", "steps": 5000, "exerciseMinutes": 0, "sleepHours": 0},
        ]}
        result = import_health_json(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertEqual(result["entries_processed"], 1)
        self.assertIn("2026-05-03", self.player.get("healthData", {}))
        self.assertNotIn("2026-05-01", self.player.get("healthData", {}))

    def test_import_health_non_finite_skipped(self):
        """JSON Infinity/NaN numerics skip that entry instead of crashing the import.

        json.load accepts the non-standard Infinity/NaN literals: int(inf)
        raised OverflowError (uncaught) and NaN sleepHours blew up later in
        _calculate_health_exp -> int(), aborting the whole import.
        """
        data = {"data": [
            {"date": "2026-05-01", "steps": float("inf")},
            {"date": "2026-05-02", "steps": 5000, "sleepHours": float("inf")},
            {"date": "2026-05-03", "steps": 5000, "sleepHours": float("nan")},
            {"date": "2026-05-04", "steps": 5000, "exerciseMinutes": 0, "sleepHours": 0},
        ]}
        result = import_health_json(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertEqual(result["entries_processed"], 1)
        self.assertIn("2026-05-04", self.player.get("healthData", {}))
        for bad in ("2026-05-01", "2026-05-02", "2026-05-03"):
            self.assertNotIn(bad, self.player.get("healthData", {}))


class TestHealthImportCSV(unittest.TestCase):
    """Test health data CSV import."""

    def setUp(self):
        self.player = create_default_player()
        self.temp_dir = tempfile.mkdtemp()

    def _write_csv(self, rows: list[dict]) -> str:
        path = Path(self.temp_dir) / "health.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    def test_import_health_csv_basic(self):
        """CSV import should work."""
        rows = [
            {"date": "2026-05-01", "steps": "6000", "exercise_minutes": "15", "sleep_hours": "7"},
        ]
        result = import_health_csv(self.player, self._write_csv(rows))
        self.assertTrue(result["success"])
        self.assertGreater(result["total_exp"], 0)

    def test_import_health_csv_multiple_rows(self):
        """CSV import should process multiple rows."""
        rows = [
            {"date": "2026-05-01", "steps": "5000", "exercise_minutes": "0", "sleep_hours": "0"},
            {"date": "2026-05-02", "steps": "8000", "exercise_minutes": "20", "sleep_hours": "7"},
        ]
        result = import_health_csv(self.player, self._write_csv(rows))
        self.assertEqual(result["entries_processed"], 2)

    def test_import_health_csv_non_finite_skipped(self):
        """Non-finite sleep_hours strings ("inf"/"nan") skip the row, not abort.

        float("inf") succeeds, and int(inf * config) later raised OverflowError
        outside the row-level try/except, crashing the whole CSV import.
        """
        rows = [
            {"date": "2026-05-01", "steps": "6000", "exercise_minutes": "15", "sleep_hours": "inf"},
            {"date": "2026-05-02", "steps": "6000", "exercise_minutes": "15", "sleep_hours": "nan"},
            {"date": "2026-05-03", "steps": "6000", "exercise_minutes": "15", "sleep_hours": "7"},
        ]
        result = import_health_csv(self.player, self._write_csv(rows))
        self.assertTrue(result["success"])
        self.assertEqual(result["entries_processed"], 1)
        self.assertIn("2026-05-03", self.player.get("healthData", {}))
        self.assertNotIn("2026-05-01", self.player.get("healthData", {}))


class TestHealthManual(unittest.TestCase):
    """Test manual health recording."""

    def setUp(self):
        self.player = create_default_player()

    def test_record_health_manual(self):
        """Manual health record should grant EXP."""
        result = record_health_manual(self.player, steps=5000, exercise_min=30, sleep_hours=8)
        self.assertTrue(result["success"])
        self.assertGreater(result["total_exp"], 0)

    def test_record_health_manual_zero(self):
        """Zero values should grant 0 EXP."""
        result = record_health_manual(self.player, steps=0, exercise_min=0, sleep_hours=0)
        self.assertEqual(result["total_exp"], 0)

    def test_record_health_stored(self):
        """Manual record should store in healthData."""
        record_health_manual(self.player, steps=6000, exercise_min=20, sleep_hours=7)
        today_data = self.player.get("healthData", {})
        self.assertEqual(len(today_data), 1)


class TestHealthSummary(unittest.TestCase):
    """Test health summary."""

    def setUp(self):
        self.player = create_default_player()

    def test_get_health_summary_empty(self):
        """Empty player should return zero summary."""
        summary = get_health_summary(self.player, days=7)
        self.assertEqual(summary["total_steps"], 0)
        self.assertEqual(summary["total_exp"], 0)

    def test_get_health_summary_with_data(self):
        """Summary should reflect stored health data."""
        today = datetime.now()
        d1 = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        d2 = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        self.player["healthData"] = {
            d1: {"steps": 5000, "exerciseMin": 30, "sleepHours": 8},
            d2: {"steps": 8000, "exerciseMin": 20, "sleepHours": 7},
        }
        summary = get_health_summary(self.player, days=7)
        self.assertEqual(summary["days_with_data"], 2)
        self.assertEqual(summary["total_steps"], 13000)


# ── Reading Integration Tests ──────────────────────────────────────────────

class TestReadingImportJSON(unittest.TestCase):
    """Test reading data JSON import."""

    def setUp(self):
        self.player = create_default_player()
        self.temp_dir = tempfile.mkdtemp()

    def _write_json(self, data) -> str:
        path = Path(self.temp_dir) / "reading.json"
        with open(path, "w") as f:
            json.dump(data, f)
        return str(path)

    def test_import_reading_basic(self):
        """Basic reading JSON import should grant EXP."""
        data = {"records": [
            {"date": "2026-05-01", "minutes": 30, "pages": 20, "book": "Test Book"}
        ]}
        result = import_reading_json(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertGreater(result["total_exp"], 0)

    def test_import_reading_multiple(self):
        """Import multiple reading entries."""
        data = {"records": [
            {"date": "2026-05-01", "minutes": 30, "pages": 20, "book": "Book A"},
            {"date": "2026-05-02", "minutes": 60, "pages": 50, "book": "Book B"},
        ]}
        result = import_reading_json(self.player, self._write_json(data))
        self.assertEqual(result["entries_processed"], 2)

    def test_import_reading_daily_cap(self):
        """Reading EXP should be capped."""
        data = {"records": [
            {"date": "2026-05-01", "minutes": 500, "pages": 500, "book": "Book"}
        ]}
        result = import_reading_json(self.player, self._write_json(data))
        self.assertLessEqual(result["total_exp"], 150)

    def test_import_reading_invalid_file(self):
        """Invalid file should return error."""
        result = import_reading_json(self.player, "/nonexistent/path.json")
        self.assertFalse(result["success"])

    def test_import_reading_malformed_numeric_skipped(self):
        """Malformed numeric fields skip that entry instead of crashing the import."""
        data = {"records": [
            {"date": "2026-05-01", "minutes": "abc", "pages": 20},
            {"date": "2026-05-02", "minutes": None, "pages": None},
            {"date": "2026-05-03", "minutes": 30, "pages": 20, "book": "Book"},
        ]}
        result = import_reading_json(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertEqual(result["entries_processed"], 1)
        self.assertIn("2026-05-03", self.player.get("readingData", {}))

    def test_import_reading_non_finite_skipped(self):
        """JSON Infinity/NaN numerics skip that entry instead of crashing.

        int(inf) from JSON's non-standard Infinity literal raised OverflowError,
        which the previous (ValueError, TypeError) guard did not catch.
        """
        data = {"records": [
            {"date": "2026-05-01", "minutes": float("inf")},
            {"date": "2026-05-02", "minutes": float("nan"), "pages": 10},
            {"date": "2026-05-03", "minutes": 30, "pages": 20, "book": "Book"},
        ]}
        result = import_reading_json(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertEqual(result["entries_processed"], 1)
        self.assertIn("2026-05-03", self.player.get("readingData", {}))
        self.assertNotIn("2026-05-01", self.player.get("readingData", {}))


class TestReadingImportCSV(unittest.TestCase):
    """Test reading data CSV import."""

    def setUp(self):
        self.player = create_default_player()
        self.temp_dir = tempfile.mkdtemp()

    def _write_csv(self, rows: list[dict]) -> str:
        path = Path(self.temp_dir) / "reading.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    def test_import_reading_csv_basic(self):
        """CSV import should work."""
        rows = [
            {"date": "2026-05-01", "minutes": "30", "pages": "20", "book_title": "Book"},
        ]
        result = import_reading_csv(self.player, self._write_csv(rows))
        self.assertTrue(result["success"])
        self.assertGreater(result["total_exp"], 0)


class TestReadingManual(unittest.TestCase):
    """Test manual reading recording."""

    def setUp(self):
        self.player = create_default_player()

    def test_record_reading_manual(self):
        """Manual reading record should grant EXP."""
        result = record_reading_manual(self.player, minutes=30, pages=20, book_title="Test Book")
        self.assertTrue(result["success"])
        self.assertGreater(result["total_exp"], 0)

    def test_record_reading_zero(self):
        """Zero values should grant 0 EXP."""
        result = record_reading_manual(self.player, minutes=0, pages=0)
        self.assertEqual(result["total_exp"], 0)


class TestReadingSummary(unittest.TestCase):
    """Test reading summary."""

    def setUp(self):
        self.player = create_default_player()

    def test_get_reading_summary_empty(self):
        """Empty player should return zero summary."""
        summary = get_reading_summary(self.player, days=7)
        self.assertEqual(summary["total_minutes"], 0)
        self.assertEqual(summary["total_exp"], 0)


# ── Browser Integration Tests ──────────────────────────────────────────────

class TestBrowserImportJSON(unittest.TestCase):
    """Test browser activity JSON import."""

    def setUp(self):
        self.player = create_default_player()
        self.temp_dir = tempfile.mkdtemp()

    def _write_json(self, data) -> str:
        path = Path(self.temp_dir) / "browser.json"
        with open(path, "w") as f:
            json.dump(data, f)
        return str(path)

    def test_import_browser_basic(self):
        """Basic browser import should grant EXP."""
        data = {"entries": [
            {"date": "2026-05-01", "site": "leetcode.com", "minutes": 30}
        ]}
        result = import_browser_data(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertGreater(result["total_exp"], 0)

    def test_import_browser_multiple_sites(self):
        """Import data from multiple sites."""
        data = {"entries": [
            {"date": "2026-05-01", "site": "leetcode.com", "minutes": 30},
            {"date": "2026-05-01", "site": "stackoverflow.com", "minutes": 20},
        ]}
        result = import_browser_data(self.player, self._write_json(data))
        self.assertEqual(result["entries_processed"], 1)  # Same day = 1 entry

    def test_import_browser_daily_cap(self):
        """Browser EXP should be capped."""
        data = {"entries": [
            {"date": "2026-05-01", "site": "leetcode.com", "minutes": 500}
        ]}
        result = import_browser_data(self.player, self._write_json(data))
        self.assertLessEqual(result["total_exp"], 100)

    def test_import_browser_invalid_file(self):
        """Invalid file should return error."""
        result = import_browser_data(self.player, "/nonexistent/path.json")
        self.assertFalse(result["success"])

    def test_import_browser_malformed_numeric_skipped(self):
        """Malformed numeric fields skip that entry instead of crashing the import.

        Before the fix, int(entry.get("minutes", ...)) ran unguarded: a string
        like "abc" raised ValueError, null raised TypeError (and a JSON
        Infinity/NaN literal raised OverflowError/ValueError), which escaped
        cmd_browser_import and aborted the whole CLI command. Health/reading
        imports were already hardened; browser was missed.
        """
        data = {"entries": [
            {"date": "2026-05-01", "site": "leetcode.com", "minutes": "abc"},
            {"date": "2026-05-02", "site": "leetcode.com", "minutes": None},
            {"date": "2026-05-03", "site": "leetcode.com", "minutes": 30},
        ]}
        result = import_browser_data(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertEqual(result["entries_processed"], 1)
        self.assertIn("2026-05-03", self.player.get("browserData", {}))
        self.assertNotIn("2026-05-01", self.player.get("browserData", {}))
        self.assertNotIn("2026-05-02", self.player.get("browserData", {}))

    def test_import_browser_non_finite_skipped(self):
        """JSON Infinity/NaN minutes skip that entry instead of crashing.

        json.load accepts the non-standard Infinity/NaN literals; int(inf)
        raised OverflowError (uncaught) and aborted the entire import.
        """
        data = {"entries": [
            {"date": "2026-05-01", "site": "leetcode.com", "minutes": float("inf")},
            {"date": "2026-05-02", "site": "leetcode.com", "minutes": float("nan")},
            {"date": "2026-05-03", "site": "leetcode.com", "minutes": 30},
        ]}
        result = import_browser_data(self.player, self._write_json(data))
        self.assertTrue(result["success"])
        self.assertEqual(result["entries_processed"], 1)
        self.assertIn("2026-05-03", self.player.get("browserData", {}))
        for bad in ("2026-05-01", "2026-05-02"):
            self.assertNotIn(bad, self.player.get("browserData", {}))
        self.assertGreater(result["total_exp"], 0)


class TestBrowserManual(unittest.TestCase):
    """Test manual browser recording."""

    def setUp(self):
        self.player = create_default_player()

    def test_record_browser_manual(self):
        """Manual browser record should grant EXP."""
        result = record_browser_manual(self.player, "leetcode.com", 30)
        self.assertTrue(result["success"])
        self.assertGreater(result["total_exp"], 0)


class TestBrowserSummary(unittest.TestCase):
    """Test browser summary."""

    def setUp(self):
        self.player = create_default_player()

    def test_get_browser_summary_empty(self):
        """Empty player should return zero summary."""
        summary = get_browser_summary(self.player, days=7)
        self.assertEqual(summary["total_minutes"], 0)
        self.assertEqual(summary["total_exp"], 0)

    def test_get_browser_summary_with_data(self):
        """Summary should reflect stored browser data."""
        today = datetime.now()
        d1 = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        self.player["browserData"] = {
            d1: {"totalMinutes": 60, "sites": {"leetcode.com": 45, "stackoverflow.com": 15}},
        }
        summary = get_browser_summary(self.player, days=7)
        self.assertEqual(summary["days_with_data"], 1)
        self.assertEqual(summary["total_minutes"], 60)


# ── Integration Status Tests ───────────────────────────────────────────────

class TestIntegrationStatus(unittest.TestCase):
    """Test integration settings management."""

    def setUp(self):
        self.player = create_default_player()

    def test_default_settings_disabled(self):
        """All integrations should be disabled by default."""
        settings = self.player.get("integrationSettings", {})
        self.assertFalse(settings.get("health_enabled", True))
        self.assertFalse(settings.get("reading_enabled", True))
        self.assertFalse(settings.get("browser_enabled", True))

    def test_new_fields_present(self):
        """Player should have new integration fields."""
        self.assertIn("importHistory", self.player)
        self.assertIn("healthData", self.player)
        self.assertIn("readingData", self.player)
        self.assertIn("browserData", self.player)
        self.assertIn("integrationSettings", self.player)


# ── Workflow Tests ──────────────────────────────────────────────────────────

class TestIntegrationWorkflow(unittest.TestCase):
    """Test full integration workflows."""

    def setUp(self):
        self.player = create_default_player()
        self.temp_dir = tempfile.mkdtemp()

    def test_health_import_workflow(self):
        """Import health → verify EXP → verify data stored → summary."""
        today = datetime.now().strftime("%Y-%m-%d")
        data = {"data": [
            {"date": today, "steps": 10000, "exerciseMinutes": 30, "sleepHours": 8},
        ]}
        path = Path(self.temp_dir) / "health.json"
        with open(path, "w") as f:
            json.dump(data, f)

        exp_before = self.player.get("totalExp", 0)
        result = import_health_json(self.player, str(path))
        self.assertTrue(result["success"])
        self.assertGreater(self.player.get("totalExp", 0), exp_before)
        self.assertIn(today, self.player["healthData"])
        summary = get_health_summary(self.player, days=7)
        self.assertGreater(summary["total_exp"], 0)

    def test_reading_import_workflow(self):
        """Import reading → verify EXP."""
        data = {"records": [
            {"date": "2026-05-01", "minutes": 60, "pages": 40, "book": "Test"},
        ]}
        path = Path(self.temp_dir) / "reading.json"
        with open(path, "w") as f:
            json.dump(data, f)

        exp_before = self.player.get("totalExp", 0)
        result = import_reading_json(self.player, str(path))
        self.assertTrue(result["success"])
        self.assertGreater(self.player.get("totalExp", 0), exp_before)

    def test_browser_import_workflow(self):
        """Import browser → verify EXP."""
        data = {"entries": [
            {"date": "2026-05-01", "site": "leetcode.com", "minutes": 45},
        ]}
        path = Path(self.temp_dir) / "browser.json"
        with open(path, "w") as f:
            json.dump(data, f)

        exp_before = self.player.get("totalExp", 0)
        result = import_browser_data(self.player, str(path))
        self.assertTrue(result["success"])
        self.assertGreater(self.player.get("totalExp", 0), exp_before)

    def test_multiple_imports_accumulate(self):
        """Multiple imports should accumulate EXP."""
        player = create_default_player()

        # Health import
        health_data = {"data": [{"date": "2026-05-01", "steps": 5000, "exerciseMinutes": 0, "sleepHours": 0}]}
        hp = Path(self.temp_dir) / "h.json"
        with open(hp, "w") as f:
            json.dump(health_data, f)
        import_health_json(player, str(hp))

        # Reading import
        reading_data = {"records": [{"date": "2026-05-01", "minutes": 30, "pages": 0, "book": ""}]}
        rp = Path(self.temp_dir) / "r.json"
        with open(rp, "w") as f:
            json.dump(reading_data, f)
        import_reading_json(player, str(rp))

        # Browser import
        browser_data = {"entries": [{"date": "2026-05-01", "site": "test.com", "minutes": 30}]}
        bp = Path(self.temp_dir) / "b.json"
        with open(bp, "w") as f:
            json.dump(browser_data, f)
        import_browser_data(player, str(bp))

        self.assertGreater(player.get("totalExp", 0), 0)
        self.assertGreater(len(player.get("importHistory", [])), 0)
