---
name: dingtalk-ai-table
description: 钉钉多维表格数据写入。通过 webhook 方式将舆情分析结果写入钉钉多维表格。舆情结果经分析后，需要持久化到多维表格进行展示和管理时使用此技能。触发词：写入表格、多维表格、钉钉表格、数据写入、AI table。
---

# 钉钉多维表格写入

将舆情分析结果写入钉钉多维表格。

## 数据源

Webhook 地址从项目配置的 `ai_table_webhook` 字段获取。

**非 OpenClaw API 端点**，是钉钉多维表格的 webhook 地址。

## 认证

使用项目配置中的 `ai_table_webhook` 字段作为请求地址（无需额外认证头）。

## 写入单条数据

```json
{
  "skill": "dingtalk-ai-table",
  "action": "write",
  "params": {
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

```json
{
  "skill": "dingtalk-ai-table",
  "action": "batch_write",
  "params": {
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
}
```

## 舆情倾向

| 值 | 说明 |
|----|------|
| 正向 | 正面评价 |
| 负向 | 负面评价 |
| 中性 | 客观陈述 |
| 预警 | 需要关注 |

详细 API 文档参见 [references/api.md](references/api.md)
