---
name: openclaw-work-data-query
description: 作品数据查询。用于查询数据库中已抓取的作品信息、详情和舆情分析结果。触发词：查作品、找作品、作品详情、舆情结果、作品数据、works query、查询作品信息。
---

# 作品数据查询

本 Skill 用于从本地 SQLite 数据库查询已抓取的作品信息和舆情分析结果。

## 核心约束

- **查询入口**：`GET /api/v1/projects/{project_id}/works`
- **禁止飞书**：任何时候都不查飞书表格找作品数据
- **匹配方式**：用 `platform_work_url` 或 `platform_work_id` 精确匹配，不要用标题模糊搜索
- **分页遍历**：必须循环翻页 `page=1,2,3...` 直到数据取完，不能用 `page_size=100` 只查一页

## 分页遍历逻辑

```javascript
// 标准分页查询流程
let page = 1;
let hasMore = true;
const allWorks = [];

while (hasMore) {
  const response = await fetch(
    `${RELAY_BASE_URL}/api/v1/projects/${projectId}/works?page=${page}&page_size=20`
  );
  const data = await response.json();

  if (data.items && data.items.length > 0) {
    allWorks.push(...data.items);
    page++;
  }

  // 计算 has_more：page * page_size < total
  hasMore = (page * data.page_size) < data.total;
}

// allWorks 现在包含该项目的所有作品
```

## 精确匹配查询

查询特定作品时，必须使用 `platform_work_url` 或 `platform_work_id`：

```javascript
// 通过 URL 精确匹配
const works = allWorks.filter(w => w.platform_work_url === targetUrl);

// 或者通过 platform_work_id 精确匹配
const works = allWorks.filter(w => w.platform_work_id === targetId);

// 不要用标题模糊搜索
```

## 返回字段说明

查询返回的每条作品记录包含以下关键字段：

| 字段名 | 说明 |
|--------|------|
| `id` | 数据库自增 ID |
| `platform_work_id` | 平台作品 ID |
| `platform_work_url` | 作品链接 |
| `platform` | 平台名称（xhs/dy/bili 等） |
| `title` | 作品标题 |
| `content` | 作品正文内容 |
| `author_name` | 作者昵称 |
| `publish_time` | 发布时间 |
| `like_count` | 点赞数 |
| `comment_count` | 评论数 |
| `collect_count` | 收藏数 |
| `share_count` | 分享数 |
| `ai_analyse_summary` | AI 内容摘要 |
| `latest_opinion_key` | 舆情正负面（正面/中性/负面） |
| `latest_opinion_reason` | 舆情判断原因 |
| `latest_opinion.opinion_think` | 舆情分析推理过程 |

**优先读取字段**：
- 舆情方向：`latest_opinion_key`
- 舆情原因：`latest_opinion_reason`
- 内容摘要：`ai_analyse_summary`

## API 认证

请求头：`X-OpenClaw-API-Key: <relay_api_key>`

## 相关参考

- [api.md](references/api.md)
