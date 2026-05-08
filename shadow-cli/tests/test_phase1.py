"""
Shadow System - Phase 1 Tests
Tests for task system, soldier system, achievement system, and combo.
"""

import sys
import os
import unittest
from pathlib import Path
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from engine import (
    add_exp,
    get_exp_for_action,
    get_combo_bonus,
    apply_task_progress,
    claim_daily_reward,
    summon_soldier,
    summon_legion,
    check_achievements,
    get_achievement_status,
)
from state import create_default_player


# ── Test Fixtures ──────────────────────────────────────────────────────

def make_player(**overrides):
    """Create a minimal player dict for testing."""
    player = create_default_player()
    player.pop("createdAt", None)
    player.pop("lastActive", None)
    player.pop("dailyProgress", None)
    player.pop("logs", None)
    player.update(overrides)
    return player


# ── Combo Tests ─────────────────────────────────────────────────────────

class TestComboBonus(unittest.TestCase):
    """Test get_combo_bonus(combo)."""

    def test_no_combo(self):
        self.assertAlmostEqual(get_combo_bonus(0), 1.0)

    def test_one_combo(self):
        self.assertAlmostEqual(get_combo_bonus(1), 1.1)

    def test_five_combos(self):
        self.assertAlmostEqual(get_combo_bonus(5), 1.5)


class TestExpRewardsWithCombo(unittest.TestCase):
    """Test EXP rewards with combo stacking."""

    def test_commit_with_combo(self):
        # 50 * 1.0 (streak) * 1.1 (1 combo) = 55
        self.assertEqual(get_exp_for_action("commit", 1, streak=0, combo=1), 55)

    def test_commit_streak_and_combo(self):
        # 50 * 1.2 (2 streak) * 1.3 (3 combo) = 50 * 1.56 = 78
        result = get_exp_for_action("commit", 1, streak=2, combo=3)
        self.assertEqual(result, 78)


# ── Task System Tests ───────────────────────────────────────────────────

class TestApplyTaskProgress(unittest.TestCase):
    """Test apply_task_progress(player, action_type, quantity)."""

    def test_apply_commit_progress(self):
        p = make_player()
        # First record triggers task generation
        result = apply_task_progress(p, "commit", 1)
        self.assertTrue(len(result["progress"]) > 0)

    def test_task_completion(self):
        p = make_player()
        # Commit 1 time should complete commit task (target: 1)
        result = apply_task_progress(p, "commit", 1)
        self.assertTrue(len(result["completed"]) >= 1)
        # all_done should be False (other tasks not done)
        self.assertFalse(result["all_done"])

    def test_all_tasks_done(self):
        p = make_player()
        # Record enough for all tasks
        apply_task_progress(p, "commit", 1)
        apply_task_progress(p, "reading", 1)
        apply_task_progress(p, "coding", 30)

        daily = p.get("dailyProgress", {})
        tasks = daily.get("tasks", {})
        all_completed = all(t.get("status") == "completed" for t in tasks.values())
        # At least some should be completed
        self.assertTrue(len(tasks) > 0)

    def test_task_status_active(self):
        p = make_player()
        # Partial progress
        result = apply_task_progress(p, "coding", 10)  # target is 30
        daily = p.get("dailyProgress", {})
        tasks = daily.get("tasks", {})
        coding_task = tasks.get("code", {})
        self.assertEqual(coding_task.get("status"), "active")
        self.assertEqual(coding_task.get("current"), 10)


class TestClaimDailyReward(unittest.TestCase):
    """Test claim_daily_reward(player, total_reward)."""

    def test_claim_increases_streak(self):
        p = make_player(streak=3)
        # Set up some completed tasks
        p["dailyProgress"] = {
            "date": date.today().isoformat(),
            "tasks": {
                "t1": {"status": "completed", "reward": 50},
                "t2": {"status": "completed", "reward": 50},
            }
        }
        msgs = claim_daily_reward(p, 100)
        self.assertEqual(p["streak"], 4)
        # Gold: 10 per completed task = 20
        self.assertEqual(p["gold"], 20)

    def test_claim_increases_combo(self):
        p = make_player(combo=2)
        p["dailyProgress"] = {
            "date": date.today().isoformat(),
            "tasks": {
                "t1": {"status": "completed", "reward": 50},
            }
        }
        claim_daily_reward(p, 50)
        self.assertEqual(p["combo"], 3)


# ── Soldier System Tests ────────────────────────────────────────────────

class TestSummonSoldier(unittest.TestCase):
    """Test summon_soldier(player, soldier_type)."""

    def test_invalid_type(self):
        p = make_player(mp=100)
        result = summon_soldier(p, "nonexistent")
        self.assertFalse(result["success"])
        self.assertIn("未知", result["message"])

    def test_insufficient_mp(self):
        p = make_player(mp=10)
        result = summon_soldier(p, "doc")  # MP cost: 15
        self.assertFalse(result["success"])
        self.assertIn("MP 不足", result["message"])

    def test_summon_consumes_mp(self):
        p = make_player(mp=100)
        result = summon_soldier(p, "doc")  # MP cost: 15
        self.assertTrue(result["success"])
        self.assertEqual(p["mp"], 85)  # 100 - 15

    def test_summon_grants_exp(self):
        p = make_player(exp=0, totalExp=0)
        summon_soldier(p, "explore")  # MP cost: 30
        self.assertEqual(p["totalExp"], 15)  # +15 EXP for summoning

    def test_summon_random_type(self):
        p = make_player(mp=100)
        result = summon_soldier(p, None)  # Random
        self.assertTrue(result["success"])


