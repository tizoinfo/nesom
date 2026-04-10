"""Business logic for Work Order management module."""
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import AppException
from .models import WorkOrder, WorkOrderDetail, WorkOrderStatusHistory
from .schemas import ALLOWED_TRANSITIONS


# ── Work Order Number Generation ──────────────────────────────────────────────

async def _generate_work_order_no(db: AsyncSession, station_id: str) -> str:
    """Generate work order number: WO-{station_code}-{YYYYMMDD}-{seq}"""
    today = datetime.utcnow().strftime("%Y%m%d")
    # Use station_id prefix (first 4 chars) as station code
    station_code = station_id[:4].upper()
    prefix = f"WO-{station_code}-{today}-"

    # Find the max sequence for today
    result = await db.execute(
        select(func.count()).where(WorkOrder.work_order_no.like(f"{prefix}%"))
    )
    count = result.scalar_one()
    seq = str(count + 1).zfill(3)
    return f"{prefix}{seq}"


# ── Work Order CRUD ───────────────────────────────────────────────────────────

async def list_work_orders(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    station_id: Optional[str] = None,
    status: Optional[str] = None,
    work_order_type: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[WorkOrder], int]:
    stmt = select(WorkOrder)

    if station_id:
        stmt = stmt.where(WorkOrder.station_id == station_id)
    if status:
        stmt = stmt.where(WorkOrder.status == status)
    if work_order_type:
        stmt = stmt.where(WorkOrder.work_order_type == work_order_type)
    if priority:
        stmt = stmt.where(WorkOrder.priority == priority)
    if assigned_to:
        stmt = stmt.where(WorkOrder.assigned_to == assigned_to)
    if search:
        stmt = stmt.where(
            or_(
                WorkOrder.work_order_no.ilike(f"%{search}%"),
                WorkOrder.title.ilike(f"%{search}%"),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(desc(WorkOrder.reported_at))
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_work_order(db: AsyncSession, work_order_id: str) -> WorkOrder:
    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.id == work_order_id)
        .options(
            selectinload(WorkOrder.details),
            selectinload(WorkOrder.status_history),
        )
    )
    wo = result.scalar_one_or_none()
    if not wo:
        raise AppException(status_code=404, message="工单不存在")
    return wo


async def create_work_order(db: AsyncSession, **kwargs) -> WorkOrder:
    work_order_no = await _generate_work_order_no(db, kwargs["station_id"])
    wo = WorkOrder(
        id=str(uuid.uuid4()),
        work_order_no=work_order_no,
        status="draft",
        **kwargs,
    )
    db.add(wo)
    await db.flush()
    await db.refresh(wo)
    return wo


async def update_work_order(db: AsyncSession, work_order_id: str, **kwargs) -> WorkOrder:
    wo = await get_work_order(db, work_order_id)
    if wo.status in ("closed", "cancelled"):
        raise AppException(status_code=422, message="已关闭或已取消的工单不可修改")

    for key, value in kwargs.items():
        if value is not None:
            setattr(wo, key, value)

    await db.flush()
    await db.refresh(wo)
    return wo


async def delete_work_order(db: AsyncSession, work_order_id: str) -> None:
    wo = await get_work_order(db, work_order_id)
    if wo.status not in ("draft", "cancelled"):
        raise AppException(status_code=422, message="只有草稿或已取消状态的工单可以删除")
    await db.delete(wo)
    await db.flush()


# ── Status Transitions ────────────────────────────────────────────────────────

