"""
Shadow CLI - Multi-User Authentication
JWT-like tokens via HMAC-SHA256 (stdlib only). Password hashing with PBKDF2.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime
from pathlib import Path

import config

# ── Token Configuration ───────────────────────────────────────────────────

TOKEN_SECRET_FILE = config.STATE_DIR / "token_secret"
TOKEN_EXPIRY_HOURS = 24 * 7  # 7 days
ALGORITHM = "HS256"

# ── Secret Management ─────────────────────────────────────────────────────

def _load_secret() -> bytes:
    """Load or generate the HMAC signing secret."""
    if TOKEN_SECRET_FILE.exists():
        return TOKEN_SECRET_FILE.read_bytes()
    secret = secrets.token_bytes(32)
    TOKEN_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_SECRET_FILE.write_bytes(secret)
    return secret

# ── User File Paths ────────────────────────────────────────────────────────

def _users_dir() -> Path:
    d = config.STATE_DIR / "users"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _user_file(user_id: str) -> Path:
    return _users_dir() / f"{user_id}.json"

# ── Password Hashing ──────────────────────────────────────────────────────

def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash password with PBKDF2-HMAC-SHA256. Returns (hash, salt)."""
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return pw_hash, salt

def _verify_password(password: str, pw_hash: str, salt: str) -> bool:
    """Verify password against stored hash."""
    computed, _ = _hash_password(password, salt)
    return hmac.compare_digest(computed, pw_hash)

# ── Token Signing ──────────────────────────────────────────────────────────

def _sign_payload(payload: dict) -> str:
    """Create a signed token: base64(payload).base64(signature)."""
    import base64

    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header).encode()
    ).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()

    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        _load_secret(),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    return f"{message}.{sig_b64}"

def _verify_token(token: str) -> dict | None:
    """Verify and decode a token. Returns payload dict or None."""
    import base64

    parts = token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts

    # Verify signature
    message = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        _load_secret(),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    try:
        provided_sig = base64.urlsafe_b64decode(sig_b64 + "==")
    except Exception:
        return None

    if not hmac.compare_digest(expected_sig, provided_sig):
        return None

    # Decode payload
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
        payload = json.loads(payload_bytes)
    except Exception:
        return None

    # Check expiry
    if payload.get("exp", 0) < time.time():
        return None

    return payload

# ── User CRUD ──────────────────────────────────────────────────────────────

def create_user(username: str, password: str, display_name: str | None = None) -> dict:
    """Register a new user. Returns user dict or raises ValueError."""
    username = username.lower().strip()
    if not username or len(username) < 2:
        raise ValueError("用户名至少 2 个字符")
    if len(password) < 4:
        raise ValueError("密码至少 4 个字符")

    user_file = _user_file(username)
    if user_file.exists():
        raise ValueError(f"用户已存在: {username}")

    pw_hash, salt = _hash_password(password)

    # Create default player state
    from state import create_default_player
    player = create_default_player()
    player["name"] = display_name or username
    player["username"] = username

    user_data = {
        "id": username,
        "displayName": player["name"],
        "pwHash": pw_hash,
        "salt": salt,
        "player": player,
        "createdAt": datetime.now().isoformat(),
        "lastLogin": None,
    }

    user_file.write_text(json.dumps(user_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return user_data

def authenticate(username: str, password: str) -> str | None:
    """Authenticate user. Returns token string or None."""
    username = username.lower().strip()
    user_file = _user_file(username)
    if not user_file.exists():
        return None

    user_data = json.loads(user_file.read_text(encoding="utf-8"))
    if not _verify_password(password, user_data["pwHash"], user_data["salt"]):
        return None

    # Update last login
    user_data["lastLogin"] = datetime.now().isoformat()
    user_file.write_text(json.dumps(user_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Issue token
    payload = {
        "sub": username,
        "iat": time.time(),
        "exp": time.time() + TOKEN_EXPIRY_HOURS * 3600,
    }
    return _sign_payload(payload)

def get_current_user(token: str) -> dict | None:
    """Decode token and return user data, or None."""
    payload = _verify_token(token)
    if payload is None:
        return None
    username = payload.get("sub")
    user_file = _user_file(username)
    if not user_file.exists():
        return None
    return json.loads(user_file.read_text(encoding="utf-8"))

def get_player(token: str) -> dict | None:
    """Get the player state for the authenticated user."""
    user = get_current_user(token)
    if user is None:
        return None
    return user.get("player", {})

def save_player_with_token(token: str, player: dict) -> bool:
    """Save player state back to user file."""
    user = get_current_user(token)
    if user is None:
        return False
    user["player"] = player
    user_file = _user_file(user["id"])
    user_file.write_text(json.dumps(user, indent=2, ensure_ascii=False), encoding="utf-8")
    return True

def refresh_token(token: str) -> str | None:
    """Extend token expiry. Returns new token or None."""
    payload = _verify_token(token)
    if payload is None:
        return None
    payload["iat"] = time.time()
    payload["exp"] = time.time() + TOKEN_EXPIRY_HOURS * 3600
    return _sign_payload(payload)

def list_users() -> list[dict]:
    """List all users (without passwords)."""
    users = []
    for f in _users_dir().glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            players = data.get("player", {})
            users.append({
                "id": data["id"],
                "displayName": data.get("displayName", data["id"]),
                "level": players.get("level", 1),
                "title": players.get("title", "E 级猎人"),
                "createdAt": data.get("createdAt"),
                "lastLogin": data.get("lastLogin"),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return sorted(users, key=lambda u: u.get("level", 0), reverse=True)

# ── Fallback: Single-user mode ────────────────────────────────────────────
# If no auth token is provided, use the legacy single-player file.

def _load_fallback_player() -> dict:
    """Load the legacy single-player state."""
    from state import load_player
    return load_player()

def _save_fallback_player(player: dict) -> None:
    """Save to the legacy single-player state."""
    from state import save_player
    save_player(player)
