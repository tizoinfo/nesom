"""System configuration module database models."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
    Text,
    Index,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class SysConfig(Base):
    """System parameter configuration table."""
    __tablename__ = "sys_config"
    __table_args__ = (
        Index("idx_sys_config_module", "module"),
        Index("idx_sys_config_created", "created_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_type: Mapped[str] = mapped_column(String(20), nullable=False, default="STRING")
    module: Mapped[str] = mapped_column(String(50), nullable=False, default="SYSTEM")
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_sensitive: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_system: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    updated_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)


class SysDict(Base):
    """Dictionary data table."""
    __tablename__ = "sys_dict"
    __table_args__ = (
        Index("idx_sys_dict_type", "dict_type"),
        Index("idx_sys_dict_parent", "parent_id"),
        Index("idx_sys_dict_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dict_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dict_code: Mapped[str] = mapped_column(String(50), nullable=False)
    dict_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dict_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parent_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_system: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class SysNoticeTemplate(Base):
    """Notification template table."""
    __tablename__ = "sys_notice_template"
    __table_args__ = (
        Index("idx_notice_type", "notice_type"),
        Index("idx_notice_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    notice_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title_template: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_html: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
