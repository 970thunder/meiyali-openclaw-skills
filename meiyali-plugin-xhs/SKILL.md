---
name: meiyali-plugin-xhs
description: 小红书插件指令下发。通过浏览器插件爬取小红书平台内容，支持关键词搜索和笔记详情提取。当需要采集小红书内容、搜索小红书笔记、获取笔记详情时使用此技能。触发词：小红书搜索、爬取小红书、笔记详情、xhs。
---

# 小红书插件指令

向浏览器插件下发小红书任务指令。

## API 端点

```
POST http://127.0.0.1:8888/openclaw/command/plugin
```

## 认证

请求头：`api-key: <用户ApiKey>`

## 关键词搜索

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

> keywords 参数为逗号分隔的字符串格式，如 "宠物保险,宠物食品"

## 笔记详情

```json
{
  "skill": "meiyali-plugin-xhs",
  "action": "xhs.detail",
  "payload": {
    "note_id": "64f1b2c0000000001c02a23"
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
