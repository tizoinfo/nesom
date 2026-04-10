"""FastAPI router for Device monitoring module."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok, PaginatedData
from . import service
from .schemas import (
    AlertAcknowledge,
    AlertCreate,
    AlertRead,
    AlertResolve,
    DeviceCreate,
    DeviceDetail,
    DeviceRead,
    DeviceTypeRead,
    DeviceUpdate,
    HeartbeatUpdate,
    MetricCreate,
    MetricRead,
    RealtimeMetricsResponse,
    HistoricalMetricsResponse,
    MetricDataPoint,
)
from .websocket import handle_device_websocket

router = APIRouter()


# ── Device Types ──────────────────────────────────────────────────────────────

@router.get("/device-types", summary="获取设备类型列表")
async def list_device_types(db: AsyncSession = Depends(get_db)):
    types = await service.list_device_types(db)
    return ok(data=[DeviceTypeRead.model_validate(t) for t in types], message="成功")


# ── Devices ───────────────────────────────────────────────────────────────────

@router.get("/devices", summary="获取设备列表")
async def list_devices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    station_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    device_type_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    devices, total = await service.list_devices(
        db,
        page=page,
        page_size=page_size,
        station_id=station_id,
        status=status,
        device_type_id=device_type_id,
        search=search,
    )
    items = [DeviceRead.model_validate(d) for d in devices]
    paginated = PaginatedData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")


@router.get("/devices/{device_id}", summary="获取设备详情")
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    device = await service.get_device(db, device_id)
    return ok(data=DeviceDetail.model_validate(device), message="成功")


@router.post("/devices", summary="创建设备", status_code=201)
async def create_device(body: DeviceCreate, db: AsyncSession = Depends(get_db)):
    device = await service.create_device(
        db,
        device_code=body.device_code,
        device_name=body.device_name,
        device_type_id=body.device_type_id,
        station_id=body.station_id,
        status=body.status,
        manufacturer=body.manufacturer,
        model=body.model,
        serial_number=body.serial_number,
        rated_power=body.rated_power,
        rated_voltage=body.rated_voltage,
        rated_current=body.rated_current,
        parameters=body.parameters,
        installation_date=body.installation_date,
        location_description=body.location_description,
        longitude=body.longitude,
        latitude=body.latitude,
        description=body.description,
        responsible_person_id=body.responsible_person_id,
        responsible_person_name=body.responsible_person_name,
        data_collection_config=body.data_collection_config,
    )
    return ok(
        data={"id": device.id, "device_code": device.device_code, "status": device.status},
        message="设备创建成功",
    )


@router.put("/devices/{device_id}", summary="更新设备")
async def update_device(device_id: str, body: DeviceUpdate, db: AsyncSession = Depends(get_db)):
    update_data = body.model_dump(exclude_none=True)
    device = await service.update_device(db, device_id, **update_data)
    return ok(
        data={"id": device.id, "device_code": device.device_code, "status": device.status},
        message="设备更新成功",
    )


@router.delete("/devices/{device_id}", summary="删除设备", status_code=204)
async def delete_device(
    device_id: str,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_device(db, device_id, force=force)


# ── Heartbeat ─────────────────────────────────────────────────────────────────

@router.post("/devices/{device_id}/heartbeat", summary="更新设备心跳")
async def update_heartbeat(
    device_id: str,
    body: HeartbeatUpdate = HeartbeatUpdate(),
    db: AsyncSession = Depends(get_db),
):
    device = await service.update_heartbeat(db, device_id, timestamp=body.timestamp)
    return ok(
        data={"device_id": device.id, "status": device.status, "last_heartbeat": device.last_heartbeat},
        message="心跳更新成功",
    )


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/devices/{device_id}/metrics/realtime", summary="获取设备实时数据")
async def get_realtime_metrics(
    device_id: str,
    metric_types: Optional[str] = Query(None, description="指标类型，逗号分隔"),
    db: AsyncSession = Depends(get_db),
):
    types_list = metric_types.split(",") if metric_types else None
    device = await service.get_device(db, device_id)
    metrics = await service.get_realtime_metrics(db, device_id, metric_types=types_list)
    response = RealtimeMetricsResponse(
        device_id=device_id,
        device_name=device.device_name,
        collected_at=metrics[0].collected_at if metrics else None,
        metrics=[MetricRead.model_validate(m) for m in metrics],
    )
    return ok(data=response, message="成功")


@router.get("/devices/{device_id}/metrics/historical", summary="查询设备历史数据")
async def get_historical_metrics(
    device_id: str,
    metric_type: str = Query(...),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    aggregation: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
):
    metrics = await service.get_historical_metrics(
        db,
        device_id=device_id,
        metric_type=metric_type,
        start_time=start_time,
        end_time=end_time,
        aggregation=aggregation,
        limit=limit,
    )

    data_points = [
        MetricDataPoint(time=m.collected_at, value=float(m.metric_value), quality=m.quality)
        for m in metrics
    ]

    # Compute summary
    summary = None
    if data_points:
        values = [p.value for p in data_points]
        summary = {
            "avg": sum(values) / len(values),
            "max": max(values),
            "min": min(values),
            "count": float(len(values)),
        }

    unit = metrics[0].metric_unit if metrics else ""
    response = HistoricalMetricsResponse(
        device_id=device_id,
        metric_type=metric_type,
        metric_unit=unit,
        aggregation=aggregation,
        interval=None,
        data=data_points,
        summary=summary,
    )
    return ok(data=response, message="成功")


@router.post("/devices/{device_id}/metrics", summary="提交设备指标数据")
async def create_metric(
    device_id: str,
    body: MetricCreate,
    db: AsyncSession = Depends(get_db),
):
    metric = await service.create_metric(
        db,
        device_id=device_id,
        metric_type=body.metric_type,
        metric_value=body.metric_value,
        metric_unit=body.metric_unit,
        quality=body.quality,
        collected_at=body.collected_at,
        source=body.source,
    )
    # Check thresholds
    await service.check_thresholds_and_alert(db, device_id, body.metric_type, body.metric_value)
    return ok(data={"id": metric.id}, message="指标数据提交成功")


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/devices/{device_id}/alerts", summary="获取设备告警列表")
async def list_alerts(
    device_id: str,
    status: Optional[str] = Query(None),
    alert_level: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    alerts, total = await service.list_alerts(
        db,
        device_id=device_id,
        status=status,
        alert_level=alert_level,
        page=page,
        page_size=page_size,
    )
    items = [AlertRead.model_validate(a) for a in alerts]
    paginated = PaginatedData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")


@router.post("/devices/{device_id}/alerts", summary="创建设备告警", status_code=201)
async def create_alert(
    device_id: str,
    body: AlertCreate,
    db: AsyncSession = Depends(get_db),
):
    alert = await service.create_alert(
        db,
        device_id=device_id,
        alert_type=body.alert_type,
        alert_level=body.alert_level,
        alert_title=body.alert_title,
        alert_message=body.alert_message,
        trigger_value=body.trigger_value,
        threshold_value=body.threshold_value,
        alert_data=body.alert_data,
    )
    return ok(data=AlertRead.model_validate(alert), message="告警创建成功")


@router.post("/devices/{device_id}/alerts/{alert_id}/acknowledge", summary="确认告警")
async def acknowledge_alert(
    device_id: str,
    alert_id: int,
    body: AlertAcknowledge = AlertAcknowledge(),
    db: AsyncSession = Depends(get_db),
):
    alert = await service.acknowledge_alert(
        db,
        device_id=device_id,
        alert_id=alert_id,
        acknowledged_by="system",
        acknowledged_by_name="系统",
        notes=body.notes,
    )
    return ok(
        data={
            "alert_id": alert.id,
            "status": alert.status,
            "acknowledged_at": alert.acknowledged_at,
        },
        message="告警确认成功",
    )


@router.post("/devices/{device_id}/alerts/{alert_id}/resolve", summary="解决告警")
async def resolve_alert(
    device_id: str,
    alert_id: int,
    body: AlertResolve,
    db: AsyncSession = Depends(get_db),
):
    alert = await service.resolve_alert(
        db,
        device_id=device_id,
        alert_id=alert_id,
        resolved_by="system",
        resolved_by_name="系统",
        resolution_notes=body.resolution_notes,
    )
    return ok(
        data={
            "alert_id": alert.id,
            "status": alert.status,
            "resolved_at": alert.resolved_at,
            "resolution_notes": alert.resolution_notes,
        },
        message="告警解决成功",
    )


# ── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws/devices/{device_id}/metrics")
async def websocket_device_metrics(device_id: str, websocket: WebSocket):
    """WebSocket endpoint for real-time device metrics and status push."""
    await handle_device_websocket(device_id, websocket)
