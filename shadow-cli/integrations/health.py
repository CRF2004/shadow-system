"""
Shadow CLI - Health Integration Module
Import health data from Xiaomi/Zepp/Apple Health exports and record EXP.
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import config
from engine import add_exp, apply_task_progress, check_achievements


def _calculate_health_exp(steps: int = 0, exercise_min: int = 0, sleep_hours: float = 0) -> dict:
    """Calculate EXP from health data with daily caps.

    Returns dict with exp, steps_exp, exercise_exp, sleep_exp.
    """
    cfg = config.HEALTH_EXP

    steps_exp = min(steps // cfg["steps_per_exp"], 50)
    exercise_exp = min(exercise_min * cfg["exercise_minute_exp"], 100)
    sleep_exp = min(int(sleep_hours * cfg["sleep_hour_exp"]), 50)

    total = steps_exp + exercise_exp + sleep_exp
    total = min(total, cfg["daily_health_cap"])

    return {
        "total": total,
        "steps_exp": steps_exp,
        "exercise_exp": exercise_exp,
        "sleep_exp": sleep_exp,
        "steps": steps,
        "exercise_min": exercise_min,
        "sleep_hours": sleep_hours,
    }


def _record_import(player: dict, source: str, date_str: str, exp: int, details: dict) -> list[str]:
    """Record an import event and grant EXP. Returns messages."""
    messages = []
    levelup_msgs = add_exp(player, exp)
    messages.extend(levelup_msgs)

    # Gold: 10% of exp
    gold = exp // 10
    player["gold"] = player.get("gold", 0) + gold

    # Record import history
    player.setdefault("importHistory", []).append({
        "date": date_str,
        "source": source,
        "exp": exp,
        "gold": gold,
        "details": details,
        "importedAt": datetime.now().isoformat(),
    })

    # Keep only last 100 imports
    if len(player["importHistory"]) > 100:
        player["importHistory"] = player["importHistory"][-100:]

    # Check achievements
    new_ach = check_achievements(player)
    for ach in new_ach:
        messages.append(f"🏆 成就解锁: {ach['name']} (+{ach['reward_exp']} EXP)")

    return messages


# ── JSON Import ────────────────────────────────────────────────────────────

def import_health_json(player: dict, file_path: str) -> dict:
    """Import health data from a JSON export.

    Supported formats:
    - Zepp/Xiaomi Health: {"data": [{"date": "...", "steps": N, "exerciseMinutes": N, "sleepHours": N}]}
    - Generic: {"entries": [...]} or [{"date": "...", "steps": N, ...}]

    Returns summary dict with success, total_exp, entries_processed, messages.
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
        for key in ("data", "entries", "records", "health"):
            if key in data:
                entries = data[key]
                break
        if not entries and "records" in data:
            entries = data["records"]

    if not isinstance(entries, list):
        return {"success": False, "message": "❌ 无效的 JSON 格式，期望数组"}

    total_exp = 0
    entries_processed = 0
    messages = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        date_str = entry.get("date", entry.get("dateTime", entry.get("time", "")))
        steps = int(entry.get("steps", entry.get("stepCount", entry.get("步数", 0))))
        exercise_min = int(entry.get("exerciseMinutes", entry.get("exercise_minutes", entry.get("运动分钟", 0))))
        sleep_hours = float(entry.get("sleepHours", entry.get("sleep_hours", entry.get("sleep", entry.get("睡眠小时", 0)))))

        if not date_str:
            continue

        exp_info = _calculate_health_exp(steps, exercise_min, sleep_hours)
        if exp_info["total"] > 0:
            msgs = _record_import(player, "health", date_str, exp_info["total"], {
                "steps": steps,
                "exercise_min": exercise_min,
                "sleep_hours": sleep_hours,
            })
            messages.extend(msgs)
            total_exp += exp_info["total"]
            entries_processed += 1

        # Store health data
        player.setdefault("healthData", {})[date_str] = {
            "steps": steps,
            "exerciseMin": exercise_min,
            "sleepHours": sleep_hours,
        }

    return {
        "success": True,
        "total_exp": total_exp,
        "entries_processed": entries_processed,
        "messages": messages,
        "message": f"✅ 导入 {entries_processed} 条健康数据，+{total_exp} EXP",
    }


# ── CSV Import ─────────────────────────────────────────────────────────────

