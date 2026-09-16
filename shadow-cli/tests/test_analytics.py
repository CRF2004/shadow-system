"""Tests for analytics module."""

import os
import sys
from datetime import date, timedelta

# Add shadow-cli to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analytics import (
    log_daily_activity, get_daily_log,
    get_weekly_report, get_monthly_report,
    get_type_breakdown, get_streak_history, get_insights, get_smart_reminders,
    format_ascii_chart, format_weekly_report,
)
from state import create_default_player


class TestLogDailyActivity:
    def test_log_creates_entry(self):
        player = create_default_player()
        log_daily_activity(player, "2026-05-09", "commit", 3, 150, 10)
        assert len(player["dailyLog"]) == 1
        entry = player["dailyLog"][0]
        assert entry["date"] == "2026-05-09"
        assert entry["totalExp"] == 150
        assert entry["totalGold"] == 10
        assert entry["actions"][0]["type"] == "commit"
        assert entry["actions"][0]["quantity"] == 3

    def test_log_appends_to_existing(self):
        player = create_default_player()
        log_daily_activity(player, "2026-05-09", "commit", 3, 150, 10)
        log_daily_activity(player, "2026-05-09", "coding", 500, 50, 0)
        assert len(player["dailyLog"]) == 1
        assert len(player["dailyLog"][0]["actions"]) == 2
        assert player["dailyLog"][0]["totalExp"] == 200

    def test_log_multiple_days(self):
        player = create_default_player()
        log_daily_activity(player, "2026-05-09", "commit", 1, 50, 0)
        log_daily_activity(player, "2026-05-08", "coding", 100, 10, 0)
        assert len(player["dailyLog"]) == 2


class TestGetDailyLog:
    def test_newest_first(self):
        player = create_default_player()
        log_daily_activity(player, "2026-05-07", "commit", 1, 50, 0)
        log_daily_activity(player, "2026-05-09", "commit", 3, 150, 0)
        log_daily_activity(player, "2026-05-08", "coding", 100, 10, 0)
        log = get_daily_log(player)
        assert log[0]["date"] == "2026-05-09"
        assert log[1]["date"] == "2026-05-08"
        assert log[2]["date"] == "2026-05-07"

    def test_empty_log(self):
        player = create_default_player()
        assert get_daily_log(player) == []


class TestWeeklyReport:
    def test_empty_week(self):
        player = create_default_player()
        report = get_weekly_report(player)
        assert report["total_exp"] == 0
        assert report["days_active"] == 0
        assert report["trend"] == "stable"

    def test_report_with_data(self):
        player = create_default_player()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        log_daily_activity(player, monday.isoformat(), "commit", 3, 150, 10)
        log_daily_activity(player, monday.isoformat(), "coding", 500, 50, 0)

        report = get_weekly_report(player)
        assert report["total_exp"] == 200
        assert report["days_active"] == 1
        assert report["total_gold"] == 10

    def test_trend_up(self):
        player = create_default_player()
        today = date.today()
        monday_cur = today - timedelta(days=today.weekday())
        monday_prev = monday_cur - timedelta(weeks=1)

        log_daily_activity(player, monday_prev.isoformat(), "commit", 1, 50, 0)
        log_daily_activity(player, monday_cur.isoformat(), "commit", 5, 250, 0)

        report = get_weekly_report(player)
        assert report["trend"] == "up"

    def test_trend_down(self):
        player = create_default_player()
        today = date.today()
        monday_cur = today - timedelta(days=today.weekday())
        monday_prev = monday_cur - timedelta(weeks=1)

        log_daily_activity(player, monday_prev.isoformat(), "commit", 5, 250, 0)
        log_daily_activity(player, monday_cur.isoformat(), "commit", 1, 50, 0)

        report = get_weekly_report(player)
        assert report["trend"] == "down"

    def test_missing_days(self):
        player = create_default_player()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        log_daily_activity(player, monday.isoformat(), "commit", 1, 50, 0)

        report = get_weekly_report(player)
        assert len(report["missing_days"]) == 6

    def test_noncanonical_date_maps_to_weekday(self):
        """A log date stored in non-canonical form (e.g. compact YYYYMMDD) must
        still map to its weekday slot: counted in daily_data, excluded from
        missing_days, and best_day normalized to ISO form."""
        player = create_default_player()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        log_daily_activity(player, monday.isoformat(), "commit", 1, 50, 0)
        # Rewrite the stored date to compact form to simulate alternate-format data.
        player["dailyLog"][0]["date"] = monday.strftime("%Y%m%d")

        report = get_weekly_report(player)
        assert report["days_active"] == 1
        assert report["total_exp"] == 50
        # Monday is daily_data index 0.
        assert report["daily_data"][0][1] == 50
        assert monday.isoformat() not in report["missing_days"]
        assert report["best_day"] == monday.isoformat()