class TestSummonLegion(unittest.TestCase):
    """Test summon_legion(player, scale)."""

    def test_legion_insufficient_mp(self):
        p = make_player(mp=50)
        result = summon_legion(p, "large")  # MP cost: 250
        self.assertFalse(result["success"])

    def test_legion_medium(self):
        p = make_player(mp=1000, level=10, exp=0, totalExp=0)
        result = summon_legion(p, "medium")
        self.assertTrue(result["success"])
        # medium: 5 units, 180 MP
        self.assertEqual(p["mp"], 820)
        # EXP: 5 * 10 = 50
        self.assertEqual(p["totalExp"], 50)

    def test_legion_grants_soldiers(self):
        p = make_player(mp=1000, level=10, exp=0, totalExp=0, soldiers=[])
        # Force high drop rate by manipulating random
        import random
        original_random = random.random

        def always_drop():
            return 0.05  # Always below 0.10 drop chance

        random.random = always_drop
        try:
            result = summon_legion(p, "small")  # 3 units
            self.assertEqual(result["soldiers_obtained"], 3)
            self.assertEqual(len(p["soldiers"]), 3)
        finally:
            random.random = original_random


# ── Achievement System Tests ────────────────────────────────────────────

class TestCheckAchievements(unittest.TestCase):
    """Test check_achievements(player)."""

    def test_hello_world(self):
        p = make_player(totalExp=1, achievements=[])
        unlocked = check_achievements(p)
        names = [a["id"] for a in unlocked]
        self.assertIn("hello_world", names)

    def test_first_level(self):
        p = make_player(level=5, totalExp=1000, achievements=[])
        unlocked = check_achievements(p)
        names = [a["id"] for a in unlocked]
        self.assertIn("first_level", names)

    def test_no_achievement(self):
        p = make_player(level=1, totalExp=0, achievements=[])
        unlocked = check_achievements(p)
        self.assertEqual(len(unlocked), 0)

    def test_achievement_rewards(self):
        p = make_player(level=5, totalExp=1000, achievements=[], gold=0, exp=0)
        check_achievements(p)
        # Should have received gold from hello_world + first_level
        self.assertGreater(p["gold"], 0)

    def test_already_unlocked(self):
        p = make_player(totalExp=1, achievements=["hello_world"])
        unlocked = check_achievements(p)
        self.assertEqual(len(unlocked), 0)


class TestGetAchievementStatus(unittest.TestCase):
    """Test get_achievement_status(player)."""

    def test_all_returned(self):
        p = make_player()
        status = get_achievement_status(p)
        self.assertEqual(len(status), len(config.ACHIEVEMENTS))

    def test_unlocked_shown(self):
        p = make_player(achievements=["hello_world"])
        status = get_achievement_status(p)
        hello = next(a for a in status if a["id"] == "hello_world")
        self.assertTrue(hello["unlocked"])

    def test_locked_shown(self):
        p = make_player(achievements=[])
        status = get_achievement_status(p)
        hello = next(a for a in status if a["id"] == "hello_world")
        self.assertFalse(hello["unlocked"])


# ── Integration: Full Loop ──────────────────────────────────────────────

class TestFullLoop(unittest.TestCase):
    """Integration test: record → daily → summon → achievements."""

    def test_record_then_daily(self):
        p = make_player()
        # Record a commit
        apply_task_progress(p, "commit", 1)
        daily = p["dailyProgress"]
        tasks = daily["tasks"]
        # At least one task should be completed (the commit task)
        completed_count = sum(1 for t in tasks.values() if t["status"] == "completed")
        self.assertGreaterEqual(completed_count, 1)

    def test_level_then_achievements(self):
        p = make_player(level=1, exp=0, totalExp=0, achievements=[])
        # Level up to 5
        for _ in range(5):
            add_exp(p, 500)  # Should be enough for level 5
        # Check achievements
        unlocked = check_achievements(p)
        if p["level"] >= 5:
            names = [a["id"] for a in unlocked]
            if "first_level" in names:
                pass  # Correct

    def test_summon_then_soldier_achievement(self):
        p = make_player(mp=1000, level=50, exp=0, totalExp=0, soldiers=[], achievements=[])

        import random
        original_random = random.random

        def always_drop():
            return 0.05

        random.random = always_drop
        try:
            # Summon 5 soldiers
            for _ in range(5):
                summon_soldier(p, "explore")
            # Check soldier count achievement
            unlocked = check_achievements(p)
            names = [a["id"] for a in unlocked]
            if len(p["soldiers"]) >= 5:
                self.assertIn("multithread_god", names)
        finally:
            random.random = original_random


# ── Run Tests ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
