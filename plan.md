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
Phase 5  · Web 面板（RPG 风格 UI，零框架）                 →  ~8h    ✅ v0.5.0
Phase 6  · Chat UI（NextChat + 对话式交互）               →  ~12h   ✅ v0.6.0
Phase 7  · 数据洞察 + 留存分析                             →  ~10h   ✅ v0.7.0
Phase 8  · 自定义技能 + 初始化引导                          →  ~8h    ✅ v0.8.0
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
- [x] 副本类型定义（代码地下城、单词深渊、跑步试炼、项目 RAID）
- [x] 限时挑战机制（24h 过期）
- [x] Boss 战：周期性挑战，高奖励

### 3.2 商店系统
- [x] 货币体系：金币（任务奖励）、宝石（成就奖励）
- [x] 商品分类：消耗品（体力药水、经验书）、装备、外观、功能
- [x] 购买/出售逻辑

### 3.3 每日任务优化
- [x] 根据用户行为历史智能生成每日任务 (行为自动关联副本任务)
- [x] 难度动态调整 (按玩家等级自动分配难度)

---

## Phase 4：外部集成（已完成）

### 4.1 健康数据
- [x] 小米运动/苹果健康导出文件导入 (JSON/CSV)
- [x] 手动记录健康数据 (步数/运动/睡眠)
- [x] EXP 换算: 100步=1EXP, 1运动分钟=2EXP, 1睡眠小时=5EXP (每日上限 200)
- [x] 健康数据概要统计

### 4.2 阅读数据
- [x] 微信读书导出文件导入 (JSON/CSV)
- [x] 手动记录阅读数据 (时长/页数/书名)
- [x] EXP 换算: 1分钟=1EXP, 1页=1EXP (每日上限 150)
- [x] 阅读数据概要统计

### 4.3 浏览器活动
- [x] 浏览器扩展导出数据导入 (JSON)
- [x] 手动记录浏览器学习时长
- [x] EXP 换算: 1学习分钟=2EXP (每日上限 100)
- [x] 按站点分类统计
- [ ] 浏览器插件 (预留接口)

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
| **M3: Phase 3 完成** | 副本+商店+Boss 战上线 | Phase 2 + 20h | 🟢 2026-05-08 |
| **M4: Phase 4 完成** | 外部集成(健康/阅读/浏览器) | Phase 3 + 20h | 🟢 2026-05-08 |
| **M5: Phase 5 完成** | Web 面板 (RPG 风格 UI) | Phase 4 + 8h | 🟢 2026-05-08 |
| **M6: Phase 6 完成** | Chat UI 上线，对话式交互可用 | Phase 5 + 12h | 🟢 2026-05-09 |

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

### DEC-003: 使用 NextChat 作为 Chat UI
- **日期**：2026-05-09
- **理由**：最轻量（Next.js SPA），纯代理模式，支持 OpenAI 兼容 API，Docker 一键部署
- **替代方案**：Open WebUI（更重但 Python 友好）、自研前端（成本高）
- **对接方式**：`BASE_URL` 环境变量指向游戏引擎的 `/v1/chat/completions` 端点

---

## Phase 5：Web 面板（已完成）

### 5.1 Web 服务端
- [x] `web_server.py` — 纯 Python `http.server`，零外部依赖
- [x] 20+ JSON API 端点，覆盖所有游戏操作
- [x] CORS 支持，静态文件服务
- [x] `main.py web [--port 8080]` 命令

### 5.2 Web 面板界面
- [x] RPG 风格深色主题 UI
- [x] 9 个页面: 仪表盘/每日任务/快捷操作/成就/商店/士兵/副本/Boss/集成
- [x] 状态条 (HP/MP/EXP)、属性面板、战力显示
- [x] 响应式设计，支持手机浏览器
- [x] 30 秒自动刷新
- [x] 零 JavaScript 框架，纯原生 HTML/CSS/JS

### 5.3 测试
- [x] 40 个 Web API 测试，覆盖所有端点
- [x] 测试包括：状态/任务/记录/召唤/军团/士兵/成就/副本/Boss/商店/背包/集成/健康/阅读/浏览器/属性分配/CORS/静态文件

---

## Phase 6：Chat UI 对话式接口（已完成）

**背景**：Phase 5 Web 面板已有完整功能，但需要用户主动点击操作，上手仍有门槛。
目标：**用 ChatGPT 风格聊天界面替代/补充 Web 面板**，用户通过自然语言对话完成所有游戏操作。
**核心判断**：主流开源聊天 UI 都走 OpenAI 兼容 API 协议 → 游戏引擎只需包一层 FastAPI/标准 HTTP 接口，无需改 UI 代码。

### 6.1 Chat UI 选型
- [x] 候选框架评估：NextChat（首选）、Open WebUI、LobeChat、ChatBot UI
- [x] 决策：**使用 NextChat**（8.8万 star，最轻量，纯代理模式，不改后端）
- [ ] 部署 NextChat Docker，设置 `BASE_URL` 指向游戏引擎

### 6.2 OpenAI 兼容 API 适配层
- [x] `POST /v1/chat/completions` 端点
- [x] 解析用户消息 → 调用 engine 对应逻辑 → 返回角色扮演回复
- [x] 支持流式输出（streaming）→ 更好的聊天体验
- [x] 指令识别：
  - 自然语言："背了50个单词" → 自动识别为 record vocabulary
  - 斜杠命令："/status" "/daily" "/summon explore" 等
  - 模糊输入："今天的任务" → 返回今日任务列表
- [x] 回复风格：暗影君主 NPC 口吻，带 RPG 风格文本