async def _transition_status(
    db: AsyncSession,
    work_order_id: str,
    target_status: str,
    changed_by: str,
    changed_by_name: str,
    change_reason: Optional[str] = None,
    change_notes: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> WorkOrder:
    wo = await get_work_order(db, work_order_id)
    allowed = ALLOWED_TRANSITIONS.get(wo.status, set())
    if target_status not in allowed:
        raise AppException(
            status_code=422,
            message=f"不允许从 {wo.status} 转换到 {target_status}",
        )

    old_status = wo.status
    wo.status = target_status

    history = WorkOrderStatusHistory(
        work_order_id=work_order_id,
        old_status=old_status,
        new_status=target_status,
        changed_by=changed_by,
        changed_by_name=changed_by_name,
        change_reason=change_reason,
        change_notes=change_notes,
        metadata_=metadata,
    )
    db.add(history)
    await db.flush()
    await db.refresh(wo)
    return wo


async def submit_work_order(
    db: AsyncSession, work_order_id: str, changed_by: str, changed_by_name: str, notes: Optional[str] = None
) -> WorkOrder:
    return await _transition_status(
        db, work_order_id, "pending", changed_by, changed_by_name, change_notes=notes
    )


async def assign_work_order(
    db: AsyncSession,
    work_order_id: str,
    assigned_to: str,
    assigned_to_name: str,
    changed_by: str,
    changed_by_name: str,
    notes: Optional[str] = None,
    scheduled_start: Optional[datetime] = None,
    scheduled_end: Optional[datetime] = None,
) -> WorkOrder:
    wo = await _transition_status(
        db, work_order_id, "assigned", changed_by, changed_by_name, change_notes=notes
    )
    wo.assigned_to = assigned_to
    wo.assigned_to_name = assigned_to_name
    wo.assigned_at = datetime.utcnow()
    if scheduled_start:
        wo.scheduled_start = scheduled_start
    if scheduled_end:
        wo.scheduled_end = scheduled_end
    await db.flush()
    await db.refresh(wo)
    return wo


async def start_work_order(
    db: AsyncSession,
    work_order_id: str,
    changed_by: str,
    changed_by_name: str,
    location: Optional[str] = None,
    longitude: Optional[float] = None,
    latitude: Optional[float] = None,
    notes: Optional[str] = None,
) -> WorkOrder:
    wo = await _transition_status(
        db, work_order_id, "in_progress", changed_by, changed_by_name, change_notes=notes
    )
    wo.actual_start = datetime.utcnow()
    if location:
        wo.location = location
    if longitude is not None:
        wo.longitude = longitude
    if latitude is not None:
        wo.latitude = latitude
    await db.flush()
    await db.refresh(wo)
    return wo


async def submit_review(
    db: AsyncSession,
    work_order_id: str,
    changed_by: str,
    changed_by_name: str,
    completion_rate: int = 100,
    actual_duration: Optional[int] = None,
    notes: Optional[str] = None,
    images: Optional[list] = None,
) -> WorkOrder:
    wo = await _transition_status(
        db, work_order_id, "pending_review", changed_by, changed_by_name, change_notes=notes
    )
    wo.actual_end = datetime.utcnow()
    wo.completion_rate = completion_rate
    if actual_duration is not None:
        wo.actual_duration = actual_duration
    if images:
        existing = wo.images or []
        wo.images = existing + images
    await db.flush()
    await db.refresh(wo)
    return wo


async def approve_work_order(
    db: AsyncSession,
    work_order_id: str,
    changed_by: str,
    changed_by_name: str,
    notes: Optional[str] = None,
    actual_cost: Optional[float] = None,
) -> WorkOrder:
    wo = await _transition_status(
        db, work_order_id, "completed", changed_by, changed_by_name, change_notes=notes
    )
    if actual_cost is not None:
        wo.actual_cost = actual_cost
    await db.flush()
    await db.refresh(wo)
    return wo


async def close_work_order(
    db: AsyncSession,
    work_order_id: str,
    changed_by: str,
    changed_by_name: str,
    notes: Optional[str] = None,
) -> WorkOrder:
    wo = await _transition_status(
        db, work_order_id, "closed", changed_by, changed_by_name, change_notes=notes
    )
    wo.closed_at = datetime.utcnow()
    wo.closed_by = changed_by
    await db.flush()
    await db.refresh(wo)
    return wo


async def cancel_work_order(
    db: AsyncSession,
    work_order_id: str,
    changed_by: str,
    changed_by_name: str,
    cancel_reason: str,
    cancel_notes: Optional[str] = None,
) -> WorkOrder:
    return await _transition_status(
        db, work_order_id, "cancelled", changed_by, changed_by_name,
        change_reason=cancel_reason, change_notes=cancel_notes,
    )


async def reject_to_in_progress(
    db: AsyncSession,
    work_order_id: str,
    changed_by: str,
    changed_by_name: str,
    notes: Optional[str] = None,
) -> WorkOrder:
    """Reject review and send back to in_progress."""
    return await _transition_status(
        db, work_order_id, "in_progress", changed_by, changed_by_name, change_notes=notes
    )



# ── Timeout Monitoring & Auto-Escalation ──────────────────────────────────────

# Priority timeout thresholds in hours
PRIORITY_TIMEOUT_HOURS = {
    "low": 72,
    "medium": 24,
    "high": 8,
    "emergency": 2,
}

# Priority escalation order
PRIORITY_ESCALATION = {
    "low": "medium",
    "medium": "high",
    "high": "emergency",
    "emergency": "emergency",  # already max
}


async def check_overdue_work_orders(db: AsyncSession) -> List[WorkOrder]:
    """Find work orders that have exceeded their priority-based time limit
    and escalate their priority."""
    now = datetime.utcnow()
    escalated = []

    # Query active work orders (assigned or in_progress) that have an assigned_at time
    result = await db.execute(
        select(WorkOrder).where(
            WorkOrder.status.in_(["assigned", "in_progress"]),
            WorkOrder.assigned_at.isnot(None),
        )
    )
    work_orders = list(result.scalars().all())

    for wo in work_orders:
        timeout_hours = PRIORITY_TIMEOUT_HOURS.get(wo.priority, 24)
        elapsed_hours = (now - wo.assigned_at).total_seconds() / 3600

        if elapsed_hours > timeout_hours:
            new_priority = PRIORITY_ESCALATION.get(wo.priority, wo.priority)
            if new_priority != wo.priority:
                old_priority = wo.priority
                wo.priority = new_priority
                # Record the escalation in status history
                history = WorkOrderStatusHistory(
                    work_order_id=wo.id,
                    old_status=wo.status,
                    new_status=wo.status,  # status doesn't change, only priority
                    changed_by="system",
                    changed_by_name="系统自动升级",
                    change_reason=f"工单超时自动升级优先级: {old_priority} -> {new_priority}",
                    metadata_={"escalation": True, "old_priority": old_priority, "elapsed_hours": round(elapsed_hours, 1)},
                )
                db.add(history)
                escalated.append(wo)

    if escalated:
        await db.flush()

    return escalated



# ── Work Order Templates ──────────────────────────────────────────────────────

async def list_templates(
    db: AsyncSession,
    work_order_type: Optional[str] = None,
    device_type_id: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List["WorkOrderTemplate"]:
    from .models import WorkOrderTemplate

    stmt = select(WorkOrderTemplate)
    if work_order_type:
        stmt = stmt.where(WorkOrderTemplate.work_order_type == work_order_type)
    if device_type_id:
        stmt = stmt.where(WorkOrderTemplate.device_type_id == device_type_id)
    if is_active is not None:
        stmt = stmt.where(WorkOrderTemplate.is_active == is_active)
    stmt = stmt.order_by(WorkOrderTemplate.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_template(db: AsyncSession, template_id: str) -> "WorkOrderTemplate":
    from .models import WorkOrderTemplate

    result = await db.execute(
        select(WorkOrderTemplate).where(WorkOrderTemplate.id == template_id)
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise AppException(status_code=404, message="工单模板不存在")
    return tpl


async def create_template(db: AsyncSession, **kwargs) -> "WorkOrderTemplate":
    from .models import WorkOrderTemplate

    # Check uniqueness of template_code
    existing = await db.execute(
        select(WorkOrderTemplate).where(WorkOrderTemplate.template_code == kwargs["template_code"])
    )
    if existing.scalar_one_or_none():
        raise AppException(status_code=409, message="模板编码已存在")

    # Convert steps_template items to dicts if they are Pydantic models
    steps = kwargs.get("steps_template", [])
    if steps and hasattr(steps[0], "model_dump"):
        kwargs["steps_template"] = [s.model_dump() for s in steps]

    tpl = WorkOrderTemplate(id=str(uuid.uuid4()), **kwargs)
    db.add(tpl)
    await db.flush()
    await db.refresh(tpl)
    return tpl


async def update_template(db: AsyncSession, template_id: str, **kwargs) -> "WorkOrderTemplate":
    tpl = await get_template(db, template_id)

    steps = kwargs.get("steps_template")
    if steps and hasattr(steps[0], "model_dump"):
        kwargs["steps_template"] = [s.model_dump() for s in steps]

    for key, value in kwargs.items():
        if value is not None:
            setattr(tpl, key, value)

    await db.flush()
    await db.refresh(tpl)
    return tpl


async def create_from_template(
    db: AsyncSession,
    template_id: str,
    station_id: str,
    reported_by: str,
    reported_by_name: str,
    title: str,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    device_id: Optional[str] = None,
    device_name: Optional[str] = None,
    device_code: Optional[str] = None,
    scheduled_start: Optional[datetime] = None,
    scheduled_end: Optional[datetime] = None,
) -> WorkOrder:
    tpl = await get_template(db, template_id)
    if not tpl.is_active:
        raise AppException(status_code=422, message="模板已禁用")

    wo = await create_work_order(
        db,
        work_order_type=tpl.work_order_type,
        title=title,
        description=description or tpl.description_template,
        priority=priority or tpl.priority,
        emergency_level="normal",
        station_id=station_id,
        device_id=device_id,
        device_name=device_name,
        device_code=device_code,
        reported_by=reported_by,
        reported_by_name=reported_by_name,
        estimated_duration=tpl.estimated_duration,
        cost_estimate=tpl.cost_estimate,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
    )

    # Create steps from template
    steps = tpl.steps_template or []
    for i, step in enumerate(steps, start=1):
        detail = WorkOrderDetail(
            work_order_id=wo.id,
            step_number=i,
            step_title=step.get("step_title", f"步骤 {i}"),
            step_description=step.get("step_description"),
        )
        db.add(detail)

    # Increment used_count
    tpl.used_count = (tpl.used_count or 0) + 1
    await db.flush()
    await db.refresh(wo)
    return wo



# ── Work Order Statistics ─────────────────────────────────────────────────────

async def get_count_statistics(
    db: AsyncSession,
    station_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Get work order count statistics by status, type, and priority."""
    base = select(WorkOrder)
    if station_id:
        base = base.where(WorkOrder.station_id == station_id)
    if start_date:
        base = base.where(WorkOrder.reported_at >= start_date)
    if end_date:
        base = base.where(WorkOrder.reported_at <= end_date)

    # Total
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    # By status
    status_stmt = (
        select(WorkOrder.status, func.count().label("cnt"))
        .select_from(base.subquery().alias("sub"))
    )
    # Re-build grouped queries from scratch for correctness
    by_status = {}
    for s in ALLOWED_TRANSITIONS.keys():
        q = select(func.count()).where(WorkOrder.status == s)
        if station_id:
            q = q.where(WorkOrder.station_id == station_id)
        if start_date:
            q = q.where(WorkOrder.reported_at >= start_date)
        if end_date:
            q = q.where(WorkOrder.reported_at <= end_date)
        by_status[s] = (await db.execute(q)).scalar_one()

    # By type
    by_type = {}
    for t in ["repair", "inspection", "maintenance", "fault", "other"]:
        q = select(func.count()).where(WorkOrder.work_order_type == t)
        if station_id:
            q = q.where(WorkOrder.station_id == station_id)
        if start_date:
            q = q.where(WorkOrder.reported_at >= start_date)
        if end_date:
            q = q.where(WorkOrder.reported_at <= end_date)
        by_type[t] = (await db.execute(q)).scalar_one()

    # By priority
    by_priority = {}
    for p in ["low", "medium", "high", "emergency"]:
        q = select(func.count()).where(WorkOrder.priority == p)
        if station_id:
            q = q.where(WorkOrder.station_id == station_id)
        if start_date:
            q = q.where(WorkOrder.reported_at >= start_date)
        if end_date:
            q = q.where(WorkOrder.reported_at <= end_date)
        by_priority[p] = (await db.execute(q)).scalar_one()

    return {
        "total": total,
        "by_status": by_status,
        "by_type": by_type,
        "by_priority": by_priority,
    }


async def get_timeliness_statistics(
    db: AsyncSession,
    station_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Get work order timeliness statistics."""
    base_where = [WorkOrder.status.in_(["completed", "closed"])]
    if station_id:
        base_where.append(WorkOrder.station_id == station_id)
    if start_date:
        base_where.append(WorkOrder.reported_at >= start_date)
    if end_date:
        base_where.append(WorkOrder.reported_at <= end_date)

    # Average processing time (actual_duration in minutes)
    avg_result = await db.execute(
        select(func.avg(WorkOrder.actual_duration)).where(*base_where)
    )
    avg_processing_time = avg_result.scalar_one() or 0

    # Average response time (assigned_at - reported_at) — approximate via count
    total_completed = (await db.execute(
        select(func.count()).where(*base_where)
    )).scalar_one()

    # Overdue count: completed orders where actual_end > scheduled_end
    overdue_where = base_where + [
        WorkOrder.actual_end.isnot(None),
        WorkOrder.scheduled_end.isnot(None),
        WorkOrder.actual_end > WorkOrder.scheduled_end,
    ]
    overdue_count = (await db.execute(
        select(func.count()).where(*overdue_where)
    )).scalar_one()

    on_time_rate = (total_completed - overdue_count) / total_completed if total_completed > 0 else 0

    return {
        "avg_processing_time": round(float(avg_processing_time), 1),
        "on_time_rate": round(on_time_rate, 2),
        "overdue_count": overdue_count,
        "total_completed": total_completed,
    }


async def get_performance_statistics(
    db: AsyncSession,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list:
    """Get personnel performance statistics."""
    base_where = [WorkOrder.assigned_to.isnot(None)]
    if start_date:
        base_where.append(WorkOrder.reported_at >= start_date)
    if end_date:
        base_where.append(WorkOrder.reported_at <= end_date)

    if user_id:
        base_where.append(WorkOrder.assigned_to == user_id)

    stmt = (
        select(
            WorkOrder.assigned_to,
            WorkOrder.assigned_to_name,
            func.count().label("total_assigned"),
            func.sum(func.IF(WorkOrder.status.in_(["completed", "closed"]), 1, 0)).label("total_completed"),
            func.avg(WorkOrder.actual_duration).label("avg_processing_time"),
        )
        .where(*base_where)
        .group_by(WorkOrder.assigned_to, WorkOrder.assigned_to_name)
    )
    result = await db.execute(stmt)
    rows = result.all()

    performance = []
    for row in rows:
        total_assigned = row.total_assigned or 0
        total_completed = row.total_completed or 0
        completion_rate = total_completed / total_assigned if total_assigned > 0 else 0
        performance.append({
            "user_id": row.assigned_to,
            "user_name": row.assigned_to_name,
            "total_assigned": total_assigned,
            "total_completed": int(total_completed),
            "completion_rate": round(completion_rate, 2),
            "avg_processing_time": round(float(row.avg_processing_time or 0), 1),
        })

    return performance
