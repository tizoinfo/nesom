"""Business logic for Device monitoring module."""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import redis.asyncio as aioredis
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.core.exceptions import AppException
from .models import Device, DeviceAlert, DeviceMetric, DeviceThreshold, DeviceType
from .schemas import ALLOWED_TRANSITIONS

REALTIME_CACHE_TTL = 5  # seconds


def _redis_client() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


# ── DeviceType helpers ────────────────────────────────────────────────────────

async def get_device_type(db: AsyncSession, type_id: str) -> DeviceType:
    result = await db.execute(select(DeviceType).where(DeviceType.id == type_id))
    dt = result.scalar_one_or_none()
    if not dt:
        raise AppException(status_code=400, message="设备类型不存在")
    return dt


async def list_device_types(db: AsyncSession) -> List[DeviceType]:
    result = await db.execute(select(DeviceType).order_by(DeviceType.sort_order))
    return list(result.scalars().all())


# ── Device CRUD ───────────────────────────────────────────────────────────────

async def list_devices(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    station_id: Optional[str] = None,
    status: Optional[str] = None,
    device_type_id: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[Device], int]:
    stmt = select(Device).where(Device.deleted_at.is_(None))

    if station_id:
        stmt = stmt.where(Device.station_id == station_id)
    if status:
        stmt = stmt.where(Device.status == status)
    if device_type_id:
        stmt = stmt.where(Device.device_type_id == device_type_id)
    if search:
        stmt = stmt.where(
            or_(
                Device.device_code.ilike(f"%{search}%"),
                Device.device_name.ilike(f"%{search}%"),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        stmt.options(selectinload(Device.device_type))
        .offset(offset)
        .limit(page_size)
        .order_by(Device.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_device(db: AsyncSession, device_id: str) -> Device:
    result = await db.execute(
        select(Device)
        .where(Device.id == device_id, Device.deleted_at.is_(None))
        .options(selectinload(Device.device_type))
    )
    device = result.scalar_one_or_none()
    if not device:
        raise AppException(status_code=404, message="设备不存在")
    return device


async def create_device(
    db: AsyncSession,
    device_code: str,
    device_name: str,
    device_type_id: str,
    station_id: str,
    status: str = "offline",
    **kwargs,
) -> Device:
    # Validate device type exists
    await get_device_type(db, device_type_id)

    # Check uniqueness within station
    existing = await db.execute(
        select(Device).where(
            Device.station_id == station_id,
            Device.device_code == device_code,
            Device.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise AppException(status_code=409, message="设备编码在该场站内已存在")

    device = Device(
        id=str(uuid.uuid4()),
        device_code=device_code,
        device_name=device_name,
        device_type_id=device_type_id,
        station_id=station_id,
        status=status,
        **kwargs,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def update_device(
    db: AsyncSession,
    device_id: str,
    **kwargs,
) -> Device:
    device = await get_device(db, device_id)

    # Validate status transition if status is being changed
    new_status = kwargs.get("status")
    if new_status and new_status != device.status:
        allowed = ALLOWED_TRANSITIONS.get(device.status, set())
        if new_status not in allowed:
            raise AppException(
                status_code=422,
                message=f"不允许从 {device.status} 转换到 {new_status}",
            )

    for key, value in kwargs.items():
        if value is not None:
            setattr(device, key, value)

    await db.commit()
    await db.refresh(device)
    return device


async def delete_device(db: AsyncSession, device_id: str, force: bool = False) -> None:
    device = await get_device(db, device_id)

    if device.status == "online":
        raise AppException(status_code=409, message="设备在线，无法删除")

    # Soft delete
    device.deleted_at = datetime.utcnow()
    await db.commit()


# ── Heartbeat ─────────────────────────────────────────────────────────────────

async def update_heartbeat(db: AsyncSession, device_id: str, timestamp: Optional[datetime] = None) -> Device:
    device = await get_device(db, device_id)
    device.last_heartbeat = timestamp or datetime.utcnow()

    # If device was offline, bring it online
    if device.status == "offline":
        device.status = "online"

    await db.commit()
    await db.refresh(device)
    return device


async def check_offline_devices(db: AsyncSession) -> List[Device]:
    """Mark devices as offline if heartbeat is older than 5 minutes."""
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    result = await db.execute(
        select(Device).where(
            Device.status == "online",
            Device.last_heartbeat < cutoff,
            Device.deleted_at.is_(None),
        )
    )
    devices = list(result.scalars().all())
    for device in devices:
        device.status = "offline"
    if devices:
        await db.commit()
    return devices


# ── Metrics ───────────────────────────────────────────────────────────────────

async def get_realtime_metrics(
    db: AsyncSession,
    device_id: str,
    metric_types: Optional[List[str]] = None,
) -> List[DeviceMetric]:
    """Get the latest metric reading for each metric type, with Redis cache."""
    # Ensure device exists
    device = await get_device(db, device_id)

    # Try Redis cache first
    cache_key = f"device:{device_id}:realtime"
    try:
        r = _redis_client()
        cached = await r.get(cache_key)
        await r.aclose()
        if cached:
            # Return cached data as mock metric objects
            cached_data = json.loads(cached)
            metrics = []
            for item in cached_data:
                if metric_types and item["metric_type"] not in metric_types:
                    continue
                m = DeviceMetric(
                    device_id=device_id,
                    metric_type=item["metric_type"],
                    metric_value=item["metric_value"],
                    metric_unit=item["metric_unit"],
                    quality=item.get("quality", 100),
                    collected_at=datetime.fromisoformat(item["collected_at"]),
                )
                metrics.append(m)
            return metrics
    except Exception:
        pass

    # Subquery: latest collected_at per metric_type for this device
    subq = (
        select(
            DeviceMetric.metric_type,
            func.max(DeviceMetric.collected_at).label("max_collected"),
        )
        .where(DeviceMetric.device_id == device_id)
        .group_by(DeviceMetric.metric_type)
    )
    if metric_types:
        subq = subq.where(DeviceMetric.metric_type.in_(metric_types))
    subq = subq.subquery()

    stmt = select(DeviceMetric).join(
        subq,
        and_(
            DeviceMetric.device_id == device_id,
            DeviceMetric.metric_type == subq.c.metric_type,
            DeviceMetric.collected_at == subq.c.max_collected,
        ),
    )
    result = await db.execute(stmt)
    metrics = list(result.scalars().all())

    # Cache the result
    try:
        r = _redis_client()
        cache_data = [
            {
                "metric_type": m.metric_type,
                "metric_value": float(m.metric_value),
                "metric_unit": m.metric_unit,
                "quality": m.quality,
                "collected_at": m.collected_at.isoformat(),
            }
            for m in metrics
        ]
        await r.setex(cache_key, REALTIME_CACHE_TTL, json.dumps(cache_data))
        await r.aclose()
    except Exception:
        pass

    return metrics


async def get_historical_metrics(
    db: AsyncSession,
    device_id: str,
    metric_type: str,
    start_time: datetime,
    end_time: datetime,
    aggregation: Optional[str] = None,
    limit: int = 1000,
) -> List[DeviceMetric]:
    """Get historical metrics for a device within a time range."""
    await get_device(db, device_id)

    stmt = (
        select(DeviceMetric)
        .where(
            DeviceMetric.device_id == device_id,
            DeviceMetric.metric_type == metric_type,
            DeviceMetric.collected_at >= start_time,
            DeviceMetric.collected_at <= end_time,
        )
        .order_by(DeviceMetric.collected_at)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_metric(
    db: AsyncSession,
    device_id: str,
    metric_type: str,
    metric_value: float,
    metric_unit: str,
    quality: int = 100,
    collected_at: Optional[datetime] = None,
    source: str = "direct",
) -> DeviceMetric:
    await get_device(db, device_id)
    metric = DeviceMetric(
        device_id=device_id,
        metric_type=metric_type,
        metric_value=metric_value,
        metric_unit=metric_unit,
        quality=quality,
        collected_at=collected_at or datetime.utcnow(),
        source=source,
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


# ── Alerts ────────────────────────────────────────────────────────────────────

async def list_alerts(
    db: AsyncSession,
    device_id: str,
    status: Optional[str] = None,
    alert_level: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[DeviceAlert], int]:
    await get_device(db, device_id)

    stmt = select(DeviceAlert).where(DeviceAlert.device_id == device_id)
    if status:
        stmt = stmt.where(DeviceAlert.status == status)
    if alert_level:
        stmt = stmt.where(DeviceAlert.alert_level == alert_level)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(desc(DeviceAlert.start_time)).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_alert(db: AsyncSession, device_id: str, alert_id: int) -> DeviceAlert:
    result = await db.execute(
        select(DeviceAlert).where(
            DeviceAlert.id == alert_id,
            DeviceAlert.device_id == device_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise AppException(status_code=404, message="告警不存在")
    return alert


async def create_alert(
    db: AsyncSession,
    device_id: str,
    alert_type: str,
    alert_level: str,
    alert_title: str,
    alert_message: str,
    trigger_value: Optional[float] = None,
    threshold_value: Optional[float] = None,
    alert_data: Optional[dict] = None,
) -> DeviceAlert:
    device = await get_device(db, device_id)
    now = datetime.utcnow()
    alert_code = f"ALERT-{device.device_code}-{now.strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"

    alert = DeviceAlert(
        device_id=device_id,
        alert_code=alert_code,
        alert_type=alert_type,
        alert_level=alert_level,
        alert_title=alert_title,
        alert_message=alert_message,
        trigger_value=trigger_value,
        threshold_value=threshold_value,
        alert_data=alert_data,
        start_time=now,
        status="active",
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def acknowledge_alert(
    db: AsyncSession,
    device_id: str,
    alert_id: int,
    acknowledged_by: str,
    acknowledged_by_name: str,
    notes: Optional[str] = None,
) -> DeviceAlert:
    alert = await get_alert(db, device_id, alert_id)
    if alert.status != "active":
        raise AppException(status_code=400, message="只有活跃告警可以确认")

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = acknowledged_by
    alert.acknowledged_by_name = acknowledged_by_name
    if notes:
        alert.resolution_notes = notes

    await db.commit()
    await db.refresh(alert)
    return alert


async def resolve_alert(
    db: AsyncSession,
    device_id: str,
    alert_id: int,
    resolved_by: str,
    resolved_by_name: str,
    resolution_notes: str,
) -> DeviceAlert:
    alert = await get_alert(db, device_id, alert_id)
    if alert.status not in ("active", "acknowledged"):
        raise AppException(status_code=400, message="只有活跃或已确认的告警可以解决")

    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = resolved_by
    alert.resolved_by_name = resolved_by_name
    alert.resolution_notes = resolution_notes
    alert.end_time = datetime.utcnow()

    await db.commit()
    await db.refresh(alert)
    return alert


# ── Threshold-based alert checking ───────────────────────────────────────────

async def check_thresholds_and_alert(
    db: AsyncSession,
    device_id: str,
    metric_type: str,
    metric_value: float,
) -> Optional[DeviceAlert]:
    """Check if a metric value exceeds thresholds and create an alert if needed."""
    # Get applicable threshold (device-level first, then type-level)
    device = await get_device(db, device_id)

    threshold_result = await db.execute(
        select(DeviceThreshold).where(
            DeviceThreshold.device_id == device_id,
            DeviceThreshold.metric_type == metric_type,
            DeviceThreshold.is_enabled == True,
        )
    )
    threshold = threshold_result.scalar_one_or_none()

    if not threshold:
        # Try device-type level
        threshold_result = await db.execute(
            select(DeviceThreshold).where(
                DeviceThreshold.device_type_id == device.device_type_id,
                DeviceThreshold.device_id.is_(None),
                DeviceThreshold.metric_type == metric_type,
                DeviceThreshold.is_enabled == True,
            )
        )
        threshold = threshold_result.scalar_one_or_none()

    if not threshold:
        return None

    # Determine alert level
    alert_level = None
    threshold_val = None

    if threshold.threshold_type == "max":
        if threshold.critical_value and metric_value >= threshold.critical_value:
            alert_level = "critical"
            threshold_val = threshold.critical_value
        elif threshold.error_value and metric_value >= threshold.error_value:
            alert_level = "error"
            threshold_val = threshold.error_value
        elif threshold.warning_value and metric_value >= threshold.warning_value:
            alert_level = "warning"
            threshold_val = threshold.warning_value
    elif threshold.threshold_type == "min":
        if threshold.critical_value and metric_value <= threshold.critical_value:
            alert_level = "critical"
            threshold_val = threshold.critical_value
        elif threshold.error_value and metric_value <= threshold.error_value:
            alert_level = "error"
            threshold_val = threshold.error_value
        elif threshold.warning_value and metric_value <= threshold.warning_value:
            alert_level = "warning"
            threshold_val = threshold.warning_value

    if not alert_level:
        return None

    # Check for duplicate active alert (suppress within 5 minutes)
    existing = await db.execute(
        select(DeviceAlert).where(
            DeviceAlert.device_id == device_id,
            DeviceAlert.alert_type == "threshold",
            DeviceAlert.status.in_(["active", "acknowledged"]),
            DeviceAlert.alert_data["metric_type"].as_string() == metric_type,
        )
    )
    if existing.scalar_one_or_none():
        return None  # Suppress duplicate

    return await create_alert(
        db,
        device_id=device_id,
        alert_type="threshold",
        alert_level=alert_level,
        alert_title=f"{metric_type} 超过阈值",
        alert_message=f"设备 {device.device_code} 的 {metric_type} 值 {metric_value} 超过阈值 {threshold_val}",
        trigger_value=metric_value,
        threshold_value=threshold_val,
        alert_data={"metric_type": metric_type},
    )