def import_health_csv(player: dict, file_path: str) -> dict:
    """Import health data from a CSV file.

    Expected columns: date, steps, exercise_minutes, sleep_hours
    Column names are flexible (case-insensitive, supports Chinese).
    """
    try:
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except (OSError, csv.Error) as e:
        return {"success": False, "message": f"❌ 读取 CSV 失败: {e}"}

    if not rows:
        return {"success": False, "message": "❌ CSV 文件为空"}

    # Normalize column names
    def normalize(col: str) -> str:
        return col.strip().lower().replace(" ", "_")

    total_exp = 0
    entries_processed = 0
    messages = []

    for row in rows:
        normalized = {normalize(k): v for k, v in row.items()}

        date_str = normalized.get("date", normalized.get("时间", normalized.get("日期", "")))
        try:
            steps = int(normalized.get("steps", normalized.get("步数", normalized.get("step", 0))))
            exercise_min = int(normalized.get("exercise_minutes", normalized.get("运动分钟", normalized.get("exercise", 0))))
            sleep_hours = float(normalized.get("sleep_hours", normalized.get("睡眠小时", normalized.get("sleep", 0))))
        except (ValueError, TypeError):
            continue

        if not date_str:
            continue

        exp_info = _calculate_health_exp(steps, exercise_min, sleep_hours)
        if exp_info["total"] > 0:
            msgs = _record_import(player, "health", date_str, exp_info["total"], {
                "steps": steps,
                "exercise_min": exercise_min,
                "sleep_hours": sleep_hours,
            })
            messages.extend(msgs)
            total_exp += exp_info["total"]
            entries_processed += 1

        player.setdefault("healthData", {})[date_str] = {
            "steps": steps,
            "exerciseMin": exercise_min,
            "sleepHours": sleep_hours,
        }

    return {
        "success": True,
        "total_exp": total_exp,
        "entries_processed": entries_processed,
        "messages": messages,
        "message": f"✅ 导入 {entries_processed} 条健康数据 (CSV)，+{total_exp} EXP",
    }


# ── Directory Import ──────────────────────────────────────────────────────

def import_health_export(player: dict, directory: str) -> dict:
    """Scan directory for health export files and import all of them.

    Supports .json and .csv files in the directory.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        return {"success": False, "message": f"❌ 目录不存在: {directory}"}

    total_exp = 0
    total_entries = 0
    all_messages = []

    for f in sorted(dir_path.iterdir()):
        if f.suffix == ".json":
            result = import_health_json(player, str(f))
        elif f.suffix == ".csv":
            result = import_health_csv(player, str(f))
        else:
            continue

        if result["success"]:
            total_exp += result.get("total_exp", 0)
            total_entries += result.get("entries_processed", 0)
            all_messages.extend(result.get("messages", []))

    return {
        "success": True,
        "total_exp": total_exp,
        "entries_processed": total_entries,
        "messages": all_messages,
        "message": f"✅ 扫描目录 {directory}，导入 {total_entries} 条数据，+{total_exp} EXP",
    }


# ── Manual Entry ───────────────────────────────────────────────────────────

def record_health_manual(player: dict, steps: int = 0, exercise_min: int = 0, sleep_hours: float = 0) -> dict:
    """Manually record health data for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    exp_info = _calculate_health_exp(steps, exercise_min, sleep_hours)

    messages = _record_import(player, "health", today, exp_info["total"], {
        "steps": steps,
        "exercise_min": exercise_min,
        "sleep_hours": sleep_hours,
    })

    player.setdefault("healthData", {})[today] = {
        "steps": steps,
        "exerciseMin": exercise_min,
        "sleepHours": sleep_hours,
    }

    return {
        "success": True,
        "total_exp": exp_info["total"],
        "exp_breakdown": exp_info,
        "messages": messages,
        "message": f"🏃 健康数据记录: 步数 {steps}, 运动 {exercise_min}min, 睡眠 {sleep_hours}h → +{exp_info['total']} EXP",
    }


# ── Summary ────────────────────────────────────────────────────────────────

def get_health_summary(player: dict, days: int = 7) -> dict:
    """Get health data summary for the last N days."""
    health_data = player.get("healthData", {})
    import_history = player.get("importHistory", [])

    # Filter recent imports
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent_imports = [
        h for h in import_history
        if h.get("source") == "health" and h.get("date", "") >= cutoff
    ]

    total_steps = 0
    total_exercise = 0
    total_sleep = 0
    total_exp = 0
    days_with_data = 0

    for date_str, data in health_data.items():
        if date_str >= cutoff:
            total_steps += data.get("steps", 0)
            total_exercise += data.get("exerciseMin", 0)
            total_sleep += data.get("sleepHours", 0)
            days_with_data += 1

    for imp in recent_imports:
        total_exp += imp.get("exp", 0)

    return {
        "days": days,
        "days_with_data": days_with_data,
        "total_steps": total_steps,
        "avg_steps": total_steps // max(days_with_data, 1),
        "total_exercise_min": total_exercise,
        "total_sleep_hours": round(total_sleep, 1),
        "total_exp": total_exp,
        "recent_imports": len(recent_imports),
    }
