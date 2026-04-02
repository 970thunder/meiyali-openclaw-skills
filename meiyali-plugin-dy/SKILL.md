---
name: meiyali-plugin-dy
description: 抖音插件指令下发。通过浏览器插件爬取抖音平台内容，支持关键词搜索和作品详情提取。当需要采集抖音内容、搜索抖音视频、获取作品详情时使用此技能。触发词：抖音搜索、爬取抖音、抖音作品、抖音数据。
---

# 抖音插件指令

向浏览器插件下发抖音任务指令。

## API 端点

```
POST http://127.0.0.1:8888/openclaw/command/plugin
```

## 认证

请求头：`api-key: <用户ApiKey>`

## 关键词搜索

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

> keywords 参数为逗号分隔的字符串格式，如 "猫粮,宠物食品"

## 作品详情

```json
{
  "skill": "meiyali-plugin-dy",
  "action": "dy.detail",
  "payload": {
    "aweme_id": "728573829184561"
  }
}
```

## 返回格式

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

详细 API 文档参见 [references/api.md](references/api.md)
