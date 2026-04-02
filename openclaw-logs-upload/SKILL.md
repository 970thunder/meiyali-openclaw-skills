---
name: openclaw-logs-upload
description: OpenClaw 日志上报。OpenClaw 的行为日志上报。当需要记录操作日志、审计追踪、问题排查时使用此技能。触发词：日志上报、记录日志、操作审计、行为日志。
---

# 日志上报

将 OpenClaw 的行为日志上报至管理后台。

## 认证

请求头：`api-key: <用户ApiKey>`

## 上报日志

调用 `POST /openclaw/logs/upload`

```json
{
  "skill": "openclaw-logs-upload",
  "action": "upload",
  "params": {
    "level": "info",
    "action": "opinion.analyze",
    "message": "舆情分析完成",
    "details": {
      "project_id": 30001,
      "items_count": 20,
      "positive_count": 15,
      "negative_count": 2,
      "neutral_count": 3
    }
  }
}
```

## 批量上报

```json
{
  "skill": "openclaw-logs-upload",
  "action": "batch_upload",
  "params": {
    "logs": [
      {
        "level": "info",
        "action": "plugin.command",
        "message": "下发抖音搜索任务",
        "details": { "task_id": "uuid-xxxx" }
      },
      {
        "level": "info",
        "action": "task.result",
        "message": "获取任务结果",
        "details": { "task_id": "uuid-xxxx", "status": 2 }
      }
    ]
  }
}
```

## 日志级别

| 级别 | 说明 |
|------|------|
| debug | 调试信息 |
| info | 一般信息 |
| warn | 警告信息 |
| error | 错误信息 |

## 返回格式

```json
{
  "code": 0,
  "data": {
    "logged": 1
  },
  "msg": "成功"
}
```

详细 API 文档参见 [references/api.md](references/api.md)
