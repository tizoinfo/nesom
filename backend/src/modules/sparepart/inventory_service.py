"""Business logic for inventory management (入库、出库、预留、FIFO)."""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from .models import SparePart
from .inventory_models import (
    InventoryDetail,
    InventoryReservation,
    InventorySnapshot,
    Warehouse,
)
from .inventory_schemas import (
    IN_TYPES,
    OUT_TYPES,
    IssueItem,
    ReceiveItem,
    StockChange,
)


# ── Transaction number generation ─────────────────────────────────────────────

async def _generate_transaction_no(db: AsyncSession, tx_type: str) -> str:
    """Generate unique transaction number: TR-{YYYYMMDD}-{type_prefix}-{seq}."""
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = "IN" if tx_type in IN_TYPES else "OUT"
    pattern = f"TR-{today}-{prefix}-%"

    result = await db.execute(
        select(func.count()).select_from(
            select(InventoryDetail).where(InventoryDetail.transaction_no.like(pattern)).subquery()
        )
    )
    seq = result.scalar_one() + 1
    return f"TR-{today}-{prefix}-{seq:04d}"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_spare_part(db: AsyncSession, spare_part_id: str) -> SparePart:
    result = await db.execute(select(SparePart).where(SparePart.id == spare_part_id))
    sp = result.scalar_one_or_none()
    if not sp:
        raise AppException(status_code=404, message="备件不存在")
    return sp


async def _get_warehouse(db: AsyncSession, warehouse_id: str) -> Warehouse:
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    wh = result.scalar_one_or_none()
    if not wh:
        raise AppException(status_code=404, message="仓库不存在")
    if not wh.is_active:
        raise AppException(status_code=422, message="仓库已停用")
    return wh


async def _get_or_create_snapshot(
    db: AsyncSession,
    spare_part_id: str,
    warehouse_id: str,
    batch_no: Optional[str],
) -> InventorySnapshot:
    """Get existing snapshot row or create a new one."""
    stmt = select(InventorySnapshot).where(
        InventorySnapshot.spare_part_id == spare_part_id,
        InventorySnapshot.warehouse_id == warehouse_id,
    )
    if batch_no:
        stmt = stmt.where(InventorySnapshot.batch_no == batch_no)
    else:
        stmt = stmt.where(InventorySnapshot.batch_no.is_(None))

    result = await db.execute(stmt)
    snap = result.scalar_one_or_none()
    if snap:
        return snap

    snap = InventorySnapshot(
        spare_part_id=spare_part_id,
        warehouse_id=warehouse_id,
        batch_no=batch_no,
        quantity=0,
        unit_price=0,
        total_amount=0,
        status="available",
    )
    db.add(snap)
    await db.flush()
    return snap


async def _update_spare_part_stock(db: AsyncSession, spare_part_id: str) -> None:
    """Recalculate aggregated stock fields on the spare_parts row."""
    result = await db.execute(
        select(
            func.coalesce(func.sum(InventorySnapshot.quantity), 0),
        ).where(
            InventorySnapshot.spare_part_id == spare_part_id,
            InventorySnapshot.status == "available",
        )
    )
    total_available = float(result.scalar_one())

    # reserved stock from active reservations
    res_result = await db.execute(
        select(
            func.coalesce(func.sum(InventoryReservation.quantity), 0),
        ).where(
            InventoryReservation.spare_part_id == spare_part_id,
            InventoryReservation.status == "active",
        )
    )
    total_reserved = float(res_result.scalar_one())

    current_stock = total_available
    available_stock = max(current_stock - total_reserved, 0)

    await db.execute(
        update(SparePart)
        .where(SparePart.id == spare_part_id)
        .values(
            current_stock=current_stock,
            available_stock=available_stock,
            reserved_stock=total_reserved,
        )
    )


# ── Receive (入库) ────────────────────────────────────────────────────────────

