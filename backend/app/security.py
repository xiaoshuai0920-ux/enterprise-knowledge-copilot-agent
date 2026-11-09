from fastapi import Header
from .schemas import SecurityContext


async def get_security_context(
    x_user_id: str = Header(default="u_dev_001"),
    x_tenant_id: str = Header(default="tenant_demo"),
    x_user_role: str = Header(default="developer"),
    x_user_department: str = Header(default="engineering"),
    x_user_groups: str = Header(default="all,engineering"),
) -> SecurityContext:
    groups = [g.strip() for g in x_user_groups.split(",") if g.strip()]
    if "all" not in groups:
        groups.append("all")
    return SecurityContext(
        user_id=x_user_id,
        tenant_id=x_tenant_id,
        role=x_user_role,
        department=x_user_department,
        groups=groups,
    )
