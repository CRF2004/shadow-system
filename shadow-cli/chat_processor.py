#!/usr/bin/env python3
"""
Shadow System - Chat Processor
OpenAI-compatible chat interface for the Shadow CLI game engine.

Maps natural language / slash commands to game actions and returns
roleplay-style responses in the "Shadow Monarch" voice.
"""

import json
import re
import time
import uuid
from datetime import datetime
from typing import Generator

# Engine functions (lazy import to avoid circular deps)
# These will be imported at runtime by the caller
_ENGINE_IMPORTS = None


def _get_engine():
    """Lazy-import engine functions."""
    global _ENGINE_IMPORTS
    if _ENGINE_IMPORTS is None:
        import engine
        from state import save_player
        _ENGINE_IMPORTS = {
            "add_exp": engine.add_exp,
            "calculate_power": engine.calculate_power,
            "get_title": engine.get_title,
            "allocate_stat": engine.allocate_stat,
            "apply_task_progress": engine.apply_task_progress,
            "claim_daily_reward": engine.claim_daily_reward,
            "summon_soldier": engine.summon_soldier,
            "summon_legion": engine.summon_legion,
            "check_achievements": engine.check_achievements,
            "get_achievement_status": engine.get_achievement_status,
            "generate_daily_tasks": engine.generate_daily_tasks,
            "get_exp_for_action": engine.get_exp_for_action,
            "save_player": save_player,
        }
    return _ENGINE_IMPORTS


# ── NPC Persona ────────────────────────────────────────────────────────────

PERSONA_PREFIX = "「暗影君主」"

PERSONA_GREETINGS = [
    "臣民，你的暗影之力在涌动。告诉我，今天有何行动？",
    "王，你的意志决定命运。汇报你的进展。",
    "暗影在注视着你。今日有何收获？",
]

PERSONA_LEVELUP = "⚡ 暗影之力涌动！你突破了界限！"
PERSONA_SUMMON = "🌑 暗影之门开启，新的战士加入你的军团。"
PERSONA_DUNGEON = "🗡️ 虚空裂隙在你面前展开。"
PERSONA_ACHIEVEMENT = "🏆 你的传说被刻入暗影之书。"
PERSONA_LOW_EXP = "⚠️ 你的暗影之力正在衰弱，需要更多训练。"
PERSONA_COMPLIANT = "遵命，王。"
PERSONA_CONFUSED = "暗影的意志模糊不清……能否再说一遍？"


# ── Command Registry ──────────────────────────────────────────────────────

# Slash commands → handler name
SLASH_COMMANDS = {
    "/status": "status",
    "/状态": "status",
    "/daily": "daily",
    "/每日任务": "daily",
    "/record": "record",
    "/打卡": "record",
    "/summon": "summon",
    "/召唤": "summon",
    "/army": "army",
    "/军队": "army",
    "/legion": "legion",
    "/军团": "legion",
    "/add": "allocate_stat",
    "/分配": "allocate_stat",
    "/achievements": "achievements",
    "/成就": "achievements",
    "/shop": "shop",
    "/商店": "shop",
    "/dungeon": "dungeon",
    "/副本": "dungeon",
    "/boss": "boss",
    "/boss战": "boss",
    "/inventory": "inventory",
    "/背包": "inventory",
    "/analyze": "analyze",
    "/分析": "analyze",
    "/plan": "plan",
    "/计划": "plan",
    "/monitor": "monitor",
    "/监控": "monitor",
    "/archive": "archive",
    "/归档": "archive",
    "/help": "help",
    "/帮助": "help",
    "/reset": "reset_tasks",
    "/刷新任务": "reset_tasks",
    "/scan-git": "scan_git",
    "/扫描git": "scan_git",
    "/scan-files": "scan_files",
    "/扫描文件": "scan_files",
    "/health": "health_summary",
    "/健康": "health_summary",
    "/reading": "reading_summary",
    "/阅读": "reading_summary",
}

