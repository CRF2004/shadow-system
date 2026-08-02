#!/usr/bin/env python3
"""
Shadow CLI - 暗影君主系统 v0.4.0
个人成长游戏化工具

Usage:
    python main.py status                    查看角色状态面板
    python main.py record <类型> [数量]       记录行为并获取 EXP
    python main.py daily                     查看/完成每日任务
    python main.py add <属性> <数量>          分配属性点
    python main.py summon [类型]              召唤暗影士兵
    python main.py army                      查看士兵列表
    python main.py legion [规模]              全军出击
    python main.py achievements              查看成就
    python main.py analyze [路径]             深渊凝视: 分析项目
    python main.py plan "[任务描述]"          影之战略: 规划任务
    python main.py monitor                   虚空监控: 实时面板
    python main.py deploy [分钟]              领域展开: 全局诊断
    python main.py archive "[主题]"           记忆固化: 保存经验
    python main.py scan-git [路径]           扫描 Git 提交并获取 EXP
    python main.py setup-git [路径]          安装 Git post-commit hook
    python main.py remove-git [路径]         移除 Git post-commit hook
    python main.py git-status                查看 Git 追踪状态
    python main.py scan-files [路径]         扫描代码文件变更并获取 EXP
    python main.py file-status               查看文件追踪状态
    python main.py dungeons                  查看可用副本
    python main.py enter-dungeon <副本ID>     进入副本
    python main.py boss-list                 查看 Boss 列表
    python main.py shop [类别]               浏览商店
    python main.py buy <商品ID>              购买商品
    python main.py sell <商品ID>             出售物品
    python main.py inventory                 查看背包
    python main.py reset                     重置角色 (危险!)
"""

import argparse
import json
import os
import random
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import VERSION, DAILY_TASKS, STAT_NAMES_CN, STAT_FULL_NAMES, SOLDIER_TYPES, LEGION_SCALES, QUESTS_DIR
import config
from state import load_player, save_player, reset_player
from git_tracker import (
    scan_commits_and_grant,
    install_git_hook,
    uninstall_git_hook,
    get_git_root,
    get_git_status_info,
    github_add_repo,
    github_remove_repo,
    github_list_repos,
    github_scan_and_grant,
)
from file_tracker import (
    scan_files_and_grant,
    save_snapshot,
    get_file_status,
    compare_snapshots,
)
from dungeon import (
    get_available_dungeons,
    generate_dungeon_instance,
    progress_dungeon,
    claim_dungeon_reward,
    get_active_bosses,
    check_boss_defeat,
)
from shop import (
    get_shop_items,
    buy_item,
    sell_item,
    get_inventory,
    SHOP_ITEMS,
)
from engine import (
    add_exp,
    calculate_power,
    get_title,
    allocate_stat,
    get_exp_for_action,
    exp_to_next,
    apply_task_progress,
    claim_daily_reward,
    summon_soldier,
    summon_legion,
    check_achievements,
    get_achievement_status,
)
from integrations import (
    import_health_json, import_health_csv, import_health_export,
    record_health_manual, get_health_summary,
    import_reading_json, import_reading_csv,
    record_reading_manual, get_reading_summary,
    import_browser_data, record_browser_manual, get_browser_summary,
)
from guild import (
    create_guild, disband_guild, join_guild, leave_guild,
    list_guilds, get_guild, get_user_guild, get_guild_rankings,
    get_member_rankings, transfer_leadership, kick_member, promote_member,
    start_guild_task, contribute_to_guild_task,
    start_guild_battle, deal_boss_damage,
    add_guild_log, MAX_MEMBERS, GUILD_BOSSES,
    auto_progress_guild, get_active_season_id, get_season_guild_ranking,
    get_season_member_ranking, get_season_info, end_season,
)
from analytics import (
    log_daily_activity as _log_activity,
    get_weekly_report, get_monthly_report, get_insights, get_smart_reminders,
    format_weekly_report, get_streak_history, get_type_breakdown,
)


CMD_HELP = """\
Shadow CLI v{version} - 暗影君主系统

用法:
  python main.py status                查看角色状态面板
  python main.py record <type> [n]     记录行为并获取 EXP
  python main.py daily                 查看/完成每日任务
  python main.py add <stat> <n>        分配属性点
  python main.py summon [type]         召唤暗影士兵
  python main.py army                  查看士兵列表
  python main.py legion [scale]        全军出击
  python main.py achievements          查看成就
  python main.py analyze [path]        深渊凝视: 分析项目
  python main.py plan "[任务]"         影之战略: 规划任务
  python main.py monitor               虚空监控: 实时面板
  python main.py deploy [分钟]          领域展开: 全局诊断
  python main.py archive "[主题]"      记忆固化: 保存经验
  python main.py report [周期] [--offset N] 数据分析报告
  python main.py insights              数据洞察
  python main.py reminders             智能提醒
  python main.py reset                 重置角色 (危险!)

record 类型:
  commit, coding <行数>, vocabulary <单词数>,
  exercise <分钟>, reading <页数>

add 属性:
  str (力量), agi (敏捷), sen (感知), vit (体力), int (智力)

summon 类型:
  explore, plan, dev, test, debug, review, doc (留空则随机)

legion 规模:
  small (3), medium (5), large (7), full (12)
""".format(version=VERSION)


def cmd_status(player: dict) -> str:
    """Display player status panel."""
    title = get_title(player["level"])
    power = calculate_power(player)

    # EXP bar
    bar_len = 20
    exp_pct = player["exp"] / player["expToNext"]
    exp_filled = int(bar_len * exp_pct)
    exp_bar = "█" * exp_filled + "░" * (bar_len - exp_filled)

    # Soldiers
    soldiers = player.get("soldiers", [])
    soldier_str = ", ".join(f"{s['name']}(LV.{s.get('level', 1)})" for s in soldiers[:5]) if soldiers else "无"

    achievements = player.get("achievements", [])

    return f"""\
┌──────────────────────────────────────────────┐
│  Shadow CLI v{VERSION} - 暗影君主系统           │
├──────────────────────────────────────────────┤
│  名称: {player['name']:<18}  等级: LV.{player['level']}            │
│  称号: {title:<22}  战力: {power}         │
├──────────────────────────────────────────────┤
│  EXP: [{exp_bar}] {player['exp']:>4}/{player['expToNext']}           │
│  HP:  {player['hp']}/{100}  MP: {player['mp']}/{100}  金币: {player.get('gold', 0)}          │
├──────────────────────────────────────────────┤
│  [属性]              [点数]: {player['statPoints']}                 │
│  力量 STR: {player['stats']['strength']:<3}   敏捷 AGI: {player['stats']['agility']:<3}        │
│  感知 SEN: {player['stats']['sense']:<3}   体力 VIT: {player['stats']['vitality']:<3}        │
│  智力 INT: {player['stats']['intelligence']:<3}                      │
├──────────────────────────────────────────────┤
│  士兵: {soldier_str}                         │
│  连击: {player.get('streak', 0)}天  COMBO: {player.get('combo', 0)}  │
│  成就: {len(achievements)}/{len(__import__('config').ACHIEVEMENTS)}  总EXP: {player.get('totalExp', 0)}             │
└──────────────────────────────────────────────┘"""


