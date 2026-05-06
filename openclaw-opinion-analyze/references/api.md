# openclaw-opinion-analyze API 参考

## 1) 分析

`POST /api/v1/opinion/analyze`

请求头：

`X-OpenClaw-API-Key: <relay_api_key>`

请求体（按作品）：

```json
{
  "project_id": 1776650331436,
  "work_id": 12345
}
```

请求体（按文本）：

```json
{
  "project_id": 1776650331436,
  "title": "标题",
  "content": "正文",
  "platform": "dy"
}
```

## 2) 写回

`POST /api/v1/opinions`

```json
{
  "project_id": 1776650331436,
  "work_id": 12345,
  "opinion_key": "中性",
  "opinion_direction": "品牌A",
  "opinion_think": "完整推理过程",
  "reason": "判断依据摘要"
}
```

## 3) 查询

- `GET /api/v1/works/{work_id}/opinion`
- `GET /api/v1/projects/{project_id}/opinion-summary?days=7`
