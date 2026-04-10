"""Tests for audit logging service (requirement 2.5)."""
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.auth.audit import enqueue_audit_log, _audit_queue, AuditLog


# ── enqueue_audit_log tests ───────────────────────────────────────────────────

def test_enqueue_puts_entry_in_queue():
    """enqueue_audit_log should add an AuditLog entry to the queue."""
    initial_size = _audit_queue.qsize()
    enqueue_audit_log(
        user_id=1,
        username="admin",
        action="create",
        resource_type="role",
        resource_id="42",
        new_value={"role_code": "ROLE_TEST"},
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    assert _audit_queue.qsize() == initial_size + 1
    # Drain the entry we just added
    entry = _audit_queue.get_nowait()
    _audit_queue.task_done()
    assert isinstance(entry, AuditLog)
    assert entry.username == "admin"
    assert entry.action == "create"
    assert entry.resource_type == "role"
    assert entry.resource_id == "42"
    assert entry.event_type == "role.create"
    assert entry.ip_address == "127.0.0.1"
    assert entry.status == "success"


def test_enqueue_serializes_values_as_json():
    """old_value and new_value should be JSON-serialized strings."""
    enqueue_audit_log(
        user_id=None,
        username="system",
        action="update",
        resource_type="role",
        old_value={"name": "旧名称"},
        new_value={"name": "新名称"},
    )
    entry = _audit_queue.get_nowait()
    _audit_queue.task_done()
    assert json.loads(entry.old_values) == {"name": "旧名称"}
    assert json.loads(entry.new_values) == {"name": "新名称"}


def test_enqueue_none_values_stay_none():
    """When old/new values are None, columns should be None."""
    enqueue_audit_log(
        user_id=5,
        username="user5",
        action="delete",
        resource_type="role",
        resource_id="10",
    )
    entry = _audit_queue.get_nowait()
    _audit_queue.task_done()
    assert entry.old_values is None
    assert entry.new_values is None
    assert entry.extra is None


def test_enqueue_custom_status():
    """Status field should reflect the provided value."""
    enqueue_audit_log(
        user_id=1,
        username="admin",
        action="login",
        resource_type="auth",
        status="failure",
    )
    entry = _audit_queue.get_nowait()
    _audit_queue.task_done()
    assert entry.status == "failure"


def test_enqueue_extra_serialized():
    """Extra dict should be JSON-serialized."""
    enqueue_audit_log(
        user_id=1,
        username="admin",
        action="export",
        resource_type="report",
        extra={"rows": 500, "format": "excel"},
    )
    entry = _audit_queue.get_nowait()
    _audit_queue.task_done()
    assert json.loads(entry.extra) == {"rows": 500, "format": "excel"}


# ── audit_service query tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_audit_logs_returns_paginated():
    """list_audit_logs should return (logs, total) tuple."""
    from src.modules.auth import audit_service

    log = AuditLog(
        id=1,
        user_id=1,
        username="admin",
        event_type="role.create",
        resource_type="role",
        resource_id="1",
        action="create",
        status="success",
        event_time=datetime.utcnow(),
    )

    db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    logs_result = MagicMock()
    logs_result.scalars.return_value.all.return_value = [log]
    db.execute = AsyncMock(side_effect=[count_result, logs_result])

    logs, total = await audit_service.list_audit_logs(db, page=1, page_size=20)
    assert total == 1
    assert len(logs) == 1
    assert logs[0].username == "admin"


@pytest.mark.asyncio
async def test_list_audit_logs_empty():
    """list_audit_logs with no results returns empty list and zero total."""
    from src.modules.auth import audit_service

    db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    logs_result = MagicMock()
    logs_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[count_result, logs_result])

    logs, total = await audit_service.list_audit_logs(db)
    assert total == 0
    assert logs == []
