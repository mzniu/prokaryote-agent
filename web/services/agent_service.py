"""
Agent 求解服务 - AI意图解析 + 技能路由 + 执行聚合

核心流程:
1. AI解析用户问题 → 提取意图、领域、技能候选、参数
2. 根据解析结果路由到单技能或技能链
3. 通过 SkillContext 执行（支持知识库、技能互调用）
4. 聚合结果 + 知识引用 + 调用轨迹
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 交互记录目录
INTERACTIONS_DIR = PROJECT_ROOT / "prokaryote_agent" / "log" / "interactions"


def _ensure_dirs():
    INTERACTIONS_DIR.mkdir(parents=True, exist_ok=True)


# ==================== AI 意图解析 ====================

def parse_intent(
    query: str,
    available_skills: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    使用 AI 解析用户问题的意图

    Returns:
        {
            "domain": "legal",
            "task_type": "analysis",
            "skill_candidates": [
                {"skill_id": "...", "relevance": "high", "reason": "..."}
            ],
            "extracted_params": {"query": "...", ...},
            "needs_chain": false,
            "chain_plan": []
        }
    """
    try:
        from prokaryote_agent.ai_adapter import AIAdapter
        adapter = AIAdapter()
        if not adapter.config.api_key:
            return _fallback_parse(query, available_skills)
    except Exception:
        return _fallback_parse(query, available_skills)

    # 构建技能清单
    skill_list_str = "\n".join(
        f"- {s['skill_id']}: {s['name']} ({s['domain']}) "
        f"能力: {', '.join(s.get('capabilities', [])[:3])}"
        for s in available_skills
    )

    prompt = f"""你是一个AI Agent的任务路由器。用户提出了一个问题，请分析用户意图并选择合适的技能。

用户问题: {query}

当前可用技能:
{skill_list_str}

请分析:
1. 这个问题属于什么领域(domain)?
2. 需要什么类型的任务(research/drafting/analysis/code_review/generic)?
3. 应该使用哪些技能? 按相关度排序。
4. 从问题中提取技能需要的参数。
5. 是否需要多个技能链式协作? 如果是，给出执行顺序。

以严格JSON格式返回:
{{
    "domain": "领域名称",
    "task_type": "任务类型",
    "skill_candidates": [
        {{"skill_id": "技能ID", "relevance": "high/medium/low", "reason": "选择原因"}}
    ],
    "extracted_params": {{"key": "value"}},
    "needs_chain": false,
    "chain_plan": [
        {{"skill_id": "...", "params": {{}}, "purpose": "这一步做什么"}}
    ]
}}"""

    try:
        result = adapter._call_ai(prompt)
        if result.get("success") and result.get("content"):
            content = result["content"].strip()
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
            if json_match:
                content = json_match.group(1).strip()
            parsed = json.loads(content)
            logger.info(
                "AI意图解析: domain=%s, type=%s, skills=%s, chain=%s",
                parsed.get("domain"), parsed.get("task_type"),
                [c["skill_id"] for c in parsed.get("skill_candidates", [])],
                parsed.get("needs_chain", False)
            )
            return parsed
    except json.JSONDecodeError as e:
        logger.warning("AI意图解析JSON格式错误: %s", e)
    except Exception as e:
        logger.warning("AI意图解析失败: %s", e)

    return _fallback_parse(query, available_skills)


