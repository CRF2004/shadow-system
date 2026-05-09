"""
Shadow CLI - Core Game Engine
EXP calculation, leveling, title mapping, stat allocation, achievements, soldiers.
"""

import random
from datetime import date

import config


def exp_to_next(level: int) -> int:
    """Calculate EXP needed to reach the next level.

    Formula: expToNext = 100 * 1.5^(level - 1)
    """
    return int(config.BASE_EXP * (config.EXP_MULTIPLIER ** (level - 1)))


def get_title(level: int) -> str:
    """Get rank title based on level."""
    for min_level, title in config.TITLES:
        if level >= min_level:
            return title
    return "E 级猎人"


def add_exp(player: dict, amount: int) -> list[str]:
    """Add EXP to player and handle leveling.

    Returns a list of level-up messages (may be empty).
    """
    messages = []
    player["exp"] += amount
    player["totalExp"] = player.get("totalExp", 0) + amount

    while player["exp"] >= player["expToNext"]:
        player["exp"] -= player["expToNext"]
        player["level"] += 1
        player["expToNext"] = exp_to_next(player["level"])
        player["statPoints"] += config.STAT_POINTS_PER_LEVEL
        player["hp"] = config.MAX_HP
        player["mp"] = config.MAX_MP
        title = get_title(player["level"])
        messages.append(f"🎉 升级！LV.{player['level'] - 1} → LV.{player['level']} ({title})")

    return messages


def calculate_power(player: dict) -> int:
    """Calculate total combat power."""
    stats_sum = sum(player["stats"].values())
    level_bonus = player["level"] * 10
    soldiers_bonus = len(player.get("soldiers", [])) * 5
    return stats_sum + level_bonus + soldiers_bonus


def allocate_stat(player: dict, stat_key: str, amount: int) -> str | None:
    """Allocate stat points. Returns error message or None on success."""
    if stat_key not in config.STAT_FULL_NAMES:
        return f"❌ 无效属性: {stat_key}\n有效: str, agi, sen, vit, int"
    if amount <= 0:
        return "❌ 数量必须大于 0"
    if player["statPoints"] < amount:
        return f"❌ 属性点不足 (需要 {amount}, 剩余 {player['statPoints']})"

    full_name = config.STAT_FULL_NAMES[stat_key]
    player["statPoints"] -= amount
    player["stats"][full_name] += amount
    return None


def get_streak_bonus(streak: int) -> float:
    """Calculate streak EXP bonus multiplier."""
    return 1.0 + (streak * config.EXP_REWARDS["streak_bonus_pct"])


def get_combo_bonus(combo: int) -> float:
    """Calculate combo EXP bonus multiplier."""
    return 1.0 + (combo * config.EXP_REWARDS["combo_pct"])


def get_exp_for_action(action_type: str, quantity: int, streak: int = 0, combo: int = 0, player: dict = None) -> int:
    """Calculate EXP reward for a given action.

    If player has skill-based config, uses skill's exp_per_unit.
    Falls back to hardcoded EXP_REWARDS.
    """
    # Try skill-based EXP first
    if player:
        skill_config = player.get("skillConfig", {})
        skills = skill_config.get("skills", [])
        for skill in skills:
            if skill["id"] == action_type:
                from skill_config import get_exp_for_skill
                base = get_exp_for_skill(skill, quantity)
                streak_mult = get_streak_bonus(streak)
                combo_mult = get_combo_bonus(combo)
                return int(base * streak_mult * combo_mult)

    # Fallback: hardcoded EXP_REWARDS
    base = config.EXP_REWARDS.get(action_type, 0)

    # Special handling for different action types
    if action_type == "coding_line" and quantity > 0:
        base = quantity / 100.0 * config.EXP_REWARDS["coding_100"]
    elif action_type == "exercise" and quantity > 0:
        base = quantity * config.EXP_REWARDS["exercise_minute"]
    elif action_type == "vocabulary" and quantity > 0:
        base = quantity * config.EXP_REWARDS["vocabulary"]
    elif action_type == "reading" and quantity > 0:
        base = quantity * config.EXP_REWARDS["reading_page"]
    elif action_type == "commit" and quantity > 0:
        base = min(quantity, 5) * config.EXP_REWARDS["commit"]
    elif action_type in config.EXP_REWARDS and quantity == 0:
        # Use base value for zero quantity
        pass

    # Apply streak bonus
    streak_mult = get_streak_bonus(streak)
    # Apply combo bonus
    combo_mult = get_combo_bonus(combo)
    return int(base * streak_mult * combo_mult)


# ── Task System ─────────────────────────────────────────────────────────

