"""Mobile-specific Pydantic schemas for Inspection module."""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MobileResultItem(BaseModel):
    task_id: str = Field(...)
    checkpoint_id: Optional[str] = None
    local_id: Optional[str] = None
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
    is_offline: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MobileResultSubmission(BaseModel):
    device_id: Optional[str] = None
    sync_token: Optional[str] = None
    results: List[MobileResultItem]
    conflict_resolution: str = Field(default="server_wins")


class MobileSyncStatusResponse(BaseModel):
    device_id: str
    last_sync_time: Optional[str] = None
    pending_changes: Dict[str, int]
    conflict_count: int
    server_time: str
    recommended_action: str
