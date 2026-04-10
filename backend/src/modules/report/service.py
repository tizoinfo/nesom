"""Business logic for Report and statistics module."""
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import redis.asyncio as aioredis
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import AppException
from src.modules.device.models import Device, DeviceAlert, DeviceType
from src.modules.workorder.models import WorkOrder
from src.modules.inspection.models import InspectionTask
from .models import ReportTemplate, ReportExecution, StatisticsCache
from .schemas import (
    DashboardKPI,
    DashboardResponse,
    DeviceStatsSummary,
    DeviceStatsResponse,
    DeviceTypeStats,
    InspectionStatsSummary,
    StationDeviceStats,
    WorkOrderPriorityStats,
    WorkOrderStatsSummary,
    WorkOrderStatsResponse,
    WorkOrderTypeStats,
)

STATS_CACHE_TTL = 300  # 5 minutes


def _redis_client() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def _cache_get(key: str) -> Optional[str]:
    """Get a value from Redis cache, returning None on any failure."""
    try:
        r = _redis_client()
        value = await r.get(key)
        await r.aclose()
        return value
    except Exception:
        return None


async def _cache_set(key: str, value: str, ttl: int = STATS_CACHE_TTL) -> None:
    """Set a value in Redis cache, silently ignoring failures."""
    try:
        r = _redis_client()
        await r.setex(key, ttl, value)
        await r.aclose()
    except Exception:
        pass


# ── Dashboard Statistics ──────────────────────────────────────────────────────

async def get_device_stats(db: AsyncSession, station_id: Optional[str] = None) -> DeviceStatsResponse:
    """Get device running statistics (online rate, OEE, etc.)."""
    base_filter = [Device.deleted_at.is_(None)]
    if station_id:
        base_filter.append(Device.station_id == station_id)

    # Summary counts by status
    stmt = select(
        func.count().label("total"),
        func.sum(case((Device.status == "online", 1), else_=0)).label("online"),
        func.sum(case((Device.status == "offline", 1), else_=0)).label("offline"),
        func.sum(case((Device.status == "fault", 1), else_=0)).label("fault"),
        func.sum(case((Device.status == "maintenance", 1), else_=0)).label("maintenance"),
    ).where(and_(*base_filter))

    result = await db.execute(stmt)
    row = result.one()
    total = row.total or 0
    online = row.online or 0
    offline = row.offline or 0
    fault = row.fault or 0
    maintenance = row.maintenance or 0

    avg_availability = float(online / total * 100) if total > 0 else 0.0
    # Simplified OEE: availability * assumed performance(95%) * assumed quality(98%)
    avg_oee = round(avg_availability * 0.95 * 0.98 / 100, 2) if total > 0 else 0.0

    summary = DeviceStatsSummary(
        total_devices=total,
        online_devices=online,
        offline_devices=offline,
        fault_devices=fault,
        maintenance_devices=maintenance,
        avg_availability=round(avg_availability, 2),
        avg_oee=avg_oee,
    )

    # By station
    station_stmt = select(
        Device.station_id,
        func.count().label("device_count"),
        func.sum(case((Device.status == "online", 1), else_=0)).label("online_count"),
        func.sum(case((Device.status == "offline", 1), else_=0)).label("offline_count"),
        func.sum(case((Device.status == "fault", 1), else_=0)).label("fault_count"),
    ).where(and_(*base_filter)).group_by(Device.station_id)

    station_result = await db.execute(station_stmt)
    by_station = []
    for r in station_result.all():
        cnt = int(r.device_count or 0)
        on = int(r.online_count or 0)
        by_station.append(StationDeviceStats(
            station_id=r.station_id,
            device_count=cnt,
            online_count=on,
            offline_count=int(r.offline_count or 0),
            fault_count=int(r.fault_count or 0),
            availability=round(float(on / cnt * 100) if cnt > 0 else 0.0, 2),
        ))

    # By device type
    type_stmt = (
        select(
            Device.device_type_id,
            DeviceType.type_name,
            func.count().label("device_count"),
            func.sum(case((Device.status == "online", 1), else_=0)).label("online_count"),
        )
        .join(DeviceType, Device.device_type_id == DeviceType.id)
        .where(and_(*base_filter))
        .group_by(Device.device_type_id, DeviceType.type_name)
    )
    type_result = await db.execute(type_stmt)
    by_device_type = []
    for r in type_result.all():
        cnt = int(r.device_count or 0)
        on = int(r.online_count or 0)
        by_device_type.append(DeviceTypeStats(
            device_type_id=r.device_type_id,
            device_type_name=r.type_name,
            device_count=cnt,
            availability=round(float(on / cnt * 100) if cnt > 0 else 0.0, 2),
        ))

    return DeviceStatsResponse(summary=summary, by_station=by_station, by_device_type=by_device_type)


