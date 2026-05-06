---
name: opinion-monitor
description: 舆情监控工作流（编排层）。完整的舆情监控流程编排，依次调用子 Skill：获取项目配置 → 下发任务 → 轮询结果 → 舆情分析 → 数据上传。触发词：舆情监控、启动监控、执行舆情、监控流程、一键舆情。
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
  │ 输出: { project_name, brand_description, search_key_list,               │
  │        webhook_broadcast_configs, opinion_configs }                      │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 2: 下发抖音任务                                                   │
  │ Skill: meiyali-plugin-dy → dispatch_task                              │
  │ 输入: { keywords, count, sorts, timeFilter }                           │
  │ 输出: task_id (后续轮询用)                                             │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 3: 下发小红书任务                                                 │
  │ Skill: meiyali-plugin-xhs → dispatch_task                             │
  │ 输入: { keywords, count, sorts, timeFilter }                          │
  │ 输出: task_id (后续轮询用)                                            │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 4: 轮询任务结果                                                   │
  │ Skill: meiyali-plugin-task-response → poll_until_complete             │
  │ 输入: task_id(s)                                                       │
  │ 输出: { items[], task_status }                                        │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 5: 舆情分析（内置逻辑）                                           │
  │ 基于项目 opinion_configs 中的舆情标准进行分析                           │
  │ 输入: { items[], criteria (从 opinion_configs 解析) }                 │
  │ 输出: { opinion_key, opinion_direction, opinion_think, reason }       │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 6: 查询已有记录                                                   │
  │ Skill: openclaw-opinion-callback → list                               │
  │ 输入: { work_project_id, work_ids[] }                                  │
  │ 输出: { existing_records[] }                                           │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 7: 上传舆情结果                                                   │
  │ Skill: openclaw-opinion-callback → upload                             │
  │ 输入: { work_id, opinion_key, opinion_direction, opinion_think,        │
  │        reason, work_project_id }                                       │
  │ 输出: success/fail                                                     │
  └────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Step 8: 标记任务完成                                                   │
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
    "id": <项目ID>
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
    "brand_description": "XX品牌猫粮",
    "brand_tags_description": "宠物/猫粮/口碑",
    "competing_brand_description": "YY品牌，ZZ品牌",
    "yunfan_id": 123,
    "search_key_list": "猫粮,营养餐,宠物食品",
    "webhook_broadcast_within_days": 7,
    "webhook_broadcast_configs": [
      {
        "config_name": "钉钉多维表格播报",
        "config_key": "dingding-ai-table",
        "webhook_url": "https://dingtalk.ai.table/webhook",
        "secret": "",
        "enable": true
      }
    ],
    "opinion_configs": [
      {
        "config_name": "负面",
        "config_key": "负面",
        "opinion_standard": "负面判断标准，如：产品质量问题、用户投诉等",
        "broadcast_enable": true
      },
      {
        "config_name": "正面",
        "config_key": "正面",
        "opinion_standard": "正面判断标准，如：用户好评、品牌赞美等",
        "broadcast_enable": false
      }
    ],
    "created_at": "2026-03-01T10:00:00Z",
    "updated_at": "2026-03-15T08:00:00Z"
  },
  "msg": "成功"
}
```

#### Step 2 & 3: 下发插件任务

根据 `search_key_list` 分别下发抖音和小红书任务：

**抖音任务：**
```json
{
  "skill": "meiyali-plugin-dy",
  "action": "dispatch_task",
  "params": {
    "keywords": "猫粮,营养餐,宠物食品",
    "count": 30,
    "sorts": ["default", "time_descending"],
    "timeFilter": "7",
    "project_id": <项目ID>
  }
}
```

**小红书任务：**
```json
{
  "skill": "meiyali-plugin-xhs",
  "action": "dispatch_task",
  "params": {
    "keywords": "猫粮,营养餐,宠物食品",
    "count": 20,
    "sorts": ["default", "time_descending"],
    "timeFilter": "7",
    "project_id": <项目ID>
  }
}
```

#### Step 4: 轮询任务结果

```json
{
  "skill": "meiyali-plugin-task-response",
  "action": "poll_until_complete",
  "params": {
    "task_ids": [<抖音task_id>, <小红书task_id>],
    "timeout": 300
  }
}
```

#### Step 5: 舆情分析

根据 `opinion_configs` 中的配置进行分析：

```json
{
  "opinion_configs": [
    {
      "config_name": "负面",
      "config_key": "负面",
      "opinion_standard": "负面判断标准，如：产品质量问题、用户投诉等",
      "broadcast_enable": true
    },
    {
      "config_name": "正面",
      "config_key": "正面",
      "opinion_standard": "正面判断标准，如：用户好评、品牌赞美等",
      "broadcast_enable": false
    }
  ]
}
```

**分析逻辑**：
1. 解析 `opinion_configs` 获取舆情标准
2. 对每个作品内容匹配对应标准
3. 生成分析结果

#### Step 6: 查询已有记录（去重）

```json
{
  "skill": "openclaw-opinion-callback",
  "action": "list",
  "params": {
    "work_project_id": <项目ID>,
    "work_ids": [<work_id1>, <work_id2>, ...]
  }
}
```

#### Step 7: 上传舆情结果

```json
{
  "skill": "openclaw-opinion-callback",
  "action": "upload",
  "params": {
    "work_project_id": <项目ID>,
    "work_id": <作品ID>,
    "opinion_key": "正面",
    "opinion_direction": "自有品牌",
    "opinion_think": "1. 品牌识别：内容提到「XX品牌猫粮」\n2. 关键词匹配：检测到正向关键词「推荐」「爱吃」\n3. 情感分析：语气积极，用户对产品满意\n4. 舆情判断：提及自有品牌 + 正向关键词 → 正面\n5. 结论：该内容为正面舆情",
    "reason": "提及自有品牌且包含正向关键词"
  }
}
```

#### Step 8: 标记任务完成

```json
{
  "skill": "meiyali-plugin-task-response",
  "action": "finish_task",
  "params": {
    "task_ids": [<抖音task_id>, <小红书task_id>]
  }
}
```

---

## 舆情分析标准说明

### opinion_configs 配置示例

```json
[
  {
    "config_name": "负面",
    "config_key": "负面",
    "opinion_standard": "负面判断标准，如：产品质量问题、用户投诉、虚假宣传等",
    "broadcast_enable": true
  },
  {
    "config_name": "正面",
    "config_key": "正面",
    "opinion_standard": "正面判断标准，如：用户好评、品牌赞美、口碑推荐等",
    "broadcast_enable": true
  },
  {
    "config_name": "中性",
    "config_key": "中性",
    "opinion_standard": "中性判断标准，如：客观陈述、无明显情感倾向",
    "broadcast_enable": false
  }
]
```

### 舆情倾向枚举

| 值 | 说明 |
|----|------|
| 正面 | 正面评价 |
| 负面 | 负面评价 |
| 中性 | 客观陈述 |

---

## 常见错误排查

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `401 Unauthorized` | API Key 无效或未配置 | 配置有效的 `OPENCLAW_API_KEY` |
| `项目不存在` | 项目ID不存在或无权访问 | 检查 `project_id` 是否正确 |
| `Plugin service unavailable` | 插件服务未启动 | 启动浏览器插件服务 |

详细 API 文档参见 [references/workflow.md](references/workflow.md)
