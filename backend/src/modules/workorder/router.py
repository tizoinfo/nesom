"""FastAPI router for Work Order management module."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok, PaginatedData
from . import service
from .schemas import (
    ApproveWorkOrder,
    AssignWorkOrder,
    CancelWorkOrder,
    CloseWorkOrder,
    StartWorkOrder,
    SubmitReviewWorkOrder,
    SubmitWorkOrder,
    WorkOrderCreate,
    WorkOrderDetail,
    WorkOrderRead,
    WorkOrderUpdate,
)

router = APIRouter()


# ── Work Order CRUD ───────────────────────────────────────────────────────────

@router.get("/work-orders", summary="获取工单列表")
async def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    station_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    work_order_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    orders, total = await service.list_work_orders(
        db,
        page=page,
        page_size=page_size,
        station_id=station_id,
        status=status,
        work_order_type=work_order_type,
        priority=priority,
        assigned_to=assigned_to,
        search=search,
    )
    items = [WorkOrderRead.model_validate(o) for o in orders]
    paginated = PaginatedData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")


@router.get("/work-orders/{work_order_id}", summary="获取工单详情")
async def get_work_order(work_order_id: str, db: AsyncSession = Depends(get_db)):
    wo = await service.get_work_order(db, work_order_id)
    return ok(data=WorkOrderDetail.model_validate(wo), message="成功")


@router.post("/work-orders", summary="创建工单", status_code=201)
async def create_work_order(body: WorkOrderCreate, db: AsyncSession = Depends(get_db)):
    wo = await service.create_work_order(
        db,
        work_order_type=body.work_order_type,
        title=body.title,
        description=body.description,
        priority=body.priority,
        emergency_level=body.emergency_level,
        station_id=body.station_id,
        device_id=body.device_id,
        device_name=body.device_name,
        device_code=body.device_code,
        reported_by=body.reported_by,
        reported_by_name=body.reported_by_name,
        scheduled_start=body.scheduled_start,
        scheduled_end=body.scheduled_end,
        estimated_duration=body.estimated_duration,
        cost_estimate=body.cost_estimate,
        location=body.location,
        longitude=body.longitude,
        latitude=body.latitude,
        images=body.images,
        attachments=body.attachments,
        tags=body.tags,
    )
    return ok(
        data={"id": wo.id, "work_order_no": wo.work_order_no, "status": wo.status},
        message="工单创建成功",
    )


@router.patch("/work-orders/{work_order_id}", summary="更新工单")
async def update_work_order(
    work_order_id: str, body: WorkOrderUpdate, db: AsyncSession = Depends(get_db)
):
    update_data = body.model_dump(exclude_none=True)
    wo = await service.update_work_order(db, work_order_id, **update_data)
    return ok(data={"id": wo.id, "updated_at": wo.updated_at}, message="工单更新成功")


@router.delete("/work-orders/{work_order_id}", summary="删除工单", status_code=200)
async def delete_work_order(work_order_id: str, db: AsyncSession = Depends(get_db)):
    await service.delete_work_order(db, work_order_id)
    return ok(message="工单删除成功")


# ── Status Transition Endpoints ───────────────────────────────────────────────

@router.post("/work-orders/{work_order_id}/submit", summary="提交工单")
async def submit_work_order(
    work_order_id: str,
    body: SubmitWorkOrder = SubmitWorkOrder(),
    db: AsyncSession = Depends(get_db),
):
    wo = await service.submit_work_order(
        db, work_order_id, changed_by="system", changed_by_name="系统", notes=body.submit_notes
    )
    return ok(
        data={"old_status": "draft", "new_status": wo.status, "changed_at": datetime.utcnow()},
        message="工单提交成功",
    )


@router.post("/work-orders/{work_order_id}/assign", summary="分配工单")
async def assign_work_order(
    work_order_id: str, body: AssignWorkOrder, db: AsyncSession = Depends(get_db)
):
    wo = await service.assign_work_order(
        db,
        work_order_id,
        assigned_to=body.assigned_to,
        assigned_to_name=body.assigned_to_name,
        changed_by="system",
        changed_by_name="系统",
        notes=body.assign_notes,
        scheduled_start=body.scheduled_start,
        scheduled_end=body.scheduled_end,
    )
    return ok(
        data={"old_status": "pending", "new_status": wo.status, "assigned_at": wo.assigned_at},
        message="工单分配成功",
    )


@router.post("/work-orders/{work_order_id}/start", summary="开始处理工单")
async def start_work_order(
    work_order_id: str,
    body: StartWorkOrder = StartWorkOrder(),
    db: AsyncSession = Depends(get_db),
):
    wo = await service.start_work_order(
        db,
        work_order_id,
        changed_by="system",
        changed_by_name="系统",
        location=body.location,
        longitude=body.longitude,
        latitude=body.latitude,
        notes=body.start_notes,
    )
    return ok(
        data={"old_status": "assigned", "new_status": wo.status, "actual_start": wo.actual_start},
        message="工单开始处理",
    )


@router.post("/work-orders/{work_order_id}/submit-review", summary="提交审核")
async def submit_review(
    work_order_id: str, body: SubmitReviewWorkOrder, db: AsyncSession = Depends(get_db)
):
    wo = await service.submit_review(
        db,
        work_order_id,
        changed_by="system",
        changed_by_name="系统",
        completion_rate=body.completion_rate,
        actual_duration=body.actual_duration,
        notes=body.completion_notes,
        images=body.images,
    )
    return ok(
        data={"old_status": "in_progress", "new_status": wo.status, "actual_end": wo.actual_end},
        message="工单已提交审核",
    )


@router.post("/work-orders/{work_order_id}/approve", summary="审核通过")
async def approve_work_order(
    work_order_id: str,
    body: ApproveWorkOrder = ApproveWorkOrder(),
    db: AsyncSession = Depends(get_db),
):
    wo = await service.approve_work_order(
        db,
        work_order_id,
        changed_by="system",
        changed_by_name="系统",
        notes=body.approve_notes,
        actual_cost=body.actual_cost,
    )
    return ok(
        data={"old_status": "pending_review", "new_status": wo.status},
        message="工单审核通过",
    )


@router.post("/work-orders/{work_order_id}/close", summary="关闭工单")
async def close_work_order(
    work_order_id: str,
    body: CloseWorkOrder = CloseWorkOrder(),
    db: AsyncSession = Depends(get_db),
):
    wo = await service.close_work_order(
        db, work_order_id, changed_by="system", changed_by_name="系统", notes=body.close_notes
    )
    return ok(
        data={"old_status": "completed", "new_status": wo.status, "closed_at": wo.closed_at},
        message="工单已关闭",
    )


@router.post("/work-orders/{work_order_id}/cancel", summary="取消工单")
async def cancel_work_order(
    work_order_id: str, body: CancelWorkOrder, db: AsyncSession = Depends(get_db)
):
    wo = await service.cancel_work_order(
        db,
        work_order_id,
        changed_by="system",
        changed_by_name="系统",
        cancel_reason=body.cancel_reason,
        cancel_notes=body.cancel_notes,
    )
    return ok(
        data={"new_status": wo.status},
        message="工单已取消",
    )



# ── Work Order Templates ──────────────────────────────────────────────────────

from .schemas import (
    CreateFromTemplate,
    WorkOrderTemplateCreate,
    WorkOrderTemplateRead,
    WorkOrderTemplateUpdate,
)


@router.get("/work-order-templates", summary="获取工单模板列表")
async def list_templates(
    work_order_type: Optional[str] = Query(None),
    device_type_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    templates = await service.list_templates(
        db, work_order_type=work_order_type, device_type_id=device_type_id, is_active=is_active
    )
    items = [WorkOrderTemplateRead.model_validate(t) for t in templates]
    return ok(data=items, message="成功")


@router.post("/work-order-templates", summary="创建工单模板", status_code=201)
async def create_template(body: WorkOrderTemplateCreate, db: AsyncSession = Depends(get_db)):
    tpl = await service.create_template(
        db,
        template_code=body.template_code,
        template_name=body.template_name,
        work_order_type=body.work_order_type,
        device_type_id=body.device_type_id,
        priority=body.priority,
        estimated_duration=body.estimated_duration,
        cost_estimate=body.cost_estimate,
        description_template=body.description_template,
        steps_template=body.steps_template,
        required_tools=body.required_tools,
        required_parts=body.required_parts,
        safety_instructions=body.safety_instructions,
        quality_standards=body.quality_standards,
        created_by=body.created_by,
    )
    return ok(
        data={"id": tpl.id, "template_code": tpl.template_code},
        message="模板创建成功",
    )


@router.patch("/work-order-templates/{template_id}", summary="更新工单模板")
async def update_template(
    template_id: str, body: WorkOrderTemplateUpdate, db: AsyncSession = Depends(get_db)
):
    update_data = body.model_dump(exclude_none=True)
    tpl = await service.update_template(db, template_id, **update_data)
    return ok(data={"id": tpl.id, "updated_at": tpl.updated_at}, message="模板更新成功")


@router.post("/work-orders/from-template/{template_id}", summary="从模板创建工单", status_code=201)
async def create_from_template(
    template_id: str, body: CreateFromTemplate, db: AsyncSession = Depends(get_db)
):
    wo = await service.create_from_template(
        db,
        template_id=template_id,
        station_id=body.station_id,
        reported_by=body.reported_by,
        reported_by_name=body.reported_by_name,
        title=body.title,
        description=body.description,
        priority=body.priority,
        device_id=body.device_id,
        device_name=body.device_name,
        device_code=body.device_code,
        scheduled_start=body.scheduled_start,
        scheduled_end=body.scheduled_end,
    )
    return ok(
        data={"id": wo.id, "work_order_no": wo.work_order_no, "status": wo.status},
        message="工单创建成功",
    )



# ── Work Order Statistics ─────────────────────────────────────────────────────

@router.get("/work-orders/statistics/count", summary="工单数量统计")
async def get_count_statistics(
    station_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await service.get_count_statistics(
        db, station_id=station_id, start_date=start_date, end_date=end_date
    )
    return ok(data=data, message="成功")


@router.get("/work-orders/statistics/timeliness", summary="工单时效统计")
async def get_timeliness_statistics(
    station_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await service.get_timeliness_statistics(
        db, station_id=station_id, start_date=start_date, end_date=end_date
    )
    return ok(data=data, message="成功")


@router.get("/work-orders/statistics/performance", summary="人员绩效统计")
async def get_performance_statistics(
    user_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await service.get_performance_statistics(
        db, user_id=user_id, start_date=start_date, end_date=end_date
    )
    return ok(data=data, message="成功")