def cmd_record(player: dict, action_type: str, quantity: int = 1) -> str:
    """Record an action and add EXP."""
    streak = player.get("streak", 0)
    combo = player.get("combo", 0)
    exp = get_exp_for_action(action_type, quantity, streak, combo, player)

    if exp <= 0:
        return f"❌ 未知行为类型: {action_type}\n有效: commit, coding, vocabulary, exercise, reading"

    # Double EXP from shop
    if player.get("doubleExpNext", 0) > 0:
        exp *= 2
        player["doubleExpNext"] -= 1

    # Track commit count
    if action_type == "commit":
        player["commitCount"] = player.get("commitCount", 0) + quantity

    # Apply task progress
    task_result = apply_task_progress(player, action_type, quantity)

    # Progress dungeon tasks
    dungeon_result = progress_dungeon(player, action_type, quantity)

    # Add EXP
    levelup_msgs = add_exp(player, exp)

    # Check achievements
    new_achievements = check_achievements(player)
    ach_msgs = []
    for ach in new_achievements:
        ach_msgs.append(f"🏆 成就解锁: {ach['name']} — {ach['description']} (+{ach['reward_exp']} EXP, +{ach['reward_gold']} 金币)")

    # Check boss defeats
    defeated_bosses = check_boss_defeat(player)
    boss_msgs = []
    for boss in defeated_bosses:
        boss_msgs.append(f"💀 Boss 击破: {boss['name']}! (+{boss['reward_exp']} EXP, +{boss['reward_gold']} 金币)")

    # Auto-progress guild task/boss
    guild_result = auto_progress_guild(player, action_type, quantity)
    guild_msgs = []
    if guild_result.get("success") and guild_result.get("inGuild"):
        if guild_result.get("taskProgress"):
            tp = guild_result["taskProgress"]
            guild_msgs.append(
                f"🏰 公会 [{guild_result['guildName']}] 任务: {tp['progress']}/{tp['target']}"
            )
            if tp.get("completed"):
                guild_msgs.append(f"🎉 公会任务完成: {tp.get('message', '')}")
        if guild_result.get("bossDamage"):
            bd = guild_result["bossDamage"]
            guild_msgs.append(
                f"⚔️ 公会 [{guild_result['guildName']}] Boss 伤害: {bd['damage']} (HP: {bd['bossHp']}/{bd['bossMaxHp']})"
            )
            if bd.get("defeated"):
                guild_msgs.append(f"🏆 Boss 被击败: {bd.get('message', '')}")

    # Claim dungeon rewards
    dungeon_msgs = []
    if dungeon_result.get("completed"):
        for comp in dungeon_result["completed"]:
            dungeon_msgs.append(f"🏰 副本任务完成: {comp['task']} (奖励: {comp['reward']} EXP)")
        # Check if all instances are done
        all_instances_done = all(
            all(t["completed"] for t in inst["tasks"])
            for inst in dungeon_result.get("instances", [])
        )
        if all_instances_done and dungeon_result.get("instances"):
            rewards = claim_dungeon_reward(player, dungeon_result["instances"])
            dungeon_msgs.extend(rewards)

    # Log daily activity for analytics
    today = date.today().isoformat()
    _log_activity(player, today, action_type, quantity, exp, 0)

    save_player(player)

    result = f"✅ 已记录: {action_type} x{quantity} → +{exp} EXP"

    # Show task progress
    if task_result["progress"]:
        for task_id, old, new in task_result["progress"]:
            result += f"\n  📋 {task_id}: {old} → {new}"
    if task_result["completed"]:
        result += f"\n  ✅ 任务完成: {', '.join(task_result['completed'])}"
    if task_result["all_done"]:
        result += f"\n  🎉 所有每日任务完成!"

    # Show dungeon progress
    if dungeon_result.get("progress"):
        for dp in dungeon_result["progress"]:
            result += f"\n  🏰 {dp['dungeon']}: {dp['task']} {dp['old']} → {dp['new']}"

    if dungeon_msgs:
        result += "\n" + "\n".join(dungeon_msgs)
    if boss_msgs:
        result += "\n" + "\n".join(boss_msgs)
    if levelup_msgs:
        result += "\n" + "\n".join(levelup_msgs)
    if ach_msgs:
        result += "\n" + "\n".join(ach_msgs)
    if guild_msgs:
        result += "\n" + "\n".join(guild_msgs)

    return result


def cmd_daily(player: dict) -> str:
    """Show daily tasks with progress, auto-claim rewards."""
    today = date.today().isoformat()
    daily = player.get("dailyProgress", {})
    daily_date = daily.get("date", "")

    # If no tasks for today, generate them
    if daily_date != today or "tasks" not in daily:
        tasks = generate_daily_tasks(player)
        daily = {"date": today, "tasks": {}}
        for t in tasks:
            daily["tasks"][t["id"]] = {**t, "current": 0, "status": "pending"}
        player["dailyProgress"] = daily

    lines = [
        "┌──────────────────────────────────────────┐",
        "│  ⚔️  每日任务                              │",
        "├──────────────────────────────────────────┤",
    ]

    if daily_date == today:
        lines.append(f"│  📅 日期: {today}                    │")
    else:
        lines.append(f"│  📅 日期: {today} (新的一天, 任务已刷新)  │")

    lines.append("├──────────────────────────────────────────┤")

    all_tasks = daily.get("tasks", {})
    completed = sum(1 for t in all_tasks.values() if t.get("status") == "completed")
    total = len(all_tasks)

    for task_id, task in all_tasks.items():
        status_icon = "✅" if task["status"] == "completed" else "□"
        difficulty = task.get("difficulty", "D")
        lines.append(
            f"│ {status_icon} [{difficulty}] {task['name']:<14} ({task['current']}/{task['target']})"
        )

    lines.append("├──────────────────────────────────────────┤")
    total_reward = sum(t.get("reward", 0) for t in all_tasks.values())

    if completed == 0 and total > 0:
        lines.append(f"│  进度: 0/{total}  |  总奖励: {total_reward} EXP           │")
    else:
        lines.append(f"│  进度: {completed}/{total}  |  总奖励: {total_reward} EXP           │")

    lines.append("└──────────────────────────────────────────┘")

    # Auto-complete: claim rewards if all done
    if completed == total and total > 0:
        ach_before = set(player.get("achievements", []))
        reward_msgs = claim_daily_reward(player, total_reward)
        new_achievements = check_achievements(player)
        ach_msgs = []
        for ach in new_achievements:
            ach_msgs.append(f"🏆 成就解锁: {ach['name']} (+{ach['reward_exp']} EXP)")
        save_player(player)

        lines.append(f"\n🎉 所有任务完成！+{total_reward + int(total_reward * 0.2)} EXP (含连击奖励)")
        lines.extend(reward_msgs)
        lines.extend(ach_msgs)
    else:
        lines.append(f"\n💡 完成所有任务可获得 {total_reward} EXP + 连击奖励")
        bonus = int(total_reward * 0.2)
        lines.append(f"   (含 {player.get('streak', 0)} 天连击加成)")

    return "\n".join(lines)


def generate_daily_tasks(player: dict) -> list[dict]:
    """Generate daily tasks using engine function."""
    from engine import generate_daily_tasks as gen_tasks
    return gen_tasks(player)


def cmd_add_stat(player: dict, stat_key: str, amount: int) -> str:
    """Allocate stat points."""
    err = allocate_stat(player, stat_key, amount)
    if err:
        return err
    save_player(player)
    cn_name = STAT_NAMES_CN.get(stat_key, stat_key)
    stat_full = STAT_FULL_NAMES.get(stat_key, stat_key)
    return f"✅ {cn_name} ({stat_key}) +{amount} → 当前: {player['stats'][stat_full]}\n剩余点数: {player['statPoints']}"


def cmd_summon(player: dict, soldier_type: str | None = None) -> str:
    """Summon a soldier."""
    result = summon_soldier(player, soldier_type)
    if not result["success"]:
        return result["message"]
    save_player(player)
    return result["message"]


def cmd_army(player: dict) -> str:
    """Display soldier list."""
    soldiers = player.get("soldiers", [])
    lines = [
        "┌──────────────────────────────────────────┐",
        "│  ⚔️  暗影士兵列表                          │",
        "├──────────────────────────────────────────┤",
    ]

    if not soldiers:
        lines.append("│  暂无士兵 (使用 summon 召唤)                  │")
    else:
        for i, s in enumerate(soldiers, 1):
            lines.append(
                f"│  {i}. {s['name']} LV.{s.get('level', 1)} [{s['type']}]       │"
            )

    lines.append("├──────────────────────────────────────────┤")
    lines.append(f"│  总计: {len(soldiers)} 名士兵                          │")
    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_legion(player: dict, scale: str = "medium") -> str:
    """Summon a legion."""
    result = summon_legion(player, scale)
    if not result["success"]:
        return result["message"]
    save_player(player)
    return result["message"]


