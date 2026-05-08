# Shadow System · 暗影君主系统

> "想要变强吗？那就开始吧。"—— Solo Leveling

将个人成长游戏化的 CLI 工具。通过完成现实任务（coding、背单词、运动、阅读等）获得经验值，提升角色等级，解锁能力，收集"暗影士兵"。

完整 Web 应用设计见 [shadow-system-design.md](./shadow-system-design.md)。

---

## 快速开始

```bash
cd shadow-cli

# 查看状态
python main.py status

# 记录行为 → 获取 EXP
python main.py record commit 1
python main.py record vocabulary 50
python main.py record exercise 30

# 每日任务（含随机紧急任务）
python main.py daily

# 分配属性点
python main.py add str 2

# 召唤士兵
python main.py summon explore

# 查看士兵列表
python main.py army

# 全军出击
python main.py legion large

# 查看成就
python main.py achievements

# 分析项目
python main.py analyze .

# 规划任务
python main.py plan "实现登录系统"

# 虚空监控
python main.py monitor

# 领域展开（全局诊断）
python main.py deploy 10

# 记忆固化
python main.py archive "Phase 1完成"
```

## 核心机制

### 经验系统

```
升级所需经验 = 100 × 1.5^(level - 1)
```

| 行为 | 基础 EXP | 说明 |
|------|---------|------|
| Git commit | 50/次 | 每日上限 5 次 |
| 代码 100 行 | 10 | 手动输入 |
| 背单词 1 个 | 1 | 手动输入 |
| 运动 1 分钟 | 2 | 手动输入 |
| 阅读 1 页 | 1 | 手动输入 |
| 连续打卡 | +10%/天 | streak 加成 |
| COMBO | +10%/次 | 连续完成任务加成 |

### 角色属性

| 属性 | 说明 | 影响 |
|------|------|------|
| 等级 (LV) | 总体强度 | 解锁功能、称号 |
| HP | 精力值 | 升级恢复 |
| MP | 意志力 | 召唤士兵、使用技能 |
| STR 力量 | 执行力 | 代码输出量 |
| AGI 敏捷 | 效率 | 任务完成速度 |
| SEN 感知 | 洞察力 | Bug 检测 |
| VIT 体力 | 耐力 | 持续工作 |
| INT 智力 | 智慧 | 架构设计 |

### 称号体系

| 等级范围 | 称号 |
|---------|------|
| LV.1-9 | E 级猎人 |
| LV.10-19 | D 级猎人 |
| LV.20-29 | C 级猎人 |
| LV.30-39 | B 级猎人 |
| LV.40-49 | A 级猎人 |
| LV.50-69 | S 级猎人 |
| LV.70-99 | 国家级猎人 |
| LV.100+ | 暗影君主 |

## 项目结构

```
shadow-system/
├── README.md                     # 本文件
├── plan.md                       # 开发计划
├── shadow-system-design.md       # 完整 Web 应用设计
├── shadow-skills.md              # Claude Code 技能命令
├── shadow-skill-system.md        # 技能分类矩阵
├── shadow.json                   # 技能元数据定义
└── shadow-cli/
    ├── main.py          # CLI 入口 (18 个命令)
    ├── engine.py        # 游戏引擎 (EXP/升级/士兵/成就)
    ├── state.py         # 状态持久化 (JSON)
    ├── config.py        # 配置常量
    └── tests/
        ├── test_engine.py    # 55 个引擎测试
        ├── test_state.py     # 20 个状态测试
        └── test_phase1.py    # 36 个 Phase 1 测试
```

## 测试

```bash
cd shadow-cli
python -m pytest tests/ -v
```

**111 个测试全部通过。**

## 数据位置

状态文件存储在 `~/.claude/shadow-state/`：

```
~/.claude/shadow-state/
├── player.json     # 角色状态
├── quests/         # 任务记录
├── soldiers/       # 士兵信息
└── logs/           # 归档日志
```

## 版本

| 版本 | 阶段 | 状态 |
|------|------|------|
| v0.1.0 | Phase 0 | 核心循环验证 ✅ |
| v0.2.0 | Phase 1 | 完整 CLI ✅ |

---

*「暗影君主啊，这份蓝图已备好。何时出征，听您号令。」*
