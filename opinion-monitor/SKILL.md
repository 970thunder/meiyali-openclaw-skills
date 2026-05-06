---
name: opinion-monitor
description: 舆情监控工作流（Relay 编排层）。按项目级配置执行舆情监控：获取项目 → Relay manual-refresh 下发插件任务 → 自动素材分析与舆情分析 → 回写本地 SQLite。触发词：舆情监控、启动监控、执行舆情、监控流程、一键舆情。
---

# 舆情监控工作流（项目级）

本 Skill 是当前舆情监控的编排入口。
同时作为 `openclaw-opinion-workflow` 的兼容入口（两者指向同一 Relay 主流程）。

## 当前版本要点

- 只使用**项目级配置**
- 不再依赖场景配置
- 不在定时任务命令中写死项目 ID
- 默认通过 Relay `GET /api/v1/projects` 动态获取项目列表
- 如需过滤范围，可使用 `.env.meiyali` 中的 `RELAY_PROJECT_IDS`
- 当前唯一有效的主执行脚本是 `skills/opinion-monitor/scripts/opinion_monitor_relay.py`
- `skills/opinion-monitor/scripts/opinion_monitor.py` 已弃用，不再作为入口
- 不要使用历史遗留脚本，例如 `scripts/analyze_opinion.py`、`scripts/analyze-opinion.py`、`scripts/analyze-opinion.sh`
- 默认 `--mode full`：主流程一次跑完整闭环
- 定时任务只保留一个主任务：`--mode full`
- 单任务作品处理强制上限 10 条（即使上游返回更多，也会截断）

## 输入来源

项目级配置通过 Relay 接口获取：

- `GET /api/v1/projects`

关键字段：

- `project_name`
- `brand_description`
- `brand_tags_description`
- `competing_brand_description`
- `search_key_list`
- `opinion_configs`
- `webhook_broadcast_within_days`
- `webhook_broadcast_configs`

## 工作流

1. 获取项目列表
2. 按 `RELAY_PROJECT_IDS` 过滤项目（如有）
3. 读取单个项目配置
4. 调用 `POST /api/v1/projects/{project_id}/manual-refresh`（由 Relay 统一编排任务）
5. Relay 等待任务结束，自动执行素材分析与舆情分析并回写
6. 读取 `analysis_pending_work_ids`，若非空则二次读取 works
7. 通过 `GET /api/v1/projects/{project_id}/works` 获取最终结果

## manual-refresh 标准参数

对话实时刷新与 `--mode full` 都应使用以下参数：

```json
{
  "count": 10,
  "sorts": ["time_descending"],
  "timeFilter": 1,
  "result_limit": 10,
  "wait_timeout_seconds": 180,
  "analysis_wait_timeout_seconds": 120,
  "poll_interval_ms": 1000
}
```

规则：

- `wait_timeout_seconds` 负责“抓取任务完成等待”
- `analysis_wait_timeout_seconds` 负责“舆情分析结果等待”
- 返回后若 `analysis_pending_work_ids` 非空，必须再读 `GET /api/v1/projects/{project_id}/works`，直到 pending 清零或达到重试上限

## 定时任务建议

推荐主流程模式（生产）：

```bash
python3 opinion_monitor_relay.py --mode full
```

说明：

- `full` 是主闭环：读项目 -> 发任务 -> 等结果 -> 回写
- `chat` 仅用于人工抽样查看结果
- 一个 OpenClaw 内置定时任务即可，不再拆成多个定时任务

## 对话与定时的边界

- **定时任务**：使用 `python3 opinion_monitor_relay.py --mode full`
- **对话场景**（用户问“查一下/实时刷新”）：优先走 Relay HTTP 接口，不要先起 Python 脚本
  - 先查：`GET /api/v1/projects/{project_id}/works`
  - 实时刷新：`POST /api/v1/projects/{project_id}/manual-refresh`（带标准参数）
  - 刷新返回后检查 `analysis_pending_work_ids`，必要时再次查询 works

这样可以避免对话链路受脚本执行时长影响。

## 可选过滤

如果只处理指定项目，可在 `.env.meiyali` 中设置：

```env
RELAY_PROJECT_IDS=30001,30002
```

也可以临时手动执行：

```bash
python3 opinion_monitor_relay.py "30001,30002" --mode full
```

## 上传字段

舆情分析与回写在 Relay 任务成功后自动完成；OpenClaw 编排脚本只负责触发和读取结果。

## 相关参考

- [workflow.md](references/workflow.md)
