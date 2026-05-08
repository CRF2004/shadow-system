#!/usr/bin/env python3
"""
Shadow CLI - 暗影君主系统 v0.2.0
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
    exp = get_exp_for_action(action_type, quantity, streak, combo)

    if exp <= 0:
        return f"❌ 未知行为类型: {action_type}\n有效: commit, coding, vocabulary, exercise, reading"

    # Track commit count
    if action_type == "commit":
        player["commitCount"] = player.get("commitCount", 0) + quantity

    # Apply task progress
    task_result = apply_task_progress(player, action_type, quantity)

    # Add EXP
    levelup_msgs = add_exp(player, exp)

    # Check achievements
    new_achievements = check_achievements(player)
    ach_msgs = []
    for ach in new_achievements:
        ach_msgs.append(f"🏆 成就解锁: {ach['name']} — {ach['description']} (+{ach['reward_exp']} EXP, +{ach['reward_gold']} 金币)")

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

    if levelup_msgs:
        result += "\n" + "\n".join(levelup_msgs)
    if ach_msgs:
        result += "\n" + "\n".join(ach_msgs)

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


if __name__ == "__main__":
    main()
