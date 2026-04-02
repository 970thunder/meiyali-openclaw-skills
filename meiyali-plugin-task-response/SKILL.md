---
name: meiyali-plugin-task-response
description: 插件任务结果查询。轮询查询抖音/小红书插件任务执行结果，获取爬取数据。下发插件任务后需要等待结果、判断任务是否完成、获取爬取数据时使用此技能。当所有作品完成舆情分析后，需要标记任务彻底完成时也使用此技能。触发词：查询任务结果、轮询结果、获取爬取数据、任务状态、标记任务完成。
---

# 插件任务结果查询

轮询查询插件任务执行结果。

## API 端点

| 操作 | 端点 | 方法 |
|------|------|------|
| 查询结果 | `http://127.0.0.1:8888/openclaw/task/result?task_id={taskId}` | GET |
| 标记完成 | `http://127.0.0.1:8888/openclaw/task/finish` | POST |

## 认证

请求头：`api-key: <用户ApiKey>`

## 查询结果

```json
{
  "skill": "meiyali-plugin-task-response",
  "action": "get_result",
  "params": { "task_id": "uuid-xxxx-xxxx" }
}
```

## 轮询等待

轮询直到任务完成（最多30次，间隔2秒）：

```json
{
  "skill": "meiyali-plugin-task-response",
  "action": "poll_result",
  "params": {
    "task_id": "uuid-xxxx-xxxx",
    "max_attempts": 30,
    "interval_seconds": 2
  }
}
```

## 标记任务彻底完成

当任务中**所有作品**都完成舆情分析后，才调用此接口标记任务彻底完成。

- 任务原始数据有30条作品，分析完30条 → 可标记 → 状态改为3
- 任务原始数据有30条作品，只分析15条 → **不可标记** → 状态保持2

```json
{
  "skill": "meiyali-plugin-task-response",
  "action": "finish_task",
  "params": {
    "task_ids": ["uuid-xxxx-xxxx", "uuid-yyyy-yyyy"]
  }
}
```

## 任务状态

| 状态值 | 说明 | 含义 |
|--------|------|------|
| 0 | 已创建 | 任务已写入数据库，尚未发送给设备 |
| 1 | 已下发 | 任务已发送给在线设备 |
| 2 | 执行成功 | 设备执行成功，结果已回传 |
| 3 | 任务结束 | 所有作品完成舆情分析，任务彻底结束 |
| -1 | 下发失败 | 发送给设备失败 |
| -2 | 执行失败 | 设备执行失败 |

详细 API 文档参见 [references/api.md](references/api.md)