class TestMonthlyReport:
    def test_empty_month(self):
        player = create_default_player()
        report = get_monthly_report(player)
        assert report["total_exp"] == 0
        assert report["days_active"] == 0

    def test_month_with_data(self):
        player = create_default_player()
        today = date.today()
        month_str = today.strftime("%Y-%m")
        log_daily_activity(player, today.isoformat(), "commit", 2, 100, 0)

        report = get_monthly_report(player)
        assert report["month"] == month_str
        assert report["total_exp"] == 100
        assert report["days_active"] == 1

    def test_tolerates_malformed_date(self):
        """Malformed/missing dates in the log must not crash the monthly report."""
        player = create_default_player()
        log_daily_activity(player, date.today().isoformat(), "commit", 1, 50, 0)
        player["dailyLog"].append({"date": None, "actions": [], "totalExp": 10, "totalGold": 0})
        player["dailyLog"].append({"actions": [], "totalExp": 20, "totalGold": 0})  # missing date key

        report = get_monthly_report(player)
        assert report["total_exp"] == 50
        assert report["days_active"] == 1

    def test_best_worst_day_normalized_to_iso(self):
        """best_day/worst_day must be normalized to ISO form even when the log
        stores non-canonical dates, matching the weekly report's best_day."""
        player = create_default_player()
        today = date.today()
        log_daily_activity(player, today.isoformat(), "commit", 1, 50, 0)
        # Rewrite the stored date to compact form to simulate alternate-format data.
        player["dailyLog"][0]["date"] = today.strftime("%Y%m%d")

        report = get_monthly_report(player)
        assert report["days_active"] == 1
        assert report["best_day"] == today.isoformat()
        assert report["worst_day"] == today.isoformat()


class TestTypeBreakdown:
    def test_empty_breakdown(self):
        player = create_default_player()
        result = get_type_breakdown(player)
        assert result["types"] == []
        assert result["most_active_type"] == ""

    def test_breakdown_with_data(self):
        player = create_default_player()
        today = date.today()
        log_daily_activity(player, today.isoformat(), "commit", 5, 250, 0)
        log_daily_activity(player, today.isoformat(), "coding", 100, 10, 0)

        result = get_type_breakdown(player)
        assert len(result["types"]) == 2
        # commit=250 EXP > coding=10 EXP
        assert result["most_active_type"] == "commit"

    def test_noncanonical_dates_count_as_one_day(self):
        """The same actual day stored in two forms (e.g. ISO and compact) must be
        counted as a single distinct day in days_active, not two."""
        player = create_default_player()
        today = date.today()
        log_daily_activity(player, today.isoformat(), "commit", 1, 50, 0)
        # Same day, compact form.
        player["dailyLog"].append({"date": today.strftime("%Y%m%d"),
                                   "actions": [{"type": "commit", "quantity": 1, "exp": 50}],
                                   "totalExp": 50, "totalGold": 0, "streak": 0, "level": 1})

        result = get_type_breakdown(player)
        commit = next(t for t in result["types"] if t["type"] == "commit")
        assert commit["days_active"] == 1
        assert commit["avg_per_day"] == 2.0


class TestStreakHistory:
    def test_empty_streak(self):
        player = create_default_player()
        result = get_streak_history(player)
        assert result["current_streak"] == 0
        assert result["best_streak"] == 0
        assert result["active_days"] == 0

    def test_with_streak_data(self):
        player = create_default_player()
        player["streak"] = 5
        today = date.today()
        log_daily_activity(player, today.isoformat(), "commit", 1, 50, 0)

        result = get_streak_history(player)
        assert result["current_streak"] == 5
        assert result["active_days"] == 1
        assert result["completion_rate"] > 0

    def test_tolerates_malformed_created_at(self):
        """A malformed createdAt (corrupted state) must not crash streak history."""
        player = create_default_player()
        player["createdAt"] = "not-a-valid-date"
        result = get_streak_history(player)
        assert result["current_streak"] == 0
        assert result["days_since_created"] >= 1

    def test_future_created_at_clamped(self):
        """A future-dated createdAt (clock skew / bad import) must not yield a
        negative days_since or completion_rate."""
        player = create_default_player()
        player["createdAt"] = (date.today() + timedelta(days=30)).isoformat()
        log_daily_activity(player, date.today().isoformat(), "commit", 1, 50, 0)
        result = get_streak_history(player)
        assert result["days_since_created"] >= 1
        assert result["completion_rate"] >= 0


class TestInsights:
    def test_no_data_insights(self):
        player = create_default_player()
        insights = get_insights(player)
        assert isinstance(insights, list)

    def test_change_insight(self):
        player = create_default_player()
        today = date.today()
        monday_cur = today - timedelta(days=today.weekday())
        monday_prev = monday_cur - timedelta(weeks=1)

        log_daily_activity(player, monday_prev.isoformat(), "commit", 1, 50, 0)
        log_daily_activity(player, monday_cur.isoformat(), "commit", 5, 250, 0)

        insights = get_insights(player)
        assert any("增加" in i for i in insights)

    def test_tolerates_malformed_date(self):
        """A single malformed date in the log must not crash insights."""
        player = create_default_player()
        log_daily_activity(player, date.today().isoformat(), "commit", 1, 50, 0)
        player["dailyLog"].append({"date": "not-a-date", "actions": [], "totalExp": 0, "totalGold": 0})
        insights = get_insights(player)
        assert isinstance(insights, list)

    def test_idle_insight_not_suppressed_by_malformed_entry(self):
        """A malformed entry that sorts high lexically must not hide the idle
        insight — 'last activity' is chosen by parsed date, not raw string."""
        player = create_default_player()
        log_daily_activity(player, (date.today() - timedelta(days=5)).isoformat(), "commit", 1, 50, 0)
        # Sorts above any ISO date when compared as raw strings.
        player["dailyLog"].append({"date": "zzz", "actions": [], "totalExp": 0, "totalGold": 0})
        insights = get_insights(player)
        assert any("距离上次活动已过去" in i for i in insights)


