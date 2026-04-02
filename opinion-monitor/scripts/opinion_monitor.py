#!/usr/bin/env python3
"""
舆情监控工作流脚本（编排层）

本脚本是 opinion-monitor Skill 的执行入口，负责协调多个子 Skill 完成完整的舆情监控流程。

编排的子 Skill：
  1. openclaw-project-config   - 获取项目/场景配置
  2. meiyali-plugin-dy        - 下发抖音搜索任务
  3. meiyali-plugin-xhs       - 下发小红书搜索任务
  4. openclaw-task-polling    - 轮询任务结果（内置）
  5. openclaw-opinion-callback - 上传舆情分析结果
  6. openclaw-project-config   - 标记任务完成

支持三种执行模式：
  1. full     - 完整流程（默认）：下发任务 → 轮询 → 分析 → 上传
  2. dispatch - 仅下发任务：下发任务 → 任务状态 0 → 1 → 2
  3. process  - 仅处理任务：查询 status=2 → 分析 → 上传 → 状态 2 → 3

使用方式：
  python3 opinion_monitor.py                    # 完整流程（默认项目和场景）
  python3 opinion_monitor.py 30001 40001        # 完整流程（指定项目和场景）
  python3 opinion_monitor.py --mode dispatch    # 仅下发任务
  python3 opinion_monitor.py --mode process     # 仅处理已完成任务
"""
import json
import urllib.request
import urllib.error
import ssl
import os
import sys
import time
import re
import argparse
from typing import Dict, List, Optional, Tuple

API_KEY = "3ae4d7b1f3e2c0d58326e52a4cc98fb6b3fdb4849a9b945706cb367a78c0c713"
BASE_URL = "http://127.0.0.1:8888"
HEADERS = {"api-key": API_KEY, "Content-Type": "application/json"}

def api_request(endpoint: str, method: str = "GET", data: dict = None) -> Optional[dict]:
    """通用 API 请求函数"""
    try:
        url = f"{BASE_URL}{endpoint}"
        if method == "GET":
            req = urllib.request.Request(url, headers=HEADERS)
        else:
            body = json.dumps(data).encode() if data else b"{}"
            req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
        
        ctx = ssl._create_unverified_context()
        response = urllib.request.urlopen(req, context=ctx, timeout=30)
        return json.loads(response.read())
    except urllib.error.URLError as e:
        print(f"❌ 请求失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 异常: {e}")
        return None

def get_project_config(project_id: int) -> Optional[dict]:
    """获取项目配置

    Skill: openclaw-project-config
    Action: get_project
    """
    result = api_request(f"/openclaw/project/find?id={project_id}")
    if result and result.get('code') == 0:
        return result.get('data')
    return None

def get_scene_config(work_project_id: int) -> List[dict]:
    """获取场景配置列表

    Skill: openclaw-project-config
    Action: list_scenes
    """
    result = api_request(f"/openclaw/project/scene/list?work_project_id={work_project_id}")
    if result and result.get('code') == 0:
        return result.get('data', {}).get('list', [])
    return []

def get_scene_detail(scene_id: int) -> Optional[dict]:
    """获取单个场景详情

    Skill: openclaw-project-config
    Action: get_scene
    """
    result = api_request(f"/openclaw/project/scene/find?id={scene_id}")
    if result and result.get('code') == 0:
        return result.get('data')
    return None

def dispatch_plugin_task(skill: str, action: str, payload: dict) -> Optional[str]:
    """下发插件任务

    Skill: meiyali-plugin-dy / meiyali-plugin-xhs
    Action: dispatch_task
    """
    data = {"skill": skill, "action": action, "payload": payload}
    result = api_request("/openclaw/command/plugin", "POST", data)
    if result and result.get('code') == 0:
        return result.get('data', {}).get('task_id')
    return None

