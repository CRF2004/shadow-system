"""
Shadow CLI - Guild System
Guild creation, joining, tasks, contributions, battles, and rankings.
"""

import json
import random
import time
from datetime import datetime, date
from pathlib import Path

import config
from engine import add_exp, calculate_power

# ── Guild Storage ──────────────────────────────────────────────────────────

def _guilds_dir() -> Path:
    d = config.STATE_DIR / "guilds"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _guild_file(guild_id: str) -> Path:
    return _guilds_dir() / f"{guild_id}.json"

# ── Guild Constants ────────────────────────────────────────────────────────

MAX_MEMBERS = 20
MIN_MEMBERS_FOR_BATTLE = 3
GUILD_BATTLE_COOLDOWN_HOURS = 24
GUILD_TASK_INTERVAL_HOURS = 12

GUILD_RANK_TITLES = [
    (100000, "传说公会"),
    (50000,  "史诗公会"),
    (20000,  "精英公会"),
    (10000,  "高级公会"),
    (5000,   "中级公会"),
    (1000,   "初级公会"),
    (0,      "见习公会"),
]

# Guild battle boss templates
GUILD_BOSSES = [
    {"id": "gb_slime",   "name": "腐蚀史莱姆王",   "hp": 5000,  "attack": 100, "defense": 30,  "reward_exp": 3000, "reward_gold": 500},
    {"id": "gb_golem",   "name": "暗影石巨人",    "hp": 8000,  "attack": 150, "defense": 80,  "reward_exp": 5000, "reward_gold": 800},
    {"id": "gb_lich",    "name": "亡灵大君",       "hp": 12000, "attack": 200, "defense": 60,  "reward_exp": 8000, "reward_gold": 1200},
    {"id": "gb_dragon",  "name": "古龙·尼德霍格",  "hp": 20000, "attack": 300, "defense": 120, "reward_exp": 15000, "reward_gold": 2500},
    {"id": "gb_monarch", "name": "暗影君主分身",   "hp": 35000, "attack": 450, "defense": 200, "reward_exp": 25000, "reward_gold": 5000},
]

# Guild task templates
GUILD_TASK_TEMPLATES = [
    {"id": "gt_commit",   "name": "代码贡献",       "desc": "全公会累计提交 10 次 commit", "type": "commit", "target": 10, "reward_pct": 0.3},
    {"id": "gt_coding",   "name": "攻坚代码",       "desc": "全公会累计完成 500 行代码",   "type": "coding", "target": 500, "reward_pct": 0.5},
    {"id": "gt_read",     "name": "知识共享",       "desc": "全公会累计阅读 20 页",         "type": "reading", "target": 20, "reward_pct": 0.2},
    {"id": "gt_exercise", "name": "体能训练",       "desc": "全公会累计运动 120 分钟",      "type": "exercise", "target": 120, "reward_pct": 0.2},
    {"id": "gt_vocab",    "name": "词汇冲刺",       "desc": "全公会累计背 500 个单词",      "type": "vocabulary", "target": 500, "reward_pct": 0.3},
]


def _get_guild_rank(contribution: int) -> str:
    for min_val, title in GUILD_RANK_TITLES:
        if contribution >= min_val:
            return title
    return "见习公会"

def create_guild(player: dict, guild_name: str, leader_username: str) -> dict:
    """Create a new guild. Returns result dict."""
    guild_name = guild_name.strip()
    if not guild_name:
        return {"success": False, "message": "公会名不能为空"}
    if len(guild_name) > 20:
        return {"success": False, "message": "公会名最多 20 个字符"}

    guild_id = guild_name.lower().replace(" ", "_")
    if _guild_file(guild_id).exists():
        return {"success": False, "message": f"公会已存在: {guild_name}"}

    now = datetime.now().isoformat()
    guild = {
        "id": guild_id,
        "name": guild_name,
        "leader": leader_username,
        "contribution": 0,
        "rank": "见习公会",
        "createdAt": now,
        "members": [
            {
                "username": leader_username,
                "role": "leader",
                "joinedAt": now,
                "contribution": 0,
                "lastContribution": None,
            }
        ],
        "activeTask": None,
        "activeBoss": None,
        "battleHistory": [],
        "taskHistory": [],
        "logs": [],
    }

    _guild_file(guild_id).write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "success": True,
        "guild": {
            "id": guild_id,
            "name": guild_name,
            "members": 1,
            "rank": "见习公会",
        },
        "message": f"公会 [{guild_name}] 创建成功！你是第一位成员。",
    }


