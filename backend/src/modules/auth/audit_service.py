"""Service for querying audit logs."""
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import AuditLog


async def list_audit_logs(
    db: AsyncSession,
    *,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[AuditLog], int]:
    stmt = select(AuditLog)

    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if username:
        stmt = stmt.where(AuditLog.username.contains(username))
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if status:
        stmt = stmt.where(AuditLog.status == status)
    if start_time:
        stmt = stmt.where(AuditLog.event_time >= start_time)
    if end_time:
        stmt = stmt.where(AuditLog.event_time <= end_time)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(AuditLog.event_time.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    logs = list(result.scalars().all())

    return logs, total