def poll_task_result(task_id: str, max_attempts: int = 20, interval: int = 3) -> Optional[dict]:
    """轮询任务结果

    Skill: openclaw-task-polling (内置)
    Action: poll_until_complete
    """
    print(f"⏳ 开始轮询任务: {task_id[:10]}...")
    
    for i in range(max_attempts):
        result = api_request(f"/openclaw/task/result?task_id={task_id}")
        if result and result.get('code') == 0:
            status = result.get('data', {}).get('task_status')
            
            if status == 2:
                print(f"✅ 任务完成 (第{i+1}次检查)")
                return result.get('data')
            elif status == -2:
                print(f"❌ 任务失败: {result.get('data', {}).get('raw_data', {}).get('message')}")
                return None
            
            print(f"  [{i+1}/{max_attempts}] 状态: {status}, 等待中...")
        
        time.sleep(interval)
    
    print("⏱️ 轮询超时")
    return None

def finish_tasks(task_ids: List[str]) -> bool:
    """标记任务彻底完成

    Skill: openclaw-project-config
    Action: finish_task

    仅当任务中所有作品都完成舆情分析后才调用此接口。
    任务状态会从 2 变为 3（任务结束）。

    Returns:
        True: 标记成功
        False: 标记失败
    """
    if not task_ids:
        return True
    
    print(f"\n🏁 标记任务彻底完成: {task_ids}")
    data = {"task_ids": task_ids}
    result = api_request("/openclaw/task/finish", "POST", data)
    
    if result and result.get('code') == 0:
        finished_count = result.get('data', {}).get('finished_count', 0)
        print(f"✅ 已标记 {finished_count} 个任务为结束状态 (状态=3)")
        return True
    else:
        print(f"❌ 标记失败: {result}")
        return False

def parse_keywords(keywords: any) -> str:
    """解析关键词
    
    支持两种格式：
    - 逗号分隔字符串: "猫粮,宠物食品"
    - 列表: ["猫粮", "宠物食品"]
    
    Returns:
        逗号分隔的字符串（兼容插件 API）
    """
    if not keywords:
        return ""
    if isinstance(keywords, str):
        return keywords
    if isinstance(keywords, list):
        return ",".join(keywords)
    return str(keywords)

class OpinionCriteriaParser:
    """舆情判断标准解析器
    
    从场景描述中解析舆情判断标准
    格式示例：
    
    品牌描述:卫仕,醇粹,大玛仕
    竞品描述:皇家,渴望,爱肯拿
    正向关键词:推荐,好,喜欢,种草,好评,回购
    负向关键词:差,避雷,坑,差评,曝光,垃圾
    """
    
    def __init__(self, description: str):
        self.description = description
        self.brands: List[str] = []
        self.competing_brands: List[str] = []
        self.positive_keywords: List[str] = []
        self.negative_keywords: List[str] = []
        self._parse()
    
    def _parse(self):
        """解析场景描述"""
        lines = self.description.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('品牌描述:') or line.startswith('品牌:'):
                self._parse_list(line, ['品牌描述:', '品牌:'], self.brands)
            elif line.startswith('竞品描述:') or line.startswith('竞品:'):
                self._parse_list(line, ['竞品描述:', '竞品:'], self.competing_brands)
            elif line.startswith('正向关键词:') or line.startswith('正向:'):
                self._parse_list(line, ['正向关键词:', '正向:'], self.positive_keywords)
            elif line.startswith('负向关键词:') or line.startswith('负向:'):
                self._parse_list(line, ['负向关键词:', '负向:'], self.negative_keywords)
            elif line.startswith('中性关键词:') or line.startswith('中性:'):
                self._parse_list(line, ['中性关键词:', '中性:'], [])
    
    def _parse_list(self, line: str, prefixes: List[str], target_list: List[str]):
        """解析列表格式：前缀:项1,项2,项3"""
        for prefix in prefixes:
            if prefix in line:
                content = line.split(prefix, 1)[1].strip()
                items = [item.strip() for item in content.replace('，', ',').split(',') if item.strip()]
                target_list.extend(items)
                break
    
    def get_criteria_summary(self) -> str:
        """获取标准摘要"""
        return f"""
  品牌: {', '.join(self.brands) if self.brands else '未设置'}
  竞品: {', '.join(self.competing_brands) if self.competing_brands else '未设置'}
  正向: {', '.join(self.positive_keywords[:5])}{'...' if len(self.positive_keywords) > 5 else ''}
  负向: {', '.join(self.negative_keywords[:5])}{'...' if len(self.negative_keywords) > 5 else ''}
""".strip()