async def get_workorder_stats(
    db: AsyncSession,
    station_id: Optional[str] = None,
    period: str = "month",
) -> WorkOrderStatsResponse:
    """Get work order statistics (counts, timeliness)."""
    base_filter = []
    if station_id:
        base_filter.append(WorkOrder.station_id == station_id)

    # Time filter based on period
    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "quarter":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_filter.append(WorkOrder.created_at >= start)

    completed_statuses = {"completed", "closed"}

    # Summary
    stmt = select(
        func.count().label("total"),
        func.sum(case((WorkOrder.status.in_(completed_statuses), 1), else_=0)).label("completed"),
        func.sum(case((WorkOrder.status.in_({"draft", "pending"}), 1), else_=0)).label("pending"),
        func.sum(case((WorkOrder.status.in_({"assigned", "in_progress"}), 1), else_=0)).label("in_progress"),
    ).where(and_(*base_filter) if base_filter else True)

    result = await db.execute(stmt)
    row = result.one()
    total = row.total or 0
    completed = row.completed or 0
    pending = row.pending or 0
    in_progress = row.in_progress or 0

    # Average completion time for completed orders
    avg_stmt = select(
        func.avg(WorkOrder.actual_duration).label("avg_duration"),
    ).where(
        and_(
            WorkOrder.status.in_(completed_statuses),
            WorkOrder.actual_duration.isnot(None),
            *base_filter,
        )
    )
    avg_result = await db.execute(avg_stmt)
    avg_row = avg_result.one()
    avg_hours = round(float(avg_row.avg_duration) / 60, 2) if avg_row.avg_duration else None

    # Overdue: scheduled_end is past and not completed
    overdue_stmt = select(func.count()).where(
        and_(
            WorkOrder.scheduled_end < now,
            ~WorkOrder.status.in_(completed_statuses | {"cancelled"}),
            *base_filter,
        )
    )
    overdue_result = await db.execute(overdue_stmt)
    overdue = overdue_result.scalar_one() or 0

    summary = WorkOrderStatsSummary(
        total_workorders=total,
        completed_workorders=completed,
        pending_workorders=pending,
        in_progress_workorders=in_progress,
        overdue_workorders=overdue,
        avg_completion_hours=avg_hours,
        completion_rate=round((completed / total * 100) if total > 0 else 0.0, 2),
    )

    # By type
    type_stmt = (
        select(
            WorkOrder.work_order_type,
            func.count().label("count"),
            func.sum(case((WorkOrder.status.in_(completed_statuses), 1), else_=0)).label("completed"),
            func.avg(
                case((WorkOrder.actual_duration.isnot(None), WorkOrder.actual_duration), else_=None)
            ).label("avg_duration"),
        )
        .where(and_(*base_filter) if base_filter else True)
        .group_by(WorkOrder.work_order_type)
    )
    type_result = await db.execute(type_stmt)
    by_type = []
    for r in type_result.all():
        avg_d = round(float(r.avg_duration) / 60, 2) if r.avg_duration else None
        by_type.append(WorkOrderTypeStats(
            work_order_type=r.work_order_type,
            count=r.count or 0,
            completed=r.completed or 0,
            avg_duration_hours=avg_d,
        ))

    # By priority
    priority_stmt = (
        select(
            WorkOrder.priority,
            func.count().label("count"),
            func.sum(case((WorkOrder.status.in_(completed_statuses), 1), else_=0)).label("completed"),
        )
        .where(and_(*base_filter) if base_filter else True)
        .group_by(WorkOrder.priority)
    )
    priority_result = await db.execute(priority_stmt)
    by_priority = [
        WorkOrderPriorityStats(priority=r.priority, count=r.count or 0, completed=r.completed or 0)
        for r in priority_result.all()
    ]

    return WorkOrderStatsResponse(summary=summary, by_type=by_type, by_priority=by_priority)


