import json
import re
import uuid
from typing import Any

from .config import settings
from .db import connect, loads
from .llm import llm
from .retrieval import (
    load_accessible_chunks, bm25_search, vector_search,
    reciprocal_rank_fusion, rerank, build_context,
)
from .schemas import ChatMessage, ChatResponse, Citation, SecurityContext
from .trace import trace_step, get_trace


def route_query(question: str) -> str:
    q = question.strip().lower()
    if q in {"你好", "您好", "hello", "hi", "嗨"} or q.startswith("你好，"):
        return "chat"
    if "phoenix" in q and ("上级的上级" in q or "上上级" in q):
        return "multi_hop"
    if re.search(r"(张三|李四|王五).*(直属上级|直接上级)", q):
        return "hr_tool"
    return "knowledge"


def mock_rewrite(question: str, history: list[ChatMessage]) -> dict[str, Any]:
    standalone = question.strip()
    if history and any(x in question for x in ["这个", "上面", "超了", "P7呢", "P7 呢", "那"]):
        recent = " ".join(m.content for m in history[-4:] if m.role == "user")
        if "住宿" in recent or "出差" in recent:
            level = "P7" if "P7" in question or "P7" in recent else ("P6" if "P6" in recent else "")
            city = "上海" if "上海" in recent else "一线城市"
            if "超" in question:
                standalone = f"{level} 员工在{city}出差住宿费用超过公司标准后如何处理和审批？"
            else:
                standalone = f"{level} 员工在{city}出差住宿标准是多少？"
    keywords = re.findall(r"[A-Za-z][A-Za-z0-9_\-.]+|P\d+|[\u4e00-\u9fff]{2,}", standalone)
    filters: dict[str, str] = {}
    if any(w in standalone for w in ["出差", "住宿", "差旅"]):
        filters["category"] = "travel"
    elif "ERR_" in standalone or "错误码" in standalone:
        filters["category"] = "runbook"
    elif "重试" in standalone or "幂等" in standalone:
        filters["category"] = "engineering"
    elif "高管" in standalone and ("奖金" in standalone or "薪酬" in standalone):
        filters["category"] = "compensation"
    return {"standalone_query": standalone, "keywords": keywords[:12], "filters": filters}


async def rewrite_query(question: str, history: list[ChatMessage]) -> dict[str, Any]:
    if settings.mock_mode:
        return mock_rewrite(question, history)
    history_text = "\n".join(f"{m.role}: {m.content}" for m in history[-6:])
    data = await llm.json(
        "你是企业知识库 Query Rewrite 模块。只输出 JSON。不要回答问题。",
        f"""根据对话历史把当前问题改写为可独立检索的问题，并抽取关键词和 metadata filters。
filters 只允许 category 字段；不确定时返回空对象。

历史：
{history_text or '(无)'}

当前问题：{question}

返回格式：
{{"standalone_query":"...","keywords":["..."],"filters":{{}}}}""",
    )
    return {
        "standalone_query": str(data.get("standalone_query") or question),
        "keywords": list(data.get("keywords") or []),
        "filters": dict(data.get("filters") or {}),
    }


def apply_metadata_filter(docs: list[dict[str, Any]], filters: dict[str, str]) -> list[dict[str, Any]]:
    if not filters:
        return docs
    result = []
    for doc in docs:
        ok = True
        for key, value in filters.items():
            if key == "category" and doc.get("category") != value:
                ok = False
        if ok:
            result.append(doc)
    return result


