"""Inspection management module database models."""
from datetime import datetime, date, time
from typing import List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class InspectionPlan(Base):
    __tablename__ = "inspection_plans"
    __table_args__ = (
        Index("idx_plan_status", "status"),
        Index("idx_plan_type", "inspection_type"),
        Index("idx_plan_created_by", "created_by"),
        Index("idx_plan_start_date", "start_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plan_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inspection_type: Mapped[str] = mapped_column(
        Enum("routine", "special", "emergency"), nullable=False, default="routine"
    )
    priority: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical"), nullable=False, default="medium"
    )
    frequency_type: Mapped[str] = mapped_column(
        Enum("daily", "weekly", "monthly", "quarterly", "yearly", "custom"),
        nullable=False, default="weekly",
    )
    frequency_value: Mapped[int] = mapped_column(Integer, default=1)
    frequency_days: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    estimated_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    auto_assign: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assign_strategy: Mapped[str] = mapped_column(
        Enum("round_robin", "skill_based", "location_based", "manual"),
        nullable=False, default="round_robin",
    )
    require_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_gps: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_signature: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        Enum("draft", "active", "paused", "completed", "cancelled"),
        nullable=False, default="draft",
    )
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_by_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    tasks: Mapped[List["InspectionTask"]] = relationship(
        "InspectionTask", back_populates="plan", cascade="all, delete-orphan"
    )


class InspectionTask(Base):
    __tablename__ = "inspection_tasks"
    __table_args__ = (
        Index("idx_task_assigned_status", "assigned_to", "status"),
        Index("idx_task_scheduled_date", "scheduled_date"),
        Index("idx_task_status", "status"),
        Index("idx_task_plan_id", "plan_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspection_plans.id", ondelete="CASCADE"), nullable=False
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    assigned_to_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    scheduled_end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    actual_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "assigned", "in_progress", "completed", "cancelled", "overdue"),
        nullable=False, default="pending",
    )
    completion_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.00)
    total_checkpoints: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_checkpoints: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    problem_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    priority: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical"), nullable=False, default="medium"
    )
    is_offline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    offline_sync_status: Mapped[Optional[str]] = mapped_column(
        Enum("pending", "synced", "conflict", "error"), nullable=True
    )
    last_sync_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    gps_track: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    plan: Mapped["InspectionPlan"] = relationship("InspectionPlan", back_populates="tasks")
    results: Mapped[List["InspectionResult"]] = relationship(
        "InspectionResult", back_populates="task", cascade="all, delete-orphan"
    )


class InspectionResult(Base):
    __tablename__ = "inspection_results"
    __table_args__ = (
        Index("idx_result_task_checkpoint", "task_id", "checkpoint_id"),
        Index("idx_result_completed_time", "completed_time"),
        Index("idx_result_overall_status", "overall_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inspection_tasks.id", ondelete="CASCADE"), nullable=False
    )
    checkpoint_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    device_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    arrived_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    inspector_id: Mapped[str] = mapped_column(String(36), nullable=False)
    inspector_name: Mapped[str] = mapped_column(String(100), nullable=False)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    location_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    check_items: Mapped[list] = mapped_column(JSON, nullable=False)
    overall_status: Mapped[str] = mapped_column(
        Enum("normal", "warning", "fault", "skipped", "na"), nullable=False, default="normal"
    )
    problem_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photos: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    humidity: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_offline: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sync_status: Mapped[str] = mapped_column(
        Enum("pending", "synced", "conflict"), nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    task: Mapped["InspectionTask"] = relationship("InspectionTask", back_populates="results")