def cmd_achievements(player: dict) -> str:
    """Display achievement status."""
    achievements = get_achievement_status(player)
    unlocked = sum(1 for a in achievements if a["unlocked"])
    total = len(achievements)

    lines = [
        "┌──────────────────────────────────────────┐",
        "│  🏆 成就列表                              │",
        "├──────────────────────────────────────────┤",
    ]

    for ach in achievements:
        icon = "✅" if ach["unlocked"] else "🔒"
        name = ach["name"][:12]
        desc = ach["description"][:18]
        lines.append(
            f"│ {icon} {name:<14} {desc:<20} │"
        )

    lines.append("├──────────────────────────────────────────┤")
    lines.append(f"│  进度: {unlocked}/{total}                              │")
    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_analyze(player: dict, target: str | None = None) -> str:
    """Analyze a project directory."""
    target = target or "."
    target_path = Path(target).resolve()

    if not target_path.exists():
        return f"❌ 路径不存在: {target}"

    # Scan files
    code_extensions = {".py", ".js", ".ts", ".go", ".rs", ".java", ".jsx", ".tsx", ".css", ".html", ".json", ".yaml", ".yml"}
    file_count = 0
    total_lines = 0
    tech_stack = set()
    file_list = []

    try:
        for f in target_path.rglob("*"):
            if f.is_file() and f.suffix in code_extensions:
                file_count += 1
                file_list.append(f)
                if file_count > 200:
                    break
    except PermissionError:
        pass

    # Count lines for up to 50 files
    for f in file_list[:50]:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                total_lines += len(fh.readlines())
        except (PermissionError, OSError):
            pass

    # Detect tech stack
    indicator_files = {
        "Python": {"requirements.txt", "setup.py", "pyproject.toml"},
        "Node.js": {"package.json"},
        "TypeScript": {"tsconfig.json"},
        "React": {"package.json"},
        "Rust": {"Cargo.toml"},
        "Go": {"go.mod"},
    }
    try:
        for item in target_path.iterdir():
            for tech, indicators in indicator_files.items():
                if item.name in indicators:
                    tech_stack.add(tech)
    except PermissionError:
        pass

    # Complexity rating
    if file_count < 10:
        complexity = "E 级 - 小型项目"
        exp_reward = 20
    elif file_count < 50:
        complexity = "D 级 - 中型项目"
        exp_reward = 50
    elif file_count < 200:
        complexity = "C 级 - 大型项目"
        exp_reward = 100
    else:
        complexity = "B 级 - 企业级项目"
        exp_reward = 200

    # Grant EXP
    levelup_msgs = add_exp(player, exp_reward)

    # Check achievements
    new_achievements = check_achievements(player)
    ach_msgs = []
    for ach in new_achievements:
        ach_msgs.append(f"🏆 成就解锁: {ach['name']} (+{ach['reward_exp']} EXP)")

    save_player(player)

    tech_str = ", ".join(tech_stack) if tech_stack else "未知"
    level_up_msg = "\n" + "\n".join(levelup_msgs) if levelup_msgs else ""

    return f"""\
┌──────────────────────────────────────────────┐
│  👁️ 深渊凝视报告                               │
├──────────────────────────────────────────────┤
│  目标: {str(target_path)[:28]}                │
│  复杂度: {complexity}                        │
├──────────────────────────────────────────────┤
│  文件数量: {file_count}                        │
│  代码行数: ~{total_lines}行                    │
│  技术栈: {tech_str}                     │
├──────────────────────────────────────────────┤
│  获得经验: +{exp_reward} EXP                   │
└──────────────────────────────────────────────┘{level_up_msg}{chr(10) + chr(10).join(ach_msgs) if ach_msgs else ''}"""


def cmd_plan(player: dict, task_description: str) -> str:
    """Plan a task - break it into phases."""
    # Difficulty based on description length
    if len(task_description) < 20:
        difficulty = "E"
        exp_reward = 30
    elif len(task_description) < 50:
        difficulty = "D"
        exp_reward = 50
    elif len(task_description) < 100:
        difficulty = "C"
        exp_reward = 80
    else:
        difficulty = "B"
        exp_reward = 120

    # Generate task ID
    task_id = hashlib_md5(task_description + datetime.now().isoformat())[:8]

    # Save quest file
    config.QUESTS_DIR.mkdir(parents=True, exist_ok=True)
    quest = {
        "id": task_id,
        "description": task_description,
        "difficulty": difficulty,
        "status": "planned",
        "expReward": exp_reward,
        "createdAt": datetime.now().isoformat(),
    }
    quest_file = config.QUESTS_DIR / f"{task_id}.json"
    with open(quest_file, "w", encoding="utf-8") as f:
        json.dump(quest, f, indent=2, ensure_ascii=False)

    # Grant planning EXP
    add_exp(player, 10)
    save_player(player)

    return f"""\
┌──────────────────────────────────────────────┐
│  🎯 影之战略规划书                             │
├──────────────────────────────────────────────┤
│  任务: {task_description[:40]}               │
│  难度: {difficulty}级  ID: {task_id}                      │
├──────────────────────────────────────────────┤
│  Phase I: 情报收集 (准备阶段)                  │
│  ① 深度扫描项目现状                           │
│  ② 识别关键依赖和限制                         │
│  ③ 标记潜在风险点                            │
│                                              │
│  Phase II: 核心攻坚 (开发阶段)                │
│  ④ 制定详细技术方案                          │
│  ⑤ 分步实施功能开发                          │
│  ⑥ 持续质量验证                              │
│                                              │
│  Phase III: 战后重建 (收尾阶段)               │
│  ⑦ 完整性测试                                │
│  ⑧ 文档归档                                  │
│  ⑨ 经验固化                                  │
├──────────────────────────────────────────────┤
│  完成奖励: {exp_reward} EXP                    │
│  规划奖励: 10 EXP (已获得)                     │
└──────────────────────────────────────────────┘"""


def hashlib_md5(text: str) -> str:
    """Generate MD5 hash (using hashlib)."""
    import hashlib
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def cmd_monitor(player: dict) -> str:
    """Show real-time monitoring panel."""
    power = calculate_power(player)
    title = get_title(player["level"])
    streak = player.get("streak", 0)
    combo = player.get("combo", 0)

    # EXP progress
    exp_pct = int(100 * player["exp"] / player["expToNext"])

    # Active quests
    active_quests = 0
    if config.QUESTS_DIR.exists():
        for qf in config.QUESTS_DIR.glob("*.json"):
            try:
                with open(qf) as f:
                    q = json.load(f)
                if q.get("status") in ("active", "planned"):
                    active_quests += 1
            except (json.JSONDecodeError, OSError):
                pass

    lines = [
        "┌──────────────────────────────────────────┐",
        "│  👁️ 虚空监控面板                           │",
        "├──────────────────────────────────────────┤",
        f"│  称号: {title}                    │",
        f"│  LV.{player['level']}  战力: {power}                    │",
        f"│  EXP: {exp_pct}%                       │",
        f"│  HP: {player['hp']}/100  MP: {player['mp']}/100                      │",
        f"│  连击: {streak}天  COMBO: {combo}                     │",
        f"│  活跃任务: {active_quests}                      │",
        f"│  士兵: {len(player.get('soldiers', []))}名                          │",
        "├──────────────────────────────────────────┤",
        f"│  总EXP: {player.get('totalExp', 0)}                        │",
        f"│  金币: {player.get('gold', 0)}                         │",
        "└──────────────────────────────────────────┘",
    ]
    return "\n".join(lines)


def cmd_deploy(player: dict, minutes: int = 30) -> str:
    """Deploy global diagnostic mode."""
    mp_cost = minutes
    if player.get("mp", 0) < mp_cost:
        return f"⚠️ MP 不足\n需要: {mp_cost} MP\n当前: {player['mp']} MP"

    player["mp"] -= mp_cost

    # Scan current directory for issues (simulated)
    findings = []
    try:
        for p in Path(".").rglob("*.py"):
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    if "TODO" in content:
                        findings.append(f"TODO 在 {p}")
                    if "FIXME" in content:
                        findings.append(f"FIXME 在 {p}")
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass

    findings_str = "\n".join(f"  • {f}" for f in findings[:10]) if findings else "  未发现明显问题 ✓"

    save_player(player)

    return f"""\
┌──────────────────────────────────────────────┐
│  🛡️ 领域展开: 全域诊断模式                     │
├──────────────────────────────────────────────┤
│  持续时间: {minutes}分钟                       │
│  扫描维度: 语法/安全/性能/重复                │
├──────────────────────────────────────────────┤
│  扫描结果:                                    │
│{findings_str if findings_str.startswith('\n') else '  ' + findings_str}
│                                              │
│  MP 消耗: -{mp_cost}                        │
└──────────────────────────────────────────────┘
「这就是...我的领域。」"""


def cmd_archive(player: dict, topic: str) -> str:
    """Archive experience to memory."""
    # Save to logs directory
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.LOGS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{topic.replace(' ', '_')}.json"
    log_entry = {
        "topic": topic,
        "player_level": player["level"],
        "player_title": player.get("title", ""),
        "timestamp": datetime.now().isoformat(),
        "stats": player.get("stats", {}),
    }
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, indent=2, ensure_ascii=False)

    # Grant EXP + INT
    add_exp(player, 25)
    player["stats"]["intelligence"] = player.get("stats", {}).get("intelligence", 10) + 1
    save_player(player)

    return f"""\
┌──────────────────────────────────────────────┐
│  📜 记忆固化完成                               │
├──────────────────────────────────────────────┤
│  主题: {topic[:30]}                           │
│  位置: {str(log_file)[:30]}           │
├──────────────────────────────────────────────┤
│  +25 EXP                                     │
│  智力 (INT) +1 (永久)                        │
└──────────────────────────────────────────────┘"""


