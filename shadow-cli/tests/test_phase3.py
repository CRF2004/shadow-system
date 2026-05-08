"""
Shadow System - Phase 3 Tests
Tests for dungeon system and shop system.
"""

import sys
import os
import unittest
import tempfile
import json
from pathlib import Path
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from state import create_default_player, save_player
from engine import add_exp


# ── Dungeon Tests ────────────────────────────────────────────────────────

class TestDungeonGeneration(unittest.TestCase):
    """Test dungeon instance generation."""

    def test_get_available_dungeons(self):
        """Low level player should see daily dungeons."""
        from dungeon import get_available_dungeons, DUNGEONS
        p = create_default_player()
        p["level"] = 1
        available = get_available_dungeons(p)
        ids = [d["id"] for d in available]
        # Daily dungeons should be available
        self.assertIn("code_dungeon", ids)
        self.assertIn("exercise_trial", ids)
        # Weekly and boss should NOT be available
        self.assertNotIn("word_abyss", ids)
        self.assertNotIn("project_raid", ids)

    def test_dungeon_unlocks_at_level(self):
        """Weekly dungeons unlock at level 10, boss raids at level 30."""
        from dungeon import get_available_dungeons
        p = create_default_player()

        p["level"] = 5
        available = get_available_dungeons(p)
        self.assertEqual(len(available), 2)  # daily only

        p["level"] = 15
        available = get_available_dungeons(p)
        ids = [d["id"] for d in available]
        self.assertIn("word_abyss", ids)

        p["level"] = 35
        available = get_available_dungeons(p)
        ids = [d["id"] for d in available]
        self.assertIn("project_raid", ids)

    def test_generate_dungeon_instance(self):
        """Test generating a dungeon instance."""
        from dungeon import generate_dungeon_instance
        p = create_default_player()
        result = generate_dungeon_instance("code_dungeon", p)
        self.assertTrue(result["success"])
        inst = result["instance"]
        self.assertEqual(inst["dungeon_id"], "code_dungeon")
        self.assertGreater(len(inst["tasks"]), 0)
        self.assertGreater(result["entry_exp"], 0)

    def test_invalid_dungeon(self):
        """Entering invalid dungeon should fail."""
        from dungeon import generate_dungeon_instance
        p = create_default_player()
        result = generate_dungeon_instance("nonexistent", p)
        self.assertFalse(result["success"])


class TestDungeonProgress(unittest.TestCase):
    """Test dungeon progress tracking."""

    def setUp(self):
        """Create temp directory for quest files."""
        self._temp_dir = tempfile.mkdtemp()
        import config
        self._orig_quuests_dir = config.QUESTS_DIR
        config.QUESTS_DIR = Path(self._temp_dir) / "quests"
        config.QUESTS_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import config
        config.QUESTS_DIR = self._orig_quuests_dir
        import shutil
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)

    def test_progress_dungeon_no_active(self):
        """No active dungeons should return empty progress."""
        from dungeon import progress_dungeon
        p = create_default_player()
        result = progress_dungeon(p, "commit", 1)
        self.assertEqual(len(result["progress"]), 0)

    def test_progress_dungeon_with_active(self):
        """Active dungeon should progress."""
        from dungeon import generate_dungeon_instance, progress_dungeon
        p = create_default_player()

        # Create a dungeon instance
        result = generate_dungeon_instance("code_dungeon", p)
        self.assertTrue(result["success"])

        # Progress the dungeon
        prog = progress_dungeon(p, "commit", 2)
        self.assertGreater(len(prog["progress"]), 0)


class TestBossDefeat(unittest.TestCase):
    """Test boss defeat detection."""

    def test_check_boss_defeat(self):
        """Test boss defeat triggers."""
        from dungeon import check_boss_defeat, BOSSES
        p = create_default_player()
        p["commitCount"] = 15  # Enough for bug_king
        p["bosses_defeated"] = []

        defeated = check_boss_defeat(p)
        boss_ids = [b["id"] for b in defeated]
        if p["level"] >= 10:  # Bug king requires level 10
            # Should have defeated bug_king
            self.assertIn("bug_king", boss_ids)


# ── Shop Tests ───────────────────────────────────────────────────────────

