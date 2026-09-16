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
    ├── web_server.py    # Web 仪表盘 + REST API + SSE 推送
    ├── engine.py        # 游戏引擎 (EXP/升级/士兵/成就)
    ├── auth.py          # 多用户认证 (JWT/PBKDF2, 零外部依赖)
    ├── guild.py         # 公会系统 (创建/任务/公会战/排行)
    ├── events.py        # 事件总线 (SSE 实时推送)
    ├── dungeon.py       # 副本系统
    ├── shop.py          # 商店系统
    ├── chat_processor.py # OpenAI 兼容聊天接口
    ├── file_tracker.py  # 文件变更监控
    ├── git_tracker.py   # Git 提交追踪
    ├── state.py         # 状态持久化 (JSON)
    ├── config.py        # 配置常量
    └── tests/
        ├── test_engine.py       # 引擎测试
        ├── test_state.py        # 状态测试
        ├── test_auth_guild.py   # 认证 + 公会测试 (37)
        ├── test_events.py       # 事件系统测试
        └── ...
```

## 测试

```bash
cd shadow-cli
python -m pytest tests/ -v
```

**450 个测试全部通过。**

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
| v0.3.0 | Phase 2 | Git/文件追踪自动化 ✅ |
| v0.4.0 | Phase 3 | 副本/商店/Boss 战 ✅ |
| v0.5.0 | Phase 4 | 外部集成 (健康/阅读/浏览器) ✅ |
| v0.5.1 | Phase 5 | Web 仪表盘 + RPG UI ✅ |
| v0.6.0 | Phase 6 | 多用户认证 + 公会系统 + SSE 实时推送 ✅ |
| v0.7.0 | Phase 7 | 数据洞察 + 留存分析（周报/月报/insights/streak）✅ |
| v0.8.0 | Phase 8 | 自定义技能 + 初始化引导 ✅ |
| v0.9.2 | Phase 9 | 体验修复 + 智能提醒 + 移动端适配 ✅ |

---

*「暗影君主啊，这份蓝图已备好。何时出征，听您号令。」*


## 服务器停用归档（2026-09-16）

此私有仓库保存 `/mnt/chengrongfeng_private/cc_dump/shadow-system/` 的完整项目代码、原有 25 个提交和最新未提交改动。新增归档提交位于原历史之后。

服务器实际角色和任务状态位于 `/home/srp_member/.claude/shadow-state/`，快照保存在仓库 `server-state-backup/shadow-state/`。恢复前先备份目标机器已有状态，再将快照内容复制到 `~/.claude/shadow-state/`。用户状态包含个人记录，应保持仓库私有。登录签名密钥 `token_secret` 保存在本地原始备份中；恢复时可由程序生成新密钥并重新登录。

```bash
cd shadow-cli
python main.py status
python main.py web --port 8080
```

缓存、运行日志和依赖安装目录不进入版本控制。原始项目与运行状态另有本地压缩备份。