def cmd_scan_git(player: dict, path: str = ".") -> str:
    """Scan git commits and grant EXP."""
    git_root = get_git_root(path)
    if not git_root:
        git_root = str(Path(path).resolve())
        if not (Path(git_root) / ".git").exists():
            return f"❌ 不是 Git 仓库: {path}"
    result = scan_commits_and_grant(player, git_root)
    msg = result["message"]
    if result.get("levelup_msgs"):
        msg += "\n" + "\n".join(result["levelup_msgs"])
    if result.get("achievement_msgs"):
        msg += "\n" + "\n".join(result["achievement_msgs"])
    return msg


def cmd_setup_git(player: dict, path: str = ".") -> str:
    """Install Git post-commit hook."""
    git_root = get_git_root(path)
    if not git_root:
        return f"❌ 不是 Git 仓库: {path}"
    result = install_git_hook(git_root)
    return result["message"]


def cmd_remove_git(player: dict, path: str = ".") -> str:
    """Remove Git post-commit hook."""
    git_root = get_git_root(path)
    if not git_root:
        return f"❌ 不是 Git 仓库: {path}"
    result = uninstall_git_hook(git_root)
    return result["message"]


def cmd_scan_files(player: dict, path: str = ".") -> str:
    """Scan code files and grant EXP for changes."""
    result = scan_files_and_grant(player, path)
    msg = result["message"]
    if result.get("levelup_msgs"):
        msg += "\n" + "\n".join(result["levelup_msgs"])
    if result.get("achievement_msgs"):
        msg += "\n" + "\n".join(result["achievement_msgs"])
    return msg


def cmd_git_status(player: dict) -> str:
    """Show Git tracking status."""
    return get_git_status_info()


def cmd_github(player: dict, action: str, repo: str = "") -> str:
    """Manage GitHub remote repo sync.

    Actions:
        add <owner/repo>   - 添加远程仓库到同步列表
        remove <owner/repo> - 从同步列表移除
        list               - 列出已配置的仓库
        scan [owner/repo]  - 扫描远程 commit 并获取 EXP
    """
    if action == "add":
        if not repo:
            return "❌ 用法: shadow github add <owner/repo>"
        result = github_add_repo(repo)
        return result["message"]

    elif action == "remove":
        if not repo:
            return "❌ 用法: shadow github remove <owner/repo>"
        result = github_remove_repo(repo)
        return result["message"]

    elif action == "list":
        result = github_list_repos()
        if not result["repos"]:
            return "📭 未配置 GitHub 仓库\n使用 'shadow github add <owner/repo>' 添加"
        lines = ["📦 已配置的 GitHub 仓库:"]
        for r in result["repos"]:
            token_str = " 🔑" if r.get("token") else ""
            lines.append(f"  • {r['name']}{token_str}")
        lines.append(f"\n共 {result['total']} 个仓库")
        return "\n".join(lines)

    elif action == "scan":
        result = github_scan_and_grant(player, repo)
        msg = result["message"]
        if result.get("levelup_msgs"):
            msg += "\n" + "\n".join(result["levelup_msgs"])
        if result.get("achievement_msgs"):
            msg += "\n" + "\n".join(result["achievement_msgs"])
        return msg

    else:
        return f"❌ 未知动作: {action}\n可用: add, remove, list, scan"


def cmd_file_status(player: dict) -> str:
    """Show file tracking status."""
    return get_file_status()


def cmd_dungeons(player: dict) -> str:
    """Show available dungeons."""
    available = get_available_dungeons(player)
    lines = [
        "┌──────────────────────────────────────────┐",
        "│  🏰 可用副本                              │",
        "├──────────────────────────────────────────┤",
    ]

    if not available:
        lines.append("│  暂无可用副本                        │")
    else:
        for d in available:
            type_icon = {"daily": "📅", "weekly": "🔄", "boss": "💀"}.get(d["type"], "📋")
            lines.append(f"│ {type_icon} {d['id']:<20}                 │")
            lines.append(f"│   {d['name']} ({d['type']})             │")

    lines.append("├──────────────────────────────────────────┤")
    lines.append("│  使用 'shadow enter-dungeon <副本ID>' 进入  │")
    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_enter_dungeon(player: dict, dungeon_id: str) -> str:
    """Enter a dungeon."""
    available = [d["id"] for d in get_available_dungeons(player)]
    if dungeon_id not in available:
        return f"❌ 不可用副本: {dungeon_id}\n可用: {', '.join(available) if available else '无'}"

    result = generate_dungeon_instance(dungeon_id, player)
    if not result["success"]:
        return result["message"]

    inst = result["instance"]
    lines = [
        f"🏰 进入副本: {inst['dungeon_name']} [{inst['difficulty']}]",
        f"+{result['entry_exp']} EXP (入场奖励)",
        "",
        "任务列表:",
    ]
    for i, task in enumerate(inst["tasks"], 1):
        lines.append(f"  {i}. {task['name']} ({task['type']} x{task['target']}) → {task['reward']} EXP")
    lines.append("")
    lines.append(f"完成全部任务可获得: {inst['total_reward']} EXP")
    lines.append("💡 使用 record 命令记录行为自动推进副本进度")

    save_player(player)
    return "\n".join(lines)


def cmd_boss_list(player: dict) -> str:
    """Show available bosses."""
    bosses = get_active_bosses(player)
    existing = set(player.get("bosses_defeated", []))
    lines = [
        "┌──────────────────────────────────────────┐",
        "│  💀 Boss 列表                            │",
        "├──────────────────────────────────────────┤",
    ]

    if not bosses:
        lines.append("│  暂无可挑战 Boss (需要 LV.10+)          │")
    else:
        for boss in bosses:
            defeated = boss["id"] in existing
            icon = "✅" if defeated else "⚔️"
            lines.append(f"│ {icon} {boss['name']:<18} HP:{boss['hp']}      │")
            lines.append(f"│   {boss['description']:<22} │")
            if not defeated:
                lines.append(f"│   击破条件: LV.{boss['defeat_value']} (条件值)          │")
            lines.append(f"│   奖励: {boss['reward_exp']} EXP, {boss['reward_gold']} 金币         │")

    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_shop(player: dict, category: str | None = None) -> str:
    """Show shop items."""
    items = get_shop_items(player, category)
    lines = [
        "┌──────────────────────────────────────────┐",
        "│  🏪 暗影商店                              │",
        "├──────────────────────────────────────────┤",
        f"│  金币: {player.get('gold', 0)}  宝石: {player.get('gems', 0)}                  │",
        "├──────────────────────────────────────────┤",
    ]

    if not items:
        if category:
            lines.append(f"│  类别 '{category}' 暂无商品                 │")
        else:
            lines.append("│  商店暂无商品 (提高等级解锁更多)             │")
    else:
        current_cat = None
        for item in items:
            if item["category"] != current_cat:
                current_cat = item["category"]
                cat_name = {"consumable": "消耗品", "equipment": "装备", "appearance": "外观", "functional": "功能"}.get(current_cat, current_cat)
                lines.append(f"│  ── {cat_name} ──                     │")
            price_str = f"{item['price']}G" if item["price_type"] == "gold" else f"{item['price']}💎"
            name = item["name"][:14]
            desc = item["description"][:18]
            lines.append(f"│  {item['id']:<18} {price_str:<8}          │")

    lines.append("├──────────────────────────────────────────┤")
    lines.append("│  使用 'shadow buy <ID>' 购买              │")
    lines.append("│  使用 'shadow sell <ID>' 出售 (50% 回收)   │")
    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_buy(player: dict, item_id: str) -> str:
    """Buy an item from the shop."""
    result = buy_item(player, item_id)
    if result["success"]:
        save_player(player)
    return result["message"]


def cmd_sell(player: dict, item_id: str) -> str:
    """Sell an item."""
    result = sell_item(player, item_id)
    if result["success"]:
        save_player(player)
    return result["message"]


def cmd_inventory(player: dict) -> str:
    """Show player inventory."""
    items = get_inventory(player)
    lines = [
        "┌──────────────────────────────────────────┐",
        "│  🎒 背包                                  │",
        "├──────────────────────────────────────────┤",
    ]

    if not items:
        lines.append("│  背包为空                              │")
    else:
        for i, item in enumerate(items, 1):
            name = item.get("name", "未知物品")[:20]
            lines.append(f"│  {i}. {name:<24} │")

    lines.append("├──────────────────────────────────────────┤")
    lines.append(f"│  总计: {len(items)} 件物品                         │")
    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


