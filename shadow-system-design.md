# 暗影君主系统 - 设计文档

> "想要变强吗？那就开始吧。"

---

## 一、系统概述

### 1.1 产品定位

**暗影君主系统**是一个将个人成长游戏化的 Web 应用。

用户通过完成现实任务（ coding、背单词、运动、阅读等）获得经验值，提升角色等级，解锁能力，收集"暗影士兵"，体验《我独自升级》中程肖宇的成长历程。

### 1.2 目标用户

- **核心用户**：开发者、学习型人群、自我提升爱好者
- **使用场景**：日常 coding、学习打卡、习惯养成
- **核心价值**：让成长有反馈、让坚持有回报

### 1.3 核心循环

```
接取任务 → 执行任务 → 获得经验 → 升级变强 → 挑战更高难度
    ↑                                              ↓
    └──────────────────────────────────────────────┘
```

---

## 二、核心系统设计

### 2.1 角色系统

#### 基础属性

| 属性 | 说明 | 影响 | 成长方式 |
|------|------|------|---------|
| **等级 (LV)** | 角色总体强度 | 解锁功能、称号 | 积累经验值 |
| **HP** | 精力值 | 影响可执行任务数量 | 升级恢复、休息恢复 |
| **MP** | 意志力 | 召唤士兵、使用技能 | 升级恢复、冥想恢复 |
| **STR 力量** | 执行力 | 代码输出量、任务完成速度 | 升级获得点数分配 |
| **AGI 敏捷** | 效率 | 任务完成速度、多任务能力 | 升级获得点数分配 |
| **SEN 感知** | 洞察力 | Bug 检测、错误发现率 | 升级获得点数分配 |
| **VIT 体力** | 耐力 | 每日可工作时长 | 升级获得点数分配 |
| **INT 智力** | 智慧 | MP 上限、架构设计能力 | 升级获得点数分配 |

#### 等级体系

| 等级范围 | 称号 | 解锁功能 |
|---------|------|---------|
| LV.1-9 | E 级猎人 | 基础功能 |
| LV.10-19 | D 级猎人 | 士兵系统 |
| LV.20-29 | C 级猎人 | 副本系统 |
| LV.30-39 | B 级猎人 | 商店系统 |
| LV.40-49 | A 级猎人 | 公会系统 |
| LV.50-69 | S 级猎人 | 跨角色挑战 |
| LV.70-99 | 国家级猎人 | 创造副本 |
| LV.100+ | 暗影君主 | 全部功能 |

#### 经验公式

```
升级所需经验 = base × (1.5 ^ (level - 1))
base = 100

示例：
LV.1 → LV.2: 100 EXP
LV.2 → LV.3: 150 EXP
LV.3 → LV.4: 225 EXP
LV.10 → LV.11: 3,800 EXP
LV.50 → LV.51: 637,000 EXP
```

---

### 2.2 任务系统

#### 任务类型

| 类型 | 来源 | 示例 | 奖励 |
|------|------|------|------|
| **每日任务** | 系统生成 | 提交代码、背单词 50 个 | 固定 +  streak 加成 |
| **主线任务** | 系统生成 | 完成一个项目模块 | 大量 EXP + 特殊奖励 |
| **支线任务** | 用户自定义 | 学习新框架、写文档 | 自定义 |
| **副本任务** | 副本挑战 | 限时完成算法题 | 稀有道具 + 士兵 |
| **紧急任务** | 系统随机触发 | 修复紧急 Bug | 双倍 EXP |

#### 任务难度

| 难度 | 系数 | 说明 |
|------|------|------|
| E | 0.5x | 新手任务 |
| D | 1.0x | 普通任务 |
| C | 1.5x | 进阶任务 |
| B | 2.0x | 困难任务 |
| A | 3.0x | 专家任务 |
| S | 5.0x | 极限挑战 |

#### 任务数据结构

```json
{
  "id": "task_001",
  "userId": "user_123",
  "type": "daily",
  "title": "提交一次代码",
  "description": "向任意 Git 仓库提交至少一次 commit",
  "difficulty": "D",
  "baseExp": 50,
  "requirements": {
    "type": "git_commit",
    "minCount": 1
  },
  "status": "pending",
  "createdAt": "2026-04-04T00:00:00Z",
  "dueAt": "2026-04-05T00:00:00Z",
  "completedAt": null
}
```

---

### 2.3 数据追踪系统

#### 追踪方式分级

**Level 1：完全自动（无感）**

