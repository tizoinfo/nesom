"""Inventory management database models for spare part module."""
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    warehouse_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    warehouse_name: Mapped[str] = mapped_column(String(100), nullable=False)
    warehouse_type: Mapped[str] = mapped_column(
        Enum("central", "regional", "field", "virtual"), default="central", nullable=False
    )
    manager_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    manager_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class InventoryDetail(Base):
    """Records every inventory transaction (in/out)."""
    __tablename__ = "inventory_details"
    __table_args__ = (
        Index("idx_inv_spare_warehouse", "spare_part_id", "warehouse_id"),
        Index("idx_inv_transaction_date", "transaction_date"),
        Index("idx_inv_batch", "batch_no"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    spare_part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(
        Enum(
            "purchase_in", "return_in", "transfer_in", "adjust_in", "production_in", "other_in",
            "issue_out", "return_out", "transfer_out", "adjust_out", "scrap_out", "other_out",
        ),
        nullable=False,
    )
    transaction_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    batch_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    work_order_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reference_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    operator_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operator_name: Mapped[str] = mapped_column(String(100), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InventorySnapshot(Base):
    """Real-time inventory per spare-part / warehouse / batch."""
    __tablename__ = "inventory_snapshots"
    __table_args__ = (
        Index("idx_snap_spare_warehouse", "spare_part_id", "warehouse_id"),
        Index("idx_snap_expiry", "expiry_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    spare_part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("spare_parts.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    batch_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("available", "reserved", "quarantine", "frozen"), default="available", nullable=False
    )
    last_transaction_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class InventoryReservation(Base):
    """Tracks stock reservations for work orders."""
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        Index("idx_reservation_spare_status", "spare_part_id", "status"),
        Index("idx_reservation_expires", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    work_order_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    spare_part_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=False
    )
    warehouse_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "fulfilled", "released", "expired"), default="active", nullable=False
    )
    reserve_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
