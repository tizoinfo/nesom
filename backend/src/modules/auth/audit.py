"""Audit logging service with async queue-based writing.

Design reference: docs/06-详细设计/03-用户权限管理/业务逻辑设计.md §3.4
Requirement: 2.5 - 记录所有关键操作的审计日志，保留 180 天
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Optional

from loguru import logger
from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


# ── ORM Model ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """Audit log table - BIGINT PK, recommended monthly partitioning."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )


# ── In-process async queue ────────────────────────────────────────────────────

_audit_queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)


async def _queue_worker(db_factory) -> None:
    """Background coroutine: drain the queue and batch-write to DB."""
    BATCH_SIZE = 50
    FLUSH_INTERVAL = 2.0  # seconds

    while True:
        batch: list[AuditLog] = []
        deadline = asyncio.get_event_loop().time() + FLUSH_INTERVAL

        # Collect up to BATCH_SIZE items within FLUSH_INTERVAL
        while len(batch) < BATCH_SIZE:
            timeout = deadline - asyncio.get_event_loop().time()
            if timeout <= 0:
                break
            try:
                entry = await asyncio.wait_for(_audit_queue.get(), timeout=timeout)
                batch.append(entry)
                _audit_queue.task_done()
            except asyncio.TimeoutError:
                break

        if not batch:
            continue

        try:
            async with db_factory() as session:
                session.add_all(batch)
                await session.commit()
        except Exception as exc:
            logger.error(f"[AuditLog] batch write failed: {exc}")
            # Re-enqueue on failure (best-effort, non-blocking)
            for entry in batch:
                try:
                    _audit_queue.put_nowait(entry)
                except asyncio.QueueFull:
                    logger.warning("[AuditLog] queue full, dropping log entry")


def start_audit_worker(db_factory) -> asyncio.Task:
    """Start the background audit worker task. Call once at app startup."""
    return asyncio.create_task(_queue_worker(db_factory))


# ── Public API ────────────────────────────────────────────────────────────────

def enqueue_audit_log(
    *,
    user_id: Optional[int],
    username: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    extra: Optional[dict] = None,
) -> None:
    """Enqueue an audit log entry for async writing. Non-blocking."""
    entry = AuditLog(
        user_id=user_id,
        username=username,
        event_type=f"{resource_type}.{action}",
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        action=action,
        old_values=json.dumps(old_value, ensure_ascii=False, default=str) if old_value is not None else None,
        new_values=json.dumps(new_value, ensure_ascii=False, default=str) if new_value is not None else None,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        extra=json.dumps(extra, ensure_ascii=False, default=str) if extra is not None else None,
        event_time=datetime.utcnow(),
    )
    try:
        _audit_queue.put_nowait(entry)
    except asyncio.QueueFull:
        logger.warning("[AuditLog] queue full, dropping log entry for %s.%s", resource_type, action)
