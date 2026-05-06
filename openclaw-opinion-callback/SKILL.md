---
name: openclaw-opinion-callback
description: Relay 舆情结果回写。将分析结果写入本地 Relay 数据库，并供项目查询/汇总使用。触发词：回写舆情、上传分析结果、保存舆情。
---

# Relay 舆情回写

## 迁移说明

- 旧 `POST /openclaw/opinion/upload` 不再作为本地主链路。
- 当前统一写回 Relay：`POST /api/v1/opinions`。

## 认证

请求头：`X-OpenClaw-API-Key: <relay_api_key>`

## 回写接口

```text
POST /api/v1/opinions
```

请求示例：

```json
{
  "project_id": 1776650331436,
  "work_id": 12345,
  "opinion_key": "负面",
  "opinion_direction": "品牌A",
  "opinion_think": "1. 内容概述...\n2. 主体识别...\n3. 情绪依据...\n4. 判断过程...\n5. 结论...",
  "reason": "内容表达对品牌售后服务强烈不满，整体为负面舆情。"
}
```

## 必填字段约束

- `project_id`：项目数字主键
- `work_id`：作品数字主键
- `opinion_key`：正面/负面/中性
- `opinion_direction`：主体品牌或对象
- `opinion_think`：完整判断过程（必须是语义推理，不是词典命中）
- `reason`：简洁判断依据

## 查询接口

- `GET /api/v1/works/{work_id}/opinion`
- `GET /api/v1/projects/{project_id}/opinion-summary?days=7`

## 约束

- 禁止使用 `negativeWords/positiveWords` 之类词典匹配作为最终判定逻辑。
- 必须结合项目配置（品牌、竞品、判断标准）与内容语义生成结果。

详细 API 文档参见 [references/api.md](references/api.md)
