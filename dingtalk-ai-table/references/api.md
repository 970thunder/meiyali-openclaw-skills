# 钉钉多维表格 API 文档

## 说明

钉钉多维表格通过 webhook 方式写入数据，webhook 地址在项目配置中的 `ai_table_webhook` 字段获取。

## 端点

直接 POST 到项目配置的 `ai_table_webhook` URL

## 认证

使用项目配置中的 `ai_table_webhook` 字段作为请求地址。

## 写入单条数据

**请求体**:
```json
{
  "fields": {
    "title": "猫粮推荐",
    "opinion": "正向",
    "opinion_direction": "XX品牌",
    "reason": "内容积极正面",
    "author": "用户名",
    "link": "https://..."
  }
}
```

## 批量写入

**请求体**:
```json
{
  "records": [
    {
      "title": "猫粮推荐",
      "opinion": "正向",
      "opinion_direction": "XX品牌"
    },
    {
      "title": "猫粮测评",
      "opinion": "中性",
      "opinion_direction": "YY品牌"
    }
  ]
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| title | string | 作品标题 |
| opinion | string | 舆情倾向（正向/负向/中性/预警） |
| opinion_direction | string | 主体品牌 |
| reason | string | 分析原因 |
| author | string | 作者 |
| link | string | 作品链接 |
| publish_time | string | 发布时间 |

## 舆情倾向枚举

| 值 | 说明 |
|----|------|
| 正向 | 正面评价 |
| 负向 | 负面评价 |
| 中性 | 客观陈述 |
| 预警 | 需要关注 |

## 响应

```json
{
  "code": 0,
  "data": {
    "success": true,
    "errcode": 0,
    "errmsg": "ok"
  },
  "msg": "成功"
}
```

## 错误处理

| errcode | 说明 |
|---------|------|
| 0 | 成功 |
| 40014 | access_token 无效 |
| 40078 | robot 不存在 |
| 43004 | 需要 POST 请求 |
| 90001 | 安全限制 |