# ── Integration Commands ──────────────────────────────────────────────────

def cmd_health_import(player: dict, file_path: str) -> str:
    """Import health data from JSON/CSV file."""
    result = import_health_json(player, file_path)
    if not result["success"]:
        return result["message"]
    save_player(player)
    output = result["message"]
    if result.get("messages"):
        output += "\n" + "\n".join(result["messages"])
    return output


def cmd_health_manual(player: dict, steps: int = 0, exercise_min: int = 0, sleep_hours: float = 0) -> str:
    """Manually record health data."""
    result = record_health_manual(player, steps, exercise_min, sleep_hours)
    if not result["success"]:
        return result["message"]
    save_player(player)
    return result["message"]


def cmd_health_summary(player: dict, days: int = 7) -> str:
    """Show health data summary."""
    summary = get_health_summary(player, days)
    lines = [
        "┌──────────────────────────────────────────┐",
        "│  🏃 健康数据概要                           │",
        "├──────────────────────────────────────────┤",
        f"│  统计范围: 最近 {days} 天                     │",
        f"│  有数据天数: {summary['days_with_data']}                       │",
        "├──────────────────────────────────────────┤",
        f"│  总步数: {summary['total_steps']}                        │",
        f"│  日均步数: {summary['avg_steps']}                        │",
        f"│  总运动: {summary['total_exercise_min']} 分钟                    │",
        f"│  总睡眠: {summary['total_sleep_hours']} 小时                   │",
        "├──────────────────────────────────────────┤",
        f"│  获得 EXP: {summary['total_exp']}                      │",
        f"│  导入次数: {summary['recent_imports']}                       │",
        "└──────────────────────────────────────────┘",
    ]
    return "\n".join(lines)


def cmd_reading_import(player: dict, file_path: str) -> str:
    """Import reading data from JSON/CSV file."""
    result = import_reading_json(player, file_path)
    if not result["success"]:
        return result["message"]
    save_player(player)
    output = result["message"]
    if result.get("messages"):
        output += "\n" + "\n".join(result["messages"])
    return output


def cmd_reading_manual(player: dict, minutes: int = 0, pages: int = 0, book_title: str = "") -> str:
    """Manually record reading data."""
    result = record_reading_manual(player, minutes, pages, book_title)
    if not result["success"]:
        return result["message"]
    save_player(player)
    return result["message"]


def cmd_reading_summary(player: dict, days: int = 7) -> str:
    """Show reading data summary."""
    summary = get_reading_summary(player, days)
    lines = [
        "┌──────────────────────────────────────────┐",
        "│  📖 阅读数据概要                           │",
        "├──────────────────────────────────────────┤",
        f"│  统计范围: 最近 {days} 天                     │",
        f"│  有数据天数: {summary['days_with_data']}                       │",
        "├──────────────────────────────────────────┤",
        f"│  总时长: {summary['total_minutes']} 分钟                   │",
        f"│  总页数: {summary['total_pages']}                        │",
        f"│  日均: {summary['avg_minutes_per_day']} 分钟/天                  │",
        "├──────────────────────────────────────────┤",
        f"│  获得 EXP: {summary['total_exp']}                      │",
        f"│  导入次数: {summary['recent_imports']}                       │",
    ]
    if summary.get("books_read"):
        books_str = ", ".join(summary["books_read"][:3])
        lines.append(f"│  已读: {books_str:<19} │")
    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_browser_import(player: dict, file_path: str) -> str:
    """Import browser activity data from JSON file."""
    result = import_browser_data(player, file_path)
    if not result["success"]:
        return result["message"]
    save_player(player)
    output = result["message"]
    if result.get("messages"):
        output += "\n" + "\n".join(result["messages"])
    return output


def cmd_browser_manual(player: dict, site: str, minutes: int) -> str:
    """Manually record browser study time."""
    result = record_browser_manual(player, site, minutes)
    if not result["success"]:
        return result["message"]
    save_player(player)
    return result["message"]


def cmd_browser_summary(player: dict, days: int = 7) -> str:
    """Show browser activity summary."""
    summary = get_browser_summary(player, days)
    lines = [
        "┌──────────────────────────────────────────┐",
        "│  🌐 浏览器活动概要                         │",
        "├──────────────────────────────────────────┤",
        f"│  统计范围: 最近 {days} 天                     │",
        f"│  有数据天数: {summary['days_with_data']}                       │",
        "├──────────────────────────────────────────┤",
        f"│  总学习时长: {summary['total_minutes']} 分钟                │",
        f"│  获得 EXP: {summary['total_exp']}                      │",
        f"│  导入次数: {summary['recent_imports']}                       │",
    ]
    site_breakdown = summary.get("site_breakdown", {})
    if site_breakdown:
        lines.append("│                                          │")
        lines.append("│  站点分布:                                │")
        for site, mins in list(site_breakdown.items())[:5]:
            site_name = site[:16]
            lines.append(f"│    {site_name:<18} {mins}min            │")
    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_integrations(player: dict, action: str | None = None, target: str | None = None) -> str:
    """Show or manage integration settings."""
    settings = player.get("integrationSettings", {})
    health_on = settings.get("health_enabled", False)
    reading_on = settings.get("reading_enabled", False)
    browser_on = settings.get("browser_enabled", False)

    if action == "enable" and target:
        if target == "health":
            settings["health_enabled"] = True
        elif target == "reading":
            settings["reading_enabled"] = True
        elif target == "browser":
            settings["browser_enabled"] = True
        else:
            return f"❌ 未知集成类型: {target}\n可用: health, reading, browser"
        player["integrationSettings"] = settings
        save_player(player)
        return f"✅ 已启用 {target} 集成"

    elif action == "disable" and target:
        if target == "health":
            settings["health_enabled"] = False
        elif target == "reading":
            settings["reading_enabled"] = False
        elif target == "browser":
            settings["browser_enabled"] = False
        else:
            return f"❌ 未知集成类型: {target}\n可用: health, reading, browser"
        player["integrationSettings"] = settings
        save_player(player)
        return f"⏸ 已停用 {target} 集成"

    # Show status
    health_icon = "✅" if health_on else "⏸"
    reading_icon = "✅" if reading_on else "⏸"
    browser_icon = "✅" if browser_on else "⏸"

    total_imports = len(player.get("importHistory", []))

    lines = [
        "┌──────────────────────────────────────────┐",
        "│  🔗 外部集成状态                          │",
        "├──────────────────────────────────────────┤",
        f"│  {health_icon} 健康数据 (health)                      │",
        f"│  {reading_icon} 阅读数据 (reading)                     │",
        f"│  {browser_icon} 浏览器活动 (browser)                  │",
        "├──────────────────────────────────────────┤",
        f"│  总导入次数: {total_imports}                      │",
        "├──────────────────────────────────────────┤",
        "│  用法:                                    │",
        "│  shadow health import <file>              │",
        "│  shadow reading import <file>             │",
        "│  shadow browser import <file>             │",
        "│  shadow integrations enable <type>        │",
        "│  shadow integrations disable <type>       │",
        "└──────────────────────────────────────────┘",
    ]
    return "\n".join(lines)


# ── Analytics Commands ──────────────────────────────────────────────────────

