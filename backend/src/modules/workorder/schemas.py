"""Pydantic schemas for Work Order management module."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


VALID_WORK_ORDER_TYPES = {"repair", "inspection", "maintenance", "fault", "other"}
VALID_STATUSES = {"draft", "pending", "assigned", "in_progress", "pending_review", "completed", "closed", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high", "emergency"}
VALID_EMERGENCY_LEVELS = {"normal", "urgent", "critical"}

# State machine: allowed transitions from each status
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "draft": {"pending", "cancelled"},
    "pending": {"assigned", "cancelled"},
    "assigned": {"in_progress", "cancelled"},
    "in_progress": {"pending_review"},
    "pending_review": {"completed", "in_progress"},
    "completed": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


# ── Work Order schemas ────────────────────────────────────────────────────────

class WorkOrderCreate(BaseModel):
    work_order_type: str = Field(default="repair")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    priority: str = Field(default="medium")
    emergency_level: str = Field(default="normal")
    station_id: str = Field(...)
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    device_code: Optional[str] = None
    reported_by: str = Field(...)
    reported_by_name: str = Field(...)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    estimated_duration: Optional[int] = Field(None, ge=0)
    cost_estimate: Optional[float] = Field(None, ge=0)
    location: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    images: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    tags: Optional[Dict[str, Any]] = None

    @field_validator("work_order_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_WORK_ORDER_TYPES:
            raise ValueError(f"工单类型必须是 {VALID_WORK_ORDER_TYPES} 之一")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in VALID_PRIORITIES:
            raise ValueError(f"优先级必须是 {VALID_PRIORITIES} 之一")
        return v

    @field_validator("emergency_level")
    @classmethod
    def validate_emergency(cls, v: str) -> str:
        if v not in VALID_EMERGENCY_LEVELS:
            raise ValueError(f"紧急程度必须是 {VALID_EMERGENCY_LEVELS} 之一")
        return v


class WorkOrderUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    priority: Optional[str] = None
    emergency_level: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    estimated_duration: Optional[int] = Field(None, ge=0)
    cost_estimate: Optional[float] = Field(None, ge=0)
    location: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    images: Optional[List[str]] = None
    tags: Optional[Dict[str, Any]] = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PRIORITIES:
            raise ValueError(f"优先级必须是 {VALID_PRIORITIES} 之一")
        return v

    @field_validator("emergency_level")
    @classmethod
    def validate_emergency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_EMERGENCY_LEVELS:
            raise ValueError(f"紧急程度必须是 {VALID_EMERGENCY_LEVELS} 之一")
        return v


class WorkOrderRead(BaseModel):
    id: str
    work_order_no: str
    work_order_type: str
    title: str
    status: str
    priority: str
    emergency_level: str
    station_id: str
    device_name: Optional[str] = None
    device_code: Optional[str] = None
    reported_by_name: str
    reported_at: datetime
    assigned_to_name: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    completion_rate: int = 0
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkOrderDetail(WorkOrderRead):
    description: str
    device_id: Optional[str] = None
    reported_by: str
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    cost_estimate: Optional[float] = None
    actual_cost: Optional[float] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    qr_code: Optional[str] = None
    images: Optional[list] = None
    attachments: Optional[list] = None
    tags: Optional[dict] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    details: Optional[List["WorkOrderDetailStep"]] = None
    status_history: Optional[List["StatusHistoryRead"]] = None


class WorkOrderDetailStep(BaseModel):
    id: int
    step_number: int
    step_title: str
    step_description: Optional[str] = None
    performed_by_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    findings: Optional[str] = None
    actions_taken: Optional[str] = None
    quality_check: str = "pending"
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusHistoryRead(BaseModel):
    id: int
    old_status: str
    new_status: str
    changed_by_name: str
    change_reason: Optional[str] = None
    change_notes: Optional[str] = None
    changed_at: datetime

    model_config = {"from_attributes": True}


# ── Status transition schemas ─────────────────────────────────────────────────

class SubmitWorkOrder(BaseModel):
    submit_notes: Optional[str] = None


class AssignWorkOrder(BaseModel):
    assigned_to: str = Field(...)
    assigned_to_name: str = Field(...)
    assign_notes: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None


class StartWorkOrder(BaseModel):
    location: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    start_notes: Optional[str] = None


class SubmitReviewWorkOrder(BaseModel):
    completion_notes: Optional[str] = None
    completion_rate: int = Field(100, ge=0, le=100)
    actual_duration: Optional[int] = Field(None, ge=0)
    images: Optional[List[str]] = None


class ApproveWorkOrder(BaseModel):
    approve_notes: Optional[str] = None
    actual_cost: Optional[float] = Field(None, ge=0)


class CloseWorkOrder(BaseModel):
    close_notes: Optional[str] = None


class CancelWorkOrder(BaseModel):
    cancel_reason: str = Field(..., min_length=1)
    cancel_notes: Optional[str] = None



# ── Work Order Template schemas ───────────────────────────────────────────────

class TemplateStepItem(BaseModel):
    step_title: str = Field(..., min_length=1)
    step_description: Optional[str] = None
    estimated_duration: Optional[int] = Field(None, ge=0)


class WorkOrderTemplateCreate(BaseModel):
    template_code: str = Field(..., min_length=1, max_length=50)
    template_name: str = Field(..., min_length=1, max_length=100)
    work_order_type: str = Field(default="repair")
    device_type_id: Optional[str] = None
    priority: str = Field(default="medium")
    estimated_duration: int = Field(default=60, ge=0)
    cost_estimate: Optional[float] = Field(None, ge=0)
    description_template: str = Field(..., min_length=1)
    steps_template: List[TemplateStepItem]
    required_tools: Optional[List[str]] = None
    required_parts: Optional[List[str]] = None
    safety_instructions: Optional[str] = None
    quality_standards: Optional[str] = None
    created_by: str = Field(...)

    @field_validator("work_order_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"repair", "inspection", "maintenance", "fault"}
        if v not in allowed:
            raise ValueError(f"模板工单类型必须是 {allowed} 之一")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in VALID_PRIORITIES:
            raise ValueError(f"优先级必须是 {VALID_PRIORITIES} 之一")
        return v


class WorkOrderTemplateUpdate(BaseModel):
    template_name: Optional[str] = Field(None, min_length=1, max_length=100)
    priority: Optional[str] = None
    estimated_duration: Optional[int] = Field(None, ge=0)
    cost_estimate: Optional[float] = Field(None, ge=0)
    description_template: Optional[str] = None
    steps_template: Optional[List[TemplateStepItem]] = None
    required_tools: Optional[List[str]] = None
    required_parts: Optional[List[str]] = None
    safety_instructions: Optional[str] = None
    quality_standards: Optional[str] = None
    is_active: Optional[bool] = None


class WorkOrderTemplateRead(BaseModel):
    id: str
    template_code: str
    template_name: str
    work_order_type: str
    device_type_id: Optional[str] = None
    priority: str
    estimated_duration: int
    cost_estimate: Optional[float] = None
    description_template: str
    steps_template: list
    required_tools: Optional[list] = None
    required_parts: Optional[list] = None
    safety_instructions: Optional[str] = None
    quality_standards: Optional[str] = None
    is_active: bool
    used_count: int
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreateFromTemplate(BaseModel):
    station_id: str = Field(...)
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    device_code: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[str] = None
    reported_by: str = Field(...)
    reported_by_name: str = Field(...)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
