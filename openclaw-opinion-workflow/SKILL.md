---
name: openclaw-opinion-workflow
description: OpenClaw 舆情主编排（Relay 直连版）。用于手动查询、实时刷新、定时主流程统一编排。触发词：舆情工作流、openclaw-opinion-workflow、实时刷新、主流程。
---

# OpenClaw 舆情主编排（Relay 直连）

## 目标

- 让 OpenClaw 明确通过 Relay `/api/v1/*` 完成舆情流程。
- 一个主流程覆盖手动查询与定时执行。
- 不再走旧 `/openclaw/*` 任务链路。

## 认证

请求头统一使用：

`X-OpenClaw-API-Key: <relay_api_key>`

## 主流程（推荐）

1. 查询项目：`GET /api/v1/projects?status=enabled`
2. 手动查询场景先读存量结果：`GET /api/v1/projects/{project_id}/works`
3. 用户明确要求“实时刷新”时触发：
   - `POST /api/v1/projects/{project_id}/manual-refresh`
   - 参数固定为：
     - `count=10`
     - `sorts=["time_descending"]`
     - `timeFilter=1`
     - `result_limit=10`
     - `wait_timeout_seconds=180`
     - `analysis_wait_timeout_seconds=120`
     - `poll_interval_ms=1000`
4. 读取本轮结果：
   - `GET /api/v1/projects/{project_id}/works`
   - 若 `analysis_pending_work_ids` 非空，2~3 秒后重读 works，直到 pending 清零或达到重试上限
   - 必要时 `GET /api/v1/works/{work_id}`
5. 返回舆情解释字段：
   - `latest_opinion_key`
   - `latest_opinion_direction`
   - `latest_opinion_reason`
   - `latest_opinion.opinion_think`

## 定时任务入口

主定时任务只执行：

```bash
python3 opinion_monitor_relay.py --mode full
```

说明：

- 这是唯一主入口。
- 不再拆分 `dispatch/process/analyze`。

## 关键约束

- 先读库再刷新：默认先返回最近结果，用户要求实时再触发刷新。
- 不做关键词正负面硬匹配，判断依赖项目规则与语义分析。
- Relay 是任务宿主，管理后台不是 Relay 宿主进程。

## 项目查看输出口径（必须）

当用户意图是“查看项目相关内容/项目详情/项目标准”时，必须切换为产品视角输出，并遵循以下约束：

1. 仅展示产品信息：
   - 项目名、项目 ID
   - 主体标签与描述（`brand_tags_description`）
   - 品牌描述（`brand_description`）
   - 竞品描述（`competing_brand_description`）
   - 搜索词（`search_key_list`）
   - 负面/正面/中性判断标准（`opinion_configs_json`）
2. 默认不展示技术配置：
   - 爬取平台与 `crawl_config_json`
   - 播报渠道细节与 `webhook_broadcast_configs_json`
   - API 鉴权、任务调度参数、实现细节
3. 输出格式必须是表格：
   - 项目基础信息表
   - 主体标签表
   - 舆情标准表
   - 字段为空时也要明确写“未配置”

## 参考

- [workflow.md](references/workflow.md)
