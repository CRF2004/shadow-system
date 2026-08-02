"""
Shadow CLI - Configuration and Constants
"""

import os
from pathlib import Path

# Paths
STATE_DIR = Path.home() / ".claude" / "shadow-state"
PLAYER_FILE = STATE_DIR / "player.json"
QUESTS_DIR = STATE_DIR / "quests"
SOLDIERS_DIR = STATE_DIR / "soldiers"
LOGS_DIR = STATE_DIR / "logs"
INTEGRATIONS_DIR = STATE_DIR / "integrations"

# Core constants
VERSION = "0.9.2"
BASE_EXP = 100
EXP_MULTIPLIER = 1.5
STAT_POINTS_PER_LEVEL = 3
MAX_HP = 100
MAX_MP = 100

# Rank titles
TITLES = [
    (100, "暗影君主"),
    (70,  "国家级猎人"),
    (50,  "S 级猎人"),
    (40,  "A 级猎人"),
    (30,  "B 级猎人"),
    (20,  "C 级猎人"),
    (10,  "D 级猎人"),
    (1,   "E 级猎人"),
]

# Stat display names
STAT_NAMES_CN = {
    "str": "力量",
    "agi": "敏捷",
    "sen": "感知",
    "vit": "体力",
    "int": "智力",
}

STAT_FULL_NAMES = {
    "str": "strength",
    "agi": "agility",
    "sen": "sense",
    "vit": "vitality",
    "int": "intelligence",
}

# EXP rewards
EXP_REWARDS = {
    "commit": 50,
    "coding_line": 0.1,       # per line (100 lines = 10 EXP)
    "coding_100": 10,         # per 100 lines
    "vocabulary": 1,          # per word
    "exercise_minute": 2,     # per minute
    "reading_page": 1,        # per page
    "daily_complete": 100,
    "streak_bonus_pct": 0.10, # 10% per streak day
    "combo_pct": 0.10,        # 10% per combo
}

# Daily tasks (4 fixed)
DAILY_TASKS = [
    {"id": "commit",   "name": "提交一次代码",       "type": "commit",  "target": 1, "reward": 50, "difficulty": "D"},
    {"id": "debug",    "name": "修复一个 Bug",        "type": "commit",  "target": 1, "reward": 50, "difficulty": "D"},
    {"id": "learn",    "name": "学习一个新概念",      "type": "reading", "target": 1, "reward": 50, "difficulty": "D"},
    {"id": "code",     "name": "专注编码 30 分钟",    "type": "coding",  "target": 30,"reward": 60, "difficulty": "D"},
]

# Emergency task pool (random urgent tasks)
EMERGENCY_TASKS = [
    {"id": "emergency_refactor", "name": "重构一个模块",       "type": "coding", "target": 50,  "reward": 80,  "difficulty": "C"},
    {"id": "emergency_doc",      "name": "写一份文档",         "type": "reading", "target": 3, "reward": 40,  "difficulty": "D"},
    {"id": "emergency_test",     "name": "补充单元测试",       "type": "coding", "target": 30,  "reward": 70,  "difficulty": "C"},
    {"id": "emergency_review",   "name": "审查一段代码",       "type": "reading", "target": 2, "reward": 30,  "difficulty": "D"},
    {"id": "emergency_vocab",    "name": "背 50 个单词",       "type": "vocabulary", "target": 50, "reward": 50, "difficulty": "C"},
    {"id": "emergency_exercise", "name": "运动 30 分钟",       "type": "exercise", "target": 30, "reward": 60,  "difficulty": "C"},
]

# Difficulty multipliers
DIFFICULTY_MULTIPLIER = {
    "E": 0.5,
    "D": 1.0,
    "C": 1.5,
    "B": 2.0,
    "A": 3.0,
    "S": 5.0,
}

# Combat power weights
POWER_WEIGHTS = {
    "stats": 1,
    "level": 10,
    "soldier": 5,
}

# ── Soldier System ──────────────────────────────────────────────────────

