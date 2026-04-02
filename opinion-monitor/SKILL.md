---
name: opinion-monitor
description: 舆情监控工作流（编排层）。完整的舆情监控流程编排，依次调用子 Skill：获取配置 → 下发任务 → 轮询结果 → 舆情分析 → 数据上传。触发词：舆情监控、启动监控、执行舆情、监控流程、一键舆情。
---

# 舆情监控工作流（编排层）

本 Skill 是**编排层**，负责协调多个子 Skill 完成完整的舆情监控流程。

## ⚠️ 首次使用必读

### 1. API Key 配置（必需）

```bash
# 创建配置目录
mkdir -p ~/.openclaw/workspace

# 添加 API Key（联系管理员获取）
echo "OPENCLAW_API_KEY=your_api_key_here" >> ~/.openclaw/workspace/.env.meiyali
```

### 2. 前置条件检查清单

| 检查项 | 说明 | 未满足时的错误 |
|--------|------|---------------|
| API Key 已配置 | 配置 `OPENCLAW_API_KEY` | `401 Unauthorized` |
| 项目存在 | 提供有效的 `project_id` | `项目不存在` |
| 场景存在 | 提供有效的 `scene_id` | `场景不存在` |
| 本地插件服务运行 | 启动浏览器插件 | `Plugin service unavailable` |

---

## 编排流程概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     opinion-monitor 编排层                                  │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 1: 获取项目配置                                                   │
  │ Skill: openclaw-project-config → get_project                           │
  │ 输入: project_id                                                        │
  │ 输出: { project_name, brand_description, webhook_url, ... }            │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 2: 获取场景配置                                                   │
  │ Skill: openclaw-project-config → get_scene                            │
  │ 输入: scene_id                                                          │
  │ 输出: { search_keys, description (舆情标准), params }                  │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 3: 下发抖音任务                                                   │
  │ Skill: meiyali-plugin-dy → dispatch_task                              │
  │ 输入: { keywords, count, sorts, timeFilter }                           │
  │ 输出: task_id (后续轮询用)                                             │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 4: 下发小红书任务                                                 │
  │ Skill: meiyali-plugin-xhs → dispatch_task                             │
  │ 输入: { keywords, count, sorts, timeFilter }                          │
  │ 输出: task_id (后续轮询用)                                             │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 5: 轮询任务结果                                                   │
  │ Skill: meiyali-plugin-task-response → poll_until_complete             │
  │ 输入: task_id(s)                                                       │
  │ 输出: { items[], task_status }                                        │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 6: 舆情分析（内置逻辑）                                           │
  │ 基于场景 description 中的舆情标准进行分析                               │
  │ 输入: { items[], criteria (从 description 解析) }                     │
  │ 输出: { opinion, opinion_direction, reason } per item                  │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 7: 去重检查                                                       │
  │ Skill: openclaw-opinion-callback → check_duplicate                    │
  │ 输入: { work_ids[] }                                                    │
  │ 输出: { existing_ids[] }                                               │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 8: 上传舆情结果                                                   │
  │ Skill: openclaw-opinion-callback → upload                            │
  │ 输入: { work_id, opinion, opinion_direction, reason }                  │
  │ 输出: success/fail                                                     │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 9: 标记任务完成                                                   │
  │ Skill: openclaw-project-config → finish_task                          │
  │ 条件: 所有作品都完成舆情分析                                           │
  │ 输入: task_ids[]                                                        │
  │ 输出: task_status = 3                                                  │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 完整调用示例

### Agent 调用模板

当用户说「执行舆情监控」时，按以下步骤执行：

#### Step 1: 获取项目配置

```json
{
  "skill": "openclaw-project-config",
  "action": "get_project",
  "params": {
    "project_id": <项目ID>
  }
}
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "id": 30001,
    "project_name": "猫粮舆情监控",
    "brand_description": "品牌描述:卫仕,醇粹\n正向关键词:推荐,好,喜欢\n负向关键词:差,避雷,坑",
    "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
    "ai_table_webhook": "https://dingtalk.ai.table/webhook"
  }
}
```

#### Step 2: 获取场景配置

```json
{
  "skill": "openclaw-project-config",
  "action": "get_scene",
  "params": {
    "scene_id": <场景ID>
  }
}
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "id": 40001,
    "name": "默认搜索场景",
    "description": "品牌描述:卫仕,醇粹\n竞品描述:皇家,渴望\n正向关键词:推荐,好,喜欢,种草\n负向关键词:差,避雷,坑,曝光",
    "search_keys": [
      { "platform": "抖音", "search_key": "猫粮,宠物食品" },
      { "platform": "小红书", "search_key": "宠物食品,营养餐" }
    ],
    "params": {
      "dy": { "count": 30, "sorts": ["default", "time_descending"] },
      "xhs": { "count": 20, "sorts": ["default", "time_descending"] }
    }
  }
}
```

#### Step 3 & 4: 下发插件任务

根据 `search_keys` 分别下发抖音和小红书任务：