def extract_brands_from_content(text: str, brand_list: List[str], competing_list: List[str]) -> Tuple[str, str, bool]:
    """从内容中提取品牌

    Returns:
        (自有品牌, 竞品品牌, 是否无品牌)
    """
    text_lower = text.lower()
    own_brand = None
    competing_brand = None

    for brand in brand_list:
        if brand.lower() in text_lower:
            own_brand = brand
            break

    for brand in competing_list:
        if brand.lower() in text_lower:
            competing_brand = brand
            break

    if own_brand:
        return (own_brand, None, False)
    elif competing_brand:
        return (None, competing_brand, False)
    else:
        return (None, None, True)

def build_opinion_think(brand_info: dict, matched_keywords: List[str], sentiment: str, opinion: str, opinion_direction: str) -> str:
    """构建 AI 思考判断过程

    遵循 SKILL.md 中的 opinion_think 字段规范，必须包含 5 个部分：
    1. 品牌识别：从内容中识别出哪些品牌（自有品牌/竞品）
    2. 关键词匹配：检测到哪些正向/负向关键词
    3. 情感分析：内容的整体语气和情感倾向
    4. 舆情判断：基于品牌+关键词的判断逻辑
    5. 结论：最终的舆情判断及建议

    Args:
        brand_info: 品牌识别信息，包含 own_brand, competing_brand, no_brand
        matched_keywords: 匹配到的关键词列表
        sentiment: 情感分析描述
        opinion: 舆情倾向
        opinion_direction: 品牌方向

    Returns:
        opinion_think 字符串，包含完整的推理过程
    """
    own_brand = brand_info.get('own_brand')
    competing_brand = brand_info.get('competing_brand')
    no_brand = brand_info.get('no_brand')

    if competing_brand:
        brand识别 = f"竞品「{competing_brand}」"
        brand_type = "竞品"
    elif own_brand:
        brand识别 = f"自有品牌「{own_brand}」"
        brand_type = "自有品牌"
    else:
        brand识别 = "无品牌"
        brand_type = "无品牌"

    keywords_str = "、".join(matched_keywords) if matched_keywords else "未检测到正/负向关键词"

    if "正向" in opinion:
        sentiment_desc = "积极正面，用户对产品或品牌持好评态度"
    elif "负向" in opinion or "预警" in opinion:
        sentiment_desc = "消极，用户对产品或品牌存在不满或批评"
    else:
        sentiment_desc = "客观中性，无明显情感倾向"

    brand_label = "自有品牌" if own_brand else ("竞品" if competing_brand else "")
    keyword_type = "正向关键词" if any(k in "".join(criteria.positive_keywords if 'criteria' in dir() else []) for k in matched_keywords) else "负向关键词"

    conclusion = ""
    if opinion == "正向":
        conclusion = f"该内容为正向舆情，{brand识别}结合正向关键词表明用户对品牌持积极态度"
    elif opinion == "负向":
        conclusion = f"该内容为负向舆情，{brand识别}结合负向关键词表明用户对品牌存在不满"
    elif opinion == "预警":
        conclusion = f"该内容涉及竞品负面舆情，{brand识别}结合负向关键词需要关注"
    else:
        conclusion = "该内容无明显情感倾向，为中性舆情"

    return f"1. 品牌识别：内容中识别出{brand识别}\n2. 关键词匹配：检测到关键词「{keywords_str}」\n3. 情感分析：{sentiment_desc}\n4. 舆情判断：提及{brand_type} + {keyword_type} → {opinion}\n5. 结论：{conclusion}"

