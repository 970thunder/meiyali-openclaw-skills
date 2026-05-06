#!/usr/bin/env python3
"""
舆情监控工作流脚本（项目级版本）

新版说明：
- 不再依赖场景配置
- 不在定时任务里写死项目 ID
- 默认从 `/openclaw/project/list` 动态获取项目列表
- 如需限定项目范围，可在 `.env.meiyali` 中配置 `OPINION_PROJECT_IDS=30001,30002`
- dispatch/process 通过本地任务队列衔接，避免依赖不存在的任务列表接口
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parents[2]
ENV_PATH = WORKSPACE_DIR / ".env.meiyali"
DATA_DIR = WORKSPACE_DIR / "data"
QUEUE_PATH = DATA_DIR / "opinion-monitor-task-queue.json"


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


ENV = read_env_file(ENV_PATH)
API_KEY = os.getenv("MEIYALI_API_KEY") or os.getenv("API_KEY") or ENV.get("MEIYALI_API_KEY") or ENV.get("API_KEY") or ""
BASE_URL = (
    os.getenv("MEIYALI_API_BASE_URL")
    or os.getenv("API_BASE_URL")
    or ENV.get("MEIYALI_API_BASE_URL")
    or ENV.get("API_BASE_URL")
    or "http://host.docker.internal:8888"
).rstrip("/")
CONFIGURED_PROJECT_IDS = (
    os.getenv("OPINION_PROJECT_IDS")
    or ENV.get("OPINION_PROJECT_IDS")
    or os.getenv("OPINION_PROJECT_ID")
    or ENV.get("OPINION_PROJECT_ID")
    or ""
)
HEADERS = {"api-key": API_KEY, "Content-Type": "application/json"}
MIN_TEXT_LENGTH = 36
AGENT_TIMEOUT_SECONDS = int(os.getenv("OPENCLAW_ANALYSIS_TIMEOUT") or ENV.get("OPENCLAW_ANALYSIS_TIMEOUT") or "240")
ANALYSIS_BATCH_SIZE = int(os.getenv("OPENCLAW_ANALYSIS_BATCH_SIZE") or ENV.get("OPENCLAW_ANALYSIS_BATCH_SIZE") or "8")
API_TIMEOUT_SECONDS = int(os.getenv("OPENCLAW_API_TIMEOUT") or ENV.get("OPENCLAW_API_TIMEOUT") or "30")
API_RETRY_COUNT = max(1, int(os.getenv("OPENCLAW_API_RETRY_COUNT") or ENV.get("OPENCLAW_API_RETRY_COUNT") or "3"))
ANALYSIS_RETRY_COUNT = max(1, int(os.getenv("OPENCLAW_ANALYSIS_RETRY_COUNT") or ENV.get("OPENCLAW_ANALYSIS_RETRY_COUNT") or "2"))
ANALYSIS_API_URL = (os.getenv("OPENCLAW_ANALYSIS_API_URL") or ENV.get("OPENCLAW_ANALYSIS_API_URL") or "").strip()
ANALYSIS_API_KEY = (os.getenv("OPENCLAW_ANALYSIS_API_KEY") or ENV.get("OPENCLAW_ANALYSIS_API_KEY") or "").strip()
TASK_RESULT_FAIL_MAX = max(1, int(os.getenv("OPENCLAW_TASK_RESULT_FAIL_MAX") or ENV.get("OPENCLAW_TASK_RESULT_FAIL_MAX") or "6"))
MAX_WORKS_PER_TASK = 10
DY_SEARCH_COUNT = min(MAX_WORKS_PER_TASK, max(1, int(os.getenv("OPENCLAW_DY_SEARCH_COUNT") or ENV.get("OPENCLAW_DY_SEARCH_COUNT") or "10")))
XHS_SEARCH_COUNT = min(MAX_WORKS_PER_TASK, max(1, int(os.getenv("OPENCLAW_XHS_SEARCH_COUNT") or ENV.get("OPENCLAW_XHS_SEARCH_COUNT") or "10")))
PROCESS_MAX_TASKS_PER_RUN = max(1, int(os.getenv("OPENCLAW_PROCESS_MAX_TASKS_PER_RUN") or ENV.get("OPENCLAW_PROCESS_MAX_TASKS_PER_RUN") or "4"))
CHAT_SAMPLE_SIZE = min(5, max(3, int(os.getenv("OPENCLAW_CHAT_SAMPLE_SIZE") or ENV.get("OPENCLAW_CHAT_SAMPLE_SIZE") or "5")))
CHAT_MAX_TASKS_SCAN = max(1, int(os.getenv("OPENCLAW_CHAT_MAX_TASKS_SCAN") or ENV.get("OPENCLAW_CHAT_MAX_TASKS_SCAN") or "3"))
CHAT_TASK_RESULT_TIMEOUT_SECONDS = max(2, int(os.getenv("OPENCLAW_CHAT_TASK_RESULT_TIMEOUT") or ENV.get("OPENCLAW_CHAT_TASK_RESULT_TIMEOUT") or "4"))
CHAT_API_RETRY_COUNT = max(1, int(os.getenv("OPENCLAW_CHAT_API_RETRY_COUNT") or ENV.get("OPENCLAW_CHAT_API_RETRY_COUNT") or "1"))
CHAT_WORK_IDS_PER_TASK = max(CHAT_SAMPLE_SIZE, min(20, int(os.getenv("OPENCLAW_CHAT_WORK_IDS_PER_TASK") or ENV.get("OPENCLAW_CHAT_WORK_IDS_PER_TASK") or "20")))
CHAT_AUTO_DISPATCH = str(os.getenv("OPENCLAW_CHAT_AUTO_DISPATCH") or ENV.get("OPENCLAW_CHAT_AUTO_DISPATCH") or "1").strip().lower() not in {"0", "false", "off", "no"}
CHAT_DISPATCH_COOLDOWN_SECONDS = max(0, int(os.getenv("OPENCLAW_CHAT_DISPATCH_COOLDOWN") or ENV.get("OPENCLAW_CHAT_DISPATCH_COOLDOWN") or "0"))
TASK_STATUS_PENDING_TIMEOUT_SECONDS = max(300, int(os.getenv("OPENCLAW_TASK_STATUS_PENDING_TIMEOUT") or ENV.get("OPENCLAW_TASK_STATUS_PENDING_TIMEOUT") or "1200"))
ENABLE_DY = str(os.getenv("OPENCLAW_ENABLE_DY") or ENV.get("OPENCLAW_ENABLE_DY") or "1").strip().lower() not in {"0", "false", "off", "no"}
ENABLE_XHS = str(os.getenv("OPENCLAW_ENABLE_XHS") or ENV.get("OPENCLAW_ENABLE_XHS") or "1").strip().lower() not in {"0", "false", "off", "no"}
MEDIA_EXTRACT_TIMEOUT_SECONDS = max(1, int(os.getenv("OPENCLAW_MEDIA_EXTRACT_TIMEOUT") or ENV.get("OPENCLAW_MEDIA_EXTRACT_TIMEOUT") or "6"))
MEDIA_EXTRACT_RETRY_COUNT = max(1, int(os.getenv("OPENCLAW_MEDIA_EXTRACT_RETRY_COUNT") or ENV.get("OPENCLAW_MEDIA_EXTRACT_RETRY_COUNT") or "1"))
MEDIA_EXTRACT_FAIL_FAST_MAX = max(1, int(os.getenv("OPENCLAW_MEDIA_EXTRACT_FAIL_FAST_MAX") or ENV.get("OPENCLAW_MEDIA_EXTRACT_FAIL_FAST_MAX") or "2"))
MEDIA_EXTRACT_DISABLED = False
MEDIA_EXTRACT_FAILURES = 0

NEGATIVE_HINTS = [
    "避雷", "踩雷", "翻车", "太坑", "坑", "垃圾", "离谱", "吐槽", "不满", "失望", "无语", "崩溃",
    "投诉", "维权", "拒赔", "拒保", "套路", "骗", "坑人", "拉黑", "差评", "闹心", "糟糕", "难用",
    "劝退", "封号", "冻结", "不退", "退不了", "虚假", "欺诈", "暴雷", "跑路", "裁员",
]
POSITIVE_HINTS = [
    "推荐", "值得", "靠谱", "真香", "满意", "好用", "不错", "喜欢", "好评", "回购", "稳定", "专业",
    "放心", "省心", "靠谱", "报销到账", "理赔快", "通过了", "高效", "给力", "真不错", "优秀",
]
STRONG_NEGATIVE_HINTS = [
    "投诉", "维权", "拒赔", "拒保", "欺诈", "诈骗", "骗保", "骗", "虚假", "暴雷", "跑路",
    "拉黑", "封号", "冻结", "不退", "退不了", "垃圾", "坑人", "太坑", "劝退", "避雷",
]
NEGATIVE_NEGATION_PREFIXES = ["不", "没", "无", "非", "别", "勿", "避免", "防止", "拒绝", "远离", "规避"]
NEGATIVE_SAFE_PHRASES = [
    "不踩坑", "别踩坑", "避免踩坑", "防踩坑", "拒绝踩坑",
    "不踩雷", "别踩雷", "避免踩雷", "防踩雷", "拒绝踩雷",
    "避坑", "防坑", "防骗", "反诈",
]


def parse_csv_ids(text: str) -> List[str]:
    return [item.strip() for item in str(text or "").split(",") if item.strip()]


def parse_terms(text: str) -> List[str]:
    normalized = str(text or "")
    for sep in ["\n", "，", "/", "、", "；", ";", "|"]:
        normalized = normalized.replace(sep, ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[dict] = None,
    timeout_seconds: Optional[int] = None,
    retry_count: Optional[int] = None,
) -> Optional[dict]:
    if not API_KEY:
        print("❌ 未找到 API_KEY / MEIYALI_API_KEY")
        return None
    url = f"{BASE_URL}{endpoint}"
    retries = max(1, int(retry_count or API_RETRY_COUNT))
    timeout = max(1, int(timeout_seconds or API_TIMEOUT_SECONDS))
    for attempt in range(1, retries + 1):
        try:
            if method == "GET":
                req = urllib.request.Request(url, headers=HEADERS)
            else:
                body = json.dumps(data or {}, ensure_ascii=False).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
            response = urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=timeout)
            return json.loads(response.read())
        except urllib.error.URLError as err:
            print(f"❌ 请求失败(第{attempt}/{retries}次): {err}")
        except Exception as err:
            print(f"❌ 异常(第{attempt}/{retries}次): {err}")
        if attempt < retries:
            time.sleep(min(6, attempt * 2))
    return None


def extract_media_summary(material_urls: List[str], content: str = "") -> str:
    global MEDIA_EXTRACT_DISABLED, MEDIA_EXTRACT_FAILURES
    urls = [item for item in material_urls if item][:10]
    if not urls:
        return ""

    if MEDIA_EXTRACT_DISABLED:
        return ""

    result = api_request(
        "/openclaw/media/extract",
        "POST",
        {
            "material_urls": urls,
            "content": content,
        },
        timeout_seconds=MEDIA_EXTRACT_TIMEOUT_SECONDS,
        retry_count=MEDIA_EXTRACT_RETRY_COUNT,
    )
    if result and result.get("code") == 0:
        MEDIA_EXTRACT_FAILURES = 0
        return " ".join(str((result.get("data") or {}).get("summary") or "").split())

    MEDIA_EXTRACT_FAILURES += 1
    if MEDIA_EXTRACT_FAILURES >= MEDIA_EXTRACT_FAIL_FAST_MAX:
        MEDIA_EXTRACT_DISABLED = True
        print("   ⚠️ media/extract 连续失败，本轮已熔断，后续跳过素材抽取避免阻塞")
    return ""


def get_project_list() -> List[dict]:
    result = api_request("/openclaw/project/list?page=1&pageSize=100")
    if result and result.get("code") == 0:
        data = result.get("data") or {}
        return data.get("list") or []
    return []


def get_project_config(project_id: str) -> Optional[dict]:
    result = api_request(f"/openclaw/project/find?id={urllib.parse.quote(str(project_id))}")
    if result and result.get("code") == 0:
        return result.get("data") or {}
    return None


def dispatch_plugin_task(skill: str, action: str, payload: dict) -> Optional[str]:
    result = api_request("/openclaw/command/plugin", "POST", {
        "skill": skill,
        "action": action,
        "payload": payload,
    })
    if result and result.get("code") == 0:
        return ((result.get("data") or {}).get("task_id"))
    if result:
        print(f"   ❌ 下发失败 {skill}/{action}: code={result.get('code')} msg={result.get('msg') or ''}")
    else:
        print(f"   ❌ 下发失败 {skill}/{action}: API 无响应")
    return None


def get_task_result_response(task_id: str, timeout_seconds: Optional[int] = None, retry_count: Optional[int] = None) -> Optional[dict]:
    return api_request(
        f"/openclaw/task/result?task_id={urllib.parse.quote(task_id)}",
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
    )


def get_task_result(task_id: str, timeout_seconds: Optional[int] = None, retry_count: Optional[int] = None) -> Optional[dict]:
    result = get_task_result_response(task_id, timeout_seconds=timeout_seconds, retry_count=retry_count)
    if result and result.get("code") == 0:
        return result.get("data") or {}
    return None


def list_opinions(work_project_id: str, work_ids: List[str]) -> List[dict]:
    if not work_ids:
        return []
    query = "&".join(f"work_ids[]={urllib.parse.quote(str(item))}" for item in work_ids if str(item))
    result = api_request(f"/openclaw/opinion/list?work_project_id={urllib.parse.quote(str(work_project_id))}&{query}")
    if result and result.get("code") == 0:
        data = result.get("data")
        if isinstance(data, list):
            return data
    return []


def finish_tasks(task_ids: List[str]) -> bool:
    if not task_ids:
        return True
    result = api_request("/openclaw/task/finish", "POST", {"task_ids": task_ids})
    return bool(result and result.get("code") == 0)


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_queue() -> List[dict]:
    ensure_data_dir()
    if not QUEUE_PATH.exists():
        return []
    try:
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_queue(records: List[dict]) -> None:
    ensure_data_dir()
    QUEUE_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_queue_entries(entries: List[dict]) -> None:
    queue = load_queue()
    indexed = {str(item.get("task_id")): item for item in queue}
    for entry in entries:
        indexed[str(entry.get("task_id"))] = entry
    save_queue(list(indexed.values()))


def has_recent_active_task(queue: List[dict], project_id: str, platform: str, now_ts: int) -> bool:
    if CHAT_DISPATCH_COOLDOWN_SECONDS <= 0:
        return False
    for task in queue:
        if str(task.get("work_project_id") or "") != str(project_id):
            continue
        if str(task.get("platform") or "") != str(platform):
            continue
        status = str(task.get("status") or "")
        if status == "finished" or status.startswith("failed_"):
            continue
        queued_at = int(task.get("queued_at") or 0)
        if queued_at and (now_ts - queued_at) < CHAT_DISPATCH_COOLDOWN_SECONDS:
            return True
    return False


class ProjectCriteria:
    def __init__(self, project: dict):
        self.project = project
        self.project_id = str(project.get("id") or "")
        self.project_name = project.get("project_name") or project.get("name") or "未命名项目"
        self.brand_description = project.get("brand_description") or ""
        self.brand_tags_description = project.get("brand_tags_description") or ""
        self.competing_brand_description = project.get("competing_brand_description") or ""
        self.search_key_list = project.get("search_key_list") or ""
        self.opinion_configs = project.get("opinion_configs") or []

        self.own_brands = parse_terms(self.brand_description)
        self.competing_brands = parse_terms(self.competing_brand_description)

    def summary(self) -> str:
        return (
            f"项目: {self.project_name}\n"
            f"自有品牌: {', '.join(self.own_brands) if self.own_brands else '未设置'}\n"
            f"竞品品牌: {', '.join(self.competing_brands) if self.competing_brands else '未设置'}\n"
            f"项目搜索词: {self.search_key_list or '未设置'}\n"
            f"舆情标准: {json.dumps(self.opinion_configs, ensure_ascii=False)}"
        )


def detect_brand(text: str, criteria: ProjectCriteria) -> Dict[str, str]:
    lower_text = text.lower()
    for brand in criteria.own_brands:
        if brand and brand.lower() in lower_text:
            return {"type": "自有品牌", "value": brand}
    for brand in criteria.competing_brands:
        if brand and brand.lower() in lower_text:
            return {"type": "竞品", "value": brand}
    return {"type": "未识别品牌", "value": "未识别品牌"}


def collect_material_urls(item: dict) -> List[str]:
    urls: List[str] = []
    direct_keys = ["video", "video_url", "videoUrl", "cover_url", "coverUrl", "image", "image_url", "imageUrl"]
    for key in direct_keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            urls.append(value.strip())
    for key in ["images", "image_urls", "imageUrls", "covers", "cover_urls"]:
        value = item.get(key)
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, str) and entry.strip():
                    urls.append(entry.strip())
                elif isinstance(entry, dict):
                    for sub_key in ["url", "src", "image", "image_url", "cover_url"]:
                        sub_val = entry.get(sub_key)
                        if isinstance(sub_val, str) and sub_val.strip():
                            urls.append(sub_val.strip())
                            break
    seen = set()
    ordered: List[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def clean_text(text: str) -> str:
    return " ".join(str(text or "").replace("\n", " ").split())


def trim_text(text: str, limit: int) -> str:
    value = clean_text(text)
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    return value[:limit]


def shorten_text(text: str, limit: int = 34) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def split_segments(text: str) -> List[str]:
    normalized = str(text or "")
    for sep in ["\n", "。", "！", "？", "!", "?", ";", "；"]:
        normalized = normalized.replace(sep, "|")
    return [segment.strip(" ，,") for segment in normalized.split("|") if segment.strip(" ，,")]


def find_evidence_segment(title: str, content: str, hits: List[str]) -> str:
    segments = split_segments(title) + split_segments(content)
    lower_hits = [item.lower() for item in hits if item]
    for segment in segments:
        lower_segment = segment.lower()
        if any(hit in lower_segment for hit in lower_hits):
            return shorten_text(segment, 42)
    if title.strip():
        return shorten_text(title, 42)
    if content.strip():
        return shorten_text(content, 42)
    return "内容较短，需结合上下文理解"


def detect_tone(text: str, negative_hits: List[str], positive_hits: List[str]) -> str:
    lower_text = text.lower()
    if negative_hits:
        if any(word in lower_text for word in ["避雷", "太坑", "坑", "垃圾", "吐槽", "不满", "失望", "无语", "踩雷"]):
            return "明显吐槽或宣泄不满"
        if any(word in lower_text for word in ["投诉", "维权", "拒赔", "拒保", "套路", "骗"]):
            return "明确表达风险、投诉或权益受损"
        return "整体语气偏负面，带有明显担忧或否定"
    if positive_hits:
        if any(word in lower_text for word in ["推荐", "值得", "靠谱", "真香", "满意", "好用", "不错"]):
            return "明确表达认可、推荐或满意"
        return "整体语气积极，对产品或服务持肯定态度"
    if any(word in lower_text for word in ["测评", "分享", "记录", "科普", "对比", "了解一下", "问问"]):
        return "更像信息分享、经验记录或客观讨论"
    return "未出现明显褒贬，整体偏客观陈述"


def needs_media_extraction(title: str, content: str) -> bool:
    text = clean_text(f"{title} {content}")
    if not text:
        return True
    if len(text) < MIN_TEXT_LENGTH:
        return True
    weak_cues = ["见图", "如图", "看图", "看视频", "自己看", "无语", "这波", "离谱", "服了"]
    lower_text = text.lower()
    return any(cue in lower_text for cue in weak_cues)


def build_reason(title: str, content: str, media_summary: str, brand_info: Dict[str, str], opinion_key: str, positive_hits: List[str], negative_hits: List[str]) -> str:
    base_text = clean_text(f"{title} {content} {media_summary}")
    evidence = find_evidence_segment(title, content, negative_hits or positive_hits)
    if media_summary and (not evidence or evidence == shorten_text(title, 42) or evidence == shorten_text(content, 42)):
        evidence = shorten_text(media_summary, 42)
    brand_value = brand_info["value"]
    tone = detect_tone(base_text, negative_hits, positive_hits)
    source_hint = "结合图片/视频提取结果，" if media_summary else ""

    if opinion_key == "负面":
        if title.strip():
            return f"{source_hint}标题提到“{shorten_text(title, 28)}”，结合正文中“{evidence}”的表述，可见内容在评价「{brand_value}」时{tone}，情感倾向负面。"
        return f"{source_hint}正文中“{evidence}”直接体现出对「{brand_value}」的{tone}，整体判断为负面。"

    if opinion_key == "正面":
        if title.strip():
            return f"{source_hint}标题提到“{shorten_text(title, 28)}”，结合正文中“{evidence}”的表达，可见内容在评价「{brand_value}」时{tone}，情感倾向正面。"
        return f"{source_hint}正文中“{evidence}”体现出对「{brand_value}」的认可与正向反馈，整体判断为正面。"

    if title.strip():
        return f"{source_hint}标题提到“{shorten_text(title, 28)}”，正文主要围绕“{evidence}”展开，整体{tone}，未形成明显正负评价，因此判定为中性。"
    return f"{source_hint}正文主要围绕“{evidence}”展开，整体{tone}，未体现明确褒贬，因此判定为中性。"


def build_opinion_think(title: str, content: str, media_summary: str, brand_info: Dict[str, str], positive_hits: List[str], negative_hits: List[str], opinion_key: str, reason: str) -> str:
    content_summary = shorten_text(title or content or media_summary or "内容较短", 40)
    evidence = find_evidence_segment(title, content, negative_hits or positive_hits)
    if media_summary and (not evidence or evidence == shorten_text(title, 42) or evidence == shorten_text(content, 42)):
        evidence = shorten_text(media_summary, 42)
    tone = detect_tone(clean_text(f"{title} {content} {media_summary}"), negative_hits, positive_hits)
    media_line = f"；文本不足时补充参考了素材提取结果“{shorten_text(media_summary, 36)}”" if media_summary else ""
    return (
        f"1. 内容概述：这条内容核心在说“{content_summary}”。\n"
        f"2. 主体识别：结合标题和正文，当前讨论对象识别为{brand_info['type']}「{brand_info['value']}」。\n"
        f"3. 情绪依据：重点表述落在“{evidence}”，可以看出作者{tone}{media_line}。\n"
        f"4. 判断过程：正向线索为「{'、'.join(positive_hits) if positive_hits else '无'}」，负向线索为「{'、'.join(negative_hits) if negative_hits else '无'}」，结合整体语气后判定为「{opinion_key}」。\n"
        f"5. 结论：{reason}"
    )


def collect_hits(text: str, words: List[str]) -> List[str]:
    lower_text = str(text or "").lower()
    hits: List[str] = []
    seen: set[str] = set()
    for word in words:
        token = str(word or "").strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        if key in lower_text:
            seen.add(key)
            hits.append(token)
    return hits[:8]


def _is_negated_negative_occurrence(text: str, token: str, index: int) -> bool:
    left = text[max(0, index - 4):index]
    around = text[max(0, index - 4):min(len(text), index + len(token) + 4)]
    if any(phrase in around for phrase in NEGATIVE_SAFE_PHRASES):
        return True
    return any(left.endswith(prefix) for prefix in NEGATIVE_NEGATION_PREFIXES)


def normalize_negative_hits(text: str, hits: List[str]) -> List[str]:
    lower_text = str(text or "").lower()
    normalized: List[str] = []
    for token in hits:
        key = str(token or "").strip().lower()
        if not key:
            continue
        start = 0
        keep = False
        while True:
            idx = lower_text.find(key, start)
            if idx == -1:
                break
            if not _is_negated_negative_occurrence(lower_text, key, idx):
                keep = True
                break
            start = idx + len(key)
        if keep:
            normalized.append(token)
    return normalized


def has_strong_negative_signal(text: str, negative_hits: List[str]) -> bool:
    lower_text = str(text or "").lower()
    if any(token.lower() in lower_text for token in STRONG_NEGATIVE_HINTS):
        return True
    strong_hit_tokens = {"投诉", "维权", "拒赔", "拒保", "欺诈", "诈骗", "暴雷", "跑路", "拉黑", "封号", "冻结"}
    return any(str(hit or "").strip().lower() in strong_hit_tokens for hit in negative_hits)


def select_opinion_key(negative_hits: List[str], positive_hits: List[str], text: str) -> str:
    lower_text = str(text or "").lower()
    negative_score = len(negative_hits) * 2
    positive_score = len(positive_hits) * 2

    if any(token in lower_text for token in ["投诉", "维权", "拒赔", "拒保", "骗", "欺诈", "暴雷", "跑路"]):
        negative_score += 3
    if any(token in lower_text for token in ["避雷", "劝退", "翻车", "失望", "垃圾", "坑人"]):
        negative_score += 2

    if any(token in lower_text for token in ["推荐", "回购", "好评", "满意", "放心", "稳定"]):
        positive_score += 3
    if any(token in lower_text for token in ["好用", "不错", "靠谱", "给力", "优秀"]):
        positive_score += 2

    if negative_score >= positive_score + 2:
        return "负面"
    if positive_score >= negative_score + 2:
        return "正面"
    return "中性"


def build_local_analysis(prepared: dict, criteria: ProjectCriteria, fallback_note: str = "") -> Dict[str, str]:
    title = clean_text(prepared.get("title") or "")
    content = clean_text(prepared.get("content") or "")
    media_summary = clean_text(prepared.get("media_summary") or "")
    merged_text = clean_text(f"{title} {content} {media_summary}")

    brand_info = detect_brand(merged_text, criteria)
    if brand_info.get("value") == "未识别品牌":
        hint_value = str(prepared.get("brand_hint") or "").strip()
        hint_type = str(prepared.get("brand_type_hint") or "").strip() or "未识别品牌"
        if hint_value:
            brand_info = {"type": hint_type, "value": hint_value}

    negative_hits = normalize_negative_hits(merged_text, collect_hits(merged_text, NEGATIVE_HINTS))
    positive_hits = collect_hits(merged_text, POSITIVE_HINTS)
    opinion_key = select_opinion_key(negative_hits, positive_hits, merged_text)
    if opinion_key == "负面" and brand_info.get("value") == "未识别品牌" and not has_strong_negative_signal(merged_text, negative_hits):
        opinion_key = "中性"
    reason = build_reason(title, content, media_summary, brand_info, opinion_key, positive_hits, negative_hits)
    opinion_think = build_opinion_think(title, content, media_summary, brand_info, positive_hits, negative_hits, opinion_key, reason)
    if fallback_note:
        opinion_think = f"{clean_text(fallback_note)}\n{opinion_think}"

    return {
        "opinion_key": opinion_key,
        "opinion_direction": str(brand_info.get("value") or "未识别品牌"),
        "reason": reason,
        "opinion_think": opinion_think,
    }


def prepare_analysis_material(item: dict, criteria: ProjectCriteria) -> dict:
    title = clean_text(item.get("title") or "")
    content = clean_text(item.get("content") or item.get("desc") or "")
    full_text = f"{title} {content}".strip()
    brand_info = detect_brand(full_text, criteria)
    media_summary = ""

    if needs_media_extraction(title, content):
        media_summary = extract_media_summary(collect_material_urls(item), content=title or content)
        if media_summary:
            full_text = clean_text(f"{full_text} {media_summary}")
            brand_info = detect_brand(full_text, criteria)

    return {
        "work_id": str(item.get("workId") or item.get("work_id") or ""),
        "title": title,
        "content": content,
        "media_summary": clean_text(media_summary),
        "brand_hint": brand_info["value"],
        "brand_type_hint": brand_info["type"],
    }


def strip_json_fence(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def extract_json_object(text: str) -> dict:
    cleaned = strip_json_fence(text)
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def post_json(url: str, payload: dict, timeout_seconds: Optional[int] = None, extra_headers: Optional[Dict[str, str]] = None) -> dict:
    body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    timeout = max(1, int(timeout_seconds or API_TIMEOUT_SECONDS))
    resp = urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=timeout)
    raw = resp.read().decode("utf-8", errors="ignore")
    if not raw.strip():
        return {}
    return json.loads(raw)


def run_analysis_via_http_api(criteria: ProjectCriteria, items: List[dict]) -> dict:
    if not ANALYSIS_API_URL:
        raise RuntimeError("未配置 OPENCLAW_ANALYSIS_API_URL")
    payload = {
        "project": {
            "project_id": criteria.project_id,
            "project_name": criteria.project_name,
            "brand_description": criteria.brand_description,
            "brand_tags_description": criteria.brand_tags_description,
            "competing_brand_description": criteria.competing_brand_description,
            "search_key_list": criteria.search_key_list,
            "opinion_configs": criteria.opinion_configs,
        },
        "items": items,
    }
    headers: Dict[str, str] = {}
    if ANALYSIS_API_KEY:
        headers["Authorization"] = f"Bearer {ANALYSIS_API_KEY}"
        headers["x-api-key"] = ANALYSIS_API_KEY
    response = post_json(ANALYSIS_API_URL, payload, timeout_seconds=AGENT_TIMEOUT_SECONDS, extra_headers=headers)
    if not isinstance(response, dict):
        raise RuntimeError("分析 API 响应格式错误")
    if isinstance(response.get("results"), list):
        return response
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return data
    raise RuntimeError("分析 API 返回缺少 results")


def build_agent_prompt(criteria: ProjectCriteria, items: List[dict]) -> str:
    project_context = {
        "project_id": criteria.project_id,
        "project_name": criteria.project_name,
        "brand_description": criteria.brand_description,
        "brand_tags_description": criteria.brand_tags_description,
        "competing_brand_description": criteria.competing_brand_description,
        "search_key_list": criteria.search_key_list,
        "opinion_configs": criteria.opinion_configs,
    }
    batch_items = []
    for item in items:
        batch_items.append({
            "work_id": item["work_id"],
            "title": item["title"],
            "content": item["content"],
            "media_summary": item["media_summary"],
            "brand_hint": item["brand_hint"],
            "brand_type_hint": item["brand_type_hint"],
        })

    return (
        "你是舆情分析助手。请严格根据项目配置、自有品牌、竞品描述、主题标签描述、作品标题、正文、素材摘要，"
        "为每条作品输出结构化舆情判断。\n"
        "要求：\n"
        "1. 只能输出 JSON，不要输出 markdown。\n"
        "2. opinion_key 只能是“正面”“负面”“中性”之一。\n"
        "3. opinion_direction 应填写讨论主体；若无法明确识别主体，可写空字符串。\n"
        "4. reason 必须是基于真实语义判断的一句话中文，不要写“检测到关键词”“命中词”这类机械表述。\n"
        "5. opinion_think 需要简要说明判断过程，体现你如何结合标题、正文、素材摘要与项目标准得出结论。\n"
        "6. 如果文本信息不足但素材摘要提供了有效线索，要把素材摘要纳入判断。\n"
        "7. 如果无法从内容看出明确褒贬，默认判为中性，不要强行猜测。\n"
        "8. 返回格式必须为 {\"results\":[...]}，results 内每项包含 work_id、opinion_key、opinion_direction、reason、opinion_think。\n\n"
        f"项目配置:\n{json.dumps(project_context, ensure_ascii=False, indent=2)}\n\n"
        f"待分析作品:\n{json.dumps(batch_items, ensure_ascii=False, indent=2)}"
    )


def analyze_sentiment_batch(items: List[dict], criteria: ProjectCriteria) -> Dict[str, Dict[str, str]]:
    if not items:
        return {}
    if not ANALYSIS_API_URL:
        raise RuntimeError("未配置 OPENCLAW_ANALYSIS_API_URL，编排层仅支持通过 API 完成分析")

    last_err = ""
    response: dict = {}
    for attempt in range(1, ANALYSIS_RETRY_COUNT + 1):
        try:
            response = run_analysis_via_http_api(criteria, items)
            break
        except Exception as err:
            last_err = clean_text(str(err))
            print(f"   ⚠️  分析 API 重试 {attempt}/{ANALYSIS_RETRY_COUNT} 失败: {err}")
            if attempt < ANALYSIS_RETRY_COUNT:
                time.sleep(min(3, attempt * 2))
    if not response:
        raise RuntimeError(last_err or "OpenClaw 分析失败")
    results = response.get("results")
    if not isinstance(results, list):
        raise RuntimeError("OpenClaw 返回缺少 results 数组")

    mapped: Dict[str, Dict[str, str]] = {}
    for item in results:
        work_id = str((item or {}).get("work_id") or "")
        if not work_id:
            continue
        opinion_key = str((item or {}).get("opinion_key") or "中性")
        if opinion_key not in {"正面", "负面", "中性"}:
            opinion_key = "中性"
        mapped[work_id] = {
            "opinion_key": opinion_key,
            "opinion_direction": str((item or {}).get("opinion_direction") or "").strip() or str((next((x for x in items if str(x.get("work_id") or "") == work_id), {}) or {}).get("brand_hint") or "未识别品牌"),
            "reason": clean_text((item or {}).get("reason") or ""),
            "opinion_think": clean_text((item or {}).get("opinion_think") or ""),
        }
    return mapped


def upload_opinion(work_project_id: str, work_id: str, analysis: Dict[str, str]) -> bool:
    opinion_key = trim_text(analysis.get("opinion_key") or "中性", 10) or "中性"
    opinion_direction = trim_text(analysis.get("opinion_direction") or "未识别品牌", 50) or "未识别品牌"
    reason = trim_text(analysis.get("reason") or "", 50) or "内容信息有限，暂判中性。"
    opinion_think = clean_text(analysis.get("opinion_think") or "")
    payload = {
        "work_project_id": int(work_project_id),
        "work_id": int(work_id),
        "opinion_key": opinion_key,
        "opinion_direction": opinion_direction,
        "opinion_think": opinion_think,
        "reason": reason,
    }
    result = api_request("/openclaw/opinion/upload", "POST", payload)
    if result and result.get("code") == 0:
        return True
    print(f"   ⚠️ opinion/upload 失败 work_id={work_id} code={(result or {}).get('code')} msg={(result or {}).get('msg')}")
    return False


def process_task_items(task_data: dict, project: dict) -> Dict[str, int]:
    criteria = ProjectCriteria(project)
    raw_data = task_data.get("raw_data") or {}
    all_items = raw_data.get("items") or []
    items = list(all_items)[:MAX_WORKS_PER_TASK]
    stats = {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "uploaded": 0, "failed": 0}

    print(f"\n📊 开始处理项目「{criteria.project_name}」的 {len(items)} 条数据")
    if len(all_items) > len(items):
        print(f"   ⚡ 任务返回 {len(all_items)} 条，已按快速模式截断为前 {len(items)} 条处理")
    prepared_items: List[Tuple[int, dict, dict]] = []
    seen_work_ids: set[str] = set()
    for index, item in enumerate(items, start=1):
        work_id = str(item.get("workId") or item.get("work_id") or "").strip()
        if not work_id or work_id in seen_work_ids:
            continue
        seen_work_ids.add(work_id)
        prepared = prepare_analysis_material(item, criteria)
        if not prepared.get("work_id"):
            prepared["work_id"] = work_id
        prepared_items.append((index, item, prepared))

    analysis_map: Dict[str, Dict[str, str]] = {}
    batch_analysis_failed = False
    for batch_start in range(0, len(prepared_items), ANALYSIS_BATCH_SIZE):
        batch = prepared_items[batch_start : batch_start + ANALYSIS_BATCH_SIZE]
        batch_materials = [entry[2] for entry in batch if entry[2].get("work_id")]
        if not batch_materials:
            continue
        try:
            analysis_map.update(analyze_sentiment_batch(batch_materials, criteria))
        except Exception as err:
            print(f"   ❌ OpenClaw 分析失败: {err}")
            batch_analysis_failed = True

    for index, item, prepared in prepared_items:
        stats["total"] += 1
        current_work_id = str(prepared.get("work_id") or item.get("workId") or item.get("work_id") or "").strip()
        if not current_work_id:
            stats["failed"] += 1
            print(f"  [{index}] ❌ 缺少 work_id，跳过上传")
            continue
        analysis = analysis_map.get(current_work_id)
        if not analysis:
            note = "分析 API 暂不可用，已切换本地语义兜底。"
            if not batch_analysis_failed:
                note = "分析 API 返回结果不完整，已使用本地语义补齐。"
            analysis = build_local_analysis(prepared, criteria, fallback_note=note)
        else:
            if analysis.get("opinion_key") not in {"正面", "负面", "中性"}:
                analysis["opinion_key"] = "中性"
            if not clean_text(analysis.get("reason") or "") or not clean_text(analysis.get("opinion_think") or ""):
                supplement = build_local_analysis(prepared, criteria, fallback_note="OpenClaw 返回字段缺失，已补齐结构化说明。")
                if not clean_text(analysis.get("reason") or ""):
                    analysis["reason"] = supplement["reason"]
                if not clean_text(analysis.get("opinion_think") or ""):
                    analysis["opinion_think"] = supplement["opinion_think"]
                if not clean_text(analysis.get("opinion_direction") or ""):
                    analysis["opinion_direction"] = supplement["opinion_direction"]
        analysis["opinion_direction"] = str(analysis.get("opinion_direction") or "").strip() or str(prepared.get("brand_hint") or "未识别品牌")
        if analysis["opinion_key"] == "正面":
            stats["positive"] += 1
        elif analysis["opinion_key"] == "负面":
            stats["negative"] += 1
        else:
            stats["neutral"] += 1

        success = upload_opinion(str(project.get("id")), current_work_id, analysis)
        title = str(item.get("title") or item.get("desc") or "")
        if success:
            stats["uploaded"] += 1
            print(f"  [{index}] ✅ {analysis['opinion_key']} | {title[:28]}")
        else:
            stats["failed"] += 1
            print(f"  [{index}] ❌ 上传失败 | {title[:28]}")
    return stats


def resolve_target_projects(project_ids_text: Optional[str] = None) -> List[dict]:
    projects = get_project_list()
    if not projects:
        return []
    target_ids = parse_csv_ids(project_ids_text or CONFIGURED_PROJECT_IDS)
    if not target_ids:
        return projects
    return [item for item in projects if str(item.get("id")) in target_ids]


def build_search_payload(keywords: str, count: int, xhs: bool = False) -> dict:
    count = max(1, min(MAX_WORKS_PER_TASK, int(count)))
    payload = {
        "keywords": keywords,
        "count": count,
        "sorts": ["default", "time_descending"],
        "timeFilter": "7",
    }
    if xhs:
        payload["noteType"] = 0
        payload["includeDetails"] = True
    return payload


def execute_dispatch_only(project_ids_text: Optional[str] = None) -> dict:
    print("=" * 70)
    print("🚀 舆情监控 - 任务下发模式")
    print("=" * 70)
    projects = resolve_target_projects(project_ids_text)
    if not projects:
        return {"code": 7, "msg": "未获取到可执行的舆情项目"}

    entries: List[dict] = []
    for project in projects:
        project_id = str(project.get("id"))
        project_name = project.get("project_name") or project.get("name") or project_id
        keywords = ",".join(parse_terms(project.get("search_key_list") or ""))
        if not keywords:
            print(f"⚠️  项目「{project_name}」未配置项目搜索词，跳过")
            continue

        print(f"\n📋 项目：{project_name} ({project_id})")
        print(f"   搜索词：{keywords}")

        if ENABLE_DY:
            dy_task_id = dispatch_plugin_task("meiyali-plugin-dy", "dy.search", build_search_payload(keywords, DY_SEARCH_COUNT))
            if dy_task_id:
                entries.append({
                    "task_id": dy_task_id,
                    "platform": "douyin",
                    "work_project_id": project_id,
                    "project_name": project_name,
                    "status": "waiting_result",
                    "queued_at": int(time.time()),
                    "last_task_status": 0,
                    "result_query_failures": 0,
                })
                print(f"   ✅ 抖音任务已下发: {dy_task_id[:10]}...")
        else:
            print("   ⏭️  抖音下发已关闭（OPENCLAW_ENABLE_DY=0）")

        if ENABLE_XHS:
            xhs_task_id = dispatch_plugin_task("meiyali-plugin-xhs", "xhs.search", build_search_payload(keywords, XHS_SEARCH_COUNT, xhs=True))
            if xhs_task_id:
                entries.append({
                    "task_id": xhs_task_id,
                    "platform": "xiaohongshu",
                    "work_project_id": project_id,
                    "project_name": project_name,
                    "status": "waiting_result",
                    "queued_at": int(time.time()),
                    "last_task_status": 0,
                    "result_query_failures": 0,
                })
                print(f"   ✅ 小红书任务已下发: {xhs_task_id[:10]}...")
        else:
            print("   ⏭️  小红书下发已关闭（OPENCLAW_ENABLE_XHS=0）")

    if entries:
        upsert_queue_entries(entries)

    return {
        "code": 0,
        "data": {
            "project_count": len(projects),
            "task_count": len(entries),
            "projects": [str(item.get("id")) for item in projects],
            "mode": "dispatch",
        },
        "msg": "成功" if entries else "没有可下发任务；等待定时 process 执行，不要前台运行 process",
    }


def execute_process_only(project_ids_text: Optional[str] = None) -> dict:
    print("=" * 70)
    print("🚀 舆情监控 - 任务处理模式")
    print("=" * 70)
    queue = load_queue()
    if not queue:
        return {"code": 0, "data": {"processed_tasks": 0}, "msg": "任务队列为空"}

    allowed_ids = set(parse_csv_ids(project_ids_text or CONFIGURED_PROJECT_IDS))
    project_index = {str(item.get("id")): item for item in get_project_list()}
    summary = {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "uploaded": 0, "failed": 0}
    finished_task_ids: List[str] = []
    handled_tasks = 0

    for task in sorted(queue, key=lambda x: int(x.get("queued_at") or 0), reverse=True):
        status = str(task.get("status") or "")
        if status == "finished" or status.startswith("failed_"):
            continue
        project_id = str(task.get("work_project_id") or "")
        if allowed_ids and project_id not in allowed_ids:
            continue

        task_id = str(task.get("task_id") or "")
        if not task_id:
            continue
        print(f"\n⏳ 检查任务: {task_id[:10]}... ({task.get('platform')})")
        task_result = get_task_result_response(task_id)
        if not task_result:
            failed_count = int(task.get("result_query_failures") or 0) + 1
            task["result_query_failures"] = failed_count
            if failed_count >= TASK_RESULT_FAIL_MAX:
                task["status"] = "failed_result_query"
                task["failed_at"] = int(time.time())
                task["failed_reason"] = f"task/result 连续失败 {failed_count} 次"
                print(f"   ❌ 查询 task/result 连续失败 {failed_count} 次，标记失败")
                handled_tasks += 1
                if handled_tasks >= PROCESS_MAX_TASKS_PER_RUN:
                    break
            continue

        try:
            task_code = int(task_result.get("code") or 0)
        except Exception:
            task_code = -999
        if task_code == 7:
            task["status"] = "failed_task_not_found"
            task["failed_at"] = int(time.time())
            task["failed_reason"] = f"task/result 查询失败: {task_result.get('msg') or '任务不存在'}"
            task["result_query_failures"] = int(task.get("result_query_failures") or 0) + 1
            print(f"   ❌ task/result 返回 code=7，任务已失效，标记失败并跳过")
            handled_tasks += 1
            if handled_tasks >= PROCESS_MAX_TASKS_PER_RUN:
                break
            continue

        if task_code != 0:
            failed_count = int(task.get("result_query_failures") or 0) + 1
            task["result_query_failures"] = failed_count
            print(f"   ⚠️ task/result 异常 code={task_code} msg={task_result.get('msg')}")
            if failed_count >= TASK_RESULT_FAIL_MAX:
                task["status"] = "failed_result_query"
                task["failed_at"] = int(time.time())
                task["failed_reason"] = f"task/result 异常 code={task_code}"
                handled_tasks += 1
                if handled_tasks >= PROCESS_MAX_TASKS_PER_RUN:
                    break
            continue

        task_data = task_result.get("data") or {}

        task_status = int(task_data.get("task_status") or 0)
        task["last_task_status"] = task_status
        task["result_query_failures"] = 0
        if task_status == 3:
            task["status"] = "finished"
            task["finished_at"] = int(time.time())
            finished_task_ids.append(task_id)
            print("   ✅ 远端已结束(task_status=3)，本地直接收口")
            handled_tasks += 1
            if handled_tasks >= PROCESS_MAX_TASKS_PER_RUN:
                break
            continue
        if task_status in (-1, -2):
            task["status"] = "failed_task_status"
            task["failed_at"] = int(time.time())
            task["failed_reason"] = f"上游任务状态异常: {task_status}"
            print(f"   ❌ 上游任务失败，task_status={task_status}，标记失败")
            handled_tasks += 1
            if handled_tasks >= PROCESS_MAX_TASKS_PER_RUN:
                break
            continue
        if task_status == 1:
            queued_at = int(task.get("queued_at") or 0)
            wait_seconds = int(time.time()) - queued_at if queued_at else 0
            if queued_at and wait_seconds >= TASK_STATUS_PENDING_TIMEOUT_SECONDS:
                task["status"] = "failed_task_timeout"
                task["failed_at"] = int(time.time())
                task["failed_reason"] = f"任务长时间处理中超时: {wait_seconds}s"
                finish_tasks([task_id])
                print(f"   ❌ 任务长时间处于处理中(task_status=1, {wait_seconds}s)，标记超时失败")
                continue
            print(f"   当前状态: {task_status}，继续等待")
            continue
        if task_status not in (2, 3):
            print(f"   当前状态: {task_status}，继续等待")
            continue

        raw_items = ((task_data.get("raw_data") or {}).get("items") or [])
        if raw_items:
            preview: List[dict] = []
            preview_seen: set[str] = set()
            for raw_item in raw_items:
                preview_work_id = str(raw_item.get("workId") or raw_item.get("work_id") or "").strip()
                if not preview_work_id or preview_work_id in preview_seen:
                    continue
                preview_seen.add(preview_work_id)
                preview.append({
                    "work_id": preview_work_id,
                    "title": clean_text(raw_item.get("title") or raw_item.get("desc") or ""),
                    "content": clean_text(raw_item.get("content") or raw_item.get("desc") or ""),
                })
                if len(preview) >= CHAT_WORK_IDS_PER_TASK:
                    break
            task["last_items_preview"] = preview
            task["last_item_count"] = len(raw_items)
        else:
            cached_preview = task.get("last_items_preview")
            cached_items: List[dict] = []
            if isinstance(cached_preview, list) and cached_preview:
                for preview in cached_preview:
                    preview_work_id = str((preview or {}).get("work_id") or "").strip()
                    if not preview_work_id:
                        continue
                    cached_items.append({
                        "workId": preview_work_id,
                        "title": clean_text((preview or {}).get("title") or ""),
                        "content": clean_text((preview or {}).get("content") or ""),
                    })
                    if len(cached_items) >= MAX_WORKS_PER_TASK:
                        break
            if cached_items:
                print(f"   ⚡ task/result items=0，改用 last_items_preview 缓存 {len(cached_items)} 条继续处理")
                raw_items = cached_items
                task_data = dict(task_data)
                raw_data_obj = dict(task_data.get("raw_data") or {})
                raw_data_obj["items"] = raw_items
                task_data["raw_data"] = raw_data_obj

        if task_status == 2 and not raw_items:
            print("   ⚡ 任务无可处理作品(items=0)，直接标记完成")
            if finish_tasks([task_id]):
                task["status"] = "finished"
                task["finished_at"] = int(time.time())
                finished_task_ids.append(task_id)
                print("   ✅ 已标记任务完成")
            handled_tasks += 1
            if handled_tasks >= PROCESS_MAX_TASKS_PER_RUN:
                break
            continue

        project = project_index.get(project_id) or get_project_config(project_id)
        if not project:
            print(f"   ⚠️  项目 {project_id} 不存在，跳过")
            continue

        stats = process_task_items(task_data, project)
        for key in summary:
            summary[key] += stats.get(key, 0)

        if (stats["total"] == 0) or (stats["failed"] == 0 and stats["uploaded"] == stats["total"]):
            if finish_tasks([task_id]):
                task["status"] = "finished"
                task["finished_at"] = int(time.time())
                finished_task_ids.append(task_id)
                print(f"   ✅ 已标记任务完成")
        handled_tasks += 1
        if handled_tasks >= PROCESS_MAX_TASKS_PER_RUN:
            break

    save_queue(queue)
    return {
        "code": 0,
        "data": {
            "processed_tasks": len(finished_task_ids),
            "summary": summary,
            "finished_task_ids": finished_task_ids,
            "mode": "process",
        },
        "msg": "成功",
    }


def execute_chat_only(project_ids_text: Optional[str] = None) -> dict:
    print("=" * 70)
    print("🚀 舆情监控 - 对话快速模式")
    print("=" * 70)
    queue = load_queue()

    allowed_ids = set(parse_csv_ids(project_ids_text or CONFIGURED_PROJECT_IDS))
    if CHAT_AUTO_DISPATCH:
        dispatch_projects = resolve_target_projects(project_ids_text)
        now_ts = int(time.time())
        new_entries: List[dict] = []
        if dispatch_projects:
            print("⚡ 对话模式触发一次最新任务下发（不阻塞当前回复）")
        for project in dispatch_projects:
            project_id = str(project.get("id") or "")
            if allowed_ids and project_id not in allowed_ids:
                continue
            project_name = project.get("project_name") or project.get("name") or project_id
            keywords = ",".join(parse_terms(project.get("search_key_list") or ""))
            if not keywords:
                continue

            if ENABLE_DY and not has_recent_active_task(queue, project_id, "douyin", now_ts):
                dy_task_id = dispatch_plugin_task("meiyali-plugin-dy", "dy.search", build_search_payload(keywords, DY_SEARCH_COUNT))
                if dy_task_id:
                    new_entries.append({
                        "task_id": dy_task_id,
                        "platform": "douyin",
                        "work_project_id": project_id,
                        "project_name": project_name,
                        "status": "waiting_result",
                        "queued_at": now_ts,
                        "last_task_status": 0,
                        "result_query_failures": 0,
                    })
                    print(f"   ✅ chat 下发抖音任务: {dy_task_id[:10]}...")

            if ENABLE_XHS and not has_recent_active_task(queue, project_id, "xiaohongshu", now_ts):
                xhs_task_id = dispatch_plugin_task("meiyali-plugin-xhs", "xhs.search", build_search_payload(keywords, XHS_SEARCH_COUNT, xhs=True))
                if xhs_task_id:
                    new_entries.append({
                        "task_id": xhs_task_id,
                        "platform": "xiaohongshu",
                        "work_project_id": project_id,
                        "project_name": project_name,
                        "status": "waiting_result",
                        "queued_at": now_ts,
                        "last_task_status": 0,
                        "result_query_failures": 0,
                    })
                    print(f"   ✅ chat 下发小红书任务: {xhs_task_id[:10]}...")
        if new_entries:
            upsert_queue_entries(new_entries)
            queue = load_queue()

    if not queue:
        return {"code": 7, "msg": "暂无任务队列，可先等待定时 dispatch/process 产出数据"}

    rows: List[dict] = []
    seen_work_ids = set()
    source_task_ids: List[str] = []
    scanned_tasks = 0
    checked_tasks = 0
    queue_dirty = False
    max_checked_tasks = max(CHAT_SAMPLE_SIZE + 2, CHAT_MAX_TASKS_SCAN * 4)
    for task in sorted(queue, key=lambda x: int(x.get("queued_at") or 0), reverse=True):
        if len(rows) >= CHAT_SAMPLE_SIZE or checked_tasks >= max_checked_tasks:
            break
        checked_tasks += 1
        project_id = str(task.get("work_project_id") or "")
        if allowed_ids and project_id not in allowed_ids:
            continue

        task_id = str(task.get("task_id") or "")
        if not task_id:
            continue

        item_index: Dict[str, dict] = {}
        work_ids: List[str] = []
        cached_preview = task.get("last_items_preview")
        if isinstance(cached_preview, list) and cached_preview:
            for preview in cached_preview:
                wid = str((preview or {}).get("work_id") or "").strip()
                if not wid or wid in item_index:
                    continue
                item_index[wid] = {
                    "title": clean_text((preview or {}).get("title") or ""),
                    "content": clean_text((preview or {}).get("content") or ""),
                }
                work_ids.append(wid)
                if len(work_ids) >= CHAT_WORK_IDS_PER_TASK:
                    break
        else:
            if scanned_tasks >= CHAT_MAX_TASKS_SCAN:
                continue
            scanned_tasks += 1
            task_result = get_task_result_response(
                task_id,
                timeout_seconds=CHAT_TASK_RESULT_TIMEOUT_SECONDS,
                retry_count=CHAT_API_RETRY_COUNT,
            )
            if not task_result:
                continue

            try:
                task_code = int(task_result.get("code") or 0)
            except Exception:
                task_code = -999
            if task_code == 7:
                task["status"] = "failed_task_not_found"
                task["failed_at"] = int(time.time())
                task["failed_reason"] = f"chat 查询 task/result 失败: {task_result.get('msg') or '任务不存在'}"
                queue_dirty = True
                continue
            if task_code != 0:
                continue

            task_data = task_result.get("data") or {}
            task_status = int(task_data.get("task_status") or 0)
            task["last_task_status"] = task_status
            if task_status not in (2, 3):
                continue

            raw_items = ((task_data.get("raw_data") or {}).get("items") or [])
            if not raw_items:
                cached_items: List[dict] = []
                task_cached_preview = task.get("last_items_preview")
                if isinstance(task_cached_preview, list) and task_cached_preview:
                    for preview in task_cached_preview:
                        preview_work_id = str((preview or {}).get("work_id") or "").strip()
                        if not preview_work_id:
                            continue
                        cached_items.append({
                            "workId": preview_work_id,
                            "title": clean_text((preview or {}).get("title") or ""),
                            "content": clean_text((preview or {}).get("content") or ""),
                        })
                        if len(cached_items) >= CHAT_WORK_IDS_PER_TASK:
                            break
                if not cached_items:
                    continue
                raw_items = cached_items

            preview: List[dict] = []
            preview_seen: set[str] = set()
            for raw_item in raw_items:
                preview_work_id = str(raw_item.get("workId") or raw_item.get("work_id") or "").strip()
                if not preview_work_id or preview_work_id in preview_seen:
                    continue
                preview_seen.add(preview_work_id)
                preview.append({
                    "work_id": preview_work_id,
                    "title": clean_text(raw_item.get("title") or raw_item.get("desc") or ""),
                    "content": clean_text(raw_item.get("content") or raw_item.get("desc") or ""),
                })
                if len(preview) >= CHAT_WORK_IDS_PER_TASK:
                    break
            if preview:
                task["last_items_preview"] = preview
                queue_dirty = True

            for item in raw_items:
                wid = str(item.get("workId") or item.get("work_id") or "")
                if not wid or wid in item_index:
                    continue
                item_index[wid] = {
                    "title": clean_text(item.get("title") or item.get("desc") or ""),
                    "content": clean_text(item.get("content") or item.get("desc") or ""),
                }
                work_ids.append(wid)
                if len(work_ids) >= CHAT_WORK_IDS_PER_TASK:
                    break

        opinions = list_opinions(project_id, work_ids)
        if not opinions:
            continue

        source_task_ids.append(task_id)
        for op in opinions:
            wid = str(op.get("work_id") or "")
            if not wid or wid in seen_work_ids:
                continue
            src = item_index.get(wid) or {}
            rows.append({
                "work_id": wid,
                "title": clean_text(src.get("title") or src.get("content") or ""),
                "opinion_key": str(op.get("opinion_key") or ""),
                "opinion_direction": str(op.get("opinion_direction") or ""),
                "reason": clean_text(op.get("reason") or ""),
                "updated_at": op.get("updated_at"),
                "platform": task.get("platform"),
                "project_id": project_id,
                "project_name": task.get("project_name"),
            })
            seen_work_ids.add(wid)
            if len(rows) >= CHAT_SAMPLE_SIZE:
                break

    if queue_dirty:
        save_queue(queue)

    if rows:
        return {
            "code": 0,
            "data": {
                "mode": "chat",
                "source_task_ids": source_task_ids[:8],
                "sample_size": len(rows),
                "items": rows,
            },
            "msg": "成功（仅展示最新3-5条，完整处理由定时任务执行）",
        }

    return {"code": 7, "msg": "暂无可展示的舆情结果，请等待定时任务完成后再试"}


def execute_full_workflow(project_ids_text: Optional[str] = None) -> dict:
    dispatch_result = execute_dispatch_only(project_ids_text)
    time.sleep(2)
    process_result = execute_process_only(project_ids_text)
    return {
        "code": 0,
        "data": {
            "dispatch": dispatch_result.get("data") or {},
            "process": process_result.get("data") or {},
            "mode": "full",
        },
        "msg": "成功",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="舆情监控统一工作流脚本（项目级）")
    parser.add_argument("project_ids", nargs="?", help="项目 ID 列表，多个用英文逗号分隔")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["chat", "full", "dispatch", "process"],
        default="chat",
        help="默认 chat（快速展示3-5条）；需要下发/处理时显式使用 --mode dispatch/--mode process",
    )
    args = parser.parse_args()

    if args.mode == "chat":
        result = execute_chat_only(args.project_ids)
    elif args.mode == "dispatch":
        result = execute_dispatch_only(args.project_ids)
    elif args.mode == "process":
        result = execute_process_only(args.project_ids)
    else:
        result = execute_full_workflow(args.project_ids)

    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