def _mock_answer(question: str, selected: list[dict[str, Any]]) -> tuple[str, float, bool]:
    if not selected:
        return "当前账号没有可访问的相关知识，或知识库中暂时没有足够依据。", 0.2, True
    combined = "\n".join(d["content"] for d in selected)
    q = question.lower()
    if "p6" in q and ("上海" in q or "一线" in q) and "住宿" in q:
        if "超" in q or "超过" in q:
            return "P6 员工在上海等一线城市的住宿标准为 600 元/晚。超过标准时，需要补充超标说明，并经过部门负责人和财务负责人双审批后方可报销。[1][2]", 0.96, False
        return "根据当前生效的《2026 差旅管理制度 V3》，P6 员工在上海等一线城市出差的住宿标准为 600 元/晚。[1]", 0.98, False
    if "p7" in q and "住宿" in q:
        if "超" in q:
            return "P7 员工在一线城市住宿标准为 800 元/晚；超过标准时需要补充说明，并经过部门负责人和财务负责人双审批。[1][2]", 0.96, False
        return "当前生效制度规定，P7 员工在上海等一线城市出差住宿标准为 800 元/晚。[1]", 0.98, False
    if "err_payment_5008" in q:
        return "ERR_PAYMENT_5008 表示支付网关请求超时。建议先检查 payment-gateway 的 P99、上游网络和重试策略；涉及扣款的副作用操作不能直接重复执行。[1]", 0.98, False
    if "重试" in q or "幂等" in q:
        return "查询类 GET 接口可以在受控策略下自动重试，默认最多 3 次并采用指数退避；退款、创建订单、发券等副作用接口禁止无条件重试，必须使用 idempotency_key，并在超时后先查询业务状态。[1][2]", 0.94, False
    if "oms-v3" in q or "海外部署" in q:
        return "OMS-V3 海外部署要求使用区域化对象存储和当地数据库只读副本，客户敏感字段禁止跨区域复制；静态资源优先走区域 CDN，API 通过就近网关回源。[1][2]", 0.93, False
    if "高管" in q and ("奖金" in q or "薪酬" in q):
        if "经营系数" in combined:
            return "当前可访问制度显示，高管年度奖金由公司经营系数、组织绩效和个人绩效三部分组成。[1]", 0.95, False
        return "当前账号没有可访问的相关知识，或知识库中暂时没有足够依据。", 0.2, True
    first = selected[0]
    return f"根据当前可访问知识，{first['content']} [1]", 0.82, False


async def generate_answer(question: str, context: str, selected: list[dict[str, Any]]) -> tuple[str, float, bool]:
    if settings.mock_mode:
        return _mock_answer(question, selected)
    if not context:
        return "当前账号没有可访问的相关知识，或知识库中暂时没有足够依据。", 0.2, True
    text = await llm.chat(
        """你是企业内部知识助手。只能依据提供的企业知识回答，不得自行补充公司制度。
必须用 [1]、[2] 形式引用证据。证据不足时明确说没有足够依据；如知识冲突，要指出冲突。""",
        f"用户问题：{question}\n\n企业知识：\n{context}",
        temperature=0.1,
    )
    return text, 0.85, False


def _citations(selected: list[dict[str, Any]]) -> list[Citation]:
    return [
        Citation(
            chunk_id=d["id"], document_id=d["document_id"], title=d["title"],
            section=d.get("section"), version=d.get("version"), source_uri=d.get("source_uri"),
            content=d["content"], score=float(d.get("rerank_score", d.get("rrf_score", 0))),
        )
        for d in selected
    ]


def hr_lookup(ctx: SecurityContext, employee: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT employee_name,manager_name,title,department FROM hr_relations WHERE tenant_id=? AND employee_name=?",
            (ctx.tenant_id, employee),
        ).fetchone()
    return dict(row) if row else None


async def run_hr_tool(question: str, ctx: SecurityContext, trace_id: str) -> ChatResponse:
    employee = next((name for name in ["张三", "李四", "王五", "赵六"] if name in question), "")
    with trace_step(trace_id, "hr_tool", {"employee": employee}) as step:
        data = hr_lookup(ctx, employee)
        step["output"] = data
    if not data:
        answer = "没有找到对应员工的组织关系。"
    elif data.get("manager_name"):
        answer = f"{data['employee_name']} 的直属上级是 {data['manager_name']}。"
    else:
        answer = f"{data['employee_name']} 当前没有更高一级直属上级记录。"
    return ChatResponse(trace_id=trace_id, route="hr_tool", answer=answer, trace=get_trace(trace_id), confidence=0.99)


async def run_multi_hop(question: str, ctx: SecurityContext, trace_id: str) -> ChatResponse:
    """RAG 找实体 + HR Tool 连续关系查询。LangGraph 可用时使用真实图；未安装时保留同等 deterministic fallback。"""
    async def execute_steps() -> tuple[str, list[dict[str, Any]]]:
        accessible, _ = load_accessible_chunks(ctx)
        project_docs = [d for d in accessible if d.get("category") == "project"]
        found = bm25_search(question, project_docs, 3)
        if not found:
            return "当前知识不足，无法确定项目技术负责人。", []
        text = found[0]["content"]
        m = re.search(r"技术负责人是([^，。\s]+)", text)
        if not m:
            return "已找到项目文档，但无法稳定提取技术负责人。", found[:1]
        lead = m.group(1)
        first = hr_lookup(ctx, lead)
        second = hr_lookup(ctx, first["manager_name"]) if first and first.get("manager_name") else None
        if not first or not second:
            return "组织关系数据不足，无法完成两跳查询。", found[:1]
        return f"Phoenix 项目的技术负责人是 {lead}；{lead} 的直属上级是 {first['manager_name']}；其上一级是 {second['manager_name']}。所以技术负责人的上级的上级是 {second['manager_name']}。[1]", found[:1]

    with trace_step(trace_id, "multi_hop_agent", {"question": question}) as step:
        try:
            from typing import TypedDict
            from langgraph.graph import StateGraph, END

            class State(TypedDict, total=False):
                answer: str
                docs: list[dict[str, Any]]

            async def node(_: State) -> State:
                answer, docs = await execute_steps()
                return {"answer": answer, "docs": docs}

            graph = StateGraph(State)
            graph.add_node("resolve_project_and_org", node)
            graph.set_entry_point("resolve_project_and_org")
            graph.add_edge("resolve_project_and_org", END)
            result = await graph.compile().ainvoke({})
            answer, docs = result["answer"], result["docs"]
            step["output"] = {"engine": "langgraph", "answer": answer}
        except ImportError:
            answer, docs = await execute_steps()
            step["output"] = {"engine": "fallback", "answer": answer}

    return ChatResponse(
        trace_id=trace_id,
        route="multi_hop",
        answer=answer,
        citations=_citations(docs),
        trace=get_trace(trace_id),
        confidence=0.95 if docs else 0.3,
        insufficient_evidence=not bool(docs),
    )


