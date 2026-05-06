# openclaw-opinion-workflow 参考流程

## 手动查询（非实时）

```text
GET /api/v1/projects?status=enabled
GET /api/v1/projects/{project_id}/works?page=1&page_size=20
```

返回最近作品及 `latest_opinion*` 字段。

## 手动查询（实时刷新）

```text
POST /api/v1/projects/{project_id}/manual-refresh
GET  /api/v1/projects/{project_id}/works?page=1&page_size=20
```

推荐请求参数：

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

`manual-refresh` 会在 Relay 内部自动完成：

1. 按平台+关键词创建任务
2. 下发插件执行
3. 等任务结束
4. 作品入库
5. 自动分析并回写 opinion

若响应里 `analysis_pending_work_ids` 非空，说明部分作品仍在分析中，需要短暂等待后再次读取 works。

## 定时任务

```bash
python3 opinion_monitor_relay.py --mode full
```

OpenClaw 内置调度只保留这一条任务。
