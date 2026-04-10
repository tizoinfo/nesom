"""Device monitoring module database models."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class DeviceType(Base):
    __tablename__ = "device_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("device_types.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parameter_template: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    maintenance_template: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    devices: Mapped[List["Device"]] = relationship("Device", back_populates="device_type")
    children: Mapped[List["DeviceType"]] = relationship("DeviceType", back_populates="parent")
    parent: Mapped[Optional["DeviceType"]] = relationship(
        "DeviceType", back_populates="children", remote_side="DeviceType.id"
    )


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("station_id", "device_code", name="uk_station_device_code"),
        Index("idx_station_status", "station_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    station_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    device_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("device_types.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_code: Mapped[str] = mapped_column(String(50), nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="offline", nullable=False, index=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rated_power: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    rated_voltage: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    rated_current: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    installation_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    commissioning_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    warranty_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    warranty_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    health_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_maintenance_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_maintenance_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    location_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    altitude: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    images: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    documents: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    qr_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    responsible_person_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    responsible_person_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    data_collection_status: Mapped[str] = mapped_column(String(20), default="disabled", nullable=False)
    data_collection_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    device_type: Mapped["DeviceType"] = relationship("DeviceType", back_populates="devices")
    metrics: Mapped[List["DeviceMetric"]] = relationship("DeviceMetric", back_populates="device")
    alerts: Mapped[List["DeviceAlert"]] = relationship("DeviceAlert", back_populates="device")
    thresholds: Mapped[List["DeviceThreshold"]] = relationship("DeviceThreshold", back_populates="device")


class DeviceMetric(Base):
    __tablename__ = "device_metrics"
    __table_args__ = (
        Index("idx_device_collected", "device_id", "collected_at"),
        Index("idx_collected_at", "collected_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    metric_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quality: Mapped[int] = mapped_column(Integer, default=100)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="direct")
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="metrics")


class DeviceAlert(Base):
    __tablename__ = "device_alerts"
    __table_args__ = (
        Index("idx_device_alert_status", "device_id", "status"),
        Index("idx_alert_start_time", "start_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    alert_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    alert_level: Mapped[str] = mapped_column(
        Enum("info", "warning", "error", "critical"), nullable=False, default="warning", index=True
    )
    alert_title: Mapped[str] = mapped_column(String(200), nullable=False)
    alert_message: Mapped[str] = mapped_column(Text, nullable=False)
    alert_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    trigger_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    threshold_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    acknowledged_by_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    resolved_by_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "acknowledged", "resolved", "closed"),
        nullable=False,
        default="active",
        index=True,
    )
    related_work_order_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    device: Mapped["Device"] = relationship("Device", back_populates="alerts")


class DeviceThreshold(Base):
    __tablename__ = "device_thresholds"
    __table_args__ = (
        UniqueConstraint("device_id", "metric_type", "threshold_type", name="uk_device_metric_threshold"),
        Index("idx_type_metric", "device_type_id", "metric_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=True, index=True
    )
    device_type_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("device_types.id", ondelete="CASCADE"), nullable=True
    )
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)
    threshold_type: Mapped[str] = mapped_column(
        Enum("min", "max", "range", "rate_of_change"), nullable=False, default="max"
    )
    warning_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    error_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    critical_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    device: Mapped[Optional["Device"]] = relationship("Device", back_populates="thresholds")