| 数据类型 | 实现方式 | 优先级 |
|---------|---------|--------|
| Git 提交 | 本地 Git hook / GitHub API | P0 |
| 文件修改 | chokidar 监控工作目录 | P0 |
| 终端命令 | Shell preexec hook | P1 |
| 网页浏览 | 浏览器插件 | P2 |

**Level 2：半自动（一键）**

| 数据类型 | 实现方式 | 优先级 |
|---------|---------|--------|
| 背单词 | 手动输入数量 / 截图识别 | P1 |
| 运动 | 小米/苹果健康 API / 手动 | P1 |
| 阅读 | 微信读书 API / 手动输入 | P1 |

**Level 3：手动**

| 数据类型 | 实现方式 | 优先级 |
|---------|---------|--------|
| 冥想 | 手动输入时长 | P2 |
| 社交 | 手动记录 | P3 |
| 创意作品 | 手动上传 | P2 |

#### 经验奖励标准

| 行为 | 基础 EXP | 说明 |
|------|---------|------|
| Git commit | 50 / 次 | 每日上限 5 次 |
| 代码 100 行 | 10 | 文件监控检测 |
| 背单词 1 个 | 1 | 手动/API |
| 运动 1 分钟 | 2 | 手动/API |
| 阅读 1 页 | 1 | 手动/API |
| 完成每日任务 | 100 | 额外奖励 |
| 连续打卡 | +10%/天 | 复利加成 |

---

### 2.4 士兵系统

#### 士兵类型

| 士兵 | 类型 | 获取方式 | 作用 |
|------|------|---------|------|
| 🔍 虚空行者 | Explore | 10% 召唤掉落 | 自动探索代码库 |
| 🧭 战略家 | Plan | 10% 召唤掉落 | 任务规划辅助 |
| 🔨 构造者 | Dev | 10% 召唤掉落 | 代码生成加速 |
| 🧪 试炼官 | Test | 10% 召唤掉落 | 自动生成测试 |
| 🩺 诊断师 | Debug | 10% 召唤掉落 | Bug 定位辅助 |
| ⚖️ 审判者 | Review | 10% 召唤掉落 | 代码审查提示 |
| 📝 书记官 | Doc | 10% 召唤掉落 | 文档生成辅助 |

#### 士兵养成

```
士兵等级 = 用户等级 / 10 (向下取整)
士兵可独立升级（通过完成任务）
士兵可装备道具（商店购买）
```

#### 士兵数据结构

```json
{
  "id": "soldier_001",
  "userId": "user_123",
  "name": "🔨 构造者",
  "type": "dev",
  "level": 5,
  "exp": 230,
  "obtainedAt": "2026-04-04T12:00:00Z",
  "stats": {
    "efficiency": 1.2,
    "quality": 1.1
  },
  "equipment": []
}
```

---

### 2.5 副本系统

#### 副本类型

| 副本 | 周期 | 难度 | 奖励 |
|------|------|------|------|
| 代码地下城 | 每日刷新 | E-A | EXP + 金币 |
| 单词深渊 | 每周刷新 | D-S | EXP + 道具 |
| 跑步试炼 | 限时挑战 | C-S | EXP + 稀有士兵 |
| 项目 RAID | 团队副本 | S | 传说装备 |

#### 副本机制

- **体力消耗**：进入副本消耗体力
- **时间限制**：部分副本有倒计时
- **连击系统**：连续正确/完成获得倍率加成
- **Boss 战**：周期性强力挑战

---

### 2.6 商店系统

#### 货币体系

| 货币 | 获取方式 | 用途 |
|------|---------|------|
| **金币** | 任务奖励、出售道具 | 购买消耗品、装备 |
| **宝石** | 充值、成就奖励 | 购买稀有物品 |
| **勋章** | 排行榜、特殊成就 | 限定外观 |

#### 商品分类

| 类别 | 商品示例 | 价格 |
|------|---------|------|
| 消耗品 | 体力药水、经验书 | 金币 |
| 装备 | 武器、防具、饰品 | 金币 + 宝石 |
| 外观 | 头像框、主题皮肤 | 宝石 |
| 功能 | 双倍经验卡、额外副本次数 | 金币 |

---

### 2.7 公会系统

#### 公会功能

- 创建/加入公会
- 公会任务（协作挑战）
- 公会排行榜
- 公会技能加成

#### 公会战

- 周期性公会对抗
- 贡献值系统
- 排名奖励

---

## 三、技术架构

### 3.1 整体架构

