"""
Shadow CLI - Browser Activity Integration Module
Import browser study activity and record EXP.
Protocol designed for future browser extension export.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import config
from engine import add_exp, check_achievements


def _calculate_browser_exp(minutes: int = 0) -> dict:
    """Calculate EXP from browser study time with daily cap."""
    cfg = config.BROWSER_EXP
    study_exp = min(minutes * cfg["study_minute_exp"], cfg["daily_browser_cap"])

    return {
        "total": study_exp,
        "minutes": minutes,
    }


def _record_import(player: dict, date_str: str, exp: int, details: dict) -> list[str]:
    """Record an import event and grant EXP. Returns messages."""
    messages = []
    levelup_msgs = add_exp(player, exp)
    messages.extend(levelup_msgs)

    gold = exp // 10
    player["gold"] = player.get("gold", 0) + gold

    player.setdefault("importHistory", []).append({
        "date": date_str,
        "source": "browser",
        "exp": exp,
        "gold": gold,
        "details": details,
        "importedAt": datetime.now().isoformat(),
    })

    if len(player["importHistory"]) > 50:
        player["importHistory"] = player["importHistory"][-50:]

    new_ach = check_achievements(player)
    for ach in new_ach:
        messages.append(f"🏆 成就解锁: {ach['name']} (+{ach['reward_exp']} EXP)")

    return messages


# ── JSON Import ────────────────────────────────────────────────────────────

def import_browser_data(player: dict, file_path: str) -> dict:
    """Import browser study activity from a JSON export.

    Expected format (browser extension protocol):
    {
        "version": 1,
        "entries": [
            {"date": "2026-05-08", "site": "leetcode.com", "minutes": 45},
            {"date": "2026-05-08", "site": "stackoverflow.com", "minutes": 20}
        ]
    }

    Also supports generic: [{"date": "...", "site": "...", "minutes": N}]
    """
    try:
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return {"success": False, "message": f"❌ 读取文件失败: {e}"}

    entries = []
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        for key in ("entries", "data", "records", "activity"):
            if key in data:
                entries = data[key]
                break

    if not isinstance(entries, list):
        return {"success": False, "message": "❌ 无效的 JSON 格式，期望数组"}

    # Aggregate entries by date
    daily_data = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        date_str = entry.get("date", entry.get("dateTime", ""))
        site = entry.get("site", entry.get("url", entry.get("domain", "unknown")))
        minutes = int(entry.get("minutes", entry.get("timeSpent", entry.get("时间", 0))))

        if not date_str:
            continue

        if date_str not in daily_data:
            daily_data[date_str] = {}
        daily_data[date_str][site] = daily_data[date_str].get(site, 0) + minutes

    total_exp = 0
    entries_processed = 0
    messages = []

    for date_str, sites in daily_data.items():
        total_minutes = sum(sites.values())
        exp_info = _calculate_browser_exp(total_minutes)

        if exp_info["total"] > 0:
            msgs = _record_import(player, date_str, exp_info["total"], {
                "minutes": total_minutes,
                "sites": sites,
            })
            messages.extend(msgs)
            total_exp += exp_info["total"]
            entries_processed += 1

        player.setdefault("browserData", {})[date_str] = {
            "totalMinutes": total_minutes,
            "sites": sites,
        }

    return {
        "success": True,
        "total_exp": total_exp,
        "entries_processed": entries_processed,
        "messages": messages,
        "message": f"✅ 导入 {entries_processed} 天浏览器活动数据，+{total_exp} EXP",
    }


# ── Manual Entry ───────────────────────────────────────────────────────────

def record_browser_manual(player: dict, site: str, minutes: int) -> dict:
    """Manually record browser study activity for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    exp_info = _calculate_browser_exp(minutes)

    messages = _record_import(player, today, exp_info["total"], {
        "minutes": minutes,
        "site": site,
    })

    # Store browser data
    browser_data = player.setdefault("browserData", {})
    if today not in browser_data:
        browser_data[today] = {"totalMinutes": 0, "sites": {}}
    browser_data[today]["sites"][site] = browser_data[today]["sites"].get(site, 0) + minutes
    browser_data[today]["totalMinutes"] = sum(browser_data[today]["sites"].values())

    return {
        "success": True,
        "total_exp": exp_info["total"],
        "messages": messages,
        "message": f"🌐 浏览器活动记录: {site} {minutes}min → +{exp_info['total']} EXP",
    }


# ── Summary ────────────────────────────────────────────────────────────────

def get_browser_summary(player: dict, days: int = 7) -> dict:
    """Get browser activity summary for the last N days."""
    browser_data = player.get("browserData", {})
    import_history = player.get("importHistory", [])

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent_imports = [
        h for h in import_history
        if h.get("source") == "browser" and h.get("date", "") >= cutoff
    ]

    total_minutes = 0
    total_exp = 0
    days_with_data = 0
    site_totals = {}

    for date_str, data in browser_data.items():
        if date_str >= cutoff:
            total_minutes += data.get("totalMinutes", 0)
            days_with_data += 1
            for site, mins in data.get("sites", {}).items():
                site_totals[site] = site_totals.get(site, 0) + mins

    for imp in recent_imports:
        total_exp += imp.get("exp", 0)

    return {
        "days": days,
        "days_with_data": days_with_data,
        "total_minutes": total_minutes,
        "avg_minutes": total_minutes // max(days_with_data, 1),
        "total_exp": total_exp,
        "recent_imports": len(recent_imports),
        "site_breakdown": dict(sorted(site_totals.items(), key=lambda x: -x[1])),
    }
