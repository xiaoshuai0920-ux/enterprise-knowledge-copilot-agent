import hashlib
import json
from datetime import datetime, timezone

from .db import connect, init_db, dumps


NOW = datetime.now(timezone.utc).isoformat()
TENANT = "tenant_demo"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


DOCUMENTS = [
    {
        "id": "travel-policy-v1",
        "title": "差旅管理制度 V1",
        "source_type": "official_policy",
        "source_uri": "mock://hr/travel-policy-v1",
        "department": "finance",
        "category": "travel",
        "version": "V1",
        "status": "inactive",
        "effective_from": "2024-01-01",
        "effective_to": "2024-12-31",
        "acl_groups": ["all"],
        "chunks": [
            ("4.2 住宿标准", "P6 员工在北京、上海、广州、深圳等一线城市出差，住宿标准为 500 元/晚。超标需要部门负责人审批。"),
        ],
    },
    {
        "id": "travel-policy-v2",
        "title": "差旅管理制度 V2",
        "source_type": "official_policy",
        "source_uri": "mock://hr/travel-policy-v2",
        "department": "finance",
        "category": "travel",
        "version": "V2",
        "status": "inactive",
        "effective_from": "2025-01-01",
        "effective_to": "2025-12-31",
        "acl_groups": ["all"],
        "chunks": [
            ("4.2 住宿标准", "P6 员工在一线城市出差，住宿标准调整为 550 元/晚。超标需要部门负责人审批。"),
        ],
    },
    {
        "id": "travel-policy-v3",
        "title": "2026 差旅管理制度 V3",
        "source_type": "official_policy",
        "source_uri": "mock://hr/travel-policy-v3",
        "department": "finance",
        "category": "travel",
        "version": "V3",
        "status": "active",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "acl_groups": ["all"],
        "chunks": [
            ("4.2 住宿标准", "P6 员工在北京、上海、广州、深圳等一线城市出差，住宿标准为 600 元/晚；P7 员工标准为 800 元/晚。"),
            ("4.3 超标处理", "住宿费用超过对应职级标准时，员工必须补充超标说明，并经过部门负责人和财务负责人双审批后方可报销。"),
            ("3.1 交通标准", "高铁二等座、飞机经济舱属于普通差旅交通标准。特殊升级需要事前审批。"),
        ],
    },
    {
        "id": "engineering-retry-standard-v4",
        "title": "服务调用重试与幂等规范 V4",
        "source_type": "engineering_standard",
        "source_uri": "mock://wiki/retry-standard-v4",
        "department": "engineering",
        "category": "engineering",
        "version": "V4",
        "status": "active",
        "effective_from": "2026-03-01",
        "effective_to": None,
        "acl_groups": ["engineering", "sre"],
        "chunks": [
            ("2.1 GET 请求", "幂等 GET 查询接口允许自动重试，默认最多 3 次，并使用指数退避与随机抖动。"),
            ("2.2 副作用接口", "退款、创建订单、发券等副作用接口禁止无条件重试。必须携带 idempotency_key，并在超时后先查询业务状态再决定是否重试。"),
            ("2.3 熔断", "连续失败率超过阈值时应触发熔断，避免下游雪崩。恢复阶段采用半开探测。"),
        ],
    },
    {
        "id": "payment-error-catalog-v2",
        "title": "支付系统错误码手册 V2",
        "source_type": "runbook",
        "source_uri": "mock://runbook/payment-errors-v2",
        "department": "engineering",
        "category": "runbook",
        "version": "V2",
        "status": "active",
        "effective_from": "2026-02-01",
        "effective_to": None,
        "acl_groups": ["engineering", "sre"],
        "chunks": [
            ("ERR_PAYMENT_5008", "错误码 ERR_PAYMENT_5008 表示支付网关请求超时。先检查 payment-gateway P99、上游网络和重试策略，不允许直接重复扣款。"),
            ("ERR_PAYMENT_4012", "错误码 ERR_PAYMENT_4012 表示商户签名校验失败，应检查 merchant_id、签名密钥版本与时钟偏差。"),
        ],
    },
    {
        "id": "oms-v3-deploy-guide",
        "title": "OMS-V3 海外部署指南",
        "source_type": "product_doc",
        "source_uri": "mock://product/oms-v3-deploy",
        "department": "product",
        "category": "deployment",
        "version": "3.4",
        "status": "active",
        "effective_from": "2026-05-10",
        "effective_to": None,
        "acl_groups": ["engineering", "product", "sre"],
        "chunks": [
            ("5.1 海外节点", "OMS-V3 海外部署必须使用区域化对象存储和当地数据库只读副本，禁止将客户敏感字段跨区域复制。"),
            ("5.2 回源策略", "静态资源优先使用区域 CDN；API 通过就近网关回源，并配置 3 秒连接超时。"),
        ],
    },
    {
        "id": "executive-compensation-2026",
        "title": "2026 高管薪酬与奖金制度",
        "source_type": "hr_confidential",
        "source_uri": "mock://hr/confidential/executive-compensation",
        "department": "hr",
        "category": "compensation",
        "version": "2026",
        "status": "active",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "acl_groups": ["hr-admin", "executive"],
        "chunks": [
            ("奖金结构", "高管年度奖金由公司经营系数、组织绩效和个人绩效三部分组成，具体比例仅对 HR 管理员及高管开放。"),
        ],
    },
    {
        "id": "phoenix-project-overview",
        "title": "Phoenix 项目概览",
        "source_type": "project_doc",
        "source_uri": "mock://projects/phoenix/overview",
        "department": "engineering",
        "category": "project",
        "version": "1.6",
        "status": "active",
        "effective_from": "2026-06-01",
        "effective_to": None,
        "acl_groups": ["engineering", "product"],
        "chunks": [
            ("项目组织", "Phoenix 项目的技术负责人是张三，产品负责人是赵六。技术架构采用 FastAPI、React 和 PostgreSQL。"),
        ],
    },
    {
        "id": "agent-platform-architecture",
        "title": "Enterprise Agent Platform 架构说明",
        "source_type": "architecture_doc",
        "source_uri": "mock://architecture/agent-platform",
        "department": "engineering",
        "category": "architecture",
        "version": "2.1",
        "status": "active",
        "effective_from": "2026-07-01",
        "effective_to": None,
        "acl_groups": ["engineering", "sre"],
        "chunks": [
            ("状态存储", "Redis 只保存短期工作状态、缓存和限流数据；PostgreSQL 保存审批、Agent Run、审计等长期业务事实。"),
            ("长任务", "长时间 Agent 任务与 SSE 连接解耦。API 只创建 task_id，Worker 独立执行，事件持久化后由 SSE 订阅。"),
        ],
    },
]

