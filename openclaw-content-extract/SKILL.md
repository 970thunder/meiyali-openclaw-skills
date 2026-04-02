---
name: openclaw-content-extract
description: 内容提取。通过 AI 提取视频/图文素材信息，封装 n8n 能力。当任务结果中的内容不足以进行舆情分析时（content 长度 < 100），调用此技能进行补充提取。触发词：提取素材、AI分析内容、补充信息、视频图文解析、n8n提取。
---

# 内容提取

提取视频/图文内容信息，补充舆情分析所需数据。

## API 端点

```
POST http://127.0.0.1:8888/openclaw/media/extract
```

## 认证

请求头：`api-key: <用户ApiKey>`

## 扣费说明

- 先校验用户是否存在有效 token 套餐
- n8n 成功后在返回数据前扣费
- 扣费数量使用 `usage.total_tokens`

## 单个提取

```json
{
  "skill": "openclaw-content-extract",
  "action": "extract",
  "params": {
    "material_urls": ["https://example.com/cover.jpg"],
    "content": "猫粮推荐"
  }
}
```

## 批量提取

```json
{
  "skill": "openclaw-content-extract",
  "action": "batch_extract",
  "params": {
    "items": [
      {
        "item_id": "note_123",
        "material_urls": ["https://example.com/1.jpg"]
      }
    ],
    "content": "猫粮推荐"
  }
}
```

## 返回格式

```json
{
  "code": 0,
  "data": {
    "summary": "这是内容的主要信息总结...",
    "usage": {
      "total_tokens": 150
    }
  },
  "msg": "成功"
}
```

详细 API 文档参见 [references/api.md](references/api.md)
