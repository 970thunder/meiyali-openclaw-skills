# openclaw-opinion-callback API（Relay）

## 写回舆情

`POST /api/v1/opinions`

请求头：

`X-OpenClaw-API-Key: <relay_api_key>`

请求体：

```json
{
  "project_id": 1776650331436,
  "work_id": 12345,
  "opinion_key": "正面",
  "opinion_direction": "品牌A",
  "opinion_think": "完整推理过程",
  "reason": "判断依据摘要"
}
```

## 查询单作品舆情

`GET /api/v1/works/{work_id}/opinion`

## 查询项目舆情汇总

`GET /api/v1/projects/{project_id}/opinion-summary?days=7`