# Keyword patterns → (action_type, default_amount)
NATURAL_PATTERNS = [
    (r"背了?\s*(\d+)\s*个?\s*单词",        ("vocabulary", 1)),
    (r"背了?\s*(\d+)\s*个?\s*词",          ("vocabulary", 1)),
    (r"学习了?\s*(\d+)\s*个?\s*单词",      ("vocabulary", 1)),
    (r"走了?\s*(\d+)\s*步",                 ("steps", 1)),
    (r"运动了?\s*(\d+)\s*分钟",             ("exercise", 1)),
    (r"跑了?\s*(\d+)\s*分钟",               ("exercise", 1)),
    (r"读了?\s*(\d+)\s*页",                ("reading_pages", 1)),
    (r"读了?\s*(\d+)\s*分钟",              ("reading_minutes", 1)),
    (r"写了?\s*(\d+)\s*行?\s*代码",        ("coding_lines", 1)),
    (r"写了?\s*(\d+)\s*行?\s*代码?",       ("coding_lines", 1)),
    (r"提交了?\s*(\d+)\s*次?\s*commit",    ("commit", 1)),
    (r"commit\s*(\d+)\s*次?",               ("commit", 1)),
    (r"睡了?\s*(\d+\.?\d*)\s*小时",        ("sleep_hours", 1)),
    (r"睡了?\s*(\d+\.?\d*)\s*小时",       ("sleep_hours", 1)),
]

# Fuzzy intent patterns
FUZZY_PATTERNS = {
    r"(我的|看看|显示|查看|查看一下|状态|属性|面板)": "status",
    r"(今日任务|每日任务|任务列表|日常任务|今日日程|今天的任务)": "daily",
    r"(召唤|summon|招兵)": "summon",
    r"(军团|legion|全军出击|全军)": "legion",
    r"(成就|成就列表|achievements|奖杯)": "achievements",
    r"(商店|shop|买|购买|商店列表)": "shop",
    r"(副本|dungeon|闯关)": "dungeon",
    r"(背包|inventory|装备|道具)": "inventory",
    r"(军队|army|士兵|我的士兵)": "army",
    r"(健康|health|步数|运动|睡眠)": "health_summary",
    r"(阅读|reading|读书|看书)": "reading_summary",
    r"(你好|早上好|晚上好|在吗|你好吗|hi|hello|hey)": "greeting",
    r"(怎么样|如何|最近|过得|进展)": "status",
    r"(帮助|help|怎么|怎么做|怎么用|指南|说明|命令)": "help",
    r"(睡了吗|睡了没|在忙吗|有空吗|忙吗|有空)": "greeting",
    r"(加油|冲|干|行动|开始|出发)": "greeting",
}


# ── Parse Functions ────────────────────────────────────────────────────────

def parse_message(text: str) -> dict:
    """
    Parse user chat message into an action dict.

    Priority: slash commands > natural patterns > fuzzy patterns > greeting/fallback

    Returns:
        {
            "action": str,           # action type
            "params": dict,          # action parameters
            "command": str|None,     # matched command/slash
            "raw": str,              # original text
        }
    """
    text = text.strip()
    result = {
        "action": "unknown",
        "params": {},
        "command": None,
        "raw": text,
    }

    if not text:
        return result

    # 1. Slash commands
    if text.startswith("/"):
        parts = text.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Direct mapping
        for pattern, action in SLASH_COMMANDS.items():
            if cmd == pattern.lower():
                result["action"] = action
                result["command"] = cmd
                result["params"] = _parse_slash_args(action, args)
                return result

        # Unknown slash command
        result["action"] = "unknown_command"
        result["params"] = {"command": cmd, "args": args}
        return result

    # 2. Natural language patterns (recording activities)
    for pattern, (action_type, per_unit) in NATURAL_PATTERNS:
        m = re.search(pattern, text)
        if m:
            amount = int(float(m.group(1)))
            result["action"] = "record"
            result["params"] = {
                "action_type": action_type,
                "amount": amount,
            }
            return result

    # 3. Fuzzy intent
    for pattern, intent in FUZZY_PATTERNS.items():
        if re.search(pattern, text):
            result["action"] = intent
            result["params"] = {}
            return result

    # 4. Default: try to record as free-form or fallback
    result["action"] = "freeform"
    result["params"] = {"text": text}
    return result