def _fallback_parse(
    query: str,
    available_skills: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """关键词回退解析"""
    query_lower = query.lower()
    best_skill = None
    best_score = 0

    for s in available_skills:
        score = 0
        text = f"{s['name']} {s.get('description', '')}".lower()
        for word in query_lower:
            if len(word) > 1 and word in text:
                score += 1
        for cap in s.get("capabilities", []):
            if cap in query:
                score += 3
        if score > best_score:
            best_score = score
            best_skill = s

    candidates = []
    domain = "general"
    if best_skill:
        candidates.append({
            "skill_id": best_skill["skill_id"],
            "relevance": "medium",
            "reason": "关键词匹配"
        })
        domain = best_skill.get("domain", "general")

    return {
        "domain": domain,
        "task_type": "generic",
        "skill_candidates": candidates,
        "extracted_params": {"query": query},
        "needs_chain": False,
        "chain_plan": []
    }


# ==================== Agent 求解 ====================

def solve(
    query: str,
    mode: str = "auto",
    skill_id: Optional[str] = None,
    use_knowledge_first: bool = True,
    allow_web: bool = False,
) -> Dict[str, Any]:
    """
    Agent 求解入口

    Args:
        query: 用户问题
        mode: auto / manual
        skill_id: 手动模式下指定的技能ID
        use_knowledge_first: 是否优先使用知识库
        allow_web: 是否允许联网搜索

    Returns:
        包含 output, skills_used, knowledge_refs, trace, interaction_id
    """
    from prokaryote_agent.skills.skill_base import SkillLibrary

    interaction_id = str(uuid.uuid4())[:12]
    start_time = time.time()
    library = SkillLibrary()
    trace = []

    # 获取可用技能列表
    all_skills = library.list_skills()
    available = [
        {
            "skill_id": m.skill_id,
            "name": m.name,
            "domain": m.domain,
            "description": m.description,
            "capabilities": _get_capabilities(library, m.skill_id),
        }
        for m in all_skills
    ]

    # 意图解析
    if mode == "manual" and skill_id:
        intent = {
            "domain": "general",
            "task_type": "generic",
            "skill_candidates": [
                {"skill_id": skill_id, "relevance": "high",
                 "reason": "用户手动指定"}
            ],
            "extracted_params": {"query": query},
            "needs_chain": False,
            "chain_plan": [],
        }
    else:
        intent = parse_intent(query, available)

    candidates = intent.get("skill_candidates", [])
    extracted_params = intent.get("extracted_params", {})
    domain = intent.get("domain", "general")

    if not candidates:
        return _build_response(
            interaction_id=interaction_id,
            query=query,
            intent=intent,
            output="抱歉，暂无适合处理此问题的技能。",
            skills_used=[],
            knowledge_refs=[],
            trace=[],
            duration=time.time() - start_time,
            success=False,
        )

    # 执行技能
    skills_used = []
    all_outputs = []
    all_knowledge_refs = []

    if intent.get("needs_chain") and intent.get("chain_plan"):
        # 链式执行
        chain_context = {}
        for step in intent["chain_plan"]:
            sid = step.get("skill_id", "")
            params = step.get("params", {})
            params.update(extracted_params)
            if chain_context:
                params["_prev_results"] = chain_context

            step_result = _execute_one_skill(
                library, sid, domain, params,
                use_knowledge_first, allow_web
            )
            trace.append(step_result["trace_entry"])
            skills_used.append(sid)
            all_knowledge_refs.extend(step_result.get("knowledge_refs", []))

            if step_result["success"]:
                chain_context[sid] = step_result.get("result", {})
                all_outputs.append(step_result.get("output_text", ""))
            else:
                all_outputs.append(
                    f"[{sid}] 执行失败: {step_result.get('error', '')}"
                )
                if step.get("required", True):
                    break

        final_output = "\n\n---\n\n".join(all_outputs)
    else:
        # 单技能执行（使用最相关的）
        sid = candidates[0]["skill_id"]
        step_result = _execute_one_skill(
            library, sid, domain, extracted_params,
            use_knowledge_first, allow_web
        )
        trace.append(step_result["trace_entry"])
        skills_used.append(sid)
        all_knowledge_refs = step_result.get("knowledge_refs", [])
        final_output = step_result.get("output_text", "")
        if not step_result["success"]:
            final_output = f"执行失败: {step_result.get('error', '未知错误')}"

    result = _build_response(
        interaction_id=interaction_id,
        query=query,
        intent=intent,
        output=final_output,
        skills_used=skills_used,
        knowledge_refs=all_knowledge_refs,
        trace=trace,
        duration=time.time() - start_time,
        success=True,
    )

    # 持久化交互记录
    _save_interaction(result)

    return result


def _execute_one_skill(
    library, skill_id: str, domain: str,
    params: Dict[str, Any],
    use_knowledge_first: bool,
    allow_web: bool,
) -> Dict[str, Any]:
    """执行单个技能并收集结果"""
    from prokaryote_agent.skills.skill_context import SkillContext

    skill = library.get_skill(skill_id)
    if not skill:
        return {
            "success": False,
            "error": f"技能不存在: {skill_id}",
            "trace_entry": {
                "skill": skill_id, "input": params,
                "output_summary": "技能不存在",
                "duration_ms": 0, "success": False,
            },
            "knowledge_refs": [],
            "output_text": "",
        }

    ctx = SkillContext(
        skill_id=skill_id,
        skill_library=library,
        domain=domain,
    )

    # 知识库优先：先搜索知识库补充上下文
    knowledge_refs = []
    if use_knowledge_first:
        query_text = params.get("query", "")
        if query_text:
            try:
                kb_results = ctx.search_knowledge(query_text, limit=3)
                knowledge_refs = [
                    {
                        "title": r.get("title", ""),
                        "snippet": r.get("content", r.get("snippet", ""))[:200],
                        "source": "knowledge_base",
                    }
                    for r in kb_results
                ]
                if kb_results:
                    params["_knowledge_context"] = kb_results
            except Exception as e:
                logger.warning("知识库搜索失败: %s", e)

    # 执行 – 移除与 execute() 签名冲突的保留字段
    reserved_keys = ('context', 'self')
    exec_params = {k: v for k, v in params.items() if k not in reserved_keys}

    t0 = time.time()
    try:
        result = skill.execute(context=ctx, **exec_params)
        duration_ms = int((time.time() - t0) * 1000)
        success = result.get("success", False)
        skill_result = result.get("result", {})

        # 提取输出文本
        output_text = _format_skill_output(skill_result)

        # 收集 context 产出物中的知识引用
        for out in ctx._outputs:
            knowledge_refs.append({
                "title": out.get("title", ""),
                "snippet": out.get("content", "")[:200],
                "source": f"skill_output:{skill_id}",
            })

        return {
            "success": success,
            "result": skill_result,
            "output_text": output_text,
            "error": result.get("error", ""),
            "trace_entry": {
                "skill": skill_id,
                "input": {k: str(v)[:100] for k, v in params.items()
                          if not k.startswith("_")},
                "output_summary": output_text[:200],
                "duration_ms": duration_ms,
                "success": success,
                "knowledge_queries": ctx._knowledge_queries,
                "knowledge_stores": ctx._knowledge_stores,
                "called_skills": ctx._called_skills,
            },
            "knowledge_refs": knowledge_refs,
        }
    except Exception as e:
        duration_ms = int((time.time() - t0) * 1000)
        logger.error("技能执行异常 %s: %s", skill_id, e)
        return {
            "success": False,
            "error": str(e),
            "output_text": f"执行异常: {e}",
            "trace_entry": {
                "skill": skill_id,
                "input": {k: str(v)[:100] for k, v in params.items()
                          if not k.startswith("_")},
                "output_summary": f"异常: {e}",
                "duration_ms": duration_ms,
                "success": False,
            },
            "knowledge_refs": knowledge_refs,
        }


def _format_skill_output(result: Any) -> str:
    """将技能输出格式化为可读文本"""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        parts = []
        # 常见输出字段
        for key in ("content", "analysis", "output", "summary",
                    "case_summary", "results", "issues"):
            val = result.get(key)
            if val:
                if isinstance(val, str):
                    parts.append(val)
                elif isinstance(val, list):
                    for item in val[:5]:
                        if isinstance(item, dict):
                            title = item.get("title", "")
                            content = item.get("content", item.get(
                                "snippet", ""))
                            parts.append(f"**{title}**\n{content}")
                        else:
                            parts.append(str(item))
                elif isinstance(val, dict):
                    parts.append(json.dumps(val, ensure_ascii=False,
                                            indent=2))
        if parts:
            return "\n\n".join(parts)
        return json.dumps(result, ensure_ascii=False, indent=2)
    return str(result)


def _get_capabilities(library, skill_id: str) -> List[str]:
    """安全获取技能能力列表"""
    try:
        skill = library.get_skill(skill_id)
        if skill:
            return skill.get_capabilities()
    except Exception:
        pass
    return []


def _build_response(
    interaction_id: str,
    query: str,
    intent: Dict,
    output: str,
    skills_used: List[str],
    knowledge_refs: List[Dict],
    trace: List[Dict],
    duration: float,
    success: bool,
) -> Dict[str, Any]:
    return {
        "interaction_id": interaction_id,
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "intent": intent,
        "output": output,
        "skills_used": skills_used,
        "knowledge_refs": knowledge_refs,
        "trace": trace,
        "duration_ms": int(duration * 1000),
        "success": success,
    }


# ==================== 交互记录持久化 ====================

def _save_interaction(record: Dict[str, Any]):
    """保存交互记录到 JSONL 文件"""
    _ensure_dirs()
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = INTERACTIONS_DIR / f"{date_str}.jsonl"
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error("保存交互记录失败: %s", e)


def get_interactions(limit: int = 20) -> List[Dict[str, Any]]:
    """获取最近的交互记录"""
    _ensure_dirs()
    records = []
    # 按日期倒序读取
    files = sorted(INTERACTIONS_DIR.glob("*.jsonl"), reverse=True)
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception:
            continue
        if len(records) >= limit:
            break
    # 按时间倒序
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records[:limit]


def get_interaction(interaction_id: str) -> Optional[Dict[str, Any]]:
    """按ID获取交互记录"""
    _ensure_dirs()
    files = sorted(INTERACTIONS_DIR.glob("*.jsonl"), reverse=True)
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record = json.loads(line)
                        if record.get("interaction_id") == interaction_id:
                            return record
        except Exception:
            continue
    return None


def get_available_skills_info() -> List[Dict[str, Any]]:
    """获取可用技能信息（供前端展示）"""
    from prokaryote_agent.skills.skill_base import SkillLibrary
    library = SkillLibrary()
    result = []
    for m in library.list_skills():
        caps = _get_capabilities(library, m.skill_id)
        result.append({
            "skill_id": m.skill_id,
            "name": m.name,
            "domain": m.domain,
            "tier": m.tier,
            "level": m.level,
            "description": m.description,
            "capabilities": caps,
        })
    return result