SOLDIER_TYPES = [
    {"type": "explore", "name": "🔍 虚空行者", "mp_cost": 30, "specialty": "代码库探索/架构分析"},
    {"type": "plan",    "name": "🧭 战略家",   "mp_cost": 25, "specialty": "任务规划/方案设计"},
    {"type": "dev",     "name": "🔨 构造者",   "mp_cost": 35, "specialty": "功能开发/代码实现"},
    {"type": "test",    "name": "🧪 试炼官",   "mp_cost": 25, "specialty": "测试编写/Bug 复现"},
    {"type": "debug",   "name": "🩺 诊断师",   "mp_cost": 30, "specialty": "问题诊断/性能优化"},
    {"type": "review",  "name": "⚖️ 审判者",   "mp_cost": 20, "specialty": "代码审查/安全检测"},
    {"type": "doc",     "name": "📝 书记官",   "mp_cost": 15, "specialty": "文档编写/注释生成"},
]

SOLDIER_DROP_CHANCE = 0.10  # 10% chance per summon

LEGION_SCALES = {
    "small":  {"name": "小型部队 (3 人)", "mp": 100, "count": 3},
    "medium": {"name": "中型军团 (5 人)", "mp": 180, "count": 5},
    "large":  {"name": "大型远征军 (7 人)", "mp": 250, "count": 7},
    "full":   {"name": "全盛暗影大军 (12+)", "mp": 400, "count": 12},
}

# ── Integration System ────────────────────────────────────────────────────

# Health data EXP conversion rates
HEALTH_EXP = {
    "steps_per_exp": 100,         # 100 steps = 1 EXP
    "exercise_minute_exp": 2,      # 1 min exercise = 2 EXP
    "sleep_hour_exp": 5,           # 1 hour sleep = 5 EXP
    "daily_health_cap": 200,       # Max EXP per day from health
}

# Reading data EXP conversion rates
READING_EXP = {
    "minute_exp": 1,               # 1 min reading = 1 EXP
    "page_exp": 1,                 # 1 page = 1 EXP
    "daily_reading_cap": 150,      # Max EXP per day from reading
}

# Browser activity EXP conversion rates
BROWSER_EXP = {
    "study_minute_exp": 2,         # 1 min study = 2 EXP
    "daily_browser_cap": 100,      # Max EXP per day from browser
}

# Integration types
INTEGRATION_TYPES = ["health", "reading", "browser"]

# ── Achievement System ──────────────────────────────────────────────────