**抖音任务：**
```json
{
  "skill": "meiyali-plugin-dy",
  "action": "dispatch_task",
  "params": {
    "keywords": "猫粮,宠物食品",
    "count": 30,
    "sorts": ["default", "time_descending"],
    "timeFilter": "7",
    "project_id": <项目ID>,
    "scene_id": <场景ID>
  }
}
```

**小红书任务：**
```json
{
  "skill": "meiyali-plugin-xhs",
  "action": "dispatch_task",
  "params": {
    "keywords": "宠物食品,营养餐",
    "count": 20,
    "sorts": ["default", "time_descending"],
    "timeFilter": "7",
    "project_id": <项目ID>,
    "scene_id": <场景ID>
  }
}
```

**预期响应（两个任务）：**
```json
{
  "code": 0,
  "data": {
    "task_id": "uuid-xxxx-xxxx"
  }
}
```

#### Step 5: 轮询任务结果

```json
{
  "skill": "meiyali-plugin-task-response",
  "action": "poll_until_complete",
  "params": {
    "task_ids": ["<dy_task_id>", "<xhs_task_id>"],
    "max_wait_seconds": 300
  }
}
```

**预期响应：**
```json
{
  "code": 0,
  "data": {
    "task_id": "uuid-xxxx-xxxx",
    "task_status": 2,
    "items": [
      {
        "id": "item-001",
        "title": "猫粮推荐",
        "content": "最近给猫主子换了卫仕猫粮...",
        "author": "用户A",
        "platform": "dy"
      }
    ]
  }
}
```

#### Step 6-8: 舆情分析与上传

舆情分析基于 `description` 中的标准进行，然后调用上传：

```json
{
  "skill": "openclaw-opinion-callback",
  "action": "batch_upload",
  "params": {
    "work_project_id": <项目ID>,
    "scene_id": <场景ID>,
    "analyses": [
      {
        "work_id": "item-001",
        "opinion": "正向",
        "opinion_direction": "卫仕",
        "opinion_think": "1. 品牌识别：内容提到「卫仕猫粮」「猫咪很爱吃」\n2. 关键词匹配：检测到正向关键词「推荐」「爱吃」\n3. 情感分析：语气积极，用户对产品满意\n4. 舆情判断：提及自有品牌（卫仕）+ 正向关键词 → 正向\n5. 结论：该内容为正向舆情，建议收集更多类似用户体验反馈",
        "reason": "提及品牌「卫仕」且包含正向关键词「推荐」"
      }
    ]
  }
}
```

**⚠️ 注意**：`opinion_think` 字段必须包含完整的 AI 思考判断过程，详见 [openclaw-opinion-callback/SKILL.md](../openclaw-opinion-callback/SKILL.md)

#### Step 9: 标记任务完成

```json
{
  "skill": "openclaw-project-config",
  "action": "finish_task",
  "params": {
    "task_ids": ["<dy_task_id>", "<xhs_task_id>"]
  }
}
```

---

## 舆情标准解析

场景 `description` 支持以下格式：

```
品牌描述:卫仕,醇粹,大玛仕
竞品描述:皇家,渴望,爱肯拿
正向关键词:推荐,好,喜欢,种草,好评,回购
负向关键词:差,避雷,坑,差评,曝光,垃圾
```

### 判断规则

| 条件 | 舆情结果 |
|------|---------|
| 提及竞品 + 负向关键词 | 预警 |
| 提及竞品 + 正向关键词 | 中性 |
| 提及自有品牌 + 正向关键词 | 正向 |
| 提及自有品牌 + 负向关键词 | 负向 |
| 未提及品牌 | 中性 |

---

## 子 Skill 依赖关系

| 步骤 | Skill | 依赖的前置 Skill |
|------|-------|-----------------|
| 1 | openclaw-project-config | 无 |
| 2 | openclaw-project-config | Step 1 |
| 3 | meiyali-plugin-dy | Step 2 |
| 4 | meiyali-plugin-xhs | Step 2 |
| 5 | meiyali-plugin-task-response | Step 3, 4 |
| 7 | openclaw-opinion-callback | Step 5, 6 |
| 8 | openclaw-opinion-callback | Step 7 |
| 9 | openclaw-project-config | Step 8 |

---

## 便捷执行方式

对于不需要 Agent 介入的场景，可直接运行脚本：

```bash
# 完整流程
python3 scripts/opinion_monitor.py --mode full <project_id> <scene_id>

# 仅下发任务
python3 scripts/opinion_monitor.py --mode dispatch <project_id> <scene_id>

# 仅处理已完成任务
python3 scripts/opinion_monitor.py --mode process <project_id>
```

---

## 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `401 Unauthorized` | API Key 无效或未配置 | 配置 `OPENCLAW_API_KEY` |
| `项目不存在` | project_id 错误 | 检查并提供正确的 project_id |
| `场景不存在` | scene_id 错误 | 检查并提供正确的 scene_id |
| `Plugin service unavailable` | 插件服务未启动 | 启动浏览器插件并确保已连接 |
| `轮询超时` | 任务执行时间过长 | 增加 max_wait_seconds 或重试 |

详细 API 参见各子 Skill 的 references/api.md
