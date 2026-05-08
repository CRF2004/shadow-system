"""
Shadow System - Engine Tests
Tests for EXP formula, leveling, titles, stats, and streak calculations.
"""

import sys
import os
import unittest
from pathlib import Path

# Add shadow-cli to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from engine import (
    exp_to_next,
    get_title,
    add_exp,
    calculate_power,
    allocate_stat,
    get_exp_for_action,
    get_streak_bonus,
)


# ── Test Fixtures ──────────────────────────────────────────────────────

def make_player(**overrides):
    """Create a minimal player dict for testing."""
    player = {
        "name": "Test",
        "level": 1,
        "exp": 0,
        "expToNext": config.BASE_EXP,
        "hp": config.MAX_HP,
        "mp": config.MAX_MP,
        "stats": {
            "strength": 10,
            "agility": 10,
            "sense": 10,
            "vitality": 10,
            "intelligence": 10,
        },
        "statPoints": 0,
        "gold": 0,
        "soldiers": [],
        "streak": 0,
        "totalExp": 0,
    }
    player.update(overrides)
    return player


# ── EXP Formula Tests (Phase 0.3) ─────────────────────────────────────

class TestExpToNext(unittest.TestCase):
    """Test exp_to_next(level) = 100 * 1.5^(level - 1)"""

    def test_level_1(self):
        self.assertEqual(exp_to_next(1), 100)

    def test_level_2(self):
        # 100 * 1.5^1 = 150
        self.assertEqual(exp_to_next(2), 150)

    def test_level_3(self):
        # 100 * 1.5^2 = 225
        self.assertEqual(exp_to_next(3), 225)

    def test_level_10(self):
        # 100 * 1.5^9 = 3844 (truncated)
        self.assertEqual(exp_to_next(10), 3844)

    def test_level_20(self):
        # 100 * 1.5^19 = 221683
        self.assertEqual(exp_to_next(20), 221683)

    def test_level_50(self):
        # 100 * 1.5^49 = 42508100014
        self.assertEqual(exp_to_next(50), 42508100014)

    def test_monotonically_increasing(self):
        """EXP to next level should always increase."""
        prev = exp_to_next(1)
        for level in range(2, 51):
            curr = exp_to_next(level)
            self.assertGreater(curr, prev,
                f"EXP should increase: level {level-1}={prev} >= level {level}={curr}")
            prev = curr

    def test_smooth_curve_to_level_50(self):
        """Verify the EXP curve values at key milestones to level 50."""
        milestones = {
            1: 100,
            5: 506,
            10: 3844,
            15: 29192,
            20: 221683,
            25: 1683411,
            30: 12783403,
            40: 737155488,
            50: 42508100014,
        }
        for level, expected in milestones.items():
            with self.subTest(level=level):
                self.assertEqual(exp_to_next(level), expected,
                    f"exp_to_next({level}) should be {expected}")

    def test_formula_integrity(self):
        """Verify the formula uses the correct BASE_EXP and EXP_MULTIPLIER."""
        for level in range(1, 51):
            expected = int(config.BASE_EXP * (config.EXP_MULTIPLIER ** (level - 1)))
            self.assertEqual(exp_to_next(level), expected)


# ── Title Mapping Tests ────────────────────────────────────────────────

class TestGetTitle(unittest.TestCase):
    """Test get_title(level) mapping."""

    def test_level_1(self):
        self.assertEqual(get_title(1), "E 级猎人")

    def test_level_9(self):
        self.assertEqual(get_title(9), "E 级猎人")

    def test_level_10(self):
        self.assertEqual(get_title(10), "D 级猎人")

    def test_level_20(self):
        self.assertEqual(get_title(20), "C 级猎人")

    def test_level_30(self):
        self.assertEqual(get_title(30), "B 级猎人")

    def test_level_40(self):
        self.assertEqual(get_title(40), "A 级猎人")

    def test_level_50(self):
        self.assertEqual(get_title(50), "S 级猎人")

    def test_level_70(self):
        self.assertEqual(get_title(70), "国家级猎人")

    def test_level_100(self):
        self.assertEqual(get_title(100), "暗影君主")

    def test_level_99(self):
        self.assertEqual(get_title(99), "国家级猎人")

    def test_boundary_levels(self):
        """Test all title boundaries."""
        boundaries = {
            1: "E 级猎人",
            10: "D 级猎人",
            20: "C 级猎人",
            30: "B 级猎人",
            40: "A 级猎人",
            50: "S 级猎人",
            70: "国家级猎人",
            100: "暗影君主",
        }
        for level, expected in boundaries.items():
            with self.subTest(level=level):
                self.assertEqual(get_title(level), expected)