def analyze_sentiment(title: str, content: str, criteria: OpinionCriteriaParser) -> dict:
    """基于场景描述中的标准分析舆情

    返回包含 opinion_think 的完整分析结果
    """
    full_text = title + " " + (content or "")
    text_lower = full_text.lower()

    opinion = "中性"
    opinion_direction = ""
    reason = "内容无明显情感倾向"
    matched_keywords = []

    own_brand, competing_brand, no_brand = extract_brands_from_content(
        full_text, criteria.brands, criteria.competing_brands
    )

    brand_info = {'own_brand': own_brand, 'competing_brand': competing_brand, 'no_brand': no_brand}

    if competing_brand:
        opinion_direction = competing_brand
        for keyword in criteria.negative_keywords:
            if keyword in text_lower:
                matched_keywords.append(keyword)
                opinion_think = build_opinion_think(brand_info, matched_keywords, "消极", "预警", opinion_direction)
                return {
                    "opinion": "预警",
                    "opinion_direction": opinion_direction,
                    "reason": f"提及竞品「{competing_brand}」且包含负向关键词「{keyword}」",
                    "opinion_think": opinion_think
                }
        for keyword in criteria.positive_keywords:
            if keyword in text_lower:
                matched_keywords.append(keyword)
                opinion_think = build_opinion_think(brand_info, matched_keywords, "积极", "中性", opinion_direction)
                return {
                    "opinion": "中性",
                    "opinion_direction": opinion_direction,
                    "reason": f"提及竞品「{competing_brand}」但为正面评价",
                    "opinion_think": opinion_think
                }
        opinion_think = build_opinion_think(brand_info, [], "客观", "中性", opinion_direction)
        return {
            "opinion": "中性",
            "opinion_direction": opinion_direction,
            "reason": f"提及竞品「{competing_brand}」",
            "opinion_think": opinion_think
        }

    if own_brand:
        opinion_direction = own_brand
        for keyword in criteria.positive_keywords:
            if keyword in text_lower:
                matched_keywords.append(keyword)
                opinion_think = build_opinion_think(brand_info, matched_keywords, "积极", "正向", opinion_direction)
                return {
                    "opinion": "正向",
                    "opinion_direction": opinion_direction,
                    "reason": f"提及品牌「{own_brand}」且包含正向关键词「{keyword}」",
                    "opinion_think": opinion_think
                }
        for keyword in criteria.negative_keywords:
            if keyword in text_lower:
                matched_keywords.append(keyword)
                opinion_think = build_opinion_think(brand_info, matched_keywords, "消极", "负向", opinion_direction)
                return {
                    "opinion": "负向",
                    "opinion_direction": opinion_direction,
                    "reason": f"提及品牌「{own_brand}」且包含负向关键词「{keyword}」",
                    "opinion_think": opinion_think
                }
        opinion_think = build_opinion_think(brand_info, [], "客观", "中性", opinion_direction)
        return {
            "opinion": "中性",
            "opinion_direction": opinion_direction,
            "reason": f"提及品牌「{own_brand}」但无明显情感",
            "opinion_think": opinion_think
        }

    if no_brand:
        opinion_think = build_opinion_think(brand_info, [], "客观", "中性", opinion_direction)
        return {
            "opinion": "中性",
            "opinion_direction": "无品牌",
            "reason": "内容未提及品牌",
            "opinion_think": opinion_think
        }

    opinion_think = build_opinion_think(brand_info, [], "无明显情感", "中性", "")
    return {"opinion": opinion, "opinion_direction": opinion_direction, "reason": reason, "opinion_think": opinion_think}

def upload_opinion(work_project_id: int, work_id: int, scene_id: int,
                   opinion: str, opinion_direction: str, reason: str,
                   opinion_think: str = None) -> bool:
    """上传舆情分析结果

    Skill: openclaw-opinion-callback
    Action: upload

    Args:
        opinion_think: AI 思考判断过程（必填），包含品牌识别、关键词匹配、情感分析、判断逻辑、结论
    """
    data = {
        "work_project_id": work_project_id,
        "work_id": work_id,
        "scene_id": scene_id,
        "opinion": opinion,
        "opinion_direction": opinion_direction,
        "reason": reason
    }
    if opinion_think:
        data["opinion_think"] = opinion_think
    result = api_request("/openclaw/opinion/upload", "POST", data)
    return result and result.get('code') == 0