HR_RELATIONS = [
    ("张三", "李四", "高级研发工程师", "engineering"),
    ("李四", "王五", "研发经理", "engineering"),
    ("王五", None, "研发 VP", "engineering"),
    ("赵六", "孙七", "产品经理", "product"),
]

EVAL_CASES = [
    {
        "id": "travel-current-version",
        "question": "P6 去上海出差住宿标准是多少？",
        "user_groups": ["all", "engineering"],
        "expected_route": "knowledge",
        "expected_contains": "600",
        "expected_document_id": "travel-policy-v3",
        "expected_permission_denied": 0,
    },
    {
        "id": "precise-error-code",
        "question": "ERR_PAYMENT_5008 是什么意思？",
        "user_groups": ["all", "engineering"],
        "expected_route": "knowledge",
        "expected_contains": "支付网关请求超时",
        "expected_document_id": "payment-error-catalog-v2",
        "expected_permission_denied": 0,
    },
    {
        "id": "acl-deny-compensation",
        "question": "公司高管奖金是怎么计算的？",
        "user_groups": ["all", "engineering"],
        "expected_route": "knowledge",
        "expected_contains": None,
        "expected_document_id": None,
        "expected_permission_denied": 1,
    },
    {
        "id": "acl-allow-compensation",
        "question": "公司高管奖金是怎么计算的？",
        "user_groups": ["all", "hr-admin"],
        "expected_route": "knowledge",
        "expected_contains": "经营系数",
        "expected_document_id": "executive-compensation-2026",
        "expected_permission_denied": 0,
    },
    {
        "id": "multi-hop-project-manager",
        "question": "Phoenix 项目技术负责人的上级的上级是谁？",
        "user_groups": ["all", "engineering"],
        "expected_route": "multi_hop",
        "expected_contains": "王五",
        "expected_document_id": "phoenix-project-overview",
        "expected_permission_denied": 0,
    },
]


def seed_database(reset: bool = True) -> None:
    init_db()
    with connect() as conn:
        if reset:
            conn.execute("DELETE FROM traces")
            conn.execute("DELETE FROM bad_cases")
            conn.execute("DELETE FROM eval_cases")
            conn.execute("DELETE FROM hr_relations")
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM documents")

        for doc in DOCUMENTS:
            full_content = "\n".join(content for _, content in doc["chunks"])
            conn.execute(
                """
                INSERT INTO documents(id,tenant_id,title,source_type,source_uri,department,category,version,status,effective_from,effective_to,acl_groups,content_hash,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    doc["id"], TENANT, doc["title"], doc["source_type"], doc["source_uri"], doc["department"], doc["category"], doc["version"], doc["status"], doc["effective_from"], doc["effective_to"], dumps(doc["acl_groups"]), _hash(full_content), NOW,
                ),
            )
            for idx, (section, content) in enumerate(doc["chunks"]):
                chunk_id = f"{doc['id']}-c{idx+1}"
                metadata = {
                    "department": doc["department"],
                    "category": doc["category"],
                    "version": doc["version"],
                    "status": doc["status"],
                    "source_type": doc["source_type"],
                }
                conn.execute(
                    "INSERT INTO chunks(id,document_id,tenant_id,title,section,parent_chunk_id,content,chunk_index,metadata) VALUES(?,?,?,?,?,?,?,?,?)",
                    (chunk_id, doc["id"], TENANT, doc["title"], section, None, content, idx, dumps(metadata)),
                )

        for employee, manager, title, department in HR_RELATIONS:
            conn.execute(
                "INSERT INTO hr_relations(tenant_id,employee_name,manager_name,title,department) VALUES(?,?,?,?,?)",
                (TENANT, employee, manager, title, department),
            )

        for case in EVAL_CASES:
            conn.execute(
                """
                INSERT INTO eval_cases(id,question,user_groups,expected_route,expected_contains,expected_document_id,expected_permission_denied)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    case["id"], case["question"], dumps(case["user_groups"]), case["expected_route"], case["expected_contains"], case["expected_document_id"], case["expected_permission_denied"],
                ),
            )


if __name__ == "__main__":
    seed_database(reset=True)
    print(f"Seed complete: {len(DOCUMENTS)} documents, {len(EVAL_CASES)} eval cases")