async def get_inspection_stats(
    db: AsyncSession,
    station_id: Optional[str] = None,
    period: str = "month",
) -> InspectionStatsSummary:
    """Get inspection task statistics."""
    now = datetime.utcnow()
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "quarter":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_filter = [InspectionTask.created_at >= start]

    stmt = select(
        func.count().label("total"),
        func.sum(case((InspectionTask.status == "completed", 1), else_=0)).label("completed"),
        func.sum(case((InspectionTask.status == "pending", 1), else_=0)).label("pending"),
        func.sum(case((InspectionTask.status == "overdue", 1), else_=0)).label("overdue"),
        func.sum(InspectionTask.problem_count).label("problems"),
    ).where(and_(*base_filter))

    result = await db.execute(stmt)
    row = result.one()
    total = row.total or 0
    completed = row.completed or 0

    return InspectionStatsSummary(
        total_tasks=total,
        completed_tasks=completed,
        pending_tasks=row.pending or 0,
        overdue_tasks=row.overdue or 0,
        completion_rate=round((completed / total * 100) if total > 0 else 0.0, 2),
        problem_count=row.problems or 0,
    )


async def get_dashboard_data(
    db: AsyncSession,
    station_id: Optional[str] = None,
    period: str = "month",
) -> DashboardResponse:
    """Get full dashboard data with KPIs, with Redis caching."""
    cache_key = f"dashboard:stats:{station_id or 'all'}:{period}"

    # Try Redis cache
    cached = await _cache_get(cache_key)
    if cached:
        return DashboardResponse.model_validate_json(cached)

    # Compute stats
    device_stats = await get_device_stats(db, station_id=station_id)
    workorder_stats = await get_workorder_stats(db, station_id=station_id, period=period)
    inspection_stats = await get_inspection_stats(db, station_id=station_id, period=period)

    # Active alerts count
    alert_filter = [DeviceAlert.status.in_(["active", "acknowledged"])]
    alert_stmt = select(func.count()).select_from(DeviceAlert).where(and_(*alert_filter))
    alert_result = await db.execute(alert_stmt)
    active_alerts = alert_result.scalar_one() or 0

    kpi = DashboardKPI(
        device_online_rate=device_stats.summary.avg_availability,
        workorder_completion_rate=workorder_stats.summary.completion_rate,
        inspection_completion_rate=inspection_stats.completion_rate,
        active_alerts=active_alerts,
    )

    response = DashboardResponse(
        kpi=kpi,
        device_stats=device_stats,
        workorder_stats=workorder_stats,
        inspection_stats=inspection_stats,
        generated_at=datetime.utcnow(),
    )

    # Cache result
    await _cache_set(cache_key, response.model_dump_json())

    return response



# ── Report Template CRUD ──────────────────────────────────────────────────────

