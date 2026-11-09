import hashlib
import math
import re
from collections import Counter, defaultdict
from datetime import date
from typing import Any

from .config import settings
from .db import connect, loads
from .schemas import SecurityContext


TOKEN_RE = re.compile(r"[A-Za-z0-9_\-.]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """轻量 tokenizer：英文保留词/编号，中文按字 + 常见二元片段，避免额外分词依赖。"""
    raw = TOKEN_RE.findall(text.lower())
    tokens: list[str] = []
    chinese_buffer = ""
    for item in raw:
        if re.fullmatch(r"[\u4e00-\u9fff]", item):
            chinese_buffer += item
            tokens.append(item)
        else:
            if len(chinese_buffer) >= 2:
                tokens.extend(chinese_buffer[i:i+2] for i in range(len(chinese_buffer)-1))
            chinese_buffer = ""
            tokens.append(item)
    if len(chinese_buffer) >= 2:
        tokens.extend(chinese_buffer[i:i+2] for i in range(len(chinese_buffer)-1))
    return tokens


def _active_now(doc: dict[str, Any]) -> bool:
    if doc["status"] != "active":
        return False
    today = date.today().isoformat()
    start = doc.get("effective_from")
    end = doc.get("effective_to")
    if start and start > today:
        return False
    if end and end < today:
        return False
    return True


def _acl_allowed(acl_groups: list[str], ctx: SecurityContext) -> bool:
    if "all" in acl_groups:
        return True
    return bool(set(acl_groups) & set(ctx.groups))


def load_accessible_chunks(ctx: SecurityContext) -> tuple[list[dict[str, Any]], dict[str, int]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT c.*, d.source_type, d.source_uri, d.department, d.category, d.version,
                   d.status, d.effective_from, d.effective_to, d.acl_groups, d.updated_at
            FROM chunks c JOIN documents d ON d.id=c.document_id
            WHERE c.tenant_id=?
            """,
            (ctx.tenant_id,),
        ).fetchall()
    accessible: list[dict[str, Any]] = []
    stats = {"total": len(rows), "active": 0, "acl_allowed": 0}
    for row in rows:
        doc = dict(row)
        acl_groups = loads(doc.get("acl_groups"), ["all"])
        doc["acl_groups"] = acl_groups
        doc["metadata"] = loads(doc.get("metadata"), {})
        if not _active_now(doc):
            continue
        stats["active"] += 1
        if not _acl_allowed(acl_groups, ctx):
            continue
        stats["acl_allowed"] += 1
        accessible.append(doc)
    return accessible, stats


def bm25_search(query: str, docs: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    if not docs:
        return []
    q_tokens = tokenize(query)
    tokenized = [tokenize(d["content"] + " " + d["title"] + " " + (d.get("section") or "")) for d in docs]
    n = len(tokenized)
    avgdl = sum(len(t) for t in tokenized) / max(n, 1)
    df: Counter[str] = Counter()
    for ts in tokenized:
        for tok in set(ts):
            df[tok] += 1
    k1, b = 1.5, 0.75
    scored = []
    for doc, ts in zip(docs, tokenized):
        tf = Counter(ts)
        dl = len(ts)
        score = 0.0
        for tok in q_tokens:
            if tf[tok] == 0:
                continue
            idf = math.log(1 + (n - df[tok] + 0.5) / (df[tok] + 0.5))
            numer = tf[tok] * (k1 + 1)
            denom = tf[tok] + k1 * (1 - b + b * dl / max(avgdl, 1))
            score += idf * numer / denom
        if score > 0:
            item = dict(doc)
            item["bm25_score"] = round(score, 6)
            scored.append(item)
    return sorted(scored, key=lambda x: x["bm25_score"], reverse=True)[:top_k]


def _hash_vector(text: str, dim: int = 192) -> list[float]:
    vec = [0.0] * dim
    tokens = tokenize(text)
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v / norm for v in vec]


def vector_search(query: str, docs: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    qv = _hash_vector(query)
    scored = []
    for doc in docs:
        dv = _hash_vector(doc["title"] + " " + (doc.get("section") or "") + " " + doc["content"])
        score = sum(a*b for a, b in zip(qv, dv))
        if score > 0:
            item = dict(doc)
            item["vector_score"] = round(score, 6)
            scored.append(item)
    return sorted(scored, key=lambda x: x["vector_score"], reverse=True)[:top_k]


def reciprocal_rank_fusion(rankings: list[list[dict[str, Any]]], k: int | None = None) -> list[dict[str, Any]]:
    k = k or settings.rrf_k
    scores: defaultdict[str, float] = defaultdict(float)
    merged: dict[str, dict[str, Any]] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            cid = doc["id"]
            scores[cid] += 1 / (k + rank)
            merged.setdefault(cid, dict(doc))
    out = []
    for cid, doc in merged.items():
        item = dict(doc)
        item["rrf_score"] = round(scores[cid], 8)
        out.append(item)
    return sorted(out, key=lambda x: x["rrf_score"], reverse=True)


def metadata_boost(doc: dict[str, Any]) -> float:
    score = 0.0
    if doc.get("source_type") == "official_policy":
        score += 0.12
    if doc.get("status") == "active":
        score += 0.08
    if doc.get("version"):
        score += 0.02
    return score


def rerank(query: str, candidates: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    q = set(tokenize(query))
    rescored = []
    for doc in candidates:
        d = set(tokenize(doc["title"] + " " + (doc.get("section") or "") + " " + doc["content"]))
        overlap = len(q & d) / max(len(q), 1)
        exact_bonus = 0.0
        for term in re.findall(r"[A-Za-z][A-Za-z0-9_\-.]{3,}", query):
            if term.lower() in (doc["title"] + " " + doc["content"]).lower():
                exact_bonus += 0.2
        score = overlap * 0.7 + doc.get("rrf_score", 0) * 8 + metadata_boost(doc) + exact_bonus
        item = dict(doc)
        item["rerank_score"] = round(score, 6)
        rescored.append(item)
    return sorted(rescored, key=lambda x: x["rerank_score"], reverse=True)[:top_n]


def build_context(docs: list[dict[str, Any]], max_chars: int | None = None) -> tuple[str, list[dict[str, Any]]]:
    max_chars = max_chars or settings.max_context_chars
    blocks: list[str] = []
    used = 0
    seen: set[tuple[str, str]] = set()
    selected = []
    for idx, doc in enumerate(docs, start=1):
        key = (doc["document_id"], doc.get("section") or "")
        if key in seen:
            continue
        block = (
            f"[{idx}]\n文档：{doc['title']}\n章节：{doc.get('section') or '-'}\n"
            f"版本：{doc.get('version') or '-'}\n内容：{doc['content']}"
        )
        if used + len(block) > max_chars:
            break
        seen.add(key)
        blocks.append(block)
        selected.append(doc)
        used += len(block)
    return "\n\n---\n\n".join(blocks), selected