def _parse_slash_args(action: str, args: str) -> dict:
    """Parse arguments after a slash command."""
    parts = args.split() if args else []

    if action == "record" and len(parts) >= 2:
        return {"action_type": parts[0], "amount": int(parts[1])}
    elif action == "summon" and parts:
        return {"soldier_type": parts[0]}
    elif action == "allocate_stat" and len(parts) >= 2:
        return {"stat": parts[0], "amount": int(parts[1])}
    elif action == "legion" and parts:
        return {"size": parts[0]}
    elif action == "plan" and args:
        # Remove quotes
        task = args.strip('"').strip("'")
        return {"task": task}
    elif action == "archive" and args:
        topic = args.strip('"').strip("'")
        return {"topic": topic}
    elif action == "dungeon" and parts:
        return {"dungeon_type": parts[0]}
    elif action == "boss" and parts:
        return {"boss_name": parts[0]}
    elif action == "buy" and parts:
        return {"item_id": parts[0]}
    elif action == "sell" and parts:
        return {"item_id": parts[0], "quantity": int(parts[1]) if len(parts) > 1 else 1}
    return {}


# ── Response Formatter ─────────────────────────────────────────────────────

def format_status(player: dict) -> str:
    """Format player status as RPG-style text."""
    title = _get_engine()["get_title"](player["level"])
    power = _get_engine()["calculate_power"](player)
    stats = player.get("stats", {})
    progress_pct = round(100 * player["exp"] / max(player["expToNext"], 1))
    progress_bar = _make_bar(progress_pct, 20)

    lines = [
        f"╔══════════════════════════════════╗",
        f"║  🗡️ {player.get('name', 'Unknown')} — {title}                      ║",
        f"║  LV.{player['level']}  EXP: {player['exp']}/{player['expToNext']}    [{progress_bar}] ║",
        f"║  ⚡ 战力: {power:<14d}         ║",
        f"║  ❤️  HP: {player.get('hp', 100):<15d}  💎 MP: {player.get('mp', 100):<5d}  ║",
        f"║  💰 金币: {player.get('gold', 0):<14d}          ║",
        f"║  🔥 连续打卡: {player.get('streak', 0)} 天  🎯 属性点: {player.get('statPoints', 0):<3d}      ║",
        f"╠══════════════════════════════════╣",
        f"║  属性:                          ║",
        f"║  💪STR {stats.get('str', 0):3d}  🏃AGI {stats.get('agi', 0):3d}  👁️SEN {stats.get('sen', 0):3d}  ║",
        f"║  ❤️ VIT {stats.get('vit', 0):3d}  🧠INT {stats.get('int', 0):3d}  ⚡LUK {stats.get('luk', 0):3d}  ║",
        f"╚══════════════════════════════════╝",
    ]
    return "\n".join(lines)


def format_daily_tasks(tasks: list) -> str:
    """Format daily tasks as RPG-style text."""
    lines = [
        "📜 **今日暗影任务**",
        "",
    ]
    for i, task in enumerate(tasks[:5], 1):
        status_icon = "✅" if task.get("completed") else "⬜"
        diff_icon = {"E": "🟢", "D": "🔵", "C": "🟡", "B": "🟠", "A": "🔴", "S": "💀"}.get(
            task.get("difficulty", "E"), "⬜"
        )
        lines.append(f"{status_icon} {i}. {task.get('description', '???')} ({diff_icon}{task.get('difficulty', '?')})")
        if task.get("exp_reward"):
            lines[-1] += f" → +{task['exp_reward']} EXP"
    lines.append("")
    lines.append(f"💡 回复「完成任务 X」来提交任务进度")
    return "\n".join(lines)


