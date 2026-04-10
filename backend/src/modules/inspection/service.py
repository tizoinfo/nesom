"""Business logic for Inspection management module."""
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import AppException
from .models import InspectionPlan, InspectionTask, InspectionResult
from .schemas import ALLOWED_PLAN_TRANSITIONS, ALLOWED_TASK_TRANSITIONS


# ── Plan Code Generation ──────────────────────────────────────────────────────

async def _generate_plan_code(db: AsyncSession) -> str:
    """Generate plan code: INSP-PLAN-{YYYYMM}-{seq}"""
    now = datetime.utcnow()
    prefix = f"INSP-PLAN-{now.strftime('%Y%m')}-"
    result = await db.execute(
        select(func.count()).where(InspectionPlan.plan_code.like(f"{prefix}%"))
    )
    count = result.scalar_one()
    return f"{prefix}{str(count + 1).zfill(3)}"


async def _generate_task_code(db: AsyncSession, scheduled_date: date) -> str:
    """Generate task code: TASK-{YYYYMMDD}-{seq}"""
    prefix = f"TASK-{scheduled_date.strftime('%Y%m%d')}-"
    result = await db.execute(
        select(func.count()).where(InspectionTask.task_code.like(f"{prefix}%"))
    )
    count = result.scalar_one()
    return f"{prefix}{str(count + 1).zfill(3)}"


# ── Inspection Plan CRUD ──────────────────────────────────────────────────────