### 6.3 游戏引擎 → 对话式交互适配
- [x] engine 现有函数不变，新增 `chat_processor.py` 作为 NLP 指令解析层
- [x] 指令匹配优先级：斜杠命令 > 自然语言 > 模糊匹配 > 自由输入
- [x] 对话上下文：记住最近的指令类型，支持追问（如 "那就背100个"）
- [x] 卡片式回复：等级面板、状态面板、每日任务列表 → 用 Markdown 表格/ASCII 框美化输出
- [x] 35 个单元测试覆盖：解析/执行/OpenAI 格式

### 6.4 被动数据上报接口
- [ ] 保持现有 `POST /api/activities` 端点（供 Git Hook/文件监控调用）
- [ ] 被动活动也通过聊天界面推送通知："🎯 检测到 1 次 Git commit，+50 EXP"
- [ ] 支持 Webhook 推送模式（主动推给 Chat UI）

### 6.5 验收标准
- [ ] 用户打开聊天页面，与 "暗影君主" 对话即可完成所有操作
- [ ] "我背了50个单词" → 自动记录 + EXP 计算 + 升级通知
- [ ] "我的状态" → 返回 RPG 风格面板
- [ ] "/daily" → 返回今日任务列表
- [ ] Git commit 自动触发通知消息
- [ ] 手机浏览器也能正常使用（NextChat 自带响应式）

### 6.6 技术栈
- Chat UI：NextChat (Docker 部署)
- API 适配层：基于现有 `web_server.py` 扩展 或 新增 `chat_server.py`
- 指令解析：关键词 + 正则匹配（暂不引入 LLM）
- 零新外部依赖（保持 Phase 0 原则）

---

## Phase 7：数据洞察 + 留存分析（已完成）

### 7.1 每日活动日志
- [x] `log_daily_activity()` — 每次 record 时自动记录
- [x] `dailyLog` 字段加入玩家状态
- [x] 支持按日期、类型筛选

### 7.2 报告系统
- [x] 周报：`get_weekly_report()` — 每日趋势、缺勤天数、平均 EXP
- [x] 月报：`get_monthly_report()` — 按周汇总、最佳/最差日期
- [x] CLI 命令：`shadow report [weekly|monthly]`
- [x] ASCII 柱状图渲染（Unicode 块字符）

### 7.3 洞察建议
- [x] `get_insights()` — 个性化推荐（6 条以内）
- [x] 对比本周 vs 上周活跃度，识别闲置天数
- [x] Web API + Web UI 展示

### 7.4 连续打卡分析
- [x] 最佳连续天数、当前连续天数、完成率的计算
- [x] 活动类型分解（type breakdown）

### 7.5 验收
- [x] 23 个新测试，全部通过
- [x] 总测试数：353
- [x] 版本：v0.7.0

---

## Phase 8：自定义技能 + 初始化引导（已完成）

**背景**：系统硬编码了 5 种活动类型，新玩家创建角色后直接进入面板，没有引导流程。目标：**让每个玩家定义自己的技能体系**，通过 LLM 自动填充参数。

### 8.1 技能配置系统
- [x] `skill_config.py` 模块（480 行，16 个函数）
- [x] 16 个内置模板（单词、编程、跑步、吉他、绘画等）
- [x] 7 个分类（学习/开发/健康/音乐/艺术/创作/生活）
- [x] 用户自定义模板持久化到 `skill_templates.json`

### 8.2 LLM 集成（可选）
- [x] 环境变量 `SHADOW_LLM_BASE_URL` + `SHADOW_LLM_API_KEY`
- [x] OpenAI 兼容 API 调用，自动生成技能配置 JSON
- [x] 关键词匹配作为零依赖 fallback
- [x] 三级生成策略：LLM → 关键词 → 通用兜底

### 8.3 初始化引导流程
- [x] 6 个预设套餐（程序员/学生/健身/音乐/全面/艺术家）
- [x] Web UI 三步引导：选择预设/自定义 → 确认配置 → 完成
- [x] `onboarded` 标志位，控制引导流程显示
- [x] 玩家输入自然语言描述 → 自动生成技能参数

### 8.4 引擎适配
- [x] `engine.py`：`generate_daily_tasks()` 优先使用玩家技能
- [x] `engine.py`：`get_exp_for_action()` 支持动态 skill EXP 计算
- [x] 每日任务从玩家技能列表动态生成
- [x] 紧急任务从玩家技能中随机选取

### 8.5 API + Web UI
- [x] 4 个 GET 端点：status / presets / templates / categories
- [x] 2 个 POST 端点：configure / save
- [x] Web UI 引导覆盖层（3 步流程 + 套餐网格 + 技能标签 + 配置列表）

### 8.6 验收
- [x] 30 个新测试，全部通过
- [x] 总测试数：383
- [x] 版本：v0.8.0

---

## 风险登记

| 风险 | 影响 | 对策 | 状态 |
|------|------|------|------|
| 经验公式不平衡 | 升级太快或太慢导致流失 | Phase 0 先调参，A/B 测试 | 待验证 |
| 手动输入摩擦 | 用户懒得打卡 | Phase 2 做自动化追踪 | 已完成 |
| 新鲜感流失 | 游戏化应用通病 | Phase 3 加副本/商店/成就 | 已完成 |
| 过度设计 | 功能太多但核心循环不稳定 | 严格按 Phase 顺序，不跳级 | 已确认 |
| Chat UI 依赖过多 | NextChat 更新可能不兼容 | Docker pin 版本，适配层隔离 | Phase 6 监控 |

---

*最后更新：2026-05-09*
*下次评审：Phase 8 完成后 — 评估引导流程体验和模板数据积累*
