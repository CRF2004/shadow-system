"""
Shadow CLI - Skill Configuration Module
Handles dynamic skill definitions, templates, and LLM-based config generation.

Usage:
    from skill_config import get_builtin_templates, get_template, generate_config
    templates = get_builtin_templates()
    config = generate_config("我想背英语单词")  # LLM or fallback
"""

import json
import os
import random
from datetime import date
from pathlib import Path
from typing import Optional

import config


# ── Built-in Templates ────────────────────────────────────────────────────

BUILTIN_TEMPLATES = [
    {
        "id": "vocabulary",
        "name": "背单词",
        "category": "学习",
        "unit": "个",
        "icon": "📚",
        "exp_formula": "linear",
        "exp_per_unit": 1,
        "daily_cap": 150,
        "daily_target": 50,
    },
    {
        "id": "coding",
        "name": "写代码",
        "category": "开发",
        "unit": "行",
        "icon": "💻",
        "exp_formula": "linear",
        "exp_per_unit": 0.1,
        "daily_cap": 200,
        "daily_target": 100,
    },
    {
        "id": "exercise",
        "name": "运动",
        "category": "健康",
        "unit": "分钟",
        "icon": "🏃",
        "exp_formula": "linear",
        "exp_per_unit": 2,
        "daily_cap": 200,
        "daily_target": 30,
    },
    {
        "id": "reading",
        "name": "阅读",
        "category": "学习",
        "unit": "页",
        "icon": "📖",
        "exp_formula": "linear",
        "exp_per_unit": 1,
        "daily_cap": 150,
        "daily_target": 30,
    },
    {
        "id": "commit",
        "name": "提交代码",
        "category": "开发",
        "unit": "次",
        "icon": "🔀",
        "exp_formula": "linear",
        "exp_per_unit": 50,
        "daily_cap": 250,
        "daily_target": 3,
    },
    # Extended templates for user discovery
    {
        "id": "english_speaking",
        "name": "英语口语",
        "category": "学习",
        "unit": "分钟",
        "icon": "🗣️",
        "exp_formula": "linear",
        "exp_per_unit": 2,
        "daily_cap": 120,
        "daily_target": 20,
    },
    {
        "id": "running",
        "name": "跑步",
        "category": "健康",
        "unit": "公里",
        "icon": "🏃‍♂️",
        "exp_formula": "linear",
        "exp_per_unit": 10,
        "daily_cap": 100,
        "daily_target": 5,
    },
    {
        "id": "guitar",
        "name": "吉他",
        "category": "音乐",
        "unit": "分钟",
        "icon": "🎸",
        "exp_formula": "linear",
        "exp_per_unit": 2,
        "daily_cap": 120,
        "daily_target": 30,
    },
    {
        "id": "piano",
        "name": "钢琴",
        "category": "音乐",
        "unit": "分钟",
        "icon": "🎹",
        "exp_formula": "linear",
        "exp_per_unit": 2,
        "daily_cap": 120,
        "daily_target": 30,
    },
    {
        "id": "drawing",
        "name": "绘画",
        "category": "艺术",
        "unit": "分钟",
        "icon": "🎨",
        "exp_formula": "linear",
        "exp_per_unit": 2,
        "daily_cap": 120,
        "daily_target": 30,
    },
    {
        "id": "writing",
        "name": "写作",
        "category": "创作",
        "unit": "字",
        "icon": "✍️",
        "exp_formula": "linear",
        "exp_per_unit": 0.05,
        "daily_cap": 150,
        "daily_target": 500,
    },
    {
        "id": "meditation",
        "name": "冥想",
        "category": "健康",
        "unit": "分钟",
        "icon": "🧘",
        "exp_formula": "linear",
        "exp_per_unit": 3,
        "daily_cap": 150,
        "daily_target": 15,
    },
    {
        "id": "swimming",
        "name": "游泳",
        "category": "健康",
        "unit": "分钟",
        "icon": "🏊",
        "exp_formula": "linear",
        "exp_per_unit": 3,
        "daily_cap": 200,
        "daily_target": 30,
    },
    {
        "id": "yoga",
        "name": "瑜伽",
        "category": "健康",
        "unit": "分钟",
        "icon": "🧘‍♀️",
        "exp_formula": "linear",
        "exp_per_unit": 2,
        "daily_cap": 150,
        "daily_target": 30,
    },
    {
        "id": "math",
        "name": "数学练习",
        "category": "学习",
        "unit": "题",
        "icon": "🔢",
        "exp_formula": "linear",
        "exp_per_unit": 5,
        "daily_cap": 150,
        "daily_target": 10,
    },
    {
        "id": "cooking",
        "name": "烹饪",
        "category": "生活",
        "unit": "次",
        "icon": "🍳",
        "exp_formula": "linear",
        "exp_per_unit": 15,
        "daily_cap": 100,
        "daily_target": 2,
    },
]

