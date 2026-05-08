"""
Shadow System - State Persistence Tests (Phase 0.5)
Tests for player state save/load cycle, directory creation, and migration.
"""

import sys
import os
import unittest
import tempfile
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from state import (
    create_default_player,
    load_player,
    save_player,
    reset_player,
    _ensure_dirs,
)


# ── Test Fixtures ──────────────────────────────────────────────────────

class TempStateDirMixin:
    """Mixin that redirects state files to a temp directory."""

    def setUp(self):
        self._orig_state_dir = config.STATE_DIR
        self._orig_player_file = config.PLAYER_FILE
        self._origQuests_dir = config.QUESTS_DIR
        self._orig_soldiers_dir = config.SOLDIERS_DIR
        self._orig_logs_dir = config.LOGS_DIR

        self._temp_dir = tempfile.mkdtemp()
        self._temp_state = Path(self._temp_dir) / "shadow-state"

        config.STATE_DIR = self._temp_state
        config.PLAYER_FILE = self._temp_state / "player.json"
        config.QUESTS_DIR = self._temp_state / "quests"
        config.SOLDIERS_DIR = self._temp_state / "soldiers"
        config.LOGS_DIR = self._temp_state / "logs"

    def tearDown(self):
        config.STATE_DIR = self._orig_state_dir
        config.PLAYER_FILE = self._orig_player_file
        config.QUESTS_DIR = self._origQuests_dir
        config.SOLDIERS_DIR = self._orig_soldiers_dir
        config.LOGS_DIR = self._orig_logs_dir

        # Cleanup
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)


# ── Default Player Tests ──────────────────────────────────────────────

class TestCreateDefaultPlayer(unittest.TestCase):
    """Test create_default_player() returns valid initial state."""

    def test_default_level(self):
        p = create_default_player()
        self.assertEqual(p["level"], 1)

    def test_default_exp(self):
        p = create_default_player()
        self.assertEqual(p["exp"], 0)

    def test_default_exp_to_next(self):
        p = create_default_player()
        self.assertEqual(p["expToNext"], config.BASE_EXP)

    def test_default_hp_mp(self):
        p = create_default_player()
        self.assertEqual(p["hp"], config.MAX_HP)
        self.assertEqual(p["mp"], config.MAX_MP)

    def test_default_stats(self):
        p = create_default_player()
        expected = {"strength": 10, "agility": 10, "sense": 10, "vitality": 10, "intelligence": 10}
        self.assertEqual(p["stats"], expected)

    def test_default_stat_points(self):
        p = create_default_player()
        self.assertEqual(p["statPoints"], 0)

    def test_default_gold(self):
        p = create_default_player()
        self.assertEqual(p["gold"], 0)

    def test_default_soldiers(self):
        p = create_default_player()
        self.assertEqual(p["soldiers"], [])

    def test_default_achievements(self):
        p = create_default_player()
        self.assertEqual(p["achievements"], [])

    def test_has_timestamps(self):
        p = create_default_player()
        self.assertIn("createdAt", p)
        self.assertIn("lastActive", p)
        self.assertEqual(p["createdAt"], p["lastActive"])

    def test_has_daily_progress(self):
        p = create_default_player()
        self.assertIn("dailyProgress", p)
        self.assertEqual(p["dailyProgress"], {})

    def test_all_required_fields(self):
        """Verify all fields that the engine depends on exist."""
        p = create_default_player()
        required = [
            "name", "title", "level", "exp", "expToNext",
            "hp", "mp", "stats", "statPoints", "gold",
            "soldiers", "achievements", "streak", "totalExp",
            "createdAt", "lastActive", "lastDaily", "dailyProgress",
        ]
        for field in required:
            self.assertIn(field, p, f"Missing field: {field}")


# ── Save/Load Cycle Tests (Phase 0.5) ─────────────────────────────────

