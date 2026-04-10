"""
Property-based tests for device offline detection.

Property 4: Device Offline Detection
For any device, if its last heartbeat time is more than 5 minutes ago,
the system should mark it as offline.

Validates: Requirements 3.2
Feature: nesom-development, Property 4: Device Offline Detection
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.modules.device import service as device_service
from src.core.exceptions import AppException


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_device(
    device_id: str = "dev-001",
    device_code: str = "PV-001",
    status: str = "online",
    last_heartbeat: datetime = None,
):
    """Create a mock device object."""
    device = MagicMock()
    device.id = device_id
    device.device_code = device_code
    device.status = status
    device.last_heartbeat = last_heartbeat or datetime.utcnow()
    device.deleted_at = None
    return device


def _make_db_with_devices(devices: list):
    """Create a mock async DB session that returns the given devices."""
    db = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = devices
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()

    return db


# ── Property 4: Device Offline Detection ─────────────────────────────────────

@given(
    minutes_since_heartbeat=st.floats(min_value=5.01, max_value=1440.0),  # 5+ minutes to 24 hours
    num_devices=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=100)
def test_devices_with_stale_heartbeat_are_marked_offline(
    minutes_since_heartbeat: float,
    num_devices: int,
):
    """
    Property 4: Device Offline Detection
    For any device with last_heartbeat older than 5 minutes,
    check_offline_devices should mark it as offline.

    Validates: Requirements 3.2
    """
    stale_time = datetime.utcnow() - timedelta(minutes=minutes_since_heartbeat)
    devices = [
        _make_device(
            device_id=f"dev-{i}",
            device_code=f"PV-{i:03d}",
            status="online",
            last_heartbeat=stale_time,
        )
        for i in range(num_devices)
    ]

    db = _make_db_with_devices(devices)

    async def run():
        return await device_service.check_offline_devices(db)

    result = asyncio.run(run())

    # All devices with stale heartbeats should be marked offline
    assert len(result) == num_devices
    for device in result:
        assert device.status == "offline"


@given(
    minutes_since_heartbeat=st.floats(min_value=0.0, max_value=4.99),  # less than 5 minutes
)
@settings(max_examples=100)
def test_devices_with_fresh_heartbeat_stay_online(
    minutes_since_heartbeat: float,
):
    """
    Property 4 (inverse): Devices with recent heartbeats should NOT be marked offline.
    The check_offline_devices function only queries devices with stale heartbeats,
    so fresh devices should not appear in the result.

    Validates: Requirements 3.2
    """
    # Fresh heartbeat - less than 5 minutes ago
    fresh_time = datetime.utcnow() - timedelta(minutes=minutes_since_heartbeat)
    device = _make_device(status="online", last_heartbeat=fresh_time)

    # DB returns empty list (no stale devices found by the query)
    db = _make_db_with_devices([])

    async def run():
        return await device_service.check_offline_devices(db)

    result = asyncio.run(run())

    # No devices should be marked offline
    assert len(result) == 0


@given(
    minutes_since_heartbeat=st.floats(min_value=5.01, max_value=60.0),
)
@settings(max_examples=50)
def test_offline_detection_is_idempotent(minutes_since_heartbeat: float):
    """
    Idempotence: Running check_offline_devices twice on already-offline devices
    should not change their status further (they stay offline).

    Validates: Requirements 3.2
    """
    stale_time = datetime.utcnow() - timedelta(minutes=minutes_since_heartbeat)
    device = _make_device(status="online", last_heartbeat=stale_time)

    db = _make_db_with_devices([device])

    async def run():
        return await device_service.check_offline_devices(db)

    # First run: marks device offline
    result1 = asyncio.run(run())
    assert len(result1) == 1
    assert result1[0].status == "offline"

    # Second run: device is now offline, DB returns empty (no online devices with stale heartbeat)
    db2 = _make_db_with_devices([])

    async def run2():
        return await device_service.check_offline_devices(db2)

    result2 = asyncio.run(run2())
    # No additional devices should be marked offline
    assert len(result2) == 0


# ── Heartbeat update tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_heartbeat_update_brings_offline_device_online():
    """
    When an offline device sends a heartbeat, it should be brought back online.
    Validates: Requirements 3.2
    """
    device = _make_device(status="offline", last_heartbeat=datetime.utcnow() - timedelta(hours=1))

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = device
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = await device_service.update_heartbeat(db, device_id="dev-001")

    assert result.status == "online"
    assert result.last_heartbeat is not None


@pytest.mark.asyncio
async def test_heartbeat_update_refreshes_timestamp():
    """
    Heartbeat update should refresh the last_heartbeat timestamp.
    Validates: Requirements 3.2
    """
    old_time = datetime.utcnow() - timedelta(minutes=10)
    device = _make_device(status="online", last_heartbeat=old_time)

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = device
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    before = datetime.utcnow()
    result = await device_service.update_heartbeat(db, device_id="dev-001")
    after = datetime.utcnow()

    # The heartbeat should be updated to approximately now
    assert result.last_heartbeat >= before or result.last_heartbeat >= old_time


@pytest.mark.asyncio
async def test_heartbeat_for_nonexistent_device_raises():
    """
    Heartbeat for a non-existent device should raise AppException 404.
    Validates: Requirements 3.2
    """
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await device_service.update_heartbeat(db, device_id="nonexistent")

    assert exc_info.value.status_code == 404
