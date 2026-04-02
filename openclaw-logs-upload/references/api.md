# 日志上报 API 文档

## 端点

`POST /openclaw/logs/upload`

## 认证

请求头：`api-key: <用户ApiKey>`

## 上报日志

**请求体**:
```json
{
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
```

### 参数说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| level | string | 是 | 日志级别 |
| action | string | 是 | 操作类型 |
| message | string | 是 | 日志消息 |
| details | object | 否 | 详细信息 |

## 批量上报

**请求体**:
```json
{
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
```

## 日志级别

| 级别 | 说明 | 使用场景 |
|------|------|---------|
| debug | 调试信息 | 开发调试 |
| info | 一般信息 | 正常操作记录 |
| warn | 警告信息 | 异常但可恢复 |
| error | 错误信息 | 操作失败 |

## 操作类型 (action)

| action | 说明 |
|--------|------|
| plugin.command | 插件指令下发 |
| task.result | 任务结果获取 |
| opinion.analyze | 舆情分析 |
| opinion.upload | 舆情上传 |
| content.extract | 内容提取 |
| dingtalk.push | 钉钉推送 |
| user.login | 用户登录 |
| user.logout | 用户登出 |

## 响应

```json
{
  "code": 0,
  "data": {
    "logged": 1
  },
  "msg": "成功"
}
```

## 错误码

| code | 说明 |
|------|------|
| 0 | 成功 |
| 7 | 业务失败 |
| 401 | 未授权 |
