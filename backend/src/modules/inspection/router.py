"""FastAPI router for Inspection management module."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok, PaginatedData
from . import service
from .schemas import (
    InspectionPlanCreate,
    InspectionPlanDetail,
    InspectionPlanRead,
    InspectionPlanUpdate,
    InspectionTaskDetail,
    InspectionTaskRead,
    GenerateTasksRequest,
    StartTaskRequest,
    CompleteTaskRequest,
    ReassignTaskRequest,
    AssignTaskRequest,
    SubmitResultsRequest,
)

router = APIRouter()


# ── Inspection Plan CRUD ──────────────────────────────────────────────────────

@router.get("/inspection/plans", summary="获取巡检计划列表")
async def list_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    inspection_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    plans, total = await service.list_plans(
        db, page=page, page_size=page_size,
        status=status, inspection_type=inspection_type, search=search,
    )
    items = [InspectionPlanRead.model_validate(p) for p in plans]
    paginated = PaginatedData(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")


@router.get("/inspection/plans/{plan_id}", summary="获取巡检计划详情")
async def get_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan = await service.get_plan(db, plan_id)
    return ok(data=InspectionPlanDetail.model_validate(plan), message="成功")


@router.post("/inspection/plans", summary="创建巡检计划", status_code=201)
async def create_plan(body: InspectionPlanCreate, db: AsyncSession = Depends(get_db)):
    plan = await service.create_plan(
        db,
        plan_name=body.plan_name,
        description=body.description,
        inspection_type=body.inspection_type,
        priority=body.priority,
        frequency_type=body.frequency_type,
        frequency_value=body.frequency_value,
        frequency_days=body.frequency_days,
        start_date=body.start_date,
        end_date=body.end_date,
        start_time=body.start_time,
        end_time=body.end_time,
        estimated_duration=body.estimated_duration,
        auto_assign=body.auto_assign,
        assign_strategy=body.assign_strategy,
        require_photo=body.require_photo,
        require_gps=body.require_gps,
        require_signature=body.require_signature,
        created_by=body.created_by,
        created_by_name=body.created_by_name,
    )
    return ok(
        data={"id": plan.id, "plan_code": plan.plan_code, "status": plan.status},
        message="巡检计划创建成功",
    )


@router.put("/inspection/plans/{plan_id}", summary="更新巡检计划")
async def update_plan(
    plan_id: str, body: InspectionPlanUpdate, db: AsyncSession = Depends(get_db)
):
    update_data = body.model_dump(exclude_none=True)
    plan = await service.update_plan(db, plan_id, **update_data)
    return ok(data={"id": plan.id, "updated_at": plan.updated_at}, message="巡检计划更新成功")


@router.delete("/inspection/plans/{plan_id}", summary="删除巡检计划")
async def delete_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    await service.delete_plan(db, plan_id)
    return ok(message="巡检计划删除成功")


@router.post("/inspection/plans/{plan_id}/activate", summary="激活巡检计划")
async def activate_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan = await service.transition_plan_status(db, plan_id, "active")
    return ok(data={"id": plan.id, "status": plan.status}, message="巡检计划已激活")


@router.post("/inspection/plans/{plan_id}/pause", summary="暂停巡检计划")
async def pause_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan = await service.transition_plan_status(db, plan_id, "paused")
    return ok(data={"id": plan.id, "status": plan.status}, message="巡检计划已暂停")


@router.post("/inspection/plans/{plan_id}/resume", summary="恢复巡检计划")
async def resume_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan = await service.transition_plan_status(db, plan_id, "active")
    return ok(data={"id": plan.id, "status": plan.status}, message="巡检计划已恢复")


@router.post("/inspection/plans/{plan_id}/complete", summary="完成巡检计划")
async def complete_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan = await service.transition_plan_status(db, plan_id, "completed")
    return ok(data={"id": plan.id, "status": plan.status}, message="巡检计划已完成")


@router.post("/inspection/plans/{plan_id}/cancel", summary="取消巡检计划")
async def cancel_plan(plan_id: str, db: AsyncSession = Depends(get_db)):
    plan = await service.transition_plan_status(db, plan_id, "cancelled")
    return ok(data={"id": plan.id, "status": plan.status}, message="巡检计划已取消")


# ── Task Generation ───────────────────────────────────────────────────────────

@router.post("/inspection/plans/{plan_id}/generate-tasks", summary="生成巡检任务")
async def generate_tasks(
    plan_id: str, body: GenerateTasksRequest, db: AsyncSession = Depends(get_db)
):
    result = await service.generate_tasks(
        db, plan_id,
        gen_start=body.start_date,
        gen_end=body.end_date,
        override_existing=body.override_existing,
    )
    return ok(
        data=result,
        message=f"成功生成{result['generated_count']}个巡检任务",
    )


# ── Inspection Task Endpoints ─────────────────────────────────────────────────

@router.get("/inspection/tasks", summary="获取巡检任务列表")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    plan_id: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    scheduled_date_gte: Optional[date] = Query(None),
    scheduled_date_lte: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    tasks, total = await service.list_tasks(
        db, page=page, page_size=page_size,
        status=status, plan_id=plan_id, assigned_to=assigned_to,
        priority=priority, scheduled_date_gte=scheduled_date_gte,
        scheduled_date_lte=scheduled_date_lte, search=search,
    )
    items = [InspectionTaskRead.model_validate(t) for t in tasks]
    paginated = PaginatedData(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")


@router.get("/inspection/tasks/{task_id}", summary="获取巡检任务详情")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await service.get_task(db, task_id)
    return ok(data=InspectionTaskDetail.model_validate(task), message="成功")


@router.post("/inspection/tasks/{task_id}/assign", summary="分配巡检任务")
async def assign_task(
    task_id: str, body: AssignTaskRequest, db: AsyncSession = Depends(get_db)
):
    task = await service.assign_task(
        db, task_id, assigned_to=body.assigned_to, assigned_to_name=body.assigned_to_name,
    )
    return ok(
        data={"task_id": task.id, "assigned_to": task.assigned_to, "assigned_to_name": task.assigned_to_name, "status": task.status},
        message="巡检任务分配成功",
    )


@router.post("/inspection/tasks/{task_id}/start", summary="开始巡检任务")
async def start_task(
    task_id: str, body: StartTaskRequest = StartTaskRequest(), db: AsyncSession = Depends(get_db)
):
    task = await service.start_task(
        db, task_id, is_offline=body.is_offline, notes=body.notes,
    )
    return ok(
        data={"task_id": task.id, "status": task.status, "actual_start_time": task.actual_start_time},
        message="巡检任务开始成功",
    )


@router.post("/inspection/tasks/{task_id}/complete", summary="完成巡检任务")
async def complete_task(
    task_id: str, body: CompleteTaskRequest = CompleteTaskRequest(), db: AsyncSession = Depends(get_db)
):
    task = await service.complete_task(db, task_id, notes=body.notes)
    return ok(
        data={
            "task_id": task.id, "status": task.status,
            "actual_end_time": task.actual_end_time,
            "duration_minutes": task.duration_minutes,
        },
        message="巡检任务完成成功",
    )


@router.put("/inspection/tasks/{task_id}/reassign", summary="重新分配巡检任务")
async def reassign_task(
    task_id: str, body: ReassignTaskRequest, db: AsyncSession = Depends(get_db)
):
    task = await service.reassign_task(
        db, task_id,
        assigned_to=body.assigned_to,
        assigned_to_name=body.assigned_to_name,
        reason=body.reason,
    )
    return ok(
        data={"task_id": task.id, "assigned_to": task.assigned_to, "assigned_to_name": task.assigned_to_name},
        message="巡检任务重新分配成功",
    )


@router.post("/inspection/tasks/{task_id}/cancel", summary="取消巡检任务")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await service.cancel_task(db, task_id)
    return ok(data={"task_id": task.id, "status": task.status}, message="巡检任务已取消")


@router.post("/inspection/tasks/{task_id}/submit", summary="提交巡检结果")
async def submit_results(
    task_id: str, body: SubmitResultsRequest, db: AsyncSession = Depends(get_db)
):
    results_data = [r.model_dump() for r in body.results]
    result = await service.submit_results_with_auto_workorder(
        db, task_id, results=results_data,
        inspector_id="system", inspector_name="系统",
        is_offline=body.is_offline,
    )
    return ok(data=result, message="巡检结果提交成功")


# ── Statistics ────────────────────────────────────────────────────────────────

@router.get("/inspection/stats", summary="获取巡检统计")
async def get_stats(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await service.get_inspection_stats(db, start_date=start_date, end_date=end_date)
    return ok(data=data, message="成功")
