"""Work order management module database models."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        Index("idx_station_status", "station_id", "status"),
        Index("idx_assigned_status", "assigned_to", "status"),
        Index("idx_reported_at", "reported_at"),
        Index("idx_scheduled_start", "scheduled_start"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    work_order_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    work_order_type: Mapped[str] = mapped_column(
        Enum("repair", "inspection", "maintenance", "fault", "other"),
        nullable=False,
        default="repair",
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("draft", "pending", "assigned", "in_progress", "pending_review", "completed", "closed", "cancelled"),
        nullable=False,
        default="draft",
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "emergency"),
        nullable=False,
        default="medium",
        index=True,
    )
    emergency_level: Mapped[str] = mapped_column(
        Enum("normal", "urgent", "critical"),
        nullable=False,
        default="normal",
    )
    station_id: Mapped[str] = mapped_column(String(36), nullable=False)
    device_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    device_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reported_by: Mapped[str] = mapped_column(String(36), nullable=False)
    reported_by_name: Mapped[str] = mapped_column(String(100), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    assigned_to_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    estimated_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_rate: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    actual_cost: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    qr_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    images: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    attachments: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    details: Mapped[List["WorkOrderDetail"]] = relationship(
        "WorkOrderDetail", back_populates="work_order", cascade="all, delete-orphan"
    )
    status_history: Mapped[List["WorkOrderStatusHistory"]] = relationship(
        "WorkOrderStatusHistory", back_populates="work_order", cascade="all, delete-orphan"
    )


class WorkOrderDetail(Base):
    __tablename__ = "work_order_details"
    __table_args__ = (
        Index("idx_wo_detail_step", "work_order_id", "step_number"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    step_title: Mapped[str] = mapped_column(String(100), nullable=False)
    step_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    performed_by_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actions_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tools_used: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    parts_used: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    before_images: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    after_images: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    test_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_check: Mapped[str] = mapped_column(
        Enum("pass", "fail", "pending"), default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="details")


class WorkOrderStatusHistory(Base):
    __tablename__ = "work_order_status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(36), nullable=False)
    changed_by_name: Mapped[str] = mapped_column(String(100), nullable=False)
    change_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    change_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    work_order: Mapped["WorkOrder"] = relationship("WorkOrder", back_populates="status_history")



class WorkOrderTemplate(Base):
    __tablename__ = "work_order_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    work_order_type: Mapped[str] = mapped_column(
        Enum("repair", "inspection", "maintenance", "fault"),
        nullable=False,
        default="repair",
        index=True,
    )
    device_type_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "emergency"),
        nullable=False,
        default="medium",
    )
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    cost_estimate: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    description_template: Mapped[str] = mapped_column(Text, nullable=False)
    steps_template: Mapped[list] = mapped_column(JSON, nullable=False)
    required_tools: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    required_parts: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    safety_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_standards: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
