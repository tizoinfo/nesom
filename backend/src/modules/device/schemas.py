"""Pydantic schemas for Device monitoring module."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator
import re

# Valid device statuses and transitions
VALID_STATUSES = {"online", "offline", "fault", "maintenance", "testing", "standby"}

# Allowed state transitions: current -> set of allowed targets
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "offline": {"online", "maintenance"},
    "online": {"offline", "fault", "maintenance", "testing"},
    "fault": {"maintenance"},
    "maintenance": {"online", "testing"},
    "testing": {"standby", "online"},
    "standby": {"online", "offline"},
}


# ── DeviceType schemas ────────────────────────────────────────────────────────

class DeviceTypeRead(BaseModel):
    id: str
    type_code: str
    type_name: str
    category: Optional[str] = None
    sub_category: Optional[str] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Device schemas ────────────────────────────────────────────────────────────

class DeviceCreate(BaseModel):
    device_code: str = Field(..., min_length=1, max_length=50)
    device_name: str = Field(..., min_length=1, max_length=100)
    device_type_id: str
    station_id: str
    status: str = Field(default="offline")
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    rated_power: Optional[float] = Field(None, ge=0)
    rated_voltage: Optional[float] = Field(None, ge=0)
    rated_current: Optional[float] = Field(None, ge=0)
    parameters: Optional[Dict[str, Any]] = None
    installation_date: Optional[datetime] = None
    location_description: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    description: Optional[str] = None
    responsible_person_id: Optional[str] = None
    responsible_person_name: Optional[str] = None
    data_collection_config: Optional[Dict[str, Any]] = None

    @field_validator("device_code")
    @classmethod
    def validate_device_code(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError("设备编码只能包含字母、数字、下划线和连字符")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"设备状态必须是 {VALID_STATUSES} 之一")
        return v


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[str] = None
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    rated_power: Optional[float] = Field(None, ge=0)
    parameters: Optional[Dict[str, Any]] = None
    location_description: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    description: Optional[str] = None
    responsible_person_id: Optional[str] = None
    responsible_person_name: Optional[str] = None
    health_score: Optional[int] = Field(None, ge=0, le=100)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"设备状态必须是 {VALID_STATUSES} 之一")
        return v


class DeviceRead(BaseModel):
    id: str
    device_code: str
    device_name: str
    device_type_id: str
    station_id: str
    status: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    rated_power: Optional[float] = None
    health_score: Optional[int] = None
    last_heartbeat: Optional[datetime] = None
    data_collection_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeviceDetail(DeviceRead):
    rated_voltage: Optional[float] = None
    rated_current: Optional[float] = None
    parameters: Optional[Dict[str, Any]] = None
    installation_date: Optional[datetime] = None
    commissioning_date: Optional[datetime] = None
    warranty_period: Optional[int] = None
    warranty_expiry: Optional[datetime] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    location_description: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    altitude: Optional[float] = None
    description: Optional[str] = None
    images: Optional[list] = None
    documents: Optional[list] = None
    qr_code: Optional[str] = None
    responsible_person_id: Optional[str] = None
    responsible_person_name: Optional[str] = None
    data_collection_config: Optional[Dict[str, Any]] = None
    device_type: Optional[DeviceTypeRead] = None


# ── Heartbeat schema ──────────────────────────────────────────────────────────

class HeartbeatUpdate(BaseModel):
    timestamp: Optional[datetime] = None  # defaults to now if not provided


# ── DeviceMetric schemas ──────────────────────────────────────────────────────

class MetricDataPoint(BaseModel):
    time: datetime
    value: float
    quality: int = 100

    model_config = {"from_attributes": True}


class MetricRead(BaseModel):
    metric_type: str
    metric_value: float
    metric_unit: str
    collected_at: datetime
    quality: int

    model_config = {"from_attributes": True}


class RealtimeMetricsResponse(BaseModel):
    device_id: str
    device_name: str
    collected_at: Optional[datetime]
    metrics: List[MetricRead]


class HistoricalMetricsResponse(BaseModel):
    device_id: str
    metric_type: str
    metric_unit: str
    aggregation: Optional[str]
    interval: Optional[str]
    data: List[MetricDataPoint]
    summary: Optional[Dict[str, float]] = None


class MetricCreate(BaseModel):
    metric_type: str
    metric_value: float
    metric_unit: str
    quality: int = Field(default=100, ge=0, le=100)
    collected_at: Optional[datetime] = None
    source: str = "direct"


# ── DeviceAlert schemas ───────────────────────────────────────────────────────

class AlertRead(BaseModel):
    id: int
    device_id: str
    alert_code: str
    alert_type: str
    alert_level: str
    alert_title: str
    alert_message: str
    trigger_value: Optional[float] = None
    threshold_value: Optional[float] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledged_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolved_by_name: Optional[str] = None
    resolution_notes: Optional[str] = None
    related_work_order_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertAcknowledge(BaseModel):
    notes: Optional[str] = None


class AlertResolve(BaseModel):
    resolution_notes: str = Field(..., min_length=1)
    create_work_order: bool = False


class AlertCreate(BaseModel):
    alert_type: str
    alert_level: str = "warning"
    alert_title: str
    alert_message: str
    trigger_value: Optional[float] = None
    threshold_value: Optional[float] = None
    alert_data: Optional[Dict[str, Any]] = None

    @field_validator("alert_level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        allowed = {"info", "warning", "error", "critical"}
        if v not in allowed:
            raise ValueError(f"告警级别必须是 {allowed} 之一")
        return v
