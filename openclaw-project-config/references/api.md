# Relay 项目配置 API

## 认证

请求头：`X-OpenClaw-API-Key: <relay_api_key>`

## 项目管理

### 获取项目列表

```http
GET /api/v1/projects
```

### 获取单个项目

```http
GET /api/v1/projects/{project_id}
```

### 创建项目

```http
POST /api/v1/projects
Content-Type: application/json
```

示例：

```json
{
  "project_name": "猿辅导舆情监控",
  "search_key_list": "猿辅导,斑马APP",
  "opinion_configs_json": [],
  "webhook_broadcast_configs_json": [],
  "crawl_config_json": {
    "platforms": ["dy", "xhs"]
  },
  "status": 1
}
```

### 更新项目

```http
PUT /api/v1/projects/{project_id}
Content-Type: application/json
```

建议先 GET 当前项目，再只修改目标字段后 PUT，避免误清空。

## 常用字段

- `project_name`
- `brand_description`
- `brand_tags_description`
- `competing_brand_description`
- `search_key_list`
- `crawl_config_json`
- `opinion_configs_json`
- `webhook_broadcast_configs_json`
- `status`

## 约束

- 仅使用 `/api/v1/projects*` 路径，不使用旧 `/openclaw/project/*`
- `opinion_configs_json` 与 `webhook_broadcast_configs_json` 必须为 JSON 数组
- `crawl_config_json` 必须为 JSON 对象

## 项目查看响应约定（产品视角）

当意图是“查看项目内容/项目标准”时：

- 默认只返回产品信息：`project_name`、`id`、`brand_tags_description`、`brand_description`、`competing_brand_description`、`search_key_list`、`opinion_configs_json`
- 默认不返回技术配置：`crawl_config_json`、`webhook_broadcast_configs_json`、API 鉴权和调度参数
- 输出格式固定为表格：
  - 项目基础信息（字段/内容）
  - 主体标签（标签/描述）
  - 舆情标准（类型/是否播报/判断标准）
- 字段为空也需要保留表格行并显示“未配置”