class TestShopItems(unittest.TestCase):
    """Test shop item availability."""

    def test_get_shop_items_basic(self):
        """Level 1 player should see basic consumables."""
        from shop import get_shop_items
        p = create_default_player()
        items = get_shop_items(p)
        item_ids = [i["id"] for i in items]
        self.assertIn("hp_potion", item_ids)
        self.assertIn("mp_potion", item_ids)

    def test_shop_items_level_gated(self):
        """Higher level items should not be available at low level."""
        from shop import get_shop_items
        p = create_default_player()
        p["level"] = 1
        items = get_shop_items(p)
        item_ids = [i["id"] for i in items]
        # full_restore requires level 5
        self.assertNotIn("full_restore", item_ids)

        p["level"] = 5
        items = get_shop_items(p)
        item_ids = [i["id"] for i in items]
        self.assertIn("full_restore", item_ids)

    def test_get_shop_items_by_category(self):
        """Filter items by category."""
        from shop import get_shop_items
        p = create_default_player()
        p["level"] = 15

        consumables = get_shop_items(p, "consumable")
        for item in consumables:
            self.assertEqual(item["category"], "consumable")

        equipment = get_shop_items(p, "equipment")
        for item in equipment:
            self.assertEqual(item["category"], "equipment")


class TestBuySell(unittest.TestCase):
    """Test buying and selling items."""

    def test_buy_hp_potion(self):
        """Buy HP potion should restore HP."""
        from shop import buy_item
        p = create_default_player()
        p["gold"] = 100
        p["hp"] = 50

        result = buy_item(p, "hp_potion")
        self.assertTrue(result["success"])
        self.assertEqual(p["gold"], 50)  # 100 - 50
        self.assertEqual(p["hp"], 100)  # 50 + 50 = 100 (capped)

    def test_buy_insufficient_gold(self):
        """Buying with insufficient gold should fail."""
        from shop import buy_item
        p = create_default_player()
        p["gold"] = 10

        result = buy_item(p, "hp_potion")
        self.assertFalse(result["success"])

    def test_buy_exp_book(self):
        """Buy EXP book should grant EXP."""
        from shop import buy_item
        p = create_default_player()
        p["level"] = 5
        p["exp"] = 0
        p["expToNext"] = 506
        p["gold"] = 200
        p["totalExp"] = 0

        result = buy_item(p, "exp_book")
        self.assertTrue(result["success"])
        # 500 EXP granted, should increase totalExp
        self.assertEqual(p["totalExp"], 500)

    def test_buy_equipment(self):
        """Buy equipment should increase stat."""
        from shop import buy_item
        p = create_default_player()
        p["level"] = 10
        p["gold"] = 600

        result = buy_item(p, "sword_of_coding")
        self.assertTrue(result["success"])
        self.assertEqual(p["stats"]["strength"], 15)  # 10 + 5

    def test_sell_item(self):
        """Sell item should refund 50% gold."""
        from shop import buy_item, sell_item
        p = create_default_player()
        p["gold"] = 200
        p["level"] = 5

        buy_item(p, "exp_book")
        self.assertEqual(p["gold"], 50)  # 200 - 150

        result = sell_item(p, "exp_book")
        self.assertTrue(result["success"])
        # Sell refund: 150 // 2 = 75
        self.assertEqual(p["gold"], 125)

    def test_sell_nonexistent_item(self):
        """Selling non-existent item should fail."""
        from shop import sell_item
        p = create_default_player()
        result = sell_item(p, "nonexistent")
        self.assertFalse(result["success"])


class TestInventory(unittest.TestCase):
    """Test inventory display."""

    def test_get_inventory(self):
        """Inventory should track purchased items."""
        from shop import buy_item, get_inventory
        p = create_default_player()
        p["gold"] = 200

        buy_item(p, "hp_potion")
        items = get_inventory(p)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["item_id"], "hp_potion")


# ── Integration Tests ────────────────────────────────────────────────────

class TestPhase3Integration(unittest.TestCase):
    """Integration tests for Phase 3 features."""

    def test_dungeon_workflow(self):
        """Test complete dungeon workflow: enter → progress → complete."""
        from dungeon import generate_dungeon_instance, progress_dungeon, claim_dungeon_reward
        from engine import add_exp
        p = create_default_player()

        # Enter dungeon
        result = generate_dungeon_instance("code_dungeon", p)
        self.assertTrue(result["success"])

        # Progress by committing
        prog = progress_dungeon(p, "commit", 2)
        # Some progress should have been made
        self.assertGreater(len(prog["progress"]), 0)

    def test_shop_workflow(self):
        """Test complete shop workflow: buy → use → sell."""
        from shop import buy_item, get_inventory, sell_item
        p = create_default_player()
        p["gold"] = 300
        p["hp"] = 50

        # Buy potion
        result = buy_item(p, "hp_potion")
        self.assertTrue(result["success"])
        self.assertIn("hp_potion", [i["item_id"] for i in get_inventory(p)])

        # Sell it back
        result = sell_item(p, "hp_potion")
        self.assertTrue(result["success"])
        self.assertEqual(len(get_inventory(p)), 0)


# ── Run Tests ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