async def list_plans(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    inspection_type: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[InspectionPlan], int]:
    stmt = select(InspectionPlan)

    if status:
        statuses = [s.strip() for s in status.split(",")]
        stmt = stmt.where(InspectionPlan.status.in_(statuses))
    if inspection_type:
        stmt = stmt.where(InspectionPlan.inspection_type == inspection_type)
    if search:
        stmt = stmt.where(
            or_(
                InspectionPlan.plan_name.ilike(f"%{search}%"),
                InspectionPlan.plan_code.ilike(f"%{search}%"),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(desc(InspectionPlan.created_at))
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_plan(db: AsyncSession, plan_id: str) -> InspectionPlan:
    result = await db.execute(
        select(InspectionPlan).where(InspectionPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise AppException(status_code=404, message="巡检计划不存在")
    return plan


async def create_plan(db: AsyncSession, **kwargs) -> InspectionPlan:
    plan_code = await _generate_plan_code(db)
    plan = InspectionPlan(
        id=str(uuid.uuid4()),
        plan_code=plan_code,
        status="draft",
        **kwargs,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan


async def update_plan(db: AsyncSession, plan_id: str, **kwargs) -> InspectionPlan:
    plan = await get_plan(db, plan_id)
    if plan.status in ("completed", "cancelled"):
        raise AppException(status_code=422, message="已完成或已取消的计划不可修改")

    for key, value in kwargs.items():
        if value is not None:
            setattr(plan, key, value)

    await db.flush()
    await db.refresh(plan)
    return plan


async def delete_plan(db: AsyncSession, plan_id: str) -> None:
    plan = await get_plan(db, plan_id)
    if plan.status not in ("draft", "cancelled"):
        raise AppException(status_code=422, message="只有草稿或已取消状态的计划可以删除")
    await db.delete(plan)
    await db.flush()


# ── Plan Status Transitions ───────────────────────────────────────────────────

async def transition_plan_status(
    db: AsyncSession, plan_id: str, target_status: str
) -> InspectionPlan:
    plan = await get_plan(db, plan_id)
    allowed = ALLOWED_PLAN_TRANSITIONS.get(plan.status, set())
    if target_status not in allowed:
        raise AppException(
            status_code=422,
            message=f"不允许从 {plan.status} 转换到 {target_status}",
        )
    plan.status = target_status
    await db.flush()
    await db.refresh(plan)
    return plan


# ── Task Generation ───────────────────────────────────────────────────────────

def _compute_scheduled_dates(
    plan: InspectionPlan, gen_start: date, gen_end: date
) -> List[date]:
    """Compute the list of scheduled dates for a plan within a date range."""
    dates: List[date] = []
    freq = plan.frequency_type
    val = plan.frequency_value or 1
    freq_days = plan.frequency_days or []

    # Clamp to plan's own date range
    effective_start = max(gen_start, plan.start_date)
    effective_end = gen_end
    if plan.end_date:
        effective_end = min(gen_end, plan.end_date)

    if effective_start > effective_end:
        return dates

    if freq == "daily":
        current = effective_start
        while current <= effective_end:
            dates.append(current)
            current += timedelta(days=val)

    elif freq == "weekly":
        # freq_days = list of weekday numbers (1=Mon..7=Sun)
        target_days = freq_days if freq_days else [1]  # default Monday
        current = effective_start
        while current <= effective_end:
            # isoweekday: 1=Mon..7=Sun
            if current.isoweekday() in target_days:
                dates.append(current)
            current += timedelta(days=1)

    elif freq == "monthly":
        # freq_days = list of day-of-month numbers
        target_days = freq_days if freq_days else [1]
        current_month_start = effective_start.replace(day=1)
        while current_month_start <= effective_end:
            for d in target_days:
                try:
                    candidate = current_month_start.replace(day=d)
                except ValueError:
                    continue  # skip invalid days (e.g. Feb 30)
                if effective_start <= candidate <= effective_end:
                    dates.append(candidate)
            # Move to next month
            if current_month_start.month == 12:
                current_month_start = current_month_start.replace(year=current_month_start.year + 1, month=1)
            else:
                current_month_start = current_month_start.replace(month=current_month_start.month + 1)

    elif freq == "quarterly":
        # Generate on first day of each quarter within range
        target_days = freq_days if freq_days else [1]
        quarter_months = [1, 4, 7, 10]
        year = effective_start.year
        while True:
            for qm in quarter_months:
                for d in target_days:
                    try:
                        candidate = date(year, qm, d)
                    except ValueError:
                        continue
                    if effective_start <= candidate <= effective_end:
                        dates.append(candidate)
                    if candidate > effective_end:
                        return sorted(set(dates))
            year += 1
            if date(year, 1, 1) > effective_end:
                break

    elif freq == "yearly":
        target_days = freq_days if freq_days else [1]
        year = effective_start.year
        while True:
            for d in target_days:
                try:
                    candidate = date(year, 1, d)
                except ValueError:
                    continue
                if effective_start <= candidate <= effective_end:
                    dates.append(candidate)
            year += 1
            if date(year, 1, 1) > effective_end:
                break

    elif freq == "custom":
        # freq_days interpreted as interval in days
        interval = val
        current = effective_start
        while current <= effective_end:
            dates.append(current)
            current += timedelta(days=interval)

    return sorted(set(dates))


async def generate_tasks(
    db: AsyncSession, plan_id: str, gen_start: date, gen_end: date, override_existing: bool = False
) -> dict:
    """Generate inspection tasks for a plan within a date range."""
    plan = await get_plan(db, plan_id)
    if plan.status not in ("active", "draft"):
        raise AppException(status_code=422, message="只有草稿或已激活的计划可以生成任务")

    scheduled_dates = _compute_scheduled_dates(plan, gen_start, gen_end)

    generated = []
    skipped = 0

    for sched_date in scheduled_dates:
        if not override_existing:
            # Check if task already exists for this plan + date
            existing = await db.execute(
                select(func.count()).where(
                    InspectionTask.plan_id == plan_id,
                    InspectionTask.scheduled_date == sched_date,
                )
            )
            if existing.scalar_one() > 0:
                skipped += 1
                continue

        task_code = await _generate_task_code(db, sched_date)
        task = InspectionTask(
            id=str(uuid.uuid4()),
            task_code=task_code,
            plan_id=plan_id,
            scheduled_date=sched_date,
            scheduled_start_time=plan.start_time,
            scheduled_end_time=plan.end_time,
            status="pending",
            priority=plan.priority,
        )
        db.add(task)
        generated.append({
            "id": task.id,
            "task_code": task.task_code,
            "scheduled_date": sched_date.isoformat(),
            "status": "pending",
        })

    await db.flush()

    return {
        "generated_count": len(generated),
        "skipped_count": skipped,
        "tasks": generated,
    }


# ── Inspection Task CRUD ──────────────────────────────────────────────────────

async def list_tasks(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    plan_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    priority: Optional[str] = None,
    scheduled_date_gte: Optional[date] = None,
    scheduled_date_lte: Optional[date] = None,
    search: Optional[str] = None,
) -> Tuple[List[InspectionTask], int]:
    stmt = select(InspectionTask)

    if status:
        statuses = [s.strip() for s in status.split(",")]
        stmt = stmt.where(InspectionTask.status.in_(statuses))
    if plan_id:
        stmt = stmt.where(InspectionTask.plan_id == plan_id)
    if assigned_to:
        stmt = stmt.where(InspectionTask.assigned_to == assigned_to)
    if priority:
        stmt = stmt.where(InspectionTask.priority == priority)
    if scheduled_date_gte:
        stmt = stmt.where(InspectionTask.scheduled_date >= scheduled_date_gte)
    if scheduled_date_lte:
        stmt = stmt.where(InspectionTask.scheduled_date <= scheduled_date_lte)
    if search:
        stmt = stmt.where(InspectionTask.task_code.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(desc(InspectionTask.scheduled_date))
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_task(db: AsyncSession, task_id: str) -> InspectionTask:
    result = await db.execute(
        select(InspectionTask)
        .where(InspectionTask.id == task_id)
        .options(selectinload(InspectionTask.results))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise AppException(status_code=404, message="巡检任务不存在")
    return task


async def start_task(db: AsyncSession, task_id: str, **kwargs) -> InspectionTask:
    task = await get_task(db, task_id)
    allowed = ALLOWED_TASK_TRANSITIONS.get(task.status, set())
    if "in_progress" not in allowed:
        raise AppException(status_code=422, message=f"任务状态 {task.status} 不允许开始")

    task.status = "in_progress"
    task.actual_start_time = datetime.utcnow()
    if kwargs.get("is_offline"):
        task.is_offline = True
    if kwargs.get("notes"):
        task.notes = kwargs["notes"]
    await db.flush()
    await db.refresh(task)
    return task


async def complete_task(db: AsyncSession, task_id: str, **kwargs) -> InspectionTask:
    task = await get_task(db, task_id)
    if task.status != "in_progress":
        raise AppException(status_code=422, message="只有进行中的任务可以完成")

    task.status = "completed"
    task.actual_end_time = datetime.utcnow()
    if task.actual_start_time:
        delta = task.actual_end_time - task.actual_start_time
        task.duration_minutes = int(delta.total_seconds() / 60)
    if kwargs.get("notes"):
        task.notes = kwargs["notes"]
    await db.flush()
    await db.refresh(task)
    return task


async def reassign_task(
    db: AsyncSession, task_id: str, assigned_to: str, assigned_to_name: str, reason: Optional[str] = None
) -> InspectionTask:
    task = await get_task(db, task_id)
    if task.status in ("completed", "cancelled"):
        raise AppException(status_code=422, message="已完成或已取消的任务不可重新分配")

    task.assigned_to = assigned_to
    task.assigned_to_name = assigned_to_name
    task.assigned_at = datetime.utcnow()
    if task.status in ("pending", "overdue"):
        task.status = "assigned"
    await db.flush()
    await db.refresh(task)
    return task


async def assign_task(
    db: AsyncSession, task_id: str, assigned_to: str, assigned_to_name: str
) -> InspectionTask:
    """Assign a pending task to a user."""
    task = await get_task(db, task_id)
    if task.status not in ("pending",):
        raise AppException(status_code=422, message=f"只有待分配的任务可以分配，当前状态: {task.status}")

    task.assigned_to = assigned_to
    task.assigned_to_name = assigned_to_name
    task.assigned_at = datetime.utcnow()
    task.status = "assigned"
    await db.flush()
    await db.refresh(task)
    return task


async def check_overdue_tasks(db: AsyncSession) -> List[InspectionTask]:
    """Find assigned tasks past their scheduled date and mark them overdue."""
    today = datetime.utcnow().date()
    result = await db.execute(
        select(InspectionTask).where(
            InspectionTask.status == "assigned",
            InspectionTask.scheduled_date < today,
        )
    )
    tasks = list(result.scalars().all())
    for task in tasks:
        task.status = "overdue"
    if tasks:
        await db.flush()
    return tasks


async def cancel_task(db: AsyncSession, task_id: str) -> InspectionTask:
    task = await get_task(db, task_id)
    allowed = ALLOWED_TASK_TRANSITIONS.get(task.status, set())
    if "cancelled" not in allowed:
        raise AppException(status_code=422, message=f"任务状态 {task.status} 不允许取消")
    task.status = "cancelled"
    await db.flush()
    await db.refresh(task)
    return task


# ── Submit Results ────────────────────────────────────────────────────────────

async def submit_results(
    db: AsyncSession, task_id: str, results: list, inspector_id: str, inspector_name: str,
    is_offline: bool = False,
) -> dict:
    task = await get_task(db, task_id)
    if task.status not in ("in_progress", "assigned"):
        raise AppException(status_code=422, message="只有已分配或进行中的任务可以提交结果")

    if task.status == "assigned":
        task.status = "in_progress"
        task.actual_start_time = datetime.utcnow()

    problem_count = 0
    submitted_count = 0

    for idx, item in enumerate(results):
        result = InspectionResult(
            id=str(uuid.uuid4()),
            task_id=task_id,
            checkpoint_id=item.get("checkpoint_id"),
            sequence=idx + 1,
            arrived_time=item.get("arrived_time"),
            started_time=item.get("started_time"),
            completed_time=item.get("completed_time") or datetime.utcnow(),
            inspector_id=inspector_id,
            inspector_name=inspector_name,
            longitude=item.get("longitude"),
            latitude=item.get("latitude"),
            location_verified=item.get("location_verified", False),
            check_items=item.get("check_items", []),
            overall_status=item.get("overall_status", "normal"),
            problem_description=item.get("problem_description"),
            photos=item.get("photos"),
            temperature=item.get("temperature"),
            humidity=item.get("humidity"),
            notes=item.get("notes"),
            is_offline=is_offline,
            sync_status="synced" if not is_offline else "pending",
        )
        db.add(result)
        submitted_count += 1
        if item.get("overall_status") in ("warning", "fault"):
            problem_count += 1

    task.completed_checkpoints += submitted_count
    task.problem_count += problem_count
    if task.total_checkpoints > 0:
        task.completion_rate = round(
            (task.completed_checkpoints / task.total_checkpoints) * 100, 2
        )

    await db.flush()
    await db.refresh(task)

    return {
        "task_id": task_id,
        "submitted_count": submitted_count,
        "completed_checkpoints": task.completed_checkpoints,
        "completion_rate": float(task.completion_rate),
        "problem_count": task.problem_count,
    }


# ── Statistics ────────────────────────────────────────────────────────────────

async def get_inspection_stats(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    base_where = []
    if start_date:
        base_where.append(InspectionTask.scheduled_date >= start_date)
    if end_date:
        base_where.append(InspectionTask.scheduled_date <= end_date)

    total_q = select(func.count()).where(*base_where) if base_where else select(func.count()).select_from(InspectionTask)
    total = (await db.execute(total_q)).scalar_one()

    completed_q = select(func.count()).where(InspectionTask.status == "completed", *base_where)
    completed = (await db.execute(completed_q)).scalar_one()

    problem_q = select(func.sum(InspectionTask.problem_count)).where(*base_where) if base_where else select(func.sum(InspectionTask.problem_count))
    problem_count = (await db.execute(problem_q)).scalar_one() or 0

    completion_rate = round((completed / total) * 100, 1) if total > 0 else 0.0

    by_status = {}
    for s in ("pending", "assigned", "in_progress", "completed", "cancelled", "overdue"):
        q = select(func.count()).where(InspectionTask.status == s, *base_where)
        by_status[s] = (await db.execute(q)).scalar_one()

    return {
        "overview": {
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": completion_rate,
            "problem_count": int(problem_count),
        },
        "by_status": by_status,
    }


# ── Inspection Problem → Work Order Conversion ────────────────────────────────

async def create_work_order_from_problem(
    db: AsyncSession,
    task: InspectionTask,
    result_item: dict,
    plan: InspectionPlan,
) -> Optional[str]:
    """Create a work order from an inspection problem (fault/warning).
    Returns the work order ID if created, None otherwise.
    """
    from src.modules.workorder.service import create_work_order as create_wo

    overall_status = result_item.get("overall_status", "normal")
    if overall_status not in ("fault",):
        return None

    problem_desc = result_item.get("problem_description", "巡检发现异常")
    checkpoint_id = result_item.get("checkpoint_id", "")

    title = f"巡检异常工单 - {plan.plan_name} - {task.task_code}"
    description = (
        f"巡检任务 {task.task_code} 在检查点 {checkpoint_id} 发现异常。\n"
        f"问题描述: {problem_desc}\n"
        f"巡检计划: {plan.plan_name}\n"
        f"计划日期: {task.scheduled_date}"
    )

    wo = await create_wo(
        db,
        work_order_type="inspection",
        title=title,
        description=description,
        priority="high" if overall_status == "fault" else "medium",
        emergency_level="normal",
        station_id="default",
        reported_by=task.assigned_to or "system",
        reported_by_name=task.assigned_to_name or "巡检系统",
    )
    return wo.id


async def submit_results_with_auto_workorder(
    db: AsyncSession,
    task_id: str,
    results: list,
    inspector_id: str,
    inspector_name: str,
    is_offline: bool = False,
) -> dict:
    """Submit results and auto-create work orders for fault items."""
    task = await get_task(db, task_id)
    plan = await get_plan(db, task.plan_id)

    submit_result = await submit_results(
        db, task_id, results=results,
        inspector_id=inspector_id,
        inspector_name=inspector_name,
        is_offline=is_offline,
    )

    generated_work_orders = 0
    for item in results:
        if item.get("overall_status") == "fault":
            wo_id = await create_work_order_from_problem(db, task, item, plan)
            if wo_id:
                generated_work_orders += 1

    submit_result["generated_work_orders"] = generated_work_orders
    return submit_result
