---
name: openclaw-project-config
description: Relay 项目配置管理。用于获取、更新、创建舆情项目配置信息（Relay 版）。触发词：获取项目配置、更新项目、查询项目列表、舆情配置管理。
---

# Relay 项目配置管理

## 认证

请求头统一使用：

`X-OpenClaw-API-Key: <relay_api_key>`

## API 端点（Relay）

| 操作 | 端点 | 方法 |
|------|------|------|
| 项目列表 | `/api/v1/projects` | GET |
| 获取项目 | `/api/v1/projects/{project_id}` | GET |
| 创建项目 | `/api/v1/projects` | POST |
| 更新项目 | `/api/v1/projects/{project_id}` | PUT |

## 关键字段

- `project_name`
- `brand_description`
- `brand_tags_description`
- `competing_brand_description`
- `search_key_list`
- `opinion_configs_json`
- `webhook_broadcast_configs_json`
- `crawl_config_json`

## 项目查看输出规范（必须执行）

当用户意图是“查看项目相关内容/项目详情/项目标准”时，默认按**产品视角**输出，不输出技术配置细节。

### 默认展示内容（必须）

1. 项目基础信息（项目名、项目 ID）
2. 主体标签与描述（由 `brand_tags_description` 解析）
3. 品牌描述（`brand_description`）
4. 竞品描述（`competing_brand_description`）
5. 搜索词（`search_key_list`）
6. 舆情判断标准（`opinion_configs_json` / `opinion_configs`）
   - 负面 / 正面 / 中性全部完整列出
   - 使用表格展示，不省略判断标准文本

### 默认不展示内容（除非用户明确要求）

- `crawl_config_json`
- 爬取平台列表（dy/xhs 等执行层配置）
- `webhook_broadcast_configs_json` 及任何播报渠道密钥/群 ID
- API 路径、鉴权头、任务调度参数等代码层信息

### 表格格式要求（强约束）

- 项目基础信息：2 列表格（字段 / 内容）
- 主体标签：2 列表格（标签 / 描述）
- 舆情标准：3 列表格（类型 / 是否播报 / 判断标准）
- `brand_tags_description` 若为“每行一个标签，格式：标签,描述”，按行拆分成表格
- 如果某字段为空，也保留表格行并明确写“未配置”

## 推荐读改流程

1. 先读当前配置：`GET /api/v1/projects/{project_id}`
2. 基于当前配置修改目标字段（不要随意清空未修改字段）
3. 用 `PUT /api/v1/projects/{project_id}` 一次性提交
4. 更新后再次 `GET /api/v1/projects/{project_id}` 回读校验

## 严格约束

- 仅使用 Relay `projects` 系列接口
- 禁止使用旧链路 `/openclaw/project/*`
- 涉及 JSON 字段时，必须保持合法 JSON 结构
  - `opinion_configs_json` 必须是数组
  - `webhook_broadcast_configs_json` 必须是数组
  - `crawl_config_json` 必须是对象，常用 `platforms` 字段

详细参见 [references/api.md](references/api.md)
