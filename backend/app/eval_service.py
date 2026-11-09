from .db import connect, loads
from .pipeline import chat
from .schemas import SecurityContext


async def run_eval() -> list[dict]:
    with connect() as conn:
        cases = conn.execute("SELECT * FROM eval_cases ORDER BY id").fetchall()
    results = []
    for row in cases:
        case = dict(row)
        groups = loads(case["user_groups"], ["all"])
        ctx = SecurityContext(
            user_id=f"eval_{case['id']}", tenant_id="tenant_demo", role="eval",
            department="engineering", groups=groups,
        )
        response = await chat(case["question"], [], ctx)
        expected_contains = case.get("expected_contains")
        expected_doc = case.get("expected_document_id")
        perm_denied = bool(case.get("expected_permission_denied"))

        route_ok = response.route == case["expected_route"]
        text_ok = True if not expected_contains else expected_contains in response.answer
        doc_ok = True if not expected_doc else any(c.document_id == expected_doc for c in response.citations)
        permission_ok = True
        if perm_denied:
            permission_ok = response.insufficient_evidence and not response.citations

        passed = route_ok and text_ok and doc_ok and permission_ok
        results.append({
            "case_id": case["id"], "passed": passed, "question": case["question"],
            "route": response.route, "answer": response.answer,
            "details": {"route_ok": route_ok, "text_ok": text_ok, "doc_ok": doc_ok, "permission_ok": permission_ok},
        })
    return results