def generate_daily_tasks(player: dict) -> list[dict]:
    """Generate today's daily tasks from player skills or fallback to hardcoded.

    If player has skillConfig with skills, generates tasks from those.
    Otherwise falls back to hardcoded DAILY_TASKS + EMERGENCY_TASKS.
    """
    today = date.today().isoformat()

    # Check for skill-based configuration
    skill_config = player.get("skillConfig", {})
    skills = skill_config.get("skills", [])
    if skills:
        from skill_config import generate_skill_daily_tasks, generate_skill_emergency_task
        tasks = generate_skill_daily_tasks(player)
        emergency = generate_skill_emergency_task(player)
        if emergency:
            tasks.append(emergency)
        return tasks

    # Fallback: hardcoded tasks
    tasks = []

    # 4 fixed tasks
    for t in config.DAILY_TASKS:
        tasks.append({
            "id": t["id"],
            "name": t["name"],
            "type": t["type"],
            "target": t["target"],
            "reward": t["reward"],
            "difficulty": t["difficulty"],
            "status": "pending",
            "current": 0,
        })

    # 1 random emergency task (seeded by day for consistency)
    day_seed = date.today().toordinal()
    emergency = random.Random(day_seed).choice(config.EMERGENCY_TASKS)
    tasks.append({
        "id": emergency["id"],
        "name": f"⚡ {emergency['name']}",
        "type": emergency["type"],
        "target": emergency["target"],
        "reward": emergency["reward"],
        "difficulty": emergency["difficulty"],
        "status": "pending",
        "current": 0,
    })

    return tasks


def apply_task_progress(player: dict, action_type: str, quantity: int) -> dict:
    """Apply action progress to daily tasks.

    Returns:
        dict with:
        - progress: list of (task_id, old_current, new_current)
        - completed: list of task_ids newly completed
        - all_done: bool
    """
    today = date.today().isoformat()
    daily = player.get("dailyProgress", {})

    # If it's a new day, reset tasks
    if daily.get("date") != today:
        tasks = generate_daily_tasks(player)
        daily = {"date": today, "tasks": {}}
        for t in tasks:
            daily["tasks"][t["id"]] = {
                **t,
                "current": 0,
                "status": "pending",
            }
        player["dailyProgress"] = daily

    result = {"progress": [], "completed": [], "all_done": False}

    # Find matching tasks for this action type
    for task_id, task in daily.get("tasks", {}).items():
        if task["type"] == action_type:
            old_current = task["current"]
            new_current = min(old_current + quantity, task["target"])
            if new_current != old_current:
                task["current"] = new_current
                if task["status"] != "completed":
                    task["status"] = "active"
                if new_current >= task["target"] and task["status"] != "completed":
                    task["status"] = "completed"
                    result["completed"].append(task_id)
                result["progress"].append((task_id, old_current, new_current))

    # Check if all tasks are done
    all_tasks = daily.get("tasks", {})
    if all_tasks and all(t["status"] == "completed" for t in all_tasks.values()):
        result["all_done"] = True

    player["dailyProgress"] = daily
    return result


def claim_daily_reward(player: dict, total_reward: int) -> list[str]:
    """Claim daily completion reward. Returns list of messages."""
    messages = []
    streak = player.get("streak", 0)
    streak += 1
    player["streak"] = streak

    combo = player.get("combo", 0)
    combo += 1
    player["combo"] = combo

    # 20% streak bonus on daily reward
    bonus = int(total_reward * 0.2)
    total_with_bonus = total_reward + bonus

    levelup_msgs = add_exp(player, total_with_bonus)
    messages.extend(levelup_msgs)

    # Gold reward: 10 per completed task
    tasks_completed = player.get("dailyProgress", {}).get("tasks", {})
    gold_earned = sum(10 for t in tasks_completed.values() if t.get("status") == "completed")
    player["gold"] = player.get("gold", 0) + gold_earned
    player["totalGoldEarned"] = player.get("totalGoldEarned", 0) + gold_earned

    # Reset daily for next day
    player["dailyProgress"] = {}

    return messages


def reset_combo(player: dict) -> None:
    """Reset combo counter on missed day."""
    player["combo"] = 0


# ── Soldier System ──────────────────────────────────────────────────────

