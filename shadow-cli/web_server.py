#!/usr/bin/env python3
"""
Shadow CLI - Web Server
RPG-style dashboard. Zero external dependencies.

Usage:
    python web_server.py [--port 8080]

Serves API at localhost:8080/api/*
Serves UI  at localhost:8080/
"""

import argparse
import json
import os
import sys
import uuid
import time
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from datetime import date, datetime
from pathlib import Path

# Ensure we can import shadow modules
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import config
from state import load_player, save_player
from auth import (
    create_user, authenticate, get_current_user, get_player,
    save_player_with_token, list_users, _load_fallback_player,
    _save_fallback_player, refresh_token, TOKEN_EXPIRY_HOURS,
)
from engine import (
    add_exp, calculate_power, get_title, allocate_stat, get_exp_for_action,
    apply_task_progress, claim_daily_reward, summon_soldier, summon_legion,
    check_achievements, get_achievement_status, generate_daily_tasks,
)
from dungeon import get_available_dungeons, generate_dungeon_instance, progress_dungeon, get_active_bosses, check_boss_defeat
from shop import get_shop_items, buy_item, sell_item, get_inventory, SHOP_ITEMS
from git_tracker import scan_commits_and_grant, get_git_root
from file_tracker import scan_files_and_grant
from integrations import (
    record_health_manual, get_health_summary,
    record_reading_manual, get_reading_summary,
    import_browser_data, record_browser_manual, get_browser_summary,
)
from guild import (
    create_guild, disband_guild, join_guild, leave_guild,
    list_guilds, get_guild, get_user_guild, get_guild_rankings,
    get_member_rankings, transfer_leadership, kick_member, promote_member,
    start_guild_task, contribute_to_guild_task,
    start_guild_battle, deal_boss_damage,
    add_guild_log, auto_progress_guild,
)
from analytics import (
    log_daily_activity as _log_activity,
    get_weekly_report, get_monthly_report, get_insights,
    get_streak_history, get_type_breakdown, get_daily_log,
)
from events import event_bus, broadcast, format_sse, format_heartbeat

VERSION = "0.8.0"


class ShadowAPIHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with JSON API endpoints."""

    def __init__(self, *args, **kwargs):
        www_dir = str(SCRIPT_DIR / "www")
        super().__init__(*args, directory=www_dir, **kwargs)

    def log_message(self, format, *args):
        """Quiet logging."""
        pass

    # ── Response helpers ──────────────────────────────────────────────────

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _load_player(self) -> dict:
        token = self._extract_token()
        if token:
            player = get_player(token)
            if player:
                return player
        return _load_fallback_player()

    def _save_player(self, player: dict) -> None:
        token = self._extract_token()
        if token:
            save_player_with_token(token, player)
        else:
            _save_fallback_player(player)

    def _extract_token(self) -> str | None:
        """Extract JWT token from Authorization header."""
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return None

    def _get_username(self) -> str | None:
        """Get username from token, or None for fallback mode."""
        token = self._extract_token()
        if token:
            user = get_current_user(token)
            if user:
                return user["id"]
        return None

    # ── Routing ───────────────────────────────────────────────────────────

    def do_GET(self):
        # Extract path without query string or trailing slash
        path = self.path.split("?")[0].rstrip("/")
        if path == "/api/status":
            self._api_status()
        elif path == "/api/tasks":
            self._api_tasks()
        elif path == "/api/army":
            self._api_army()
        elif path == "/api/achievements":
            self._api_achievements()
        elif path == "/api/dungeons":
            self._api_dungeons()
        elif path == "/api/bosses":
            self._api_bosses()
        elif path == "/api/shop":
            self._api_shop()
        elif path == "/api/inventory":
            self._api_inventory()
        elif path == "/api/integrations":
            self._api_integrations()
        elif path == "/api/health-summary":
            self._api_health_summary()
        elif path == "/api/reading-summary":
            self._api_reading_summary()
        elif path == "/api/browser-summary":
            self._api_browser_summary()
        elif path == "/api/refresh":
            self._api_refresh()
        elif path == "/api/auth/token":
            self._api_refresh_token()
        elif path == "/api/events":
            self._api_events()
        elif path == "/api/guilds":
            self._api_guilds()
        elif path == "/api/guilds/rankings":
            self._api_guild_rankings()
        elif path == "/api/members/rankings":
            self._api_member_rankings()
        elif path == "/api/users":
            self._api_users()
        elif path == "/api/analytics/weekly":
            self._api_weekly_report()
        elif path == "/api/analytics/monthly":
            self._api_monthly_report()
        elif path == "/api/analytics/insights":
            self._api_insights()
        elif path == "/api/analytics/streak":
            self._api_streak_history()
        elif path == "/api/analytics/breakdown":
            self._api_type_breakdown()
        elif path == "/api/analytics/daily-log":
            self._api_daily_log()
        # ── Onboarding endpoints ──
        elif path == "/api/onboard/status":
            self._api_onboard_status()
        elif path == "/api/onboard/presets":
            self._api_onboard_presets()
        elif path == "/api/onboard/templates":
            self._api_onboard_templates()
        elif path == "/api/onboard/categories":
            self._api_onboard_categories()
        else:
            self.do_GET_static()

    def do_POST(self):
        path = self.path.rstrip("/")
        if path == "/api/record":
            self._api_record()
        elif path == "/api/claim-daily":
            self._api_claim_daily()
        elif path == "/api/summon":
            self._api_summon()
        elif path == "/api/legion":
            self._api_legion()
        elif path == "/api/enter-dungeon":
            self._api_enter_dungeon()
        elif path == "/api/buy":
            self._api_buy()
        elif path == "/api/sell":
            self._api_sell()
        elif path == "/api/allocate-stat":
            self._api_allocate_stat()
        elif path == "/api/health":
            self._api_health()
        elif path == "/api/reading":
            self._api_reading()
        elif path == "/api/browser":
            self._api_browser()
        elif path == "/api/scan-git":
            self._api_scan_git()
        elif path == "/api/scan-files":
            self._api_scan_files()
        elif path == "/api/integrations/enable":
            self._api_integration_enable()
        elif path == "/api/integrations/disable":
            self._api_integration_disable()
        # ── OpenAI-compatible chat endpoint ──
        elif path == "/v1/chat/completions":
            self._api_chat()
        # ── Auth endpoints ──
        elif path == "/api/auth/register":
            self._api_register()
        elif path == "/api/auth/login":
            self._api_login()
        # ── Guild endpoints ──
        elif path == "/api/guilds/create":
            self._api_guild_create()
        elif path == "/api/guilds/disband":
            self._api_guild_disband()
        elif path == "/api/guilds/join":
            self._api_guild_join()
        elif path == "/api/guilds/leave":
            self._api_guild_leave()
        elif path == "/api/guilds/info":
            self._api_guild_info()
        elif path == "/api/guilds/my":
            self._api_guild_my()
        elif path == "/api/guilds/transfer":
            self._api_guild_transfer()
        elif path == "/api/guilds/kick":
            self._api_guild_kick()
        elif path == "/api/guilds/promote":
            self._api_guild_promote()
        elif path == "/api/guilds/start-task":
            self._api_guild_start_task()
        elif path == "/api/guilds/contribute":
            self._api_guild_contribute()
        elif path == "/api/guilds/start-battle":
            self._api_guild_start_battle()
        elif path == "/api/guilds/deal-damage":
            self._api_guild_deal_damage()
        # ── Onboarding endpoints ──
        elif path == "/api/onboard/configure":
            self._api_onboard_configure()
        elif path == "/api/onboard/save":
            self._api_onboard_save()
        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    def do_GET_static(self):
        """Serve static files with no-cache for HTML."""
        path = self.path.rstrip("/")
        if path == "" or path == "/":
            self.path = "/index.html"
        # Disable caching for HTML to ensure fresh load
        if self.path.endswith(".html"):
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            try:
                f = open(self.translate_path(self.path), "rb")
                self.wfile.write(f.read())
                f.close()
            except OSError:
                pass
            return
        return super().do_GET()

    # ── API Handlers ──────────────────────────────────────────────────────

    def _api_status(self):
        player = self._load_player()
        title = get_title(player["level"])
        power = calculate_power(player)
        exp_pct = round(100 * player["exp"] / player["expToNext"])
        soldiers = player.get("soldiers", [])
        achievements = player.get("achievements", [])

        self._send_json({
            "version": VERSION,
            "name": player["name"],
            "title": title,
            "level": player["level"],
            "exp": player["exp"],
            "expToNext": player["expToNext"],
            "expPct": exp_pct,
            "hp": player["hp"],
            "mp": player["mp"],
            "gold": player.get("gold", 0),
            "gems": player.get("gems", 0),
            "power": power,
            "stats": player["stats"],
            "statPoints": player.get("statPoints", 0),
            "streak": player.get("streak", 0),
            "combo": player.get("combo", 0),
            "totalExp": player.get("totalExp", 0),
            "commitCount": player.get("commitCount", 0),
            "soldierCount": len(soldiers),
            "achievementCount": len(achievements),
            "achievementTotal": len(config.ACHIEVEMENTS),
            "bossesDefeated": len(player.get("bosses_defeated", [])),
            "inventoryCount": len(player.get("inventory", [])),
            "titleSuffixes": player.get("titleSuffixes", []),
            "skillConfig": player.get("skillConfig", {"skills": []}),
        })

    def _api_tasks(self):
        player = self._load_player()
        today_tasks = cmd_daily_tasks(player)
        self._save_player(player)
        self._send_json({"date": date.today().isoformat(), "tasks": today_tasks})

    def _api_record(self):
        body = self._read_body()
        action_type = body.get("action", body.get("type", ""))
        quantity = int(body.get("quantity", 1))

        player = self._load_player()
        streak = player.get("streak", 0)
        combo = player.get("combo", 0)
        exp = get_exp_for_action(action_type, quantity, streak, combo, player)

        if exp <= 0:
            self._send_json({"success": False, "message": f"未知行为: {action_type}"}, 400)
            return

        if player.get("doubleExpNext", 0) > 0:
            exp *= 2
            player["doubleExpNext"] -= 1

        if action_type == "commit":
            player["commitCount"] = player.get("commitCount", 0) + quantity

        task_result = apply_task_progress(player, action_type, quantity)
        dungeon_result = progress_dungeon(player, action_type, quantity)
        levelup_msgs = add_exp(player, exp)
        new_ach = check_achievements(player)
        defeated = check_boss_defeat(player)

        # Auto-progress guild task/boss
        guild_result = auto_progress_guild(player, action_type, quantity)

        # Log daily activity for analytics
        _log_activity(player, date.today().isoformat(), action_type, quantity, exp, 0)

        self._save_player(player)

        # Broadcast events
        if levelup_msgs:
            broadcast("level_up", {
                "level": player["level"],
                "title": get_title(player["level"]),
                "messages": levelup_msgs,
            })
        if new_ach:
            broadcast("achievement", {
                "achievements": [{"id": a["id"], "name": a["name"]} for a in new_ach],
            })
        if task_result.get("all_done"):
            broadcast("daily_complete", {"date": date.today().isoformat()})

        # Broadcast guild events
        if guild_result.get("success") and guild_result.get("inGuild"):
            broadcast("guild_activity", {
                "guildId": guild_result.get("guildId"),
                "guildName": guild_result.get("guildName"),
                "taskProgress": guild_result.get("taskProgress"),
                "bossDamage": guild_result.get("bossDamage"),
            })

        broadcast("activity", {
            "type": action_type,
            "quantity": quantity,
            "exp": exp,
        })

        self._send_json({
            "success": True,
            "exp": exp,
            "levelups": levelup_msgs,
            "taskProgress": task_result,
            "dungeonProgress": dungeon_result,
            "guildProgress": guild_result,
            "achievements": [{"id": a["id"], "name": a["name"]} for a in new_ach],
            "bossesDefeated": [{"id": b["id"], "name": b["name"]} for b in defeated],
        })

    def _api_claim_daily(self):
        player = self._load_player()
        tasks = player.get("dailyProgress", {}).get("tasks", {})
        total_reward = sum(t.get("reward", 0) for t in tasks.values())
        msgs = claim_daily_reward(player, total_reward)
        new_ach = check_achievements(player)
        self._save_player(player)
        self._send_json({
            "success": True,
            "messages": msgs,
            "achievements": [{"id": a["id"], "name": a["name"]} for a in new_ach],
        })

    def _api_summon(self):
        body = self._read_body()
        soldier_type = body.get("type") or None
        player = self._load_player()
        result = summon_soldier(player, soldier_type)
        self._save_player(player)
        self._send_json(result)

    def _api_legion(self):
        body = self._read_body()
        scale = body.get("scale", "medium")
        player = self._load_player()
        result = summon_legion(player, scale)
        self._save_player(player)
        self._send_json(result)

    def _api_army(self):
        player = self._load_player()
        soldiers = player.get("soldiers", [])
        self._send_json({"soldiers": soldiers, "count": len(soldiers)})

    def _api_achievements(self):
        player = self._load_player()
        status = get_achievement_status(player)
        self._send_json({"achievements": status})

    def _api_dungeons(self):
        player = self._load_player()
        available = get_available_dungeons(player)
        self._send_json({"dungeons": available})

    def _api_enter_dungeon(self):
        body = self._read_body()
        dungeon_id = body.get("id", body.get("dungeon_id", ""))
        player = self._load_player()
        available_ids = [d["id"] for d in get_available_dungeons(player)]
        if dungeon_id not in available_ids:
            self._send_json({"success": False, "message": f"不可用副本: {dungeon_id}"}, 400)
            return
        result = generate_dungeon_instance(dungeon_id, player)
        self._save_player(player)
        self._send_json(result)

    def _api_bosses(self):
        player = self._load_player()
        bosses = get_active_bosses(player)
        defeated = set(player.get("bosses_defeated", []))
        result = []
        for b in bosses:
            result.append({**b, "defeated": b["id"] in defeated})
        self._send_json({"bosses": result})

    def _api_shop(self):
        player = self._load_player()
        category = self._get_query_param("category")
        items = get_shop_items(player, category)
        self._send_json({"items": items, "gold": player.get("gold", 0)})

    def _api_buy(self):
        body = self._read_body()
        item_id = body.get("id", body.get("item_id", ""))
        player = self._load_player()
        result = buy_item(player, item_id)
        if result["success"]:
            self._save_player(player)
        self._send_json(result)

    def _api_sell(self):
        body = self._read_body()
        item_id = body.get("id", body.get("item_id", ""))
        player = self._load_player()
        result = sell_item(player, item_id)
        if result["success"]:
            self._save_player(player)
        self._send_json(result)

    def _api_inventory(self):
        player = self._load_player()
        items = get_inventory(player)
        self._send_json({"items": items, "count": len(items)})

    def _api_integrations(self):
        player = self._load_player()
        settings = player.get("integrationSettings", {})
        health_summary = get_health_summary(player, 7)
        reading_summary = get_reading_summary(player, 7)
        browser_summary = get_browser_summary(player, 7)
        self._send_json({
            "settings": settings,
            "healthEnabled": settings.get("health_enabled", False),
            "readingEnabled": settings.get("reading_enabled", False),
            "browserEnabled": settings.get("browser_enabled", False),
            "totalImports": len(player.get("importHistory", [])),
            "healthSummary": health_summary,
            "readingSummary": reading_summary,
            "browserSummary": browser_summary,
        })

    def _api_health(self):
        body = self._read_body()
        steps = int(body.get("steps", 0))
        exercise_min = int(body.get("exercise", body.get("exercise_min", 0)))
        sleep_hours = float(body.get("sleep", body.get("sleep_hours", 0)))
        player = self._load_player()
        result = record_health_manual(player, steps, exercise_min, sleep_hours)
        if result["success"]:
            self._save_player(player)
        self._send_json(result)

    def _api_health_summary(self):
        player = self._load_player()
        days = int(self._get_query_param("days", "7"))
        summary = get_health_summary(player, days)
        self._send_json(summary)

    def _api_reading(self):
        body = self._read_body()
        minutes = int(body.get("minutes", 0))
        pages = int(body.get("pages", 0))
        book = body.get("book", "")
        player = self._load_player()
        result = record_reading_manual(player, minutes, pages, book)
        if result["success"]:
            self._save_player(player)
        self._send_json(result)

    def _api_reading_summary(self):
        player = self._load_player()
        days = int(self._get_query_param("days", "7"))
        summary = get_reading_summary(player, days)
        self._send_json(summary)

    def _api_browser(self):
        body = self._read_body()
        site = body.get("site", "")
        minutes = int(body.get("minutes", 0))
        player = self._load_player()
        result = record_browser_manual(player, site, minutes)
        if result["success"]:
            self._save_player(player)
        self._send_json(result)

    def _api_browser_summary(self):
        player = self._load_player()
        days = int(self._get_query_param("days", "7"))
        summary = get_browser_summary(player, days)
        self._send_json(summary)

    def _api_allocate_stat(self):
        body = self._read_body()
        stat = body.get("stat", "")
        amount = int(body.get("amount", 0))
        player = self._load_player()
        err = allocate_stat(player, stat, amount)
        if err:
            self._send_json({"success": False, "message": err}, 400)
            return
        self._save_player(player)
        self._send_json({"success": True, "stats": player["stats"], "statPoints": player["statPoints"]})

    def _api_scan_git(self):
        body = self._read_body()
        path = body.get("path", ".")
        git_root = get_git_root(path)
        if not git_root:
            self._send_json({"success": False, "message": "不是 Git 仓库"}, 400)
            return
        player = self._load_player()
        result = scan_commits_and_grant(player, git_root)
        self._save_player(player)
        self._send_json(result)

    def _api_scan_files(self):
        body = self._read_body()
        path = body.get("path", ".")
        player = self._load_player()
        result = scan_files_and_grant(player, path)
        self._save_player(player)
        self._send_json(result)

    def _api_integration_enable(self):
        body = self._read_body()
        target = body.get("target", "")
        player = self._load_player()
        settings = player.get("integrationSettings", {})
        if target == "health":
            settings["health_enabled"] = True
        elif target == "reading":
            settings["reading_enabled"] = True
        elif target == "browser":
            settings["browser_enabled"] = True
        else:
            self._send_json({"success": False, "message": f"未知类型: {target}"}, 400)
            return
        player["integrationSettings"] = settings
        self._save_player(player)
        self._send_json({"success": True, "message": f"已启用 {target}"})

    def _api_integration_disable(self):
        body = self._read_body()
        target = body.get("target", "")
        player = self._load_player()
        settings = player.get("integrationSettings", {})
        if target == "health":
            settings["health_enabled"] = False
        elif target == "reading":
            settings["reading_enabled"] = False
        elif target == "browser":
            settings["browser_enabled"] = False
        else:
            self._send_json({"success": False, "message": f"未知类型: {target}"}, 400)
            return
        player["integrationSettings"] = settings
        self._save_player(player)
        self._send_json({"success": True, "message": f"已停用 {target}"})

    def _api_refresh(self):
        """Full page refresh: returns all data needed to render the dashboard."""
        player = self._load_player()
        title = get_title(player["level"])
        power = calculate_power(player)
        exp_pct = round(100 * player["exp"] / player["expToNext"])
        soldiers = player.get("soldiers", [])
        achievements = player.get("achievements", [])

        today_tasks = cmd_daily_tasks(player)

        self._send_json({
            "status": {
                "version": VERSION,
                "name": player["name"],
                "title": title,
                "level": player["level"],
                "exp": player["exp"],
                "expToNext": player["expToNext"],
                "expPct": exp_pct,
                "hp": player["hp"],
                "mp": player["mp"],
                "gold": player.get("gold", 0),
                "gems": player.get("gems", 0),
                "power": power,
                "stats": player["stats"],
                "statPoints": player.get("statPoints", 0),
                "streak": player.get("streak", 0),
                "combo": player.get("combo", 0),
                "totalExp": player.get("totalExp", 0),
                "commitCount": player.get("commitCount", 0),
                "soldierCount": len(soldiers),
                "achievementCount": len(achievements),
                "achievementTotal": len(config.ACHIEVEMENTS),
                "bossesDefeated": len(player.get("bosses_defeated", [])),
                "inventoryCount": len(player.get("inventory", [])),
            },
            "tasks": today_tasks,
            "achievements": get_achievement_status(player),
            "shop": get_shop_items(player),
            "inventory": get_inventory(player),
            "army": soldiers,
            "dungeons": get_available_dungeons(player),
            "bosses": [b for b in get_active_bosses(player)],
        })

    def _api_events(self):
        """SSE endpoint for real-time events."""
        # Extract subscription types from query
        types_param = self._get_query_param("types", "")
        event_types = [t.strip() for t in types_param.split(",") if t.strip()] if types_param else None

        client_id = f"sse-{uuid.uuid4().hex[:8]}"
        queue = event_bus.subscribe(client_id, event_types)

        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Send initial events from history
            since = self._get_query_param("since")
            history = event_bus.get_history(event_types, since)
            for evt in history:
                self.wfile.write(format_sse(evt).encode("utf-8"))
                self.wfile.flush()

            # Stream new events
            while True:
                try:
                    event = queue.get(timeout=HEARTBEAT_INTERVAL)
                    self.wfile.write(format_sse(event).encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    # Queue timeout → send heartbeat
                    try:
                        self.wfile.write(format_heartbeat().encode("utf-8"))
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        break
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            event_bus.unsubscribe(client_id)

    def _get_query_param(self, key: str, default: str = "") -> str:
        """Extract query parameter from URL."""
        if "?" in self.path:
            query = self.path.split("?", 1)[1]
            for param in query.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    if k == key:
                        return v
        return default

    def _api_chat(self):
        """OpenAI-compatible chat completion endpoint."""
        from chat_processor import parse_message, execute_action, build_chat_response, stream_response

        body = self._read_body()
        messages = body.get("messages", [])
        stream = body.get("stream", False)

        # Extract the last user message
        user_text = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_text = msg.get("content", "")
                break

        if not user_text:
            self._send_json({"error": "No user message found"}, 400)
            return

        # Parse & execute
        player = self._load_player()
        parsed = parse_message(user_text)
        action_result = execute_action(player, parsed["action"], parsed["params"])
        model = body.get("model", "shadow-cli-v1")

        if stream:
            # Streaming response
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            for chunk in stream_response(action_result, model):
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
        else:
            response = build_chat_response(action_result, model)
            self._send_json(response)

    # ── Auth API Handlers ──────────────────────────────────────────────────

    def _api_register(self):
        """Register a new user."""
        body = self._read_body()
        username = body.get("username", "")
        password = body.get("password", "")
        display_name = body.get("displayName", username)

        try:
            create_user(username, password, display_name)
        except ValueError as e:
            self._send_json({"success": False, "message": str(e)}, 400)
            return

        # Auto-login after registration
        token = authenticate(username, password)
        self._send_json({
            "success": True,
            "token": token,
            "message": f"注册成功，欢迎 {display_name}！",
        })

    def _api_login(self):
        """Authenticate and get token."""
        body = self._read_body()
        username = body.get("username", "")
        password = body.get("password", "")

        token = authenticate(username, password)
        if token is None:
            self._send_json({"success": False, "message": "用户名或密码错误"}, 401)
            return

        self._send_json({"success": True, "token": token})

    def _api_refresh_token(self):
        """Refresh/extend authentication token."""
        token = self._extract_token()
        if not token:
            self._send_json({"success": False, "message": "未提供认证令牌"}, 401)
            return

        new_token = refresh_token(token)
        if new_token is None:
            self._send_json({"success": False, "message": "令牌已过期，请重新登录"}, 401)
            return

        self._send_json({"success": True, "token": new_token})

    def _api_users(self):
        """List all registered users."""
        users = list_users()
        self._send_json({"users": users})

    # ── Guild API Handlers ────────────────────────────────────────────────

    def _api_guild_create(self):
        """Create a guild."""
        body = self._read_body()
        guild_name = body.get("name", "")
        username = self._get_username() or "fallback"
        player = self._load_player()

        # Check if already in a guild
        existing = get_user_guild(username or "fallback")
        if existing:
            self._send_json({"success": False, "message": f"你已在公会 [{existing['name']}] 中"}, 400)
            return

        result = create_guild(player, guild_name, username or "fallback")
        if result["success"]:
            player["guildCreated"] = True
            player["guildJoined"] = True
            self._save_player(player)
        self._send_json(result)

    def _api_guild_disband(self):
        """Disband a guild (leader only)."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        username = self._get_username() or "fallback"
        result = disband_guild(guild_id, username)
        self._send_json(result)

    def _api_guild_join(self):
        """Join a guild."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        username = self._get_username() or "fallback"
        player = self._load_player()
        result = join_guild(guild_id, username, player)
        if result["success"]:
            player["guildJoined"] = True
            self._save_player(player)
        self._send_json(result)

    def _api_guild_leave(self):
        """Leave a guild."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        username = self._get_username() or "fallback"
        result = leave_guild(guild_id, username)
        self._send_json(result)

    def _api_guild_info(self):
        """Get guild details."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        guild = get_guild(guild_id)
        if not guild:
            self._send_json({"success": False, "message": "公会不存在"}, 404)
            return

        self._send_json({
            "id": guild["id"],
            "name": guild["name"],
            "leader": guild["leader"],
            "contribution": guild["contribution"],
            "rank": guild["rank"],
            "members": guild["members"],
            "memberCount": len(guild["members"]),
            "activeTask": guild.get("activeTask"),
            "activeBoss": guild.get("activeBoss"),
            "battleCount": len(guild.get("battleHistory", [])),
            "taskCount": len(guild.get("taskHistory", [])),
            "logs": guild.get("logs", [])[-20:],
        })

    def _api_guild_my(self):
        """Get current user's guild info."""
        username = self._get_username() or "fallback"
        guild = get_user_guild(username)
        if not guild:
            self._send_json({"success": False, "message": "未加入任何公会"})
            return

        self._send_json({
            "success": True,
            "id": guild["id"],
            "name": guild["name"],
            "leader": guild["leader"],
            "contribution": guild["contribution"],
            "rank": guild["rank"],
            "members": guild["members"],
            "memberCount": len(guild["members"]),
            "activeTask": guild.get("activeTask"),
            "activeBoss": guild.get("activeBoss"),
        })

    def _api_guilds(self):
        """List all guilds."""
        guilds = list_guilds()
        self._send_json({"guilds": guilds})

    def _api_guild_rankings(self):
        """Get guild rankings."""
        rankings = get_guild_rankings()
        self._send_json({"rankings": rankings})

    def _api_member_rankings(self):
        """Get member rankings for a guild."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        rankings = get_member_rankings(guild_id)
        self._send_json({"rankings": rankings})

    def _api_guild_transfer(self):
        """Transfer guild leadership."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        new_leader = body.get("newLeader", body.get("new_leader", ""))
        username = self._get_username() or "fallback"
        result = transfer_leadership(guild_id, username, new_leader)
        self._send_json(result)

    def _api_guild_kick(self):
        """Kick a member."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        target = body.get("target", "")
        username = self._get_username() or "fallback"
        result = kick_member(guild_id, username, target)
        self._send_json(result)

    def _api_guild_promote(self):
        """Promote a member to officer."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        target = body.get("target", "")
        username = self._get_username() or "fallback"
        result = promote_member(guild_id, username, target)
        self._send_json(result)

    def _api_guild_start_task(self):
        """Start a guild task."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        username = self._get_username() or "fallback"
        result = start_guild_task(guild_id, username)
        self._send_json(result)

    def _api_guild_contribute(self):
        """Contribute to guild task."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        action_type = body.get("actionType", body.get("action_type", ""))
        quantity = int(body.get("quantity", 1))
        username = self._get_username() or "fallback"
        result = contribute_to_guild_task(guild_id, username, action_type, quantity)

        if result.get("success"):
            broadcast("guild_task_progress", {
                "guildId": guild_id,
                "progress": result.get("progress", 0),
                "target": result.get("target", 0),
                "completed": result.get("completed", False),
                "username": username,
            })
            if result.get("completed"):
                broadcast("guild_task_complete", {
                    "guildId": guild_id,
                    "rewards": result.get("rewards", {}),
                })

        self._send_json(result)

    def _api_guild_start_battle(self):
        """Start a guild boss battle."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        username = self._get_username() or "fallback"
        result = start_guild_battle(guild_id, username)

        if result.get("success"):
            broadcast("guild_battle_start", {
                "guildId": guild_id,
                "boss": result.get("boss", {}),
            })

        self._send_json(result)

    def _api_guild_deal_damage(self):
        """Deal damage to guild boss."""
        body = self._read_body()
        guild_id = body.get("guildId", body.get("guild_id", ""))
        action_type = body.get("actionType", body.get("action_type", ""))
        quantity = int(body.get("quantity", 1))
        username = self._get_username() or "fallback"
        result = deal_boss_damage(guild_id, username, action_type, quantity)

        if result.get("success"):
            broadcast("guild_battle_damage", {
                "guildId": guild_id,
                "damage": result.get("damage", 0),
                "bossHp": result.get("bossHp", 0),
                "bossMaxHp": result.get("bossMaxHp", 0),
                "defeated": result.get("defeated", False),
                "username": username,
            })
            if result.get("defeated"):
                broadcast("guild_battle_victory", {
                    "guildId": guild_id,
                    "rewards": result.get("rewards", {}),
                })

        self._send_json(result)

    # ── Analytics API Handlers ─────────────────────────────────────────────

    def _api_weekly_report(self):
        """Get weekly analytics report."""
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        offset = int(params.get("offset", [0])[0])
        player = self._load_player()
        report = get_weekly_report(player, offset)
        # Convert daily_data tuples to list of dicts for JSON
        report["daily_data"] = [{"date": d, "exp": e} for d, e in report.get("daily_data", [])]
        report["missing_days"] = report.get("missing_days", [])
        self._send_json(report)

    def _api_monthly_report(self):
        """Get monthly analytics report."""
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        offset = int(params.get("offset", [0])[0])
        player = self._load_player()
        report = get_monthly_report(player, offset)
        self._send_json(report)

    def _api_insights(self):
        """Get personalized insights."""
        player = self._load_player()
        insights = get_insights(player)
        self._send_json({"insights": insights})

    def _api_streak_history(self):
        """Get streak history stats."""
        player = self._load_player()
        stats = get_streak_history(player)
        self._send_json(stats)

    def _api_type_breakdown(self):
        """Get activity type breakdown."""
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        days = int(params.get("days", [30])[0])
        player = self._load_player()
        breakdown = get_type_breakdown(player, days)
        self._send_json(breakdown)

    def _api_daily_log(self):
        """Get daily activity log."""
        player = self._load_player()
        log = get_daily_log(player)
        self._send_json({"log": log})

    # ── Onboarding API Handlers ────────────────────────────────────────────

    def _api_onboard_status(self):
        """Check onboarding status."""
        player = self._load_player()
        onboarded = player.get("onboarded", False)
        skill_config = player.get("skillConfig", {})
        self._send_json({
            "onboarded": onboarded,
            "skills": skill_config.get("skills", []),
            "template_used": skill_config.get("templateUsed"),
        })

    def _api_onboard_presets(self):
        """Get onboarding skill presets."""
        from skill_config import get_presets
        presets = get_presets()
        self._send_json({"presets": presets})

    def _api_onboard_templates(self):
        """Get all skill templates."""
        from skill_config import get_all_templates
        templates = get_all_templates()
        self._send_json({"templates": templates})

    def _api_onboard_categories(self):
        """Get skill categories."""
        from skill_config import get_categories
        categories = get_categories()
        self._send_json({"categories": categories})

    def _api_onboard_configure(self):
        """Generate skill configs from descriptions (LLM or keyword fallback)."""
        body = self._read_body()
        descriptions = body.get("descriptions", [])
        preset = body.get("preset")

        if preset:
            # Load configs from a preset
            from skill_config import get_presets, generate_skill_configs
            presets = get_presets()
            p = next((x for x in presets if x["id"] == preset), None)
            if p:
                configs = generate_skill_configs(p["skills"])
                self._send_json({"configs": configs, "preset_name": p["name"]})
                return
            self._send_json({"error": f"Unknown preset: {preset}"}, 404)
            return

        if descriptions:
            from skill_config import generate_skill_configs
            configs = generate_skill_configs(descriptions)
            self._send_json({"configs": configs})
            return

        self._send_json({"error": "Provide 'descriptions' or 'preset'"}, 400)

    def _api_onboard_save(self):
        """Save skill configuration and mark player as onboarded."""
        body = self._read_body()
        skills = body.get("skills", [])
        template_used = body.get("template_used")

        player = self._load_player()
        player["skillConfig"] = {
            "skills": skills,
            "templateUsed": template_used,
        }
        player["onboarded"] = True
        self._save_player(player)

        self._send_json({
            "success": True,
            "message": f"已配置 {len(skills)} 项技能",
            "skills": skills,
        })


def cmd_daily_tasks(player: dict) -> list[dict]:
    """Get today's daily tasks with progress."""
    from datetime import date
    today = date.today().isoformat()
    daily = player.get("dailyProgress", {})

    if daily.get("date") != today or "tasks" not in daily:
        tasks = generate_daily_tasks(player)
        daily = {"date": today, "tasks": {}}
        for t in tasks:
            daily["tasks"][t["id"]] = {**t, "current": 0, "status": "pending"}
        player["dailyProgress"] = daily

    return list(daily.get("tasks", {}).values())


def run_server(port: int = 8080):
    """Start the web server."""
    server = ThreadingHTTPServer(("0.0.0.0", port), ShadowAPIHandler)
    print(f"""
┌──────────────────────────────────────────────┐
│  Shadow CLI v{VERSION} - 暗影君主 Web 面板        │
├──────────────────────────────────────────────┤
│  地址: http://localhost:{port}                     │
│  API:  http://localhost:{port}/api/status        │
│  按 Ctrl+C 退出                                 │
└──────────────────────────────────────────────┘""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止服务")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shadow CLI Web Server")
    parser.add_argument("--port", type=int, default=8080, help="端口号 (默认 8080)")
    args = parser.parse_args()
    run_server(args.port)
