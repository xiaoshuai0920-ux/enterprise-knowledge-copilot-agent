import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from .config import settings


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_uri TEXT,
    department TEXT,
    category TEXT,
    version TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    effective_from TEXT,
    effective_to TEXT,
    acl_groups TEXT NOT NULL DEFAULT '["all"]',
    content_hash TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    title TEXT NOT NULL,
    section TEXT,
    parent_chunk_id TEXT,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hr_relations (
    tenant_id TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    manager_name TEXT,
    title TEXT,
    department TEXT,
    PRIMARY KEY (tenant_id, employee_name)
);

CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL,
    node TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    input_json TEXT,
    output_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bad_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT,
    question TEXT NOT NULL,
    error_type TEXT NOT NULL,
    root_cause TEXT,
    expected_result TEXT,
    fixed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eval_cases (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    user_groups TEXT NOT NULL,
    expected_route TEXT NOT NULL,
    expected_contains TEXT,
    expected_document_id TEXT,
    expected_permission_denied INTEGER NOT NULL DEFAULT 0
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
