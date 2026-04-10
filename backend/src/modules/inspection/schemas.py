"""Pydantic schemas for Inspection management module."""
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


VALID_INSPECTION_TYPES = {"routine", "special", "emergency"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_PLAN_STATUSES = {"draft", "active", "paused", "completed", "cancelled"}
VALID_TASK_STATUSES = {"pending", "assigned", "in_progress", "completed", "cancelled", "overdue"}
VALID_FREQUENCY_TYPES = {"daily", "weekly", "monthly", "quarterly", "yearly", "custom"}
VALID_ASSIGN_STRATEGIES = {"round_robin", "skill_based", "location_based", "manual"}

# Plan state machine
ALLOWED_PLAN_TRANSITIONS: Dict[str, set] = {
    "draft": {"active", "cancelled"},
    "active": {"paused", "completed", "cancelled"},
    "paused": {"active", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

# Task state machine
ALLOWED_TASK_TRANSITIONS: Dict[str, set] = {
    "pending": {"assigned", "cancelled"},
    "assigned": {"in_progress", "overdue", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "overdue": {"assigned", "cancelled"},
}


# ── Inspection Plan schemas ───────────────────────────────────────────────────

class InspectionPlanCreate(BaseModel):
    plan_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    inspection_type: str = Field(default="routine")
    priority: str = Field(default="medium")
    frequency_type: str = Field(default="weekly")
    frequency_value: int = Field(default=1, ge=1)
    frequency_days: Optional[List[int]] = None
    start_date: date
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    estimated_duration: Optional[int] = Field(None, ge=0)
    auto_assign: bool = True
    assign_strategy: str = Field(default="round_robin")
    require_photo: bool = True
    require_gps: bool = True
    require_signature: bool = False
    created_by: str = Field(...)
    created_by_name: str = Field(...)

    @field_validator("inspection_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_INSPECTION_TYPES:
            raise ValueError(f"巡检类型必须是 {VALID_INSPECTION_TYPES} 之一")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in VALID_PRIORITIES:
            raise ValueError(f"优先级必须是 {VALID_PRIORITIES} 之一")
        return v

    @field_validator("frequency_type")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        if v not in VALID_FREQUENCY_TYPES:
            raise ValueError(f"频率类型必须是 {VALID_FREQUENCY_TYPES} 之一")
        return v

    @field_validator("assign_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in VALID_ASSIGN_STRATEGIES:
            raise ValueError(f"分配策略必须是 {VALID_ASSIGN_STRATEGIES} 之一")
        return v


class InspectionPlanUpdate(BaseModel):
    plan_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    priority: Optional[str] = None
    frequency_type: Optional[str] = None
    frequency_value: Optional[int] = Field(None, ge=1)
    frequency_days: Optional[List[int]] = None
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    estimated_duration: Optional[int] = Field(None, ge=0)
    auto_assign: Optional[bool] = None
    assign_strategy: Optional[str] = None
    require_photo: Optional[bool] = None
    require_gps: Optional[bool] = None
    require_signature: Optional[bool] = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PRIORITIES:
            raise ValueError(f"优先级必须是 {VALID_PRIORITIES} 之一")
        return v

    @field_validator("frequency_type")
    @classmethod
    def validate_frequency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_FREQUENCY_TYPES:
            raise ValueError(f"频率类型必须是 {VALID_FREQUENCY_TYPES} 之一")
        return v

    @field_validator("assign_strategy")
    @classmethod
    def validate_strategy(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ASSIGN_STRATEGIES:
            raise ValueError(f"分配策略必须是 {VALID_ASSIGN_STRATEGIES} 之一")
        return v


class InspectionPlanRead(BaseModel):
    id: str
    plan_code: str
    plan_name: str
    inspection_type: str
    priority: str
    status: str
    frequency_type: str
    start_date: date
    end_date: Optional[date] = None
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InspectionPlanDetail(InspectionPlanRead):
    description: Optional[str] = None
    frequency_value: int = 1
    frequency_days: Optional[list] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    estimated_duration: Optional[int] = None
    auto_assign: bool = True
    assign_strategy: str = "round_robin"
    require_photo: bool = True
    require_gps: bool = True
    require_signature: bool = False
    created_by: str

    model_config = {"from_attributes": True}


# ── Task generation schemas ───────────────────────────────────────────────────

class GenerateTasksRequest(BaseModel):
    start_date: date
    end_date: date
    override_existing: bool = False


class GenerateTasksResponse(BaseModel):
    generated_count: int
    skipped_count: int
    tasks: List[dict]


# ── Inspection Task schemas ───────────────────────────────────────────────────

class InspectionTaskRead(BaseModel):
    id: str
    task_code: str
    plan_id: str
    scheduled_date: date
    scheduled_start_time: Optional[time] = None
    scheduled_end_time: Optional[time] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    status: str
    priority: str
    total_checkpoints: int = 0
    completed_checkpoints: int = 0
    completion_rate: float = 0.0
    problem_count: int = 0
    is_offline: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class InspectionTaskDetail(InspectionTaskRead):
    assigned_at: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    offline_sync_status: Optional[str] = None
    last_sync_time: Optional[datetime] = None
    gps_track: Optional[list] = None
    notes: Optional[str] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class StartTaskRequest(BaseModel):
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    notes: Optional[str] = None
    is_offline: bool = False


class CompleteTaskRequest(BaseModel):
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    notes: Optional[str] = None
    signature: Optional[str] = None


class ReassignTaskRequest(BaseModel):
    assigned_to: str = Field(...)
    assigned_to_name: str = Field(...)
    reason: Optional[str] = None


class AssignTaskRequest(BaseModel):
    assigned_to: str = Field(...)
    assigned_to_name: str = Field(...)


class SubmitResultItem(BaseModel):
    checkpoint_id: Optional[str] = None
    arrived_time: Optional[datetime] = None
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    location_verified: bool = False
    check_items: List[dict] = Field(default_factory=list)
    overall_status: str = Field(default="normal")
    problem_description: Optional[str] = None
    photos: Optional[List[dict]] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    notes: Optional[str] = None


class SubmitResultsRequest(BaseModel):
    results: List[SubmitResultItem]
    is_offline: bool = False
    sync_token: Optional[str] = None
