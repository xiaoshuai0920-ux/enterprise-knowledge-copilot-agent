from typing import Any, Literal
from pydantic import BaseModel, Field


class SecurityContext(BaseModel):
    user_id: str
    tenant_id: str
    role: str = "developer"
    department: str = "engineering"
    groups: list[str] = Field(default_factory=lambda: ["all", "engineering"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = Field(default_factory=list)


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    section: str | None = None
    version: str | None = None
    source_uri: str | None = None
    content: str
    score: float = 0


class TraceStep(BaseModel):
    node: str
    status: str
    latency_ms: int
    input: Any = None
    output: Any = None


class ChatResponse(BaseModel):
    trace_id: str
    route: str
    answer: str
    rewritten_query: str | None = None
    keywords: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    trace: list[TraceStep] = Field(default_factory=list)
    confidence: float = 0.0
    insufficient_evidence: bool = False


class DocumentOut(BaseModel):
    id: str
    title: str
    source_type: str
    department: str | None = None
    category: str | None = None
    version: str | None = None
    status: str
    effective_from: str | None = None
    effective_to: str | None = None
    acl_groups: list[str]
    updated_at: str
    chunk_count: int = 0


class BadCaseCreate(BaseModel):
    trace_id: str | None = None
    question: str
    error_type: str
    root_cause: str | None = None
    expected_result: str | None = None


class EvalResult(BaseModel):
    case_id: str
    passed: bool
    question: str
    route: str
    answer: str
    details: dict[str, Any] = Field(default_factory=dict)
