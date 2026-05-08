"""
Shadow CLI - Dungeon System
限时挑战副本、Boss 战、难度分级。
"""

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import config
from engine import add_exp, check_achievements, get_exp_for_action
from state import load_player, save_player


# ── Dungeon Definitions ─────────────────────────────────────────────────

DUNGEONS = {
    "code_dungeon": {
        "id": "code_dungeon",
        "name": "代码地下城",
        "type": "daily",
        "description": "在限定时间内完成编码挑战",
        "difficulty_range": ("E", "A"),
        "tasks": [
            {"name": "修复一个 Bug", "type": "commit", "target": 2, "base_exp": 80, "time_limit": 60},
            {"name": "重构一段代码", "type": "coding", "target": 50, "base_exp": 100, "time_limit": 120},
            {"name": "编写单元测试", "type": "coding", "target": 30, "base_exp": 90, "time_limit": 90},
            {"name": "优化性能问题", "type": "coding", "target": 20, "base_exp": 120, "time_limit": 90},
        ],
    },
    "word_abyss": {
        "id": "word_abyss",
        "name": "单词深渊",
        "type": "weekly",
        "description": "积累大量词汇量挑战",
        "difficulty_range": ("D", "S"),
        "tasks": [
            {"name": "背诵 100 个单词", "type": "vocabulary", "target": 100, "base_exp": 100, "time_limit": 300},
            {"name": "背诵 200 个单词", "type": "vocabulary", "target": 200, "base_exp": 200, "time_limit": 600},
            {"name": "阅读英文文章 5 篇", "type": "reading", "target": 5, "base_exp": 80, "time_limit": 240},
        ],
    },
    "exercise_trial": {
        "id": "exercise_trial",
        "name": "运动试炼",
        "type": "daily",
        "description": "限时运动挑战",
        "difficulty_range": ("C", "S"),
        "tasks": [
            {"name": "跑步 30 分钟", "type": "exercise", "target": 30, "base_exp": 100, "time_limit": 1800},
            {"name": "运动 60 分钟", "type": "exercise", "target": 60, "base_exp": 180, "time_limit": 3600},
        ],
    },
    "project_raid": {
        "id": "project_raid",
        "name": "项目 RAID",
        "type": "boss",
        "description": "周期性高难度挑战 — Boss 战",
        "difficulty_range": ("S", "S"),
        "tasks": [
            {"name": "完成一个完整功能模块", "type": "coding", "target": 200, "base_exp": 500, "time_limit": 7200},
            {"name": "修复 5 个 Bug 并编写文档", "type": "commit", "target": 5, "base_exp": 400, "time_limit": 3600},
            {"name": "系统级重构", "type": "coding", "target": 300, "base_exp": 800, "time_limit": 10800},
        ],
    },
}

# ── Boss Definitions ─────────────────────────────────────────────────────

BOSSES = [
    {
        "id": "bug_king",
        "name": "Bug 之王",
        "hp": 100,
        "reward_exp": 300,
        "reward_gold": 200,
        "description": "消灭所有 Bug，证明你的SEN",
        "defeat_condition": "commit_count",
        "defeat_value": 10,
    },
    {
        "id": "code_golem",
        "name": "代码巨像",
        "hp": 200,
        "reward_exp": 500,
        "reward_gold": 400,
        "description": "在限定时间内输出大量代码",
        "defeat_condition": "total_exp",
        "defeat_value": 2000,
    },
    {
        "id": "streak_dragon",
        "name": "连击巨龙",
        "hp": 300,
        "reward_exp": 1000,
        "reward_gold": 800,
        "description": "连续打卡 21 天",
        "defeat_condition": "streak",
        "defeat_value": 21,
    },
]


def get_available_dungeons(player: dict) -> list[dict]:
    """Get dungeons available to the player based on level."""
    level = player["level"]
    available = []

    for d in DUNGEONS.values():
        # Daily dungeons always available
        if d["type"] in ("daily",):
            available.append(d)
        # Weekly dungeons available at level 10+
        elif d["type"] == "weekly" and level >= 10:
            available.append(d)
        # Boss raids available at level 30+
        elif d["type"] == "boss" and level >= 30:
            available.append(d)

    return available


def generate_dungeon_instance(dungeon_id: str, player: dict) -> dict:
    """Generate a dungeon instance for the player.

    Creates a timed challenge with randomized task selection.
    """
    dungeon = DUNGEONS.get(dungeon_id)
    if not dungeon:
        return {"success": False, "message": f"❌ 未知副本: {dungeon_id}"}

    # Pick difficulty based on player level
    player_level = player["level"]
    if player_level < 10:
        difficulty = "E"
    elif player_level < 20:
        difficulty = "D"
    elif player_level < 30:
        difficulty = "C"
    elif player_level < 50:
        difficulty = "B"
    else:
        difficulty = "A"

    # Select tasks — pick 2-3 random tasks from dungeon
    task_pool = dungeon["tasks"]
    num_tasks = min(3, len(task_pool))
    selected_tasks = random.sample(task_pool, num_tasks)

    # Scale base_exp by difficulty
    diff_mult = config.DIFFICULTY_MULTIPLIER.get(difficulty, 1.0)

    tasks = []
    total_reward = 0
    for t in selected_tasks:
        exp = int(t["base_exp"] * diff_mult)
        total_reward += exp
        tasks.append({
            "name": t["name"],
            "type": t["type"],
            "target": t["target"],
            "current": 0,
            "completed": False,
            "reward": exp,
        })

    instance = {
        "dungeon_id": dungeon_id,
        "dungeon_name": dungeon["name"],
        "difficulty": difficulty,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
        "tasks": tasks,
        "total_reward": total_reward,
        "completed": False,
        "failed": False,
    }

    # Save instance
    config.QUESTS_DIR.mkdir(parents=True, exist_ok=True)
    instance_id = f"dungeon_{dungeon_id}_{date.today().isoformat()}_{int(datetime.now().timestamp())}"
    instance_file = config.QUESTS_DIR / f"{instance_id}.json"
    with open(instance_file, "w", encoding="utf-8") as f:
        json.dump(instance, f, indent=2, ensure_ascii=False)

    instance["instance_id"] = instance_id

    # Grant entry EXP
    add_exp(player, 10)

    return {"success": True, "instance": instance, "entry_exp": 10}