def process_task_items(task_data: dict, work_project_id: int, scene_id: int, 
                      criteria: OpinionCriteriaParser) -> dict:
    """处理任务数据并上传舆情分析"""
    raw_data = task_data.get('raw_data', {})
    items = raw_data.get('items', [])
    
    stats = {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "warning": 0, "uploaded": 0, "failed": 0}
    
    print(f"\n📊 开始处理 {len(items)} 条数据...")
    print(f"  舆情判断标准:")
    print(criteria.get_criteria_summary())
    
    for i, item in enumerate(items):
        work_id = item.get('workId')
        if not work_id:
            continue
        
        stats["total"] += 1
        
        author = item.get('author', '')
        title = item.get('title', '')
        content = item.get('content') or item.get('desc', '')
        
        analysis = analyze_sentiment(title, content, criteria)
        
        if analysis["opinion"] == "正向":
            stats["positive"] += 1
        elif analysis["opinion"] == "负向":
            stats["negative"] += 1
        elif analysis["opinion"] == "预警":
            stats["warning"] += 1
        else:
            stats["neutral"] += 1
        
        success = upload_opinion(
            work_project_id=work_project_id,
            work_id=work_id,
            scene_id=scene_id,
            opinion=analysis["opinion"],
            opinion_direction=analysis["opinion_direction"],
            reason=analysis["reason"],
            opinion_think=analysis.get("opinion_think", "")
        )
        
        if success:
            stats["uploaded"] += 1
            print(f"  [{i+1}] ✅ {author[:15]:15} | {title[:25]:25} | {analysis['opinion']:4} | {analysis['opinion_direction']}")
        else:
            stats["failed"] += 1
            print(f"  [{i+1}] ❌ {author[:15]:15} | {title[:25]:25} | 上传失败")
    
    return stats