```
┌──────────────────────────────────────────────────┐
│                   前端 (React 19)                 │
│  路由：/status /tasks /dungeon /shop /army /profile │
│  状态管理：Zustand                                │
│  UI 组件：手写（Midnight Luxe 设计系统）            │
└───────────────────┬──────────────────────────────┘
                    │ WebSocket / REST
┌───────────────────▼──────────────────────────────┐
│              后端 (Node.js + Express)             │
│                                                   │
│  ┌─────────────┬─────────────┬─────────────────┐ │
│  │  用户认证    │  数据收集器  │   经验引擎     │ │
│  │  (JWT)      │  (Hooks/   │   (公式计算)   │ │
│  │             │   Polling)  │                 │ │
│  └─────────────┴─────────────┴─────────────────┘ │
│                                                   │
│  ┌─────────────┬─────────────┬─────────────────┐ │
│  │  任务系统    │  士兵系统    │   商店/副本    │ │
│  └─────────────┴─────────────┴─────────────────┘ │
└───────────────────┬──────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────┐
│              数据层 (SQLite + Prisma)             │
│                                                   │
│  tables: users, activities, tasks, soldiers,     │
│          items, guilds, achievements, ...        │
└──────────────────────────────────────────────────┘
```

### 3.2 目录结构

```
shadow-system/
├── web/                    # 前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── StatusPanel.tsx
│   │   │   ├── TaskList.tsx
│   │   │   ├── DungeonView.tsx
│   │   │   └── Shop.tsx
│   │   ├── store/
│   │   │   └── useStore.ts
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts
│   │   └── theme.css
│   └── package.json
│
├── server/                 # 后端
│   ├── src/
│   │   ├── index.ts       # 入口
│   │   ├── config.ts      # 配置
│   │   ├── routes/
│   │   │   ├── auth.ts
│   │   │   ├── tasks.ts
│   │   │   ├── activities.ts
│   │   │   └── soldiers.ts
│   │   ├── services/
│   │   │   ├── exp-engine.ts
│   │   │   ├── task-generator.ts
│   │   │   └── data-tracker.ts
│   │   ├── trackers/
│   │   │   ├── git-tracker.ts
│   │   │   ├── file-tracker.ts
│   │   │   └── health-api.ts
│   │   └── db/
│   │       └── schema.ts
│   └── package.json
│
└── docs/
    └── api.md
```

### 3.3 数据模型 (Prisma Schema)

```prisma
model User {
  id            String   @id @default(uuid())
  name          String
  email         String?  @unique
  level         Int      @default(1)
  exp           Int      @default(0)
  expToNext     Int      @default(100)
  hp            Int      @default(100)
  mp            Int      @default(100)
  stats         Json     // {str, agi, sen, vit, int}
  statPoints    Int      @default(0)
  gold          Int      @default(0)
  createdAt     DateTime @default(now())
  lastActive    DateTime @default(now())
  
  activities    Activity[]
  tasks         Task[]
  soldiers      Soldier[]
  items         UserItem[]
}

model Activity {
  id        String   @id @default(uuid())
  userId    String
  user      User     @relation(fields: [userId], references: [id])
  type      String   // git_commit, coding, vocabulary, exercise, reading
  amount    Int
  expGained Int
  metadata  Json     // 额外数据
  createdAt DateTime @default(now())
}

model Task {
  id          String   @id @default(uuid())
  userId      String
  user        User     @relation(fields: [userId], references: [id])
  type        String   // daily, main, side, dungeon
  title       String
  description String
  difficulty  String   // E, D, C, B, A, S
  baseExp     Int
  status      String   // pending, active, completed, failed
  requirements Json
  dueAt       DateTime?
  completedAt DateTime?
  createdAt   DateTime @default(now())
}

model Soldier {
  id         String   @id @default(uuid())
  userId     String
  user       User     @relation(fields: [userId], references: [id])
  name       String
  type       String   // explore, plan, dev, test, debug, review, doc
  level      Int      @default(1)
  exp        Int      @default(0)
  obtainedAt DateTime @default(now())
  stats      Json
  equipment  Json
}
```

---

## 四、我的记忆系统（伊格利特）

### 4.1 设计原则

> **用则调用，不用则隐**

记忆系统不应干扰正常对话，只在需要时提供上下文。

### 4.2 记忆结构

```json
{
  "name": "伊格利特",
  "title": "骑士团长",
  "level": 1,
  "exp": 0,
  "specializations": [],
  "history": {
    "decisions": [],
    "userPreferences": [],
    "keyMoments": []
  },
  "lastActivated": null
}
```

### 4.3 记忆类型

