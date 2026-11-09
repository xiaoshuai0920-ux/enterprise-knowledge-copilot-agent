from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import connect, init_db, loads, dumps
from .eval_service import run_eval
from .pipeline import chat
from .schemas import BadCaseCreate, ChatRequest, ChatResponse, DocumentOut, SecurityContext
from .security import get_security_context
from .seed import seed_database
from .trace import get_trace


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
    if count == 0:
        seed_database(reset=False)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": settings.mock_mode, "model": settings.deepseek_model}


@app.get("/api/v1/runtime")
def runtime():
    return {
        "mock_mode": settings.mock_mode,
        "llm_provider": "mock" if settings.mock_mode else "deepseek",
        "model": "mock-knowledge-llm" if settings.mock_mode else settings.deepseek_model,
        "retrieval": "BM25 + local hash vector + RRF + deterministic rerank",
        "note": "Real mode uses DeepSeek for Query Rewrite and Answer; retrieval stays deterministic and key-free by default.",
    }


@app.post("/api/v1/chat", response_model=ChatResponse)
async def knowledge_chat(request: ChatRequest, ctx: SecurityContext = Depends(get_security_context)):
    return await chat(request.question, request.history, ctx)


@app.get("/api/v1/documents", response_model=list[DocumentOut])
def documents(ctx: SecurityContext = Depends(get_security_context)):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT d.*, COUNT(c.id) AS chunk_count FROM documents d
            LEFT JOIN chunks c ON c.document_id=d.id
            WHERE d.tenant_id=? GROUP BY d.id ORDER BY d.title,d.version
            """,
            (ctx.tenant_id,),
        ).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        acl = loads(d["acl_groups"], ["all"])
        visible_meta = "all" in acl or bool(set(acl) & set(ctx.groups))
        if not visible_meta:
            continue
        out.append(DocumentOut(
            id=d["id"], title=d["title"], source_type=d["source_type"], department=d["department"],
            category=d["category"], version=d["version"], status=d["status"], effective_from=d["effective_from"],
            effective_to=d["effective_to"], acl_groups=acl, updated_at=d["updated_at"], chunk_count=d["chunk_count"],
        ))
    return out


@app.get("/api/v1/traces/{trace_id}")
def trace_detail(trace_id: str):
    trace = get_trace(trace_id)
    if not trace:
        raise HTTPException(404, "trace not found")
    return trace


@app.get("/api/v1/dashboard")
def dashboard(ctx: SecurityContext = Depends(get_security_context)):
    with connect() as conn:
        docs = conn.execute("SELECT COUNT(*) AS n FROM documents WHERE tenant_id=?", (ctx.tenant_id,)).fetchone()["n"]
        chunks = conn.execute("SELECT COUNT(*) AS n FROM chunks WHERE tenant_id=?", (ctx.tenant_id,)).fetchone()["n"]
        traces = conn.execute("SELECT COUNT(DISTINCT trace_id) AS n FROM traces").fetchone()["n"]
        bad_cases = conn.execute("SELECT COUNT(*) AS n FROM bad_cases WHERE fixed=0").fetchone()["n"]
        versions = conn.execute("SELECT status,COUNT(*) AS n FROM documents WHERE tenant_id=? GROUP BY status", (ctx.tenant_id,)).fetchall()
    return {
        "documents": docs, "chunks": chunks, "traces": traces, "open_bad_cases": bad_cases,
        "versions": {r["status"]: r["n"] for r in versions},
        "pipeline": ["Router", "Rewrite", "ACL", "BM25", "Vector", "RRF", "Rerank", "Context", "Citation"],
    }


@app.post("/api/v1/eval/run")
async def evaluation():
    results = await run_eval()
    return {"total": len(results), "passed": sum(1 for r in results if r["passed"]), "results": results}


@app.get("/api/v1/bad-cases")
def list_bad_cases():
    with connect() as conn:
        rows = conn.execute("SELECT * FROM bad_cases ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/v1/bad-cases")
def create_bad_case(payload: BadCaseCreate):
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO bad_cases(trace_id,question,error_type,root_cause,expected_result) VALUES(?,?,?,?,?)",
            (payload.trace_id, payload.question, payload.error_type, payload.root_cause, payload.expected_result),
        )
    return {"id": cur.lastrowid, "status": "created"}


@app.post("/api/v1/admin/reseed")
def reseed():
    seed_database(reset=True)
    return {"status": "ok"}
