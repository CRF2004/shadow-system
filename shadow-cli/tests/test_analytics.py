"""Tests for analytics module."""

from datetime import date, timedelta

from analytics import (
    log_daily_activity, get_daily_log,
    get_weekly_report, get_monthly_report,
    get_type_breakdown, get_streak_history, get_insights,
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
