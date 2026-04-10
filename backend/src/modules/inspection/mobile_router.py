"""Mobile-specific API router for Inspection module - offline sync and result submission."""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok
from . import service
from .mobile_schemas import (
    MobileResultSubmission,
    MobileSyncStatusResponse,
)
from .schemas import InspectionTaskRead

router = APIRouter()


@router.get("/mobile/inspection/tasks", summary="移动端获取巡检任务")
async def get_mobile_tasks(
    status: Optional[str] = Query(None),
    scheduled_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    since: Optional[datetime] = Query(None),
    assigned_to: Optional[str] = Query(None),
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    db: AsyncSession = Depends(get_db),
):
    """Get tasks for mobile client, supports incremental sync via 'since' parameter."""
    tasks, total = await service.list_tasks(
        db, page=1, page_size=limit,
        status=status, assigned_to=assigned_to,
        scheduled_date_gte=scheduled_date,
        scheduled_date_lte=scheduled_date,
    )

    # Filter by updated_at if 'since' is provided (incremental sync)
    if since:
        tasks = [t for t in tasks if t.updated_at and t.updated_at > since]

    items = [InspectionTaskRead.model_validate(t) for t in tasks]
    return ok(
        data={
            "tasks": [item.model_dump() for item in items],
            "sync_info": {
                "server_time": datetime.utcnow().isoformat(),
                "has_more": total > limit,
                "total": total,
            },
        },
        message="成功",
    )


@router.post("/mobile/inspection/results", summary="移动端提交巡检结果")
async def submit_mobile_results(
    body: MobileResultSubmission,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    db: AsyncSession = Depends(get_db),
):
    """Submit inspection results from mobile client, supports offline batch sync."""
    synced_count = 0
    conflict_count = 0
    conflicts = []

    # Group results by task_id
    task_results: dict = {}
    for item in body.results:
        tid = item.task_id
        if tid not in task_results:
            task_results[tid] = []
        task_results[tid].append(item.model_dump())

    for task_id, results in task_results.items():
        # Check for conflicts if sync_token provided
        if body.conflict_resolution == "server_wins":
            # Server wins: check if server has newer data
            task = await service.get_task(db, task_id)
            for r in results:
                local_updated = r.get("updated_at")
                if local_updated and task.updated_at and local_updated < task.updated_at.isoformat():
                    conflict_count += 1
                    conflicts.append({
                        "task_id": task_id,
                        "local_id": r.get("local_id"),
                        "resolution": "server_wins",
                    })
                    continue

        result = await service.submit_results(
            db, task_id, results=results,
            inspector_id="mobile_user",
            inspector_name="移动端用户",
            is_offline=True,
        )
        synced_count += result["submitted_count"]

    return ok(
        data={
            "synced_count": synced_count,
            "conflict_count": conflict_count,
            "conflicts": conflicts,
            "server_time": datetime.utcnow().isoformat(),
        },
        message="巡检结果同步成功",
    )


@router.get("/mobile/inspection/sync-status", summary="离线同步状态检查")
async def get_sync_status(
    device_id: str = Query(...),
    last_sync_time: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Check offline data sync status and detect conflicts."""
    from sqlalchemy import select, func
    from .models import InspectionTask, InspectionResult

    # Count pending sync items
    pending_results = 0
    if last_sync_time:
        q = select(func.count()).where(
            InspectionResult.is_offline == True,
            InspectionResult.sync_status == "pending",
            InspectionResult.updated_at > last_sync_time,
        )
        pending_results = (await db.execute(q)).scalar_one()

    # Count tasks updated since last sync
    pending_tasks = 0
    if last_sync_time:
        q = select(func.count()).where(
            InspectionTask.updated_at > last_sync_time,
        )
        pending_tasks = (await db.execute(q)).scalar_one()

    # Count conflicts
    conflict_q = select(func.count()).where(
        InspectionResult.sync_status == "conflict",
    )
    conflict_count = (await db.execute(conflict_q)).scalar_one()

    return ok(
        data={
            "device_id": device_id,
            "last_sync_time": last_sync_time.isoformat() if last_sync_time else None,
            "pending_changes": {
                "results": pending_results,
                "tasks": pending_tasks,
            },
            "conflict_count": conflict_count,
            "server_time": datetime.utcnow().isoformat(),
            "recommended_action": "review_conflicts" if conflict_count > 0 else "sync",
        },
        message="成功",
    )
