# 抖音插件 API 文档

## 端点

`POST /openclaw/command/plugin`

## 认证

请求头：`api-key: <用户ApiKey>`

## 关键词搜索

**请求体**:
```json
{
  "skill": "meiyali-plugin-dy",
  "action": "dy.search",
  "payload": {
    "keywords": "猫粮,宠物食品",
    "count": 20,
    "sorts": ["default"],
    "timeFilter": "7"
  }
}
```

> 注意：接口文档中 `payload` 为实际请求字段名

### Payload 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| keywords | string | 关键词，多个用逗号分隔（如 "猫粮,宠物食品"） |
| count | number | 采集数量，默认 20 |
| sorts | string[] | 排序方式 |
| timeFilter | string | 时间过滤 |
| includeDetails | boolean | 是否补充详情 |

### 排序枚举 (sorts)

- `default` / `general` - 综合排序
- `time_descending` - 最新优先
- `popularity_descending` - 热度优先
- `comment_descending` - 评论最多
- `collect_descending` - 收藏最多

### 时间过滤 (timeFilter)

- `0` - 不限
- `1` - 一天内
- `7` - 一周内
- `30` - 一月内
- `180` - 半年内

## 作品详情

**请求体**:
```json
{
  "skill": "meiyali-plugin-dy",
  "action": "dy.detail",
  "payload": {
    "aweme_id": "728573829184561"
  }
}
```

## 响应

```json
{
  "code": 0,
  "data": {
    "task_id": "uuid-xxxx-xxxx",
    "plugin_device_id": "device_xxx"
  },
  "msg": "成功"
}
```

### 返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务唯一标识 |
| plugin_device_id | string | 接收任务的设备 ID |

## 插件执行结果

```json
{
  "id": "task_uuid_xxxx",
  "result": {
    "success": true,
    "count": 20,
    "items": [
      {
        "id": "728573829184561",
        "title": "猫粮推荐",
        "desc": "很好用的猫粮...",
        "author": "用户名",
        "authorId": "user_xxx",
        "link": "https://www.douyin.com/video/728573829184561",
        "coverUrl": "https://xxx.jpg",
        "stats": {
          "diggCount": 100,
          "commentCount": 20,
          "collectCount": 50,
          "shareCount": 10
        }
      }
    ]
  }
}
```