# ── EXP Addition & Leveling Tests ──────────────────────────────────────

class TestAddExp(unittest.TestCase):
    """Test add_exp(player, amount) and leveling logic."""

    def test_add_exp_no_levelup(self):
        p = make_player(level=1, exp=0, expToNext=100)
        msgs = add_exp(p, 50)
        self.assertEqual(msgs, [])
        self.assertEqual(p["exp"], 50)
        self.assertEqual(p["level"], 1)

    def test_add_exp_single_levelup(self):
        p = make_player(level=1, exp=0, expToNext=100)
        msgs = add_exp(p, 100)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(p["level"], 2)
        self.assertEqual(p["exp"], 0)  # Exp rolled over to 0
        self.assertEqual(p["statPoints"], config.STAT_POINTS_PER_LEVEL)  # 3 points
        self.assertEqual(p["hp"], config.MAX_HP)  # HP reset
        self.assertEqual(p["mp"], config.MAX_MP)  # MP reset

    def test_add_exp_double_levelup(self):
        p = make_player(level=1, exp=0, expToNext=100)
        # Level 1 needs 100, Level 2 needs 150 → total 250
        msgs = add_exp(p, 250)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(p["level"], 3)
        self.assertEqual(p["exp"], 0)
        self.assertEqual(p["statPoints"], config.STAT_POINTS_PER_LEVEL * 2)  # 6 points

    def test_add_exp_exact_levelup_boundary(self):
        """Player at 99 EXP, receives 1 EXP → should level up."""
        p = make_player(level=1, exp=99, expToNext=100)
        msgs = add_exp(p, 1)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(p["level"], 2)
        self.assertEqual(p["exp"], 0)

    def test_add_exp_overshoot_levelup(self):
        """Player receives more EXP than needed → overflow to next level."""
        p = make_player(level=1, exp=50, expToNext=100)
        # Needs 50 more, receives 200 → 150 remaining, but level 2 needs 150
        msgs = add_exp(p, 200)
        self.assertEqual(len(msgs), 2)  # Should level up twice
        self.assertEqual(p["level"], 3)
        self.assertEqual(p["exp"], 0)  # 200 + 50 = 250, 100+150=250, exactly 0 left

    def test_add_exp_hp_mp_reset(self):
        """HP/MP should reset on level up."""
        p = make_player(level=1, exp=0, expToNext=100, hp=30, mp=20)
        add_exp(p, 100)
        self.assertEqual(p["hp"], config.MAX_HP)
        self.assertEqual(p["mp"], config.MAX_MP)

    def test_add_exp_total_exp_tracks(self):
        """totalExp should accumulate across all gains."""
        p = make_player(totalExp=500)
        add_exp(p, 100)
        self.assertEqual(p["totalExp"], 600)

    def test_exp_curve_level_1_to_10(self):
        """Level from 1 to 10 and verify total EXP needed."""
        p = make_player(level=1, exp=0, expToNext=100)
        total_needed = 0
        level = 1
        while level < 10:
            needed = exp_to_next(level)
            total_needed += needed
            add_exp(p, needed)  # Exactly enough for one level
            level += 1
        self.assertEqual(p["level"], 10)
        # Sum of exp_to_next for levels 1..9
        expected = sum(exp_to_next(l) for l in range(1, 10))
        self.assertEqual(total_needed, expected)

    def test_exp_curve_level_1_to_50(self):
        """Verify leveling from 1 to 50 completes without errors."""
        p = make_player(level=1, exp=0, expToNext=100)
        for level in range(1, 50):
            needed = exp_to_next(level)
            msgs = add_exp(p, needed)
            # Should level up exactly once per iteration
            self.assertEqual(len(msgs), 1, f"Expected 1 levelup at level {level}, got {len(msgs)}")
            self.assertEqual(p["level"], level + 1)
        self.assertEqual(p["level"], 50)

    def test_exp_curve_level_1_to_50_batch(self):
        """Add all EXP needed for level 1→50 in one batch."""
        p = make_player(level=1, exp=0, expToNext=100)
        total = sum(exp_to_next(l) for l in range(1, 50))
        msgs = add_exp(p, total)
        self.assertEqual(len(msgs), 49)  # Should level up 49 times
        self.assertEqual(p["level"], 50)


# ── EXP Rewards Tests ──────────────────────────────────────────────────

