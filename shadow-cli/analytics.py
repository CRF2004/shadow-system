"""Data analytics module for Shadow System gamification CLI."""

from datetime import date, datetime, timedelta
from typing import Any

def log_daily_activity(player: dict, date_str: str, action_type: str, quantity: int, exp: int, gold: int) -> None:
    """Record an action in the daily log for the given date."""
    daily_log: list[dict] = player.setdefault("dailyLog", [])
    for entry in daily_log:
        if entry["date"] == date_str:
            entry["actions"].append({"type": action_type, "quantity": quantity, "exp": exp})
            entry["totalExp"] += exp
            entry["totalGold"] += gold
            return
    daily_log.append({"date": date_str, "actions": [{"type": action_type, "quantity": quantity, "exp": exp}],
                      "totalExp": exp, "totalGold": gold, "streak": player.get("streak", 0),
                      "level": player.get("level", 1)})

def get_daily_log(player: dict) -> list[dict]:
    """Return the player's daily log, newest first."""
    return sorted(player.get("dailyLog", []), key=lambda e: e["date"], reverse=True)

def _get_week_range(week_offset: int = 0) -> tuple[date, date]:
    """Return (monday, sunday) for the given week offset."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    monday = monday - timedelta(weeks=week_offset)
    sunday = monday + timedelta(days=6)
    return monday, sunday

def _parse_date(value: str) -> date | None:
    """Parse an ISO date string, returning None if malformed.

    Mirrors the try/except tolerance already used in get_insights' day_exp loop:
    a single malformed entry in the daily log must not crash reports/reminders.
    """
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None

def _parse_datetime_date(value: str) -> date | None:
    """Parse an ISO datetime/date string, returning the date part or None if malformed.

    Used for fields like player.createdAt which are stored as full datetime strings;
    falls back to None so callers can apply a sensible default.
    """
    try:
        return datetime.fromisoformat(value).date()
    except (ValueError, TypeError):
        return None

def _filter_week(daily_log: list[dict], week_start: date, week_end: date) -> list[dict]:
    result = []
    for e in daily_log:
        d = _parse_date(e.get("date", ""))
        if d is not None and week_start <= d <= week_end:
            result.append(e)
    return result

def _filter_days(daily_log: list[dict], days: int) -> list[dict]:
    cutoff = date.today() - timedelta(days=days)
    result = []
    for e in daily_log:
        d = _parse_date(e.get("date", ""))
        if d is not None and d >= cutoff:
            result.append(e)
    return result

def _actions_by_type(entries: list[dict]) -> dict[str, int]:
    result: dict[str, int] = {}
    for e in entries:
        for a in e.get("actions", []):
            t = a["type"]
            result[t] = result.get(t, 0) + a["quantity"]
    return result

def _latest_activity_date(daily_log: list[dict]) -> date | None:
    """Return the date of the most recent parseable daily-log entry, or None.

    Selects by parsed date rather than by raw string: a malformed entry that
    happens to sort high lexically (e.g. "not-a-date") must not be mistaken for
    the latest activity and suppress idle detection.
    """
    latest: date | None = None
    for e in daily_log:
        d = _parse_date(e.get("date", ""))
        if d is not None and (latest is None or d > latest):
            latest = d
    return latest

def get_weekly_report(player: dict, week_offset: int = 0) -> dict:
    """Generate a weekly report."""
    monday, sunday = _get_week_range(week_offset)
    daily_log = player.get("dailyLog", [])
    week_entries = _filter_week(daily_log, monday, sunday)
    total_exp = sum(e.get("totalExp", 0) for e in week_entries)
    total_gold = sum(e.get("totalGold", 0) for e in week_entries)
    best_entry = max(week_entries, key=lambda e: e.get("totalExp", 0)) if week_entries else None
    if best_entry is not None:
        best_parsed = _parse_date(best_entry["date"])
        # Normalize to ISO form so best_day stays consistent with the daily_data
        # keys even when the log stores non-canonical dates (e.g. "20260824").
        best_day = best_parsed.isoformat() if best_parsed else best_entry["date"]
    else:
        best_day = None
    daily_data: list[tuple[str, int]] = []
    for i in range(7):
        d = monday + timedelta(days=i)
        ds = d.isoformat()
        # Match by parsed date, not raw string, so any date form that
        # _filter_week accepted maps to its correct weekday slot.
        val = next((e.get("totalExp", 0) for e in week_entries if _parse_date(e["date"]) == d), 0)
        daily_data.append((ds, val))
    prev_mon, prev_sun = _get_week_range(week_offset + 1)
    prev_entries = _filter_week(daily_log, prev_mon, prev_sun)
    prev_exp = sum(e.get("totalExp", 0) for e in prev_entries)
    if prev_exp > 0:
        ratio = total_exp / prev_exp
        trend = "up" if ratio > 1.1 else ("down" if ratio < 0.9 else "stable")
    else:
        trend = "up" if total_exp > 0 else "stable"
    missing = [monday + timedelta(days=i) for i in range(7)
               if not any(_parse_date(e["date"]) == (monday + timedelta(days=i)) for e in week_entries)]
    active_days = len(week_entries)
    avg = total_exp / active_days if active_days else 0
    return {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "days_active": active_days,
        "days_total": 7,
        "total_exp": total_exp,
        "total_gold": total_gold,
        "actions_by_type": _actions_by_type(week_entries),
        "best_day": best_day,
        "daily_data": daily_data,
        "trend": trend,
        "avg_daily_exp": round(avg, 1),
        "missing_days": [d.isoformat() for d in missing],
    }

def get_monthly_report(player: dict, month_offset: int = 0) -> dict:
    """Generate a monthly report."""
    today = date.today()
    m = today.month - month_offset
    y = today.year
    while m < 1:
        m += 12
        y -= 1
    month_str = f"{y}-{m:02d}"
    days_in = (date(y, m % 12 + 1, 1) if m < 12 else date(y + 1, 1, 1)) - date(y, m, 1)
    days_in_month = days_in.days
    daily_log = player.get("dailyLog", [])
    entries = [e for e in daily_log
               if (d := _parse_date(e.get("date", ""))) is not None and d.strftime("%Y-%m") == month_str]
    total_exp = sum(e.get("totalExp", 0) for e in entries)
    total_gold = sum(e.get("totalGold", 0) for e in entries)
    best_entry = max(entries, key=lambda e: e.get("totalExp", 0)) if entries else None
    worst_entry = min(entries, key=lambda e: e.get("totalExp", 0)) if entries else None
    # Normalize to ISO form so best_day/worst_day stay consistent with the
    # weekly report even when the log stores non-canonical dates.
    best_day = _parse_date(best_entry["date"]).isoformat() if best_entry else None
    worst_day = _parse_date(worst_entry["date"]).isoformat() if worst_entry else None
    first_day = date(y, m, 1)
    weekly_trend: list[int] = []
    cur = first_day
    while cur.month == m or (cur == first_day and cur.day <= days_in_month):
        w_start = cur
        w_end = min(cur + timedelta(days=6), date(y, m, days_in_month))
        w_entries = _filter_week(entries, w_start, w_end)
        weekly_trend.append(sum(e.get("totalExp", 0) for e in w_entries))
        cur = w_end + timedelta(days=1)
        if cur.month != m:
            break
    active = len(entries)
    avg = total_exp / active if active else 0
    return {
        "month": month_str,
        "days_active": active,
        "days_in_month": days_in_month,
        "total_exp": total_exp,
        "total_gold": total_gold,
        "actions_by_type": _actions_by_type(entries),
        "best_day": best_day,
        "worst_day": worst_day,
        "weekly_trend": weekly_trend,
        "avg_daily_exp": round(avg, 1),
    }

def get_type_breakdown(player: dict, days: int = 30) -> dict:
    """Break down activity by type over the last N days."""
    daily_log = player.get("dailyLog", [])
    entries = _filter_days(daily_log, days)
    type_map: dict[str, dict[str, Any]] = {}
    for e in entries:
        for a in e.get("actions", []):
            t = a["type"]
            if t not in type_map:
                type_map[t] = {"total_quantity": 0, "total_exp": 0, "days": set()}
            type_map[t]["total_quantity"] += a["quantity"]
            type_map[t]["total_exp"] += a["exp"]
            # Dedup by parsed date (ISO form) so the same actual day stored in
            # alternate forms (e.g. "20260824" vs "2026-08-24") counts once.
            type_map[t]["days"].add(_parse_date(e["date"]).isoformat())
    types = []
    for t, v in type_map.items():
        da = len(v["days"])
        types.append({
            "type": t,
            "total_quantity": v["total_quantity"],
            "total_exp": v["total_exp"],
            "days_active": da,
            "avg_per_day": round(v["total_quantity"] / da, 1) if da else 0,
        })
    types.sort(key=lambda x: x["total_exp"], reverse=True)
    most = types[0]["type"] if types else ""
    least = types[-1]["type"] if types else ""
    return {"types": types, "most_active_type": most, "least_active_type": least}

def get_streak_history(player: dict) -> dict:
    """Analyze streak data from daily log."""
    daily_log = player.get("dailyLog", [])
    best_streak = 0
    best_streak_date = ""
    for e in daily_log:
        s = e.get("streak", 0)
        if s > best_streak:
            best_streak = s
            parsed = _parse_date(e.get("date", ""))
            # Normalize to ISO form; fall back to the raw value if unparseable.
            best_streak_date = parsed.isoformat() if parsed else e.get("date", "")
    created = _parse_datetime_date(player.get("createdAt", date.today().isoformat()))
    if created is None:
        # Malformed createdAt (corrupted state) — fall back to today so the
        # report still renders instead of crashing.
        created = date.today()
    # Clamp to >= 1: a future-dated createdAt (clock skew / bad import) must not
    # yield a negative days_since and a nonsensical completion_rate.
    days_since = max(1, (date.today() - created).days + 1)
    active_days = len(daily_log)
    rate = round(active_days / days_since * 100, 1) if days_since else 0
    return {
        "current_streak": player.get("streak", 0),
        "best_streak": best_streak,
        "best_streak_date": best_streak_date,
        "days_since_created": days_since,
        "active_days": active_days,
        "completion_rate": rate,
    }

def get_insights(player: dict) -> list[str]:
    """Generate personalized insights based on activity patterns."""
    insights: list[str] = []
    daily_log = player.get("dailyLog", [])
    cur_mon, cur_sun = _get_week_range(0)
    prev_mon, prev_sun = _get_week_range(1)
    cur_entries = _filter_week(daily_log, cur_mon, cur_sun)
    prev_entries = _filter_week(daily_log, prev_mon, prev_sun)
    cur_types = _actions_by_type(cur_entries)
    prev_types = _actions_by_type(prev_entries)
    all_types = set(list(cur_types.keys()) + list(prev_types.keys()))
    for t in all_types:
        c = cur_types.get(t, 0)
        p = prev_types.get(t, 0)
        if p > 0 and c > p:
            pct = round((c - p) / p * 100)
            insights.append(f"本周{t}活动比上周增加了 {pct}% -- 继续保持！")
        elif p > 0 and c < p:
            pct = round((p - c) / p * 100)
            insights.append(f"本周{t}活动比上周减少了 {pct}%，注意保持节奏")
        elif p == 0 and c > 0:
            insights.append(f"本周开始进行{t}活动，不错的新增习惯！")
    last7 = _filter_days(daily_log, 7)
    recent_types = set()
    for e in last7:
        for a in e.get("actions", []):
            recent_types.add(a["type"])
    all_known = set()
    for e in daily_log:
        for a in e.get("actions", []):
            all_known.add(a["type"])
    for t in all_known - recent_types:
        insights.append(f"你已连续 7 天未记录{t}活动，考虑添加{t}任务")
    day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    day_exp: list[int] = [0] * 7
    for e in daily_log:
        d = _parse_date(e.get("date", ""))
        if d is not None:
            day_exp[d.weekday()] += e.get("totalExp", 0)
    if any(day_exp):
        best_d = day_names[day_exp.index(max(day_exp))]
        insights.append(f"你的最佳活动日是{best_d}，尝试在{best_d}安排重要任务")
    last_date = _latest_activity_date(daily_log)
    if last_date is not None:
        idle = (date.today() - last_date).days
        if idle >= 2:
            insights.append(f"距离上次活动已过去 {idle} 天，记得回来打卡！")
    cur_total = sum(cur_types.values())
    if cur_total > 0:
        for t, qty in cur_types.items():
            if qty / cur_total >= 0.8:
                insights.append(f"本周 {t} 数量占所有活动的 {round(qty/cur_total*100)}%，可以尝试多样化你的活动类型")
                break
    return insights

def get_smart_reminders(player: dict) -> list[str]:
    """Generate actionable reminders for the player's recent behavior."""
    reminders: list[str] = []
    daily_log = player.get("dailyLog", [])
    if not daily_log:
        return ["先完成一次打卡，系统会根据你的习惯生成更精准的提醒"]

    last_date = _latest_activity_date(daily_log)
    if last_date is not None:
        idle_days = (date.today() - last_date).days
        if idle_days >= 1:
            reminders.append(f"你已经 {idle_days} 天没有记录活动了，建议先补一次最容易完成的任务")
        if idle_days >= 3:
            reminders.append("当前间隔偏长，今天优先完成一个低门槛任务，先把节奏拉回来")

    recent_7d = _filter_days(daily_log, 7)
    recent_types = set()
    for e in recent_7d:
        for a in e.get("actions", []):
            recent_types.add(a["type"])

    all_known = set()
    for e in daily_log:
        for a in e.get("actions", []):
            all_known.add(a["type"])

    missing_types = sorted(all_known - recent_types)
    if missing_types:
        reminders.append(f"最近 7 天没有记录这些类型：{', '.join(missing_types[:3])}，可以安排一次补全")

    cur_mon, _ = _get_week_range(0)
    week_entries = _filter_week(daily_log, cur_mon, cur_mon + timedelta(days=6))
    week_types = _actions_by_type(week_entries)
    if week_types:
        top_type, top_qty = max(week_types.items(), key=lambda x: x[1])
        total_qty = sum(week_types.values())
        if total_qty > 0 and top_qty / total_qty >= 0.8:
            reminders.append(f"本周 {top_type} 占比过高，建议加入其他类型任务，避免训练内容单一")

    if not reminders:
        reminders.append("保持当前节奏即可，继续稳定打卡会带来更好的成长曲线")
    return reminders