# ── Template Database (User-generated) ────────────────────────────────────

def _get_templates_file() -> Path:
    """Get path to user-generated templates file."""
    return config.STATE_DIR / "skill_templates.json"


def load_user_templates() -> list[dict]:
    """Load user-generated templates from disk."""
    f = _get_templates_file()
    if f.exists():
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            return data.get("templates", [])
        except (json.JSONDecodeError, KeyError):
            pass
    return []


def save_user_template(template: dict) -> None:
    """Save a user-generated template to disk."""
    f = _get_templates_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    templates = load_user_templates()
    # Avoid duplicates
    if not any(t["id"] == template["id"] for t in templates):
        templates.append(template)
    with open(f, "w", encoding="utf-8") as fp:
        json.dump({"templates": templates}, fp, indent=2, ensure_ascii=False)


def get_all_templates() -> list[dict]:
    """Get all templates (built-in + user-generated)."""
    return BUILTIN_TEMPLATES + load_user_templates()


def get_template(skill_id: str) -> Optional[dict]:
    """Get a template by ID."""
    for t in get_all_templates():
        if t["id"] == skill_id:
            return t
    return None


def get_categories() -> list[dict]:
    """Get available skill categories."""
    return [
        {"id": "学习", "name": "学习", "icon": "📚"},
        {"id": "开发", "name": "开发", "icon": "💻"},
        {"id": "健康", "name": "健康", "icon": "💪"},
        {"id": "音乐", "name": "音乐", "icon": "🎵"},
        {"id": "艺术", "name": "艺术", "icon": "🎨"},
        {"id": "创作", "name": "创作", "icon": "✍️"},
        {"id": "生活", "name": "生活", "icon": "🌿"},
        {"id": "其他", "name": "其他", "icon": "⭐"},
    ]


# ── Keyword Matching (Fallback) ───────────────────────────────────────────

KEYWORD_MAP = {
    # vocabulary
    "单词": "vocabulary", "word": "vocabulary", "vocab": "vocabulary", "英语": "vocabulary",
    "背词": "vocabulary", "生字": "vocabulary", "词汇": "vocabulary",
    # coding
    "代码": "coding", "coding": "coding", "编程": "coding", "program": "coding",
    "写码": "coding", "开发": "coding", "写程序": "coding",
    # exercise
    "运动": "exercise", "exercise": "exercise", "健身": "exercise",
    " workout": "exercise", "锻炼": "exercise", "训练": "exercise",
    # reading
    "阅读": "reading", "read": "reading", "读书": "reading", "看书": "reading",
    "书籍": "reading", "文献": "reading",
    # commit
    "提交": "commit", "commit": "commit", "git": "commit", "push": "commit",
    # english_speaking
    "口语": "english_speaking", "speaking": "english_speaking",
    # running
    "跑步": "running", "run": "running", "慢跑": "running", "jog": "running",
    # guitar
    "吉他": "guitar", "guitar": "guitar",
    # piano
    "钢琴": "piano", "piano": "piano",
    # drawing
    "绘画": "drawing", "draw": "drawing", "画画": "drawing", "素描": "drawing",
    # writing
    "写作": "writing", "write": "writing", "写文章": "writing", "日记": "writing",
    # meditation
    "冥想": "meditation", "meditation": "meditation", "正念": "meditation",
    # swimming
    "游泳": "swimming", "swimming": "swimming",
    # yoga
    "瑜伽": "yoga", "yoga": "yoga",
    # math
    "数学": "math", "math": "math", "做题": "math", "刷题": "math",
    # cooking
    "烹饪": "cooking", "cooking": "cooking", "做饭": "cooking", "做菜": "cooking",
}


def match_by_keywords(description: str) -> Optional[dict]:
    """Try to match a description to a built-in template via keywords."""
    desc = description.strip()
    for keyword, template_id in KEYWORD_MAP.items():
        if keyword in desc:
            t = get_template(template_id)
            if t:
                return t
    return None


def match_fuzzy(description: str) -> Optional[dict]:
    """Fuzzy match: try individual words."""
    words = description.split()
    best_match = None
    best_len = 0
    for word in words:
        t = match_by_keywords(word)
        if t and len(word) > best_len:
            best_match = t
            best_len = len(word)
    return best_match


