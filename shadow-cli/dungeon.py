"""
Shadow CLI - Dungeon System
限时挑战副本、Boss 战、难度分级。

Dungeons are generated dynamically from the player's skill config.
If no skills configured, falls back to hardcoded defaults.
"""

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import config
from engine import add_exp, check_achievements, get_exp_for_action
from state import load_player, save_player


# ── Fallback Dungeons (used when player has no skillConfig) ─────────────

_FALLBACK_DUNGEONS = {
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

_FALLBACK_BOSSES = [
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


# ── Dynamic Dungeon Generation from Player Skills ───────────────────────

# Task templates per difficulty for skill-based dungeons
_SKILL_TASK_TEMPLATES = {
    "daily_easy": [
        {"name_fmt": "练习 {name} ({quantity}{unit})", "target_scale": 0.6, "base_exp": 20},
        {"name_fmt": "专注 {name} ({quantity}{unit})", "target_scale": 0.8, "base_exp": 30},
    ],
    "daily_hard": [
        {"name_fmt": "深度练习 {name} ({quantity}{unit})", "target_scale": 1.0, "base_exp": 50},
        {"name_fmt": "挑战 {name}极限 ({quantity}{unit})", "target_scale": 1.2, "base_exp": 70},
    ],
    "weekly": [
        {"name_fmt": "完成 {name} 训练计划 ({quantity}{unit})", "target_scale": 2.0, "base_exp": 100},
        {"name_fmt": "精通 {name} ({quantity}{unit})", "target_scale": 3.0, "base_exp": 150},
    ],
    "boss": [
        {"name_fmt": "{name} 终极挑战 ({quantity}{unit})", "target_scale": 5.0, "base_exp": 300},
        {"name_fmt": "{name} 大师之路", "target_scale": 8.0, "base_exp": 500},
    ],
}

# Dungeon type suffixes
_DUNGEON_SUFFIXES = {
    "daily": "副本",
    "weekly": "试炼",
    "boss": "深渊",
}

# Dungeon name prefixes for common skill categories
_CATEGORY_PREFIXES = {
    "学习": "学海",
    "创作": "艺术",
    "身体": "体魄",
    "心智": "心灵",
    "音乐": "音律",
    "技能": "修行",
}


def _get_dungeon_name(skills: list[dict], dtype: str) -> str:
    """Generate a dungeon name from the skills it contains."""
    if len(skills) == 1:
        sk = skills[0]
        prefix = _CATEGORY_PREFIXES.get(sk.get("category", ""), "")
        name = sk.get("name", "未知")
        suffix = _DUNGEON_SUFFIXES.get(dtype, "副本")
        if prefix:
            return f"{prefix}{name}{suffix}"
        return f"{name}{suffix}"
    # Multi-skill dungeon
    names = [sk.get("name", "") for sk in skills[:2]]
    return f"{' + '.join(names)}试炼"


def _generate_skill_tasks(skill: dict, template_key: str) -> list[dict]:
    """Generate dungeon tasks from a single skill using task templates."""
    templates = _SKILL_TASK_TEMPLATES.get(template_key, [])
    tasks = []
    daily_target = skill.get("daily_target", 100)
    unit = skill.get("unit", "次")
    name = skill.get("name", "未知")
    exp_per_unit = skill.get("exp_per_unit", 1)
    skill_id = skill.get("id", name)

    for t in templates:
        target = max(1, int(daily_target * t["target_scale"]))
        task_name = t["name_fmt"].format(name=name, quantity=target, unit=unit)
        tasks.append({
            "name": task_name,
            "type": skill_id,
            "target": target,
            "base_exp": t["base_exp"],
            "time_limit": 3600,  # 1 hour per task
        })

    return tasks


def _generate_daily_dungeons(skills: list[dict]) -> list[dict]:
    """Generate daily dungeons from player skills.

    If <=3 skills: one dungeon per skill (skill-specific dungeon).
    If >3 skills: one mixed dungeon containing tasks from multiple skills.
    """
    dungeons = []

    if len(skills) <= 3:
        # One dungeon per skill
        for sk in skills:
            tasks = _generate_skill_tasks(sk, "daily_easy")
            # Add one harder task
            tasks.extend(_generate_skill_tasks(sk, "daily_hard")[:1])
            dungeons.append({
                "id": f"skill_daily_{sk.get('id', 'unknown')}",
                "name": _get_dungeon_name([sk], "daily"),
                "type": "daily",
                "description": f"今日 {sk.get('name', '')} 修炼",
                "difficulty_range": ("E", "A"),
                "tasks": tasks,
            })
    else:
        # Mixed dungeon — pick top 3 skills
        top_skills = skills[:3]
        all_tasks = []
        for sk in top_skills:
            all_tasks.extend(_generate_skill_tasks(sk, "daily_easy")[:1])
            all_tasks.extend(_generate_skill_tasks(sk, "daily_hard")[:1])
        dungeons.append({
            "id": "skill_mixed_daily",
            "name": _get_dungeon_name(top_skills, "daily"),
            "type": "daily",
            "description": "综合修炼挑战",
            "difficulty_range": ("E", "A"),
            "tasks": all_tasks[:4],  # Cap at 4 tasks
        })

    return dungeons


def _generate_weekly_dungeons(skills: list[dict]) -> list[dict]:
    """Generate weekly dungeons from player skills."""
    if not skills:
        return []

    all_tasks = []
    for sk in skills[:3]:  # Use up to 3 skills
        all_tasks.extend(_generate_skill_tasks(sk, "weekly")[:1])

    return [{
        "id": "skill_weekly",
        "name": _get_dungeon_name(skills[:2], "weekly"),
        "type": "weekly",
        "description": "每周深度修炼挑战",
        "difficulty_range": ("D", "S"),
        "tasks": all_tasks[:3],
    }]


def _generate_boss_raid(skills: list[dict]) -> list[dict]:
    """Generate boss raid dungeon from player skills."""
    if not skills:
        return []

    all_tasks = []
    for sk in skills[:2]:  # Top 2 skills for boss raid
        all_tasks.extend(_generate_skill_tasks(sk, "boss")[:1])

    return [{
        "id": "skill_boss_raid",
        "name": _get_dungeon_name(skills[:2], "boss"),
        "type": "boss",
        "description": "终极技能挑战",
        "difficulty_range": ("S", "S"),
        "tasks": all_tasks,
    }]


def _generate_skill_bosses(skills: list[dict]) -> list[dict]:
    """Generate skill-based bosses from player skills."""
    bosses = []
    for i, sk in enumerate(skills):
        name = sk.get("name", "未知")
        icon = sk.get("icon", "⭐")
        hp = 100 * (i + 1)
        reward_exp = 300 * (i + 1)
        reward_gold = 200 * (i + 1)
        bosses.append({
            "id": f"skill_boss_{sk.get('id', 'unknown')}",
            "name": f"{icon} {name}守护者",
            "hp": hp,
            "reward_exp": reward_exp,
            "reward_gold": reward_gold,
            "description": f"完成 {name} 修炼来击败它",
            "defeat_condition": "skill_progress",
            "defeat_skill_id": sk.get("id", ""),
            "defeat_value": sk.get("daily_target", 100) * 7,  # 1 week of daily goals
        })

    # Always include streak boss (global)
    bosses.append({
        "id": "streak_dragon",
        "name": "连击巨龙",
        "hp": 300,
        "reward_exp": 1000,
        "reward_gold": 800,
        "description": "连续打卡 21 天",
        "defeat_condition": "streak",
        "defeat_value": 21,
    })

    return bosses


def get_player_skills(player: dict) -> list[dict]:
    """Get player's configured skills, or empty list."""
    return player.get("skillConfig", {}).get("skills", [])


# ── Dungeon Generation (skill-based or fallback) ────────────────────────

def get_available_dungeons(player: dict) -> list[dict]:
    """Get dungeons available to the player based on level and skills."""
    level = player["level"]
    skills = get_player_skills(player)

    if not skills:
        # Fallback to hardcoded dungeons
        available = []
        for d in _FALLBACK_DUNGEONS.values():
            if d["type"] in ("daily",):
                available.append(d)
            elif d["type"] == "weekly" and level >= 10:
                available.append(d)
            elif d["type"] == "boss" and level >= 30:
                available.append(d)
        return available

    # Skill-based dungeons
    available = []
    available.extend(_generate_daily_dungeons(skills))
    if level >= 10:
        available.extend(_generate_weekly_dungeons(skills))
    if level >= 30:
        available.extend(_generate_boss_raid(skills))

    return available


def generate_dungeon_instance(dungeon_id: str, player: dict) -> dict:
    """Generate a dungeon instance for the player.

    Creates a timed challenge with randomized task selection.
    """
    skills = get_player_skills(player)

    # Find the dungeon definition
    if skills:
        all_dungeons = _generate_daily_dungeons(skills)
        if player["level"] >= 10:
            all_dungeons.extend(_generate_weekly_dungeons(skills))
        if player["level"] >= 30:
            all_dungeons.extend(_generate_boss_raid(skills))
        dungeon = next((d for d in all_dungeons if d["id"] == dungeon_id), None)
    else:
        dungeon = _FALLBACK_DUNGEONS.get(dungeon_id)

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
        if d.get("dungeon_id") == "project_raid" or d.get("dungeon_id") == "skill_boss_raid":
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
    skills = get_player_skills(player)

    if not skills:
        # Fallback to hardcoded bosses
        available = []
        for boss in _FALLBACK_BOSSES:
            if boss["id"] == "bug_king" and level >= 10:
                available.append(boss)
            elif boss["id"] == "code_golem" and level >= 20:
                available.append(boss)
            elif boss["id"] == "streak_dragon" and level >= 30:
                available.append(boss)
        return available

    # Skill-based bosses
    bosses = _generate_skill_bosses(skills)
    available = []
    for boss in bosses:
        # Skill bosses available at level 5+
        if boss["defeat_condition"] == "skill_progress" and level >= 5:
            available.append(boss)
        elif boss["id"] == "streak_dragon" and level >= 30:
            available.append(boss)

    return available


def check_boss_defeat(player: dict) -> list[dict]:
    """Check if any boss has been defeated based on player progress."""
    defeated = []
    existing = set(player.get("bosses_defeated", []))

    for boss in get_active_bosses(player):
        if boss["id"] in existing:
            continue

        defeated_by = False
        condition = boss.get("defeat_condition", "")

        if condition == "commit_count":
            defeated_by = player.get("commitCount", 0) >= boss["defeat_value"]
        elif condition == "total_exp":
            defeated_by = player.get("totalExp", 0) >= boss["defeat_value"]
        elif condition == "streak":
            defeated_by = player.get("streak", 0) >= boss["defeat_value"]
        elif condition == "skill_progress":
            # Check if player has logged enough of the skill
            skill_id = boss.get("defeat_skill_id", "")
            daily = player.get("dailyProgress", {})
            # Sum up total logged for this skill across all time
            # For simplicity, use totalExp as a proxy
            defeated_by = player.get("totalExp", 0) >= boss["defeat_value"]

        if defeated_by:
            defeated.append(boss)
            existing.add(boss["id"])
            player.setdefault("bosses_defeated", []).append(boss["id"])
            add_exp(player, boss["reward_exp"])
            player["gold"] = player.get("gold", 0) + boss["reward_gold"]

    return defeated
