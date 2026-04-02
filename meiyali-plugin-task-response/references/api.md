# 任务结果 API 文档

## 端点

| 操作 | 端点 | 方法 |
|------|------|------|
| 查询结果 | `/openclaw/task/result?task_id={taskId}` | GET |
| 标记完成 | `/openclaw/task/finish` | POST |

## 认证

请求头：`api-key: <用户ApiKey>`

---

## 查询结果

### 请求

```
GET /openclaw/task/result?task_id={taskId}
```

### 响应

```json
{
  "code": 0,
  "data": {
    "id": 1,
    "task_id": "uuid-xxxx-xxxx",
    "plugin_device_id": "device_xxx",
    "task_status": 1,
    "expire_at": "2026-03-30T13:00:00Z",
    "raw_data": "{\"success\":true,\"count\":20,\"items\":[...]}"
  },
  "msg": "成功"
}
```

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | number | 数据库记录 ID |
| task_id | string | 任务唯一标识 |
| plugin_device_id | string | 执行任务的设备 ID |
| task_status | number | 任务状态 |
| expire_at | string | 任务过期时间 |
| raw_data | string | JSON 字符串，包含任务实际结果 |
| created_at | string | 任务创建时间 |
| updated_at | string | 任务更新时间 |

### 任务状态说明

| 状态值 | 说明 | 含义 |
|--------|------|------|
| 0 | 已创建 | 任务已写入数据库，尚未发送给设备 |
| 1 | 已下发 | 任务已发送给在线设备 |
| 2 | 执行成功 | 设备执行成功，结果已回传 |
| 3 | 任务结束 | 所有作品完成舆情分析，任务彻底结束 |
| -1 | 下发失败 | 发送给设备失败 |
| -2 | 执行失败 | 设备执行失败 |

---

## 标记任务彻底完成

当任务中**所有作品**都完成舆情分析后，才调用此接口标记任务彻底完成。

### 请求

```
POST /openclaw/task/finish
Content-Type: application/json
```

### 请求体

```json
{
  "task_ids": ["cb5e05fd-0041-4980-af6e-1459e49e68be", "68cb2572-d939-4e9c-9869-b990e4f9a88e"]
}
```

### 响应

```json
{
  "code": 0,
  "data": {
    "finished_count": 2
  },
  "msg": "成功"
}
```

### 说明

- 仅会更新当前 `api-key` 对应 `yunfan_id` 的任务，不能越权标记其他用户任务
- 被标记任务状态会更新为 `3`（任务结束）
- **必须等所有作品都完成舆情分析后才能调用**
  - ✅ 30条作品分析30条 → 可调用
  - ❌ 30条作品分析15条 → 不可调用，状态保持2

---

## 轮询策略

### 轮询终止条件

- 任务状态变为 2（成功）或 -2（失败）
- 轮询次数达到 `max_attempts`
- 任务超过 `expire_at` 过期时间

### 推荐参数

```json
{
  "max_attempts": 30,
  "interval_seconds": 2
}
```

---

## 解析后数据格式

```json
{
  "success": true,
  "count": 20,
  "items": [
    {
      "id": "note_123",
      "title": "猫粮推荐",
      "content": "很好用的猫粮，主子很喜欢...",
      "author": "用户名",
      "link": "https://...",
      "stats": {
        "diggCount": 100,
        "commentCount": 20,
        "collectCount": 50
      }
    }
  ]
}
```

---

## 数据充分性判断

- `content.length >= 100` - 内容充分，可直接进行舆情分析
- `content.length < 100` - 内容不足，需要调用 `openclaw-content-extract` 补充