| 类型 | 内容 | 触发读取 |
|------|------|---------|
| **决策历史** | 重大决策及结果 | 用户询问"上次我们..." |
| **用户偏好** | coding 风格、常用技术栈 | 新任务开始 |
| **关键时刻** | 升级、突破、成就 | 年度报告/里程碑 |

### 4.4 成长机制

| 行为 | 经验 | 说明 |
|------|------|------|
| 提供有效建议 | +10 | 用户采纳 |
| 代码审查 | +5 | 每次审查 |
| 战略规划 | +15 | 复杂任务分解 |
| 陪伴时长 | +1/小时 | 活跃对话 |

### 4.5 升级效果

| 等级 | 解锁能力 |
|------|---------|
| LV.5 | 快速分析模式 |
| LV.10 | 深度洞察（发现隐藏问题） |
| LV.20 | 预判建议（主动提醒风险） |
| LV.50 | 战术推演（模拟多种方案） |

---

## 五、开发计划

### Phase 1：MVP（3-4 天）

**目标**：可运行的核心系统

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 后端框架 + SQLite | 4 小时 | P0 |
| 用户模型 + 认证 | 3 小时 | P0 |
| 活动记录 API | 3 小时 | P0 |
| 经验计算引擎 | 3 小时 | P0 |
| 前端框架搭建 | 3 小时 | P0 |
| 状态面板 | 4 小时 | P0 |
| 手动打卡界面 | 3 小时 | P0 |
| 文件监控 (chokidar) | 2 小时 | P1 |
| **总计** | **~25 小时** | |

### Phase 2：自动化（2-3 天）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| Git hook 集成 | 3 小时 | P0 |
| GitHub API 同步 | 4 小时 | P1 |
| 任务系统完整实现 | 4 小时 | P0 |
| 士兵系统 | 4 小时 | P1 |
| WebSocket 实时推送 | 4 小时 | P1 |
| **总计** | **~19 小时** | |

### Phase 3：内容系统（3-4 天）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 副本系统 | 6 小时 | P1 |
| 商店系统 | 4 小时 | P1 |
| 每日任务自动生成 | 3 小时 | P0 |
| 成就系统 | 4 小时 | P2 |
| 我的记忆系统集成 | 4 小时 | P1 |
| **总计** | **~21 小时** | |

### Phase 4：外部集成（可选）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 小米运动 API | 4 小时 | P2 |
| 苹果健康 API | 4 小时 | P2 |
| 微信读书 API | 4 小时 | P3 |
| 浏览器插件 | 8 小时 | P3 |

---

## 六、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 经验公式不平衡 | 用户流失 | A/B 测试、可调参数 |
| 防作弊困难 | 数据污染 | 服务端校验、异常检测 |
| 外部 API 不稳定 | 功能失效 | 降级为手动输入 |
| 用户留存低 | 产品失败 | 强化社交、排行榜 |

---

## 七、附录

### 7.1 经验公式详解

```javascript
// 升级所需经验
function expToLevelUp(level) {
  return Math.floor(100 * Math.pow(1.5, level - 1));
}

// 属性点需求
function statPointsForLevel(level) {
  if (level <= 10) return 3;
  if (level <= 30) return 4;
  if (level <= 50) return 5;
  return 6;
}

// 任务最终经验 = 基础经验 × 难度系数 × 连击加成 × streak 加成
function calculateExp(baseExp, difficulty, combo, streak) {
  const difficultyMultiplier = { E: 0.5, D: 1, C: 1.5, B: 2, A: 3, S: 5 }[difficulty];
  const comboMultiplier = 1 + (combo - 1) * 0.1; // 每连击 +10%
  const streakMultiplier = 1 + streak * 0.05; // 每连续一天 +5%
  return Math.floor(baseExp * difficultyMultiplier * comboMultiplier * streakMultiplier);
}
```

### 7.2 API 端点规划

```
POST   /api/auth/login          # 登录
POST   /api/auth/register       # 注册
GET    /api/user/status         # 获取状态
POST   /api/user/stats          # 分配属性点

GET    /api/activities          # 获取活动记录
POST   /api/activities          # 手动记录活动

GET    /api/tasks               # 获取任务列表
POST   /api/tasks               # 创建任务
POST   /api/tasks/:id/complete  # 完成任务

GET    /api/soldiers            # 获取士兵列表
POST   /api/soldiers/summon     # 召唤士兵

GET    /api/dungeons            # 获取副本列表
POST   /api/dungeons/:id/start  # 开始副本

GET    /api/shop                # 商店物品
POST   /api/shop/buy            # 购买物品
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-04-04 | 初始设计文档 |

---

*「暗影君主啊，这份蓝图已备好。何时出征，听您号令。」*
