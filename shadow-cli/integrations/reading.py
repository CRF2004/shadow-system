"""
Shadow CLI - Reading Integration Module
Import reading data from WeChat Read (微信读书) exports and record EXP.
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import config
from engine import add_exp, check_achievements


def _calculate_reading_exp(minutes: int = 0, pages: int = 0) -> dict:
    """Calculate EXP from reading data with daily caps.

    Returns dict with total, time_exp, page_exp.
    """
    cfg = config.READING_EXP

    time_exp = min(minutes * cfg["minute_exp"], 80)
    page_exp = min(pages * cfg["page_exp"], 70)
    total = min(time_exp + page_exp, cfg["daily_reading_cap"])

    return {
        "total": total,
        "time_exp": time_exp,
        "page_exp": page_exp,
        "minutes": minutes,
        "pages": pages,
    }


def _record_import(player: dict, source: str, date_str: str, exp: int, details: dict) -> list[str]:
    """Record an import event and grant EXP. Returns messages."""
    messages = []
    levelup_msgs = add_exp(player, exp)
    messages.extend(levelup_msgs)

    gold = exp // 10
    player["gold"] = player.get("gold", 0) + gold

    player.setdefault("importHistory", []).append({
        "date": date_str,
        "source": source,
        "exp": exp,
        "gold": gold,
        "details": details,
        "importedAt": datetime.now().isoformat(),
    })

    if len(player["importHistory"]) > 100:
        player["importHistory"] = player["importHistory"][-100:]

    new_ach = check_achievements(player)
    for ach in new_ach:
        messages.append(f"🏆 成就解锁: {ach['name']} (+{ach['reward_exp']} EXP)")

    return messages


# ── JSON Import ────────────────────────────────────────────────────────────

def import_reading_json(player: dict, file_path: str) -> dict:
    """Import reading data from a JSON export.

    Supported formats:
    - WeChat Read: {"records": [{"date": "...", "minutes": N, "pages": N, "book": "..."}]}
    - Generic: [{"date": "...", "readingMinutes": N, "pagesRead": N, ...}]

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
        for key in ("records", "data", "entries", "reading", "books"):
            if key in data:
                entries = data[key]
                break

    if not isinstance(entries, list):
        return {"success": False, "message": "❌ 无效的 JSON 格式，期望数组"}

    total_exp = 0
    entries_processed = 0
    messages = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        date_str = entry.get("date", entry.get("dateTime", entry.get("time", entry.get("日期", ""))))
        minutes = int(entry.get("minutes", entry.get("readingMinutes", entry.get("阅读时长", entry.get("分钟", 0)))))
        pages = int(entry.get("pages", entry.get("pagesRead", entry.get("页数", entry.get("页", 0)))))
        book_title = entry.get("book", entry.get("bookTitle", entry.get("书名", entry.get("title", ""))))

        if not date_str:
            continue

        exp_info = _calculate_reading_exp(minutes, pages)
        if exp_info["total"] > 0:
            msgs = _record_import(player, "reading", date_str, exp_info["total"], {
                "minutes": minutes,
                "pages": pages,
                "book": book_title,
            })
            messages.extend(msgs)
            total_exp += exp_info["total"]
            entries_processed += 1

        # Store reading data
        player.setdefault("readingData", {})[date_str] = {
            "minutes": minutes,
            "pages": pages,
            "books": [book_title] if book_title else [],
        }

    return {
        "success": True,
        "total_exp": total_exp,
        "entries_processed": entries_processed,
        "messages": messages,
        "message": f"✅ 导入 {entries_processed} 条阅读数据，+{total_exp} EXP",
    }


# ── CSV Import ─────────────────────────────────────────────────────────────

def import_reading_csv(player: dict, file_path: str) -> dict:
    """Import reading data from a CSV file.

    Expected columns: date, minutes, pages, book_title
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

    def normalize(col: str) -> str:
        return col.strip().lower().replace(" ", "_")

    total_exp = 0
    entries_processed = 0
    messages = []

    for row in rows:
        normalized = {normalize(k): v for k, v in row.items()}

        date_str = normalized.get("date", normalized.get("日期", ""))
        try:
            minutes = int(normalized.get("minutes", normalized.get("阅读时长", normalized.get("分钟", normalized.get("reading_minutes", 0)))))
            pages = int(normalized.get("pages", normalized.get("页数", normalized.get("页", 0))))
        except (ValueError, TypeError):
            continue

        book_title = normalized.get("book_title", normalized.get("书名", normalized.get("book", "")))

        if not date_str:
            continue

        exp_info = _calculate_reading_exp(minutes, pages)
        if exp_info["total"] > 0:
            msgs = _record_import(player, "reading", date_str, exp_info["total"], {
                "minutes": minutes,
                "pages": pages,
                "book": book_title,
            })
            messages.extend(msgs)
            total_exp += exp_info["total"]
            entries_processed += 1

        player.setdefault("readingData", {})[date_str] = {
            "minutes": minutes,
            "pages": pages,
            "books": [book_title] if book_title else [],
        }

    return {
        "success": True,
        "total_exp": total_exp,
        "entries_processed": entries_processed,
        "messages": messages,
        "message": f"✅ 导入 {entries_processed} 条阅读数据 (CSV)，+{total_exp} EXP",
    }


# ── Manual Entry ───────────────────────────────────────────────────────────

def record_reading_manual(player: dict, minutes: int = 0, pages: int = 0, book_title: str = "") -> dict:
    """Manually record reading data for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    exp_info = _calculate_reading_exp(minutes, pages)

    messages = _record_import(player, "reading", today, exp_info["total"], {
        "minutes": minutes,
        "pages": pages,
        "book": book_title,
    })

    player.setdefault("readingData", {})[today] = {
        "minutes": minutes,
        "pages": pages,
        "books": [book_title] if book_title else [],
    }

    return {
        "success": True,
        "total_exp": exp_info["total"],
        "exp_breakdown": exp_info,
        "messages": messages,
        "message": f"📖 阅读数据记录: {minutes}分钟, {pages}页, {book_title} → +{exp_info['total']} EXP",
    }


# ── Summary ────────────────────────────────────────────────────────────────

def get_reading_summary(player: dict, days: int = 7) -> dict:
    """Get reading data summary for the last N days."""
    reading_data = player.get("readingData", {})
    import_history = player.get("importHistory", [])

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent_imports = [
        h for h in import_history
        if h.get("source") == "reading" and h.get("date", "") >= cutoff
    ]

    total_minutes = 0
    total_pages = 0
    total_exp = 0
    days_with_data = 0
    all_books = set()

    for date_str, data in reading_data.items():
        if date_str >= cutoff:
            total_minutes += data.get("minutes", 0)
            total_pages += data.get("pages", 0)
            days_with_data += 1
            for b in data.get("books", []):
                if b:
                    all_books.add(b)

    for imp in recent_imports:
        total_exp += imp.get("exp", 0)

    return {
        "days": days,
        "days_with_data": days_with_data,
        "total_minutes": total_minutes,
        "total_pages": total_pages,
        "avg_minutes_per_day": total_minutes // max(days_with_data, 1),
        "total_exp": total_exp,
        "recent_imports": len(recent_imports),
        "books_read": list(all_books),
    }