def format_ascii_chart(data: list[tuple[str, int]], title: str = "", max_bar_width: int = 40) -> str:
    """Render ASCII horizontal bar chart."""
    if not data:
        lines = [f"  {title}" if title else ""]
        lines.append("  (无数据)")
        return "\n".join(lines)
    max_val = max(v for _, v in data) if max(v for _, v in data) > 0 else 1
    label_w = max(len(str(l)) for l, _ in data)
    lines = [f"  {title}"] if title else []
    for label, val in data:
        bar_len = round(val / max_val * max_bar_width) if max_val > 0 else 0
        filled = "\u2588" * bar_len
        empty = "\u2591" * (max_bar_width - bar_len)
        lines.append(f"  {label:>{label_w}} {filled}{empty} {val}")
    return "\n".join(lines)

def format_weekly_report(player: dict, week_offset: int = 0) -> str:
    """Generate a formatted ASCII report string for CLI display."""
    r = get_weekly_report(player, week_offset)
    monday = date.fromisoformat(r["week_start"])
    sunday = date.fromisoformat(r["week_end"])
    iso_week = monday.isocalendar()[1]
    daily_log = player.get("dailyLog", [])
    week_entries = _filter_week(daily_log, monday, sunday)
    sep = "\u2550" * 42
    lines = [sep]
    lines.append(f"  \U0001f4ca 周报 - {monday.year}-W{iso_week:02d} ({monday.strftime('%m/%d')}-{sunday.strftime('%m/%d')})")
    lines.append(sep)
    lines.append(f"  活跃天数: {r['days_active']}/{r['days_total']}")
    lines.append(f"  获得经验: {r['total_exp']:,} EXP")
    lines.append(f"  获得金币: {r['total_gold']:,} G")
    lines.append(f"  日均EXP: {r['avg_daily_exp']} EXP")
    trend_symbols = {"up": "\U0001f4c8 上升", "down": "\U0001f4c9 下降", "stable": "\u2500\u2500 稳定"}
    trend_str = trend_symbols.get(r["trend"], r["trend"])
    if r["trend"] != "stable":
        prev_mon, prev_sun = _get_week_range(week_offset + 1)
        prev_exp = sum(e.get("totalExp", 0) for e in _filter_week(daily_log, prev_mon, prev_sun))
        if prev_exp > 0:
            pct = round((r["total_exp"] - prev_exp) / prev_exp * 100)
            trend_str += f" (比上周 {'+' if pct >= 0 else ''}{pct}%)"
    lines.append(f"  趋势: {trend_str}")
    lines.append("\u2500" * 37)
    if r["actions_by_type"]:
        for t, qty in sorted(r["actions_by_type"].items(), key=lambda x: x[1], reverse=True):
            te = sum(a["exp"] for e in week_entries for a in e.get("actions", []) if a["type"] == t)
            # Dedup by parsed date so the same day stored in alternate forms
            # (e.g. ISO vs compact) counts once, matching get_type_breakdown.
            dt = len({_parse_date(e["date"]).isoformat()
                      for e in week_entries for a in e.get("actions", []) if a["type"] == t})
            lines.append(f"  {t}:  {te} EXP ({dt} 天)")
        lines.append("\u2500" * 37)
    chart_data = [(date.fromisoformat(ds).strftime("%a"), val) for ds, val in r["daily_data"]]
    lines.append(format_ascii_chart(chart_data, "  每日EXP"))
    lines.append(sep)
    return "\n".join(lines)