def disband_guild(guild_id: str, username: str) -> dict:
    """Disband a guild (leader only)."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))
    if guild["leader"] != username:
        return {"success": False, "message": "只有公会领导者可以解散公会"}

    guild_file.unlink()
    return {
        "success": True,
        "message": f"公会 [{guild['name']}] 已解散",
    }


def join_guild(guild_id: str, username: str, player: dict) -> dict:
    """Join an existing guild."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))

    # Check if already a member
    for m in guild["members"]:
        if m["username"] == username:
            return {"success": False, "message": "你已经是该公会成员"}

    if len(guild["members"]) >= MAX_MEMBERS:
        return {"success": False, "message": f"公会已满（上限 {MAX_MEMBERS} 人）"}

    now = datetime.now().isoformat()
    guild["members"].append({
        "username": username,
        "role": "member",
        "joinedAt": now,
        "contribution": 0,
        "lastContribution": None,
    })

    guild_file.write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "success": True,
        "message": f"已加入公会 [{guild['name']}]！",
    }


def leave_guild(guild_id: str, username: str) -> dict:
    """Leave a guild."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))

    # Leader cannot leave
    if guild["leader"] == username:
        return {"success": False, "message": "领导者无法离开公会，请解散或转让"}

    members = [m for m in guild["members"] if m["username"] != username]
    if len(members) == len(guild["members"]):
        return {"success": False, "message": "你不在该公会中"}

    guild["members"] = members
    guild_file.write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "success": True,
        "message": f"已离开公会 [{guild['name']}]",
    }


def get_guild(guild_id: str) -> dict | None:
    """Get guild data."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return None
    return json.loads(guild_file.read_text(encoding="utf-8"))


def get_user_guild(username: str) -> dict | None:
    """Find which guild a user belongs to."""
    for f in _guilds_dir().glob("*.json"):
        try:
            guild = json.loads(f.read_text(encoding="utf-8"))
            for m in guild["members"]:
                if m["username"] == username:
                    return guild
        except (json.JSONDecodeError, KeyError):
            continue
    return None


def list_guilds() -> list[dict]:
    """List all guilds."""
    guilds = []
    for f in _guilds_dir().glob("*.json"):
        try:
            guild = json.loads(f.read_text(encoding="utf-8"))
            guilds.append({
                "id": guild["id"],
                "name": guild["name"],
                "leader": guild["leader"],
                "members": len(guild["members"]),
                "maxMembers": MAX_MEMBERS,
                "contribution": guild["contribution"],
                "rank": guild["rank"],
                "activeTask": guild.get("activeTask") is not None,
                "activeBoss": guild.get("activeBoss") is not None,
                "createdAt": guild["createdAt"],
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return sorted(guilds, key=lambda g: g["contribution"], reverse=True)


def transfer_leadership(guild_id: str, username: str, new_leader: str) -> dict:
    """Transfer guild leadership."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))
    if guild["leader"] != username:
        return {"success": False, "message": "只有领导者可以转让"}

    new_leader = new_leader.lower().strip()
    member_found = False
    for m in guild["members"]:
        if m["username"] == username:
            m["role"] = "member"
        if m["username"] == new_leader:
            m["role"] = "leader"
            member_found = True

    if not member_found:
        return {"success": False, "message": f"成员 {new_leader} 不在公会中"}

    guild["leader"] = new_leader
    guild_file.write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"success": True, "message": f"已将领导权转让给 {new_leader}"}


def kick_member(guild_id: str, username: str, target: str) -> dict:
    """Kick a member (leader/officer only)."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))
    actor = None
    for m in guild["members"]:
        if m["username"] == username:
            actor = m
            break

    if not actor or actor["role"] not in ("leader", "officer"):
        return {"success": False, "message": "只有领导者或副手可以踢人"}

    if target == guild["leader"]:
        return {"success": False, "message": "不能踢出领导者"}

    members = [m for m in guild["members"] if m["username"] != target]
    if len(members) == len(guild["members"]):
        return {"success": False, "message": f"{target} 不在公会中"}

    guild["members"] = members
    guild_file.write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"success": True, "message": f"已将 {target} 移出公会"}


def promote_member(guild_id: str, username: str, target: str, role: str = "officer") -> dict:
    """Promote a member to officer."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))
    if guild["leader"] != username:
        return {"success": False, "message": "只有领导者可以任命"}

    for m in guild["members"]:
        if m["username"] == target:
            m["role"] = role
            guild_file.write_text(
                json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return {"success": True, "message": f"已任命 {target} 为副手"}

    return {"success": False, "message": f"{target} 不在公会中"}


# ── Guild Tasks ────────────────────────────────────────────────────────────

def start_guild_task(guild_id: str, username: str) -> dict:
    """Start a guild task (must not have active task)."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))
    if guild.get("activeTask"):
        return {"success": False, "message": "已有进行中的公会任务"}

    # Check cooldown
    if guild.get("taskHistory"):
        last_task = guild["taskHistory"][-1]
        last_time = datetime.fromisoformat(last_task["completedAt"])
        if (datetime.now() - last_time).total_seconds() < GUILD_TASK_INTERVAL_HOURS * 3600:
            return {"success": False, "message": f"公会任务冷却中（每 {GUILD_TASK_INTERVAL_HOURS} 小时一次）"}

    # Pick random task
    template = random.choice(GUILD_TASK_TEMPLATES)
    difficulty = random.choice(["C", "B", "A"])
    diff_mult = config.DIFFICULTY_MULTIPLIER.get(difficulty, 1.0)
    target = int(template["target"] * diff_mult)

    now = datetime.now().isoformat()
    task = {
        "templateId": template["id"],
        "name": template["name"],
        "desc": template["desc"],
        "type": template["type"],
        "target": target,
        "current": 0,
        "difficulty": difficulty,
        "rewardPct": template["reward_pct"],
        "startedAt": now,
        "members": {m["username"]: 0 for m in guild["members"]},
    }
    guild["activeTask"] = task

    guild_file.write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "success": True,
        "task": {
            "name": task["name"],
            "desc": task["desc"],
            "type": task["type"],
            "target": target,
            "current": 0,
            "difficulty": difficulty,
        },
        "message": f"公会任务开始: {task['name']} ({task['desc']})",
    }


