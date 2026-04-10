"""Pydantic schemas for inventory management."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Transaction types ─────────────────────────────────────────────────────────

IN_TYPES = {"purchase_in", "return_in", "transfer_in", "adjust_in", "production_in", "other_in"}
OUT_TYPES = {"issue_out", "return_out", "transfer_out", "adjust_out", "scrap_out", "other_out"}
ALL_TRANSACTION_TYPES = IN_TYPES | OUT_TYPES


# ── Receive (入库) ────────────────────────────────────────────────────────────

class ReceiveItem(BaseModel):
    spare_part_id: str
    warehouse_id: str
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(0, ge=0)
    batch_no: Optional[str] = None
    expiry_date: Optional[date] = None

class ReceiveRequest(BaseModel):
    transaction_type: str = Field(default="purchase_in")
    reference_no: Optional[str] = None
    operator_id: str
    operator_name: str
    items: List[ReceiveItem] = Field(..., min_length=1)
    remarks: Optional[str] = None


# ── Issue (出库) ──────────────────────────────────────────────────────────────

class IssueItem(BaseModel):
    spare_part_id: str
    warehouse_id: str
    quantity: float = Field(..., gt=0)
    batch_no: Optional[str] = None
    reservation_id: Optional[str] = None

class IssueRequest(BaseModel):
    transaction_type: str = Field(default="issue_out")
    work_order_id: Optional[str] = None
    reference_no: Optional[str] = None
    operator_id: str
    operator_name: str
    items: List[IssueItem] = Field(..., min_length=1)
    remarks: Optional[str] = None


# ── Reserve (预留) ────────────────────────────────────────────────────────────

class ReserveItem(BaseModel):
    spare_part_id: str
    warehouse_id: str
    quantity: float = Field(..., gt=0)

class ReserveRequest(BaseModel):
    work_order_id: str
    items: List[ReserveItem] = Field(..., min_length=1)
    reserve_notes: Optional[str] = None


# ── Response schemas ──────────────────────────────────────────────────────────

class StockChange(BaseModel):
    spare_part_id: str
    warehouse_id: str
    old_stock: float
    new_stock: float
    change: float

class ReceiveResponse(BaseModel):
    transaction_ids: List[int]
    updated_stock: List[StockChange]

class IssueResponse(BaseModel):
    transaction_ids: List[int]
    updated_stock: List[StockChange]

class ReserveResponse(BaseModel):
    reservation_id: str
    reserved_items: List[Dict[str, Any]]
    expires_at: datetime

class InventoryDetailRead(BaseModel):
    id: int
    transaction_no: str
    spare_part_id: str
    warehouse_id: str
    transaction_type: str
    transaction_date: datetime
    quantity: float
    unit_price: float
    total_amount: float
    batch_no: Optional[str] = None
    expiry_date: Optional[date] = None
    work_order_id: Optional[str] = None
    reference_no: Optional[str] = None
    operator_name: str
    remarks: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class InventorySnapshotRead(BaseModel):
    id: int
    spare_part_id: str
    warehouse_id: str
    batch_no: Optional[str] = None
    quantity: float
    unit_price: float
    total_amount: float
    expiry_date: Optional[date] = None
    status: str
    version: int

    model_config = {"from_attributes": True}

class WarehouseRead(BaseModel):
    id: str
    warehouse_code: str
    warehouse_name: str
    warehouse_type: str
    is_active: bool

    model_config = {"from_attributes": True}
