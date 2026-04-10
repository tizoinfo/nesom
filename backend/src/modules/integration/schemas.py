"""Pydantic schemas for cross-module integration events."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Alert → Work Order ────────────────────────────────────────────────────────

class AlertToWorkOrderRequest(BaseModel):
    """Request to create a work order from a device alert."""
    device_id: str = Field(...)
    alert_id: int = Field(...)
    station_id: str = Field(...)
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    notes: Optional[str] = None


class AlertToWorkOrderResponse(BaseModel):
    work_order_id: str
    work_order_no: str
    alert_id: int
    device_id: str
    message: str


# ── Inspection → Work Order ───────────────────────────────────────────────────

class InspectionToWorkOrderRequest(BaseModel):
    """Request to create a work order from an inspection task problem."""
    task_id: str = Field(...)
    result_id: Optional[str] = None
    problem_description: str = Field(...)
    station_id: str = Field(default="default")
    priority: Optional[str] = "high"
    notes: Optional[str] = None


class InspectionToWorkOrderResponse(BaseModel):
    work_order_id: str
    work_order_no: str
    task_id: str
    message: str


# ── Work Order → Inventory Deduction ──────────────────────────────────────────

class SparePartItem(BaseModel):
    spare_part_id: str = Field(...)
    warehouse_id: str = Field(...)
    quantity: float = Field(..., gt=0)
    batch_no: Optional[str] = None
    reservation_id: Optional[str] = None


class WorkOrderSparePartRequest(BaseModel):
    """Request to deduct inventory for a work order."""
    work_order_id: str = Field(...)
    items: List[SparePartItem] = Field(..., min_length=1)
    operator_id: str = Field(...)
    operator_name: str = Field(...)
    remarks: Optional[str] = None


class StockChangeItem(BaseModel):
    spare_part_id: str
    warehouse_id: str
    old_stock: float
    new_stock: float
    change: float


class WorkOrderSparePartResponse(BaseModel):
    work_order_id: str
    transaction_ids: List[int]
    stock_changes: List[StockChangeItem]
    message: str
