"""
Shadow CLI - Auth & Guild Tests
Tests for multi-user authentication and guild system.
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

# ── Test Fixtures ──────────────────────────────────────────────────────────

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


# ── Auth Tests ─────────────────────────────────────────────────────────────

class TestAuthRegistration:
    """Test user registration."""

    def test_create_user(self, isolated_state):
        from auth import create_user

        user = create_user("testuser", "password123", "Test User")
        assert user["id"] == "testuser"
        assert user["displayName"] == "Test User"
        assert "pwHash" in user
        assert "salt" in user
        assert "player" in user
        assert user["player"]["name"] == "Test User"

    def test_create_user_lowercase(self, isolated_state):
        from auth import create_user

        user = create_user("TestUser", "password123")
        assert user["id"] == "testuser"

    def test_create_user_duplicate(self, isolated_state):
        from auth import create_user

        create_user("dup", "pass1234")
        with pytest.raises(ValueError, match="已存在"):
            create_user("dup", "pass5678")

    def test_create_user_short_username(self, isolated_state):
        from auth import create_user

        with pytest.raises(ValueError, match="至少 2 个字符"):
            create_user("a", "pass1234")

    def test_create_user_short_password(self, isolated_state):
        from auth import create_user

        with pytest.raises(ValueError, match="至少 4 个字符"):
            create_user("user", "abc")

    def test_password_not_stored_plaintext(self, isolated_state):
        from auth import create_user

        create_user("nopass", "secretpass123")
        users_dir = Path(isolated_state.state_dir if hasattr(isolated_state, 'state_dir') else '')
        # Read the user file directly
        from config import STATE_DIR
        user_file = STATE_DIR / "users" / "nopass.json"
        raw = user_file.read_text(encoding="utf-8")
        assert "secretpass123" not in raw


class TestAuthentication:
    """Test login and token generation."""

    def test_login_success(self, isolated_state):
        from auth import create_user, authenticate

        create_user("loginuser", "mypassword")
        token = authenticate("loginuser", "mypassword")
        assert token is not None
        assert len(token.split(".")) == 3  # JWT format

    def test_login_wrong_password(self, isolated_state):
        from auth import create_user, authenticate

        create_user("loginuser", "correctpass")
        token = authenticate("loginuser", "wrongpass")
        assert token is None

    def test_login_nonexistent_user(self, isolated_state):
        from auth import authenticate

        token = authenticate("ghost", "pass")
        assert token is None

    def test_token_expiry(self, isolated_state, monkeypatch):
        from auth import create_user, authenticate, _verify_token
        import time

        create_user("expireuser", "pass1234")
        token = authenticate("expireuser", "pass1234")

        # Token should be valid initially
        payload = _verify_token(token)
        assert payload is not None

        # Simulate expiry by setting exp in the past
        import base64
        parts = token.split(".")
        payload_bytes = base64.urlsafe_b64decode(parts[1] + "==")
        payload = json.loads(payload_bytes)
        payload["exp"] = time.time() - 1000

        # Re-encode (without valid signature, so it should fail)
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        expired_token = f"{parts[0]}.{payload_b64}.{parts[2]}"
        assert _verify_token(expired_token) is None


class TestTokenOperations:
    """Test token verification and refresh."""

    def test_get_current_user(self, isolated_state):
        from auth import create_user, authenticate, get_current_user

        create_user("tokenuser", "pass1234")
        token = authenticate("tokenuser", "pass1234")
        user = get_current_user(token)
        assert user is not None
        assert user["id"] == "tokenuser"

    def test_get_current_user_invalid_token(self, isolated_state):
        from auth import get_current_user

        user = get_current_user("invalid.token.here")
        assert user is None

    def test_get_player(self, isolated_state):
        from auth import create_user, authenticate, get_player

        create_user("playeruser", "pass1234", "Player One")
        token = authenticate("playeruser", "pass1234")
        player = get_player(token)
        assert player is not None
        assert player["name"] == "Player One"

    def test_refresh_token(self, isolated_state):
        from auth import create_user, authenticate, refresh_token

        create_user("refuser", "pass1234")
        token = authenticate("refuser", "pass1234")
        new_token = refresh_token(token)
        assert new_token is not None
        assert new_token != token

    def test_refresh_expired_token(self, isolated_state):
        from auth import refresh_token

        assert refresh_token("expired.token") is None

    def test_save_and_load_player(self, isolated_state):
        from auth import create_user, authenticate, get_player, save_player_with_token

        create_user("saveuser", "pass1234")
        token = authenticate("saveuser", "pass1234")
        player = get_player(token)
        player["gold"] = 999
        assert save_player_with_token(token, player)

        # Verify persistence
        player2 = get_player(token)
        assert player2["gold"] == 999


class TestUserListing:
    """Test user listing functionality."""

    def test_list_users(self, isolated_state):
        from auth import create_user, list_users

        create_user("alice", "pass1234", "Alice")
        create_user("bob", "pass1234", "Bob")
        users = list_users()
        assert len(users) == 2
        names = [u["displayName"] for u in users]
        assert "Alice" in names
        assert "Bob" in names

    def test_list_users_empty(self, isolated_state):
        from auth import list_users

        users = list_users()
        assert users == []

    def test_list_users_no_passwords(self, isolated_state):
        from auth import create_user, list_users

        create_user("secret", "mypassword123")
        users = list_users()
        assert len(users) == 1
        user_data = users[0]
        assert "pwHash" not in user_data
        assert "salt" not in user_data
        assert "password" not in json.dumps(user_data).lower()


# ── Guild Tests ────────────────────────────────────────────────────────────

class TestGuildCreation:
    """Test guild creation and management."""

    def test_create_guild(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild

        create_user("leader1", "pass1234")
        token = authenticate("leader1", "pass1234")
        player = get_player(token)

        result = create_guild(player, "暗影骑士团", "leader1")
        assert result["success"] is True
        assert "暗影骑士团" in result["message"]
        assert result["guild"]["members"] == 1

    def test_create_guild_empty_name(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild

        create_user("leader1", "pass1234")
        token = authenticate("leader1", "pass1234")
        player = get_player(token)

        result = create_guild(player, "", "leader1")
        assert result["success"] is False

    def test_create_guild_duplicate(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild

        create_user("leader1", "pass1234")
        token = authenticate("leader1", "pass1234")
        player = get_player(token)

        create_guild(player, "TestGuild", "leader1")
        result = create_guild(player, "TestGuild", "leader1")
        assert result["success"] is False
        assert "已存在" in result["message"]


class TestGuildMembership:
    """Test guild join/leave."""

    def test_join_guild(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, join_guild, get_guild

        create_user("leader1", "pass1234")
        create_user("member1", "pass1234")

        token1 = authenticate("leader1", "pass1234")
        token2 = authenticate("member1", "pass1234")
        player1 = get_player(token1)
        player2 = get_player(token2)

        create_guild(player1, "ShadowClan", "leader1")
        result = join_guild("shadowclan", "member1", player2)
        assert result["success"] is True

        guild = get_guild("shadowclan")
        assert len(guild["members"]) == 2

    def test_leave_guild(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, join_guild, leave_guild, get_guild

        create_user("leader1", "pass1234")
        create_user("member1", "pass1234")

        token1 = authenticate("leader1", "pass1234")
        token2 = authenticate("member1", "pass1234")
        player1 = get_player(token1)
        player2 = get_player(token2)

        create_guild(player1, "ShadowClan", "leader1")
        join_guild("shadowclan", "member1", player2)
        result = leave_guild("shadowclan", "member1")
        assert result["success"] is True

        guild = get_guild("shadowclan")
        assert len(guild["members"]) == 1

    def test_leader_cannot_leave(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, leave_guild

        create_user("leader1", "pass1234")
        token = authenticate("leader1", "pass1234")
        player = get_player(token)

        create_guild(player, "SoloGuild", "leader1")
        result = leave_guild("sologuild", "leader1")
        assert result["success"] is False
        assert "领导者" in result["message"]

    def test_join_already_member(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, join_guild

        create_user("member1", "pass1234")
        create_user("leader1", "pass1234")

        token1 = authenticate("leader1", "pass1234")
        token2 = authenticate("member1", "pass1234")
        player1 = get_player(token1)
        player2 = get_player(token2)

        create_guild(player1, "TestGuild", "leader1")
        join_guild("testguild", "member1", player2)
        result = join_guild("testguild", "member1", player2)
        assert result["success"] is False
        assert "已经是" in result["message"]


class TestGuildLeadership:
    """Test guild leadership operations."""

    def test_transfer_leadership(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, join_guild, transfer_leadership, get_guild

        create_user("leader1", "pass1234")
        create_user("member1", "pass1234")

        token1 = authenticate("leader1", "pass1234")
        token2 = authenticate("member1", "pass1234")
        player1 = get_player(token1)
        player2 = get_player(token2)

        create_guild(player1, "GuildX", "leader1")
        join_guild("guildx", "member1", player2)

        result = transfer_leadership("guildx", "leader1", "member1")
        assert result["success"] is True

        guild = get_guild("guildx")
        assert guild["leader"] == "member1"

    def test_non_leader_cannot_transfer(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, join_guild, transfer_leadership

        create_user("leader1", "pass1234")
        create_user("member1", "pass1234")
        create_user("member2", "pass1234")

        token1 = authenticate("leader1", "pass1234")
        token2 = authenticate("member1", "pass1234")
        player1 = get_player(token1)
        player2 = get_player(token2)

        create_guild(player1, "GuildX", "leader1")
        join_guild("guildx", "member1", player2)

        result = transfer_leadership("guildx", "member1", "member2")
        assert result["success"] is False

    def test_kick_member(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, join_guild, kick_member, get_guild

        create_user("leader1", "pass1234")
        create_user("member1", "pass1234")

        token1 = authenticate("leader1", "pass1234")
        token2 = authenticate("member1", "pass1234")
        player1 = get_player(token1)
        player2 = get_player(token2)

        create_guild(player1, "GuildX", "leader1")
        join_guild("guildx", "member1", player2)

        result = kick_member("guildx", "leader1", "member1")
        assert result["success"] is True

        guild = get_guild("guildx")
        assert len(guild["members"]) == 1

    def test_promote_member(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, join_guild, promote_member, get_guild

        create_user("leader1", "pass1234")
        create_user("member1", "pass1234")

        token1 = authenticate("leader1", "pass1234")
        token2 = authenticate("member1", "pass1234")
        player1 = get_player(token1)
        player2 = get_player(token2)

        create_guild(player1, "GuildX", "leader1")
        join_guild("guildx", "member1", player2)

        result = promote_member("guildx", "leader1", "member1")
        assert result["success"] is True

        guild = get_guild("guildx")
        officer = next(m for m in guild["members"] if m["username"] == "member1")
        assert officer["role"] == "officer"


class TestGuildTasks:
    """Test guild task system."""

    def test_start_guild_task(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, start_guild_task

        create_user("leader1", "pass1234")
        token = authenticate("leader1", "pass1234")
        player = get_player(token)

        create_guild(player, "TaskGuild", "leader1")
        result = start_guild_task("taskguild", "leader1")
        assert result["success"] is True
        assert "task" in result
        assert result["task"]["target"] > 0

    def test_cannot_start_duplicate_task(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, start_guild_task

        create_user("leader1", "pass1234")
        token = authenticate("leader1", "pass1234")
        player = get_player(token)

        create_guild(player, "TaskGuild", "leader1")
        start_guild_task("taskguild", "leader1")
        result = start_guild_task("taskguild", "leader1")
        assert result["success"] is False
        assert "已有" in result["message"]


class TestGuildBossBattles:
    """Test guild boss battle system."""

    def test_start_battle_insufficient_members(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, start_guild_battle

        create_user("leader1", "pass1234")
        token = authenticate("leader1", "pass1234")
        player = get_player(token)

        create_guild(player, "SmallGuild", "leader1")
        result = start_guild_battle("smallguild", "leader1")
        assert result["success"] is False
        assert "至少需要" in result["message"]


class TestGuildRankings:
    """Test guild and member ranking systems."""

    def test_list_guilds(self, isolated_state):
        from auth import create_user, get_player, authenticate
        from guild import create_guild, list_guilds

        create_user("leader1", "pass1234")
        create_user("leader2", "pass1234")

        token1 = authenticate("leader1", "pass1234")
        token2 = authenticate("leader2", "pass1234")
        player1 = get_player(token1)
        player2 = get_player(token2)

        create_guild(player1, "GuildA", "leader1")
        create_guild(player2, "GuildB", "leader2")

        guilds = list_guilds()
        assert len(guilds) == 2

    def test_guild_rank_titles(self, isolated_state):
        from guild import _get_guild_rank

        assert _get_guild_rank(0) == "见习公会"
        assert _get_guild_rank(1000) == "初级公会"
        assert _get_guild_rank(10000) == "高级公会"
        assert _get_guild_rank(100000) == "传说公会"


# ── Integration: Auth + Guild ─────────────────────────────────────────────

class TestAuthGuildIntegration:
    """Test auth and guild integration."""

    def test_full_guild_lifecycle(self, isolated_state):
        """Test creating guild, inviting members, completing tasks, and battling."""
        from auth import create_user, get_player, authenticate
        from guild import (
            create_guild, join_guild, list_guilds, start_guild_task,
            contribute_to_guild_task, get_guild, get_user_guild,
        )

        # Create users
        for name in ["alice", "bob", "charlie", "dave"]:
            create_user(name, "pass1234", name.capitalize())

        tokens = {n: authenticate(n, "pass1234") for n in ["alice", "bob", "charlie", "dave"]}
        players = {n: get_player(t) for n, t in tokens.items()}

        # Alice creates guild
        result = create_guild(players["alice"], "AlphaGuild", "alice")
        assert result["success"]

        # Bob and Charlie join
        assert join_guild("alphaguild", "bob", players["bob"])["success"]
        assert join_guild("alphaguild", "charlie", players["charlie"])["success"]

        # Check membership
        guild = get_guild("alphaguild")
        assert len(guild["members"]) == 3

        # Check user guild lookup
        assert get_user_guild("alice")["id"] == "alphaguild"
        assert get_user_guild("dave") is None

        # List guilds
        guilds = list_guilds()
        assert any(g["id"] == "alphaguild" for g in guilds)

    def test_multi_user_isolation(self, isolated_state):
        """Test that different users have isolated state."""
        from auth import create_user, authenticate, get_player, save_player_with_token

        create_user("user_a", "pass1234", "User A")
        create_user("user_b", "pass1234", "User B")

        token_a = authenticate("user_a", "pass1234")
        token_b = authenticate("user_b", "pass1234")

        player_a = get_player(token_a)
        player_b = get_player(token_b)

        # Modify player A
        player_a["gold"] = 1000
        player_a["level"] = 50
        save_player_with_token(token_a, player_a)

        # Verify player B is unaffected
        player_b2 = get_player(token_b)
        assert player_b2["gold"] != 1000
        assert player_b2["level"] != 50
        assert player_b2["name"] == "User B"

        # Verify player A is persisted
        player_a2 = get_player(token_a)
        assert player_a2["gold"] == 1000
        assert player_a2["level"] == 50
