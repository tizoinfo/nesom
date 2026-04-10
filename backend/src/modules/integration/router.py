"""FastAPI router for cross-module integration endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok
from . import service
from .schemas import (
    AlertToWorkOrderRequest,
    AlertToWorkOrderResponse,
    InspectionToWorkOrderRequest,
    InspectionToWorkOrderResponse,
    WorkOrderSparePartRequest,
    WorkOrderSparePartResponse,
    StockChangeItem,
)

router = APIRouter(prefix="/integration")


@router.post(
    "/alert-to-workorder",
    summary="设备告警自动创建工单",
    response_model=None,
)
async def alert_to_workorder(
    body: AlertToWorkOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a work order from a device alert.

    Maps alert level to work order priority:
    - critical → emergency
    - error → high
    - warning → medium
    - info → low
    """
    result = await service.create_workorder_from_alert(
        db,
        device_id=body.device_id,
        alert_id=body.alert_id,
        station_id=body.station_id,
        priority=body.priority,
        assigned_to=body.assigned_to,
        assigned_to_name=body.assigned_to_name,
        notes=body.notes,
    )
    return ok(
        data=AlertToWorkOrderResponse(
            work_order_id=result["work_order_id"],
            work_order_no=result["work_order_no"],
            alert_id=result["alert_id"],
            device_id=result["device_id"],
            message="告警工单创建成功",
        ),
        message="告警工单创建成功",
    )


@router.post(
    "/inspection-to-workorder",
    summary="巡检异常自动创建工单",
    response_model=None,
)
async def inspection_to_workorder(
    body: InspectionToWorkOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a work order from an inspection task anomaly."""
    result = await service.create_workorder_from_inspection(
        db,
        task_id=body.task_id,
        problem_description=body.problem_description,
        station_id=body.station_id,
        priority=body.priority,
        result_id=body.result_id,
        notes=body.notes,
    )
    return ok(
        data=InspectionToWorkOrderResponse(
            work_order_id=result["work_order_id"],
            work_order_no=result["work_order_no"],
            task_id=result["task_id"],
            message="巡检异常工单创建成功",
        ),
        message="巡检异常工单创建成功",
    )


@router.post(
    "/workorder-spare-parts",
    summary="工单备件领用（库存扣减）",
    response_model=None,
)
async def workorder_spare_parts(
    body: WorkOrderSparePartRequest,
    db: AsyncSession = Depends(get_db),
):
    """Deduct spare part inventory for a work order."""
    items = [item.model_dump() for item in body.items]
    result = await service.deduct_inventory_for_workorder(
        db,
        work_order_id=body.work_order_id,
        items=items,
        operator_id=body.operator_id,
        operator_name=body.operator_name,
        remarks=body.remarks,
    )
    return ok(
        data=WorkOrderSparePartResponse(
            work_order_id=result["work_order_id"],
            transaction_ids=result["transaction_ids"],
            stock_changes=[
                StockChangeItem(**c) for c in result["stock_changes"]
            ],
            message="备件领用成功",
        ),
        message="备件领用成功",
    )