class TestExpRewards(unittest.TestCase):
    """Test get_exp_for_action(action_type, quantity, streak)."""

    def test_commit(self):
        self.assertEqual(get_exp_for_action("commit", 1, 0), 50)

    def test_commit_capped_at_5(self):
        # Capped at 5 commits/day = 5 * 50 = 250
        self.assertEqual(get_exp_for_action("commit", 10, 0), 250)

    def test_coding_lines(self):
        # 100 lines = 10 EXP
        self.assertEqual(get_exp_for_action("coding_line", 100, 0), 10)

    def test_coding_lines_500(self):
        # 500 lines = 50 EXP
        self.assertEqual(get_exp_for_action("coding_line", 500, 0), 50)

    def test_vocabulary(self):
        self.assertEqual(get_exp_for_action("vocabulary", 10, 0), 10)

    def test_exercise(self):
        # 30 min * 2 = 60 EXP
        self.assertEqual(get_exp_for_action("exercise", 30, 0), 60)

    def test_reading(self):
        # 50 pages * 1 = 50 EXP
        self.assertEqual(get_exp_for_action("reading", 50, 0), 50)

    def test_unknown_action(self):
        self.assertEqual(get_exp_for_action("unknown", 1, 0), 0)

    def test_zero_quantity(self):
        self.assertEqual(get_exp_for_action("commit", 0, 0), 50)  # Base reward

    def test_streak_bonus_level_1(self):
        # 1 day streak = 10% bonus → 50 * 1.1 = 55
        self.assertEqual(get_exp_for_action("commit", 1, 1), 55)

    def test_streak_bonus_level_5(self):
        # 5 day streak = 50% bonus → 50 * 1.5 = 75
        self.assertEqual(get_exp_for_action("commit", 1, 5), 75)

    def test_streak_bonus_level_10(self):
        # 10 day streak = 100% bonus → 50 * 2.0 = 100
        self.assertEqual(get_exp_for_action("commit", 1, 10), 100)


# ── Streak Bonus Tests ─────────────────────────────────────────────────

class TestStreakBonus(unittest.TestCase):
    """Test get_streak_bonus(streak)."""

    def test_no_streak(self):
        self.assertAlmostEqual(get_streak_bonus(0), 1.0)

    def test_one_day(self):
        self.assertAlmostEqual(get_streak_bonus(1), 1.1)

    def test_five_days(self):
        self.assertAlmostEqual(get_streak_bonus(5), 1.5)

    def test_ten_days(self):
        self.assertAlmostEqual(get_streak_bonus(10), 2.0)


# ── Stat Allocation Tests ──────────────────────────────────────────────

class TestAllocateStat(unittest.TestCase):
    """Test allocate_stat(player, stat_key, amount)."""

    def test_valid_allocation(self):
        p = make_player(statPoints=5)
        err = allocate_stat(p, "str", 2)
        self.assertIsNone(err)
        self.assertEqual(p["stats"]["strength"], 12)
        self.assertEqual(p["statPoints"], 3)

    def test_invalid_stat_key(self):
        p = make_player(statPoints=5)
        err = allocate_stat(p, "xyz", 1)
        self.assertIn("无效属性", err)

    def test_negative_amount(self):
        p = make_player(statPoints=5)
        err = allocate_stat(p, "str", -1)
        self.assertIn("必须大于 0", err)

    def test_zero_amount(self):
        p = make_player(statPoints=5)
        err = allocate_stat(p, "str", 0)
        self.assertIn("必须大于 0", err)

    def test_insufficient_points(self):
        p = make_player(statPoints=2)
        err = allocate_stat(p, "str", 5)
        self.assertIn("不足", err)
        # Stats should not change
        self.assertEqual(p["stats"]["strength"], 10)
        self.assertEqual(p["statPoints"], 2)

    def test_all_stat_keys(self):
        """Test all valid stat keys."""
        for key in ["str", "agi", "sen", "vit", "int"]:
            p = make_player(statPoints=10)
            err = allocate_stat(p, key, 1)
            self.assertIsNone(err, f"stat key '{key}' should be valid")


# ── Power Calculation Tests ────────────────────────────────────────────

class TestCalculatePower(unittest.TestCase):
    """Test calculate_power(player)."""

    def test_default_player(self):
        # stats sum = 50, level bonus = 1*10 = 10, soldier bonus = 0
        # total = 50 + 10 + 0 = 60
        p = make_player(level=1)
        self.assertEqual(calculate_power(p), 60)

    def test_with_soldiers(self):
        p = make_player(level=1, soldiers=[{"name": "A", "level": 1}, {"name": "B", "level": 2}])
        # stats = 50, level = 10, soldiers = 2*5 = 10 → total = 70
        self.assertEqual(calculate_power(p), 70)

    def test_high_level(self):
        # stats = 50, level = 50*10 = 500, soldiers = 0 → total = 550
        p = make_player(level=50)
        self.assertEqual(calculate_power(p), 550)


# ── Run Tests ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main()