def execute_full_workflow(project_id: int = None, scene_id: int = None) -> dict:
    """执行完整的舆情监控流程

    编排步骤：
      1. openclaw-project-config.get_project       - 获取项目配置
      2. openclaw-project-config.get_scene        - 获取场景配置
      3. meiyali-plugin-dy.dispatch_task          - 下发抖音任务
      4. meiyali-plugin-xhs.dispatch_task         - 下发小红书任务
      5. openclaw-task-polling.poll_until_complete - 轮询任务结果
      6. (内置) opinion_analysis                  - 舆情分析
      7. openclaw-opinion-callback.upload         - 上传舆情结果
      8. openclaw-project-config.finish_task      - 标记任务完成
    """
    print("=" * 70)
    print("🚀 舆情监控完整流程")
    print("=" * 70)
    
    if not project_id:
        project_id = 1775008425285355
    if not scene_id:
        scene_id = 1775008436157844
    
    print(f"\n📋 获取项目配置 (ID: {project_id})")
    project = get_project_config(project_id)
    if not project:
        return {"code": 7, "msg": "项目不存在"}
    print(f"  项目名称: {project.get('project_name')}")
    
    print(f"\n🎯 获取场景配置 (ID: {scene_id})")
    scene = get_scene_detail(scene_id)
    if not scene:
        scenes = get_scene_config(project_id)
        scene = next((s for s in scenes if s['id'] == scene_id), None)
        if not scene:
            return {"code": 7, "msg": "场景不存在"}
    
    print(f"  场景名称: {scene.get('name')}")
    print(f"  场景描述: {scene.get('description', '未设置')}")
    
    criteria = OpinionCriteriaParser(scene.get('description', ''))
    
    print(f"\n📝 解析舆情判断标准:")
    print(criteria.get_criteria_summary())
    
    search_keys = scene.get('search_keys', {})
    dy_config = None
    xhs_config = None
    
    # 支持两种格式：
    # 1. dict 格式: {"dy": {"keywords": "xxx", "count": 30}, "xhs": {...}}
    # 2. list 格式: [{"platform": "抖音", "search_key": "xxx"}, ...]
    
    if isinstance(search_keys, dict):
        # dict 格式
        if 'dy' in search_keys:
            dy_config = search_keys['dy']
        if 'xhs' in search_keys:
            xhs_config = search_keys['xhs']
    elif isinstance(search_keys, list):
        # list 格式
        for item in search_keys:
            platform = item.get('platform', '')
            search_key = item.get('search_key', '')
            if platform in ['抖音', 'dy']:
                dy_config = {'keywords': search_key, 'count': 30}
            elif platform in ['小红书', 'xhs']:
                xhs_config = {'keywords': search_key, 'count': 20}
    
    print("\n📤 下发插件任务")
    task_ids = []
    
    if dy_config:
        keywords = parse_keywords(dy_config.get('keywords', ''))
        print(f"  抖音关键词: {keywords}")
        dy_task_id = dispatch_plugin_task(
            skill="meiyali-plugin-dy",
            action="dy.search",
            payload={
                "keywords": keywords,
                "count": dy_config.get('count', 30),
                "sorts": ["default", "time_descending"],
                "timeFilter": "7"
            }
        )
        if dy_task_id:
            task_ids.append(('douyin', dy_task_id))
            print(f"  ✅ 抖音任务已下发: {dy_task_id[:10]}...")
    
    if xhs_config:
        keywords = parse_keywords(xhs_config.get('keywords', ''))
        print(f"  小红书关键词: {keywords}")
        xhs_task_id = dispatch_plugin_task(
            skill="meiyali-plugin-xhs",
            action="xhs.search",
            payload={
                "keywords": keywords,
                "count": xhs_config.get('count', 20),
                "sorts": ["default", "time_descending"],
                "timeFilter": "7"
            }
        )
        if xhs_task_id:
            task_ids.append(('xiaohongshu', xhs_task_id))
            print(f"  ✅ 小红书任务已下发: {xhs_task_id[:10]}...")
    
    if not task_ids:
        return {"code": 7, "msg": "没有可执行的任务"}
    
    print("\n⏳ 轮询任务结果")
    all_stats = {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "warning": 0, "uploaded": 0, "failed": 0}
    completed_task_ids = []
    
    for platform, task_id in task_ids:
        print(f"\n  [{platform}] 轮询任务...")
        task_data = poll_task_result(task_id)
        
        if task_data:
            raw_data = task_data.get('raw_data', {})
            total_items = len(raw_data.get('items', []))
            
            stats = process_task_items(task_data, project_id, scene_id, criteria)
            for key in all_stats:
                all_stats[key] += stats.get(key, 0)
            
            if stats['total'] > 0 and stats['failed'] == 0 and stats['total'] == stats['uploaded']:
                completed_task_ids.append(task_id)
    
    if completed_task_ids:
        finish_tasks(completed_task_ids)
    else:
        print("\n⚠️  未满足标记条件：")
        print("   - 必须所有作品都完成舆情分析（上传成功）")
        print("   - 任务状态保持为 2（执行成功）")
        print("   - 等待后续补全分析后再次调用 finish_task")
    
    print("\n" + "=" * 70)
    print("📊 舆情监控完成")
    print("=" * 70)
    print(f"  总数据:   {all_stats['total']} 条")
    print(f"  正向:    {all_stats['positive']} 条")
    print(f"  中性:    {all_stats['neutral']} 条")
    print(f"  负向:    {all_stats['negative']} 条")
    print(f"  预警:    {all_stats['warning']} 条")
    print(f"  上传成功: {all_stats['uploaded']} 条")
    print(f"  上传失败: {all_stats['failed']} 条")
    
    return {
        "code": 0,
        "data": {
            "project_id": project_id,
            "scene_id": scene_id,
            "project_name": project.get('project_name'),
            "scene_name": scene.get('name'),
            "scene_description": scene.get('description'),
            "criteria": {
                "brands": criteria.brands,
                "competing_brands": criteria.competing_brands,
                "positive_keywords": criteria.positive_keywords,
                "negative_keywords": criteria.negative_keywords
            },
            "status": "completed",
            "summary": all_stats,
            "finished_task_ids": completed_task_ids,
            "task_status": "3" if completed_task_ids else "2"
        },
        "msg": "成功"
    }

def get_completed_tasks(project_id: int = None) -> List[dict]:
    """查询状态为 2（执行成功）的任务列表
    
    Args:
        project_id: 可选，按项目 ID 过滤
    
    Returns:
        任务列表
    """
    endpoint = "/openclaw/task/list?status=2"
    if project_id:
        endpoint += f"&project_id={project_id}"
    
    result = api_request(endpoint)
    
    if result and result.get('code') == 0:
        return result.get('data', {}).get('list', [])
    
    # 如果 API 不存在，返回空列表
    print("⚠️  查询任务列表 API 可能不存在")
    print(f"   尝试访问: GET {endpoint}")
    return []