def contribute_to_guild_task(guild_id: str, username: str, action_type: str, quantity: int) -> dict:
    """Contribute action progress to guild task."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))
    task = guild.get("activeTask")
    if not task:
        return {"success": False, "message": "当前没有进行中的公会任务"}

    if task["type"] != action_type:
        return {"success": False, "message": f"该行为不适用于当前任务 (需要 {task['type']})"}

    # Check if member
    member_found = False
    for m in guild["members"]:
        if m["username"] == username:
            member_found = True
            break
    if not member_found:
        return {"success": False, "message": "不是公会成员"}

    task["members"][username] = task["members"].get(username, 0) + quantity
    task["current"] += quantity

    completed = task["current"] >= task["target"]
    now = datetime.now().isoformat()

    result = {
        "progress": task["current"],
        "target": task["target"],
        "completed": completed,
        "yourContribution": task["members"].get(username, 0),
    }

    if completed:
        # Calculate rewards
        base_exp_reward = int(task["rewardPct"] * 5000)
        base_gold_reward = int(task["rewardPct"] * 1000)

        guild["contribution"] += base_exp_reward
        guild["rank"] = _get_guild_rank(guild["contribution"])

        task["completedAt"] = now
        guild["taskHistory"].append(task)
        guild["activeTask"] = None

        # Distribute rewards to contributing members
        member_rewards = {}
        total_contrib = sum(task["members"].values())
        for member, contrib in task["members"].items():
            if contrib > 0:
                share = contrib / total_contrib
                member_exp = int(base_exp_reward * share)
                member_gold = int(base_gold_reward * share)
                member_rewards[member] = {"exp": member_exp, "gold": member_gold}

        result["rewards"] = member_rewards
        result["message"] = f"🎉 公会任务完成！ [{guild['name']}] 贡献 +{base_exp_reward}"

    guild_file.write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


# ── Guild Boss Battles ─────────────────────────────────────────────────────

def start_guild_battle(guild_id: str, username: str) -> dict:
    """Start a guild boss battle."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))
    if guild.get("activeBoss"):
        return {"success": False, "message": "已有进行中的 Boss 战"}

    # Check member count
    member_count = len(guild["members"])
    if member_count < MIN_MEMBERS_FOR_BATTLE:
        return {"success": False, "message": f"至少需要 {MIN_MEMBERS_FOR_BATTLE} 名成员才能挑战 Boss（当前 {member_count} 人）"}

    # Check cooldown
    if guild.get("battleHistory"):
        last_battle = guild["battleHistory"][-1]
        last_time = datetime.fromisoformat(last_battle["endedAt"])
        if (datetime.now() - last_time).total_seconds() < GUILD_BATTLE_COOLDOWN_HOURS * 3600:
            return {"success": False, "message": f"Boss 战冷却中（每 {GUILD_BATTLE_COOLDOWN_HOURS} 小时一次）"}

    # Pick boss based on guild level
    avg_level = 1
    # We can't easily get all member levels without loading all players,
    # so use guild contribution as a proxy
    contribution = guild.get("contribution", 0)
    if contribution > 50000:
        boss_pool = GUILD_BOSSES[-3:]  # Top 3 hardest
    elif contribution > 10000:
        boss_pool = GUILD_BOSSES[-4:-1]  # Middle difficulty
    else:
        boss_pool = GUILD_BOSSES[:3]  # Easiest

    boss = random.choice(boss_pool)
    # Scale boss HP based on member count
    scaled_hp = int(boss["hp"] * (1 + member_count * 0.1))

    now = datetime.now().isoformat()
    active_boss = {
        "id": boss["id"],
        "name": boss["name"],
        "maxHp": scaled_hp,
        "currentHp": scaled_hp,
        "attack": boss["attack"],
        "defense": boss["defense"],
        "rewardExp": boss["reward_exp"],
        "rewardGold": boss["reward_gold"],
        "startedAt": now,
        "damageByMember": {},
    }
    guild["activeBoss"] = active_boss

    guild_file.write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "success": True,
        "boss": {
            "name": boss["name"],
            "hp": scaled_hp,
            "attack": boss["attack"],
            "defense": boss["defense"],
        },
        "message": f"⚔️ Boss 战开始: {boss['name']} (HP: {scaled_hp})",
    }


