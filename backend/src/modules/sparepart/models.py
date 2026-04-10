"""Spare part management module database models."""
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class SparePartCategory(Base):
    __tablename__ = "spare_part_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    category_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("spare_part_categories.id", ondelete="CASCADE"), nullable=True, index=True
    )
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_leaf: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attribute_template: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    storage_requirements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), default="piece", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    spare_parts: Mapped[List["SparePart"]] = relationship("SparePart", back_populates="category")
    children: Mapped[List["SparePartCategory"]] = relationship("SparePartCategory", back_populates="parent")
    parent: Mapped[Optional["SparePartCategory"]] = relationship(
        "SparePartCategory", back_populates="children", remote_side="SparePartCategory.id"
    )


class SparePart(Base):
    __tablename__ = "spare_parts"
    __table_args__ = (
        Index("idx_sp_category", "category_id"),
        Index("idx_sp_status", "status"),
        Index("idx_sp_brand", "brand"),
        Index("idx_sp_model", "model"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    spare_part_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    spare_part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("spare_part_categories.id", ondelete="RESTRICT"), nullable=False
    )
    specification: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), default="piece", nullable=False)
    unit_weight: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    unit_volume: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    attributes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technical_parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    applicable_devices: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    images: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    documents: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    qr_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", "obsolete"), default="active", nullable=False
    )
    is_consumable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_controlled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_serial_number: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shelf_life_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    procurement_lead_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_order_quantity: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    economic_order_quantity: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    standard_cost: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    last_purchase_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    avg_purchase_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    min_stock_level: Mapped[Optional[float]] = mapped_column(Numeric(12, 3), nullable=True)
    max_stock_level: Mapped[Optional[float]] = mapped_column(Numeric(12, 3), nullable=True)
    safety_stock_level: Mapped[Optional[float]] = mapped_column(Numeric(12, 3), nullable=True)
    current_stock: Mapped[float] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    available_stock: Mapped[float] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    reserved_stock: Mapped[float] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    in_transit_stock: Mapped[float] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    total_value: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    abc_classification: Mapped[Optional[str]] = mapped_column(
        Enum("A", "B", "C"), nullable=True
    )
    last_inventory_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    category: Mapped["SparePartCategory"] = relationship("SparePartCategory", back_populates="spare_parts")
