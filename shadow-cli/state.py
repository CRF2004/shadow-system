"""
Shadow CLI - State Management
Handles player data persistence (load/save/create).

Phase 9.6: Split large datasets (healthData/readingData/browserData/dailyLog/importHistory)
into separate files, with lazy-loading proxy objects that auto-sync on mutation.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import config

# ── File-backed data keys ──────────────────────────────────────────────────
# These keys are stored in separate files to keep player.json small.
SEPARATED_KEYS = {"healthData", "readingData", "browserData", "dailyLog", "importHistory"}

# Max sizes for separated data
MAX_DAILY_LOG_DAYS = 90
MAX_IMPORT_HISTORY = 50

# ── Helpers ────────────────────────────────────────────────────────────────

def _ensure_dirs():
    """Create state directories if they don't exist."""
    for d in [config.STATE_DIR, config.QUESTS_DIR, config.SOLDIERS_DIR, config.LOGS_DIR, config.INTEGRATIONS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _data_file(key: str) -> Path:
    """Return the file path for a separated data key."""
    return config.STATE_DIR / f"{key}.json"


def _read_separated(key: str, fallback_value):
    """Read separated data from disk, falling back to fallback_value if missing."""
    fpath = _data_file(key)
    if fpath.exists():
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    if isinstance(fallback_value, dict):
        return {}
    return []


def _write_separated(key: str, data) -> None:
    """Write separated data to its own file."""
    _ensure_dirs()
    with open(_data_file(key), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _prune_daily_log(log: list) -> list:
    """Keep only the last MAX_DAILY_LOG_DAYS days of daily log."""
    if len(log) <= MAX_DAILY_LOG_DAYS:
        return log
    cutoff = (datetime.today() - timedelta(days=MAX_DAILY_LOG_DAYS)).date().isoformat()
    return [e for e in log if e.get("date", "") >= cutoff]


def _prune_import_history(history: list) -> list:
    """Keep only the last MAX_IMPORT_HISTORY imports."""
    if len(history) <= MAX_IMPORT_HISTORY:
        return history
    return history[-MAX_IMPORT_HISTORY:]


# ── LazyDict / LazyList proxies ────────────────────────────────────────────
# These are transparent proxy objects: they behave like dict/list but auto-sync
# to disk on every mutation. The rest of the code uses them as normal dict/list.


class LazyDict(dict):
    """A dict that auto-syncs to a separate JSON file on any mutation."""

    def __init__(self, data: dict, key: str):
        super().__init__(data)
        self._key = key
        self._syncing = True

    def _sync(self):
        """Write current state to disk."""
        if getattr(self, "_syncing", True):
            _write_separated(self._key, dict(self))

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._sync()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._sync()

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._sync()

    def pop(self, *args):
        result = super().pop(*args)
        self._sync()
        return result

    def popitem(self):
        result = super().popitem()
        self._sync()
        return result

    def clear(self):
        super().clear()
        self._sync()

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


class LazyList(list):
    """A list that auto-syncs to a separate JSON file on any mutation."""

    def __init__(self, data: list, key: str):
        super().__init__(data)
        self._key = key
        self._syncing = True

    def _sync(self):
        if getattr(self, "_syncing", True):
            _write_separated(self._key, list(self))

    def append(self, item):
        super().append(item)
        self._sync()

    def extend(self, items):
        super().extend(items)
        self._sync()

    def insert(self, index, item):
        super().insert(index, item)
        self._sync()

    def remove(self, item):
        super().remove(item)
        self._sync()

    def pop(self, *args):
        result = super().pop(*args)
        self._sync()
        return result

    def clear(self):
        super().clear()
        self._sync()

    def sort(self, *args, **kwargs):
        super().sort(*args, **kwargs)
        self._sync()


# ── Player defaults ────────────────────────────────────────────────────────

def create_default_player() -> dict:
    """Create a new player with default values."""
    now = datetime.now().isoformat()
    return {
        "schemaVersion": _MIGRATION_VERSION,
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
        "dailyLog": [],
        "onboarded": False,
        "skillConfig": {
            "skills": [],
            "templateUsed": None,
        },
        "logs": [],
    }


# ── Migration ──────────────────────────────────────────────────────────────

_MIGRATION_VERSION = 1

def _migrate_player(data: dict) -> dict:
    """Migrate old player.json to new format, splitting large data into files."""
    defaults = create_default_player()

    # Add missing fields
    for key, value in defaults.items():
        if key not in data:
            data[key] = value

    # Split separated data to files (migration: data in player.json → separate files)
    needs_save = False
    for key in SEPARATED_KEYS:
        if key in data and (isinstance(data[key], (dict, list))):
            # Don't overwrite existing separated file — save_player or
            # LazyList auto-sync already has the current data there.
            # Only migrate when the file does not exist yet (old format).
            if _data_file(key).exists():
                continue
            data_val = data[key]
            # Apply pruning
            if key == "dailyLog" and isinstance(data_val, list):
                data_val = _prune_daily_log(data_val)
                data[key] = data_val
                needs_save = True
            elif key == "importHistory" and isinstance(data_val, list):
                data_val = _prune_import_history(data_val)
                data[key] = data_val
                needs_save = True
            # Write to separate file
            _write_separated(key, data_val)
            # Leave in player dict for backwards compat with old code,
            # but new load_player will use proxies
    if needs_save:
        _ensure_dirs()
        with open(config.PLAYER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return data


# ── Load / Save ────────────────────────────────────────────────────────────

def load_player() -> dict:
    """Load player state from disk, or create a new player.

    Large datasets (healthData, readingData, browserData, dailyLog, importHistory)
    are loaded from separate files via LazyDict/LazyList proxies that auto-sync
    on mutation.
    """
    _ensure_dirs()
    if config.PLAYER_FILE.exists():
        try:
            with open(config.PLAYER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data = _migrate_player(data)
        except (json.JSONDecodeError, KeyError):
            data = create_default_player()
    else:
        data = create_default_player()

    # Wrap separated keys with lazy proxies.
    # Always check the file on disk even if the key is not in player.json
    # (it may have been written by save_player or LazyList auto-sync).
    for key in SEPARATED_KEYS:
        fallback = data.get(key)
        file_data = _read_separated(key, fallback)
        if isinstance(file_data, dict):
            data[key] = LazyDict(file_data, key)
        elif isinstance(file_data, list):
            data[key] = LazyList(file_data, key)

    return data


def save_player(player: dict) -> None:
    """Save player state to disk.

    Separated data (healthData, etc.) is auto-synced by LazyDict/LazyList proxies.
    Only the core player dict (minus separated keys) is written to player.json.
    Separated data keys present in the player dict are flushed to their files.
    """
    _ensure_dirs()
    player["lastActive"] = datetime.now().isoformat()
    # Update title based on level
    from engine import get_title
    player["title"] = get_title(player["level"])

    # Build a clean dict for player.json (exclude separated keys)
    core = {}
    for k, v in player.items():
        if k in SEPARATED_KEYS:
            # Flush in-memory separated data to file (handles cases where
            # nested mutations on LazyList/LazyDict elements bypass auto-sync)
            _write_separated(k, v)
            continue
        core[k] = v

    with open(config.PLAYER_FILE, "w", encoding="utf-8") as f:
        json.dump(core, f, indent=2, ensure_ascii=False)

    # Prune daily log after save
    for key in SEPARATED_KEYS:
        fpath = _data_file(key)
        if not fpath.exists():
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if key == "dailyLog" and isinstance(data, list):
            new_data = _prune_daily_log(data)
            if len(new_data) != len(data):
                _write_separated(key, new_data)
        elif key == "importHistory" and isinstance(data, list):
            new_data = _prune_import_history(data)
            if len(new_data) != len(data):
                _write_separated(key, new_data)


def reset_player() -> dict:
    """Reset player to default (for testing)."""
    if config.PLAYER_FILE.exists():
        config.PLAYER_FILE.unlink()
    # Also remove separated files
    for key in SEPARATED_KEYS:
        fpath = _data_file(key)
        if fpath.exists():
            fpath.unlink()
    return create_default_player()