async def receive_stock(
    db: AsyncSession,
    transaction_type: str,
    items: List[ReceiveItem],
    operator_id: str,
    operator_name: str,
    reference_no: Optional[str] = None,
    remarks: Optional[str] = None,
) -> Tuple[List[int], List[StockChange]]:
    """Receive stock into warehouse(s). Runs inside a single transaction."""
    if transaction_type not in IN_TYPES:
        raise AppException(status_code=422, message=f"无效的入库类型: {transaction_type}")

    tx_ids: List[int] = []
    changes: List[StockChange] = []

    for item in items:
        sp = await _get_spare_part(db, item.spare_part_id)
        await _get_warehouse(db, item.warehouse_id)

        old_stock = float(sp.current_stock)

        # Create transaction record
        tx_no = await _generate_transaction_no(db, transaction_type)
        total_amount = item.quantity * item.unit_price
        detail = InventoryDetail(
            transaction_no=tx_no,
            spare_part_id=item.spare_part_id,
            warehouse_id=item.warehouse_id,
            transaction_type=transaction_type,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_amount=total_amount,
            batch_no=item.batch_no,
            expiry_date=item.expiry_date,
            operator_id=operator_id,
            operator_name=operator_name,
            reference_no=reference_no,
            remarks=remarks,
        )
        db.add(detail)
        await db.flush()
        tx_ids.append(detail.id)

        # Update snapshot
        snap = await _get_or_create_snapshot(db, item.spare_part_id, item.warehouse_id, item.batch_no)
        snap.quantity = float(snap.quantity) + item.quantity
        snap.unit_price = item.unit_price
        snap.total_amount = float(snap.quantity) * item.unit_price
        snap.last_transaction_date = datetime.utcnow()
        if item.expiry_date:
            snap.expiry_date = item.expiry_date

        # Recalculate spare part aggregate
        await _update_spare_part_stock(db, item.spare_part_id)

        sp_refreshed = await _get_spare_part(db, item.spare_part_id)
        changes.append(StockChange(
            spare_part_id=item.spare_part_id,
            warehouse_id=item.warehouse_id,
            old_stock=old_stock,
            new_stock=float(sp_refreshed.current_stock),
            change=item.quantity,
        ))

    await db.commit()
    return tx_ids, changes


# ── Issue (出库) with FIFO ────────────────────────────────────────────────────

async def issue_stock(
    db: AsyncSession,
    transaction_type: str,
    items: List[IssueItem],
    operator_id: str,
    operator_name: str,
    work_order_id: Optional[str] = None,
    reference_no: Optional[str] = None,
    remarks: Optional[str] = None,
) -> Tuple[List[int], List[StockChange]]:
    """Issue stock from warehouse(s). Uses FIFO allocation. Atomic transaction."""
    if transaction_type not in OUT_TYPES:
        raise AppException(status_code=422, message=f"无效的出库类型: {transaction_type}")

    tx_ids: List[int] = []
    changes: List[StockChange] = []

    for item in items:
        sp = await _get_spare_part(db, item.spare_part_id)
        await _get_warehouse(db, item.warehouse_id)

        old_stock = float(sp.current_stock)

        # Check available stock
        if float(sp.available_stock) < item.quantity:
            raise AppException(
                status_code=422,
                message=f"备件 {sp.spare_part_code} 可用库存不足",
                detail={
                    "spare_part_code": sp.spare_part_code,
                    "available_stock": float(sp.available_stock),
                    "requested_quantity": item.quantity,
                },
            )

        # FIFO allocation from snapshots
        remaining = item.quantity
        if item.batch_no:
            # Specific batch requested
            snap = await _get_or_create_snapshot(db, item.spare_part_id, item.warehouse_id, item.batch_no)
            if float(snap.quantity) < remaining:
                raise AppException(status_code=422, message=f"批次 {item.batch_no} 库存不足")
            snap.quantity = float(snap.quantity) - remaining
            snap.total_amount = float(snap.quantity) * float(snap.unit_price)
            unit_price = float(snap.unit_price)
            remaining = 0
        else:
            # FIFO: oldest batches first (by last_transaction_date)
            stmt = (
                select(InventorySnapshot)
                .where(
                    InventorySnapshot.spare_part_id == item.spare_part_id,
                    InventorySnapshot.warehouse_id == item.warehouse_id,
                    InventorySnapshot.quantity > 0,
                    InventorySnapshot.status == "available",
                )
                .order_by(InventorySnapshot.last_transaction_date.asc())
            )
            result = await db.execute(stmt)
            snapshots = list(result.scalars().all())

            unit_price = 0.0
            total_cost = 0.0
            for snap in snapshots:
                if remaining <= 0:
                    break
                take = min(float(snap.quantity), remaining)
                total_cost += take * float(snap.unit_price)
                snap.quantity = float(snap.quantity) - take
                snap.total_amount = float(snap.quantity) * float(snap.unit_price)
                remaining -= take

            if remaining > 0:
                raise AppException(status_code=422, message=f"仓库库存不足，无法完成出库")
            unit_price = total_cost / item.quantity if item.quantity else 0

        # Fulfill reservation if provided
        if item.reservation_id:
            res_result = await db.execute(
                select(InventoryReservation).where(
                    InventoryReservation.id == item.reservation_id,
                    InventoryReservation.status == "active",
                )
            )
            reservation = res_result.scalar_one_or_none()
            if reservation:
                reservation.status = "fulfilled"

        # Create transaction record
        tx_no = await _generate_transaction_no(db, transaction_type)
        total_amount = item.quantity * unit_price
        detail = InventoryDetail(
            transaction_no=tx_no,
            spare_part_id=item.spare_part_id,
            warehouse_id=item.warehouse_id,
            transaction_type=transaction_type,
            quantity=-item.quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            batch_no=item.batch_no,
            work_order_id=work_order_id,
            operator_id=operator_id,
            operator_name=operator_name,
            reference_no=reference_no,
            remarks=remarks,
        )
        db.add(detail)
        await db.flush()
        tx_ids.append(detail.id)

        # Recalculate spare part aggregate
        await _update_spare_part_stock(db, item.spare_part_id)

        sp_refreshed = await _get_spare_part(db, item.spare_part_id)
        changes.append(StockChange(
            spare_part_id=item.spare_part_id,
            warehouse_id=item.warehouse_id,
            old_stock=old_stock,
            new_stock=float(sp_refreshed.current_stock),
            change=-item.quantity,
        ))

    await db.commit()
    return tx_ids, changes


