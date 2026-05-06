# 舆情监控工作流（Relay 版）

## 流程概览

```text
项目列表（Relay）→ manual-refresh（Relay）→ Relay 下发插件任务并等待结束 →
Relay 入库作品并自动舆情回写 → OpenClaw 读取项目作品与舆情结果
```

## 详细步骤

### 1. 获取项目列表

```text
GET /api/v1/projects
```

- 若配置了 `RELAY_PROJECT_IDS`，按项目列表过滤
- 若未配置，则处理全部可见项目

### 2. 触发项目刷新

```text
POST /api/v1/projects/{project_id}/manual-refresh
```

请求体关键参数：

- `search_keys`
- `platforms`
- `count`
- `sorts`（建议 `["time_descending"]`）
- `timeFilter`（建议 `1`，仅抓一天内）
- `wait_timeout_seconds`
- `analysis_wait_timeout_seconds`
- `poll_interval_ms`
- `result_limit`

推荐值（本地联调）：

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

### 3. Relay 内部闭环

`manual-refresh` 内部自动完成：

- 按项目创建搜索任务（抖音/小红书）
- 通过在线插件设备执行抓取
- 写入 `platform_works`
- 任务成功后自动触发舆情分析并回写 `platform_work_opinions`

### 4. OpenClaw 读取结果

```text
GET /api/v1/projects/{project_id}/works
```

若 `manual-refresh` 响应中存在 `analysis_pending_work_ids`：

- 说明部分作品分析仍在进行中
- 需要等待 2~3 秒后再次读取 works
- 直到 pending 归零或达到重试上限

读取字段：

- `latest_opinion_key`
- `latest_opinion_direction`
- `latest_opinion_reason`
- `latest_opinion`（结构化对象）

### 5. 可选详情/评论能力

```text
POST /api/v1/works/{work_id}/detail-task
POST /api/v1/works/{work_id}/comment-task
GET  /api/v1/works/{work_id}/comments
```

## 定时任务建议（单主任务）

```bash
python3 opinion_monitor_relay.py --mode full
```

使用 OpenClaw 内置定时任务只保留这一个命令即可，不再拆分成多个子任务。
