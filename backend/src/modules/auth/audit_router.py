"""FastAPI router for audit log queries."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok, PaginatedData
from . import audit_service
from .audit_schemas import AuditLogRead

router = APIRouter()


@router.get("/audit-logs", summary="查询审计日志")
async def list_audit_logs(
    user_id: Optional[int] = Query(None, description="按用户ID过滤"),
    username: Optional[str] = Query(None, description="按用户名过滤（模糊）"),
    resource_type: Optional[str] = Query(None, description="按资源类型过滤"),
    action: Optional[str] = Query(None, description="按操作类型过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await audit_service.list_audit_logs(
        db,
        user_id=user_id,
        username=username,
        resource_type=resource_type,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    items = [AuditLogRead.model_validate(log) for log in logs]
    paginated = PaginatedData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")
