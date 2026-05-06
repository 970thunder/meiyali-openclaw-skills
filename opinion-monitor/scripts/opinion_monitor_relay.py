#!/usr/bin/env python3
"""
OpenClaw 本地舆情编排（Relay 版）

设计目标：
- 完全基于 Relay `/api/v1/*` 接口，不再依赖旧 `/openclaw/*` 后台接口
- 以项目为粒度执行 `manual-refresh`，由 Relay 负责插件调度、结果入库、舆情回写
- 脚本仅做编排与展示，不做关键词匹配判定
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[2]
ENV_PATH = WORKSPACE_DIR / ".env.meiyali"


def read_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def parse_csv_ids(text: str) -> List[str]:
    return [item.strip() for item in str(text or "").split(",") if item.strip()]


def parse_terms(text: str) -> List[str]:
    normalized = str(text or "")
    for sep in ["\n", "，", "/", "、", "；", ";", "|"]:
        normalized = normalized.replace(sep, ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def unique_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def is_true(text: str, default: bool = False) -> bool:
    raw = str(text or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "on", "yes"}


def to_int(value: Any, default: int, lower: int, upper: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    parsed = max(lower, parsed)
    parsed = min(upper, parsed)
    return parsed


def result_code(payload: Optional[dict], default: int = -1) -> int:
    if not isinstance(payload, dict):
        return default
    try:
        return int(payload.get("code", default))
    except Exception:
        return default


ENV = read_env_file(ENV_PATH)
RELAY_BASE_URL = (
    os.getenv("RELAY_API_BASE_URL")
    or ENV.get("RELAY_API_BASE_URL")
    or "http://host.docker.internal:18888"
).rstrip("/")
RELAY_API_KEY = (
    os.getenv("RELAY_API_KEY")
    or ENV.get("RELAY_API_KEY")
    or "relay-local-dev-key"
).strip()
RELAY_PROJECT_IDS = (
    os.getenv("RELAY_PROJECT_IDS")
    or ENV.get("RELAY_PROJECT_IDS")
    or os.getenv("OPINION_PROJECT_IDS")
    or ENV.get("OPINION_PROJECT_IDS")
    or os.getenv("OPINION_PROJECT_ID")
    or ENV.get("OPINION_PROJECT_ID")
    or ""
)
RELAY_HEADERS = {
    "X-OpenClaw-API-Key": RELAY_API_KEY,
    "Content-Type": "application/json",
}

RELAY_API_TIMEOUT = to_int(
    os.getenv("RELAY_API_TIMEOUT") or ENV.get("RELAY_API_TIMEOUT") or "30",
    default=30,
    lower=5,
    upper=600,
)
RELAY_API_RETRY = to_int(
    os.getenv("RELAY_API_RETRY_COUNT") or ENV.get("RELAY_API_RETRY_COUNT") or "2",
    default=2,
    lower=1,
    upper=5,
)
RELAY_WAIT_TIMEOUT_SECONDS = to_int(
    os.getenv("RELAY_WAIT_TIMEOUT_SECONDS") or ENV.get("RELAY_WAIT_TIMEOUT_SECONDS") or "300",
    default=300,
    lower=10,
    upper=1800,
)
RELAY_ANALYSIS_WAIT_TIMEOUT_SECONDS = to_int(
    os.getenv("RELAY_ANALYSIS_WAIT_TIMEOUT_SECONDS")
    or ENV.get("RELAY_ANALYSIS_WAIT_TIMEOUT_SECONDS")
    or str(min(RELAY_WAIT_TIMEOUT_SECONDS, 180)),
    default=min(RELAY_WAIT_TIMEOUT_SECONDS, 180),
    lower=5,
    upper=1800,
)
RELAY_POLL_INTERVAL_MS = to_int(
    os.getenv("RELAY_POLL_INTERVAL_MS") or ENV.get("RELAY_POLL_INTERVAL_MS") or "1000",
    default=1000,
    lower=200,
    upper=10000,
)
RELAY_RESULT_LIMIT = to_int(
    os.getenv("RELAY_RESULT_LIMIT") or ENV.get("RELAY_RESULT_LIMIT") or "10",
    default=10,
    lower=1,
    upper=200,
)
RELAY_PER_TASK_COUNT = to_int(
    os.getenv("RELAY_PER_TASK_COUNT") or ENV.get("RELAY_PER_TASK_COUNT") or "10",
    default=10,
    lower=1,
    upper=100,
)
RELAY_CHAT_SAMPLE_SIZE = to_int(
    os.getenv("RELAY_CHAT_SAMPLE_SIZE") or ENV.get("RELAY_CHAT_SAMPLE_SIZE") or "5",
    default=5,
    lower=3,
    upper=20,
)
RELAY_CHAT_AUTO_REFRESH = is_true(
    os.getenv("RELAY_CHAT_AUTO_REFRESH") or ENV.get("RELAY_CHAT_AUTO_REFRESH") or "0",
    default=False,
)
RELAY_POST_REFRESH_RECHECK_ROUNDS = to_int(
    os.getenv("RELAY_POST_REFRESH_RECHECK_ROUNDS")
    or ENV.get("RELAY_POST_REFRESH_RECHECK_ROUNDS")
    or "2",
    default=2,
    lower=0,
    upper=8,
)
RELAY_POST_REFRESH_RECHECK_INTERVAL_SECONDS = to_int(
    os.getenv("RELAY_POST_REFRESH_RECHECK_INTERVAL_SECONDS")
    or ENV.get("RELAY_POST_REFRESH_RECHECK_INTERVAL_SECONDS")
    or "3",
    default=3,
    lower=1,
    upper=30,
)
ENABLE_DY = is_true(os.getenv("OPENCLAW_ENABLE_DY") or ENV.get("OPENCLAW_ENABLE_DY") or "1", default=True)
ENABLE_XHS = is_true(os.getenv("OPENCLAW_ENABLE_XHS") or ENV.get("OPENCLAW_ENABLE_XHS") or "1", default=True)
RELAY_SORTS = unique_keep_order(
    parse_terms(os.getenv("RELAY_SORTS") or ENV.get("RELAY_SORTS") or "time_descending")
) or ["time_descending"]
RELAY_TIME_FILTER_DAYS = to_int(
    os.getenv("RELAY_TIME_FILTER_DAYS") or ENV.get("RELAY_TIME_FILTER_DAYS") or "1",
    default=1,
    lower=1,
    upper=180,
)


RELAY_FAIL_STREAK = 0
RELAY_LAST_ERROR = ""


def relay_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[dict] = None,
    timeout_seconds: Optional[int] = None,
    retry_count: Optional[int] = None,
) -> Optional[dict]:
    global RELAY_FAIL_STREAK, RELAY_LAST_ERROR
    if not RELAY_API_KEY:
        RELAY_FAIL_STREAK += 1
        RELAY_LAST_ERROR = "未配置 RELAY_API_KEY"
        print(f"❌ {RELAY_LAST_ERROR}")
        return None

    url = f"{RELAY_BASE_URL}{endpoint}"
    retries = max(1, int(retry_count or RELAY_API_RETRY))
    timeout = max(1, int(timeout_seconds or RELAY_API_TIMEOUT))
    for attempt in range(1, retries + 1):
        try:
            if method == "GET":
                req = urllib.request.Request(url, headers=RELAY_HEADERS)
            else:
                body = json.dumps(data or {}, ensure_ascii=False).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers=RELAY_HEADERS, method=method)
            response = urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=timeout)
            payload = json.loads(response.read())
            RELAY_FAIL_STREAK = 0
            RELAY_LAST_ERROR = ""
            return payload
        except urllib.error.URLError as err:
            RELAY_LAST_ERROR = str(err)
            print(f"❌ Relay 请求失败(第{attempt}/{retries}次): {err}")
        except Exception as err:
            RELAY_LAST_ERROR = str(err)
            print(f"❌ Relay 异常(第{attempt}/{retries}次): {err}")
        if attempt < retries:
            time.sleep(min(6, attempt * 2))
    RELAY_FAIL_STREAK += 1
    return None


def relay_unavailable_message() -> str:
    detail = (RELAY_LAST_ERROR or "未知错误").strip()
    if RELAY_FAIL_STREAK <= 1:
        return f"Relay 接口临时失败，已跳过本轮并稍后重试（{detail}）"
    return f"Relay 接口连续失败，请检查服务状态（{detail}）"


def probe_relay() -> bool:
    result = relay_request("/api/v1/status", retry_count=1, timeout_seconds=min(8, RELAY_API_TIMEOUT))
    return result_code(result) == 0


def list_projects() -> List[dict]:
    result = relay_request("/api/v1/projects")
    if result_code(result) != 0:
        return []
    data = (result or {}).get("data") or {}
    items = data.get("items") or []
    return items if isinstance(items, list) else []


def resolve_target_projects(project_ids_text: Optional[str] = None) -> List[dict]:
    projects = list_projects()
    if not projects:
        return []
    target_ids = parse_csv_ids(project_ids_text or RELAY_PROJECT_IDS)
    if not target_ids:
        return projects
    target = set(target_ids)
    return [project for project in projects if str((project or {}).get("id") or "") in target]


def extract_project_platforms(project: dict) -> List[str]:
    crawl = project.get("crawl_config_json")
    if not isinstance(crawl, dict):
        platforms = []
    else:
        raw = crawl.get("platforms")
        platforms = [str(item).strip().lower() for item in raw] if isinstance(raw, list) else []
    if not platforms:
        platforms = []
    if not ENABLE_DY:
        platforms = [item for item in platforms if item not in {"dy", "douyin"}]
    if not ENABLE_XHS:
        platforms = [item for item in platforms if item not in {"xhs", "xiaohongshu"}]
    if platforms:
        return platforms
    fallback: List[str] = []
    if ENABLE_DY:
        fallback.append("dy")
    if ENABLE_XHS:
        fallback.append("xhs")
    return fallback


def manual_refresh(project: dict) -> Optional[dict]:
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        return None

    payload: Dict[str, Any] = {
        "count": RELAY_PER_TASK_COUNT,
        "wait_timeout_seconds": RELAY_WAIT_TIMEOUT_SECONDS,
        "analysis_wait_timeout_seconds": RELAY_ANALYSIS_WAIT_TIMEOUT_SECONDS,
        "poll_interval_ms": RELAY_POLL_INTERVAL_MS,
        "result_limit": RELAY_RESULT_LIMIT,
        "sorts": RELAY_SORTS,
        "timeFilter": RELAY_TIME_FILTER_DAYS,
        "time_filter": RELAY_TIME_FILTER_DAYS,
    }

    search_keys = parse_terms(project.get("search_key_list") or "")
    if search_keys:
        payload["search_keys"] = search_keys

    platforms = extract_project_platforms(project)
    if platforms:
        payload["platforms"] = platforms

    endpoint = f"/api/v1/projects/{urllib.parse.quote(project_id)}/manual-refresh"
    timeout = max(RELAY_API_TIMEOUT, RELAY_WAIT_TIMEOUT_SECONDS + RELAY_ANALYSIS_WAIT_TIMEOUT_SECONDS + 60)
    result = relay_request(endpoint, method="POST", data=payload, timeout_seconds=timeout, retry_count=1)
    if result_code(result) != 0:
        code = result_code(result)
        msg = (result or {}).get("message") if isinstance(result, dict) else ""
        print(f"❌ Relay 刷新失败 project={project_id} code={code} msg={msg}")
        return None
    return (result or {}).get("data") or {}


def list_project_works(project_id: str, limit: int) -> List[dict]:
    query = urllib.parse.urlencode({"page": 1, "page_size": max(1, min(200, int(limit or 20)))})
    endpoint = f"/api/v1/projects/{urllib.parse.quote(str(project_id))}/works?{query}"
    result = relay_request(endpoint)
    if result_code(result) != 0:
        return []
    data = (result or {}).get("data") or {}
    items = data.get("items") or []
    return items if isinstance(items, list) else []


def has_latest_opinion(work: dict) -> bool:
    if not isinstance(work, dict):
        return False
    latest_opinion = work.get("latest_opinion")
    if isinstance(latest_opinion, dict):
        opinion_key = str(latest_opinion.get("opinion_key") or "").strip()
        if opinion_key:
            return True
    fallback_key = str(work.get("latest_opinion_key") or "").strip()
    return bool(fallback_key)


def recalc_pending_opinion_ids(work_items: List[dict], target_ids: List[int]) -> List[int]:
    if not target_ids:
        return []
    by_id: Dict[int, dict] = {}
    for work in work_items:
        try:
            work_id = int(work.get("id") or 0)
        except Exception:
            work_id = 0
        if work_id > 0:
            by_id[work_id] = work
    pending: List[int] = []
    for target_id in target_ids:
        current = by_id.get(int(target_id))
        if not has_latest_opinion(current or {}):
            pending.append(int(target_id))
    return pending


def refresh_works_for_pending_opinions(project_id: str, target_ids: List[int], initial_items: List[dict]) -> Dict[str, Any]:
    items = list(initial_items or [])
    pending_ids = recalc_pending_opinion_ids(items, target_ids)
    if not pending_ids:
        return {"items": items, "pending_ids": pending_ids, "recheck_rounds": 0}
    if RELAY_POST_REFRESH_RECHECK_ROUNDS <= 0:
        return {"items": items, "pending_ids": pending_ids, "recheck_rounds": 0}

    fetch_limit = max(RELAY_RESULT_LIMIT, len(target_ids), 10)
    rounds = 0
    while pending_ids and rounds < RELAY_POST_REFRESH_RECHECK_ROUNDS:
        rounds += 1
        time.sleep(RELAY_POST_REFRESH_RECHECK_INTERVAL_SECONDS)
        latest_items = list_project_works(project_id, fetch_limit)
        if latest_items:
            items = latest_items
            pending_ids = recalc_pending_opinion_ids(items, target_ids)
    return {"items": items, "pending_ids": pending_ids, "recheck_rounds": rounds}


def execute_main_flow(project_ids_text: Optional[str] = None) -> dict:
    print("=" * 70)
    print("🚀 OpenClaw Relay 编排 - full")
    print("=" * 70)
    if not probe_relay():
        return {"code": 7, "msg": relay_unavailable_message()}

    projects = resolve_target_projects(project_ids_text)
    if not projects:
        return {"code": 7, "msg": "未获取到可执行项目"}

    summary_items: List[dict] = []
    failed_project_ids: List[str] = []
    total_tasks = 0
    total_works = 0
    total_opinion_targets = 0
    total_opinion_pending = 0

    for project in projects:
        project_id = str(project.get("id") or "")
        project_name = str(project.get("project_name") or project.get("name") or project_id)
        print(f"\n📋 刷新项目：{project_name} ({project_id})")
        refreshed = manual_refresh(project)
        if not refreshed:
            failed_project_ids.append(project_id)
            continue

        tasks = refreshed.get("tasks") or {}
        works = refreshed.get("works") or {}
        task_items = tasks.get("items") or []
        work_items = works.get("items") or []
        analysis_target_ids = [int(item) for item in (works.get("analysis_target_work_ids") or []) if str(item).isdigit()]
        analysis_pending_ids = [int(item) for item in (works.get("analysis_pending_work_ids") or []) if str(item).isdigit()]

        recheck = refresh_works_for_pending_opinions(project_id, analysis_target_ids, work_items)
        work_items = recheck.get("items") or work_items
        if analysis_target_ids:
            analysis_pending_ids = recheck.get("pending_ids") or analysis_pending_ids

        opinion_target = len(analysis_target_ids)
        opinion_pending = len(analysis_pending_ids)
        opinion_ready = max(0, opinion_target - opinion_pending)

        total_tasks += len(task_items)
        total_works += len(work_items)
        total_opinion_targets += opinion_target
        total_opinion_pending += opinion_pending
        summary_items.append(
            {
                "project_id": project_id,
                "project_name": project_name,
                "task_total": int(tasks.get("total") or len(task_items)),
                "task_finished": int(tasks.get("finished") or 0),
                "task_pending": int(tasks.get("pending") or 0),
                "task_failed": int(tasks.get("failed") or 0),
                "task_timed_out": bool(tasks.get("timed_out")),
                "work_total": int(works.get("total") or len(work_items)),
                "work_returned": int(works.get("returned") or len(work_items)),
                "opinion_target": opinion_target,
                "opinion_ready": opinion_ready,
                "opinion_pending": opinion_pending,
                "analysis_wait_timeout_seconds": int(
                    ((refreshed.get("parameters") or {}).get("analysis_wait_timeout_seconds"))
                    or RELAY_ANALYSIS_WAIT_TIMEOUT_SECONDS
                ),
                "post_refresh_recheck_rounds": int(recheck.get("recheck_rounds") or 0),
            }
        )
        print(
            f"   ✅ tasks={len(task_items)} works={len(work_items)} "
            f"(finished={tasks.get('finished')}, pending={tasks.get('pending')}) "
            f"opinions={opinion_ready}/{opinion_target}"
        )
        if opinion_pending > 0:
            print(f"   ⏳ 仍有 {opinion_pending} 条作品分析中，建议稍后再次读取 works")

    if not summary_items:
        return {"code": 7, "msg": "全部项目刷新失败"}

    msg = "成功"
    if failed_project_ids:
        msg = f"部分成功，失败项目 {len(failed_project_ids)} 个"
    return {
        "code": 0,
        "data": {
            "mode": "full",
            "project_count": len(summary_items),
            "task_count": total_tasks,
            "work_count": total_works,
            "opinion_target_count": total_opinion_targets,
            "opinion_pending_count": total_opinion_pending,
            "failed_project_ids": failed_project_ids,
            "items": summary_items,
        },
        "msg": msg,
    }


def execute_chat(project_ids_text: Optional[str] = None) -> dict:
    print("=" * 70)
    print("🚀 OpenClaw Relay 编排 - chat")
    print("=" * 70)
    if not probe_relay():
        return {"code": 7, "msg": relay_unavailable_message()}

    if RELAY_CHAT_AUTO_REFRESH:
        print("⚡ chat 模式先触发一次 full 主流程刷新")
        full_result = execute_full(project_ids_text)
        if result_code(full_result, default=7) != 0:
            print(f"⚠️ full 主流程失败: {full_result.get('msg')}")

    projects = resolve_target_projects(project_ids_text)
    if not projects:
        return {"code": 7, "msg": "未获取到可查询项目"}

    rows: List[dict] = []
    seen_work_ids: set[str] = set()
    fetch_limit = max(RELAY_CHAT_SAMPLE_SIZE * 3, 10)

    for project in projects:
        project_id = str(project.get("id") or "")
        project_name = str(project.get("project_name") or project.get("name") or project_id)
        works = list_project_works(project_id, fetch_limit)
        for work in works:
            work_id = str(work.get("id") or "").strip()
            if not work_id or work_id in seen_work_ids:
                continue
            seen_work_ids.add(work_id)

            latest_opinion = work.get("latest_opinion")
            if not isinstance(latest_opinion, dict):
                latest_opinion = {}

            opinion_key = str(latest_opinion.get("opinion_key") or work.get("latest_opinion_key") or "").strip() or "未分析"
            opinion_direction = str(latest_opinion.get("opinion_direction") or work.get("latest_opinion_direction") or "").strip()
            reason = str(latest_opinion.get("reason") or work.get("latest_opinion_reason") or "").strip()

            rows.append(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "platform": str(work.get("platform") or ""),
                    "work_id": work_id,
                    "title": str(work.get("title") or work.get("content") or "").strip(),
                    "opinion_key": opinion_key,
                    "opinion_direction": opinion_direction,
                    "reason": reason,
                    "updated_at": work.get("updated_at"),
                }
            )
            if len(rows) >= RELAY_CHAT_SAMPLE_SIZE:
                break
        if len(rows) >= RELAY_CHAT_SAMPLE_SIZE:
            break

    if not rows:
        return {"code": 7, "msg": "暂无可展示舆情结果，请先执行 full 主流程"}

    return {
        "code": 0,
        "data": {
            "mode": "chat",
            "sample_size": len(rows),
            "items": rows,
        },
        "msg": "成功（Relay 数据源）",
    }


def execute_full(project_ids_text: Optional[str] = None) -> dict:
    main_result = execute_main_flow(project_ids_text)
    if result_code(main_result, default=7) != 0:
        return main_result
    return {
        "code": 0,
        "data": {
            "mode": "full",
            "workflow": main_result.get("data") or {},
        },
        "msg": "成功（主流程闭环：读项目 -> 发任务 -> 等结果 -> 回写）",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw Relay 编排脚本（精简版）")
    parser.add_argument("project_ids", nargs="?", help="项目 ID 列表，多个用英文逗号分隔；不传则取 RELAY_PROJECT_IDS 或全部项目")
    parser.add_argument(
        "--mode",
        "-m",
        default="full",
        help="默认 full（单任务主流程）；chat 用于人工查看样本。历史 dispatch/process/analyze 会自动映射到 full。",
    )
    args = parser.parse_args()
    mode = str(args.mode or "full").strip().lower()
    deprecated_modes = {"dispatch", "process", "analyze"}
    if mode in deprecated_modes:
        print(f"⚠️ --mode {mode} 已废弃，自动切换为 --mode full")
        mode = "full"

    if mode == "chat":
        result = execute_chat(args.project_ids)
    elif mode == "full":
        result = execute_full(args.project_ids)
    else:
        result = {
            "code": 7,
            "msg": f"不支持的 mode: {mode}，请使用 full 或 chat",
            "data": {"mode": mode},
        }

    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
