# 小红书插件 API 文档

## 端点

`POST /openclaw/command/plugin`

## 认证

请求头：`api-key: <用户ApiKey>`

## 关键词搜索

**请求体**:
```json
{
  "skill": "meiyali-plugin-xhs",
  "action": "xhs.search",
  "payload": {
    "keywords": "宠物保险,宠物食品",
    "count": 20,
    "sorts": ["default"],
    "timeFilter": "7",
    "noteType": 0
  }
}
```

> 注意：接口文档中 `payload` 为实际请求字段名

### Payload 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| keywords | string | 关键词，多个用逗号分隔（如 "宠物保险,宠物食品"） |
| count | number | 采集数量，默认 20 |
| sorts | string[] | 排序方式 |
| timeFilter | string | 时间过滤 |
| noteType | number | 0不限, 1视频, 2图文 |
| includeDetails | boolean | 是否补充详情 |

## 笔记详情

**请求体**:
```json
{
  "skill": "meiyali-plugin-xhs",
  "action": "xhs.detail",
  "payload": {
    "note_id": "64f1b2c0000000001c02a23"
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

## 插件执行结果

```json
{
  "id": "task_uuid_xxxx",
  "result": {
    "success": true,
    "count": 20,
    "items": [
      {
        "id": "64f1b2c0000000001c02a23",
        "title": "猫粮推荐",
        "content": "很好用的猫粮，主子很喜欢...",
        "author": "用户名",
        "authorId": "user_xxx",
        "link": "https://www.xiaohongshu.com/explore/64f1b2c0",
        "coverUrl": "https://xxx.jpg",
        "type": "normal",
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