class TestSmartReminders:
    def test_no_data_reminder(self):
        player = create_default_player()
        reminders = get_smart_reminders(player)
        assert reminders
        assert any("打卡" in r for r in reminders)

    def test_idle_reminder(self):
        player = create_default_player()
        log_daily_activity(player, (date.today() - timedelta(days=4)).isoformat(), "commit", 1, 50, 0)
        reminders = get_smart_reminders(player)
        assert any("没有记录活动" in r or "低门槛" in r for r in reminders)

    def test_idle_reminder_not_suppressed_by_malformed_entry(self):
        """A malformed entry that sorts high lexically must not hide the idle
        reminder — the 'last activity' is chosen by parsed date, not raw string."""
        player = create_default_player()
        log_daily_activity(player, (date.today() - timedelta(days=4)).isoformat(), "commit", 1, 50, 0)
        # Sorts above any ISO date when compared as raw strings.
        player["dailyLog"].append({"date": "not-a-date", "actions": [], "totalExp": 0, "totalGold": 0})
        reminders = get_smart_reminders(player)
        assert any("没有记录活动" in r or "低门槛" in r for r in reminders)

    def test_missing_type_reminder(self):
        """A type done in the past but not in the last 7 days should be suggested."""
        player = create_default_player()
        log_daily_activity(player, (date.today() - timedelta(days=10)).isoformat(), "reading", 1, 30, 0)
        log_daily_activity(player, (date.today() - timedelta(days=1)).isoformat(), "commit", 1, 50, 0)
        reminders = get_smart_reminders(player)
        assert any("reading" in r for r in reminders)

    def test_diversity_reminder(self):
        """A single type dominating the week should trigger a variety suggestion."""
        player = create_default_player()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        # 5 commit actions, only one type this week
        for i in range(5):
            log_daily_activity(player, (monday + timedelta(days=i)).isoformat(), "commit", 2, 100, 0)
        reminders = get_smart_reminders(player)
        assert any("占比过高" in r for r in reminders)

    def test_fallback_when_recent_balanced_activity(self):
        """Recent, balanced activity with no specific trigger → fallback encouragement."""
        player = create_default_player()
        today = date.today().isoformat()
        log_daily_activity(player, today, "commit", 3, 150, 0)
        log_daily_activity(player, today, "reading", 2, 50, 0)
        reminders = get_smart_reminders(player)
        assert reminders
        assert any("保持当前节奏" in r for r in reminders)

    def test_tolerates_malformed_date(self):
        """A single malformed date in the log must not crash reminders."""
        player = create_default_player()
        log_daily_activity(player, date.today().isoformat(), "commit", 1, 50, 0)
        player["dailyLog"].append({"date": "not-a-date", "actions": [], "totalExp": 0, "totalGold": 0})
        reminders = get_smart_reminders(player)
        assert isinstance(reminders, list)
        assert reminders


class TestFormatAsciiChart:
    def test_empty_chart(self):
        result = format_ascii_chart([], "Title")
        assert "无数据" in result

    def test_chart_with_data(self):
        data = [("Mon", 100), ("Tue", 200), ("Wed", 50)]
        result = format_ascii_chart(data, "Test Chart")
        assert "Test Chart" in result
        assert "█" in result

    def test_chart_all_zeros(self):
        data = [("Mon", 0), ("Tue", 0)]
        result = format_ascii_chart(data)
        assert "░" in result


class TestFormatWeeklyReport:
    def test_empty_report(self):
        player = create_default_player()
        result = format_weekly_report(player)
        assert "周报" in result
        assert "活跃天数" in result

    def test_report_with_data(self):
        player = create_default_player()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        log_daily_activity(player, monday.isoformat(), "commit", 3, 150, 10)

        result = format_weekly_report(player)
        assert "周报" in result
        assert "150" in result

    def test_per_type_day_count_dedups_noncanonical(self):
        """The same actual day stored in two forms must count as one distinct
        day in the per-type 'N 天' display, matching get_type_breakdown."""
        player = create_default_player()
        today = date.today()
        log_daily_activity(player, today.isoformat(), "commit", 1, 50, 0)
        player["dailyLog"].append({"date": today.strftime("%Y%m%d"),
                                   "actions": [{"type": "commit", "quantity": 1, "exp": 50}],
                                   "totalExp": 50, "totalGold": 0, "streak": 0, "level": 1})
        result = format_weekly_report(player)
        assert "(1 天)" in result
        assert "(2 天)" not in result