def deal_boss_damage(guild_id: str, username: str, action_type: str, quantity: int) -> dict:
    """Deal damage to active guild boss."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return {"success": False, "message": "公会不存在"}

    guild = json.loads(guild_file.read_text(encoding="utf-8"))
    boss = guild.get("activeBoss")
    if not boss:
        return {"success": False, "message": "当前没有进行中的 Boss 战"}

    # Check if member
    member_found = False
    for m in guild["members"]:
        if m["username"] == username:
            member_found = True
            break
    if not member_found:
        return {"success": False, "message": "不是公会成员"}

    # Calculate damage based on action
    # Different action types deal different amounts of damage
    damage_multipliers = {
        "commit": 200,
        "coding": 100,
        "exercise": 150,
        "reading": 50,
        "vocabulary": 30,
    }
    base_damage = damage_multipliers.get(action_type, 50)
    raw_damage = base_damage * quantity

    # Apply defense reduction
    defense = boss.get("defense", 0)
    actual_damage = max(1, raw_damage - defense // 10)

    boss["currentHp"] -= actual_damage
    boss["damageByMember"][username] = boss["damageByMember"].get(username, 0) + actual_damage

    defeated = boss["currentHp"] <= 0
    if defeated:
        boss["currentHp"] = 0

    result = {
        "damage": actual_damage,
        "bossHp": max(0, boss["currentHp"]),
        "bossMaxHp": boss["maxHp"],
        "defeated": defeated,
        "yourDamage": boss["damageByMember"].get(username, 0),
    }

    if defeated:
        now = datetime.now().isoformat()
        guild["contribution"] += boss["rewardExp"] // 10
        guild["rank"] = _get_guild_rank(guild["contribution"])

        # Distribute rewards
        total_damage = sum(boss["damageByMember"].values())
        member_rewards = {}
        for member, dmg in boss["damageByMember"].items():
            share = dmg / total_damage if total_damage > 0 else 0
            member_exp = int(boss["rewardExp"] * share)
            member_gold = int(boss["rewardGold"] * share)
            member_rewards[member] = {"exp": member_exp, "gold": member_gold}

        boss["endedAt"] = now
        boss["result"] = "victory"
        guild["battleHistory"].append(boss)
        guild["activeBoss"] = None

        result["rewards"] = member_rewards
        result["message"] = f"🏆 Boss [{boss['name']}] 被击败！[{guild['name']}] 贡献 +{boss['rewardExp'] // 10}"

    guild_file.write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


# ── Guild Rankings ─────────────────────────────────────────────────────────

def get_guild_rankings() -> list[dict]:
    """Get ranked list of all guilds."""
    guilds = list_guilds()
    return guilds  # Already sorted by contribution descending


def get_member_rankings(guild_id: str) -> list[dict]:
    """Get member rankings within a guild."""
    guild = get_guild(guild_id)
    if not guild:
        return []

    rankings = []
    for m in guild["members"]:
        rankings.append({
            "username": m["username"],
            "role": m["role"],
            "contribution": m.get("contribution", 0),
            "joinedAt": m["joinedAt"],
            "lastContribution": m.get("lastContribution"),
        })

    return sorted(rankings, key=lambda r: r["contribution"], reverse=True)


# ── Guild Activity Log ─────────────────────────────────────────────────────

def add_guild_log(guild_id: str, message: str) -> bool:
    """Add a log entry to a guild."""
    guild_file = _guild_file(guild_id)
    if not guild_file.exists():
        return False

    guild = json.loads(guild_file.read_text(encoding="utf-8"))
    guild.setdefault("logs", [])
    guild["logs"].append({
        "message": message,
        "timestamp": datetime.now().isoformat(),
    })
    # Keep only last 100 entries
    guild["logs"] = guild["logs"][-100:]

    guild_file.write_text(
        json.dumps(guild, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return True