def progress_dungeon(player: dict, action_type: str, quantity: int) -> dict:
    """Progress active dungeon tasks based on player action.

    Returns:
        dict with progress info and any completions.
    """
    # Find active dungeon instances
    active_instances = []
    if config.QUESTS_DIR.exists():
        for f in config.QUESTS_DIR.glob("dungeon_*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    inst = json.load(fh)
                if not inst.get("completed") and not inst.get("failed"):
                    # Check if not expired
                    expires = datetime.fromisoformat(inst["expires_at"])
                    if datetime.now() < expires:
                        inst["_file"] = str(f)
                        active_instances.append(inst)
            except (json.JSONDecodeError, OSError):
                continue

    if not active_instances:
        return {"progress": [], "completed": [], "all_done": False}

    result = {"progress": [], "completed": [], "all_done": False, "instances": []}

    for inst in active_instances:
        for task in inst["tasks"]:
            if task["type"] == action_type and not task["completed"]:
                old = task["current"]
                new = min(old + quantity, task["target"])
                task["current"] = new
                if new != old:
                    result["progress"].append({
                        "dungeon": inst["dungeon_name"],
                        "task": task["name"],
                        "old": old,
                        "new": new,
                    })
                if new >= task["target"]:
                    task["completed"] = True
                    result["completed"].append({
                        "dungeon": inst["dungeon_name"],
                        "task": task["name"],
                        "reward": task["reward"],
                    })

        # Check if all tasks done
        all_done = all(t["completed"] for t in inst["tasks"])
        if all_done and not inst["completed"]:
            inst["completed"] = True
            inst["completed_at"] = datetime.now().isoformat()
            result["all_done"] = True

        # Save updated instance
        if "_file" in inst:
            with open(inst["_file"], "w", encoding="utf-8") as fh:
                json.dump(inst, fh, indent=2, ensure_ascii=False)

        result["instances"].append(inst)

    return result


def claim_dungeon_reward(player: dict, completed_dungeons: list[dict]) -> list[str]:
    """Claim rewards for completed dungeons."""
    messages = []
    total_exp = 0
    total_gold = 0

    for d in completed_dungeons:
        exp = d.get("total_reward", 0)
        gold = exp // 5  # Gold = 20% of EXP
        total_exp += exp
        total_gold += gold

        levelup_msgs = add_exp(player, exp)
        messages.extend(levelup_msgs)

        # Check for boss-specific rewards
        if d.get("dungeon_id") == "project_raid":
            # Raid gives extra gold
            bonus_gold = total_gold // 2
            total_gold += bonus_gold
            messages.append(f"🏰 RAID 奖励: +{bonus_gold} 金币")

    player["gold"] = player.get("gold", 0) + total_gold

    if total_exp > 0:
        # Check achievements
        new_ach = check_achievements(player)
        for ach in new_ach:
            messages.append(f"🏆 成就解锁: {ach['name']} (+{ach['reward_exp']} EXP)")

    return messages


def get_active_bosses(player: dict) -> list[dict]:
    """Get bosses available to the player."""
    level = player["level"]
    available = []
    for boss in BOSSES:
        # Boss availability based on level
        if boss["id"] == "bug_king" and level >= 10:
            available.append(boss)
        elif boss["id"] == "code_golem" and level >= 20:
            available.append(boss)
        elif boss["id"] == "streak_dragon" and level >= 30:
            available.append(boss)
    return available


def check_boss_defeat(player: dict) -> list[dict]:
    """Check if any boss has been defeated based on player progress."""
    defeated = []
    existing = set(player.get("bosses_defeated", []))

    for boss in BOSSES:
        if boss["id"] in existing:
            continue

        defeated_by = False
        if boss["defeat_condition"] == "commit_count":
            defeated_by = player.get("commitCount", 0) >= boss["defeat_value"]
        elif boss["defeat_condition"] == "total_exp":
            defeated_by = player.get("totalExp", 0) >= boss["defeat_value"]
        elif boss["defeat_condition"] == "streak":
            defeated_by = player.get("streak", 0) >= boss["defeat_value"]

        if defeated_by:
            defeated.append(boss)
            existing.add(boss["id"])
            player.setdefault("bosses_defeated", []).append(boss["id"])
            add_exp(player, boss["reward_exp"])
            player["gold"] = player.get("gold", 0) + boss["reward_gold"]

    return defeated