def cmd_report(player: dict, period: str = "weekly", offset: int = 0) -> str:
    """Show weekly or monthly analytics report."""
    if period == "monthly":
        r = get_monthly_report(player, offset)
        sep = "═" * 42
        lines = [sep]
        lines.append(f"  📊 月报 - {r['month']}")
        lines.append(sep)
        lines.append(f"  活跃天数: {r['days_active']}/{r['days_in_month']}")
        lines.append(f"  获得经验: {r['total_exp']:,} EXP")
        lines.append(f"  获得金币: {r['total_gold']:,} G")
        lines.append(f"  日均EXP: {r['avg_daily_exp']} EXP")
        if r.get("best_day"):
            lines.append(f"  最佳日: {r['best_day']}")
        if r.get("worst_day"):
            lines.append(f"  最低日: {r['worst_day']}")
        lines.append("─" * 37)
        if r["actions_by_type"]:
            for t, qty in sorted(r["actions_by_type"].items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {t}: {qty}")
        lines.append("─" * 37)
        lines.append(sep)
        return "\n".join(lines)
    else:
        return format_weekly_report(player, offset)


def cmd_insights(player: dict) -> str:
    """Show personalized insights and recommendations."""
    insights = get_insights(player)
    streak = get_streak_history(player)
    breakdown = get_type_breakdown(player)

    sep = "═" * 42
    lines = [sep]
    lines.append("  🔮 数据洞察")
    lines.append(sep)
    lines.append(f"  当前连击: {streak['current_streak']} 天")
    lines.append(f"  最佳连击: {streak['best_streak']} 天")
    lines.append(f"  活跃天数: {streak['active_days']}/{streak['days_since_created']} ({streak['completion_rate']}%)")
    lines.append("─" * 37)
    if insights:
        for i, insight in enumerate(insights[:8], 1):
            lines.append(f"  {i}. {insight}")
    else:
        lines.append("  暂无洞察数据 — 先记录一些活动吧！")
    lines.append("─" * 37)
    if breakdown.get("types"):
        lines.append("  最近30天活动分布:")
        for t in breakdown["types"][:5]:
            bar_len = min(t["total_exp"] // 10, 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            lines.append(f"    {t['type']:>10} [{bar}] {t['total_exp']} EXP")
    lines.append(sep)
    return "\n".join(lines)


def cmd_reminders(player: dict) -> str:
    """Show smart reminders based on recent activity."""
    reminders = get_smart_reminders(player)
    sep = "═" * 42
    lines = [sep, "  ⏰ 智能提醒", sep]
    for i, reminder in enumerate(reminders, 1):
        lines.append(f"  {i}. {reminder}")
    lines.append(sep)
    return "\n".join(lines)


# ── Guild CLI Commands ─────────────────────────────────────────────────────

def cmd_guild_create(player: dict, name: str) -> str:
    """Create a new guild."""
    username = player.get("username", "fallback")
    existing = get_user_guild(username)
    if existing:
        return f"❌ 你已在公会 [{existing['name']}] 中，先离开再创建"
    result = create_guild(player, name, username)
    if result["success"]:
        player["guildCreated"] = True
        player["guildJoined"] = True
        save_player(player)
    return result["message"]


def cmd_guild_join(player: dict, guild_id: str) -> str:
    """Join a guild."""
    username = player.get("username", "fallback")
    existing = get_user_guild(username)
    if existing:
        return f"❌ 你已在公会 [{existing['name']}] 中"
    result = join_guild(guild_id, username, player)
    if result["success"]:
        player["guildJoined"] = True
        save_player(player)
    return result["message"]


def cmd_guild_leave(player: dict) -> str:
    """Leave current guild."""
    username = player.get("username", "fallback")
    guild = get_user_guild(username)
    if not guild:
        return "❌ 你未加入任何公会"
    result = leave_guild(guild["id"], username)
    return result["message"]


def cmd_guild_info(player: dict, guild_id: str | None = None) -> str:
    """Show guild info."""
    username = player.get("username", "fallback")
    if not guild_id:
        guild = get_user_guild(username)
        if not guild:
            return "❌ 你未加入任何公会\n使用 'guild join <ID>' 加入公会"
        guild_id = guild["id"]

    guild = get_guild(guild_id)
    if not guild:
        return f"❌ 公会不存在: {guild_id}"

    lines = [
        "┌──────────────────────────────────────────┐",
        f"│  🏰 公会: {guild['name']:<20}   │",
        f"│  排行: {guild['rank']:<22}   │",
        f"│  贡献: {guild['contribution']:<22}   │",
        f"│  领袖: {guild['leader']:<22}   │",
        "├──────────────────────────────────────────┤",
        f"│  成员: {len(guild['members'])}/{MAX_MEMBERS}                           │",
        "├──────────────────────────────────────────┤",
    ]
    for m in guild["members"]:
        role_icon = {"leader": "👑", "officer": "⭐", "member": "·"}.get(m["role"], "·")
        lines.append(f"│  {role_icon} {m['username']:<18} {m.get('contribution', 0):>6}  │")
    lines.append("├──────────────────────────────────────────┤")

    if guild.get("activeTask"):
        t = guild["activeTask"]
        pct = int(t["current"] / t["target"] * 100) if t["target"] > 0 else 0
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        lines.append(f"│  📋 任务: {t['name']:<16}   │")
        lines.append(f"│  [{bar}] {t['current']}/{t['target']}                 │")

    if guild.get("activeBoss"):
        b = guild["activeBoss"]
        hp_pct = int(b["currentHp"] / b["maxHp"] * 100)
        bar_len = hp_pct // 5
        bar = "█" * bar_len + "░" * (20 - bar_len)
        lines.append(f"│  💀 Boss: {b['name']:<17}   │")
        lines.append(f"│  [{bar}] {b['currentHp']}/{b['maxHp']}               │")

    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_guild_list(player: dict) -> str:
    """List all guilds."""
    guilds = list_guilds()
    if not guilds:
        return "🏰 暂无公会\n使用 'guild create <名称>' 创建你的公会"

    lines = [
        "┌──────────────────────────────────────────────────────┐",
        "│  🏰 公会排行榜                                    │",
        "├──────────────────────────────────────────────────────┤",
    ]
    for i, g in enumerate(guilds[:10], 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
        lines.append(
            f"│ {medal} {g['name']:<15} {g['rank']:<8} {g['members']}人 "
            f"贡献:{g['contribution']:<8} │"
        )
    lines.append("└──────────────────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_guild_task(player: dict, action: str, guild_id: str | None = None) -> str:
    """Manage guild tasks."""
    username = player.get("username", "fallback")
    if not guild_id:
        guild = get_user_guild(username)
        if not guild:
            return "❌ 你未加入任何公会"
        guild_id = guild["id"]

    if action == "start":
        result = start_guild_task(guild_id, username)
        return result["message"]
    elif action == "contribute":
        return "❌ 请通过 record 命令自动贡献到公会任务\n公会任务会自动匹配同类型的行为"

    return f"❌ 未知任务操作: {action}\n可用: start, contribute"


def cmd_guild_battle(player: dict, action: str, guild_id: str | None = None) -> str:
    """Manage guild boss battles."""
    username = player.get("username", "fallback")
    if not guild_id:
        guild = get_user_guild(username)
        if not guild:
            return "❌ 你未加入任何公会"
        guild_id = guild["id"]

    if action == "start":
        result = start_guild_battle(guild_id, username)
        return result["message"]
    elif action == "attack":
        return "❌ 请通过 record 命令自动攻击 Boss\n公会战会自动匹配行为类型"

    return f"❌ 未知 Boss 操作: {action}\n可用: start, attack"


def cmd_guild_members(player: dict, guild_id: str | None = None) -> str:
    """Show guild member rankings."""
    username = player.get("username", "fallback")
    if not guild_id:
        guild = get_user_guild(username)
        if not guild:
            return "❌ 你未加入任何公会"
        guild_id = guild["id"]

    rankings = get_member_rankings(guild_id)
    if not rankings:
        return "❌ 公会不存在或无成员"

    lines = [
        "┌──────────────────────────────────────────┐",
        "│  👥 成员排行                              │",
        "├──────────────────────────────────────────┤",
    ]
    for i, m in enumerate(rankings, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f" {i}")
        role = {"leader": "👑", "officer": "⭐"}.get(m["role"], "  ")
        lines.append(
            f"│ {medal} {role} {m['username']:<14} 贡献:{m.get('contribution', 0):>6} │"
        )
    lines.append("└──────────────────────────────────────────┘")
    return "\n".join(lines)


def cmd_guild_promote(player: dict, target: str, guild_id: str | None = None) -> str:
    """Promote a member to officer."""
    actor = player.get("username", "fallback")
    if not guild_id:
        guild = get_user_guild(actor)
        if not guild:
            return "❌ 你未加入任何公会"
        guild_id = guild["id"]
    result = promote_member(guild_id, actor, target)
    return result["message"]


def cmd_guild_kick(player: dict, target: str, guild_id: str | None = None) -> str:
    """Kick a member."""
    actor = player.get("username", "fallback")
    if not guild_id:
        guild = get_user_guild(actor)
        if not guild:
            return "❌ 你未加入任何公会"
        guild_id = guild["id"]
    result = kick_member(guild_id, actor, target)
    return result["message"]


def cmd_guild_transfer(player: dict, new_leader: str, guild_id: str | None = None) -> str:
    """Transfer guild leadership."""
    actor = player.get("username", "fallback")
    if not guild_id:
        guild = get_user_guild(actor)
        if not guild:
            return "❌ 你未加入任何公会"
        guild_id = guild["id"]
    result = transfer_leadership(guild_id, actor, new_leader)
    return result["message"]


def cmd_guild_disband(player: dict, guild_id: str) -> str:
    """Disband a guild."""
    username = player.get("username", "fallback")
    result = disband_guild(guild_id, username)
    return result["message"]


def cmd_season(player: dict, action: str | None = None, season_id: str | None = None) -> str:
    """View/manage season rankings."""
    if not action or action == "info":
        sid = season_id or get_active_season_id()
        info = get_season_info(sid)
        if not info.get("success"):
            return f"❌ {info.get('message', '赛季不存在')}"
        lines = [
            "┌──────────────────────────────────────────┐",
            f"│  📊 赛季信息                             │",
            "├──────────────────────────────────────────┤",
            f"│  赛季: {info['id']:<24}   │",
            f"│  类型: {info['type']:<24}   │",
            f"│  公会数: {info['guildCount']:<22}   │",
            f"│  成员数: {info['memberCount']:<22}   │",
            f"│  状态: {'已结束' if info.get('endedAt') else '进行中'}{'':>20}   │",
            "└──────────────────────────────────────────┘",
        ]
        return "\n".join(lines)

    elif action == "rankings" or action == "guilds":
        sid = season_id or get_active_season_id()
        rankings = get_season_guild_ranking(sid)
        if not rankings:
            return f"📊 赛季 {sid} 暂无排行"
        lines = [
            f"┌──────────────────────────────────────────────────┐",
            f"│  📊 赛季排行: {sid}                      │",
            "├──────────────────────────────────────────────────┤",
        ]
        for i, g in enumerate(rankings[:10], 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f" {i}")
            lines.append(
                f"│ {medal} {g['guildName']:<12} {g['rank']:<8} "
                f"贡献:{g['contribution']:<8} │"
            )
        lines.append("└──────────────────────────────────────────────────┘")
        return "\n".join(lines)

    elif action == "members":
        sid = season_id or get_active_season_id()
        rankings = get_season_member_ranking(sid)
        if not rankings:
            return f"📊 赛季 {sid} 暂无成员排行"
        lines = [
            f"┌──────────────────────────────────────────┐",
            f"│  📊 赛季成员排行: {sid}           │",
            "├──────────────────────────────────────────┤",
        ]
        for i, m in enumerate(rankings[:10], 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f" {i}")
            lines.append(
                f"│ {medal} {m['username']:<18} 贡献:{m['contribution']:<6} │"
            )
        lines.append("└──────────────────────────────────────────┘")
        return "\n".join(lines)

    elif action == "end":
        sid = season_id or get_active_season_id()
        result = end_season(sid)
        if result.get("success"):
            return f"✅ 赛季 {sid} 已结束\n" + json.dumps(result["rewards"], indent=2, ensure_ascii=False)
        return f"❌ {result.get('message', '结束赛季失败')}"

    return f"❌ 未知赛季操作: {action}\n可用: info, rankings, members, end"


def main():
    parser = argparse.ArgumentParser(
        description="Shadow CLI - 暗影君主系统",
        add_help=True,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # status
    subparsers.add_parser("status", help="查看角色状态")

    # record
    rec_parser = subparsers.add_parser("record", help="记录行为并获取 EXP")
    rec_parser.add_argument("action", help="行为类型: commit, coding, vocabulary, exercise, reading")
    rec_parser.add_argument("quantity", nargs="?", type=int, default=1, help="数量")

    # daily
    subparsers.add_parser("daily", help="查看每日任务")

    # add stat
    add_parser = subparsers.add_parser("add", help="分配属性点")
    add_parser.add_argument("stat", help="属性: str, agi, sen, vit, int")
    add_parser.add_argument("amount", type=int, help="数量")

    # summon
    summon_parser = subparsers.add_parser("summon", help="召唤暗影士兵")
    summon_parser.add_argument("type", nargs="?", help="士兵类型 (留空则随机)")

    # army
    subparsers.add_parser("army", help="查看士兵列表")

    # legion
    legion_parser = subparsers.add_parser("legion", help="全军出击")
    legion_parser.add_argument("scale", nargs="?", default="medium", help="规模: small/medium/large/full")

    # achievements
    subparsers.add_parser("achievements", help="查看成就")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="深渊凝视: 分析项目")
    analyze_parser.add_argument("path", nargs="?", default=".", help="项目路径")

    # plan
    plan_parser = subparsers.add_parser("plan", help="影之战略: 规划任务")
    plan_parser.add_argument("task", help="任务描述")

    # monitor
    subparsers.add_parser("monitor", help="虚空监控: 实时面板")

    # deploy
    deploy_parser = subparsers.add_parser("deploy", help="领域展开: 全局诊断")
    deploy_parser.add_argument("minutes", nargs="?", type=int, default=30, help="持续时间(分钟)")

    # archive
    archive_parser = subparsers.add_parser("archive", help="记忆固化: 保存经验")
    archive_parser.add_argument("topic", help="归档主题")

    # reset
    subparsers.add_parser("reset", help="重置角色 (危险!)")

    # scan-git
    scan_git_parser = subparsers.add_parser("scan-git", help="扫描 Git 提交并获取 EXP")
    scan_git_parser.add_argument("path", nargs="?", default=".", help="仓库路径")

    # setup-git
    setup_git_parser = subparsers.add_parser("setup-git", help="安装 Git post-commit hook")
    setup_git_parser.add_argument("path", nargs="?", default=".", help="仓库路径")

    # remove-git
    remove_git_parser = subparsers.add_parser("remove-git", help="移除 Git post-commit hook")
    remove_git_parser.add_argument("path", nargs="?", default=".", help="仓库路径")

    # github
    github_parser = subparsers.add_parser("github", help="GitHub 远程仓库同步")
    github_parser.add_argument("action", choices=["add", "remove", "list", "scan"], help="操作")
    github_parser.add_argument("repo", nargs="?", default="", help="仓库名 owner/repo")

    # git-status
    subparsers.add_parser("git-status", help="查看 Git 追踪状态")

    # scan-files
    scan_files_parser = subparsers.add_parser("scan-files", help="扫描代码文件变更并获取 EXP")
    scan_files_parser.add_argument("path", nargs="?", default=".", help="目录路径")

    # file-status
    subparsers.add_parser("file-status", help="查看文件追踪状态")

    # dungeons
    subparsers.add_parser("dungeons", help="查看可用副本")

    # enter-dungeon
    enter_dungeon_parser = subparsers.add_parser("enter-dungeon", help="进入副本")
    enter_dungeon_parser.add_argument("dungeon_id", help="副本ID")

    # boss-list
    subparsers.add_parser("boss-list", help="查看 Boss 列表")

    # shop
    shop_parser = subparsers.add_parser("shop", help="浏览商店")
    shop_parser.add_argument("category", nargs="?", help="商品类别: consumable/equipment/appearance/functional")

    # buy
    buy_parser = subparsers.add_parser("buy", help="购买商品")
    buy_parser.add_argument("item_id", help="商品ID")

    # sell
    sell_parser = subparsers.add_parser("sell", help="出售物品")
    sell_parser.add_argument("item_id", help="商品ID")

    # inventory
    subparsers.add_parser("inventory", help="查看背包")

    # health import
    health_import_parser = subparsers.add_parser("health-import", help="导入健康数据")
    health_import_parser.add_argument("file", help="JSON/CSV 文件路径")

    # health manual
    health_manual_parser = subparsers.add_parser("health-manual", help="手动记录健康数据")
    health_manual_parser.add_argument("steps", nargs="?", type=int, default=0, help="步数")
    health_manual_parser.add_argument("--exercise", type=int, default=0, help="运动分钟")
    health_manual_parser.add_argument("--sleep", type=float, default=0, help="睡眠小时")

    # health summary
    health_summary_parser = subparsers.add_parser("health-summary", help="查看健康数据概要")
    health_summary_parser.add_argument("--days", type=int, default=7, help="统计天数")

    # reading import
    reading_import_parser = subparsers.add_parser("reading-import", help="导入阅读数据")
    reading_import_parser.add_argument("file", help="JSON/CSV 文件路径")

    # reading manual
    reading_manual_parser = subparsers.add_parser("reading-manual", help="手动记录阅读数据")
    reading_manual_parser.add_argument("minutes", nargs="?", type=int, default=0, help="阅读分钟")
    reading_manual_parser.add_argument("--pages", type=int, default=0, help="页数")
    reading_manual_parser.add_argument("--book", type=str, default="", help="书名")

    # reading summary
    reading_summary_parser = subparsers.add_parser("reading-summary", help="查看阅读数据概要")
    reading_summary_parser.add_argument("--days", type=int, default=7, help="统计天数")

    # browser import
    browser_import_parser = subparsers.add_parser("browser-import", help="导入浏览器活动数据")
    browser_import_parser.add_argument("file", help="JSON 文件路径")

    # browser manual
    browser_manual_parser = subparsers.add_parser("browser-manual", help="手动记录浏览器学习")
    browser_manual_parser.add_argument("site", help="网站域名")
    browser_manual_parser.add_argument("minutes", type=int, help="学习分钟")

    # browser summary
    browser_summary_parser = subparsers.add_parser("browser-summary", help="查看浏览器活动概要")
    browser_summary_parser.add_argument("--days", type=int, default=7, help="统计天数")

    # integrations
    int_parser = subparsers.add_parser("integrations", help="查看/管理集成状态")
    int_parser.add_argument("action", nargs="?", help="操作: enable/disable")
    int_parser.add_argument("target", nargs="?", help="目标: health/reading/browser")

    # season
    season_parser = subparsers.add_parser("season", help="查看/管理赛季排行")
    season_parser.add_argument("action", nargs="?", help="操作: info/rankings/guilds/members/end")
    season_parser.add_argument("season_id", nargs="?", help="赛季ID (可选)")

    # report
    report_parser = subparsers.add_parser("report", help="查看数据分析报告")
    report_parser.add_argument("period", nargs="?", default="weekly", help="周期: weekly/monthly")
    report_parser.add_argument("--offset", type=int, default=0, help="回退周数/月数")

    # insights
    subparsers.add_parser("insights", help="查看数据洞察和建议")

    # reminders
    subparsers.add_parser("reminders", help="查看智能提醒")

    # guild create
    guild_create_parser = subparsers.add_parser("guild-create", help="创建公会")
    guild_create_parser.add_argument("name", help="公会名称")

    # guild join
    guild_join_parser = subparsers.add_parser("guild-join", help="加入公会")
    guild_join_parser.add_argument("guild_id", help="公会ID")

    # guild leave
    subparsers.add_parser("guild-leave", help="离开公会")

    # guild info
    guild_info_parser = subparsers.add_parser("guild-info", help="查看公会信息")
    guild_info_parser.add_argument("guild_id", nargs="?", help="公会ID (可选)")

    # guild list
    subparsers.add_parser("guild-list", help="查看所有公会")

    # guild task
    guild_task_parser = subparsers.add_parser("guild-task", help="公会任务管理")
    guild_task_parser.add_argument("action", help="操作: start/contribute")
    guild_task_parser.add_argument("guild_id", nargs="?", help="公会ID (可选)")

    # guild battle
    guild_battle_parser = subparsers.add_parser("guild-battle", help="公会 Boss 战")
    guild_battle_parser.add_argument("action", help="操作: start/attack")
    guild_battle_parser.add_argument("guild_id", nargs="?", help="公会ID (可选)")

    # guild members
    guild_members_parser = subparsers.add_parser("guild-members", help="公会成员排行")
    guild_members_parser.add_argument("guild_id", nargs="?", help="公会ID (可选)")

    # guild promote
    guild_promote_parser = subparsers.add_parser("guild-promote", help="任命公会副手")
    guild_promote_parser.add_argument("target", help="目标用户名")
    guild_promote_parser.add_argument("guild_id", nargs="?", help="公会ID (可选)")

    # guild kick
    guild_kick_parser = subparsers.add_parser("guild-kick", help="踢出公会成员")
    guild_kick_parser.add_argument("target", help="目标用户名")
    guild_kick_parser.add_argument("guild_id", nargs="?", help="公会ID (可选)")

    # guild transfer
    guild_transfer_parser = subparsers.add_parser("guild-transfer", help="转让公会领导权")
    guild_transfer_parser.add_argument("new_leader", help="新领导者用户名")
    guild_transfer_parser.add_argument("guild_id", nargs="?", help="公会ID (可选)")

    # guild disband
    guild_disband_parser = subparsers.add_parser("guild-disband", help="解散公会 (危险!)")
    guild_disband_parser.add_argument("guild_id", help="公会ID")

    # web
    web_parser = subparsers.add_parser("web", help="启动 Web 面板")
    web_parser.add_argument("--port", type=int, default=8080, help="端口号 (默认 8080)")

    args = parser.parse_args()

    if not args.command:
        print(CMD_HELP)
        sys.exit(0)

    player = load_player()

    if args.command == "status":
        print(cmd_status(player))

    elif args.command == "record":
        print(cmd_record(player, args.action, args.quantity))

    elif args.command == "daily":
        print(cmd_daily(player))

    elif args.command == "add":
        print(cmd_add_stat(player, args.stat, args.amount))

    elif args.command == "summon":
        print(cmd_summon(player, args.type))

    elif args.command == "army":
        print(cmd_army(player))

    elif args.command == "legion":
        print(cmd_legion(player, args.scale))

    elif args.command == "achievements":
        print(cmd_achievements(player))

    elif args.command == "analyze":
        print(cmd_analyze(player, args.path))

    elif args.command == "plan":
        print(cmd_plan(player, args.task))

    elif args.command == "monitor":
        print(cmd_monitor(player))

    elif args.command == "deploy":
        print(cmd_deploy(player, args.minutes))

    elif args.command == "archive":
        print(cmd_archive(player, args.topic))

    elif args.command == "reset":
        reset_player()
        print("✅ 角色已重置")

    elif args.command == "scan-git":
        print(cmd_scan_git(player, args.path))

    elif args.command == "setup-git":
        print(cmd_setup_git(player, args.path))

    elif args.command == "remove-git":
        print(cmd_remove_git(player, args.path))

    elif args.command == "git-status":
        print(cmd_git_status(player))

    elif args.command == "github":
        print(cmd_github(player, args.action, args.repo))

    elif args.command == "scan-files":
        print(cmd_scan_files(player, args.path))

    elif args.command == "file-status":
        print(cmd_file_status(player))

    elif args.command == "dungeons":
        print(cmd_dungeons(player))

    elif args.command == "enter-dungeon":
        print(cmd_enter_dungeon(player, args.dungeon_id))

    elif args.command == "boss-list":
        print(cmd_boss_list(player))

    elif args.command == "shop":
        print(cmd_shop(player, args.category))

    elif args.command == "buy":
        print(cmd_buy(player, args.item_id))

    elif args.command == "sell":
        print(cmd_sell(player, args.item_id))

    elif args.command == "inventory":
        print(cmd_inventory(player))

    elif args.command == "health-import":
        print(cmd_health_import(player, args.file))

    elif args.command == "health-manual":
        print(cmd_health_manual(player, args.steps, args.exercise, args.sleep))

    elif args.command == "health-summary":
        print(cmd_health_summary(player, args.days))

    elif args.command == "reading-import":
        print(cmd_reading_import(player, args.file))

    elif args.command == "reading-manual":
        print(cmd_reading_manual(player, args.minutes, args.pages, args.book))

    elif args.command == "reading-summary":
        print(cmd_reading_summary(player, args.days))

    elif args.command == "browser-import":
        print(cmd_browser_import(player, args.file))

    elif args.command == "browser-manual":
        print(cmd_browser_manual(player, args.site, args.minutes))

    elif args.command == "browser-summary":
        print(cmd_browser_summary(player, args.days))

    elif args.command == "integrations":
        print(cmd_integrations(player, args.action, args.target))

    elif args.command == "season":
        print(cmd_season(player, args.action, getattr(args, "season_id", None)))

    elif args.command == "report":
        print(cmd_report(player, args.period, args.offset))

    elif args.command == "insights":
        print(cmd_insights(player))

    elif args.command == "reminders":
        print(cmd_reminders(player))

    elif args.command == "guild-create":
        print(cmd_guild_create(player, args.name))
    elif args.command == "guild-join":
        print(cmd_guild_join(player, args.guild_id))
    elif args.command == "guild-leave":
        print(cmd_guild_leave(player))
    elif args.command == "guild-info":
        print(cmd_guild_info(player, getattr(args, "guild_id", None)))
    elif args.command == "guild-list":
        print(cmd_guild_list(player))
    elif args.command == "guild-task":
        print(cmd_guild_task(player, args.action, getattr(args, "guild_id", None)))
    elif args.command == "guild-battle":
        print(cmd_guild_battle(player, args.action, getattr(args, "guild_id", None)))
    elif args.command == "guild-members":
        print(cmd_guild_members(player, getattr(args, "guild_id", None)))
    elif args.command == "guild-promote":
        print(cmd_guild_promote(player, args.target, getattr(args, "guild_id", None)))
    elif args.command == "guild-kick":
        print(cmd_guild_kick(player, args.target, getattr(args, "guild_id", None)))
    elif args.command == "guild-transfer":
        print(cmd_guild_transfer(player, args.new_leader, getattr(args, "guild_id", None)))
    elif args.command == "guild-disband":
        print(cmd_guild_disband(player, args.guild_id))

    elif args.command == "web":
        from web_server import run_server
        run_server(args.port)


if __name__ == "__main__":
    main()