class TestSaveLoadCycle(TempStateDirMixin, unittest.TestCase):
    """Test that player state persists correctly across save/load."""

    def test_save_and_load_basic(self):
        """Save a player and load it back."""
        p = create_default_player()
        save_player(p)

        loaded = load_player()
        self.assertEqual(loaded["level"], p["level"])
        self.assertEqual(loaded["exp"], p["exp"])
        self.assertEqual(loaded["stats"], p["stats"])

    def test_save_load_preserves_changes(self):
        """Modify player, save, load — verify changes persist."""
        p = create_default_player()
        p["level"] = 5
        p["exp"] = 200
        p["gold"] = 500
        p["stats"]["strength"] = 25
        p["statPoints"] = 10
        p["streak"] = 7
        save_player(p)

        loaded = load_player()
        self.assertEqual(loaded["level"], 5)
        self.assertEqual(loaded["exp"], 200)
        self.assertEqual(loaded["gold"], 500)
        self.assertEqual(loaded["stats"]["strength"], 25)
        self.assertEqual(loaded["statPoints"], 10)
        self.assertEqual(loaded["streak"], 7)

    def test_save_load_after_multiple_rounds(self):
        """Simulate multiple save/load cycles (like playing over days)."""
        p = create_default_player()

        # Round 1
        p["level"] = 3
        p["exp"] = 50
        p["gold"] = 100
        save_player(p)
        loaded = load_player()

        # Round 2
        loaded["level"] = 7
        loaded["exp"] = 300
        loaded["gold"] = 500
        save_player(loaded)
        loaded2 = load_player()

        # Verify final state
        self.assertEqual(loaded2["level"], 7)
        self.assertEqual(loaded2["exp"], 300)
        self.assertEqual(loaded2["gold"], 500)

    def test_save_creates_file(self):
        """save_player should create player.json."""
        p = create_default_player()
        save_player(p)
        self.assertTrue(config.PLAYER_FILE.exists())

    def test_save_creates_directories(self):
        """save_player should create state directories."""
        p = create_default_player()
        save_player(p)
        self.assertTrue(config.STATE_DIR.exists())
        self.assertTrue(config.QUESTS_DIR.exists())
        self.assertTrue(config.SOLDIERS_DIR.exists())
        self.assertTrue(config.LOGS_DIR.exists())

    def test_save_is_valid_json(self):
        """Saved file should be valid, readable JSON."""
        p = create_default_player()
        p["level"] = 10
        p["name"] = "Test Player"
        save_player(p)

        with open(config.PLAYER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["level"], 10)
        self.assertEqual(data["name"], "Test Player")

    def test_save_updates_title(self):
        """save_player should update title based on level."""
        p = create_default_player()
        p["level"] = 50
        save_player(p)

        loaded = load_player()
        self.assertEqual(loaded["title"], "S 级猎人")

    def test_save_updates_last_active(self):
        """save_player should update lastActive timestamp."""
        p = create_default_player()
        import time
        original_active = p["lastActive"]
        save_player(p)

        loaded = load_player()
        self.assertNotEqual(loaded["lastActive"], original_active)

    def test_load_creates_new_if_no_file(self):
        """load_player should create new player if no file exists."""
        loaded = load_player()
        self.assertEqual(loaded["level"], 1)
        self.assertEqual(loaded["exp"], 0)

    def test_reset_player(self):
        """reset_player should delete file and return fresh player."""
        p = create_default_player()
        p["level"] = 99
        save_player(p)

        fresh = reset_player()
        self.assertFalse(config.PLAYER_FILE.exists())
        self.assertEqual(fresh["level"], 1)


# ── State Migration Tests ──────────────────────────────────────────────

class TestStateMigration(TempStateDirMixin, unittest.TestCase):
    """Test forward compatibility when loading old state formats."""

    def test_load_missing_field(self):
        """Load a state file that's missing newer fields — should fill defaults."""
        p = create_default_player()
        save_player(p)

        # Manually remove a field to simulate old format
        with open(config.PLAYER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        del data["totalExp"]

        loaded = load_player()
        # Should have the default value filled in
        self.assertIn("totalExp", loaded)
        self.assertEqual(loaded["totalExp"], 0)

    def test_load_partial_state(self):
        """Load a minimal state file — should fill all missing fields."""
        p = create_default_player()
        save_player(p)

        # Write a minimal state (only essential fields)
        with open(config.PLAYER_FILE, "w", encoding="utf-8") as f:
            json.dump({"level": 5, "exp": 100}, f)

        loaded = load_player()
        self.assertEqual(loaded["level"], 5)
        self.assertEqual(loaded["exp"], 100)
        # All default fields should be filled
        self.assertEqual(loaded["hp"], config.MAX_HP)
        self.assertEqual(loaded["stats"]["strength"], 10)


# ── Directory Creation Tests ───────────────────────────────────────────

class TestDirectoryCreation(TempStateDirMixin, unittest.TestCase):
    """Test state directory creation."""

    def test_ensure_dirs(self):
        _ensure_dirs()
        self.assertTrue(config.STATE_DIR.exists())
        self.assertTrue(config.QUESTS_DIR.exists())
        self.assertTrue(config.SOLDIERS_DIR.exists())
        self.assertTrue(config.LOGS_DIR.exists())

    def test_ensure_dirs_idempotent(self):
        """Calling ensure_dirs twice should not fail."""
        _ensure_dirs()
        _ensure_dirs()  # Should not raise
        self.assertTrue(config.STATE_DIR.exists())


# ── Run Tests ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
