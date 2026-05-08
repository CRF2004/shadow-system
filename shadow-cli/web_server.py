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
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import date, datetime
from pathlib import Path

# Ensure we can import shadow modules
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import config
from state import load_player, save_player
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

VERSION = "0.5.0"


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
        return load_player()

    def _save_player(self, player: dict):
        save_player(player)

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
        else:
            self._send_json({"error": f"Unknown endpoint: {path}"}, 404)

    def do_GET_static(self):
        """Serve static files."""
        path = self.path.rstrip("/")
        if path == "" or path == "/":
            self.path = "/index.html"
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
        exp = get_exp_for_action(action_type, quantity, streak, combo)

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

        self._save_player(player)

        self._send_json({
            "success": True,
            "exp": exp,
            "levelups": levelup_msgs,
            "taskProgress": task_result,
            "dungeonProgress": dungeon_result,
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
    server = HTTPServer(("0.0.0.0", port), ShadowAPIHandler)
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