def format_achievements(player: dict) -> str:
    """Format achievement status."""
    eng = _get_engine()
    all_status = eng["get_achievement_status"](player)
    unlocked = [a for a in all_status if a["unlocked"]]
    locked = [a for a in all_status if not a["unlocked"]]
    lines = [f"🏆 **成就列表** ({len(unlocked)}/{len(unlocked) + len(locked)} 已解锁)", ""]
    for ach in unlocked:
        lines.append(f"✅ {ach['name']} — {ach['description']}")
    if locked:
        lines.append("")
        lines.append("--- 未解锁 ---")
        for ach in locked[:5]:
            lines.append(f"🔒 {ach['name']} — {ach['description']}")
    return "\n".join(lines)


def format_army(player: dict) -> str:
    """Format soldier list."""
    soldiers = player.get("soldiers", [])
    if not soldiers:
        return "🌑 你的暗影军团空空如也……去召唤一些战士吧！"
    lines = [f"🌑 **暗影军团** ({len(soldiers)} 名战士)", ""]
    for s in soldiers:
        lines.append(f"  ⚔️ {s.get('name', '???')} ({s.get('type', '?')}) — LV.{s.get('level', 1)}")
    return "\n".join(lines)


def format_shop(player: dict) -> str:
    """Format shop items."""
    from shop import get_shop_items
    items = get_shop_items(player)
    lines = ["🏪 **暗影商店**", ""]
    if not items:
        lines.append("暂无可购买商品。")
    else:
        for item in items[:10]:
            price = item.get("price", 0)
            currency = item.get("price_type", "gold")
            icon = "💰" if currency == "gold" else "💎"
            cat = item.get("category", "")
            if cat:
                lines.append(f"  📦 [{cat}] {item['name']} — {icon}{price}")
            else:
                lines.append(f"  📦 {item['name']} — {icon}{price}")
    return "\n".join(lines)


def format_help() -> str:
    """Format help text."""
    return """📖 **暗影君主 · 命令指南**

**斜杠命令** (最快):
- `/status` 或 `/状态` — 查看角色状态
- `/daily` 或 `/每日任务` — 今日任务
- `/summon <类型>` — 召唤士兵 (explore/plan/dev/test/debug/review/doc)
- `/add <属性> <数量>` — 分配属性点 (str/agi/sen/vit/int)
- `/army` — 查看军队
- `/achievements` — 成就列表
- `/shop` — 商店
- `/dungeon` — 副本
- `/inventory` — 背包
- `/help` — 帮助

**自然语言** (直接说):
- 「背了50个单词」→ 记录单词
- 「运动30分钟」→ 记录运动
- 「走了10000步」→ 记录步数
- 「读了40页」→ 记录阅读
- 「写了500行代码」→ 记录编码

试试用自然语言描述你的行动！"""


# ── Execute Actions ────────────────────────────────────────────────────────

