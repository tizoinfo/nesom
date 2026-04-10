"""Pydantic schemas for audit log queries."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    user_id: Optional[int]
    username: str
    event_type: str
    resource_type: str
    resource_id: Optional[str]
    action: str
    old_values: Optional[str]
    new_values: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: str
    extra: Optional[str]
    event_time: datetime

    model_config = {"from_attributes": True}
