"""Pydantic schemas for Report and statistics module."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Dashboard / Stats response schemas ────────────────────────────────────────

class DeviceStatsSummary(BaseModel):
    total_devices: int = 0
    online_devices: int = 0
    offline_devices: int = 0
    fault_devices: int = 0
    maintenance_devices: int = 0
    avg_availability: float = 0.0
    avg_oee: float = 0.0


class StationDeviceStats(BaseModel):
    station_id: str
    device_count: int = 0
    online_count: int = 0
    offline_count: int = 0
    fault_count: int = 0
    availability: float = 0.0


class DeviceTypeStats(BaseModel):
    device_type_id: str
    device_type_name: str
    device_count: int = 0
    availability: float = 0.0


class DeviceStatsResponse(BaseModel):
    summary: DeviceStatsSummary
    by_station: List[StationDeviceStats] = []
    by_device_type: List[DeviceTypeStats] = []


class WorkOrderStatsSummary(BaseModel):
    total_workorders: int = 0
    completed_workorders: int = 0
    pending_workorders: int = 0
    in_progress_workorders: int = 0
    overdue_workorders: int = 0
    avg_completion_hours: Optional[float] = None
    completion_rate: float = 0.0


class WorkOrderTypeStats(BaseModel):
    work_order_type: str
    count: int = 0
    completed: int = 0
    avg_duration_hours: Optional[float] = None


class WorkOrderPriorityStats(BaseModel):
    priority: str
    count: int = 0
    completed: int = 0


class WorkOrderStatsResponse(BaseModel):
    summary: WorkOrderStatsSummary
    by_type: List[WorkOrderTypeStats] = []
    by_priority: List[WorkOrderPriorityStats] = []


class InspectionStatsSummary(BaseModel):
    total_tasks: int = 0
    completed_tasks: int = 0
    pending_tasks: int = 0
    overdue_tasks: int = 0
    completion_rate: float = 0.0
    problem_count: int = 0


class DashboardKPI(BaseModel):
    device_online_rate: float = 0.0
    workorder_completion_rate: float = 0.0
    inspection_completion_rate: float = 0.0
    active_alerts: int = 0


class DashboardResponse(BaseModel):
    kpi: DashboardKPI
    device_stats: DeviceStatsResponse
    workorder_stats: WorkOrderStatsResponse
    inspection_stats: InspectionStatsSummary
    generated_at: datetime


# ── Report Template schemas ───────────────────────────────────────────────────

class ReportTemplateCreate(BaseModel):
    template_code: str = Field(..., min_length=1, max_length=50)
    template_name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    data_source_type: str = Field(default="sql", max_length=20)
    data_source_config: Dict[str, Any] = Field(default_factory=dict)
    parameter_definitions: List[Dict[str, Any]] = Field(default_factory=list)
    column_definitions: List[Dict[str, Any]] = Field(default_factory=list)
    visualization_config: Dict[str, Any] = Field(default_factory=dict)
    layout_config: Dict[str, Any] = Field(default_factory=dict)
    export_config: Dict[str, Any] = Field(default_factory=dict)
    access_level: str = Field(default="public", max_length=20)


class ReportTemplateUpdate(BaseModel):
    template_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=50)
    data_source_config: Optional[Dict[str, Any]] = None
    parameter_definitions: Optional[List[Dict[str, Any]]] = None
    column_definitions: Optional[List[Dict[str, Any]]] = None
    visualization_config: Optional[Dict[str, Any]] = None
    layout_config: Optional[Dict[str, Any]] = None
    export_config: Optional[Dict[str, Any]] = None
    access_level: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class ReportTemplateRead(BaseModel):
    id: str
    template_code: str
    template_name: str
    category: str
    sub_category: Optional[str] = None
    description: Optional[str] = None
    data_source_type: str
    parameter_definitions: List[Dict[str, Any]] = []
    access_level: str
    created_by: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportTemplateDetail(ReportTemplateRead):
    data_source_config: Dict[str, Any] = {}
    column_definitions: List[Dict[str, Any]] = []
    visualization_config: Dict[str, Any] = {}
    layout_config: Dict[str, Any] = {}
    export_config: Dict[str, Any] = {}
    sort_order: int = 0


# ── Report Query schemas ──────────────────────────────────────────────────────

class ReportQueryRequest(BaseModel):
    template_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=10000)
    enable_cache: bool = True


class ReportQueryColumn(BaseModel):
    field: str
    display_name: str
    data_type: str


class ReportQueryResponse(BaseModel):
    columns: List[ReportQueryColumn] = []
    rows: List[Dict[str, Any]] = []
    summary: Optional[Dict[str, Any]] = None


# ── Report Export schemas ─────────────────────────────────────────────────────

class ReportExportRequest(BaseModel):
    parameters: Dict[str, Any] = Field(default_factory=dict)
    format: str = Field(default="excel")
    options: Dict[str, Any] = Field(default_factory=dict)


class ReportExportResponse(BaseModel):
    task_id: str
    status: str
    message: str
