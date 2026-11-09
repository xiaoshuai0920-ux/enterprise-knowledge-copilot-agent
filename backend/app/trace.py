import json
import time
from contextlib import contextmanager
from typing import Any, Iterator

from .db import connect, dumps, loads


def save_trace(trace_id: str, node: str, status: str, latency_ms: int, input_data: Any = None, output_data: Any = None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO traces(trace_id,node,status,latency_ms,input_json,output_json) VALUES(?,?,?,?,?,?)",
            (trace_id, node, status, latency_ms, dumps(input_data), dumps(output_data)),
        )


@contextmanager
def trace_step(trace_id: str, node: str, input_data: Any = None) -> Iterator[dict[str, Any]]:
    started = time.perf_counter()
    holder: dict[str, Any] = {}
    try:
        yield holder
        save_trace(
            trace_id,
            node,
            "success",
            int((time.perf_counter() - started) * 1000),
            input_data,
            holder.get("output"),
        )
    except Exception as exc:
        save_trace(
            trace_id,
            node,
            "failed",
            int((time.perf_counter() - started) * 1000),
            input_data,
            {"error": str(exc)},
        )
        raise


def get_trace(trace_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT node,status,latency_ms,input_json,output_json FROM traces WHERE trace_id=? ORDER BY id",
            (trace_id,),
        ).fetchall()
    return [
        {
            "node": r["node"],
            "status": r["status"],
            "latency_ms": r["latency_ms"],
            "input": loads(r["input_json"], None),
            "output": loads(r["output_json"], None),
        }
        for r in rows
    ]
