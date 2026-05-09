"""
Shadow CLI - State Management
Handles player data persistence (load/save/create).
"""

import json
from datetime import datetime
from pathlib import Path

import config


def _ensure_dirs():
    """Create state directories if they don't exist."""
    for d in [config.STATE_DIR, config.QUESTS_DIR, config.SOLDIERS_DIR, config.LOGS_DIR, config.INTEGRATIONS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def create_default_player() -> dict:
    """Create a new player with default values."""
    now = datetime.now().isoformat()
    return {
        "name": "Shadow Monarch",
        "title": "E 级猎人",
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
        "gems": 0,
        "soldiers": [],
        "achievements": [],
        "bosses_defeated": [],
        "inventory": [],
        "titleSuffixes": [],
        "guildJoined": False,
        "guildCreated": False,
        "guildTasksCompleted": 0,
        "guildBossesDefeated": 0,
        "totalGoldEarned": 0,
        "streak": 0,
        "combo": 0,
        "totalExp": 0,
        "commitCount": 0,
        "doubleExpNext": 0,
        "extraDungeonToday": 0,
        "importHistory": [],
        "healthData": {},
        "readingData": {},
        "browserData": {},
        "integrationSettings": {
            "health_enabled": False,
            "reading_enabled": False,
            "browser_enabled": False,
        },
        "createdAt": now,
        "lastActive": now,
        "lastDaily": None,
        "dailyProgress": {},
        "logs": [],
    }


def load_player() -> dict:
    """Load player state from disk, or create a new player."""
    _ensure_dirs()
    if config.PLAYER_FILE.exists():
        try:
            with open(config.PLAYER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Migrate missing fields for forward compatibility
            defaults = create_default_player()
            for key, value in defaults.items():
                if key not in data:
                    data[key] = value
            return data
        except (json.JSONDecodeError, KeyError):
            pass
    return create_default_player()


def save_player(player: dict) -> None:
    """Save player state to disk."""
    _ensure_dirs()
    player["lastActive"] = datetime.now().isoformat()
    # Update title based on level
    from engine import get_title
    player["title"] = get_title(player["level"])
    with open(config.PLAYER_FILE, "w", encoding="utf-8") as f:
        json.dump(player, f, indent=2, ensure_ascii=False)


def reset_player() -> dict:
    """Reset player to default (for testing)."""
    if config.PLAYER_FILE.exists():
        config.PLAYER_FILE.unlink()
    return create_default_player()
