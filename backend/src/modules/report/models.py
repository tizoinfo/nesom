"""Report and statistics module database models."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    data_source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="sql")
    data_source_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    parameter_definitions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    column_definitions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    visualization_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    layout_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    export_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    access_level: Mapped[str] = mapped_column(String(20), nullable=False, default="public")
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ReportExecution(Base):
    __tablename__ = "report_executions"
    __table_args__ = (
        Index("idx_exec_status", "status"),
        Index("idx_exec_start_time", "start_time"),
        Index("idx_exec_template_id", "template_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    template_id: Mapped[str] = mapped_column(String(36), nullable=False)
    schedule_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    execution_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_files: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    executed_by: Mapped[str] = mapped_column(String(36), nullable=False)


class StatisticsCache(Base):
    __tablename__ = "statistics_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    cache_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    parameters_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data_content: Mapped[str] = mapped_column(Text, nullable=False)
    data_size: Mapped[int] = mapped_column(Integer, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_hit_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    computed_by: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
