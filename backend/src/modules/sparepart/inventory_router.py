"""FastAPI router for inventory management endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok, PaginatedData
from . import inventory_service as svc
from .inventory_schemas import (
    InventoryDetailRead,
    InventorySnapshotRead,
    IssueItem,
    IssueRequest,
    IssueResponse,
    ReceiveItem,
    ReceiveRequest,
    ReceiveResponse,
    ReserveRequest,
    ReserveResponse,
    StockChange,
    WarehouseRead,
)

router = APIRouter()


# ── Warehouses ────────────────────────────────────────────────────────────────

@router.get("/warehouses", summary="获取仓库列表")
async def list_warehouses(db: AsyncSession = Depends(get_db)):
    warehouses = await svc.list_warehouses(db)
    return ok(data=[WarehouseRead.model_validate(w) for w in warehouses])


# ── Receive (入库) ────────────────────────────────────────────────────────────

@router.post("/inventory/receive", summary="入库操作", status_code=201)
async def receive_stock(body: ReceiveRequest, db: AsyncSession = Depends(get_db)):
    items = [ReceiveItem(**i.model_dump()) for i in body.items]
    tx_ids, changes = await svc.receive_stock(
        db,
        transaction_type=body.transaction_type,
        items=items,
        operator_id=body.operator_id,
        operator_name=body.operator_name,
        reference_no=body.reference_no,
        remarks=body.remarks,
    )
    return ok(
        data=ReceiveResponse(
            transaction_ids=tx_ids,
            updated_stock=changes,
        ).model_dump(),
        message="入库成功",
    )


# ── Issue (出库) ──────────────────────────────────────────────────────────────

@router.post("/inventory/issue", summary="出库操作", status_code=201)
async def issue_stock(body: IssueRequest, db: AsyncSession = Depends(get_db)):
    items = [IssueItem(**i.model_dump()) for i in body.items]
    tx_ids, changes = await svc.issue_stock(
        db,
        transaction_type=body.transaction_type,
        items=items,
        operator_id=body.operator_id,
        operator_name=body.operator_name,
        work_order_id=body.work_order_id,
        reference_no=body.reference_no,
        remarks=body.remarks,
    )
    return ok(
        data=IssueResponse(
            transaction_ids=tx_ids,
            updated_stock=changes,
        ).model_dump(),
        message="出库成功",
    )


# ── Reserve (预留) ────────────────────────────────────────────────────────────

@router.post("/inventory/reserve", summary="库存预留")
async def reserve_stock(body: ReserveRequest, db: AsyncSession = Depends(get_db)):
    items = [i.model_dump() for i in body.items]
    reservation_id, reserved_items, expires_at = await svc.reserve_stock(
        db,
        work_order_id=body.work_order_id,
        items=items,
        reserve_notes=body.reserve_notes,
    )
    return ok(
        data=ReserveResponse(
            reservation_id=reservation_id,
            reserved_items=reserved_items,
            expires_at=expires_at,
        ).model_dump(),
        message="库存预留成功",
    )


@router.post("/inventory/reserve/{reservation_id}/release", summary="释放库存预留")
async def release_reservation(reservation_id: str, db: AsyncSession = Depends(get_db)):
    await svc.release_reservation(db, reservation_id)
    return ok(message="预留已释放")


# ── Transactions query ────────────────────────────────────────────────────────

@router.get("/inventory/transactions", summary="查询库存事务记录")
async def list_transactions(
    spare_part_id: Optional[str] = Query(None),
    warehouse_id: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    records, total = await svc.list_transactions(
        db,
        spare_part_id=spare_part_id,
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
        page=page,
        page_size=page_size,
    )
    items = [InventoryDetailRead.model_validate(r) for r in records]
    paginated = PaginatedData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated)


# ── Snapshots query ───────────────────────────────────────────────────────────

@router.get("/inventory/snapshots", summary="查询库存快照")
async def list_snapshots(
    spare_part_id: Optional[str] = Query(None),
    warehouse_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    snapshots = await svc.list_snapshots(db, spare_part_id=spare_part_id, warehouse_id=warehouse_id)
    return ok(data=[InventorySnapshotRead.model_validate(s) for s in snapshots])


# ── Alerts (预警) ─────────────────────────────────────────────────────────────

from . import alert_service


@router.get("/alerts/inventory", summary="获取库存预警")
async def get_inventory_alerts(
    alert_type: Optional[str] = Query(None, description="low_stock | near_expiry"),
    severity: Optional[str] = Query(None, description="info | warning | error | critical"),
    db: AsyncSession = Depends(get_db),
):
    alerts = await alert_service.get_all_alerts(db, alert_type=alert_type, severity=severity)
    return ok(data=alerts, message="成功")