def execute_action(player: dict, action: str, params: dict) -> dict:
    """
    Execute a parsed action on the player state.

    Returns:
        {
            "response": str,    # formatted text response
            "level_up": bool,   # whether player leveled up
            "achievements": [], # new achievements
        }
    """
    eng = _get_engine()
    result = {"response": "", "level_up": False, "achievements": []}

    if action == "status":
        result["response"] = f"{PERSONA_PREFIX}\n\n{format_status(player)}"

    elif action == "daily":
        tasks = eng["generate_daily_tasks"](player)
        result["response"] = f"{PERSONA_PREFIX}\n\n{format_daily_tasks(tasks)}"

    elif action == "record":
        action_type = params.get("action_type", "")
        amount = params.get("amount", 0)
        exp_info = eng["get_exp_for_action"](action_type, amount, player.get("streak", 0), player.get("combo", 0), player)
        if exp_info <= 0:
            result["response"] = f"{PERSONA_PREFIX}\n\n⚠️ 无法识别行为: {action_type}。试试自然语言描述。"
            return result
        level_msgs = eng["add_exp"](player, exp_info)
        eng["save_player"](player)
        gold = exp_info // 10
        player["gold"] = player.get("gold", 0) + gold

        parts = [f"{PERSONA_PREFIX}\n\n"]
        parts.append(f"📝 记录: {action_type} × {amount}\n")
        parts.append(f"🌟 +{exp_info} EXP")
        parts.append(f"\n💰 +{gold} 金币")
        if level_msgs:
            parts.append(f"\n\n{PERSONA_LEVELUP}\n" + "\n".join(level_msgs))
            result["level_up"] = True
        parts.append(f"\n\n{format_status(player)}")
        result["response"] = "".join(parts)

        # Check achievements
        new_ach = eng["check_achievements"](player)
        if new_ach:
            result["achievements"] = new_ach
            ach_names = [a["name"] for a in new_ach]
            result["response"] += f"\n\n{PERSONA_ACHIEVEMENT}\n解锁: {', '.join(ach_names)}"

    elif action == "summon":
        soldier_type = params.get("soldier_type", None)
        result = eng["summon_soldier"](player, soldier_type)
        eng["save_player"](player)
        if result.get("success") and result.get("obtained"):
            s = result["soldier"]
            s_level = max(1, player["level"] // 10)
            result["response"] = (
                f"{PERSONA_PREFIX}\n\n{PERSONA_SUMMON}\n\n"
                f"⚔️ {s['name']} ({s['type']}) — LV.{s_level}\n"
                f"能力: {s.get('power', 1)}\n\n"
                f"{format_army(player)}"
            )
        elif result.get("success"):
            result["response"] = f"{PERSONA_PREFIX}\n\n{result.get('message', '召唤完成，但未获得士兵。')}"
        else:
            result["response"] = f"{PERSONA_PREFIX}\n\n{result.get('message', '暗影之力不足...')}"

    elif action == "army":
        result["response"] = f"{PERSONA_PREFIX}\n\n{format_army(player)}"

    elif action == "legion":
        size = params.get("size", "small")
        result = eng["summon_legion"](player, size)
        eng["save_player"](player)
        if result.get("success"):
            result["response"] = (
                f"{PERSONA_PREFIX}\n\n{PERSONA_SUMMON}\n\n"
                f"召唤了 {result.get('count', 0)} 名战士！\n\n"
                f"{format_army(player)}"
            )
        else:
            result["response"] = f"{PERSONA_PREFIX}\n\n{result.get('message', '暗影之力不足...')}"

    elif action == "allocate_stat":
        stat = params.get("stat", "")
        amount = params.get("amount", 1)
        err = eng["allocate_stat"](player, stat, amount)
        eng["save_player"](player)
        if err is None:
            result["response"] = (
                f"{PERSONA_PREFIX}\n\n✅ 属性分配成功！\n"
                f"{stat.upper()} +{amount}\n\n"
                f"{format_status(player)}"
            )
        else:
            result["response"] = f"{PERSONA_PREFIX}\n\n⚠️ {err}"

    elif action == "achievements":
        result["response"] = f"{PERSONA_PREFIX}\n\n{format_achievements(player)}"

    elif action == "shop":
        result["response"] = f"{PERSONA_PREFIX}\n\n{format_shop(player)}"

    elif action == "inventory":
        from shop import get_inventory
        inv = get_inventory(player)
        if not inv:
            result["response"] = f"{PERSONA_PREFIX}\n\n🎒 背包空空如也……"
        else:
            lines = [f"{PERSONA_PREFIX}\n\n🎒 **暗影背包** ({player.get('gold', 0)} 金币)", ""]
            for item in inv:
                lines.append(f"  📦 {item['name']} × {item.get('quantity', 1)}")
            result["response"] = "\n".join(lines)

    elif action == "health_summary":
        from integrations import get_health_summary
        summary = get_health_summary(player)
        lines = [f"{PERSONA_PREFIX}\n\n💚 **健康概览**", ""]
        lines.append(f"步数: {summary.get('total_steps', 0):,}")
        lines.append(f"运动: {summary.get('total_exercise_min', 0)} 分钟")
        lines.append(f"睡眠: {summary.get('total_sleep_hours', 0)} 小时")
        lines.append(f"获得 EXP: {summary.get('total_exp', 0)}")
        result["response"] = "\n".join(lines)

    elif action == "reading_summary":
        from integrations import get_reading_summary
        summary = get_reading_summary(player)
        lines = [f"{PERSONA_PREFIX}\n\n📚 **阅读概览**", ""]
        lines.append(f"时长: {summary.get('total_minutes', 0)} 分钟")
        lines.append(f"页数: {summary.get('total_pages', 0)}")
        lines.append(f"获得 EXP: {summary.get('total_exp', 0)}")
        result["response"] = "\n".join(lines)

    elif action == "dungeon":
        from dungeon import get_available_dungeons
        dungeons = get_available_dungeons(player)
        lines = [f"{PERSONA_PREFIX}\n\n{PERSONA_DUNGEON}\n"]
        lines.append("可进入的副本:")
        for d in dungeons[:5]:
            lines.append(f"  🗡️ {d['name']} — {d.get('description', '')} (奖励: {d.get('exp_reward', 0)} EXP)")
        result["response"] = "\n".join(lines)

    elif action == "boss":
        from dungeon import get_active_bosses
        bosses = get_active_bosses(player)
        if bosses:
            lines = [f"{PERSONA_PREFIX}\n\n💀 **Boss 战**", ""]
            for b in bosses:
                hp_bar = _make_bar(b.get("hp", 100), 15, max_val=b.get("max_hp", 100))
                lines.append(f"  💀 {b['name']} HP: [{hp_bar}] {b.get('hp', 0)}/{b.get('max_hp', 100)}")
            result["response"] = "\n".join(lines)
        else:
            result["response"] = f"{PERSONA_PREFIX}\n\n当前没有活跃的 Boss。"

    elif action == "greeting":
        import random
        greeting = random.choice(PERSONA_GREETINGS)
        result["response"] = f"{PERSONA_PREFIX}\n\n{greeting}\n\n{format_status(player)}"

    elif action == "help":
        result["response"] = format_help()

    elif action == "status":
        result["response"] = f"{PERSONA_PREFIX}\n\n{format_status(player)}"

    elif action == "unknown":
        result["response"] = f"{PERSONA_PREFIX}\n\n{PERSONA_CONFUSED}\n\n回复 `/help` 查看可用命令。"

    elif action == "freeform":
        # Try to interpret as a status check
        result["response"] = (
            f"{PERSONA_PREFIX}\n\n"
            f"「{params.get('text', '')}」\n\n"
            f"你的意志我收到了，但暗影的力量需要具体的行动。"
            f"试试说「背了50个单词」或「运动30分钟」来记录你的进展。\n\n"
            f"回复 `/help` 查看完整指南。"
        )

    else:
        result["response"] = (
            f"{PERSONA_PREFIX}\n\n"
            f"未知指令: {action}\n"
            f"回复 `/help` 查看可用命令。"
        )

    return result


# ── Utility ────────────────────────────────────────────────────────────────

def _make_bar(pct: int, width: int, max_val: int = 100) -> str:
    """Create a progress bar string."""
    filled = int(pct / max_val * width) if max_val > 0 else 0
    filled = min(filled, width)
    return "█" * filled + "░" * (width - filled)


# ── OpenAI Chat Completion Response Builders ───────────────────────────────

def build_chat_response(action_result: dict, model: str = "shadow-cli-v1") -> dict:
    """Build a non-streaming OpenAI-compatible chat completion response."""
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": action_result["response"],
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(action_result["response"]),
            "total_tokens": len(action_result["response"]),
        },
    }


def build_stream_chunk(content: str, model: str = "shadow-cli-v1") -> str:
    """Build a streaming chunk (SSE format)."""
    chunk = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": content} if content else {},
            "finish_reason": "stop" if not content else None,
        }],
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def stream_response(action_result: dict, model: str = "shadow-cli-v1") -> Generator[str, None, None]:
    """Generator that streams the response text in chunks."""
    # Opening chunk
    yield build_stream_chunk("", model)

    # Stream text in chunks of ~20 chars
    text = action_result["response"]
    chunk_size = 20
    for i in range(0, len(text), chunk_size):
        yield build_stream_chunk(text[i:i + chunk_size], model)

    # Final empty chunk to signal completion
    yield build_stream_chunk("", model)
    yield "data: [DONE]\n\n"