def execute_dispatch_only(project_id: int = None, scene_id: int = None) -> dict:
    """Part A: 仅下发任务（不下发任务后立即返回，等待定时任务处理）
    
    适用于分离模式的任务下发阶段。
    任务状态流转：0（已创建）→ 1（已下发）→ 2（执行成功）
    
    Returns:
        包含下发任务 ID 的结果
    """
    print("=" * 70)
    print("🚀 舆情监控 - 任务下发模式（Part A）")
    print("=" * 70)
    
    if not project_id:
        project_id = 1775008425285355
    if not scene_id:
        scene_id = 1775008436157844
    
    print(f"\n📋 获取项目配置 (ID: {project_id})")
    project = get_project_config(project_id)
    if not project:
        return {"code": 7, "msg": "项目不存在"}
    print(f"  项目名称: {project.get('project_name')}")
    
    print(f"\n🎯 获取场景配置 (ID: {scene_id})")
    scene = get_scene_detail(scene_id)
    if not scene:
        scenes = get_scene_config(project_id)
        scene = next((s for s in scenes if s['id'] == scene_id), None)
        if not scene:
            return {"code": 7, "msg": "场景不存在"}
    
    print(f"  场景名称: {scene.get('name')}")
    
    # 解析搜索配置
    search_keys = scene.get('search_keys', {})
    dy_config = None
    xhs_config = None
    
    if isinstance(search_keys, dict):
        if 'dy' in search_keys:
            dy_config = search_keys['dy']
        if 'xhs' in search_keys:
            xhs_config = search_keys['xhs']
    elif isinstance(search_keys, list):
        for item in search_keys:
            platform = item.get('platform', '')
            search_key = item.get('search_key', '')
            if platform in ['抖音', 'dy']:
                dy_config = {'keywords': search_key, 'count': 30}
            elif platform in ['小红书', 'xhs']:
                xhs_config = {'keywords': search_key, 'count': 20}
    
    print("\n📤 下发插件任务")
    dispatched_tasks = []
    
    if dy_config:
        keywords = parse_keywords(dy_config.get('keywords', ''))
        print(f"  抖音关键词: {keywords}")
        dy_task_id = dispatch_plugin_task(
            skill="meiyali-plugin-dy",
            action="dy.search",
            payload={
                "keywords": keywords,
                "count": dy_config.get('count', 30),
                "sorts": ["default", "time_descending"],
                "timeFilter": "7"
            }
        )
        if dy_task_id:
            dispatched_tasks.append({'platform': 'douyin', 'task_id': dy_task_id})
            print(f"  ✅ 抖音任务已下发: {dy_task_id[:10]}...")
    
    if xhs_config:
        keywords = parse_keywords(xhs_config.get('keywords', ''))
        print(f"  小红书关键词: {keywords}")
        xhs_task_id = dispatch_plugin_task(
            skill="meiyali-plugin-xhs",
            action="xhs.search",
            payload={
                "keywords": keywords,
                "count": xhs_config.get('count', 20),
                "sorts": ["default", "time_descending"],
                "timeFilter": "7"
            }
        )
        if xhs_task_id:
            dispatched_tasks.append({'platform': 'xiaohongshu', 'task_id': xhs_task_id})
            print(f"  ✅ 小红书任务已下发: {xhs_task_id[:10]}...")
    
    if not dispatched_tasks:
        return {"code": 7, "msg": "没有可执行的任务"}
    
    print("\n" + "=" * 70)
    print("✅ 任务下发完成")
    print("=" * 70)
    print(f"  下发任务数: {len(dispatched_tasks)}")
    print(f"  任务状态: 等待插件执行（状态 0 → 1 → 2）")
    print(f"  下一步: 等待定时任务处理（运行 --mode process）")
    
    return {
        "code": 0,
        "data": {
            "project_id": project_id,
            "scene_id": scene_id,
            "dispatched_tasks": dispatched_tasks,
            "task_count": len(dispatched_tasks),
            "mode": "dispatch_only"
        },
        "msg": "成功"
    }

