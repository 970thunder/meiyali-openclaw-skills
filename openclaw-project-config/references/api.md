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
    "webhook_broadcast_within_days": 30,
    "webhook_broadcast_configs": [
      {
        "config_name": "钉钉主推送",
        "config_key": "dingtalk_primary",
        "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
        "secret": "ding-secret",
        "enable": true
      }
    ],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
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

### 创建项目

**端点**: `POST /openclaw/project/create`

**请求体**:
```json
{
  "project_name": "猫粮舆情监控",
  "brand_description": "XX品牌猫粮",
  "brand_tags_description": "宠物/猫粮/口碑",
  "competing_brand_description": "YY品牌，ZZ品牌",
  "webhook_broadcast_within_days": 30,
  "webhook_broadcast_configs": [
    {
      "config_name": "钉钉主推送",
      "config_key": "dingtalk_primary",
      "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
      "secret": "ding-secret",
      "enable": true
    },
    {
      "config_name": "AI表格",
      "config_key": "ai_table",
      "webhook_url": "https://dingtalk.ai.table/webhook",
      "secret": "",
      "enable": false
    }
  ]
}
```

**字段说明**:
- `webhook_broadcast_within_days`: Webhook 广播推送的时间范围（天数），0 表示不限制
- `webhook_broadcast_configs`: Webhook 配置数组
  - `config_name`: 配置名称
  - `config_key`: 配置唯一标识（如 `dingtalk_primary`, `ai_table`）
  - `webhook_url`: Webhook 地址
  - `secret`: 签名密钥（钉钉需要）
  - `enable`: 是否启用

### 更新项目

**端点**: `PUT /openclaw/project/update`

**请求体**:
```json
{
  "id": 30001,
  "project_name": "猫粮舆情监控（更新）",
  "webhook_broadcast_within_days": 7,
  "webhook_broadcast_configs": [
    {
      "config_name": "钉钉主推送",
      "config_key": "dingtalk_primary",
      "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=yyy",
      "secret": "new-secret",
      "enable": true
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

## 场景操作

### 获取场景

**端点**: `GET /openclaw/project/scene/find?id={sceneId}`

**响应**:
```json
{
  "code": 0,
  "data": {
    "id": 40001,
    "name": "默认搜索场景",
    "description": "用于猫粮相关检索",
    "search_key_list": "猫粮,宠物食品",
    "search_keys": [
      { "platform": "抖音", "search_key": "猫粮,宠物食品" },
      { "platform": "小红书", "search_key": "宠物食品" }
    ],
    "work_project_id": 30001
  },
  "msg": "成功"
}
```

### 获取场景列表

**端点**: `GET /openclaw/project/scene/list`

**参数**:
- `work_project_id` - 项目ID（必填）
- `page` - 页码，默认 1
- `pageSize` - 每页数量，默认 10
- `name` - 场景名称模糊搜索

**响应**:
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "id": 40001,
        "name": "默认搜索场景",
        "description": "用于猫粮相关检索",
        "search_key_list": "猫粮,宠物食品",
        "search_keys": [
          { "platform": "抖音", "search_key": "猫粮,宠物食品" },
          { "platform": "小红书", "search_key": "宠物食品" }
        ],
        "work_project_id": 30001
      }
    ],
    "total": 1,
    "page": 1,
    "pageSize": 10
  },
  "msg": "获取成功"
}
```

### 创建场景

**端点**: `POST /openclaw/project/scene/create`

**请求体**:
```json
{
  "name": "默认搜索场景",
  "description": "用于猫粮相关检索",
  "search_key_list": "猫粮,宠物食品",
  "search_keys": [
    { "platform": "抖音", "search_key": "猫粮,宠物食品" },
    { "platform": "小红书", "search_key": "宠物食品" }
  ],
  "work_project_id": 30001
}
```

**字段说明**:
- `search_keys` - 必须是数组结构
- `search_keys[].platform` - 仅支持 `抖音` / `小红书`（也兼容 `dy` / `xhs`）
- `search_keys[].search_key` - 关键词，不能为空

### 更新场景

**端点**: `PUT /openclaw/project/scene/update`

**请求体**: 同创建，额外需要 `id` 字段

### 删除场景

**端点**: `DELETE /openclaw/project/scene/delete`

**请求体**:
```json
{ "id": 40001 }
```

## 错误码

| code | 说明 |
|------|------|
| 0 | 成功 |
| 7 | 业务失败 |
| 401 | 未授权 |
| 404 | 资源不存在 |
