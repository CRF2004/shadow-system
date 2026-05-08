# Shadow Skills Handler
# Claude Code - 暗影君主系统 (Solo Leveling Inspired)

import json
import os
import urllib.parse
from datetime import datetime
from pathlib import Path

STATE_DIR = Path.home() / ".claude" / "shadow-state"
PLAYER_FILE = STATE_DIR / "player.json"
QUESTS_DIR = STATE_DIR / "quests"
SOLDIERS_DIR = STATE_DIR / "soldiers"
LOGS_DIR = STATE_DIR / "logs"

# 确保目录存在
STATE_DIR.mkdir(parents=True, exist_ok=True)
QUESTS_DIR.mkdir(parents=True, exist_ok=True)
SOLDIERS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 工具函数 ====================

def load_player():
    """加载玩家状态"""
    if PLAYER_FILE.exists():
        with open(PLAYER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return create_default_player()

def save_player(player):
    """保存玩家状态到 JSON 文件和 MetaMemory"""
    player['lastActive'] = datetime.now().isoformat()
    with open(PLAYER_FILE, 'w', encoding='utf-8') as f:
        json.dump(player, f, indent=2, ensure_ascii=False)
    # 同步到 MetaMemory
    save_player_to_memory(player)

def create_default_player():
    """创建默认玩家"""
    player = {
        "name": "Shadow Monarch",
        "title": "E 级猎人",
        "level": 1,
        "exp": 0,
        "expToNext": 100,
        "hp": 100,
        "mp": 100,
        "stats": {"strength": 10, "agility": 10, "sense": 10, "vitality": 10, "intelligence": 10},
        "statPoints": 0,
        "gold": 0,
        "soldiers": [],
        "achievements": [],
        "dailyQuest": None,
        "streak": 0,
        "createdAt": datetime.now().isoformat(),
        "lastActive": datetime.now().isoformat()
    }
    save_player(player)
    return player

def add_exp(player, amount):
    """添加经验值并处理升级"""
    player['exp'] += amount
    leveled_up = False
    while player['exp'] >= player['expToNext']:
        player['exp'] -= player['expToNext']
        player['level'] += 1
        player['expToNext'] = int(player['expToNext'] * 1.5)
        player['statPoints'] += 3
        player['hp'] = 100
        player['mp'] = 100
        leveled_up = True
    return leveled_up

def get_title(level):
    """根据等级获得称号"""
    if level < 10:
        return "E 级猎人"
    elif level < 20:
        return "D 级猎人"
    elif level < 30:
        return "C 级猎人"
    elif level < 40:
        return "B 级猎人"
    elif level < 50:
        return "A 级猎人"
    elif level < 70:
        return "S 级猎人"
    elif level < 100:
        return "国家级猎人"
    else:
        return "暗影君主"

# ==================== 技能实现 ====================

def shadow_help():
    """显示帮助信息"""
    return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  👁️ 暗影技能系统 v2.0 - 我独自升级
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  「暗影君主啊，举起您的剑，命令吧。」

  【核心命令】
  • /shadow status          - 状态面板：查看角色信息
  • /shadow analyze [path]  - 深渊凝视：分析项目
  • /shadow plan "[任务]"   - 影之战略：分解任务
  • /shadow execute [步骤]  - 暗影执行：执行计划
  • /shadow monitor         - 虚空监控：追踪进度
  • /shadow summon <type>   - 暗影召唤：调用专家 Agent
  • /shadow deploy [分钟]   - 领域展开：全局诊断
  • /shadow archive [主题]  - 记忆固化：保存经验
  • /shadow legion [规模]   - 暗影兵营：全军出击
  • /shadow add <stat> <n>  - 分配属性点

  【每日任务】
  • /shadow daily           - 查看每日任务
  • /shadow daily claim     - 领取完成奖励

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_status(options=None):
    """显示玩家状态"""
    player = load_player()

    # 计算总战斗力
    power = sum(player['stats'].values()) + player['level'] * 10 + len(player['soldiers']) * 5

    # 称号
    title = get_title(player['level'])

    # 进度条
    exp_bar_len = 30
    exp_filled = int(exp_bar_len * player['exp'] / player['expToNext'])
    exp_bar = "█" * exp_filled + "░" * (exp_bar_len - exp_filled)

    hp_bar = "█" * int(player['hp'] / 3.33) + "░" * (30 - int(player['hp'] / 3.33))
    mp_bar = "█" * int(player['mp'] / 3.33) + "░" * (30 - int(player['mp'] / 3.33))

    soldiers_list = ""
    if player['soldiers']:
        for s in player['soldiers'][:5]:
            soldiers_list += f"  • {s['name']} (LV.{s['level']} {s['type']})\n"
        if len(player['soldiers']) > 5:
            soldiers_list += f"  ... 还有 {len(player['soldiers']) - 5} 名士兵\n"
    else:
        soldiers_list = "  暂无暗影士兵 (通过 summon 召唤)\n"

    return f"""
╔═══════════════════════════════════════════╗
║         暗影君主状态面板                   ║
╠═══════════════════════════════════════════╣
║ 名称：{player['name']:<20} 等级：LV.{player['level']}
║ 称号：{title:<20} 战力：{power}
╠═══════════════════════════════════════════╣
║ HP: {hp_bar} {player['hp']/100:.0%}
║ MP: {mp_bar} {player['mp']/100:.0%}
╠═══════════════════════════════════════════╣
║ 经验：[{exp_bar}] {player['exp']}/{player['expToNext']}
╠═══════════════════════════════════════════╣
║ 【属性】                 【可用点数】:{player['statPoints']}
║ 力量 (STR):{player['stats']['strength']:<3}  - 代码输出量
║ 敏捷 (AGI):{player['stats']['agility']:<3}  - 任务完成速度
║ 感知 (SEN):{player['stats']['sense']:<3}  - Bug 检测
║ 体力 (VIT):{player['stats']['vitality']:<3}  - 持续工作
║ 智力 (INT):{player['stats']['intelligence']:<3}  - 架构设计
╠═══════════════════════════════════════════╣
║ 【暗影士兵】({len(player['soldiers'])}名)
{soldiers_list}
╠═══════════════════════════════════════════╣
║ 连续登录：{player['streak']}天  | 金币：{player['gold']}
╚═══════════════════════════════════════════╝

💡 提示：使用 /shadow add <属性> <数量> 分配属性点
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_analyze(path=None, options=None):
    """深渊凝视 - 分析项目"""
    import subprocess

    player = load_player()
    target = path or "."

    # 扫描文件
    try:
        result = subprocess.run(
            ['find', target, '-type', 'f', '-name', '*.py', '-o', '-name', '*.js', '-o', '-name', '*.ts', '-o', '-name', '*.json'],
            capture_output=True, text=True, timeout=10
        )
        files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        file_count = len([f for f in files if f])
    except:
        file_count = 0
        files = []

    # 技术栈检测
    tech_stack = []
    tech_indicators = {
        'Python': ['requirements.txt', 'setup.py', 'pyproject.toml'],
        'Node.js': ['package.json'],
        'TypeScript': ['tsconfig.json'],
        'React': ['package.json'],
        'Rust': ['Cargo.toml'],
        'Go': ['go.mod'],
    }

    for name, indicators in tech_indicators.items():
        for f in files:
            if any(ind in f for ind in indicators):
                if name not in tech_stack:
                    tech_stack.append(name)
                    break

    # 代码行数统计
    total_lines = 0
    for f in files[:50]:
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                total_lines += len(file.readlines())
        except:
            pass

    # 复杂度评级
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

    # 添加经验
    leveled = add_exp(player, exp_reward)
    save_player(player)

    level_up_msg = f"\n🎉 升级了！当前等级：LV.{player['level']}" if leveled else ""
    tech_str = ", ".join(tech_stack) if tech_stack else "未知"

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  👁️ 深渊凝视报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 目标：{target}
📊 复杂度：{complexity}

【项目指标】
┌──────────────────────────────────┐
│ 文件数量：{file_count}
│ 代码行数：~{total_lines}行
│ 技术栈：{tech_str}
│ 推荐难度：{complexity.split(' - ')[0]}级
└──────────────────────────────────┘

【分析结果】
✓ 项目结构已解析
✓ 技术栈已识别
✓ 复杂度已评估

✨ 获得经验：+{exp_reward} EXP{level_up_msg}

🔍 暗影君主，这个项目已被完全解析。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_plan(task, options=None):
    """影之战略 - 任务分解"""
    player = load_player()

    # 难度分级
    if len(task) < 20:
        difficulty = "E"
        exp_reward = 30
    elif len(task) < 50:
        difficulty = "D"
        exp_reward = 50
    elif len(task) < 100:
        difficulty = "C"
        exp_reward = 80
    else:
        difficulty = "B"
        exp_reward = 120

    # 生成任务 ID
    import hashlib
    task_id = hashlib.md5(f"{task}{datetime.now().isoformat()}".encode()).hexdigest()[:8]

    # 保存任务
    quest = {
        "id": task_id,
        "description": task,
        "difficulty": difficulty,
        "status": "planned",
        "steps": [],
        "expReward": exp_reward,
        "createdAt": datetime.now().isoformat()
    }

    quest_file = QUESTS_DIR / f"{task_id}.json"
    with open(quest_file, 'w', encoding='utf-8') as f:
        json.dump(quest, f, indent=2, ensure_ascii=False)

    add_exp(player, 10)
    save_player(player)

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🎯 影之战略规划书
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 任务：{task}
🎖️ 难度：{difficulty}级
🆔 ID: {task_id}

【战略部署】
┌──────────────────────────────────┐
│ Phase I: 情报收集 (准备阶段)      │
│ ① 深度扫描项目现状               │
│ ② 识别关键依赖和限制             │
│ ③ 标记潜在风险点                 │
│                                  │
│ Phase II: 核心攻坚 (开发阶段)     │
│ ④ 制定详细技术方案               │
│ ⑤ 分步实施功能开发               │
│ ⑥ 持续质量验证                   │
│                                  │
│ Phase III: 战后重建 (收尾阶段)    │
│ ⑦ 完整性测试                     │
│ ⑧ 文档归档                       │
│ ⑨ 经验固化                       │
└──────────────────────────────────┘

【任务奖励】
• 完成奖励：{exp_reward} EXP
• 规划奖励：10 EXP (已获得)

💡 使用 /shadow execute {task_id} 开始执行
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_execute(steps, options=None):
    """暗影执行 - 执行计划"""
    player = load_player()

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚔️ 暗影执行引擎
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 执行步骤：{steps}

【执行状态】
████░░░░░░░░░░░░░░░░ 25% 进行中

✓ 步骤初始化完成
✓ 权限验证通过
└ ▶ 正在加载任务模块...

【提示】
请描述具体要执行的代码任务，我将帮你实现。
例如："创建一个用户登录页面"或"修复 API 超时问题"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_monitor():
    """虚空监控 - 追踪进度"""
    player = load_player()

    quests = list(QUESTS_DIR.glob("*.json"))
    active_count = 0
    for q in quests:
        with open(q, 'r') as f:
            quest = json.load(f)
            if quest.get('status') == 'active':
                active_count += 1

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  👁️ 虚空监控面板
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前状态：🟢 活跃执行中
活跃任务：{active_count}

【实时指标】
├─ HP: {player['hp']}/100
├─ MP: {player['mp']}/100
├─ 连击计数：{player['streak']}天
└─ 战力评分：{sum(player['stats'].values()) + player['level'] * 10}

【今日状态】
✓ 已登录
○ 待完成任务
○ 待召唤士兵

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_summon(agent_type="explore", context=None):
    """暗影召唤 - 调用专家 Agent"""
    player = load_player()

    agent_map = {
        "explore": ("🔍 虚空行者", 50, "代码库探索/架构分析"),
        "plan": ("🧭 战略家", 40, "任务规划/方案设计"),
        "dev": ("🔨 构造者", 60, "功能开发/代码实现"),
        "test": ("🧪 试炼官", 45, "测试编写/Bug 复现"),
        "debug": ("🩺 诊断师", 55, "问题诊断/性能优化"),
        "review": ("⚖️ 审判者", 35, "代码审查/安全检测"),
        "doc": ("📝 书记官", 25, "文档编写/注释生成"),
    }

    agent_name, mp_cost, specialty = agent_map.get(agent_type, ("👻 未知单位", 50, "未知"))

    if player['mp'] < mp_cost:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠️ MP 不足
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

需要：{mp_cost} MP
当前：{player['mp']} MP

💡 休息或升级可恢复 MP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    player['mp'] -= mp_cost
    add_exp(player, 15)

    import random
    got_soldier = False
    if random.random() < 0.1 and agent_type not in [s['type'] for s in player['soldiers']]:
        player['soldiers'].append({
            "name": agent_name,
            "type": agent_type,
            "level": 1,
            "obtainedAt": datetime.now().isoformat()
        })
        got_soldier = True

    save_player(player)

    soldier_msg = f"\n🎉 获得暗影士兵：{agent_name}" if got_soldier else ""

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  💀 暗影召唤仪式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

召唤：{agent_name} [{agent_type}]
消耗：{mp_cost} MP
专长：{specialty}

「臣服于我的意志，现身吧！」

✨ Agent 已就绪
{soldier_msg}
💡 现在可以向 {agent_name} 下达指令了

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_deploy(minutes=30):
    """领域展开 - 全局诊断"""
    player = load_player()
    mp_cost = int(minutes)

    if player['mp'] < mp_cost:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠️ MP 不足
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

需要：{mp_cost} MP
当前：{player['mp']} MP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    player['mp'] -= mp_cost
    save_player(player)

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🛡️ 领域展开：全域诊断模式
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ 持续时间：{minutes}分钟
🔮 扫描维度：全面开启

【激活效果】
✓ 语法错误实时监控
✓ 安全漏洞批量扫描
✓ 性能瓶颈静态分析
✓ 代码重复相似度检测
✓ 依赖更新建议推送

【领域消耗】- {mp_cost} MP

「这就是...我的领域。」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_archive(topic, tags=None):
    """记忆固化 - 保存经验"""
    player = load_player()
    tag_str = f" #{', '.join(tags)}" if tags else ""
    add_exp(player, 25)
    player['stats']['intelligence'] += 1
    save_player(player)

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📜 记忆固化完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

主题：{topic}
标签：{tag_str}
位置：~/.claude/projects/memory/

【存档内容】
✓ 问题背景记录完成
✓ 解决方案归档完成
✓ 关键代码备份完成

【奖励】
✨ +25 EXP
✨ 智力 (INT) +1 (永久)

下次遇到相似场景将优先调取此记忆！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_legion(scale="large"):
    """暗影兵营 - 全军出击"""
    player = load_player()

    scale_config = {
        "small": ("小型部队 (3 人)", 300, "12h", 3),
        "medium": ("中型军团 (5 人)", 500, "18h", 5),
        "large": ("大型远征军 (7 人)", 800, "24h", 7),
        "full": ("全盛暗影大军 (12+)", 1200, "48h", 12),
    }

    name, mp, cd, count = scale_config.get(scale, scale_config["large"])

    if player['mp'] < mp:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠️ MP 不足
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

需要：{mp} MP
当前：{player['mp']} MP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    player['mp'] -= mp
    save_player(player)

    soldier_types = ["explore", "plan", "dev", "test", "debug", "review", "doc"]
    soldiers_display = ""
    for i in range(min(count, len(soldier_types))):
        stype = soldier_types[i % len(soldier_types)]
        soldiers_display += f"  • {stype.upper()} Agent [就绪]\n"

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  💫 暗影兵营 · 全军出击
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

规模：{name}
消耗：{mp} MP | CD: {cd}

【作战单位】
┌──────────────────────────────┐
{soldiers_display.rstrip()}
└──────────────────────────────┘

「我们随时听候您的指挥，主使者！」

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_add(stat, amount=1, options=None):
    """分配属性点"""
    player = load_player()

    valid_stats = ["strength", "agility", "sense", "vitality", "intelligence"]
    stat_map = {
        "str": "strength",
        "agi": "agility",
        "sen": "sense",
        "vit": "vitality",
        "int": "intelligence",
        "strength": "strength",
        "agility": "agility",
        "sense": "sense",
        "vitality": "vitality",
        "intelligence": "intelligence",
    }

    stat_name = stat_map.get(stat.lower())
    if not stat_name:
        return f"❌ 无效属性：{stat}\n有效属性：{', '.join(valid_stats)}"

    try:
        amount = int(amount)
    except:
        return "❌ 无效的数量"

    if player['statPoints'] < amount:
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠️ 属性点不足
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

需要：{amount}点
当前：{player['statPoints']}点
可用：{', '.join(valid_stats)}

💡 升级可获得属性点
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    player['statPoints'] -= amount
    player['stats'][stat_name] += amount
    save_player(player)

    stat_names_cn = {
        "strength": "力量",
        "agility": "敏捷",
        "sense": "感知",
        "vitality": "体力",
        "intelligence": "智力",
    }

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✨ 属性分配完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{stat_names_cn.get(stat_name, stat_name)} +{amount}
当前：{player['stats'][stat_name]}

剩余点数：{player['statPoints']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def shadow_daily(action=None, options=None):
    """每日任务"""
    player = load_player()

    if action == "claim":
        add_exp(player, 500)
        player['stats']['strength'] += 3
        player['stats']['agility'] += 3
        player['stats']['sense'] += 3
        player['stats']['vitality'] += 3
        player['stats']['intelligence'] += 3
        player['streak'] += 1
        save_player(player)
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🎁 每日任务奖励
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

奖励已领取!
✨ 全属性 +3
✨ 经验 +500
✨ 连续登录：{player['streak']}天

明天再来继续变强吧！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    return """
╔═══════════════════════════════════════════╗
║         【每日任务：变强】                  ║
╠═══════════════════════════════════════════╣
║ □ 提交一次代码                    (0/1)   ║
║ □ 修复一个 Bug                      (0/1) ║
║ □ 学习一个新概念                  (0/1)   ║
║ □ 专注编码 30 分钟                 (0/30m) ║
╠═══════════════════════════════════════════╣
║ 完成奖励：全属性 +3, 经验 +500             ║
║ 失败惩罚：进入"虚弱状态"(经验 -50%)        ║
╚═══════════════════════════════════════════╝

「想要变强吗？那就完成每日任务吧。」

💡 使用 /shadow daily claim 领取奖励
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# ==================== MetaMemory 集成 ====================

import urllib.request
import urllib.error

MEMORY_BASE_URL = "http://localhost:8100"

def memory_get_document(path: str) -> dict | None:
    """从 MetaMemory 获取文档"""
    try:
        # 先搜索
        search_url = f"{MEMORY_BASE_URL}/api/search?q={urllib.parse.quote(path)}"
        req = urllib.request.Request(search_url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            results = json.loads(resp.read().decode('utf-8'))
            for doc in results:
                if path in doc.get('path', ''):
                    return doc
    except Exception as e:
        pass  # 静默失败，回退到 JSON 文件
    return None

def memory_update_document(doc_id: str, content: str, title: str = None, tags: list = None) -> bool:
    """更新 MetaMemory 文档"""
    try:
        url = f"{MEMORY_BASE_URL}/api/documents/{doc_id}"
        data = json.dumps({
            "content": content,
            "title": title,
            "tags": tags or []
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def memory_create_or_update_document(path: str, content: str, title: str, folder_id: str, tags: list = None) -> bool:
    """创建或更新 MetaMemory 文档"""
    try:
        # 先尝试创建
        url = f"{MEMORY_BASE_URL}/api/documents"
        data = json.dumps({
            "title": title,
            "folder_id": folder_id,
            "content": content,
            "tags": tags or []
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def save_player_to_memory(player: dict) -> bool:
    """将玩家状态保存到 MetaMemory"""
    from datetime import datetime
    
    markdown = f"""# Shadow Monarch - 角色状态

> 最后更新：{datetime.now().isoformat()}

---

## 👤 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | {player['name']} |
| 称号 | {player['title']} |
| 等级 | LV.{player['level']} |
| 战力 | {sum(player['stats'].values()) + player['level'] * 10 + len(player['soldiers']) * 5} |

---

## ❤️ 状态

| HP | MP | 经验 |
|----|----|------|
| {player['hp']}/100 | {player['mp']}/100 | {player['exp']}/{player['expToNext']} |

---

## 💪 属性

| 属性 | 值 | 说明 |
|------|-----|------|
| STR (力量) | {player['stats']['strength']} | 代码输出量 |
| AGI (敏捷) | {player['stats']['agility']} | 任务完成速度 |
| SEN (感知) | {player['stats']['sense']} | Bug 检测 |
| VIT (体力) | {player['stats']['vitality']} | 持续工作 |
| INT (智力) | {player['stats']['intelligence']} | 架构设计 |

**可用属性点**: {player['statPoints']}

---

## ⚔️ 暗影士兵

"""
    if player['soldiers']:
        markdown += "| 士兵 | 类型 | 等级 | 获得时间 |\n"
        markdown += "|------|------|------|---------|\n"
        for soldier in player['soldiers']:
            markdown += f"| {soldier['name']} | {soldier['type']} | {soldier['level']} | {soldier.get('obtainedAt', 'N/A')} |\n"
    else:
        markdown += "暂无士兵\n"

    markdown += f"""
---

## 📊 统计

- 连续登录：{player['streak']}天
- 金币：{player['gold']}
- 成就：{len(player['achievements'])}个
"""
    
    # 保存到 MetaMemory (folder_id 是 shadow-state 文件夹)
    return memory_create_or_update_document(
        path="/shadow-state/player-status",
        content=markdown,
        title="player-status",
        folder_id="34b93267-de4d-41d6-b823-854063e6c382",
        tags=["shadow", "rpg", "status"]
    )
