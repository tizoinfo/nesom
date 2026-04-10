"""Cross-module integration service.

Implements three core integration flows:
1. Device alert → automatic work order creation
2. Inspection anomaly → automatic work order creation
3. Work order spare part requisition → inventory deduction
"""
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.modules.device import service as device_service
from src.modules.workorder import service as workorder_service
from src.modules.inspection import service as inspection_service
from src.modules.sparepart.inventory_service import issue_stock, IssueItem


# ── 1. Device Alert → Work Order ─────────────────────────────────────────────

async def create_workorder_from_alert(
    db: AsyncSession,
    device_id: str,
    alert_id: int,
    station_id: str,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    assigned_to_name: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Create a work order triggered by a device alert.

    Returns dict with work_order_id, work_order_no, alert_id, device_id.
    """
    # Fetch the device and alert
    device = await device_service.get_device(db, device_id)
    alert = await device_service.get_alert(db, device_id, alert_id)

    if alert.related_work_order_id:
        raise AppException(
            status_code=409,
            message="该告警已关联工单",
            detail={"work_order_id": alert.related_work_order_id},
        )

    # Map alert level to work order priority
    if priority is None:
        level_priority_map = {
            "critical": "emergency",
            "error": "high",
            "warning": "medium",
            "info": "low",
        }
        priority = level_priority_map.get(alert.alert_level, "medium")

    title = f"设备告警工单 - {device.device_name} - {alert.alert_title}"
    description = (
        f"设备告警自动生成工单\n"
        f"设备: {device.device_name} ({device.device_code})\n"
        f"告警: {alert.alert_title}\n"
        f"告警级别: {alert.alert_level}\n"
        f"告警信息: {alert.alert_message}\n"
    )
    if alert.trigger_value is not None:
        description += f"触发值: {alert.trigger_value}\n"
    if alert.threshold_value is not None:
        description += f"阈值: {alert.threshold_value}\n"
    if notes:
        description += f"备注: {notes}\n"

    wo = await workorder_service.create_work_order(
        db,
        work_order_type="fault",
        title=title,
        description=description,
        priority=priority,
        emergency_level="urgent" if priority == "emergency" else "normal",
        station_id=station_id,
        device_id=device_id,
        device_name=device.device_name,
        device_code=device.device_code,
        reported_by="system",
        reported_by_name="告警系统",
    )

    # Link alert to work order
    alert.related_work_order_id = wo.id

    # Auto-submit the work order (draft → pending)
    await workorder_service.submit_work_order(
        db, wo.id, changed_by="system", changed_by_name="告警系统",
        notes="设备告警自动创建并提交",
    )

    # Auto-assign if assignee provided
    if assigned_to and assigned_to_name:
        await workorder_service.assign_work_order(
            db, wo.id,
            assigned_to=assigned_to,
            assigned_to_name=assigned_to_name,
            changed_by="system",
            changed_by_name="告警系统",
            notes="设备告警自动分配",
        )

    await db.commit()

    return {
        "work_order_id": wo.id,
        "work_order_no": wo.work_order_no,
        "alert_id": alert.id,
        "device_id": device_id,
    }


# ── 2. Inspection Anomaly → Work Order ───────────────────────────────────────

async def create_workorder_from_inspection(
    db: AsyncSession,
    task_id: str,
    problem_description: str,
    station_id: str = "default",
    priority: Optional[str] = "high",
    result_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Create a work order from an inspection task anomaly.

    Returns dict with work_order_id, work_order_no, task_id.
    """
    task = await inspection_service.get_task(db, task_id)
    plan = await inspection_service.get_plan(db, task.plan_id)

    title = f"巡检异常工单 - {plan.plan_name} - {task.task_code}"
    description = (
        f"巡检异常自动生成工单\n"
        f"巡检计划: {plan.plan_name}\n"
        f"巡检任务: {task.task_code}\n"
        f"计划日期: {task.scheduled_date}\n"
        f"问题描述: {problem_description}\n"
    )
    if notes:
        description += f"备注: {notes}\n"

    wo = await workorder_service.create_work_order(
        db,
        work_order_type="inspection",
        title=title,
        description=description,
        priority=priority or "high",
        emergency_level="normal",
        station_id=station_id,
        reported_by=task.assigned_to or "system",
        reported_by_name=task.assigned_to_name or "巡检系统",
    )

    # Auto-submit
    await workorder_service.submit_work_order(
        db, wo.id, changed_by="system", changed_by_name="巡检系统",
        notes="巡检异常自动创建并提交",
    )

    await db.commit()

    return {
        "work_order_id": wo.id,
        "work_order_no": wo.work_order_no,
        "task_id": task_id,
    }


# ── 3. Work Order Spare Part Requisition → Inventory Deduction ───────────────

async def deduct_inventory_for_workorder(
    db: AsyncSession,
    work_order_id: str,
    items: list,
    operator_id: str,
    operator_name: str,
    remarks: Optional[str] = None,
) -> dict:
    """Deduct spare part inventory for a work order.

    items: list of dicts with spare_part_id, warehouse_id, quantity,
           optional batch_no and reservation_id.
    Returns dict with work_order_id, transaction_ids, stock_changes.
    """
    # Verify work order exists and is in a valid state for part requisition
    wo = await workorder_service.get_work_order(db, work_order_id)
    if wo.status not in ("assigned", "in_progress"):
        raise AppException(
            status_code=422,
            message="只有已分配或进行中的工单可以领用备件",
            detail={"current_status": wo.status},
        )

    # Build IssueItem list
    issue_items = [
        IssueItem(
            spare_part_id=item["spare_part_id"],
            warehouse_id=item["warehouse_id"],
            quantity=item["quantity"],
            batch_no=item.get("batch_no"),
            reservation_id=item.get("reservation_id"),
        )
        for item in items
    ]

    tx_ids, changes = await issue_stock(
        db,
        transaction_type="issue_out",
        items=issue_items,
        operator_id=operator_id,
        operator_name=operator_name,
        work_order_id=work_order_id,
        reference_no=wo.work_order_no,
        remarks=remarks or f"工单 {wo.work_order_no} 备件领用",
    )

    return {
        "work_order_id": work_order_id,
        "transaction_ids": tx_ids,
        "stock_changes": [
            {
                "spare_part_id": c.spare_part_id,
                "warehouse_id": c.warehouse_id,
                "old_stock": c.old_stock,
                "new_stock": c.new_stock,
                "change": c.change,
            }
            for c in changes
        ],
    }
