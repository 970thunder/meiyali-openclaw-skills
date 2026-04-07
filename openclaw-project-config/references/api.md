# 项目配置 API 文档

## 认证

请求头：`api-key: <用户ApiKey>`

## 项目操作

### 获取项目

**端点**: `GET /openclaw/project/find?id={projectId}`

**响应**:
```json
{
  "code": 0,
  "data": {
    "id": 30001,
    "project_name": "猫粮舆情监控",
    "brand_description": "XX品牌猫粮",
    "brand_tags_description": "宠物/猫粮/口碑",
    "competing_brand_description": "YY品牌，ZZ品牌",
    "yunfan_id": 123,
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
        "opinion_standard": "负面判断标准",
        "broadcast_enable": true
      },
      {
        "config_name": "正面",
        "config_key": "正面",
        "opinion_standard": "正面判断标准",
        "broadcast_enable": false
      },
      {
        "config_name": "中性",
        "config_key": "中性",
        "opinion_standard": "中性判断标准",
        "broadcast_enable": false
      }
    ],
    "created_at": "2026-03-01T10:00:00Z",
    "updated_at": "2026-03-15T08:00:00Z"
  },
  "msg": "成功"
}
```

### 获取列表

**端点**: `GET /openclaw/project/list`

**参数**:
- `page` - 页码，默认 1
- `pageSize` - 每页数量，默认 10
- `project_name` - 项目名称模糊搜索
- `brand_description` - 品牌描述模糊搜索

**响应**:
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "id": 30001,
        "project_name": "猫粮舆情监控",
        "brand_description": "XX品牌猫粮",
        "competing_brand_description": "YY品牌，ZZ品牌",
        "brand_tags_description": "宠物/猫粮/口碑",
        "yunfan_id": 123,
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
            "opinion_standard": "负面判断标准",
            "broadcast_enable": true
          }
        ],
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-15T08:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 10
  },
  "msg": "获取成功"
}
```

### 创建项目

**端点**: `POST /openclaw/project/create`

**请求体**:
```json
{
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
      "opinion_standard": "负面判断标准",
      "broadcast_enable": true
    },
    {
      "config_name": "正面",
      "config_key": "正面",
      "opinion_standard": "正面判断标准",
      "broadcast_enable": false
    },
    {
      "config_name": "中性",
      "config_key": "中性",
      "opinion_standard": "中性判断标准",
      "broadcast_enable": false
    }
  ]
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `project_name` | string | 项目名称（必填） |
| `brand_description` | string | 品牌描述 |
| `brand_tags_description` | string | 品牌标签描述 |
| `competing_brand_description` | string | 竞品品牌描述 |
| `search_key_list` | string | 关键词列表，逗号分隔 |
| `webhook_broadcast_within_days` | number | Webhook 播报时间范围（天数），0 表示不限制 |
| `webhook_broadcast_configs` | array | Webhook 播报配置数组 |
| `opinion_configs` | array | 舆情配置数组 |

**webhook_broadcast_configs 字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `config_name` | string | 配置名称 |
| `config_key` | string | 配置唯一标识 |
| `webhook_url` | string | Webhook 地址 |
| `secret` | string | 签名密钥（钉钉需要） |
| `enable` | boolean | 是否启用 |

**opinion_configs 字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `config_name` | string | 配置名称（负面/正面/中性） |
| `config_key` | string | 配置唯一标识 |
| `opinion_standard` | string | 舆情判断标准描述 |
| `broadcast_enable` | boolean | 是否启用播报 |

**说明**:
- 若会员配置了 `max_project_number` 且已达到上限，创建会失败并返回：`已达到可创建舆情项目上限`
- `webhook_broadcast_configs` 用于统一配置播报方式，服务端会按 `enable=true` 的配置决定播报渠道

### 更新项目

**端点**: `PUT /openclaw/project/update`

**请求体**:
```json
{
  "id": 30001,
  "project_name": "猫粮舆情监控（更新）",
  "brand_description": "XX品牌猫粮（更新）",
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
```

### 删除项目

**端点**: `DELETE /openclaw/project/delete`

**请求体**:
```json
{ "id": 30001 }
```

### 批量删除项目

**端点**: `DELETE /openclaw/project/deleteByIds`

**请求体**:
```json
{ "ids": [30001, 30002] }
```

## 错误码

| code | 说明 |
|------|------|
| 0 | 成功 |
| 7 | 业务失败 |
| 401 | 未授权 |
| 404 | 资源不存在 |
