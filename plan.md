# Shadow System · 开发计划

> 「暗影君主啊，这份蓝图已备好。何时出征，听您号令。」

---

## 路线总览

```
Phase 0  · 验证核心循环（Python CLI，无 UI，最快跑出闭环）  →  ~8h
Phase 1  · MVP 可运行版本（CLI 完整功能 + 状态持久化）      →  ~16h
Phase 2  · 自动化追踪（Git Hook + 文件监控）               →  ~12h
Phase 3  · 内容扩展（副本 + 商店 + 成就）                  →  ~20h
Phase 4  · 外部集成（运动 API + 读书 API + 浏览器插件）    →  ~20h
```

**决策门**：Phase 0 完成后，验证经验公式和等级体系的合理性。如果核心循环跑不通或用户留存验证失败，及时止损，不进入 Phase 1 以上的投入。

---

## Phase 0：核心循环验证（CLI 版）

**目标**：用最少的代码跑通"接任务 → 执行 → 获得经验 → 升级"的完整闭环，验证数值平衡。

### 0.1 项目脚手架
- [x] 目录结构：`shadow-cli/`，包含 `main.py`、`state.py`、`engine.py`、`config.py`
- [x] Python 3.10+，仅依赖标准库（json、pathlib、datetime），零外部依赖
- [x] 状态存储：`~/.claude/shadow-state/player.json`，已有代码可直接复用

### 0.2 状态管理
- [x] 玩家数据模型：`name, level, exp, expToNext, hp, mp, stats, statPoints, gold, streak`
- [x] 加载/保存函数：`load_player()`, `save_player()`, `create_default_player()`
- [x] 已有 `shadow.py` 中的状态管理代码直接迁移

### 0.3 经验计算引擎
- [x] 升级公式：`expToNext = 100 × 1.5^(level-1)`
- [x] 经验判定：`add_exp(amount)` → 检查升级 → 自动升等级 → 重置 HP/MP → 给予属性点
- [x] 称号映射：等级 → 称号（E级猎人 → 暗影君主）
- [x] **关键验证**：写单元测试，确认 LV.1→LV.50 的经验曲线是否平滑

### 0.4 手动打卡
- [x] 命令：`shadow daily` → 列出 4 个每日任务
- [x] 命令：`shadow record <类型> <数量>` → 记录行为并计算 EXP
  - 行为类型：`commit`、`coding`、`vocabulary`、`exercise`、`reading`
  - 自动换算为 EXP（参考设计文档经验表）
- [x] 命令：`shadow status` → 打印 ASCII 状态面板
- [x] 命令：`shadow add <属性> <数量>` → 分配属性点

### 0.5 MVP 验收标准
- [x] `shadow status` 能正确显示等级、经验、属性、称号
- [x] `shadow record commit` 能正确加 EXP 并触发升级
- [x] `shadow add str 2` 能正确扣除属性点
- [x] 状态持久化：重启后数据不丢失 (手动验证 + 单元测试)
- [x] 经验公式通过 50 级范围内的单元测试

---

## Phase 1：完整 CLI 版本

**前提**：Phase 0 验收通过，经验公式数值平衡。

### 1.1 任务系统
- [x] 每日任务自动生成（4 个固定 + 1 个随机紧急任务）
- [x] 任务状态流转：`pending → active → completed / failed`
- [x] 任务难度分级：E/D/C/B/A/S，影响经验倍率
- [x] 连击（combo）系统：连续完成任务获得经验加成
- [x] 连续打卡（streak）系统：每日登录加成

### 1.2 士兵系统
- [x] 召唤命令：`shadow summon <type>` → 消耗 MP，随机概率获得士兵
- [x] 7 种士兵类型（explore / plan / dev / test / debug / review / doc）
- [x] 士兵养成：士兵等级随用户等级提升，可独立升级
- [x] 命令：`shadow army` → 显示士兵列表

### 1.3 技能命令完善
- [x] `/shadow analyze [path]` → 扫描项目，评估复杂度（已有代码可迁移）
- [x] `/shadow plan "[任务]"` → 任务分解为多阶段步骤
- [x] `/shadow monitor` → 实时监控面板
- [x] `/shadow deploy [分钟]` → 全局诊断模式（模拟）
- [x] `/shadow archive [主题]` → 保存经验到记忆库（写入文件）
- [x] `/shadow legion [规模]` → 批量召唤

