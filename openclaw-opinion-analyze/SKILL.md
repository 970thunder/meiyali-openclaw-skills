---
name: openclaw-opinion-analyze
description: Relay 舆情分析与写回。用于调用分析接口并写入作品舆情结果。触发词：舆情分析、分析作品、写回舆情、opinion analyze。
---

# Relay 舆情分析与写回

## 迁移说明

- 旧 `/openclaw/opinion/*` 链路不再作为本地主链路。
- 当前统一使用 Relay `/api/v1/opinion/analyze` 与 `/api/v1/opinions`。

## 认证

请求头：`X-OpenClaw-API-Key: <relay_api_key>`

## 分析接口

```text
POST /api/v1/opinion/analyze
```

请求体示例：

```json
{
  "project_id": 1776650331436,
  "work_id": 12345
}
```

也支持直接传文本：

```json
{
  "project_id": 1776650331436,
  "title": "作品标题",
  "content": "作品正文",
  "platform": "xhs"
}
```

## 写回接口

```text
POST /api/v1/opinions
```

请求体示例：

```json
{
  "project_id": 1776650331436,
  "work_id": 12345,
  "opinion_key": "负面",
  "opinion_direction": "品牌A",
  "opinion_think": "基于项目规则与内容语义的完整判断过程",
  "reason": "用户投诉售后体验差，情绪显著负面"
}
```

## 查询接口

- `GET /api/v1/works/{work_id}/opinion`
- `GET /api/v1/projects/{project_id}/opinion-summary?days=7`

## 约束

- 禁止使用词典匹配（如 `negativeWords/positiveWords`）直接判定正负面。
- 必须结合项目配置与内容语义输出 `opinion_think` 和 `reason`。

## 参考

- [api.md](references/api.md)