async def run_knowledge(question: str, history: list[ChatMessage], ctx: SecurityContext, trace_id: str) -> ChatResponse:
    with trace_step(trace_id, "query_rewrite", {"question": question}) as step:
        rewrite = await rewrite_query(question, history)
        step["output"] = rewrite

    with trace_step(trace_id, "acl_filter", {"groups": ctx.groups}) as step:
        accessible, stats = load_accessible_chunks(ctx)
        filtered = apply_metadata_filter(accessible, rewrite.get("filters", {}))
        step["output"] = {**stats, "after_metadata_filter": len(filtered)}

    with trace_step(trace_id, "bm25_retrieve", {"query": rewrite["standalone_query"]}) as step:
        bm25 = bm25_search(rewrite["standalone_query"], filtered, settings.retrieval_top_k)
        step["output"] = [{"chunk_id": d["id"], "score": d["bm25_score"]} for d in bm25]

    with trace_step(trace_id, "vector_retrieve", {"query": rewrite["standalone_query"]}) as step:
        vector = vector_search(rewrite["standalone_query"], filtered, settings.retrieval_top_k)
        step["output"] = [{"chunk_id": d["id"], "score": d["vector_score"]} for d in vector]

    with trace_step(trace_id, "rrf", {"bm25": len(bm25), "vector": len(vector)}) as step:
        fused = reciprocal_rank_fusion([bm25, vector])
        step["output"] = [{"chunk_id": d["id"], "score": d["rrf_score"]} for d in fused[:10]]

    with trace_step(trace_id, "rerank", {"candidates": len(fused)}) as step:
        ranked = rerank(rewrite["standalone_query"], fused, settings.rerank_top_n)
        step["output"] = [{"chunk_id": d["id"], "score": d["rerank_score"]} for d in ranked]

    with trace_step(trace_id, "context_builder", {"candidates": len(ranked)}) as step:
        context, selected = build_context(ranked)
        step["output"] = {"selected": [d["id"] for d in selected], "chars": len(context)}

    with trace_step(trace_id, "answer_generation", {"evidence_count": len(selected)}) as step:
        answer, confidence, insufficient = await generate_answer(rewrite["standalone_query"], context, selected)
        step["output"] = {"answer": answer, "confidence": confidence, "insufficient_evidence": insufficient}

    return ChatResponse(
        trace_id=trace_id,
        route="knowledge",
        answer=answer,
        rewritten_query=rewrite["standalone_query"],
        keywords=rewrite.get("keywords", []),
        citations=[] if insufficient else _citations(selected),
        trace=get_trace(trace_id),
        confidence=confidence,
        insufficient_evidence=insufficient,
    )


async def chat(question: str, history: list[ChatMessage], ctx: SecurityContext) -> ChatResponse:
    trace_id = f"tr_{uuid.uuid4().hex[:16]}"
    with trace_step(trace_id, "query_router", {"question": question}) as step:
        route = route_query(question)
        step["output"] = {"route": route}

    if route == "chat":
        return ChatResponse(
            trace_id=trace_id, route="chat", answer="你好，我是企业知识助手。你可以问我公司制度、研发规范、产品文档、Runbook 等内容。",
            trace=get_trace(trace_id), confidence=1.0,
        )
    if route == "hr_tool":
        return await run_hr_tool(question, ctx, trace_id)
    if route == "multi_hop":
        return await run_multi_hop(question, ctx, trace_id)
    return await run_knowledge(question, history, ctx, trace_id)