# ── LLM Config Generation (Optional) ──────────────────────────────────────

def _get_llm_config() -> Optional[dict]:
    """Get LLM API config from environment variables."""
    base_url = os.environ.get("SHADOW_LLM_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("SHADOW_LLM_API_KEY", "")
    model = os.environ.get("SHADOW_LLM_MODEL", "qwen-turbo")

    if not base_url or not api_key:
        return None

    return {"base_url": base_url, "api_key": api_key, "model": model}


def _call_llm(prompt: str) -> Optional[str]:
    """Call LLM API, return response text or None."""
    llm = _get_llm_config()
    if not llm:
        return None

    try:
        import urllib.request
        url = llm["base_url"]
        # Ensure path ends with chat completions
        if "/chat/completions" not in url:
            url = url.rstrip("/") + "/chat/completions"

        payload = json.dumps({
            "model": llm["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 500,
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {llm['api_key']}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except Exception:
        return None


def _parse_llm_response(text: str) -> Optional[dict]:
    """Parse LLM JSON response into skill config."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        import re
        match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
    return None


PROMPT_SKILL_CONFIG = """你是一个游戏化学习系统的技能配置助手。根据用户的描述，生成一个技能配置JSON。

要求输出严格JSON格式，不要包含其他文字，不要使用markdown代码块。字段如下：
- id: 英文唯一标识符（小写+下划线）
- name: 技能中文名
- category: 分类（学习/开发/健康/音乐/艺术/创作/生活/其他）
- unit: 计量单位（个/分钟/公里/页/题/次/行/字等）
- icon: 一个emoji图标
- exp_formula: 固定为"linear"
- exp_per_unit: 每个单位获得的经验值（数字，合理范围0.1-50）
- daily_cap: 每日经验上限（数字，合理范围50-300）
- daily_target: 推荐的每日目标值（数字，根据单位量级合理设置）

示例：
用户输入：我想背英语单词
输出：{{"id":"english_vocab","name":"背英语单词","category":"学习","unit":"个","icon":"🔤","exp_formula":"linear","exp_per_unit":1,"daily_cap":150,"daily_target":50}}

用户输入：我想练习吉他
输出：{{"id":"guitar","name":"吉他练习","category":"音乐","unit":"分钟","icon":"🎸","exp_formula":"linear","exp_per_unit":2,"daily_cap":120,"daily_target":30}}

用户输入：我想每天跑步
输出：{{"id":"running","name":"跑步","category":"健康","unit":"公里","icon":"🏃‍♂️","exp_formula":"linear","exp_per_unit":10,"daily_cap":100,"daily_target":5}}

现在请根据用户描述生成配置：%s"""


def generate_config_from_llm(description: str) -> Optional[dict]:
    """Generate skill config from description using LLM."""
    prompt = PROMPT_SKILL_CONFIG % description
    response = _call_llm(prompt)
    if not response:
        return None
    return _parse_llm_response(response)


# ── Main Config Generation ────────────────────────────────────────────────

def generate_config(description: str) -> dict:
    """
    Generate a skill config from a description.
    Tries: LLM → keyword match → fuzzy match → generic fallback.
    """
    # 1. Try LLM
    llm_config = generate_config_from_llm(description)
    if llm_config:
        # Validate required fields
        required = ["id", "name", "category", "unit", "icon", "exp_formula", "exp_per_unit", "daily_cap", "daily_target"]
        if all(k in llm_config for k in required):
            llm_config["id"] = llm_config["id"].lower().replace(" ", "_")
            return llm_config

    # 2. Try keyword match
    matched = match_by_keywords(description) or match_fuzzy(description)
    if matched:
        cfg = dict(matched)
        # If description differs from template name, create a variant
        if description.strip().lower() != matched["name"].lower() and len(description.strip()) > 2:
            cfg["id"] = description.strip().lower().replace(" ", "_")[:30]
            cfg["name"] = description.strip()
        return cfg

    # 3. Generic fallback
    return {
        "id": description.strip().lower().replace(" ", "_")[:30],
        "name": description.strip(),
        "category": "其他",
        "unit": "次",
        "icon": "⭐",
        "exp_formula": "linear",
        "exp_per_unit": 5,
        "daily_cap": 100,
        "daily_target": 5,
    }


# ── Batch Config Generation (Onboarding) ──────────────────────────────────

def generate_skill_configs(descriptions: list[str]) -> list[dict]:
    """Generate configs for multiple skill descriptions."""
    configs = []
    seen_ids = set()
    for desc in descriptions:
        if not desc.strip():
            continue
        cfg = generate_config(desc.strip())
        # Ensure unique ID
        base_id = cfg["id"]
        counter = 1
        while cfg["id"] in seen_ids:
            cfg["id"] = f"{base_id}_{counter}"
            counter += 1
        seen_ids.add(cfg["id"])
        configs.append(cfg)
    return configs


# ── Preset Onboarding Templates ────────────────────────────────────────────
# Quick-select packs for users who don't want to type

ONBOARDING_PRESETS = [
    {
        "id": "developer",
        "name": "🧑‍💻 程序员套餐",
        "description": "写代码 + 提交 + 阅读",
        "skills": ["写代码", "提交代码", "技术阅读"],
    },
    {
        "id": "student",
        "name": "📚 学生套餐",
        "description": "背单词 + 刷题 + 阅读",
        "skills": ["背单词", "数学练习", "阅读"],
    },
    {
        "id": "fitness",
        "name": "💪 健身套餐",
        "description": "跑步 + 运动 + 冥想",
        "skills": ["跑步", "运动", "冥想"],
    },
    {
        "id": "music",
        "name": "🎵 音乐套餐",
        "description": "吉他 + 钢琴",
        "skills": ["吉他", "钢琴"],
    },
    {
        "id": "balanced",
        "name": "⚖️ 全面发展套餐",
        "description": "编码 + 运动 + 阅读 + 冥想",
        "skills": ["写代码", "跑步", "阅读", "冥想"],
    },
    {
        "id": "artist",
        "name": "🎨 艺术家套餐",
        "description": "绘画 + 写作",
        "skills": ["绘画", "写作"],
    },
]


def get_presets() -> list[dict]:
    """Get onboarding presets."""
    return ONBOARDING_PRESETS


# ── Daily Task Generation (Skill-based) ──────────────────────────────────

def generate_skill_daily_tasks(player: dict) -> list[dict]:
    """Generate daily tasks from player's configured skills (replaces hardcoded DAILY_TASKS)."""
    today = date.today().isoformat()
    tasks = []

    skill_config = player.get("skillConfig", {})
    skills = skill_config.get("skills", [])

    if not skills:
        return []

    for skill in skills:
        skill_id = skill["id"]
        target = skill.get("daily_target", 5)
        # Scale reward with player level
        player_level = player.get("level", 1)
        base_reward = max(20, int(target * skill.get("exp_per_unit", 1) * 0.5))
        difficulty_map = {1: "E", 5: "D", 10: "C", 20: "B", 40: "A"}
        difficulty = "D"
        for lvl, diff in sorted(difficulty_map.items(), reverse=True):
            if player_level >= lvl:
                difficulty = diff
                break

        tasks.append({
            "id": f"daily_{skill_id}",
            "name": f"{skill.get('icon', '⭐')} {skill['name']}",
            "type": skill_id,
            "target": target,
            "reward": base_reward,
            "difficulty": difficulty,
            "status": "pending",
            "current": 0,
        })

    return tasks


def generate_skill_emergency_task(player: dict) -> Optional[dict]:
    """Generate a random emergency task from player's skills."""
    import random

    skill_config = player.get("skillConfig", {})
    skills = skill_config.get("skills", [])
    if not skills:
        return None

    skill = random.choice(skills)
    skill_id = skill["id"]
    target = int(skill.get("daily_target", 5) * random.uniform(1.5, 2.5))
    base_reward = max(30, int(target * skill.get("exp_per_unit", 1) * 0.8))
    player_level = player.get("level", 1)
    difficulty = "C"
    if player_level >= 20:
        difficulty = "B"
    if player_level >= 40:
        difficulty = "A"

    return {
        "id": f"emergency_{skill_id}",
        "name": f"⚡ {skill['name']} (紧急挑战)",
        "type": skill_id,
        "target": target,
        "reward": base_reward,
        "difficulty": difficulty,
        "status": "pending",
        "current": 0,
    }


def get_exp_for_skill(skill: dict, quantity: int) -> int:
    """Calculate EXP for a skill action using the skill's config."""
    formula = skill.get("exp_formula", "linear")
    per_unit = skill.get("exp_per_unit", 1)
    daily_cap = skill.get("daily_cap", 150)

    if formula == "linear":
        exp = int(quantity * per_unit)
    else:
        exp = int(quantity * per_unit)

    return min(exp, daily_cap)