def execute_process_only(project_id: int = None) -> dict:
    """Part B: 仅处理已完成任务（查询状态为 2 的任务并处理）
    
    适用于分离模式的结果处理阶段。
    任务状态流转：2（执行成功）→ 3（任务结束）
    
    Returns:
        处理结果统计
    """
    print("=" * 70)
    print("🚀 舆情监控 - 任务处理模式（Part B）")
    print("=" * 70)
    
    print(f"\n📋 查询状态为 2（执行成功）的任务...")
    tasks = get_completed_tasks(project_id)
    
    if not tasks:
        print("✅ 没有待处理的任务")
        return {
            "code": 0,
            "data": {
                "total_tasks": 0,
                "processed_tasks": 0,
                "mode": "process_only"
            },
            "msg": "没有待处理任务"
        }
    
    print(f"✅ 发现 {len(tasks)} 个待处理任务\n")
    
    all_stats = {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "warning": 0, "uploaded": 0, "failed": 0}
    processed_task_ids = []
    
    for idx, task in enumerate(tasks):
        task_id = task.get('task_id')
        task_project_id = task.get('work_project_id', project_id)
        task_scene_id = task.get('scene_id')
        
        print(f"\n[{idx+1}/{len(tasks)}] 处理任务: {task_id[:10]}...")
        
        # 获取项目和场景配置
        if not task_project_id or not task_scene_id:
            print(f"  ⚠️  任务缺少项目或场景 ID，跳过")
            continue
        
        task_data = poll_task_result(task_id)
        
        if task_data:
            # 获取场景配置以解析舆情标准
            scene = get_scene_detail(task_scene_id)
            if not scene:
                print(f"  ⚠️  场景不存在，跳过")
                continue
            
            criteria = OpinionCriteriaParser(scene.get('description', ''))
            
            stats = process_task_items(task_data, task_project_id, task_scene_id, criteria)
            
            for key in all_stats:
                all_stats[key] += stats.get(key, 0)
            
            if stats['total'] > 0 and stats['failed'] == 0 and stats['total'] == stats['uploaded']:
                processed_task_ids.append(task_id)
    
    # 批量标记任务完成
    if processed_task_ids:
        print(f"\n🏁 标记 {len(processed_task_ids)} 个任务为完成状态...")
        finish_tasks(processed_task_ids)
    
    print("\n" + "=" * 70)
    print("📊 任务处理完成")
    print("=" * 70)
    print(f"  处理任务数: {len(tasks)}")
    print(f"  成功任务数: {len(processed_task_ids)}")
    print(f"  总数据:    {all_stats['total']} 条")
    print(f"  正向:     {all_stats['positive']} 条")
    print(f"  中性:     {all_stats['neutral']} 条")
    print(f"  负向:     {all_stats['negative']} 条")
    print(f"  预警:     {all_stats['warning']} 条")
    print(f"  上传成功:  {all_stats['uploaded']} 条")
    print(f"  上传失败:  {all_stats['failed']} 条")
    
    return {
        "code": 0,
        "data": {
            "total_tasks": len(tasks),
            "processed_tasks": len(processed_task_ids),
            "summary": all_stats,
            "finished_task_ids": processed_task_ids,
            "mode": "process_only"
        },
        "msg": "成功"
    }

def main():
    """主函数 - 支持多种执行模式"""
    parser = argparse.ArgumentParser(description='舆情监控统一工作流脚本')
    parser.add_argument('project_id', type=int, nargs='?', help='项目 ID')
    parser.add_argument('scene_id', type=int, nargs='?', help='场景 ID')
    parser.add_argument('--mode', '-m', choices=['full', 'dispatch', 'process'], 
                       default='full', help='执行模式: full(完整流程), dispatch(仅下发), process(仅处理)')
    
    args = parser.parse_args()
    
    if args.mode == 'full':
        # 完整流程（默认）
        result = execute_full_workflow(args.project_id, args.scene_id)
    elif args.mode == 'dispatch':
        # Part A: 仅下发任务
        result = execute_dispatch_only(args.project_id, args.scene_id)
    elif args.mode == 'process':
        # Part B: 仅处理任务
        result = execute_process_only(args.project_id)
    
    print(f"\n{json.dumps(result, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    main()
