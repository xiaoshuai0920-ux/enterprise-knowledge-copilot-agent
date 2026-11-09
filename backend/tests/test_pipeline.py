import os
os.environ["MOCK_MODE"] = "true"

import pytest

from app.seed import seed_database
from app.pipeline import chat
from app.schemas import SecurityContext, ChatMessage


@pytest.fixture(autouse=True)
def seed():
    seed_database(reset=True)


@pytest.mark.asyncio
async def test_current_policy_version():
    ctx = SecurityContext(user_id="u1", tenant_id="tenant_demo", groups=["all", "engineering"])
    result = await chat("P6 去上海出差住宿标准是多少？", [], ctx)
    assert "600" in result.answer
    assert any(c.document_id == "travel-policy-v3" for c in result.citations)
    assert all(c.document_id != "travel-policy-v1" for c in result.citations)


@pytest.mark.asyncio
async def test_acl_denies_confidential_doc():
    ctx = SecurityContext(user_id="u1", tenant_id="tenant_demo", groups=["all", "engineering"])
    result = await chat("公司高管奖金是怎么计算的？", [], ctx)
    assert result.insufficient_evidence is True
    assert not result.citations


@pytest.mark.asyncio
async def test_acl_allows_hr_admin():
    ctx = SecurityContext(user_id="hr1", tenant_id="tenant_demo", groups=["all", "hr-admin"])
    result = await chat("公司高管奖金是怎么计算的？", [], ctx)
    assert "经营系数" in result.answer


@pytest.mark.asyncio
async def test_query_rewrite_followup():
    ctx = SecurityContext(user_id="u1", tenant_id="tenant_demo", groups=["all", "engineering"])
    history = [ChatMessage(role="user", content="P7 去上海出差住宿标准是多少？"), ChatMessage(role="assistant", content="800 元")]
    result = await chat("如果超了怎么办？", history, ctx)
    assert "双审批" in result.answer
    assert "P7" in (result.rewritten_query or "")


@pytest.mark.asyncio
async def test_multihop():
    ctx = SecurityContext(user_id="u1", tenant_id="tenant_demo", groups=["all", "engineering"])
    result = await chat("Phoenix 项目技术负责人的上级的上级是谁？", [], ctx)
    assert result.route == "multi_hop"
    assert "王五" in result.answer
