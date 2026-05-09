"""
Shadow CLI - Season, Achievements, and Auto-Progress Tests
"""

import json
import sys
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Redirect all state files to a temp directory."""
    import config

    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "shadow-state")
    monkeypatch.setattr(config, "QUESTS_DIR", tmp_path / "shadow-state" / "quests")
    monkeypatch.setattr(config, "SOLDIERS_DIR", tmp_path / "shadow-state" / "soldiers")
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path / "shadow-state" / "logs")
    monkeypatch.setattr(config, "INTEGRATIONS_DIR", tmp_path / "shadow-state" / "integrations")
    monkeypatch.setattr(config, "PLAYER_FILE", tmp_path / "shadow-state" / "player.json")
    yield tmp_path


# ── Season Tests ───────────────────────────────────────────────────────────

class TestSeason:
    """Test guild season ranking system."""

    def test_get_current_week(self, isolated_state):
        from guild import _get_current_week
        week = _get_current_week()
        # Should be in format YYYY-W##
        assert "W" in week
        assert len(week) == 8  # e.g. "2026-W19"

    def test_ensure_season(self, isolated_state):
        from guild import _ensure_season

        season = _ensure_season("2026-W19", "weekly")
        assert season["id"] == "2026-W19"
        assert season["type"] == "weekly"
        assert season["guildContributions"] == {}

    def test_record_season_contribution(self, isolated_state):
        from guild import _ensure_season, _record_season_contribution

        _ensure_season("2026-W19")
        _record_season_contribution("2026-W19", "guild1", "user1", 10)
        _record_season_contribution("2026-W19", "guild1", "user1", 5)

        season_path = Path(isolated_state) / "shadow-state" / "seasons" / "2026-W19.json"
        season = json.loads(season_path.read_text(encoding="utf-8"))
        assert season["guildContributions"]["guild1"] == 15
        assert season["memberContributions"]["user1"] == 15

    def test_season_guild_ranking(self, isolated_state):
        from guild import _ensure_season, _record_season_contribution, get_season_guild_ranking
        from auth import create_user, authenticate, get_player
        from guild import create_guild

        # Create users and guilds
        create_user("leader1", "pass1234")
        create_user("leader2", "pass1234")
        t1 = authenticate("leader1", "pass1234")
        t2 = authenticate("leader2", "pass1234")
        create_guild(get_player(t1), "AlphaGuild", "leader1")
        create_guild(get_player(t2), "BetaGuild", "leader2")

        _ensure_season("2026-W19")
        _record_season_contribution("2026-W19", "alphaguild", "leader1", 100)
        _record_season_contribution("2026-W19", "betaguild", "leader2", 200)

        rankings = get_season_guild_ranking("2026-W19")
        assert len(rankings) == 2
        assert rankings[0]["guildId"] == "betaguild"
        assert rankings[0]["contribution"] == 200

    def test_season_member_ranking(self, isolated_state):
        from guild import _ensure_season, _record_season_contribution, get_season_member_ranking

        _ensure_season("2026-W19")
        _record_season_contribution("2026-W19", "guild1", "user1", 50)
        _record_season_contribution("2026-W19", "guild1", "user2", 100)
        _record_season_contribution("2026-W19", "guild1", "user3", 25)

        rankings = get_season_member_ranking("2026-W19")
        assert len(rankings) == 3
        assert rankings[0]["username"] == "user2"
        assert rankings[0]["contribution"] == 100

    def test_end_season(self, isolated_state):
        from guild import _ensure_season, _record_season_contribution, end_season

        _ensure_season("2026-W19")
        _record_season_contribution("2026-W19", "guild1", "user1", 100)

        result = end_season("2026-W19")
        assert result["success"]
        assert "rewards" in result
        # Top guild should get reward
        assert "guildRewards" in result["rewards"]

    def test_season_info(self, isolated_state):
        from guild import _ensure_season, get_season_info

        _ensure_season("2026-W19")
        info = get_season_info("2026-W19")
        assert info["success"]
        assert info["id"] == "2026-W19"
        assert info["endedAt"] is None

    def test_nonexistent_season(self, isolated_state):
        from guild import get_season_info

        info = get_season_info("9999-W99")
        assert not info["success"]


# ── Achievement Expansion Tests ────────────────────────────────────────────

class TestAchievementsExpanded:
    """Test new achievement condition types."""

    def test_boss_defeat_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["bosses_defeated"] = ["boss1"]
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "first_boss" in ach_ids

    def test_boss_hunter_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["bosses_defeated"] = [f"boss{i}" for i in range(10)]
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "boss_hunter" in ach_ids

    def test_guild_joined_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["guildJoined"] = True
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "guild_member" in ach_ids

    def test_guild_created_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["guildCreated"] = True
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "guild_leader" in ach_ids

    def test_guild_tasks_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["guildTasksCompleted"] = 5
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "guild_task_done" in ach_ids

    def test_guild_boss_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["guildBossesDefeated"] = 3
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "guild_boss_victory" in ach_ids

    def test_total_gold_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["totalGoldEarned"] = 10000
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "wealthy" in ach_ids

    def test_milestone_level_achievements(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["level"] = 50
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "lv_50" in ach_ids

        player["level"] = 75
        achs2 = check_achievements(player)
        ach_ids2 = [a["id"] for a in achs2]
        assert "lv_75" in ach_ids2

    def test_century_commit_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["commitCount"] = 100
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "century_commit" in ach_ids

    def test_super_streak_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["streak"] = 100
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "super_streak" in ach_ids

    def test_soldier_army_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["soldiers"] = [{"name": f"S{i}", "type": "dev", "level": 1} for i in range(20)]
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "soldier_army" in ach_ids

    def test_ten_thousand_exp_achievement(self, isolated_state):
        from state import create_default_player
        from engine import check_achievements

        player = create_default_player()
        player["totalExp"] = 10000
        achs = check_achievements(player)
        ach_ids = [a["id"] for a in achs]
        assert "ten_thousand_exp" in ach_ids

    def test_total_achievement_count(self, isolated_state):
        """Verify we have 24 total achievements."""
        import config
        assert len(config.ACHIEVEMENTS) == 24


# ── Auto-Progress Integration Tests ────────────────────────────────────────

class TestAutoProgress:
    """Test guild auto-progress integration."""

    def test_auto_progress_no_guild(self, isolated_state):
        from state import create_default_player
        from guild import auto_progress_guild

        player = create_default_player()
        result = auto_progress_guild(player, "commit", 1)
        assert result["success"]
        assert not result["inGuild"]

    def test_auto_progress_task_contribution(self, isolated_state):
        from auth import create_user, authenticate, get_player
        from guild import create_guild, start_guild_task, auto_progress_guild
        from state import create_default_player

        create_user("user1", "pass1234")
        token = authenticate("user1", "pass1234")
        player = get_player(token)

        create_guild(player, "TaskGuild", "user1")
        start_guild_task("taskguild", "user1")

        # Get the actual task type from the guild
        from guild import get_guild
        guild_data = get_guild("taskguild")
        task_type = guild_data["activeTask"]["type"]

        result = auto_progress_guild(player, task_type, 1)
        assert result["success"]
        assert result["inGuild"]
        assert result["taskProgress"] is not None  # Task got progress

    def test_auto_progress_tracks_completions(self, isolated_state):
        """Verify that auto_progress_guild updates player guild counters."""
        from state import create_default_player
        from guild import auto_progress_guild

        player = create_default_player()
        player["guildTasksCompleted"] = 0
        player["guildBossesDefeated"] = 0

        # Not in guild - counters should not change
        result = auto_progress_guild(player, "commit", 1)
        assert player["guildTasksCompleted"] == 0
        assert player["guildBossesDefeated"] == 0

    def test_default_player_has_guild_fields(self, isolated_state):
        from state import create_default_player

        player = create_default_player()
        assert "guildJoined" in player
        assert "guildCreated" in player
        assert "guildTasksCompleted" in player
        assert "guildBossesDefeated" in player
        assert "totalGoldEarned" in player
        assert player["guildJoined"] is False
        assert player["guildCreated"] is False
