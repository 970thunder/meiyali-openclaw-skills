# 内容提取 API 文档

## 端点

`POST /openclaw/media/extract`

## 认证

请求头：`api-key: <用户ApiKey>`

## 扣费说明

- 先校验用户是否存在有效 token 套餐（未过期且余额 > 0）
- n8n 成功后在返回数据前扣费
- 扣费数量使用 `usage.total_tokens`
- 扣费失败会返回错误且不会返回 n8n 数据

## 单个提取

**请求体**:
```json
{
  "material_urls": ["https://example.com/image1.png"],
  "content": "可选的关联文本，如标题或简介"
}
```

### 参数说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| material_urls | string[] | 是 | 图片或视频 URL 列表，最多 10 个 |
| content | string | 否 | 可选的关联文本，用于辅助理解 |

**响应**:
```json
{
  "code": 0,
  "data": {
    "summary": "这是内容的主要信息总结...",
    "usage": {
      "input_tokens": 100,
      "output_tokens": 50,
      "total_tokens": 150
    }
  },
  "msg": "成功"
}
```

## 批量提取

**请求体**:
```json
{
  "items": [
    {
      "item_id": "note_123",
      "material_urls": ["https://example.com/1.jpg"]
    },
    {
      "item_id": "note_456",
      "material_urls": ["https://example.com/2.jpg", "https://example.com/3.jpg"]
    }
  ],
  "content": "猫粮推荐"
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "results": [
      {
        "item_id": "note_123",
        "summary": "内容摘要...",
        "usage": { "total_tokens": 100 }
      }
    ],
    "total_usage": { "total_tokens": 250 }
  },
  "msg": "成功"
}
```

## 错误码

| 错误码 | 说明 | 处理方式 |
|-------|------|---------|
| 0 | 成功 | 继续下一步 |
| 7 | Token余额不足 | 请充值 |
| 7 | n8n调用失败 | 稍后重试 |
| 7 | 扣费失败 | 任务已取消 |