### 1.4 成就系统
- [x] 成就定义：`id, name, description, condition, reward`
- [x] 预置成就：Hello World、初露锋芒、Bug 杀手、完美构建、多线程之神、代码医生、暗影君主
- [x] 成就检查：每次经验结算时检查是否达成
- [x] 命令：`shadow achievements` → 显示成就列表

---

## Phase 2：自动化追踪

**前提**：Phase 1 完整可用，用户手动打卡频率稳定。

### 2.1 Git 提交追踪
- [x] 安装 Git pre-commit hook：自动记录 commit 时间和文件变更
- [x] 读取 Git log：统计每日 commit 数量，自动记录 EXP
- [ ] GitHub API 同步（可选）：同步远程仓库的 commit 记录

### 2.2 文件变更监控
- [x] 文件变更扫描 — 零依赖实现（无 watchdog）
- [x] 统计代码行数变化 → 自动换算为 coding EXP
- [x] 过滤器：仅追踪 .py/.js/.ts/.go/.rs 等 23 种代码文件

### 2.3 Shell 命令记录
- [ ] Shell preexec hook：记录终端执行的命令类型
- [ ] 识别常用开发命令（npm test、pytest、cargo build 等）→ 给予经验

---

## Phase 3：内容扩展

### 3.1 副本系统
- [ ] 副本类型定义（代码地下城、单词深渊、跑步试炼、项目 RAID）
- [ ] 限时挑战机制（倒计时）
- [ ] Boss 战：周期性挑战，高奖励

### 3.2 商店系统
- [ ] 货币体系：金币（任务奖励）、宝石（成就奖励）
- [ ] 商品分类：消耗品（体力药水、经验书）、装备、外观、功能
- [ ] 购买/出售逻辑

### 3.3 每日任务优化
- [ ] 根据用户行为历史智能生成每日任务
- [ ] 难度动态调整

---

## Phase 4：外部集成（可选）

### 4.1 健康数据
- [ ] 小米运动 API：步数、运动时长 → 自动记录 EXP
- [ ] 苹果健康 API（如适用）

### 4.2 阅读数据
- [ ] 微信读书 API：阅读时长/页数 → 自动记录 EXP

### 4.3 浏览器插件
- [ ] 记录学习时长（LeetCode、StackOverflow 等）
- [ ] 自动打卡

---

## 风险登记

| 风险 | 影响 | 对策 | 状态 |
|------|------|------|------|
| 经验公式不平衡 | 升级太快或太慢导致流失 | Phase 0 先调参，A/B 测试 | 待验证 |
| 手动输入摩擦 | 用户懒得打卡 | Phase 2 做自动化追踪 | 已排期 |
| 新鲜感流失 | 游戏化应用通病 | Phase 3 加副本/商店/成就 | 已排期 |
| 过度设计 | 功能太多但核心循环不稳定 | 严格按 Phase 顺序，不跳级 | 已确认 |

---

## 关键里程碑

| 里程碑 | 目标 | 预估完成 | 状态 |
|--------|------|---------|------|
| **M0: Phase 0 完成** | CLI 能跑通完整循环，经验公式验证 | ✅ 2026-05-06 | 🟢 |
| **M1: Phase 1 完成** | 完整 CLI 可用，含任务/士兵/成就 | Phase 0 + 16h | 🟢 2026-05-08 |
| **M2: Phase 2 完成** | Git 自动追踪上线 | Phase 1 + 12h | 🟢 2026-05-08 |
| **M3: Phase 3 完成** | 副本+商店+成就上线 | Phase 2 + 20h | 🔴 |
| **M4: Web 版本决策** | 基于数据决定是否投入 Web 开发 | Phase 3 后评估 | 🔴 |

---

## 决策记录

### DEC-001: 先做 CLI 不做 Web
- **日期**：2026-05-03
- **理由**：Web 开发成本高（~40h），核心循环未验证前投入风险大
- **替代方案**：用 Python CLI 快速验证经验公式和等级体系
- **复审条件**：Phase 0 完成后，根据用户反馈决定是否进入 Web 开发

### DEC-002: 零外部依赖
- **日期**：2026-05-03
- **理由**：降低安装门槛，避免依赖冲突
- **约束**：Phase 0 仅使用 Python 标准库

---

*最后更新：2026-05-08*
*下次评审：Phase 2 完成后 — 进入 Phase 3（副本+商店+成就）*
