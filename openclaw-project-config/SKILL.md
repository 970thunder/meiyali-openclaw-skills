---
name: openclaw-project-config
description: 舆情项目配置管理。用于获取、更新、创建舆情项目配置信息，包括产品信息、舆情标准、关键词、钉钉webhook地址等。当需要查询项目设置、更新项目参数、获取项目列表、管理场景配置时使用此技能。触发词：获取项目配置、更新项目、查询项目列表、项目场景配置、关键词管理。
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

### 2. 项目与场景的关系

```
项目 (Project)
  └── 场景 (Scene)
        ├── search_keys: 关键词配置
        ├── params: 采集参数
        └── 其他配置
```

- **项目**: 包含品牌信息、舆情标准、Webhook 地址等全局配置
- **场景**: 包含具体关键词、平台配置、采集参数等执行参数

### 3. API 端点

| 操作 | 端点 | 方法 |
|------|------|------|
| 获取项目 | `http://127.0.0.1:8888/openclaw/project/find?id={id}` | GET |
| 获取列表 | `http://127.0.0.1:8888/openclaw/project/list` | GET |
| 创建项目 | `http://127.0.0.1:8888/openclaw/project/create` | POST |
| 更新项目 | `http://127.0.0.1:8888/openclaw/project/update` | PUT |
| 删除项目 | `http://127.0.0.1:8888/openclaw/project/delete` | DELETE |
| 获取场景 | `http://127.0.0.1:8888/openclaw/project/scene/find?id={id}` | GET |
| 场景列表 | `http://127.0.0.1:8888/openclaw/project/scene/list` | GET |
| 创建场景 | `http://127.0.0.1:8888/openclaw/project/scene/create` | POST |
| 更新场景 | `http://127.0.0.1:8888/openclaw/project/scene/update` | PUT |
| 删除场景 | `http://127.0.0.1:8888/openclaw/project/scene/delete` | DELETE |

### 4. 认证

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
    "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
    "secret": "ding-secret",
    "ai_table_webhook": "https://dingtalk.ai.table/webhook",
    "search_key_list": "猫粮,宠物食品"
  }
}
```

### 更新项目

```json
{
  "skill": "openclaw-project-config",
  "action": "update_project",
  "params": {
    "id": <项目ID>,
    "project_name": "猫粮舆情监控（更新）",
    "search_key_list": "猫粮,宠物食品,营养餐"
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

## 场景操作

### 获取场景

```json
{
  "skill": "openclaw-project-config",
  "action": "get_scene",
  "params": { "id": <场景ID> }
}
```

### 获取场景列表

```json
{
  "skill": "openclaw-project-config",
  "action": "list_scenes",
  "params": { "work_project_id": <项目ID>, "page": 1, "pageSize": 10 }
}
```

### 创建场景

```json
{
  "skill": "openclaw-project-config",
  "action": "create_scene",
  "params": {
    "name": "默认搜索场景",
    "description": "用于猫粮相关检索",
    "search_key_list": "猫粮,宠物食品",
    "search_keys": [
      { "platform": "抖音", "search_key": "猫粮,宠物食品" },
      { "platform": "小红书", "search_key": "宠物食品" }
    ],
    "work_project_id": <项目ID>
  }
}
```

> 📌 **search_keys 格式说明：**
> - `platform`: 支持 `抖音`/`dy` 和 `小红书`/`xhs`
> - `search_key`: 多个关键词用逗号分隔，如 `"猫粮,宠物食品"`

### 更新场景

```json
{
  "skill": "openclaw-project-config",
  "action": "update_scene",
  "params": {
    "id": <场景ID>,
    "name": "默认搜索场景（更新）",
    "search_keys": [
      { "platform": "抖音", "search_key": "猫粮,宠物食品,营养餐" }
    ]
  }
}
```

### 删除场景

```json
{
  "skill": "openclaw-project-config",
  "action": "delete_scene",
  "params": { "id": <场景ID> }
}
```

## 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `401 Unauthorized` | API Key 无效或未配置 | 配置有效的 `OPENCLAW_API_KEY` |
| `404 Not Found` | 项目/场景不存在 | 检查 ID 是否正确 |
| `Validation failed` | 必填字段缺失 | 检查请求参数 |
| `webhook_url is required` | 缺少钉钉 Webhook | 在项目中配置 `webhook_url` |

详细 API 文档参见 [references/api.md](references/api.md)
