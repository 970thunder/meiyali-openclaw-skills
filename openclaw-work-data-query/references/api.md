# 作品数据查询 API 参考

## 1) 查询项目下所有作品（分页）

```
GET /api/v1/projects/{project_id}/works
```

### 请求头

```
X-OpenClaw-API-Key: <relay_api_key>
```

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码，从 1 开始 |
| page_size | integer | 20 | 每页数量，最大 200 |
| platform | string | - | 按平台过滤（xhs/dy/bili 等） |
| search_key | string | - | 按搜索关键词过滤 |
| opinion_key | string | - | 按舆情正负面过滤（正面/中性/负面） |

### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 12345,
        "project_id": 1776650331436,
        "platform_work_id": "7287348293487234",
        "platform_work_url": "https://www.xiaohongshu.com/explore/abc123",
        "platform": "xhs",
        "title": "作品标题",
        "content": "作品正文内容",
        "author_name": "作者昵称",
        "author_url": "https://www.xiaohongshu.com/user/profile/xxx",
        "publish_time": "2026-05-01T10:30:00",
        "like_count": 1520,
        "comment_count": 89,
        "collect_count": 340,
        "share_count": 56,
        "ai_analyse_summary": "这是一篇关于产品使用体验的笔记...",
        "latest_opinion_key": "正面",
        "latest_opinion_reason": "用户对产品整体满意，反馈积极",
        "latest_opinion_think": "根据内容语义分析...",
        "media_urls_json": ["https://example.com/img1.jpg"],
        "search_key": "品牌A",
        "detail_status": 1,
        "comment_crawl_status": 1,
        "created_at": "2026-05-01T10:35:00",
        "updated_at": "2026-05-01T12:00:00",
        "last_crawled_at": "2026-05-01T11:00:00"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 156
  }
}
```

### 分页遍历完整示例

```javascript
async function fetchAllWorks(projectId, relayApiKey) {
  const allWorks = [];
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const response = await fetch(
      `${RELAY_BASE_URL}/api/v1/projects/${projectId}/works?page=${page}&page_size=20`,
      {
        headers: {
          'X-OpenClaw-API-Key': relayApiKey
        }
      }
    );

    const result = await response.json();
    const { items, page_size, total } = result.data;

    if (items && items.length > 0) {
      allWorks.push(...items);
      page++;
    }

    // 判断是否还有更多数据
    hasMore = (page * page_size) < total;
  }

  return allWorks;
}
```

## 2) 精确匹配作品

获取所有作品后，使用 `platform_work_url` 或 `platform_work_id` 精确匹配：

```javascript
// 方式一：通过 URL 匹配
const targetUrl = "https://www.xiaohongshu.com/explore/abc123";
const matchedWork = allWorks.find(w => w.platform_work_url === targetUrl);

// 方式二：通过 platform_work_id 匹配
const targetId = "7287348293487234";
const matchedWork = allWorks.find(w => w.platform_work_id === targetId);
```

**注意**：不要使用标题模糊搜索，严格使用精确匹配。

## 3) 作品舆情详情

获取作品舆情分析结果，优先读取以下字段：

```javascript
// 舆情分析结果
const work = matchedWork;

console.log({
  opinion_key: work.latest_opinion_key,        // 正面/中性/负面
  opinion_reason: work.latest_opinion_reason,  // 判断原因
  opinion_think: work.latest_opinion?.opinion_think, // 推理过程
  ai_summary: work.ai_analyse_summary         // 内容摘要
});
```

## 4) 按平台过滤查询

```javascript
// 只查询小红书作品
GET /api/v1/projects/{project_id}/works?platform=xhs

// 只查询抖音作品
GET /api/v1/projects/{project_id}/works?platform=dy
```

## 5) 按舆情过滤查询

```javascript
// 只查询负面舆情作品
GET /api/v1/projects/{project_id}/works?opinion_key=负面
```

## 重要约束

1. **必须分页遍历**：使用 `page=1,2,3...` 循环，不能用 `page_size=100` 跳过遍历
2. **禁止飞书查询**：所有作品数据必须从本地数据库获取
3. **精确匹配**：使用 `platform_work_url` 或 `platform_work_id`，不用标题搜索
4. **优先字段**：读取舆情时优先使用 `latest_opinion_key`、`latest_opinion_reason`、`ai_analyse_summary`