def summon_soldier(player: dict, soldier_type: str | None = None) -> dict:
    """Summon a soldier. Returns result dict with messages and success flag."""
    if soldier_type:
        # Summon specific type
        soldier_info = next((s for s in config.SOLDIER_TYPES if s["type"] == soldier_type), None)
        if not soldier_info:
            return {"success": False, "message": f"❌ 未知士兵类型: {soldier_type}"}
        mp_cost = soldier_info["mp_cost"]
    else:
        # Random summon — pick from all types
        soldier_info = random.choice(config.SOLDIER_TYPES)
        mp_cost = soldier_info["mp_cost"]

    if player.get("mp", 0) < mp_cost:
        return {
            "success": False,
            "message": f"⚠️ MP 不足\n需要: {mp_cost} MP\n当前: {player.get('mp', 0)} MP",
        }

    player["mp"] -= mp_cost

    # EXP for summoning
    add_exp(player, 15)

    # Check if soldier is obtained
    obtained = random.random() < config.SOLDIER_DROP_CHANCE
    if obtained:
        player.setdefault("soldiers", []).append({
            "name": soldier_info["name"],
            "type": soldier_info["type"],
            "level": max(1, player["level"] // 10),
            "exp": 0,
            "obtainedAt": date.today().isoformat(),
        })
        return {
            "success": True,
            "obtained": True,
            "soldier": soldier_info,
            "mp_cost": mp_cost,
            "message": f"🎉 获得暗影士兵: {soldier_info['name']}\n消耗: {mp_cost} MP | +15 EXP",
        }

    return {
        "success": True,
        "obtained": False,
        "soldier": soldier_info,
        "mp_cost": mp_cost,
        "message": f"召唤: {soldier_info['name']} [{soldier_info['type']}]\n消耗: {mp_cost} MP\n+15 EXP\n未获得士兵，下次努力！",
    }


def summon_legion(player: dict, scale: str = "medium") -> dict:
    """Summon a legion of soldiers. Returns result dict."""
    scale_config = config.LEGION_SCALES.get(scale, config.LEGION_SCALES["medium"])
    mp_cost = scale_config["mp"]
    count = scale_config["count"]

    if player.get("mp", 0) < mp_cost:
        return {
            "success": False,
            "message": f"⚠️ MP 不足\n需要: {mp_cost} MP\n当前: {player.get('mp', 0)} MP",
        }

    player["mp"] -= mp_cost
    add_exp(player, count * 10)

    soldiers = []
    soldiers_display = []
    for i in range(count):
        soldier_info = config.SOLDIER_TYPES[i % len(config.SOLDIER_TYPES)]
        obtained = random.random() < config.SOLDIER_DROP_CHANCE
        if obtained:
            player.setdefault("soldiers", []).append({
                "name": soldier_info["name"],
                "type": soldier_info["type"],
                "level": max(1, player["level"] // 10),
                "exp": 0,
                "obtainedAt": date.today().isoformat(),
            })
            soldiers.append(soldier_info)

        soldiers_display.append(f"  • {soldier_info['name']} [{soldier_info['type']}]")

    obtained_names = [s["name"] for s in soldiers]
    message = f"""规模: {scale_config['name']}
消耗: {mp_cost} MP
出征: {count} 名单位
获得士兵: {len(obtained_names)} 名"""
    if obtained_names:
        message += "\n🎉 " + ", ".join(obtained_names)

    return {
        "success": True,
        "mp_cost": mp_cost,
        "soldiers_obtained": len(obtained_names),
        "message": message,
    }


# ── Achievement System ──────────────────────────────────────────────────

def check_achievements(player: dict) -> list[dict]:
    """Check all achievement conditions. Returns list of newly unlocked achievements."""
    unlocked = []
    existing = set(player.get("achievements", []))

    for ach in config.ACHIEVEMENTS:
        if ach["id"] in existing:
            continue

        met = False
        if ach["condition_type"] == "total_exp":
            met = player.get("totalExp", 0) >= ach["condition_value"]
        elif ach["condition_type"] == "level":
            met = player["level"] >= ach["condition_value"]
        elif ach["condition_type"] == "streak":
            met = player.get("streak", 0) >= ach["condition_value"]
        elif ach["condition_type"] == "soldier_count":
            met = len(player.get("soldiers", [])) >= ach["condition_value"]
        elif ach["condition_type"] == "commit_count":
            met = player.get("commitCount", 0) >= ach["condition_value"]
        elif ach["condition_type"] == "bosses_defeated":
            met = len(player.get("bosses_defeated", [])) >= ach["condition_value"]
        elif ach["condition_type"] == "guild_joined":
            met = player.get("guildJoined", False)
        elif ach["condition_type"] == "guild_created":
            met = player.get("guildCreated", False)
        elif ach["condition_type"] == "guild_tasks_completed":
            met = player.get("guildTasksCompleted", 0) >= ach["condition_value"]
        elif ach["condition_type"] == "guild_bosses_defeated":
            met = player.get("guildBossesDefeated", 0) >= ach["condition_value"]
        elif ach["condition_type"] == "total_gold":
            met = player.get("totalGoldEarned", 0) >= ach["condition_value"]

        if met:
            unlocked.append(ach)

    # Apply rewards
    for ach in unlocked:
        player.setdefault("achievements", []).append(ach["id"])
        add_exp(player, ach["reward_exp"])
        player["gold"] = player.get("gold", 0) + ach["reward_gold"]
        player["totalGoldEarned"] = player.get("totalGoldEarned", 0) + ach["reward_gold"]

    return unlocked


def get_achievement_status(player: dict) -> list[dict]:
    """Return all achievements with their completion status."""
    existing = set(player.get("achievements", []))
    status = []
    for ach in config.ACHIEVEMENTS:
        unlocked = ach["id"] in existing
        status.append({
            "id": ach["id"],
            "name": ach["name"],
            "description": ach["description"],
            "unlocked": unlocked,
            "reward_exp": ach["reward_exp"],
            "reward_gold": ach["reward_gold"],
        })
    return status