# ── Reserve (预留) ────────────────────────────────────────────────────────────

async def reserve_stock(
    db: AsyncSession,
    work_order_id: str,
    items: List[dict],
    reserve_notes: Optional[str] = None,
) -> Tuple[str, List[dict], datetime]:
    """Reserve stock for a work order. Returns reservation_id, items, expires_at."""
    reservation_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=24)
    reserved_items = []

    for item in items:
        sp = await _get_spare_part(db, item["spare_part_id"])
        await _get_warehouse(db, item["warehouse_id"])

        if float(sp.available_stock) < item["quantity"]:
            raise AppException(
                status_code=422,
                message=f"备件 {sp.spare_part_code} 可用库存不足，无法预留",
            )

        reservation = InventoryReservation(
            id=reservation_id if len(items) == 1 else str(uuid.uuid4()),
            work_order_id=work_order_id,
            spare_part_id=item["spare_part_id"],
            warehouse_id=item["warehouse_id"],
            quantity=item["quantity"],
            reserve_notes=reserve_notes,
            expires_at=expires_at,
        )
        db.add(reservation)

        # Recalculate available stock
        await db.flush()
        await _update_spare_part_stock(db, item["spare_part_id"])

        sp_refreshed = await _get_spare_part(db, item["spare_part_id"])
        reserved_items.append({
            "spare_part_id": item["spare_part_id"],
            "spare_part_name": sp.spare_part_name,
            "warehouse_id": item["warehouse_id"],
            "quantity": item["quantity"],
            "available_after_reserve": float(sp_refreshed.available_stock),
        })

    await db.commit()
    return reservation_id, reserved_items, expires_at


async def release_reservation(db: AsyncSession, reservation_id: str) -> None:
    """Release a stock reservation."""
    result = await db.execute(
        select(InventoryReservation).where(
            InventoryReservation.id == reservation_id,
            InventoryReservation.status == "active",
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise AppException(status_code=404, message="预留记录不存在或已释放")

    reservation.status = "released"
    await db.flush()
    await _update_spare_part_stock(db, reservation.spare_part_id)
    await db.commit()


# ── Query helpers ─────────────────────────────────────────────────────────────

async def list_transactions(
    db: AsyncSession,
    spare_part_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    transaction_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[InventoryDetail], int]:
    stmt = select(InventoryDetail)
    if spare_part_id:
        stmt = stmt.where(InventoryDetail.spare_part_id == spare_part_id)
    if warehouse_id:
        stmt = stmt.where(InventoryDetail.warehouse_id == warehouse_id)
    if transaction_type:
        stmt = stmt.where(InventoryDetail.transaction_type == transaction_type)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(InventoryDetail.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def list_snapshots(
    db: AsyncSession,
    spare_part_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
) -> List[InventorySnapshot]:
    stmt = select(InventorySnapshot).where(InventorySnapshot.quantity > 0)
    if spare_part_id:
        stmt = stmt.where(InventorySnapshot.spare_part_id == spare_part_id)
    if warehouse_id:
        stmt = stmt.where(InventorySnapshot.warehouse_id == warehouse_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_warehouses(db: AsyncSession) -> List[Warehouse]:
    result = await db.execute(select(Warehouse).where(Warehouse.is_active == True))
    return list(result.scalars().all())
