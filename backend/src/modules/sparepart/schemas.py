"""Pydantic schemas for Spare Part management module."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


VALID_STATUSES = {"active", "inactive", "obsolete"}
VALID_ABC = {"A", "B", "C"}

ALLOWED_STATUS_TRANSITIONS: Dict[str, set] = {
    "active": {"inactive", "obsolete"},
    "inactive": {"active", "obsolete"},
    "obsolete": set(),  # terminal state
}


# ── Category schemas ──────────────────────────────────────────────────────────

class SparePartCategoryRead(BaseModel):
    id: str
    category_code: str
    category_name: str
    parent_id: Optional[str] = None
    level: int
    is_leaf: bool
    unit: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


# ── SparePart schemas ─────────────────────────────────────────────────────────

class SparePartCreate(BaseModel):
    spare_part_name: str = Field(..., min_length=1, max_length=200)
    category_id: str
    specification: str = Field(..., min_length=1, max_length=500)
    model: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    unit: str = Field(default="piece", max_length=20)
    unit_weight: Optional[float] = Field(None, ge=0)
    unit_volume: Optional[float] = Field(None, ge=0)
    attributes: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    technical_parameters: Optional[Dict[str, Any]] = None
    applicable_devices: Optional[List[Dict[str, Any]]] = None
    is_consumable: bool = True
    is_controlled: bool = False
    has_serial_number: bool = False
    shelf_life_months: Optional[int] = Field(None, ge=0)
    procurement_lead_time: Optional[int] = Field(None, ge=0)
    min_order_quantity: Optional[float] = Field(None, ge=0)
    economic_order_quantity: Optional[float] = Field(None, ge=0)
    standard_cost: Optional[float] = Field(None, ge=0)
    min_stock_level: Optional[float] = Field(None, ge=0)
    max_stock_level: Optional[float] = Field(None, ge=0)
    safety_stock_level: Optional[float] = Field(None, ge=0)
    abc_classification: Optional[str] = None
    storage_requirements: Optional[Dict[str, Any]] = None

    @field_validator("abc_classification")
    @classmethod
    def validate_abc(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ABC:
            raise ValueError(f"ABC分类必须是 {VALID_ABC} 之一")
        return v


class SparePartUpdate(BaseModel):
    spare_part_name: Optional[str] = Field(None, min_length=1, max_length=200)
    specification: Optional[str] = Field(None, min_length=1, max_length=500)
    model: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)
    unit_weight: Optional[float] = Field(None, ge=0)
    unit_volume: Optional[float] = Field(None, ge=0)
    attributes: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    technical_parameters: Optional[Dict[str, Any]] = None
    applicable_devices: Optional[List[Dict[str, Any]]] = None
    is_consumable: Optional[bool] = None
    is_controlled: Optional[bool] = None
    has_serial_number: Optional[bool] = None
    shelf_life_months: Optional[int] = Field(None, ge=0)
    procurement_lead_time: Optional[int] = Field(None, ge=0)
    min_order_quantity: Optional[float] = Field(None, ge=0)
    economic_order_quantity: Optional[float] = Field(None, ge=0)
    standard_cost: Optional[float] = Field(None, ge=0)
    min_stock_level: Optional[float] = Field(None, ge=0)
    max_stock_level: Optional[float] = Field(None, ge=0)
    safety_stock_level: Optional[float] = Field(None, ge=0)
    abc_classification: Optional[str] = None
    status: Optional[str] = None

    @field_validator("abc_classification")
    @classmethod
    def validate_abc(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ABC:
            raise ValueError(f"ABC分类必须是 {VALID_ABC} 之一")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"状态必须是 {VALID_STATUSES} 之一")
        return v


class SparePartRead(BaseModel):
    id: str
    spare_part_code: str
    spare_part_name: str
    category_id: str
    specification: str
    model: Optional[str] = None
    brand: Optional[str] = None
    unit: str
    status: str
    is_consumable: bool
    is_controlled: bool
    current_stock: float
    available_stock: float
    reserved_stock: float
    min_stock_level: Optional[float] = None
    max_stock_level: Optional[float] = None
    safety_stock_level: Optional[float] = None
    last_purchase_price: Optional[float] = None
    abc_classification: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SparePartDetail(SparePartRead):
    unit_weight: Optional[float] = None
    unit_volume: Optional[float] = None
    attributes: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    technical_parameters: Optional[Dict[str, Any]] = None
    applicable_devices: Optional[List[Dict[str, Any]]] = None
    images: Optional[list] = None
    documents: Optional[list] = None
    qr_code: Optional[str] = None
    has_serial_number: bool = False
    shelf_life_months: Optional[int] = None
    procurement_lead_time: Optional[int] = None
    min_order_quantity: Optional[float] = None
    economic_order_quantity: Optional[float] = None
    standard_cost: Optional[float] = None
    avg_purchase_price: Optional[float] = None
    in_transit_stock: float = 0
    total_value: float = 0
    last_inventory_date: Optional[date] = None
    last_purchase_date: Optional[date] = None
    last_issue_date: Optional[date] = None
    category: Optional[SparePartCategoryRead] = None
