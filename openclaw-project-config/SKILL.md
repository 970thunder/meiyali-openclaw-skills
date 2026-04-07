---
name: openclaw-project-config
description: 舆情项目配置管理。用于获取、更新、创建舆情项目配置信息，包括产品信息、舆情标准、关键词、Webhook播报配置等。当需要查询项目设置、更新项目参数、获取项目列表、管理舆情配置时使用此技能。触发词：获取项目配置、更新项目、查询项目列表、舆情配置管理、关键词管理。
---

# 舆情项目配置管理

获取和管理舆情监控项目配置。

## ⚠️ 首次使用必读

### 1. API Key 配置（必需）

所有 API 请求都需要有效的 API Key：

```bash
# 创建配置目录
mkdir -p ~/.openclaw/workspace

# 添加 API Key
echo "OPENCLAW_API_KEY=your_api_key_here" >> ~/.openclaw/workspace/.env.meiyali
```

> 📌 **如何获取 API Key？**
> 请联系管理员获取 OpenClaw 平台的 API Key

### 2. API 端点

| 操作 | 端点 | 方法 |
|------|------|------|
| 获取项目 | `http://127.0.0.1:8888/openclaw/project/find?id={id}` | GET |
| 获取列表 | `http://127.0.0.1:8888/openclaw/project/list` | GET |
| 创建项目 | `http://127.0.0.1:8888/openclaw/project/create` | POST |
| 更新项目 | `http://127.0.0.1:8888/openclaw/project/update` | PUT |
| 删除项目 | `http://127.0.0.1:8888/openclaw/project/delete` | DELETE |
| 批量删除 | `http://127.0.0.1:8888/openclaw/project/deleteByIds` | DELETE |

### 3. 认证

请求头：`api-key: <用户ApiKey>`

> ⚠️ **必须配置 API Key**，否则所有请求都会返回 401 错误

## 项目操作

### 获取项目

```json
{
  "skill": "openclaw-project-config",
  "action": "get_project",
  "params": { "id": <项目ID> }
}
```

### 获取项目列表

```json
{
  "skill": "openclaw-project-config",
  "action": "list_projects",
  "params": { "page": 1, "pageSize": 10 }
}
```

### 创建项目

```json
{
  "skill": "openclaw-project-config",
  "action": "create_project",
  "params": {
    "project_name": "猫粮舆情监控",
    "brand_description": "XX品牌猫粮",
    "brand_tags_description": "宠物/猫粮/口碑",
    "competing_brand_description": "YY品牌，ZZ品牌",
    "search_key_list": "猫粮,营养餐,宠物食品",
    "webhook_broadcast_within_days": 7,
    "webhook_broadcast_configs": [
      {
        "config_name": "钉钉多维表格播报",
        "config_key": "dingding-ai-table",
        "webhook_url": "https://dingtalk.ai.table/webhook",
        "secret": "",
        "enable": true
      },
      {
        "config_name": "钉钉机器人播报",
        "config_key": "dingding-robot",
        "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
        "secret": "ding-secret",
        "enable": false
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
      },
      {
        "config_name": "中性",
        "config_key": "中性",
        "opinion_standard": "中性判断标准，如：客观陈述、无明显情感倾向",
        "broadcast_enable": false
      }
    ]
  }
}
```

> 📌 **字段说明：**
> - `search_key_list`: 关键词列表，逗号分隔
> - `webhook_broadcast_within_days`: Webhook 播报时间范围（天数），0 表示不限制
> - `webhook_broadcast_configs`: Webhook 播报配置数组
>   - `config_name`: 配置名称
>   - `config_key`: 配置唯一标识
>   - `webhook_url`: Webhook 地址
>   - `secret`: 签名密钥（钉钉需要）
>   - `enable`: 是否启用
> - `opinion_configs`: 舆情配置数组
>   - `config_name`: 配置名称（负面/正面/中性）
>   - `config_key`: 配置唯一标识
>   - `opinion_standard`: 舆情判断标准描述
>   - `broadcast_enable`: 是否启用播报

### 更新项目

```json
{
  "skill": "openclaw-project-config",
  "action": "update_project",
  "params": {
    "id": <项目ID>,
    "project_name": "猫粮舆情监控（更新）",
    "brand_description": "XX品牌猫粮（更新）",
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
        "opinion_standard": "更新后的负面判断标准",
        "broadcast_enable": true
      }
    ]
  }
}
```

### 删除项目

```json
{
  "skill": "openclaw-project-config",
  "action": "delete_project",
  "params": { "id": <项目ID> }
}
```

### 批量删除项目

```json
{
  "skill": "openclaw-project-config",
  "action": "delete_projects",
  "params": { "ids": [<项目ID1>, <项目ID2>] }
}
```

## 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `401 Unauthorized` | API Key 无效或未配置 | 配置有效的 `OPENCLAW_API_KEY` |
| `404 Not Found` | 项目不存在 | 检查 ID 是否正确 |
| `Validation failed` | 必填字段缺失 | 检查请求参数 |
| `已达到可创建舆情项目上限` | 会员项目数量已达上限 | 升级会员或删除已有项目 |

详细 API 文档参见 [references/api.md](references/api.md)