async def list_templates(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Tuple[List[ReportTemplate], int]:
    stmt = select(ReportTemplate)

    if category:
        stmt = stmt.where(ReportTemplate.category == category)
    if is_active is not None:
        stmt = stmt.where(ReportTemplate.is_active == is_active)
    if search:
        stmt = stmt.where(
            ReportTemplate.template_name.ilike(f"%{search}%")
            | ReportTemplate.template_code.ilike(f"%{search}%")
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(ReportTemplate.sort_order, ReportTemplate.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_template(db: AsyncSession, template_id: str) -> ReportTemplate:
    result = await db.execute(select(ReportTemplate).where(ReportTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise AppException(status_code=404, message="报表模板不存在")
    return template


async def create_template(
    db: AsyncSession,
    template_code: str,
    template_name: str,
    category: str,
    created_by: str,
    **kwargs,
) -> ReportTemplate:
    # Check uniqueness
    existing = await db.execute(
        select(ReportTemplate).where(ReportTemplate.template_code == template_code)
    )
    if existing.scalar_one_or_none():
        raise AppException(status_code=409, message="模板编码已存在")

    template = ReportTemplate(
        id=str(uuid.uuid4()),
        template_code=template_code,
        template_name=template_name,
        category=category,
        created_by=created_by,
        **kwargs,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def update_template(db: AsyncSession, template_id: str, **kwargs) -> ReportTemplate:
    template = await get_template(db, template_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(template, key, value)
    template.version += 1
    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(db: AsyncSession, template_id: str) -> None:
    template = await get_template(db, template_id)
    template.is_active = False
    await db.commit()


# ── Report Query Execution ────────────────────────────────────────────────────

async def execute_report_query(
    db: AsyncSession,
    template_id: str,
    parameters: Dict[str, Any],
    page: int = 1,
    page_size: int = 100,
    enable_cache: bool = True,
) -> Dict[str, Any]:
    """Execute a parameterized report query against the template."""
    template = await get_template(db, template_id)

    if not template.is_active:
        raise AppException(status_code=422, message="报表模板已禁用")

    # Check cache
    cache_key = _build_query_cache_key(template_id, parameters, page, page_size)
    if enable_cache:
        cached = await _cache_get(cache_key)
        if cached:
            return json.loads(cached)

    # Build response from column definitions (simulated query execution)
    columns = [
        {"field": col.get("field", ""), "display_name": col.get("display_name", ""), "data_type": col.get("data_type", "string")}
        for col in template.column_definitions
    ]

    result = {
        "columns": columns,
        "rows": [],
        "summary": {
            "total_rows": 0,
            "execution_time_ms": 0,
            "cache_hit": False,
            "template_id": template_id,
        },
    }

    # Cache result
    if enable_cache:
        await _cache_set(cache_key, json.dumps(result))

    return result


def _build_query_cache_key(template_id: str, parameters: Dict, page: int, page_size: int) -> str:
    import hashlib
    param_str = json.dumps({"params": parameters, "page": page, "page_size": page_size}, sort_keys=True)
    h = hashlib.md5(param_str.encode()).hexdigest()
    return f"report:query:{template_id}:{h}"



# ── Report Export ─────────────────────────────────────────────────────────────

async def create_export_task(
    db: AsyncSession,
    template_id: str,
    parameters: Dict[str, Any],
    export_format: str = "excel",
    options: Optional[Dict[str, Any]] = None,
    executed_by: str = "system",
) -> ReportExecution:
    """Create an async report export task."""
    template = await get_template(db, template_id)
    if not template.is_active:
        raise AppException(status_code=422, message="报表模板已禁用")

    execution = ReportExecution(
        id=str(uuid.uuid4()),
        execution_id=f"EXP-{uuid.uuid4().hex[:12].upper()}",
        template_id=template_id,
        execution_type="manual",
        parameters=parameters,
        status="pending",
        progress=0,
        executed_by=executed_by,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Dispatch Celery task
    from src.modules.report.tasks import generate_report_export
    generate_report_export.delay(
        execution_id=execution.id,
        template_id=template_id,
        parameters=parameters,
        export_format=export_format,
        options=options or {},
    )

    return execution


async def get_export_task_status(db: AsyncSession, execution_id: str) -> ReportExecution:
    """Get the status of an export task."""
    result = await db.execute(
        select(ReportExecution).where(ReportExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise AppException(status_code=404, message="导出任务不存在")
    return execution
