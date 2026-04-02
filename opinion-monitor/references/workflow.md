# 舆情监控工作流

本文档描述 opinion-monitor 编排层如何协调多个子 Skill 完成完整的舆情监控流程。

## 流程概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户触发                                       │
│                     "执行项目 30001 的舆情监控"                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Step 1: 获取项目配置                                 │
│  Skill: openclaw-project-config                                             │
│  Action: get_project                                                         │
│  输入: project_id=30001                                                       │
│  输出: { id, project_name, brand_description, webhook_url, ai_table_webhook }│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Step 2: 获取场景配置                                 │
│  Skill: openclaw-project-config                                             │
│  Action: get_scene                                                           │
│  输入: scene_id=40001                                                         │
│  输出: { id, name, description, search_keys[], params{} }                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Step 3-4: 并行下发插件任务                             │
│                                                                              │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐          │
│  │  Skill: meiyali-plugin-dy   │    │  Skill: meiyali-plugin-xhs │          │
│  │  Action: dispatch_task      │    │  Action: dispatch_task     │          │
│  │  输入:                       │    │  输入:                      │          │
│  │    keywords="猫粮,宠物食品"  │    │    keywords="宠物食品,营养餐"│          │
│  │    count=30                 │    │    count=20                │          │
│  │    sorts=[default,time_desc] │    │    sorts=[default,time_desc]│          │
│  │  输出: task_id=uuid-dy-xxx   │    │  输出: task_id=uuid-xhs-xxx │          │
│  └─────────────────────────────┘    └─────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Step 5: 轮询任务结果                                │
│  Skill: openclaw-task-polling (或 meiyali-plugin-task-response)            │
│  Action: poll_until_complete                                                │
│  输入: task_ids=[uuid-dy-xxx, uuid-xhs-xxx]                                  │
│  轮询: 每 5 秒检查一次，直到 task_status=2 或超时                            │
│  输出: { dy: { items[] }, xhs: { items[] } }                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Step 6: 舆情分析与归类（内置逻辑）                         │
│                                                                              │
│  基于 description 解析舆情标准:                                                │
│    品牌描述:卫仕,醇粹                                                          │
│    竞品描述:皇家,渴望                                                          │
│    正向关键词:推荐,好,喜欢                                                     │
│    负向关键词:差,避雷,坑                                                       │
│                                                                              │
│  对每个 item 进行判断:                                                        │
│    - 提及自有品牌 + 正向 → 正向                                               │
│    - 提及自有品牌 + 负向 → 负向                                               │
│    - 提及竞品 + 负向 → 预警                                                   │
│    - 其他 → 中性                                                              │
│                                                                              │
│  输出: analyses[] = [ { work_id, opinion, opinion_direction, opinion_think, reason } ] │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Step 7: 去重检查                                     │
│  Skill: openclaw-opinion-callback                                           │
│  Action: check_duplicate                                                      │
│  输入: work_ids=[item-001, item-002, ...]                                   │
│  输出: existing_ids=[已存在的work_id]                                        │
│  过滤: analyses = analyses.filter(i => !existing_ids.includes(i.work_id)) │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Step 8: 批量上传舆情结果                                 │
│  Skill: openclaw-opinion-callback                                           │
│  Action: batch_upload                                                        │
│  输入: { work_project_id, scene_id, analyses[] }                            │
│  输出: success_count, fail_count                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Step 9: 推送钉钉通知                                     │
│  Skill: dingtalk-ai-table (或 webhook)                                      │
│  Action: send_message                                                        │
│  输入: { webhook_url, message: 舆情统计摘要 }                                 │
│  输出: success/fail                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Step 10: 标记任务完成                                    │
│  Skill: openclaw-project-config                                             │
│  Action: finish_task                                                         │
│  条件: 所有作品都完成舆情分析                                                  │
│  输入: task_ids=[uuid-dy-xxx, uuid-xhs-xxx]                                 │
│  输出: task_status=3 (finished)                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              流程完成                                        │
│                   摘要: 正向 N, 负向 M, 预警 K                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 数据流

```
project_id, scene_id
        │
        ▼
┌───────────────────┐
│ get_project       │ ──→ project_name, brand_description
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ get_scene         │ ──→ search_keys, params, description
└───────────────────┘
        │
        ├──────────────────────┐
        ▼                      ▼
┌───────────────┐      ┌───────────────┐
│ dispatch dy   │      │ dispatch xhs  │
│ keywords: ... │      │ keywords: ... │
└───────────────┘      └───────────────┘
        │                      │
        ▼                      ▼
┌───────────────┐      ┌───────────────┐
│ task_id_dy    │      │ task_id_xhs   │
└───────────────┘      └───────────────┘
        │                      │
        └──────────┬───────────┘
                   ▼
        ┌─────────────────────┐
        │ poll_until_complete │
        └─────────────────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ items (merged)      │
        └─────────────────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ opinion_analysis()  │ ──→ analyses[]
        │ (内置逻辑)           │
        └─────────────────────┘
                   │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐    ┌───────────────┐
│ check_duplicate│    │ filter new   │
└───────────────┘    └───────────────┘
        │                   │
        ▼                   ▼
        ┌───────────────────────┐
        │ batch_upload          │
        │ (仅新数据)            │
        └───────────────────────┘
        │
        ▼
        ┌───────────────────────┐
        │ finish_task           │
        │ (status = 3)          │
        └───────────────────────┘
```

## API 调用序列

| 步骤 | HTTP Method | Endpoint | Skill | Action |
|------|-------------|----------|-------|--------|
| 1 | GET | `/openclaw/project/<id>` | openclaw-project-config | get_project |
| 2 | GET | `/openclaw/scene/<id>` | openclaw-project-config | get_scene |
| 3 | POST | `/openclaw/task/dispatch` | meiyali-plugin-dy | dispatch_task |
| 4 | POST | `/openclaw/task/dispatch` | meiyali-plugin-xhs | dispatch_task |
| 5 | GET | `/openclaw/task/<id>` (轮询) | - | poll_until_complete |
| 6 | - | (内置逻辑) | - | opinion_analysis |
| 7 | POST | `/openclaw/opinion/check_duplicate` | openclaw-opinion-callback | check_duplicate |
| 8 | POST | `/openclaw/opinion/batch_upload` | openclaw-opinion-callback | batch_upload |
| 9 | POST | `<webhook_url>` | dingtalk-ai-table | send_message |
| 10 | POST | `/openclaw/task/finish` | openclaw-project-config | finish_task |

## 错误处理

| 错误场景 | 处理策略 | 重试次数 |
|---------|---------|---------|
| API 请求失败 (网络) | 指数退避重试 | 3 次 |
| 任务下发失败 | 记录错误，继续其他平台 | 0 |
| 轮询超时 | 跳过该任务，继续处理已完成 | 0 |
| 去重检查失败 | 跳过去重，直接上传 | 0 |
| 上传失败 | 记录失败项，最终汇总报告 | 2 次 |
| 钉钉推送失败 | 记录错误，不阻塞流程 | 0 |
| 标记完成失败 | 记录错误，下次可重试 | 0 |

## 状态流转

```
Task Status:
  0 (created) ──→ 1 (dispatched) ──→ 2 (success) ──→ 3 (finished)

  任务下发后变为 1
  插件执行完成后变为 2
  所有作品完成舆情分析后变为 3
```

## 并发与限流

- Step 3-4 并行下发两个平台任务
- Step 5 串行轮询（可改为并行轮询）
- Step 7-8 串行处理（去重 → 过滤 → 上传）
- 建议轮询间隔: 5 秒
- 最大轮询次数: 60 次 (5 分钟超时)