ACHIEVEMENTS = [
    {
        "id": "hello_world",
        "name": "Hello World",
        "description": "首次完成任务",
        "condition_type": "total_exp",
        "condition_value": 1,
        "reward_exp": 20,
        "reward_gold": 10,
    },
    {
        "id": "first_level",
        "name": "初露锋芒",
        "description": "达到 LV.5",
        "condition_type": "level",
        "condition_value": 5,
        "reward_exp": 100,
        "reward_gold": 50,
    },
    {
        "id": "bug_killer",
        "name": "Bug 杀手",
        "description": "累计 10 次 commit",
        "condition_type": "commit_count",
        "condition_value": 10,
        "reward_exp": 200,
        "reward_gold": 100,
    },
    {
        "id": "perfect_build",
        "name": "完美构建",
        "description": "连续 7 天打卡 (streak 7)",
        "condition_type": "streak",
        "condition_value": 7,
        "reward_exp": 300,
        "reward_gold": 150,
    },
    {
        "id": "multithread_god",
        "name": "多线程之神",
        "description": "获得 5 名士兵",
        "condition_type": "soldier_count",
        "condition_value": 5,
        "reward_exp": 500,
        "reward_gold": 200,
    },
    {
        "id": "code_doctor",
        "name": "代码医生",
        "description": "总经验达到 5000",
        "condition_type": "total_exp",
        "condition_value": 5000,
        "reward_exp": 1000,
        "reward_gold": 500,
    },
    {
        "id": "shadow_monarch",
        "name": "暗影君主",
        "description": "达到 LV.100",
        "condition_type": "level",
        "condition_value": 100,
        "reward_exp": 10000,
        "reward_gold": 5000,
    },
    # ── Boss Achievements ──────────────────────────────────
    {
        "id": "first_boss",
        "name": "首杀",
        "description": "首次击败 Boss",
        "condition_type": "bosses_defeated",
        "condition_value": 1,
        "reward_exp": 200,
        "reward_gold": 100,
    },
    {
        "id": "boss_hunter",
        "name": "Boss 猎人",
        "description": "击败 10 个 Boss",
        "condition_type": "bosses_defeated",
        "condition_value": 10,
        "reward_exp": 1000,
        "reward_gold": 500,
    },
    {
        "id": "boss_slayer",
        "name": "Boss 屠夫",
        "description": "击败 50 个 Boss",
        "condition_type": "bosses_defeated",
        "condition_value": 50,
        "reward_exp": 5000,
        "reward_gold": 2000,
    },
    # ── Guild Achievements ─────────────────────────────────
    {
        "id": "guild_member",
        "name": "公会新人",
        "description": "加入公会",
        "condition_type": "guild_joined",
        "condition_value": 1,
        "reward_exp": 100,
        "reward_gold": 50,
    },
    {
        "id": "guild_leader",
        "name": "公会领袖",
        "description": "创建公会",
        "condition_type": "guild_created",
        "condition_value": 1,
        "reward_exp": 200,
        "reward_gold": 100,
    },
    {
        "id": "guild_task_done",
        "name": "团队贡献者",
        "description": "完成 5 次公会任务",
        "condition_type": "guild_tasks_completed",
        "condition_value": 5,
        "reward_exp": 500,
        "reward_gold": 250,
    },
    {
        "id": "guild_boss_victory",
        "name": "公会英雄",
        "description": "击败 3 个公会 Boss",
        "condition_type": "guild_bosses_defeated",
        "condition_value": 3,
        "reward_exp": 1000,
        "reward_gold": 500,
    },
    # ── Milestone Achievements ─────────────────────────────
    {
        "id": "century_commit",
        "name": "百次提交",
        "description": "累计 100 次 commit",
        "condition_type": "commit_count",
        "condition_value": 100,
        "reward_exp": 1500,
        "reward_gold": 750,
    },
    {
        "id": "super_streak",
        "name": "百日筑基",
        "description": "连续打卡 100 天",
        "condition_type": "streak",
        "condition_value": 100,
        "reward_exp": 3000,
        "reward_gold": 1500,
    },
    {
        "id": "soldier_army",
        "name": "暗影大军",
        "description": "获得 20 名士兵",
        "condition_type": "soldier_count",
        "condition_value": 20,
        "reward_exp": 2000,
        "reward_gold": 1000,
    },
    {
        "id": "wealthy",
        "name": "暴富",
        "description": "累计获得 10000 金币",
        "condition_type": "total_gold",
        "condition_value": 10000,
        "reward_exp": 1000,
        "reward_gold": 500,
    },
    {
        "id": "ten_thousand_exp",
        "name": "万世传承",
        "description": "总经验达到 10000",
        "condition_type": "total_exp",
        "condition_value": 10000,
        "reward_exp": 2000,
        "reward_gold": 1000,
    },
    {
        "id": "lv_50",
        "name": "半百之境",
        "description": "达到 LV.50",
        "condition_type": "level",
        "condition_value": 50,
        "reward_exp": 3000,
        "reward_gold": 1500,
    },
    {
        "id": "lv_75",
        "name": "七十五重天",
        "description": "达到 LV.75",
        "condition_type": "level",
        "condition_value": 75,
        "reward_exp": 5000,
        "reward_gold": 2500,
    },
    # ── Legend Achievements ──────────────────────────────────
    {
        "id": "boss_legend",
        "name": "Boss 传说",
        "description": "击败 100 个 Boss",
        "condition_type": "bosses_defeated",
        "condition_value": 100,
        "reward_exp": 10000,
        "reward_gold": 5000,
    },
    {
        "id": "mega_streak",
        "name": "周年修炼",
        "description": "连续打卡 365 天",
        "condition_type": "streak",
        "condition_value": 365,
        "reward_exp": 10000,
        "reward_gold": 5000,
    },
    {
        "id": "soldier_king",
        "name": "暗影之王",
        "description": "获得 50 名士兵",
        "condition_type": "soldier_count",
        "condition_value": 50,
        "reward_exp": 5000,
        "reward_gold": 2500,
    },
]
